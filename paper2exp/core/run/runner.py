from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from paper2exp.core.utils import append_jsonl, now_unix, truncate_text


@dataclass
class Runner:
    results_path: Path
    logs_dir: Path
    no_exec: bool = False
    counter: int = 0

    def run(self, command: Sequence[str], cwd: Path, timeout_sec: float | None = None) -> dict:
        self.counter += 1
        start = now_unix()
        record = {
            "id": self.counter,
            "command": list(command),
            "cwd": str(cwd),
            "start_time": start,
            "status": "skipped" if self.no_exec else "ran",
        }
        stdout_path = self.logs_dir / f"command_{self.counter}.out"
        stderr_path = self.logs_dir / f"command_{self.counter}.err"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        if self.no_exec:
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("(no-exec)", encoding="utf-8")
            record.update(
                {
                    "end_time": start,
                    "duration_sec": 0.0,
                    "exit_code": None,
                    "stdout_path": str(stdout_path),
                    "stderr_path": str(stderr_path),
                    "stdout_tail": "",
                    "stderr_tail": "(no-exec)",
                }
            )
            append_jsonl(self.results_path, record)
            return record

        exit_code = None
        status = "ran"
        with stdout_path.open("w", encoding="utf-8") as out_f, stderr_path.open(
            "w", encoding="utf-8"
        ) as err_f:
            if timeout_sec is None:
                proc = subprocess.Popen(
                    list(command), cwd=str(cwd), stdout=out_f, stderr=err_f, text=True
                )
                exit_code = proc.wait()
            else:
                try:
                    completed = subprocess.run(
                        list(command),
                        cwd=str(cwd),
                        stdout=out_f,
                        stderr=err_f,
                        text=True,
                        timeout=timeout_sec,
                    )
                    exit_code = completed.returncode
                except subprocess.TimeoutExpired:
                    status = "timeout"
                    exit_code = None
                    err_f.write("TIMEOUT\n")
                    err_f.flush()

        end = now_unix()
        stdout_tail = ""
        stderr_tail = ""
        if stdout_path.exists():
            stdout_tail = truncate_text(stdout_path.read_text(encoding="utf-8"), 4000)
        if stderr_path.exists():
            stderr_tail = truncate_text(stderr_path.read_text(encoding="utf-8"), 4000)
        record.update(
            {
                "end_time": end,
                "duration_sec": round(end - start, 4),
                "exit_code": exit_code,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "status": status,
            }
        )
        append_jsonl(self.results_path, record)
        return record
