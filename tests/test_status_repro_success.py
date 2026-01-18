from pathlib import Path

from paper2exp.core.run.status import compute_repro_status


def test_repro_verified_success(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "repro").mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "repro" / "results.jsonl"
    results_path.write_text(
        '{"id":1,"status":"ran","command":["python","-m","pytest","-q"],"exit_code":0}\n', encoding="utf-8"
    )
    status = compute_repro_status(run_dir, repo_cloned=True)
    assert status.repro_executed is True
    assert status.repro_verified is True
    assert status.exec_ok is True
