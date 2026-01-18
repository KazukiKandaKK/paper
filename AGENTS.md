# AGENTS.md — Working agreements for Codex

## Goal
Build a Paper-to-Experiment agent (Paper2Exp) that turns paper URLs into:
- reproducible run bundles (env lock + run script + logs)
- benchmark reports
- a concise write-up

## Constraints
- Do not invent secrets, endpoints, or test results.
- Prefer minimal dependencies.
- Keep changes small and verifiable; run tests frequently.
- Always write to run-specific directories under `runs/` (no global state).

## Commands
- Run tests: `make test` (or `pytest -q` if Makefile unavailable)
- Lint (optional): `make lint`

## Output discipline
- Every run must create:
  - `runs/<run_id>/repro/spec.yaml`
  - `runs/<run_id>/repro/run.sh`
  - `runs/<run_id>/repro/results.jsonl`
  - `runs/<run_id>/summary.md`
  - `runs/<run_id>/repro/compare.md`

