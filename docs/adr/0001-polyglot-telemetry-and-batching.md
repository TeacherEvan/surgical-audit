# ADR 0001: Polyglot Telemetry, Context-Compaction Batching & Spec-Compliant Frontmatter

- **Status:** Accepted (distilled from v2.1.0–v2.4.0 design history; replaces raw scratch dump previously stored in `Docs/Surgical Audit 1 Omitted.txt`)
- **Date:** 2026-11-15

## Context

Three architectural constraints emerged during the evolution of `surgical-audit`:

1. **Multi-language telemetry without compiler toolchains:** Audits run on repositories spanning Python, TypeScript/JavaScript/React/Svelte, C#/Unity, GDScript, C/C++, GLSL, Rust, Go, and Lua where project toolchains may be offline or partially broken.
2. **LLM middle-context attention degradation:** Ingesting entire large codebases in a single prompt causes skipped files and hallucinated defects.
3. **Hermes / multi-agent spec compliance:** Overly verbose YAML frontmatter descriptions fail the 60-character Hermes discovery gate, and hardcoded home-directory paths break portable installs across mirrors.

## Decision

1. **Split AST vs. Lexical Scanners (`scripts/preflight_telemetry.py`):**
   - Use stdlib `ast` for Python (`analyze_python`), computing per-function cyclomatic complexity strictly from each function's own AST subtree (excluding nested function/class bodies) and true control-flow nesting depth (`If`/`For`/`While`/`Try`/`With`/`Match`).
   - Use comment/string-stripped lexical scanning (`analyze_polyglot_structure`) for non-Python languages, separating word-boundary branch keywords from symbolic short-circuit/ternary tokens (`&&`, `||`, `?:`).
   - Prune vendored and cache directories (`node_modules`, `.git`, `dist`, `build`, `.next`, `.turbo`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `venv`, `.venv`) during repository hashing and emit OASIS SARIF 2.1.0 when `--sarif` is passed.
2. **Ranked Hotspot Batching:** Cap audit file ingestion at `5` files or `1,200` effective LOC per turn using deterministic risk ranking (`LOC_effective * (1 + BranchDensity) + 50 * N_silent_catches`), recording per-batch findings before Pass 4 synthesis.
3. **Lean Conformance & Extracted Templates:** Keep `SKILL.md` descriptions `<= 60` characters (`Use when ... .`), extract large report/SARIF templates into `templates/`, validate outputs against Draft `2020-12` schemas (`schemas/*.schema.json`), and mirror runtime assets cleanly via `scripts/sync-skill.sh`.

## Consequences

- `Docs/Surgical Audit 1 Omitted.txt` (raw v2.1 design chat log) is superseded by this ADR and removed from the repository.
- All telemetry outputs conform to strict machine-validated JSON schemas (`unevaluatedProperties: false`) and OASIS SARIF `2.1.0`.
