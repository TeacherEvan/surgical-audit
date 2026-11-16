# AGENTS.md

Agent instructions for working inside the `surgical-audit` skill repository.

## Project Overview

- **Skill:** `surgical-audit` (`v2.4.0`) — zero-mutation 10-lens code & visual audit methodology with deterministic polyglot telemetry, dead-export sweeps, Playwright canvas geometry probes, SARIF 2.1.0 output, and Draft 2020-12 JSON schemas.
- **Layout:**
  - `SKILL.md` — concise entrypoint manifest & Pass 1–5 procedure (`<= 250` lines).
  - `references/` — detailed pass protocols (`stack_failure_matrices.md`, `test_mutation_rubric.md`, `runtime-probe-harness.md`, `remediation-delivery.md`, `engagement-and-game-feel-audit.md`, `document-audit.md`).
  - `scripts/` — runtime CLI probes (`preflight_telemetry.py`, `dead_export_sweep.py`, `canvas_geometry_probe.mjs`) and repo tooling (`conform.py`, `sync-skill.sh`).
  - `templates/` — Markdown (`report.md`) and SARIF 2.1.0 (`report.sarif`) deliverables.
  - `schemas/` — JSON Schema Draft `2020-12` contracts with `"unevaluatedProperties": false`.
  - `tests/` — `pytest` test suite verifying telemetry accuracy, dead-export detection, schema compliance, conformance, zero PII, and mirror syncing.
  - `docs/adr/` — architectural decision records.

## Non-Negotiable Constraints

1. **Zero PII:** Never include real personal emails, full names of private individuals, personal employers, home dotfiles, or credentials anywhere in `SKILL.md`, `references/`, `tests/`, or mirrored installs. Use synthetic placeholders (`<user>@example.com`, `<Candidate_Name>`).
2. **Scope Boundary:** Never modify sibling repositories (such as `Surgical-Pruning/`) from work inside this repository.
3. **Zero-Mutation Discipline:** Runtime audit tools (`preflight_telemetry.py`, `dead_export_sweep.py`, `canvas_geometry_probe.mjs`) must remain strictly read-only against audited target repositories. Never write `__pycache__/` or tool caches inside target checkouts.
4. **Canonical Sync Parity:** Keep `scripts/conform.py` and `scripts/sync-skill.sh` aligned with the `Surgical-Investigation` canonical copies. Mirror runtime assets via `bash scripts/sync-skill.sh sync && bash scripts/sync-skill.sh verify`.

## Verification Gates (Run in Order)

1. `python3 -B scripts/conform.py` (must print `PASS  surgical-audit` with zero mirror-drift warnings)
2. `taplo check pyproject.toml`
3. `ruff check --no-cache scripts/ tests/`
4. `ruff format --check --no-cache scripts/ tests/`
5. `mypy --strict --cache-dir /tmp/mypy_cache_sa scripts/ tests/`
6. `pytest -o cache_dir=/tmp/pytest_cache_sa -v tests/` (100% pass, `0` skipped)
7. `shellcheck -x install_surgical_audit.sh scripts/sync-skill.sh`
8. `yamllint --strict .github/workflows/skill-ci.yml`
9. `node --check scripts/canvas_geometry_probe.mjs`
10. `check-jsonschema --check-metaschema schemas/*.schema.json`
11. `markdownlint --disable MD013 -- *.md references/*.md templates/*.md docs/adr/*.md`
12. `bash scripts/sync-skill.sh verify`
