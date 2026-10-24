---
name: surgical-audit
description: "Use when auditing code read-only across 10 lenses, in MD."
version: 2.3.0
author: "TeacherEvan, Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [code-review, surgical-audit, static-analysis, testing, refactoring, read-only]
    requires_tools: [read_file, search_files, terminal, skill_view]
    related_skills: [surgical-investigation, surgical-implementation, surgical-pruning, surgical-hermesdothealth]
---
# Surgical Audit (v2.3 — Principal-10 Polyglot Multi-Pass Architecture)

Execute a deterministic, zero-mutation architectural and code audit equivalent to a 10-Principal-Engineer review board across any programming language, game engine, or application stack. This skill prevents LLM middle-context attention collapse by combining static AST/polyglot telemetry scanning, stack-specific failure matrices, symbolic mental mutation testing, context-compaction batching, and quantitative health scoring into a single read-only Markdown deliverable.

## When to Use

Trigger this skill when the user asks for a code audit, architecture review, pre-refactor risk assessment, or test-suite quality judgement — and especially when the complaint is visual or behavioural ("lines across the screen", "no bright colours", "it stutters") and a static read cannot prove the fix. Also trigger it when the question is about **engagement, excitement, juice, retention, or "what popular practice am I neglecting"** in a game or consumer-facing interactive: the 10 lenses audit correctness and will score such a product well while it is still joyless. Load `references/engagement-and-game-feel-audit.md` for that family. Do not use it for a single bug fix with an obvious cause; it is a full review board and its output is a report, not a patch.

## Auxiliary Skill Resources (Progressive Disclosure)

Before executing Pass 1–3, load the bundled reference files using `skill_view(name="surgical-audit", file_path="<path>")` in Nous Hermes Agent (or `get_skill_resources` in cloud environments):

