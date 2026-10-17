# Plan-Scan Dispatcher — the user's single edit rule

This is the entry contract for `surgical-implementation`. It is the ONLY dispatch
logic; everything else in the skill is the pipeline it triggers.

## Rule (verbatim from user)

> `if >0 prompt = search:plan(docs/parent_folder) & verify-implementation &&
>  use(as_prompt) to implement workflow. If all plans complete, then implement
>  code-review, handle review as prompt for skill orchestration.`

## Step-by-step

### 1. search:plan(docs/parent_folder)
Resolve the repo root (cwd may be a parent like `GAMES/` — use the cwd-vs-project
guard from code-review: find `.git` / `package.json` within 3 levels). Then scan:

```bash
# plan docs (markdown) — ASCII-safe tokens ONLY; unicode checkmarks in a
# one-shot pattern break the regex and silently yield 0 matches
rg -l --glob 'docs/**/*.md' -i 'todo|objective|tick|\[x\]|\[ \]|WIP|plan' .
# second pass for checked boxes (unicode, separate pattern)
rg -l --glob 'docs/**/*.md' '(✅|☑)' .
# agentplan / blueprint JSON
find docs -maxdepth 3 \( -name '*.agentplan' -o -name 'blueprint*.json' \) 2>/dev/null
```

Count `N = number of plan files found`.

### 2. if N > 0  →  verify-implementation & use(as_prompt)
- **verify-implementation**: for each plan objective, reconcile against the live
  tree. Apply the `verification-before-completion` discipline: a zero-match grep
  is NOT proof of absence; check `git log -- <path>`, read the actual code path,
  confirm the objective's acceptance evidence exists (test passes / behavior
  present).
- **use(as_prompt)**: the plan's OPEN objectives become the execution prompt.
  Do not author a new prompt. The plan IS the prompt fed to surgical-orchestration
  (Worker+Verifier loop). Preserve objective wording, IDs, and acceptance criteria.

### 3. if ALL plans complete  →  code-review → orchestration
"All plans complete" = every objective ticked `[x]`/done OR no open objectives
remain after verify-implementation.

- Run `code-review` (fast-path for staged diffs, full 4-phase for broad scope).
- **handle review as prompt for skill orchestration**: take the review findings
  (`review_findings.md` or fast-path verdict) and feed them BACK into
  `surgical-orchestration` as new JobCard entries — one per affected folder,
  scoped to the finding. The review is not a terminal report; it is the next
  batch of implementation work.
- Re-run VERIFY on the remediation, then FINAL_AUDIT. Only COMPLETE when evidence
  backs every acceptance criterion.

## Edge cases
- **N == 0 (no plan)**: author a fresh plan from the user's request using the
  copy-ready templates in `references/v2-artifact-templates.md`
  (`REQUIREMENTS.md`, `CODEBASE-STATE.md`, `ARCHITECTURE.md`, `TODO.md` with
  ≥10 meaningful objectives). Then run `CONSISTENCY_GATE` — reviewer PASS on
  `REQUIREMENTS ↔ CODEBASE-STATE ↔ ARCHITECTURE ↔ TODO` agreement — **before**
  `IMPLEMENT`; ≤5 replan cycles, then `STOP_AND_REQUEST_USER`. Governance rules
  (approval gates, bounded-retry ledger, failure taxonomy, research freshness,
  final-status enum): `references/v2-governance.md`. Role envelopes and the
  capability matrix: `references/v2-agent-envelopes.md`.
- **Plan already implemented (gates green, tree matches)**: do NOT spawn workers.
  Use `verify-then-sync` mode: verify gates, reconcile drift, commit scoped source,
  push, confirm `0 0`. This is the 2026-08-10 surgical-orchestration scar.
- **Plan contradicts live code**: do not silently "fix" the code to match the plan.
  Flag the divergence in CONSISTENCY_GATE; replan (≤5 cycles) or
  STOP_AND_REQUEST_USER.

## Why this is an upgrade
It composes three existing skills into one auditable loop and removes the dead-end
review: code-review findings automatically become orchestration jobs, closing the
remediation loop without human re-paste. The plan scan makes the skill
self-directing from repo state.

## References
- `references/v2-artifact-templates.md` — copy-ready templates for every V2
  artifact (REQUIREMENTS, CODEBASE-STATE, ARCHITECTURE, TODO≥10, 17-section
  debrief, TRACEABILITY, SECURITY, RISK, research ledger, runtime JSON).
- `references/v2-governance.md` — approval gates, per-state gate map,
  bounded-retry ledger, 11-class failure taxonomy, research freshness, final-status
  enum.
- `references/v2-agent-envelopes.md` — the 10 V2 agent roles as dispatchable
  mission envelopes with the capability matrix.
- `references/git-recovery-and-scan.md` — exact scan + git-recovery commands for
  the verify-implementation step.
