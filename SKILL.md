---
name: surgical-audit
description: "Use when auditing code read-only across 10 lenses, in MD."
version: 3.0.0
author: "TeacherEvan, Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [code-review, surgical-audit, static-analysis, testing, refactoring, read-only]
    requires_tools: [read_file, search_files, terminal]
    related_skills: [surgical-investigation, surgical-implementation, surgical-hermesdothealth, surgical-orchestration]
---

# Surgical Audit (v3.0 — Principal-10 Polyglot Multi-Pass Architecture)

## Overview

Execute a deterministic, zero-mutation architectural, code, and runtime-geometry audit equivalent to a 10-Principal-Engineer review board across any programming language, game engine, application stack, or multi-file document bundle. It defeats middle-context attention collapse by combining AST/polyglot telemetry, stack-specific failure matrices, symbolic mental mutation testing, context-compaction batching, and quantitative health scoring into structured Markdown (`templates/report.md`) and SARIF 2.1.0 (`templates/report.sarif`) deliverables.

## When to Use

- Auditing an unfamiliar or fast-moving codebase, pre-refactor risk assessment, architecture review, or test-suite quality verification.
- Visual or behavioural complaints (`"lines across the screen"`, `"washed-out colours"`, `"it stutters"`, overlap/occlusion) where static inspection cannot prove a fix without runtime probing (`references/runtime-probe-harness.md`).
- Player/user engagement, juice, difficulty curves, and persistence audits via the 11th lens (`references/engagement-and-game-feel-audit.md`).
- Cross-file consistency checks across resume/CV/portfolio bundles, timelines, PDFs, and credentials (`references/document-audit.md`).
- Checking whether a codebase reaches its full potential: measure the largest concrete gap first and report quantified evidence (and if remediation is requested, execute and prove before/after metrics — never deliver an empty capability inventory).

## When Not to Use

- Single isolated bug fixes with an obvious root cause — start with `surgical-investigation` instead.
- Direct code edits requested upfront without an audit gate — route to `surgical-implementation`.
- Environment/workspace health triage — use `surgical-hermesdothealth`.

## Auxiliary Resources

Load detailed protocols, templates, and executable probes on demand using portable relative paths inside this skill directory:

- `scripts/preflight_telemetry.py` — Read-only polyglot AST/regex scanner emitting JSON (`schemas/telemetry.schema.json`) or `--sarif` OASIS SARIF 2.1.0 (`templates/report.sarif`). Streaming 64 KiB `tree_integrity_sha256`, unified 20-dir pruning, true Python AST CC (no `with`/`else` inflation) & control-flow nesting, docstring-excluded LOC, JS/TS ternary/`&&`/`||` branches, regex-literal/`${...}`-template/SFC-`<script>`-aware masking, generic-function detection, context-gated hot-loop markers, and exact 1-based `silent_catch_lines`/`hot_loop_lines` SARIF spans.
- `scripts/dead_export_sweep.py` — Barrel-aware exports sweep resolving relative `import`/`export ... from` graphs so unused `index.ts` re-exports and duplicate dead names cannot mask dead exports; buckets `dead_value_exports`, `test_only_exports`, `dead_type_exports`, and `dead_barrels` under `--src`/`--json` (`schemas/dead-export-sweep.schema.json`).
- `scripts/canvas_probe_core.mjs` — Pure, browser-free stroke-gated Canvas/`Path2D` geometry hooks + hue histogram, unit-tested by `tests/canvas_probe_core.test.mjs` (`node --test`). Counters commit only on `stroke()`/`strokeRect()`/`stroke(Path2D)`, so `clip()`/`fill()` rects yield zero false artefacts.
- `scripts/canvas_geometry_probe.mjs` — Playwright CLI reusing the core hook with `getTransform()`, error capture, and `try/finally` cleanup; adds `--click SELECTOR`, `--viewport WxH`, `--probe-ms N`, and `--wcag` (WCAG 2.5.8 target size, 2.4.11 focus occlusion, media queries) (`schemas/canvas-probe.schema.json`).
- `scripts/score_audit.py` — Deterministic Pass-4 Health Score CLI (`--telemetry`/`--loc`, `--html-loc`, `--p0..--p3`, `--killed`/`--evaluated`, `--json`/`--markdown`) implementing the exact square-root formula; output validates against `schemas/audit-score.schema.json`.
- `references/stack_failure_matrices.md` — Deep failure checklists for Games/WebGL (**A**), Next.js/React/Svelte/Convex (**B**), Python/C++/CLI/Agents (**C**), and Supply-Chain/Governance (**D**).
- `references/test_mutation_rubric.md` — **7 Vibe-Coded Test Pathologies**, regression acceptance gate, Mental Mutation Testing ($M_{\text{kill}}$), and MVTH tiers.
- `references/runtime-probe-harness.md` — Pristine-baseline A/B serving, canvas geometry/colour probes, WCAG 2.2 checks, and host-contention benchmarking (§8).
- `references/remediation-delivery.md` — Pass 4.5 delivery: green commit series, splitting interleaved file concerns, deployed artefact verification, ignore-file sandbox checks, and server-before-client releases.
- `references/engagement-and-game-feel-audit.md` — Authored-but-unwired detection, feedback matrix, difficulty arcs, `forced-colors`/`prefers-contrast`, and coverage tables.
- `references/document-audit.md` — Zero-mutation cross-file verification for document/CV packs using standard CLI extractors.
- `templates/report.md` and `templates/report.sarif` — Canonical Markdown audit template and OASIS SARIF 2.1.0 reference template.