- `scripts/preflight_telemetry.py`: Zero-mutation polyglot static AST & complexity scanner (Python, TS/JS/React/Svelte, C#/Unity, GDScript/Godot, C/C++, GLSL, Rust, Go, Lua). Computes repository SHA-256 Merkle state digests, effective LOC, Cyclomatic Complexity ($CC$), brace nesting depth, God-file flags (`>400` LOC), silent catch blocks, hot-loop allocation markers, and untested module pairings.
- `references/stack_failure_matrices.md`: Deep domain failure matrices for **Matrix A** (2D/3D Game Engines, WebGL/GLSL, Pygame, Godot, Unity, Canvas), **Matrix B** (Next.js, React, Svelte, Convex, BaaS), and **Matrix C** (Python, C++, CLI, Linux/PRoot, Autonomous Agents).
- `references/test_mutation_rubric.md`: Protocol for Mental Mutation Testing ($M_{\text{kill}}$ estimation), identifying the 6 vibe-coded test pathologies, the regression-test acceptance gate, and designing a Minimal Viable Test Harness (MVTH).
- `references/runtime-probe-harness.md`: Pass 2.5 recipe for auditing what the app actually draws — scoping the preflight scan so it does not time out, pristine-baseline A/B on two ports, Canvas 2D geometry hooks, pixel hue histograms for colour complaints, and the probe traps that cost time.
- `scripts/canvas_geometry_probe.mjs`: Re-runnable Playwright probe that hooks `moveTo`/`lineTo`/`strokeRect` per canvas and reports segment count, longest segment, and horizontal/vertical span counts.
- `references/remediation-delivery.md`: Pass 4.5 delivery recipe — ordering a green commit series (fix before the acceptance test that asserts it), splitting concerns that interleave inside one file, proving each commit green on its own tree, and resolving what is *actually* deployed (a `200` is not proof).
- `references/engagement-and-game-feel-audit.md`: The 11th lens — auditing what the player *feels* rather than what the code does. Authored-but-unwired feature detection, the feedback-channel matrix, difficulty-arc arithmetic, progression persistence, and the coverage-table report shape.
- `scripts/dead_export_sweep.py`: Re-runnable sweep for exported symbols with zero external references, bucketed into dead / test-only / type-only. The mechanical way to find content that type-checks, may have a green suite, and is connected to nothing.

## Hard Operational Invariants (Zero-Mutation Law)

1. **Zero Source Mutation:** Never create, edit, format, or delete any repository source, config, or test file. Do not invoke `write_file`, `patch`, or mutating shell commands on target repository files.
2. **Cryptographic Proof of Non-Mutation:** Capture the repository's pre-audit state hash (`tree_integrity_sha256` from `scripts/preflight_telemetry.py` or `git status --porcelain` + `git rev-parse HEAD`) before Pass 1 and verify identical post-audit state in Pass 5. When the tree is already dirty (prior work in flight) or the fix needs a reproducible before/after, also export a pristine baseline with `git archive HEAD | tar -x -C <scratch>/baseline`, digest it, and serve it on a second port so one identical probe can run against both builds.
3. **Context-Compaction Batching Rule:** Never ingest more than `5` implementation files or `1,200` LOC in a single inspection turn. For repositories exceeding `1,200` LOC, audit in ranked hotspot batches (Batch 1: Top 5 highest-risk files; Batch 2: Next 5; etc.) and record structured intermediate defect notes before synthesizing the final Markdown report.
4. **No Generic Linter Filler:** Every reported defect must include:
   - Exact `file_path:L<start>-L<end>` coordinates.
   - Exact root-cause mechanism (memory model, frame budget math, state race, or AST flow).
   - Concrete runtime failure scenario (the exact input, frame rate, or concurrency timing that triggers the bug).
   - Surgical remediation blueprint and a self-contained copy-paste agent prompt.

---

## Multi-Pass Execution Protocol

### Pass 1: Deterministic Preflight Telemetry & Topology Mapping

Do not inspect files randomly. Establish objective structural metrics first:

1. Run `python3 ~/.hermes/skills/surgical-audit/scripts/preflight_telemetry.py <target_dir>` via `terminal` (or equivalent read-only workspace inspection) to extract:
   - `tree_integrity_sha256` (pre-audit state digest).
   - Top high-risk files ranked by $\text{Risk} = \text{LOC}_{\text{effective}} \times (1 + \text{BranchDensity}) + 50 \times N_{\text{SilentCatches}}$.
   - Exact list of God files (`>400` effective LOC), high-complexity functions ($CC \ge 10$, brace depth $>5$, or $\text{LOC} \ge 60$), and untested implementation modules.
2. Map the **State & Data-Flow Topology**:
   - Identify all entry points, global singletons, game/event loops, external I/O boundaries, and persistence layers.
   - Flag **AI Split-Brain State** (duplicate state representations across modules that must be manually synchronized) and **Orphaned/Hallucinated Code** (dead helpers, duplicate utilities across files, unused exports).
   - Enumerate the orphans mechanically rather than by eye: `python3 <skill>/scripts/dead_export_sweep.py <target_dir> --src <src>`. Confirm each candidate with `grep -rn "<symbol>" tests/ src/ e2e/` before proposing a delete — hand-rolled harnesses re-implement an old contract inline and keep a zero-caller module load-bearing. A symbol referenced **only** by tests is the strongest signal in the sweep: green suite, dead in production.

### Pass 2: Stack Matrix Loading & The 10-Principal-Engineer Deep Audit

Load `references/stack_failure_matrices.md` and audit the ranked hotspot batches systematically across all 10 specialized engineering lenses. Never skip a lens silently; if a lens does not apply, explicitly mark it `N/A — [1-sentence technical justification]`:

1. **Lens 1 — Systems Architect (Topology, Coupling & State Machines):**
   - Circular imports, God objects mixing rendering/physics/I/O, implicit boolean soup (`isLoading && !isPaused && isReady && !isDead` instead of an explicit Finite State Machine transition table), and leaky module boundaries.
2. **Lens 2 — Frame-Budget & Performance Engineer (Hot Loops & Latency):**
   - For games/UI: verify `16.67ms` (60Hz) and `8.33ms` (120Hz) frame budgets. Flag per-frame heap allocations (`new`, `.map()`, `.filter()`, object literals, string formatting) inside `requestAnimationFrame`, `update(dt)`, `_process(delta)`, or `Update()`.
   - Flag $O(N^2)$ entity loops, unindexed database table scans (`.collect()` without bounds), and N+1 network queries.
3. **Lens 3 — Mathematical, Physics & Algorithmic Engineer (Precision & Edge Cases):**
   - Frame-rate dependent exponential damping (`v *= 0.95` without `dt` exponentiation), unclamped `dt` physics tunneling on tab-switch, zero-vector normalization producing `NaN`, floating-point accumulation drift, off-by-one indexing, and GLSL `mediump` float overflow on mobile GPUs.
4. **Lens 4 — Concurrency, Async & Determinism Engineer (Race Conditions):**
   - Time-of-Check to Time-of-Use (TOCTOU) read-modify-write races, stale variable captures in React/Svelte closures or event callbacks, uncancelled `AbortController`/promises on unmount, and blocking synchronous I/O inside async event loops.
5. **Lens 5 — Memory & Resource Lifecycle Engineer (Leaks & Cleanup):**
   - Asymmetric resource lifecycles: `addEventListener` without `removeEventListener`, `setInterval`/`requestAnimationFrame` without cancellation ID cleanup, undisposed WebGL buffers/textures/programs, unclosed WebAudio contexts, or leaked file descriptors/sockets.
6. **Lens 6 — Security & Trust-Boundary Engineer (AppSec & Sandboxing):**
   - Client-authoritative score/payroll/permission mutations, missing server-side auth verification, path-traversal/symlink sandbox escapes (`startswith` instead of `Path.resolve().is_relative_to()`), command injection (`shell=True`), XSS (`innerHTML`/`dangerouslySetInnerHTML`), and hardcoded secrets.
   - **A server-computed verdict that is stored but never consumed downstream** — a geofence/accuracy/anomaly flag that no payout, permission, or audit gate reads — is a P0 trust-boundary finding, not a UX nit. The product records the truth and then pays against it anyway; confirm by tracing the field from writer to the money/enforcement path, not by grepping for its name.
7. **Lens 7 — Reliability, Fault Tolerance & Chaos Engineer (Crash Vectors):**
   - Silent exception swallowing (`except: pass` / empty `catch {}`), non-atomic file writes (writing directly to target file without temp-file + `os.replace`), corrupted `localStorage`/save-state crash loops on `JSON.parse`, and missing network retry/backoff logic.
8. **Lens 8 — Type Systems, Schema & Contract Engineer (Boundary Integrity):**
   - Unvalidated external JSON/API payloads, `any` / `# type: ignore` escapes masking structural mismatches, implicit coercion traps (`0` or `""` treated as falsy when valid), and Python mutable default arguments.
9. **Lens 9 — Platform, Viewport & Portability Engineer (Cross-Device Parity):**
   - Desktop-only mouse/keyboard assumptions breaking mobile touch viewports, missing `devicePixelRatio` canvas scaling, pointer coordinate desync under CSS letterboxing, and hardcoded OS path separators (`\` vs `/`).
10. **Lens 10 — Cognitive Load & AI-Context Maintainability Engineer (DX):**
    - Deeply nested arrow conditionals (`>3` indentation levels), magic numbers without named constants, inconsistent naming semantics, and overly abstract boilerplate that wastes token context in future AI coding sessions.

### Pass 2.5: Live Geometry Probe (mandatory for layout, obstruction, overlap and rendered-artefact audits)

This pass covers two families: **DOM placement** (entities obstructing each other) and **rendered artefacts** (stray lines, washed-out colour, geometry that only exists after a teleport). For the rendered-artefact family, load `references/runtime-probe-harness.md` and use `scripts/canvas_geometry_probe.mjs`; hook the draw calls and count segments instead of comparing screenshots.

Static reading cannot prove overlap. CSS cascade winners, box-model padding + negative margins, and DOM stacking order routinely make a placement engine place entities inside boxes 3–6× larger than its own constants. For any audit about entities obstructing each other, capture runtime evidence before scoring:

1. Serve the app (`npx http-server -p 8000 -c-1 --cors -s &`) and drive it with the repo's Playwright package, imported by absolute path from a scratch script so no repo file is created (`import { chromium } from "<repo>/node_modules/playwright/index.mjs"`).
2. Dismiss every input lock / onboarding gate first, then assert the lock is released (`!document.body.classList.contains('<lock-class>')`) — an active input lock makes every entity report as occluded and pollutes the sample.
3. Measure the **visual** rect with `Range.getBoundingClientRect()` over `element.textContent`, not the element rect: padding + negative margin inflate element rects and overstate overlap.
4. Hit-test 5 points per entity (`elementFromPoint`): centre + 4 inset corners. Count `fully blocked` (0/5 self), `partially blocked`, and tally blocker tags. This is the browser's own tap-routing algorithm — it is the proof that a tap lands on the wrong entity.
5. Measure chrome surfaces (`position: fixed/absolute` HUD, keypads, banners) and compute `entityWindow ∩ chrome / entityWindow` to quantify stolen playfield area.
6. Also measure declared-vs-rendered footprint: `config.symbolWidth/Height` vs `offsetWidth/offsetHeight`. A ratio > 1.5× is a P1 root cause, not a cosmetic issue.
7. Measure **two** rects per entity and report both: the element rect (what `elementFromPoint` uses = the real tap target) and the text `Range` rect (what the player sees). Padding and negative margins separate them, so an entity can be visually clear but untappable, or tappable but unreadable.
8. Never sample `document.querySelector('.entity')` — the first match is often a pooled/hidden node with no state attribute, so its rule set differs: a glyph whose state selector adds `display:flex` falls back to `display:block; width:auto` in the pool and measures the whole container width. Pick a live/visible element, and sanity-check any measurement wider than half the container before trusting it.
9. Opacity `0` does not stop pointer events. Any hidden/pooled entity still intercepts taps unless it also has `pointer-events: none`; count those as blockers in the hit-test tally or you will fix visible overlap and leave invisible theft.
10. When a media-query rule appears to be ignored, print `getComputedStyle` and the matching rules — an ID selector silently outranks `body.viewport-* .class` overrides, which is how "compaction" rules become dead code that nobody notices.

Record the numbers in the report (viewport × visible count × blocked count). A layout audit without live hit-test numbers is a guess.

### Pass 3: Existing Test Suite Comparison & Mental Mutation Analysis

Load `references/test_mutation_rubric.md` and audit every test file against the actual implementation AST:

1. Construct the **Implementation vs. Test Matrix** mapping every critical module/function to its corresponding test file.
- Check existing tests for the **6 Vibe-Coded Test Pathologies**:
   - Mock-Mirror Tautologies (testing the mock return value instead of real logic).
   - Weak/Existence-Only Assertions (`toBeDefined()` theater).
   - Happy-Path Tunnel Vision (zero negative/boundary/NaN/error tests).
   - Shared Mutable State across tests.
   - Implementation-Coupled Brittle Spies.
2b. **Prove the tested module is shipped.** For every unit-tested file, grep the page HTML and the service-worker precache for its path. A module can own a green 270-line unit suite and be loaded by nothing — that is invisible debt masquerading as coverage. Count those tests as zero coverage and recommend delete-or-wire.

3. Run the **4-Mutant Mental Execution Protocol** (`M1: Boundary Flip`, `M2: Zero/Empty Degeneracy`, `M3: Side-Effect Deletion`, `M4: Async Failure Injection`) on core tested functions to compute the **Estimated Mutation Kill Score ($M_{\text{kill}}\%$)**.
4. For every P0/P1 bug discovered in Pass 2, explicitly answer: *"Why did the existing test suite miss this defect?"*
5. Design a **Minimal Viable Test Harness (MVTH)** with concrete table-driven test cases for unprotected high-risk modules.

### Pass 4: Quantitative Scoring & Surgical Refactoring Architecture

Compute the **Deterministic Health Score ($S_{\text{health}} \in [0, 100]$)** and **Vibe-Debt Risk Classification** using explicit formulas:

$$D_{\text{raw}} = (18 \times N_{\text{P0}}) + (8 \times N_{\text{P1}}) + (3 \times N_{\text{P2}}) + (1 \times N_{\text{P3}})$$

$$P_{\text{test}} = 15 \times \left(1 - \frac{M_{\text{kill}}}{100}\right)$$

$$S_{\text{health}} = \max\left(0, \text{round}\left(100 - D_{\text{raw}} \times \sqrt{\frac{1000}{\max(500, \text{LOC}_{\text{effective}})}} - P_{\text{test}}\right)\right)$$

- **Vibe-Debt Risk Classification:**
  - `Low` ($S_{\text{health}} \ge 85$ and $N_{\text{P0}} = 0$)
  - `Moderate` ($65 \le S_{\text{health}} < 85$ and $N_{\text{P0}} = 0$)
  - `High` ($40 \le S_{\text{health}} < 65$ or $N_{\text{P0}} = 1$)
  - `Critical` ($S_{\text{health}} < 40$ or $N_{\text{P0}} \ge 2$)

For each major structural flaw, design a **Surgical Refactoring Blueprint**:
- Show exact **Before (Flawed Pattern)** vs. **After (Target Pattern)** code blocks inside the Markdown report.
- Respect the **Anti-Over-Abstraction Rule**: favor compact, deterministic patterns (explicit finite-state tables, pure math helpers, fixed-size object pools, schema validators) that minimize token footprint for future AI coding agents.

### Pass 4.5: Remediation Hand-off (only when the user says proceed)

The zero-mutation law governs the audit pass. When the user asks you to fix the findings, the audit becomes an implementation job with its own gate:

1. **Prove the regression test can fail.** Write the new assertion against the *pre-fix* failure mode ("min visible > 0", "max visible ≤ capacity"), not a proxy ("panel is visible"). If the defect is periodic, the sample window must span at least two full cycles — a 6 s sample cannot catch an 8 s cycle. Mood-check: revert the fix in your head; if the test would still pass, it is decoration. When a full cycle is too slow to sample repeatedly inside the test timeout, **compress the cycle instead of widening the timeout**: mutate the runtime config in-page (`visibleMs 400 / fadeMs 100 / hidden 250–500`), wait one old cycle for pre-scheduled timers to drain, then sample at a fraction of the cycle length — that converts a 30 s test into 12–16 observed cycles.
2. **Extract the geometry/state maths into a pure module** before writing unit tests. A 1,300-line IIFE controller hides placement maths behind a full runtime boot, which is why the invariant was never stated. Pure functions over measured rects turn "looks fine" into executable proofs (cells ≥ box; two different slots can never intersect).
3. **Never null a cached layout/grid before rebuilding it.** Swap atomically (build → swap, restore the previous value on failure). Timers fire between epochs and will find nothing to measure, silently starving the system.
4. **Re-run the whole focused suite immediately.** Failures discovered here are usually in the new code, not the old — but read the test helper's defaults before touching the rule: a fixture that synthesises an artificial offset for the very field your rule keys on (`_creationTime = clientTime + 500min`, `serverOffsetMin`) fails every case for the wrong reason. Fix the fixture, not the rule, and only after confirming the helper is not modelling a real contract. Find who mutates a suspicious field by installing a property setter that records `new Error().stack` at the write; find failing pure-function inputs by wrapping the module function *after* it exists (poll, then wrap — wrapping at definition time gets clobbered by the module's own assignment).
5. **Before editing an existing assertion to match the code, run `git log -S "<value>" -- <path>`.** If a product commit deliberately changed the behaviour, fix the stale test; if not, you are about to paper over a regression.
6. **Grep the test tree for the symbol before deleting an "unused" export.** Hand-rolled harnesses re-implement the old contract inline (`window.Helpers.populateInitialSymbols(...)`), so a module with zero production callers can still be load-bearing for a shard you did not run. `grep -rn "<symbol>" tests/ src/tools/` first, then replace the harness with an inline equivalent of the same contract before removing the module.

7. **Land the fix as a green commit series — the fix before the assertion that depends on it.** One concern per commit, and confirm every commit is green on its own tree. A commit whose own suite fails poisons `git bisect` and every reviewer or CI job that checks out that SHA. When a new assertion lives in a test file that also gates behaviour landing in a later commit, order the fix first (or land both together) — never stage the acceptance test ahead of the mechanism it asserts. `references/remediation-delivery.md` carries the recipe for splitting concerns that interleave inside a single file.
8. **Verify the deployed artefact, not the push — and never accept a `200` as proof.** A successful `git push` proves the branch moved; it does not mean CI ran, and it does not mean the host built. Every host keeps serving the previous successful deployment, so the origin answers `200` whether or not your push ever compiled. Resolve, in this order: (a) **does the automation run at all** — `gh api repos/O/R/actions/permissions` (`enabled:false` means the workflow file is decorative and has never gated anything), `gh run list --workflow=<file>`; a run ending in `startup_failure` at **0s** never started — no runner was allocated (billing/account lock) — so that is "CI never ran", not "CI failed", and every green result in the session is local-only; (b) **what does the platform say is live** — project `live` flag and `latestDeployment.readyState` / `createdAt`, or — with no platform-CLI auth — the host's own Deployment records (`gh api repos/O/R/deployments`, then `/deployments/<id>/statuses`; see `references/remediation-delivery.md` §3c); (c) **hash equality** — the hashed entry-bundle filename served by the site versus the one your own build produced; a different hash is a stale deployment, full stop; (d) only then grep the served bundle for a symbol the fix removed (expect `0`) and one it added (expect `> 0`) — string literals and CSS class names survive minification, renamed local identifiers do not. If the host build failed while your local build passed, reproduce the host runtime from `git archive` before touching code (`references/remediation-delivery.md` §3b). Report hashes and counts, or report the exact gate that blocked delivery — never the word "deployed".

9. **Remediate inside the repo's change budget.** Before designing the fix, establish what regenerating checked-in types requires. Convex's `npx convex codegen` refuses with "No CONVEX_DEPLOYMENT set", so an audited fork with no live deployment cannot absorb a new schema field or index — the tree simply stops typechecking and the fix cannot land. Express the change from fields already stored instead: derive the flag at read time from existing columns (`_creationTime` vs the client timestamp), filter inside the query handler rather than adding an index, and leave the migration to a session that can push. The same rule covers Prisma/Drizzle migrations, protobuf codegen, and any generated client that needs credentials to re-emit.

10. **Turn an ignored verdict into a review gate, not a rejected write.** When the defect is "the server computed the truth and the money path ignored it", do not fix it by rejecting the write: rejection erases the evidence the product needs for disputes and breaks legitimate edge cases (indoor GPS, site-radius drift). Insert the verdict into the state machine that already gates payment — set `needsReview` with a named reason so the shift is excluded until a human resolves it. The record survives, the money is held, and the rule is testable as a pure-function assertion.

Record before/after numbers with the same probe and paste the exact commands you ran. A fix without a failing-first test and a re-measured probe is a claim, not a result.

### Pass 5: Report Generation & Zero-Mutation Verification

1. Re-verify `tree_integrity_sha256` (or `git status --porcelain`) to confirm zero tracked files were modified.
2. Output the complete audit using the **Mandatory Markdown Report Template** below.
3. Write the report into the repository at `docs/audits/<project>-surgical-audit-<YYYY-MM-DD>.md` and commit it as its own docs commit, separate from the fix series — evidence and code must be reviewable and revertable independently.

---

## Mandatory Markdown Report Template

# Surgical Audit Report: [Project / Repository Name]

| Audit Metadata | Specification |
| :--- | :--- |
| **Audit Date** | YYYY-MM-DD |
| **Audited Scope** | `[Directories / Files]` (`[N]` impl files, `[M]` test files, `[LOC]` effective LOC) |
| **Tech Stack & Runtime** | `[Languages, Engine, Framework, Target Platforms]` |
| **Pre/Post Audit SHA-256** | `[16-char hash] / [16-char hash] (VERIFIED ZERO MUTATION)` |
| **Deterministic Health Score** | **`[S_health] / 100`** (`D_raw = [X]`, `P_test = [Y]`, `M_kill = [Z]%`) |
| **Vibe-Debt Risk Level** | **`[LOW | MODERATE | HIGH | CRITICAL]`** |

## 1. Executive Architecture & Vibe-Debt Triage

[Concise 4-6 sentence architectural synthesis: identify the primary failure mode, hot-loop or state-sync bottlenecks, trust-boundary posture, and test reliability.]

| Severity Tier | Count | Deduction Weight | Primary Failure Domains |
| :--- | :--- | :--- | :--- |
| **P0 — Critical (Crash / Data Loss / Security / Leak)** | `[N]` | `-18 pts ea` | `[Exact files & mechanisms]` |
| **P1 — High (Frame-Budget / Race / Logic Bug)** | `[N]` | `-8 pts ea` | `[Exact files & mechanisms]` |
| **P2 — Medium (God File / Split-Brain State / Debt)** | `[N]` | `-3 pts ea` | `[Exact files & mechanisms]` |
| **P3 — Low (Magic Constants / DX / Portability)** | `[N]` | `-1 pt ea` | `[Exact files & mechanisms]` |

### High-Risk File Telemetry Hotspots
| File Path | Effective LOC | Est. Cyclomatic Complexity / Branch Density | Silent Catches | Primary Vibe-Debt Signature |
| :--- | :--- | :--- | :--- | :--- |
| `path/to/file.ext` | `[LOC]` | `[CC / Density]` | `[N]` | `[e.g., God loop + per-frame GC churn]` |

## 2. The 10-Principal-Engineer Deep Audit

### Lens [1-10]: [Lens Name]
- **[[P0/P1/P2/P3]-[ID]] [Concise Defect Title]** — `path/to/file.ext:L<start>-L<end>`
  - **Root Cause Mechanism:** [Exact technical reason in AST/runtime/memory/math]
  - **Deterministic Trigger & Failure Mode:** [Exact input, timing, or frame rate that triggers failure]
  - **Surgical Fix Specification:** [Exact code/logic transformation required]

## 3. Existing Test Suite Comparison & Mutation Truth Table

- **Test-to-Code File Ratio:** `[M / N]` (`[Ratio]`)
- **Estimated Mutation Kill Score ($M_{\text{kill}}$):** **`[Z]%`**

| Implementation Module | Critical Functions / Branches | Paired Test File | Pathologies Detected | Mental Mutants Killed (`M1-M4`) | High-Priority Missing Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `path/to/file.ext` | `funcA()`, `update(dt)` | `file.test.ext` (or `NONE`) | `[e.g., Mock-Mirror, Happy-Path Only]` | `[e.g., 1/4 (25%)]` | `[Boundary, NaN, error rollback]` |

### Why Existing Tests Missed Discovered P0/P1 Defects
- **[Defect ID]:** [Exact explanation of the mock gap, missing boundary input, or unasserted side effect.]

### Minimal Viable Test Harness (MVTH) Specifications
1. **`[Test Target 1]`:** Table-driven test inputs `[...]` asserting invariant `[...]`.
2. **`[Test Target 2]`:** Lifecycle/concurrency test asserting `[...]`.

## 4. Surgical Refactoring Blueprints (Zero-Mutation Drafts)

### Refactor [R1]: [Title — e.g., Replace Boolean Soup with Explicit FSM Table / Object Pool]
- **Target Scope:** `path/to/file.ext:L<start>-L<end>`
- **Engineering ROI:** [Quantified benefit: e.g., eliminates ~240 heap allocations/sec at 60 FPS; reduces CC from 18 to 4]

**Current Pattern (Audited Code):**
```[lang]
// Exact problematic pattern from target file

```

**Target Pattern (Surgical Blueprint):**

```[lang]
// Drop-in replacement architecture

```

## 5. Phased Execution Roadmap & Scoped Agent Prompts

1. **Phase 1 — Containment & Safety Lock (`P0` Fixes + MVTH Baseline Tests)**
2. **Phase 2 — Frame-Budget, Concurrency & State Hardening (`P1` Fixes)**
3. **Phase 3 — Structural De-Vibing & Modular Extraction (`P2/P3` Refactors)**

### Copy-Paste Surgical Prompts for Coding Agents

> **Prompt [P0-1] (`path/to/file.ext`):**
> "Strictly scope edits to `path/to/file.ext` (lines X–Y) and `path/to/file.test.ext`. Do not modify any other files. Replace [flawed mechanism] with [target mechanism] so that [invariant holds]. Add a regression test verifying [boundary/failure condition] and run the test suite to confirm green."

## Pitfalls

- **Scope the scanner before you run it.** `preflight_telemetry.py` prunes `.git` only. On a JS repo with `node_modules` it will hash tens of thousands of vendored files and look hung. Copy it to a scratch dir, extend the prune set (`node_modules`, `dist`, `.next`, `__pycache__`, `.venv`), and use the **same** patched copy pre- and post-audit so the digests stay comparable.
- **`\b` cannot match `:`, `?`, `&&`, `||`.** The branch regex wraps non-word tokens in word boundaries, so ternary and short-circuit branches are invisible in the CC estimate. Treat the reported complexity as a floor, not a measurement.
- **A health score is not a verdict on the whole repo.** The formula saturates: with no test suite you lose the full 15-point `P_test` regardless of how good the code is, and a docs-only skill with one P1 lands in HIGH. Report the per-defect evidence and let the score rank, not decide.
- **Build-artefact tests fail before a build, and that is ordering, not a regression.** Tests asserting `public/sw.js`, `dist/*`, or a generated bundle exist will fail on a fresh clone; run the repo's build before scoring them, and never report a pre-build failure as a defect the audit found.
- **Zero-mutation means zero debris.** `python3 -m py_compile` writes `__pycache__/` into the target. Run probes in a scratch copy, or delete the caches before you re-verify the digest.
- **A clean `conform.py` does not mean a good skill.** It checks frontmatter shape and reference existence — not whether the procedure is correct, whether the scripts run, or whether the tests would fail if the code were wrong.
