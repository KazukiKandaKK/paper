from __future__ import annotations


def classify_blockers(signals: list[dict]) -> list[dict]:
    blockers_map: dict[str, dict] = {}

    def add(kind: str, description: str, severity: str, basis: str, signal_id: str) -> None:
        if kind not in blockers_map:
            blockers_map[kind] = {
                "kind": kind,
                "description": description,
                "severity": severity,
                "basis": basis,
                "signal_ids": [signal_id],
            }
            return
        if signal_id not in blockers_map[kind]["signal_ids"]:
            blockers_map[kind]["signal_ids"].append(signal_id)

    for signal in signals:
        quote = (signal.get("quote") or "").lower()
        signal_id = signal.get("id")
        if not signal_id:
            continue
        source = signal.get("source")
        basis = "summary"
        if source == "repo_validation":
            basis = "repo_validation"
        elif source == "results_jsonl":
            basis = "run_log"
        elif source == "bench_report":
            basis = "bench_report"

        if "could not read username" in quote or "permission denied" in quote or "authentication" in quote:
            add("auth", "authentication or permission issue", "high", basis, signal_id)
            continue
        if "nodename nor servname" in quote or "could not resolve host" in quote or "name or service not known" in quote:
            add("network_dns", "network/DNS resolution failure", "high", basis, signal_id)
            continue
        if "no module named pytest" in quote or "command not found" in quote or "no module named" in quote:
            add("missing_dependency", "missing dependency for execution", "medium", basis, signal_id)
            continue
        if "repository not found" in quote or "repo_not_found" in quote:
            add("repo_not_found", "repository not found", "high", basis, signal_id)
            continue
        if "pytest" in quote and "exit_code" in quote and "exit_code=0" not in quote:
            add("test_failed", "tests failed", "medium", basis, signal_id)
            continue

    return list(blockers_map.values())
