# Surgical Audit (`v3.0.0`)

**Deterministic, zero-mutation 10-Principal-Engineer code, visual-runtime, and document audit protocol across any stack.**

Combines AST/polyglot preflight telemetry (`preflight_telemetry.py`), dead-export sweeps (`dead_export_sweep.py`), Playwright Canvas 2D probes (`canvas_geometry_probe.mjs`), stack failure matrices, mental mutation testing ($M_{\text{kill}}$), quantitative health scoring, OASIS SARIF `2.1.0` reports, and Draft `2020-12` JSON Schemas.

## Architecture Overview

| Component | Purpose |
| :--- | :--- |
| [`SKILL.md`](SKILL.md) | Entrypoint manifest, Pass 1–5 protocol, Pass 2.5 runtime probing, Pass 4.5 delivery gates |
| [`AGENTS.md`](AGENTS.md) | Repo conventions, non-negotiable zero-PII/zero-mutation rules, and gate order |
| [`LICENSE`](LICENSE) | MIT License |
| [`scripts/preflight_telemetry.py`](scripts/preflight_telemetry.py) | Read-only scanner: streaming 64 KiB `tree_integrity_sha256`, unified pruning, per-function Python AST CC (no `with`/`else`) & nesting, docstring-excluded LOC, JS/TS short-circuit/ternary CC, regex/template/SFC-aware masking, exact-line SARIF 2.1.0 |
| [`scripts/dead_export_sweep.py`](scripts/dead_export_sweep.py) | Barrel-aware zero-caller & test-only export detector with `dead_barrels` bucket (relative import/export graph, `--src`, `--json`) |
| [`scripts/canvas_probe_core.mjs`](scripts/canvas_probe_core.mjs) | Pure stroke-gated Canvas/`Path2D` geometry hooks + hue histogram, tested via `node --test` (zero `clip()`/`fill()` false positives) |
| [`scripts/canvas_geometry_probe.mjs`](scripts/canvas_geometry_probe.mjs) | Playwright CLI reusing the core hook; `--click`, `--viewport`, `--probe-ms`, `--wcag` (WCAG 2.5.8/2.4.11/media queries) |
| [`scripts/score_audit.py`](scripts/score_audit.py) | Deterministic Pass-4 Health Score CLI (square-root formula, `--json`/`--markdown`) |
| [`scripts/conform.py`](scripts/conform.py) | Family metadata, reference, and canonical-digest conformance gate |
| [`scripts/sync-skill.sh`](scripts/sync-skill.sh) | Byte-verified 8-target local mirror sync (`check`, `sync`, `verify`, `list`) |
| [`references/stack_failure_matrices.md`](references/stack_failure_matrices.md) | Matrices A–D (Game/WebGL, React/Next/Convex, Python/C++/CLI/Agents, Supply-Chain/CVE/SBOM/`ast-grep`) |
| [`references/test_mutation_rubric.md`](references/test_mutation_rubric.md) | 7 Vibe-Coded Test Pathologies, regression gate, $M_{\text{kill}}$, MVTH pyramid |
| [`references/runtime-probe-harness.md`](references/runtime-probe-harness.md) | Pristine baselines, Canvas probes, WCAG 2.2 checks, host-load benchmarking (§8) |
| [`references/remediation-delivery.md`](references/remediation-delivery.md) | Green commit series, deployed artefact verification, ignore-file sandboxes, server-first releases |
| [`references/engagement-and-game-feel-audit.md`](references/engagement-and-game-feel-audit.md) | 11th lens: player feel, unwired systems, accessibility queries, coverage tables |
| [`references/document-audit.md`](references/document-audit.md) | Multi-file CV/document consistency & PDF/ATS verification guide (zero PII) |
| [`templates/`](templates/) | Markdown (`report.md`) and OASIS SARIF `2.1.0` (`report.sarif`) deliverables |
| [`schemas/`](schemas/) | Draft `2020-12` JSON Schemas (`unevaluatedProperties: false`) for all 4 tool outputs |
| [`docs/adr/0001-polyglot-telemetry-and-batching.md`](docs/adr/0001-polyglot-telemetry-and-batching.md) | Architecture Decision Record superseding legacy v2.1 scratch notes |
| [`docs/adr/0002-v3-lexer-graph-and-stroke-probes.md`](docs/adr/0002-v3-lexer-graph-and-stroke-probes.md) | v3.0.0 decisions: barrel graph, stroke-gated probes, deterministic scoring |

## Installation & Syncing Mirrors

From the root of this repository:

```bash
# Sync runtime assets to all 8 local agent skill targets and byte-verify
bash scripts/sync-skill.sh sync
bash scripts/sync-skill.sh verify
```

Or install into a standalone Hermes skill directory with `./install_surgical_audit.sh [target_dir]`.

## Usage Examples

```bash
# 1. Deterministic preflight telemetry (JSON or OASIS SARIF 2.1.0)
python3 -B scripts/preflight_telemetry.py /path/to/repo --out /tmp/telemetry.json
python3 -B scripts/preflight_telemetry.py /path/to/repo --sarif --out /tmp/telemetry.sarif

# 2. Dead & test-only export sweep (scanning whole repo while scoping exports to src/)
python3 -B scripts/dead_export_sweep.py /path/to/repo --src src --json

# 3. Deterministic Pass-4 Health Score
python3 -B scripts/score_audit.py --telemetry /tmp/telemetry.json \
  --p0 0 --p1 1 --p2 3 --p3 2 --killed 7 --evaluated 8 --markdown

# 4. Stroke-gated Canvas geometry, hue & WCAG 2.2 probe (requires Playwright)
node scripts/canvas_geometry_probe.mjs http://127.0.0.1:8000 300 "#game-canvas" \
  --click "#start-btn" --viewport 1280x720 --wcag

# 5. Run conformance, Python tests, and Node tests cleanly
python3 -B scripts/conform.py
pytest -o cache_dir=/tmp/pytest_cache_sa -v tests/
node --test tests/canvas_probe_core.test.mjs
```

## Non-Negotiable Invariants

- **Zero Mutation:** Probes never write into audited repositories. Invoke Python scripts with `python3 -B` and store output artifacts in `/tmp`.
- **Zero PII:** All examples, tests, schemas, and documentation use synthetic placeholders (`<user>@example.com`).
