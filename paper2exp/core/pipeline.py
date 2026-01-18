from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import yaml

from paper2exp.core.acquire.repo import clone_repo
from paper2exp.core.build.env import build_env, venv_python
from paper2exp.core.eval.scoring import load_last_result, write_compare
from paper2exp.core.insights.maturity import compute_maturity
from paper2exp.core.insights.runner import run_insights
from paper2exp.core.run.status import compute_repro_status
from paper2exp.core.build.deps import ensure_pytest
from paper2exp.core.ingest.arxiv import parse_arxiv_id
from paper2exp.core.ingest.service import ingest_paper
from paper2exp.core.memory.store import record_failure
from paper2exp.core.models import ExperimentSpec
from paper2exp.core.repo.discovery import (
    candidate_from_user,
    extract_candidates_from_llm,
    extract_candidates_from_text,
)
from paper2exp.core.repo.select import SelectionResult, select_repo
from paper2exp.core.repo.validate import ValidationResult, validate_candidates
from paper2exp.core.run.runner import Runner
from paper2exp.core.run.smoke import select_smoke_command, write_run_script
from paper2exp.core.understand.spec import build_experiment_spec
from paper2exp.core.understand.text import extract_text_from_pdf
from paper2exp.core.utils import append_jsonl, ensure_dir, safe_slug, utc_timestamp, write_text
from paper2exp.core.writeup.summary import write_summary
from paper2exp.bench.suites import run_benchmarks


REQUIRED_FILES = [
    "paper/metadata.json",
    "repro/spec.yaml",
    "repro/run.sh",
    "repro/results.jsonl",
    "repro/compare.md",
    "summary.md",
    "bench/report.md",
]


def _init_run_dirs(base: Path, paper_ref: str) -> Path:
    arxiv_id = parse_arxiv_id(paper_ref)
    slug_source = arxiv_id or paper_ref
    run_id = f"{utc_timestamp()}_{safe_slug(slug_source)}"
    run_dir = base / "runs" / run_id
    for sub in ["paper", "repro", "bench", "logs", "code"]:
        ensure_dir(run_dir / sub)
    for file_rel in REQUIRED_FILES:
        path = run_dir / file_rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
    (run_dir / "bench" / "results.json").write_text("{}", encoding="utf-8")
    return run_dir


def _log_event(results_path: Path, stage: str, status: str, details: dict) -> None:
    append_jsonl(
        results_path,
        {"stage": stage, "status": status, "details": details},
    )


