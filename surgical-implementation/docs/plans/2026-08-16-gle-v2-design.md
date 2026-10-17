# G&L Auditor V2 → surgical-implementation Integration Design

Date: 2026-08-16
Author: Hermes (augmenting the existing surgical-implementation skill)
Deliverable (approved): Complete/augment the existing `surgical-implementation`
skill so it fully realizes the G&L Software Engineering Auditor V2 spec; ship as
fixes to this repo's `SKILL.md` + `references/`.

## Problem

`surgical-implementation` (SKILL.md) claims to "wrap the G&L Auditor V2 governance
model" but is a thin conductor: it delegates to `surgical-orchestration` and
`code-review` and *names* the V2 states (DISCOVER→…→COMPLETE) without realizing
them. The V2 `SKILL.md` contract (`GLE_Software_Engineering_Auditor_V2_ULTIMATE/SKILL.md`)
requires a concrete governance layer the current skill does not provide.

### Evidence-based gap list (read, not assumed)

| # | V2 requirement | Current skill state |
|---|---|---|
| G1 | Required artifact set (REQUIREMENTS, CODEBASE-STATE, ARCHITECTURE, TODO≥10, debrief, TRACEABILITY, SECURITY, RISK, research SOURCES/FINDINGS/DECISIONS, runtime manifest/state/events) | Only loose "Evidence artifacts" mentions; no templates; no runtime JSON |
| G2 | Bounded-retry ledger + explicit ≤5 consistency stop (STOP_AND_REQUEST_USER) | "bounded retries" mentioned; no ledger; ≤5 not enforced as a run step |
| G3 | 13-class failure taxonomy recorded per failure | Verifier "failure classes" only; no canonical taxonomy mapping |
| G4 | Per-role capability matrix (10 agents: Read/Write/Exec/Web/Prod) | Absent; roles not realized as dispatchable envelopes |
| G5 | Approval gates AUTO/REVIEW/APPROVAL_REQUIRED/BLOCKED enforced per phase | Short gates section; not mapped to states; BLOCKED not refused |
| G6 | Research freshness ≤14 days for current practices | Not present |
| G7 | Final-status enum: READY / READY WITH WARNINGS / NOT READY / BLOCKED | Not present |
| G8 | Structured 17-section debrief | Loose DEBRIEF.md mention only |

## Approach (recommended)

Augment `SKILL.md` into an executable Hermes conductor that embeds the V2 state
machine with per-state actions, gates, and produced artifacts. Add three
reference files carrying the missing governance: artifact templates, agent
envelopes (capability matrix), and governance rules. Keep the user's
plan-scan dispatcher contract (references/plan-scan-dispatcher.md) intact and
extend its `N==0` branch to author a fresh plan from the templates.

No new external dependencies. The 10 V2 agent roles are realized as
`delegate_task` mission envelopes (the host already provides subagents).

### Alternatives considered

- Build a separate TS runtime realizing the V2 schemas → rejected (scope creep;
  user chose augment; repo is a skill, not a code lib).
- Leave conductor thin → rejected (gaps above violate the V2 contract it claims).

## Design sections

1. **State machine (13 states)** with per-state: entry/exit condition, action,
   artifact produced, approval gate. DISCOVER→REQUIREMENTS→RESEARCH→CODEBASE_STATE
   →ARCHITECT→PLAN→CONSISTENCY_GATE(≤5)→IMPLEMENT→VERIFY→SECURITY_AUDIT
   →FINAL_AUDIT→DEBRIEF→HANDOFF→COMPLETE.
2. **Governance layer**: approval gates, bounded-retry ledger
   (`audit/logs/retry-<state>.jsonl`), failure taxonomy mapping, research
   freshness ≤14d, capability matrix per role.
3. **Artifact set**: copy-ready templates; written to the *target* repo's
   `docs/.scratch-audit/` (or `docs/plans/`) during a run — never into this skill.
4. **Agent roles**: 10 V2 roles → `delegate_task` envelopes with capability
   matrix; Investigator/Researcher/Architect/Planner/Reviewer/Implementer/
   Verifier/Security Auditor/Final Auditor/Debriefer.
5. **Runtime state**: `manifest.json` / `state.json` / `events.jsonl` schemas.
6. **Final statuses** enum + 17-section debrief format.
7. **Plan-scan dispatcher preserved** as entry contract; `N==0` uses templates.

## Approval-gate mapping (per state)

- DISCOVER/REQUIREMENTS/RESEARCH/CODEBASE_STATE/ARCHITECT/PLAN/CONSISTENCY_GATE/
  DEBRIEF/HANDOFF → AUTO (read, search, plan artifacts, static analysis).
- IMPLEMENT (broad refactor / security-sensitive / risky dep upgrade) → REVIEW.
- IMPLEMENT (destructive/prod/credential/permission/irreversible) →
  APPROVAL_REQUIRED.
- Any host-policy-prohibited op → BLOCKED (refuse, record, request user).

## Out of scope

- Editing the `GLE_Software_Engineering_Auditor_V2_ULTIMATE/` package (it is the
  spec, left read-only).
- Pushing/committing to the remote (user authorizes separately).
- Building a TS engine (covered by `surgical-orchestration` already).

## Verification (how we know it's done)

- `skill_view(name='surgical-implementation')` returns the augmented content.
- Every V2 `tests/skill-tests/acceptance.md` item (17) is addressed in
  SKILL.md or the new references.
- All referenced `references/*.md` files exist (no dangling links).
- Plan-scan dispatcher still loads and its N==0 branch references the templates.