## Hard Operational Invariants (Zero-Mutation Law)

1. **Zero Source Mutation:** Never create, edit, format, or delete any target repository source, config, or test file during Passes 1–4.
2. **Cryptographic Proof of Non-Mutation:** Record `tree_integrity_sha256` from `scripts/preflight_telemetry.py` (or `git status --porcelain` + `git rev-parse HEAD`) before Pass 1 and verify identical state in Pass 5. On dirty trees or before/after benchmarks, export a pristine baseline via `git archive HEAD | tar -x -C <scratch>/baseline` and serve it on a second port.
3. **Context-Compaction Batching Rule:** Inspect at most `5` implementation files or `1,200` effective LOC per turn. Audit larger repositories in ranked risk batches and log findings after each batch before synthesizing.
4. **No Generic Linter Filler:** Every finding MUST cite `file_path:L<start>-L<end>`, exact root-cause mechanism, concrete runtime trigger/failure scenario, and a surgical fix blueprint.

## Procedure

### Pass 1: Deterministic Preflight Telemetry & Topology Mapping

1. Run `python3 -B <skill>/scripts/preflight_telemetry.py <target_dir>` (add `--sarif --out /tmp/telemetry.sarif` for CI/IDE ingestion) to capture `tree_integrity_sha256`, ranked risk hotspots ($\text{Risk} = \text{LOC}_{\text{effective}} \times (1 + \text{BranchDensity}) + 50 \times N_{\text{SilentCatches}}$), God files (`>400` effective LOC), and complex functions ($CC \ge 10$, nesting $>5$, or $\text{LOC} \ge 60$).
2. Map entry points, global state/stores, event loops, I/O boundaries, and **AI Split-Brain State** (duplicated unsynchronized state).
3. Run `python3 -B <skill>/scripts/dead_export_sweep.py <target_dir> --src <src> --json` and verify candidates via `grep -rn "<symbol>" tests/ src/ e2e/` (a symbol cited *only* by tests proves green suite, dead in production).
4. Audit **dead subtrees and `index.ts` barrels**: count importers per suspicious directory (`grep -rn "from \"[./]*<dir>/" src`). A barrel imported only by itself marks an entire stale tree.
5. Triage every `duplicate_export_names` collision as a split-brain candidate: read both implementations before deciding which is live (never assume identical semantics).

### Pass 2: Stack Matrix Loading & The 10-Principal-Engineer Deep Audit

Load `references/stack_failure_matrices.md` and inspect batches across all 10 lenses (never silently omit a lens; mark non-applicable lenses `N/A — <1-sentence justification>`):