def run_pipeline(
    paper_ref: str,
    workdir: Optional[Path] = None,
    mode: str = "smoke",
    no_exec: bool = False,
    llm: str = "none",
    llm_model: str = "gemini-2.5-flash",
    download_pdf: bool = False,
    agent: bool = False,
    max_agent_steps: int = 2,
    allow_network: bool = False,
    allow_package_install: bool = False,
    allow_write_repo: bool = False,
    repo_url: str | None = None,
    repo_strategy: str = "prefer_user_then_paper",
    repo_validate_only: bool = False,
    paper_to_code: bool = False,
    repo_failure_policy: str | None = None,
    insights: bool = False,
    insights_lang: str = "ja",
    insights_max_applications: int = 6,
    insights_no_llm: bool = False,
    on_missing_pytest: str = "fallback_smoke",
    llm_client=None,
) -> Path:
    base = workdir or Path.cwd()
    run_dir = _init_run_dirs(base, paper_ref)
    results_path = run_dir / "repro" / "results.jsonl"
    runner = Runner(results_path=results_path, logs_dir=run_dir / "logs", no_exec=no_exec)

    paper_dir = run_dir / "paper"
    code_dir = run_dir / "code"
    notes = ""
    if repo_failure_policy is None:
        repo_failure_policy = "fallback_paper_to_code" if agent else "stop"
    if repo_failure_policy not in {"stop", "fallback_paper_to_code"}:
        raise ValueError("invalid repo_failure_policy")
    repo_ok = False
    exec_ok = False
    pytest_required = True
    pytest_available = False
    pytest_install_attempted = False
    pytest_install_ok: bool | None = None
    pytest_reason = ""
    spec: Optional[ExperimentSpec] = None
    selection = SelectionResult(selected_url=None, reason="not evaluated")
    validation_results: list[ValidationResult] = []

    try:
        metadata = ingest_paper(
            paper_ref,
            paper_dir,
            allow_metadata_fetch=allow_network,
            download_pdf=download_pdf,
        )
    except Exception as exc:
        metadata = None
        notes = f"ingest failed: {exc}"
        _log_event(results_path, "ingest", "error", {"error": str(exc)})

    combined_text = ""
    if metadata:
        pdf_text = extract_text_from_pdf(paper_dir / "paper.pdf")
        combined_text = "\n".join([metadata.summary or "", pdf_text]).strip()
        spec = build_experiment_spec(metadata.id, metadata.title, metadata.links, combined_text)
    else:
        spec = ExperimentSpec.model_validate(
            {
                "paper": {
                    "id": paper_ref,
                    "title": paper_ref,
                    "links": {},
                },
                "repro": {"repo": {}, "env": {"python": "3.11", "notes": ""}, "runs": []},
                "eval": {"target_metrics": []},
                "bench": {"suites": ["stability_3seeds", "cost_profile", "rerun_clean"]},
            }
        )
        spec.ensure_default_run()

    if llm != "none" and download_pdf and combined_text:
        from paper2exp.core.llm.manager import run_llm_extract

        spec, _ = run_llm_extract(
            spec,
            paper_id=spec.paper.id,
            arxiv_url=spec.paper.links.arxiv,
            pdf_url=spec.paper.links.pdf,
            paper_title=spec.paper.title,
            paper_text=combined_text,
            llm=llm,
            model=llm_model,
            run_dir=run_dir,
            llm_client=llm_client,
        )
    elif llm != "none":
        llm_dir = run_dir / "llm"
        llm_dir.mkdir(parents=True, exist_ok=True)
        write_text(llm_dir / "decision.md", "LLM skipped: no paper text available.")

    spec_path = run_dir / "repro" / "spec.yaml"
    spec_path.write_text(yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8")

    repo_dir = run_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    candidates = _build_repo_candidates(
        repo_url=repo_url,
        paper_text=combined_text,
        llm_dir=run_dir / "llm",
    )
    _write_candidates(repo_dir, candidates)

    if not no_exec and allow_network:
        validate_urls = [cand.normalized_url for cand in candidates]
        validation_results = validate_candidates(validate_urls, runner)
        _write_validation(repo_dir, validation_results)
        selection = select_repo(candidates, validation_results, repo_strategy)
    else:
        selection = _select_without_validation(candidates, repo_strategy)
        _write_validation(repo_dir, [])

    _write_selection(repo_dir, selection, repo_strategy)

    if selection.selected_url:
        spec.repro.repo.url = selection.selected_url
    spec.repro.repo.candidates = [cand.normalized_url for cand in candidates[:5]]
    spec_path.write_text(yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8")

    if repo_validate_only:
        notes = "repo validation only; skipping clone/run"
        status = compute_repro_status(run_dir, repo_ok)
        maturity = compute_maturity(run_dir, repo_ok, status.paper_to_code_generated)
        write_summary(
            run_dir,
            spec,
            exec_ok=status.exec_ok,
            repo_ok=repo_ok,
            notes=notes,
            repro_executed=status.repro_executed,
            repro_verified=status.repro_verified,
            paper_to_code_generated=status.paper_to_code_generated,
            repro_status=status.official_status,
            repro_reason=status.reason,
            maturity_level=maturity.level,
            maturity_reason=maturity.reason,
            pytest_required=pytest_required,
            pytest_available=pytest_available,
            pytest_install_attempted=pytest_install_attempted,
            pytest_install_ok=pytest_install_ok,
            pytest_reason=pytest_reason,
        )
        if insights:
            run_insights(
                run_dir,
                spec,
                llm=llm,
                llm_model=llm_model,
                insights_lang=insights_lang,
                insights_max_applications=insights_max_applications,
                insights_no_llm=insights_no_llm,
                llm_client=llm_client,
            )
        return run_dir

    if not no_exec and allow_network and selection.selected_url:
        try:
            repo_ok = clone_repo(spec.repro.repo.url, code_dir, runner)
        except Exception as exc:
            _log_event(results_path, "acquire", "error", {"error": str(exc)})
    elif selection.selected_url is None:
        notes = "追試未成立: repoが検証できませんでした。"

    fallback_enabled = repo_failure_policy == "fallback_paper_to_code" or paper_to_code
    repo_unavailable = selection.selected_url is None or not repo_ok
    if not no_exec and fallback_enabled and repo_unavailable:
        from paper2exp.core.paper_to_code.planner import write_paper_to_code_artifacts

        selection.fallback_reason = "repo validation/clone failed; fallback to paper-to-code"
        _write_selection(repo_dir, selection, repo_strategy)
        write_paper_to_code_artifacts(
            run_dir,
            paper_text=combined_text,
            llm_response_path=run_dir / "llm" / "response.json",
        )
        if notes:
            notes = f"{notes} repo検証失敗→paper-to-codeへフォールバック"
        else:
            notes = "repo検証失敗→paper-to-codeへフォールバック"
        notes = f"{notes} (override: --repo-url)"

    try:
        venv_dir = build_env(
            run_dir,
            code_dir,
            runner,
            no_exec=no_exec,
            allow_package_install=allow_package_install,
        )
    except Exception as exc:
        venv_dir = run_dir / ".venv"
        _log_event(results_path, "build", "error", {"error": str(exc)})

    if not no_exec:
        ensure = ensure_pytest(
            venv_python(venv_dir),
            runner,
            allow_network=allow_network,
            allow_package_install=allow_package_install,
        )
        pytest_available = ensure.available
        pytest_install_attempted = ensure.install_attempted
        pytest_install_ok = ensure.install_ok
        pytest_reason = ensure.reason

    smoke_cmd = select_smoke_command(code_dir, venv_python(venv_dir))
    missing_pytest = pytest_required and not pytest_available and not no_exec
    if missing_pytest and on_missing_pytest == "fallback_smoke":
        smoke_cmd = [str(venv_python(venv_dir)), "-c", "print('smoke ok')"]
        if spec.repro.runs:
            spec.repro.runs[0].command = ["python", "-c", "print('smoke ok')"]
        else:
            spec.repro.runs = [
                {"name": "smoke", "command": ["python", "-c", "print('smoke ok')"], "seeds": None}
            ]
        spec_path.write_text(yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8")
    run_script_path = run_dir / "repro" / "run.sh"
    write_run_script(run_script_path, [list(smoke_cmd)])

    result = None
    if mode == "smoke":
        if missing_pytest and on_missing_pytest == "fail":
            notes = "pytest missing; run skipped"
        else:
            try:
                result = runner.run(smoke_cmd, cwd=code_dir)
                exec_ok = result.get("exit_code") == 0
                if result.get("exit_code") not in (0, None):
                    record_failure(run_dir, result.get("stderr_tail", ""), {"stage": "run"})
            except Exception as exc:
                _log_event(results_path, "run", "error", {"error": str(exc)})
                notes = f"run failed: {exc}"

    if not no_exec and (repo_failure_policy == "fallback_paper_to_code" or paper_to_code):
        if selection.selected_url is None or not repo_ok:
            _create_paper_to_code_skeleton(code_dir)

    if agent and not no_exec and llm != "none" and not exec_ok:
        from paper2exp.core.llm.agent_prompts import DEFAULT_ALLOWLIST_EXECUTABLES
        from paper2exp.core.llm.manager import run_llm_repair

        allowlist = set(DEFAULT_ALLOWLIST_EXECUTABLES)
        auto_run = os.getenv("PAPER2EXP_AGENT_AUTO", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        for step in range(1, max_agent_steps + 1):
            last_lines = _tail_lines(results_path, max_lines=10)
            stderr_tail = (result or {}).get("stderr_tail", "")
            stdout_tail = (result or {}).get("stdout_tail", "")
            bench_report = (run_dir / "bench" / "report.md").read_text(encoding="utf-8")
            spec, decision = run_llm_repair(
                spec,
                repo_file_index="",
                repo_file_snippets="",
                last_results_jsonl_lines=last_lines,
                stderr_tail=stderr_tail,
                stdout_tail=stdout_tail,
                bench_report_md=bench_report,
                llm=llm,
                model=llm_model,
                run_dir=run_dir,
                allowlist=allowlist,
                allow_network=allow_network,
                allow_package_install=allow_package_install,
                allow_write_repo=allow_write_repo,
                max_steps=max_agent_steps,
                step_index=step,
                llm_client=llm_client,
            )
            spec_path.write_text(
                yaml.safe_dump(spec.model_dump(), sort_keys=False), encoding="utf-8"
            )
            if decision.stop or not auto_run:
                break
            suggested = [s for s in decision.accepted_suggestions if not s.get("needs_approval")]
            if not suggested:
                break
            command = suggested[0]["command"]
            result = runner.run(command, cwd=code_dir)
            exec_ok = result.get("exit_code") == 0
            if exec_ok:
                break

    bench_no_exec = no_exec or (missing_pytest and on_missing_pytest == "fail")
    bench_results = run_benchmarks(spec, run_dir, code_dir, smoke_cmd, runner, bench_no_exec)
    rerun_result = bench_results.get("rerun_clean", {})
    if isinstance(rerun_result, dict) and "exit_code" in rerun_result:
        rerun_ok = rerun_result.get("exit_code") == 0
    else:
        rerun_ok = None

    status = compute_repro_status(run_dir, repo_ok)
    maturity = compute_maturity(run_dir, repo_ok, status.paper_to_code_generated)
    compare = write_compare(spec, run_dir, rerun_ok, exec_ok_override=status.exec_ok)
    exec_ok = compare.get("exec_ok", status.exec_ok)
    write_summary(
        run_dir,
        spec,
        exec_ok=exec_ok,
        repo_ok=repo_ok,
        notes=notes,
        repro_executed=status.repro_executed,
        repro_verified=status.repro_verified,
        paper_to_code_generated=status.paper_to_code_generated,
        repro_status=status.official_status,
        repro_reason=status.reason,
        maturity_level=maturity.level,
        maturity_reason=maturity.reason,
        pytest_required=pytest_required,
        pytest_available=pytest_available,
        pytest_install_attempted=pytest_install_attempted,
        pytest_install_ok=pytest_install_ok,
        pytest_reason=pytest_reason,
    )

    if insights:
        run_insights(
            run_dir,
            spec,
            llm=llm,
            llm_model=llm_model,
            insights_lang=insights_lang,
            insights_max_applications=insights_max_applications,
            insights_no_llm=insights_no_llm,
            llm_client=llm_client,
        )

    return run_dir


def load_seed_list(path: Path) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [str(item) for item in data]
    if isinstance(data, dict):
        papers = []
        for value in data.values():
            if isinstance(value, list):
                papers.extend([str(item) for item in value])
        return papers
    return []


def batch_run(
    path: Path,
    workdir: Optional[Path],
    no_exec: bool,
    llm: str = "none",
    llm_model: str = "gemini-2.5-flash",
    download_pdf: bool = False,
    agent: bool = False,
    max_agent_steps: int = 2,
    allow_network: bool = False,
    allow_package_install: bool = False,
    allow_write_repo: bool = False,
    repo_url: str | None = None,
    repo_strategy: str = "prefer_user_then_paper",
    repo_validate_only: bool = False,
    paper_to_code: bool = False,
    repo_failure_policy: str | None = None,
    insights: bool = False,
    insights_lang: str = "ja",
    insights_max_applications: int = 6,
    insights_no_llm: bool = False,
    on_missing_pytest: str = "fallback_smoke",
) -> list[Path]:
    results = []
    for paper_ref in load_seed_list(path):
        results.append(
            run_pipeline(
                paper_ref,
                workdir=workdir,
                no_exec=no_exec,
                llm=llm,
                llm_model=llm_model,
                download_pdf=download_pdf,
                agent=agent,
                max_agent_steps=max_agent_steps,
                allow_network=allow_network,
                allow_package_install=allow_package_install,
                allow_write_repo=allow_write_repo,
                repo_url=repo_url,
                repo_strategy=repo_strategy,
                repo_validate_only=repo_validate_only,
                paper_to_code=paper_to_code,
                repo_failure_policy=repo_failure_policy,
                insights=insights,
                insights_lang=insights_lang,
                insights_max_applications=insights_max_applications,
                insights_no_llm=insights_no_llm,
                on_missing_pytest=on_missing_pytest,
            )
        )
    return results


def report_run(run_dir: Path) -> dict:
    summary_path = run_dir / "summary.md"
    return {
        "run_dir": str(run_dir),
        "summary_exists": summary_path.exists(),
        "summary": summary_path.read_text(encoding="utf-8") if summary_path.exists() else "",
        "spec": str(run_dir / "repro" / "spec.yaml"),
        "results": str(run_dir / "repro" / "results.jsonl"),
    }


def _tail_lines(path: Path, max_lines: int = 10) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def _build_repo_candidates(
    repo_url: str | None,
    paper_text: str,
    llm_dir: Path,
) -> list:
    candidates = []
    if repo_url:
        candidates.append(candidate_from_user(repo_url))
    candidates.extend(extract_candidates_from_text(paper_text, source="paper_text"))
    response_path = llm_dir / "response.json"
    if response_path.exists():
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            response = {}
        candidates.extend(extract_candidates_from_llm(response, paper_text))
    # de-duplicate by normalized_url while preserving order
    unique: list = []
    seen: set[str] = set()
    for cand in candidates:
        if cand.normalized_url in seen:
            continue
        seen.add(cand.normalized_url)
        unique.append(cand)
    for idx, cand in enumerate(unique):
        cand.priority_rank = idx
    return unique


def _write_candidates(repo_dir: Path, candidates: list) -> None:
    payload = {
        "candidates": [
            {
                "url": cand.url,
                "normalized_url": cand.normalized_url,
                "source": cand.source,
                "priority_rank": cand.priority_rank,
                "evidence": {
                    "locator": cand.evidence.locator if cand.evidence else None,
                    "quote": cand.evidence.quote if cand.evidence else None,
                },
            }
            for cand in candidates
        ]
    }
    (repo_dir / "candidates.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_validation(repo_dir: Path, results: list[ValidationResult]) -> None:
    payload = {
        "results": [
            {
                "url": item.url,
                "status": item.status,
                "stdout_tail": item.stdout_tail,
                "stderr_tail": item.stderr_tail,
            }
            for item in results
        ]
    }
    (repo_dir / "validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_selection(repo_dir: Path, selection: SelectionResult, strategy: str) -> None:
    payload = {
        "selected_url": selection.selected_url,
        "reason": selection.reason,
        "strategy": strategy,
        "fallback_reason": selection.fallback_reason,
    }
    (repo_dir / "selection.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _select_without_validation(candidates: list, strategy: str) -> SelectionResult:
    if candidates and candidates[0].source == "user_input":
        return SelectionResult(
            selected_url=candidates[0].normalized_url,
            reason="user_input (validation skipped)",
        )
    return SelectionResult(selected_url=None, reason="validation skipped")


def _create_paper_to_code_skeleton(code_dir: Path) -> None:
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "README.md").write_text(
        "# Minimal Paper-to-Code Skeleton\n\n"
        "This is a minimal placeholder implementation. Details are not confirmed.\n",
        encoding="utf-8",
    )
    (code_dir / "main.py").write_text(
        "from __future__ import annotations\n\n"
        "def main() -> None:\n"
        "    raise SystemExit('implementation details not confirmed')\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )
