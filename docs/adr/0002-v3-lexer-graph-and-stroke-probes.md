# ADR 0002: Barrel-Aware Export Graph, Stroke-Gated Probes & Deterministic Scoring

- Status: Accepted
- Date: 2026-11-21
- Deciders: TeacherEvan, Hermes Agent

## Context

Self-auditing surgical-audit v2.4.0 against its own 10-lens and mutation-testing
standards surfaced concrete functional defects:

1. **Telemetry inaccuracies.** `preflight_telemetry.py` loaded whole files into
   RAM via `read_bytes()`, counted Python `with` and polyglot `else` as
   cyclomatic branches, double-counted `void Update(` / `FixedUpdate(` through
   overlapping substring triggers, counted `.map(` / `.filter(` outside any
   loop, pruned fewer directories than `dead_export_sweep.py`, and pinned
   `SA-SILENT-CATCH` / `SA-HOT-LOOP` SARIF results to line 1. Its C-style masker
   treated backtick templates as flat strings (wiping `${...}` branches) and did
   not handle JS/TS regex literals or `.svelte`/`.vue` `<script>` isolation.
2. **Barrel & duplicate masking.** `dead_export_sweep.py` used flat identifier
   subtraction, so an unused `index.ts` re-export or a sibling duplicate dead
   export name masked dead declarations as live.
3. **Canvas probe false positives & untestable architecture.** `proto.rect`
   incremented geometry counters during path construction, firing on
   `clip()`/`fill()` rects with zero strokes, and missed `Path2D`. The monolithic
   Playwright CLI had zero behavioural tests.
4. **Manual Pass-4 scoring.** Agents computed the square-root health score by
   hand despite an exact formula.
5. **PII policy & CI drift.** The negative PII assertion embedded private string
   fragments and exempted `tests/`; Ruff rules differed between `pyproject.toml`
   and `skill-ci.yml`; CI installs were unpinned; the installer hardcoded an
   18-item asset manifest.

## Decision

1. Upgrade `preflight_telemetry.py` to streaming 64 KiB SHA-256 hashing, a unified
   20-entry `PRUNE_DIRS`, standard McCabe branching (no `with`/`else`),
   non-overlapping context-gated hot-loop regexes, generic-function detection,
   a line-preserving masker handling regex literals, recursive `${...}` templates
   and SFC `<script>` extraction, and exact 1-based `silent_catch_lines` /
   `hot_loop_lines` emitted per-occurrence in SARIF 2.1.0. The public
   `silent_catches()` / `hot_loop_markers()` integer contracts are preserved;
   line arrays are additive schema fields.
2. Upgrade `dead_export_sweep.py` with a relative `import` / `export ... from`
   module-graph resolver that excludes barrel pass-throughs from live
   consumption, isolates duplicate declarers, and adds a first-class
   `dead_barrels` bucket.
3. Split pure stroke-gated Canvas/`Path2D` hooks and hue histograms into
   `scripts/canvas_probe_core.mjs`, tested by `tests/canvas_probe_core.test.mjs`
   via `node --test`. Geometry counters commit only on `stroke()` /
   `strokeRect()` / `stroke(Path2D)`.
4. Add deterministic `scripts/score_audit.py` + `schemas/audit-score.schema.json`
   implementing the documented Pass-4 formula (square-root scale) so scoring is
   never done by hand.
5. Enforce generic zero-PII/secret invariants across the whole repository
   (including `tests/`), consolidate Ruff rules into `pyproject.toml`, pin CI
   tool versions, add `node --test` and TOML/Markdown gates to CI, and make the
   installer discover assets dynamically. Keep canonical `scripts/conform.py`
   and `scripts/sync-skill.sh` byte-identical.

## Consequences

- Every CLI probe output validates strictly against Draft 2020-12 schemas
  (`unevaluatedProperties: false`).
- Both Python (`pytest`) and Node (`node --test`) suites verify real execution
  behaviour; each v3.0.0 defect fix is pinned by a regression test.
- The scoring formula keeps the repo-canonical square-root scale documented in
  `SKILL.md`; the non-sqrt variant proposed in external review was deliberately
  not adopted to avoid silently changing scoring semantics.