1. **Lens 1 — Systems Architect:** Circular imports, God objects mixing rendering/physics/I/O, boolean soup vs. explicit FSMs, leaky boundaries.
2. **Lens 2 — Frame-Budget & Performance:** Verify `16.67ms`/`8.33ms` budgets; flag hot-loop allocations, $O(N^2)$ scans, unbounded `.collect()`, N+1 queries, and **shipped-media payload bloat** (`git ls-files -z | xargs -0 du -h | sort -hr`).
3. **Lens 3 — Mathematical, Physics & Algorithmic:** Unclamped `dt`, non-`dt`-normalized damping, zero-vector `NaN`, float drift, off-by-one indexing, `mediump` overflow.
4. **Lens 4 — Concurrency, Async & Determinism:** TOCTOU races, stale closures, uncancelled `AbortController`/timers, blocking sync I/O on async loops.
5. **Lens 5 — Memory & Resource Lifecycle:** Unremoved listeners, uncancelled intervals/RAF, undisposed WebGL buffers/textures/AudioContexts, leaked file descriptors.
6. **Lens 6 — Security & Trust-Boundary:** Client-authoritative money/scores/auth, path traversal (`is_relative_to()`), `shell=True`, XSS, hardcoded secrets, **plus ignored server-computed verdicts** (flags persisted but ignored along payout/permission/audit gates = P0).
7. **Lens 7 — Reliability & Fault Tolerance:** Silent catches, non-atomic writes (`os.replace`), unguarded `JSON.parse`, missing retry/backoff.
8. **Lens 8 — Type Systems, Schema & Contracts:** Unvalidated external payloads, `any`/`# type: ignore` escapes, falsy `0`/`""` coercion bugs, mutable defaults, non-strict JSON Schemas.
9. **Lens 9 — Platform, Viewport & Portability:** Touch-hostile assumptions, missing `devicePixelRatio` scaling, CSS letterboxing desync, OS separator coupling.
10. **Lens 10 — Cognitive Load & AI Maintainability:** Deep nesting (`>3`), magic constants, inconsistent naming, boilerplate wasting agent context.

### Pass 2.5: Live Geometry & Runtime Probe

Mandatory for layout/overlap and rendered-artefact audits (`references/runtime-probe-harness.md`, `scripts/canvas_geometry_probe.mjs`):

- Serve app cleanly (`npx http-server -p 8000 -c-1 --cors -s &`); dismiss onboarding/input locks before sampling (`!document.body.classList.contains('<lock-class>')`).
- Measure **two rects** per entity: the element box (`elementFromPoint` tap target) and visual text `Range.getBoundingClientRect()`. Hit-test 5 points (`centre` + `4` inset corners) per entity, compute `chrome ∩ entityWindow`, compare `config.symbolWidth/Height` vs `offsetWidth/Height` (`>1.5x` = P1), avoid `.querySelector()` hitting pooled/hidden nodes, check `opacity: 0` elements lacking `pointer-events: none`, and inspect `getComputedStyle` specificity overrides (ID selectors beating `body.viewport-* .class`).
- Also probe WCAG `2.5.8` target size (`>=24px`), `2.4.11` focus visibility, `prefers-reduced-motion`/`prefers-contrast`/`forced-colors`, and composited pixel contrast. The probe CLI accepts `--click SELECTOR` (prerequisite setup), `--viewport WxH`, `--probe-ms N`, and `--wcag` to automate these checks.

### Pass 3: Existing Test Suite Comparison & Mental Mutation Analysis

Load `references/test_mutation_rubric.md` and construct the **Implementation vs. Test Matrix**:

1. Audit tests against the **7 Vibe-Coded Test Pathologies** (`Mock-Mirror`, `No-Throw Theater`, `Happy-Path Tunnel Vision`, `Shared Mutable State`, `Implementation-Coupled / Canvas-Stub`, `Time-Window Myopia`, `Result-Only Assertions`).
2. **Prove tested modules actually ship:** grep entry HTML and service-worker precache for every unit-tested module path; unshipped tested files count as `0%` coverage.
3. Evaluate mutants `M1–M4` (`Boundary Flip`, `Zero/Empty`, `Side-Effect Deletion`, `Async Failure`) to compute $M_{\text{kill}}\%$. **State the basis next to `$M_{\text{kill}}$`:** exact assertion count, negative/boundary assertion files, mock-heavy files, and unpaired critical modules.
4. Explain why existing tests missed every Pass 2 P0/P1 defect and specify a **Minimal Viable Test Harness (MVTH)** (`Tier 0–3`).

### Pass 4: Quantitative Scoring & Surgical Refactoring Architecture

Compute Health Score and Risk Level deterministically with `python3 -B <skill>/scripts/score_audit.py --telemetry /tmp/telemetry.json --p0 N --p1 N --p2 N --p3 N --killed K --evaluated E` (or `--loc N --html-loc H`); never do the floating-point math by hand. The formula:

- $D_{\text{raw}} = (18 \times N_{\text{P0}}) + (8 \times N_{\text{P1}}) + (3 \times N_{\text{P2}}) + (1 \times N_{\text{P3}})$ and $P_{\text{test}} = 15 \times (1 - M_{\text{kill}} / 100)$.
- $S_{\text{health}} = \max\left(0, \text{round}\left(100 - D_{\text{raw}} \times \sqrt{\frac{1000}{\max(500, \text{LOC}_{\text{effective}})}} - P_{\text{test}}\right)\right)$.
- Classification: **Low** ($\ge85$, $N_{\text{P0}}=0$), **Moderate** ($65\text{–}84$, $N_{\text{P0}}=0$), **High** ($40\text{–}64$ or $N_{\text{P0}}=1$), **Critical** ($<40$ or $N_{\text{P0}}\ge2$).
- Draft Before/After blueprints respecting the **Anti-Over-Abstraction Rule** (compact FSMs, pure helpers, fixed object pools, strict schemas).

### Pass 4.5: Remediation Hand-off (only when user requests fixes)

1. **Prove the regression test fails first:** assert the failure mode (not proxy existence) over `>=2` defect periods (compress cycle duration in runtime config if needed). Copy the fixed file to scratch, mechanically revert the fix (`assert old in s`), confirm the focused test fails with the pre-fix symptom, then restore and re-run green.
2. **Extract pure geometry/state maths** before writing unit tests; **swap layout caches atomically** (never null before rebuild); re-run the focused suite and check test fixtures/helpers before altering domain rules (`git log -S "<value>" -- <path>` before touching old assertions); grep `tests/`/`src/`/`e2e/` and migrate harnesses before removing dead exports.
3. **Land a green commit series** (`references/remediation-delivery.md`): one concern per commit, fix before assertion, prove every commit independently, enforce server-before-client contract order, and check repo change budgets (`convex codegen`/Prisma/Drizzle without deploy keys -> derive flags from existing columns instead of uncompilable schema edits). Turn ignored trust verdicts into explicit `needsReview` review states rather than deleting dispute evidence.
4. **Verify deployed artefacts, not HTTP `200`:** check CI permissions/runs (`0s startup_failure` = CI never ran), platform deployment records, bundle hash comparison (remember sandbox builds emit different hashes for identical source — verify by grepping served JS bundles AND every `<link>` CSS `href`, searching both `::before` and `:before`), and simulate host ignore files (`.vercelignore`/`.dockerignore`) from `git archive` if cloud builds fail while local passes.
5. **Host contention guard before any performance claim:** run `uptime` + `ps -eo pcpu,comm --sort=-pcpu | head` first (`references/runtime-probe-harness.md` §8); when noisy, report deterministic work counts and state wall-clock speed as unproven.

### Pass 5: Report Generation & Zero-Mutation Verification

Verify unchanged `tree_integrity_sha256` / `git status --porcelain`, synthesize the report strictly matching `templates/report.md` (and optional `templates/report.sarif` via `--sarif`), and write to `docs/audits/<project>-surgical-audit-<YYYY-MM-DD>.md` as a separate docs commit.

## Pitfalls

- **Health score saturation:** A repo with zero tests immediately loses 15 `P_test` points and docs-only skills drop rapidly on one P1; always report per-defect evidence alongside `$S_{\text{health}}$`.
- **Build-artefact test ordering:** Tests checking `dist/*` or `public/sw.js` fail before running the build step; build before scoring test failures.
- **Zero-mutation debris:** Never pollute audited checkouts with `__pycache__/`, `.mypy_cache/`, or `.ruff_cache/`; invoke `python3 -B` and write probe outputs to `/tmp` or scratch.
- **Clean `conform.py` vs. working skill:** Metadata conformance does not prove scripts work or assertions catch real bugs.
- **Order-dependent dedupe:** Dropping duplicate keys by "first encountered" creates query-order financial/scoring bugs; sort totally (`skew-corrected time -> _creationTime -> key`) and emit `needsReview` (`duplicate_key_conflict`) when payloads disagree.
- **Single-file HTML invisibility:** `preflight_telemetry.py` scans code extensions, missing inline `<script>` inside standalone `index.html`; manually measure HTML LOC (`wc -l`), run DOM/style greps, compute WCAG contrast tokens, and include HTML LOC in the report metadata.

## Related Skills

- `surgical-investigation` — Root-cause hypothesis verification for targeted defects.
- `surgical-implementation` — Scoped implementation execution once audit findings are approved.
- `surgical-hermesdothealth` — Runtime workspace, daemon, and skill environment diagnostics.
- `surgical-orchestration` — Multi-agent coordination across investigation, audit, and implementation waves.

## Author

TeacherEvan, Hermes Agent

## License

MIT — see `LICENSE`.
