from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import yaml

from paper2exp.core.acquire.repo import clone_repo
from paper2exp.core.build.env import build_env, venv_python
from paper2exp.core.eval.scoring import load_last_result, write_compare
from paper2exp.core.ingest.arxiv import parse_arxiv_id
from paper2exp.core.ingest.service import ingest_paper
from paper2exp.core.memory.store import record_failure
from paper2exp.core.models import ExperimentSpec
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
    llm_client=None,
) -> Path:
    base = workdir or Path.cwd()
    run_dir = _init_run_dirs(base, paper_ref)
    results_path = run_dir / "repro" / "results.jsonl"
    runner = Runner(results_path=results_path, logs_dir=run_dir / "logs", no_exec=no_exec)

    paper_dir = run_dir / "paper"
    code_dir = run_dir / "code"
    notes = ""
    repo_ok = False
    exec_ok = False
    spec: Optional[ExperimentSpec] = None

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

    if not no_exec and allow_network:
        try:
            repo_ok = clone_repo(spec.repro.repo.url, code_dir, runner)
        except Exception as exc:
            _log_event(results_path, "acquire", "error", {"error": str(exc)})

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

    smoke_cmd = select_smoke_command(code_dir, venv_python(venv_dir))
    run_script_path = run_dir / "repro" / "run.sh"
    write_run_script(run_script_path, [list(smoke_cmd)])

    result = None
    if mode == "smoke":
        try:
            result = runner.run(smoke_cmd, cwd=code_dir)
            exec_ok = result.get("exit_code") == 0
            if result.get("exit_code") not in (0, None):
                record_failure(run_dir, result.get("stderr_tail", ""), {"stage": "run"})
        except Exception as exc:
            _log_event(results_path, "run", "error", {"error": str(exc)})
            notes = f"run failed: {exc}"

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

    bench_results = run_benchmarks(spec, run_dir, code_dir, smoke_cmd, runner, no_exec)
    rerun_result = bench_results.get("rerun_clean", {})
    if isinstance(rerun_result, dict) and "exit_code" in rerun_result:
        rerun_ok = rerun_result.get("exit_code") == 0
    else:
        rerun_ok = None

    compare = write_compare(spec, run_dir, rerun_ok)
    exec_ok = compare.get("exec_ok", exec_ok)
    write_summary(run_dir, spec, exec_ok=exec_ok, repo_ok=repo_ok, notes=notes)

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
