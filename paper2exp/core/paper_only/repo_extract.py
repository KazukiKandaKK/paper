from __future__ import annotations

import re
from pathlib import Path

from paper2exp.core.paper_only.evidence import EvidenceBuilder
from paper2exp.core.utils import truncate_text


ENTRYPOINT_NAMES = {
    "train.py",
    "eval.py",
    "cli.py",
    "app.py",
    "main.py",
    "__main__.py",
}

COMMAND_RE = re.compile(r"^\s*(python3?|pytest|pip|make|bash|sh|torchrun|\./)\b")


def extract_repo_facts(base_dir: Path, files: list[Path]) -> tuple[dict, list[dict], EvidenceBuilder]:
    builder = EvidenceBuilder()
    facts = {
        "entrypoints": [],
        "dependencies": [],
        "repro_steps": [],
        "eval_harness": [],
        "config_surface": [],
    }

    def add_fact(kind: str, value: str, locator: str, quote: str) -> None:
        value = value.strip()
        if not value:
            return
        if value not in facts[kind]:
            facts[kind].append(value)
        builder.add("paper_repo", locator, quote)

    for path in files:
        rel = path.relative_to(base_dir)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        locator_prefix = str(rel)

        if rel.name in ENTRYPOINT_NAMES:
            add_fact("entrypoints", str(rel), f"{locator_prefix}:1", str(rel))

        if rel.suffix in {".yaml", ".yml", ".json"} and (
            "config" in rel.name.lower() or "config" in rel.parts
        ):
            add_fact("config_surface", str(rel), f"{locator_prefix}:1", str(rel))

        if rel.name.startswith("requirements") and rel.name.endswith(".txt"):
            for idx, line in enumerate(lines, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                add_fact("dependencies", line, f"{locator_prefix}:{idx}", line)

        if rel.name == "pyproject.toml":
            for idx, line in enumerate(lines, start=1):
                if "dependencies" in line or "requires" in line:
                    add_fact(
                        "dependencies",
                        truncate_text(line, 200),
                        f"{locator_prefix}:{idx}",
                        line,
                    )

        if rel.name in {"environment.yml", "environment.yaml"}:
            for idx, line in enumerate(lines, start=1):
                if line.strip().startswith("- ") and not line.strip().startswith("- pip"):
                    add_fact(
                        "dependencies",
                        line.strip()[2:],
                        f"{locator_prefix}:{idx}",
                        line,
                    )

        if rel.name.lower() == "dockerfile":
            for idx, line in enumerate(lines, start=1):
                if "pip install" in line:
                    add_fact(
                        "dependencies",
                        truncate_text(line, 200),
                        f"{locator_prefix}:{idx}",
                        line,
                    )

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "```", ">")):
                continue
            if COMMAND_RE.match(stripped):
                add_fact(
                    "repro_steps",
                    truncate_text(stripped, 200),
                    f"{locator_prefix}:{idx}",
                    stripped,
                )
                if "pytest" in stripped:
                    add_fact("eval_harness", "pytest", f"{locator_prefix}:{idx}", stripped)
            if "--config" in stripped or "config=" in stripped:
                add_fact(
                    "config_surface",
                    truncate_text(stripped, 200),
                    f"{locator_prefix}:{idx}",
                    stripped,
                )
            if "eval" in stripped and stripped.endswith(".py"):
                add_fact(
                    "eval_harness",
                    truncate_text(stripped, 200),
                    f"{locator_prefix}:{idx}",
                    stripped,
                )

        if rel.parts and rel.parts[0] == "tests":
            add_fact("eval_harness", str(rel), f"{locator_prefix}:1", str(rel))

        if rel.name.endswith(".py") and rel.name in {"train.py", "evaluate.py", "evaluation.py"}:
            add_fact("entrypoints", str(rel), f"{locator_prefix}:1", str(rel))

    return facts, builder.items(), builder
