# Surgical Audit Report: [Project / Repository Name]

| Audit Metadata | Specification |
| :--- | :--- |
| **Audit Date** | YYYY-MM-DD |
| **Audited Scope** | `[Directories / Files]` (`[N]` impl files, `[M]` test files, `[LOC]` effective LOC, `[HTML_LOC]` inline HTML lines if applicable) |
| **Tech Stack & Runtime** | `[Languages, Engine, Framework, Target Platforms]` |
| **Pre/Post Audit SHA-256** | `[16-char hash] / [16-char hash] (VERIFIED ZERO MUTATION)` |
| **Deterministic Health Score** | **`[S_health] / 100`** (`D_raw = [X]`, `P_test = [Y]`, `M_kill = [Z]%`) |
| **Vibe-Debt Risk Level** | **`[LOW / MODERATE / HIGH / CRITICAL]`** |

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
- **Estimated Mutation Kill Score ($M_{\text{kill}}$):** **`[Z]%`** (`[assertions]` assertions, `[neg_count]` negative/boundary signals, `[mock_count]` mocked files, `[unpaired]` unpaired critical modules)

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
