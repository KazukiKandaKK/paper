from __future__ import annotations

from paper2exp.core.models import ExperimentSpec


def format_ok(spec: ExperimentSpec) -> bool:
    return spec is not None
