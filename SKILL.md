---
name: surgical-audit
description: "Read-only 10-principal-engineer code, test, and refactor audit in MD."
version: 2.1.0
author: "TeacherEvan, Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [code-review, surgical-audit, static-analysis, testing, refactoring, read-only]
    requires_tools: [read_file, search_files, terminal, skill_view]
---
# Surgical Audit (v2.1 — Principal-10 Polyglot Multi-Pass Architecture)

Execute a deterministic, zero-mutation architectural and code audit equivalent to a 10-Principal-Engineer review board across any programming language, game engine, or application stack. This skill prevents LLM middle-context attention collapse by combining static AST/polyglot telemetry scanning, stack-specific failure matrices, symbolic mental mutation testing, context-compaction batching, and quantitative health scoring into a single read-only Markdown deliverable.

## Auxiliary Skill Resources (Progressive Disclosure)

Before executing Pass 1–3, load the bundled reference files using `skill_view(name="surgical-audit", file_path="<path>")` in Nous Hermes Agent (or `get_skill_resources` in cloud environments):

- `scripts/preflight_telemetry.py`: Zero-mutation polyglot static AST & complexity scanner (Python, TS/JS/React/Svelte, C#/Unity, GDScript/Godot, C/C++, GLSL, Rust, Go, Lua). Computes repository SHA-256 Merkle state digests, effective LOC, Cyclomatic Complexity ($CC$), brace nesting depth, God-file flags (`>400` LOC), silent catch blocks, hot-loop allocation markers, and untested module pairings.
- `references/stack_failure_matrices.md`: Deep domain failure matrices for **Matrix A** (2D/3D Game Engines, WebGL/GLSL, Pygame, Godot, Unity, Canvas), **Matrix B** (Next.js, React, Svelte, Convex, BaaS), and **Matrix C** (Python, C++, CLI, Linux/PRoot, Autonomous Agents).
- `references/test_mutation_rubric.md`: Protocol for Mental Mutation Testing ($M_{\text{kill}}$ estimation), identifying the 5 vibe-coded test pathologies, and designing a Minimal Viable Test Harness (MVTH).

## Hard Operational Invariants (Zero-Mutation Law)

1. **Zero Source Mutation:** Never create, edit, format, or delete any repository source, config, or test file. Do not invoke `write_file`, `patch`, or mutating shell commands on target repository files.
2. **Cryptographic Proof of Non-Mutation:** Capture the repository's pre-audit state hash (`tree_integrity_sha256` from `scripts/preflight_telemetry.py` or `git status --porcelain` + `git rev-parse HEAD`) before Pass 1 and verify identical post-audit state in Pass 5.
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
7. **Lens 7 — Reliability, Fault Tolerance & Chaos Engineer (Crash Vectors):**
   - Silent exception swallowing (`except: pass` / empty `catch {}`), non-atomic file writes (writing directly to target file without temp-file + `os.replace`), corrupted `localStorage`/save-state crash loops on `JSON.parse`, and missing network retry/backoff logic.
8. **Lens 8 — Type Systems, Schema & Contract Engineer (Boundary Integrity):**
   - Unvalidated external JSON/API payloads, `any` / `# type: ignore` escapes masking structural mismatches, implicit coercion traps (`0` or `""` treated as falsy when valid), and Python mutable default arguments.
9. **Lens 9 — Platform, Viewport & Portability Engineer (Cross-Device Parity):**
   - Desktop-only mouse/keyboard assumptions breaking mobile touch viewports, missing `devicePixelRatio` canvas scaling, pointer coordinate desync under CSS letterboxing, and hardcoded OS path separators (`\` vs `/`).
10. **Lens 10 — Cognitive Load & AI-Context Maintainability Engineer (DX):**
    - Deeply nested arrow conditionals (`>3` indentation levels), magic numbers without named constants, inconsistent naming semantics, and overly abstract boilerplate that wastes token context in future AI coding sessions.

### Pass 3: Existing Test Suite Comparison & Mental Mutation Analysis

Load `references/test_mutation_rubric.md` and audit every test file against the actual implementation AST:

1. Construct the **Implementation vs. Test Matrix** mapping every critical module/function to its corresponding test file.
2. Check existing tests for the **5 Vibe-Coded Test Pathologies**:
   - Mock-Mirror Tautologies (testing the mock return value instead of real logic).
   - Weak/Existence-Only Assertions (`toBeDefined()` theater).
   - Happy-Path Tunnel Vision (zero negative/boundary/NaN/error tests).
   - Shared Mutable State across tests.
   - Implementation-Coupled Brittle Spies.
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

### Pass 5: Report Generation & Zero-Mutation Verification

1. Re-verify `tree_integrity_sha256` (or `git status --porcelain`) to confirm zero tracked files were modified.
2. Output the complete audit using the **Mandatory Markdown Report Template** below.

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
