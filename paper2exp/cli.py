from __future__ import annotations

from pathlib import Path
import os

import typer

from paper2exp.core.pipeline import batch_run, report_run, run_pipeline

app = typer.Typer(add_completion=False)


@app.command()
def run(
    paper_ref: str,
    workdir: Path = typer.Option(None, "--workdir", exists=False, dir_okay=True),
    mode: str = typer.Option("smoke", "--mode"),
    no_exec: bool = typer.Option(False, "--no-exec"),
    llm: str = typer.Option("none", "--llm"),
    llm_model: str = typer.Option("gemini-2.5-flash", "--llm-model"),
    download_pdf: bool = typer.Option(False, "--download-pdf"),
    agent: bool = typer.Option(False, "--agent"),
    max_agent_steps: int = typer.Option(2, "--max-agent-steps"),
    allow_network: bool = typer.Option(False, "--allow-network"),
    allow_package_install: bool = typer.Option(False, "--allow-package-install"),
    allow_write_repo: bool = typer.Option(False, "--allow-write-repo"),
    repo_url: str | None = typer.Option(None, "--repo-url"),
    repo_strategy: str = typer.Option("prefer_user_then_paper", "--repo-strategy"),
    repo_validate_only: bool = typer.Option(False, "--repo-validate-only"),
    paper_to_code: bool = typer.Option(False, "--paper-to-code"),
    repo_failure_policy: str | None = typer.Option(None, "--repo-failure-policy"),
    insights: bool = typer.Option(False, "--insights"),
    insights_lang: str = typer.Option("ja", "--insights-lang"),
    insights_max_applications: int = typer.Option(6, "--insights-max-applications"),
    insights_no_llm: bool = typer.Option(False, "--insights-no-llm"),
    on_missing_pytest: str = typer.Option("fallback_smoke", "--on-missing-pytest"),
) -> None:
    """Run a single paper pipeline."""
    if agent and llm != "gemini":
        raise typer.BadParameter("--agent requires --llm gemini")
    if agent and no_exec:
        raise typer.BadParameter("--agent requires execution (remove --no-exec)")
    if repo_validate_only and no_exec:
        raise typer.BadParameter("--repo-validate-only cannot be used with --no-exec")
    if llm == "gemini":
        _require_gemini_env()
    run_dir = run_pipeline(
        paper_ref,
        workdir=workdir,
        mode=mode,
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
    typer.echo(str(run_dir))


@app.command()
def batch(
    config_path: Path,
    workdir: Path = typer.Option(None, "--workdir", exists=False, dir_okay=True),
    no_exec: bool = typer.Option(False, "--no-exec"),
    llm: str = typer.Option("none", "--llm"),
    llm_model: str = typer.Option("gemini-2.5-flash", "--llm-model"),
    download_pdf: bool = typer.Option(False, "--download-pdf"),
    agent: bool = typer.Option(False, "--agent"),
    max_agent_steps: int = typer.Option(2, "--max-agent-steps"),
    allow_network: bool = typer.Option(False, "--allow-network"),
    allow_package_install: bool = typer.Option(False, "--allow-package-install"),
    allow_write_repo: bool = typer.Option(False, "--allow-write-repo"),
    repo_url: str | None = typer.Option(None, "--repo-url"),
    repo_strategy: str = typer.Option("prefer_user_then_paper", "--repo-strategy"),
    repo_validate_only: bool = typer.Option(False, "--repo-validate-only"),
    paper_to_code: bool = typer.Option(False, "--paper-to-code"),
    repo_failure_policy: str | None = typer.Option(None, "--repo-failure-policy"),
    insights: bool = typer.Option(False, "--insights"),
    insights_lang: str = typer.Option("ja", "--insights-lang"),
    insights_max_applications: int = typer.Option(6, "--insights-max-applications"),
    insights_no_llm: bool = typer.Option(False, "--insights-no-llm"),
    on_missing_pytest: str = typer.Option("fallback_smoke", "--on-missing-pytest"),
) -> None:
    """Run pipeline for a list of papers."""
    if agent and llm != "gemini":
        raise typer.BadParameter("--agent requires --llm gemini")
    if agent and no_exec:
        raise typer.BadParameter("--agent requires execution (remove --no-exec)")
    if repo_validate_only and no_exec:
        raise typer.BadParameter("--repo-validate-only cannot be used with --no-exec")
    if llm == "gemini":
        _require_gemini_env()
    results = batch_run(
        config_path,
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
    for run_dir in results:
        typer.echo(str(run_dir))


@app.command()
def report(run_dir: Path) -> None:
    """Print a concise status summary."""
    report = report_run(run_dir)
    typer.echo(f"Run: {report['run_dir']}")
    typer.echo(f"Summary exists: {report['summary_exists']}")
    if report["summary"]:
        typer.echo("---")
        typer.echo(report["summary"].strip())
    typer.echo(f"Spec: {report['spec']}")
    typer.echo(f"Results: {report['results']}")


def _require_gemini_env() -> None:
    required = [
        "GOOGLE_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_VERTEXAI",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise typer.BadParameter(f"Missing env vars for Gemini: {', '.join(missing)}")


if __name__ == "__main__":
    app()
