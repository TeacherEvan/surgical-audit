# G&L Auditor V2 Integration — Implementation Plan

Date: 2026-08-16
Follows design: docs/plans/2026-08-16-gle-v2-design.md

This plan is the execution prompt for `surgical-implementation` (which wraps
`surgical-orchestration` Worker+Verifier loop + `document-to-action-items`).
Each job is a directory/file scope with a real gate (exit code 0 = pass).

```agentplan
@BAN .env *.pem ~/.hermes/profiles/** GLE_Software_Engineering_Auditor_V2_ULTIMATE/** node_modules/**

@JOB J1 scope=/home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation/SKILL.md
  goal: Rewrite SKILL.md to embed the full 13-state V2 machine + governance (approval gates, bounded-retry ledger, failure taxonomy, research freshness, capability matrix, final-status enum) + wire the 10 agent roles + preserve the plan-scan dispatcher contract.
  needs: (none)
  gate: cd /home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation && rg -q 'CONSISTENCY_GATE|SECURITY_AUDIT|FINAL_AUDIT|HANDOFF|COMPLETE' SKILL.md && rg -q 'Investigator|Researcher|Architect|Planner|Reviewer|Implementer|Verifier|Security Auditor|Final Auditor|Debriefer' SKILL.md && rg -q 'READY WITH WARNINGS|NOT READY|BLOCKED' SKILL.md && test -f references/v2-artifact-templates.md && test -f references/v2-agent-envelopes.md && test -f references/v2-governance.md && echo GATE_OK

@JOB J2 scope=/home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation/references/v2-artifact-templates.md
  goal: New file with copy-ready templates for all V2 required artifacts: REQUIREMENTS, CODEBASE-STATE, ARCHITECTURE, TODO(>=10 objectives), debrief(17 sections), TRACEABILITY, SECURITY, RISK, research SOURCES/FINDINGS/DECISIONS, runtime manifest/state/events.
  needs: J1
  gate: test -f references/v2-artifact-templates.md && rg -c '^#' references/v2-artifact-templates.md | grep -q '^1[0-9]$' || rg -q 'REQUIREMENTS|CODEBASE-STATE|ARCHITECTURE|TRACEABILITY|SECURITY|RISK|SOURCES|FINDINGS|DECISIONS|manifest.json|state.json|events.jsonl' references/v2-artifact-templates.md

@JOB J3 scope=/home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation/references/v2-agent-envelopes.md
  goal: New file mapping the 10 V2 agent roles to delegate_task mission envelopes, each annotated with the capability matrix (Read/Write/Exec/Web/Prod), scope rules, and a JSON exit schema.
  needs: J1
  gate: test -f references/v2-agent-envelopes.md && rg -q 'Investigator|Researcher|Architect|Planner|Reviewer|Implementer|Verifier|Security Auditor|Final Auditor|Debriefer' references/v2-agent-envelopes.md

@JOB J4 scope=/home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation/references/v2-governance.md
  goal: New file documenting approval gates (AUTO/REVIEW/APPROVAL_REQUIRED/BLOCKED) with per-state mapping, bounded-retry ledger format + <=5 consistency STOP_AND_REQUEST_USER, the 13-class failure taxonomy, research freshness <=14d rule, and the final-status enum.
  needs: J1
  gate: test -f references/v2-governance.md && rg -q 'APPROVAL_REQUIRED|BLOCKED|STOP_AND_REQUEST_USER|Failure Taxonomy|14 days|READY WITH WARNINGS' references/v2-governance.md

@JOB J5 scope=/home/ewaldt/Documents/VS/Other/SKILLS/LittleDevil-Skills/Surgical-Implementation/references/plan-scan-dispatcher.md
  goal: Update the dispatcher so its N==0 branch authors a fresh plan using v2-artifact-templates and runs CONSISTENCY_GATE (<=5 cycles); link the three new reference files. Preserve the user's verbatim dispatch rule.
  needs: J2,J3,J4
  gate: test -f references/plan-scan-dispatcher.md && rg -q 'v2-artifact-templates|CONSISTENCY_GATE|<=5|STOP_AND_REQUEST_USER' references/plan-scan-dispatcher.md

@SEQ J1 -> J2,J3,J4
@SEQ J2,J3,J4 -> J5

@EXIT all JOB=[X] && skill_view(name='surgical-implementation') loads && rg -q 'CONSISTENCY_GATE' SKILL.md
```

## Final gate (run after all jobs VERIFIED)

1. `skill_view(name='surgical-implementation')` returns augmented content.
2. Each V2 acceptance item (`GLE_Software_Engineering_Auditor_V2_ULTIMATE/tests/skill-tests/acceptance.md`, 17 items) is addressed in SKILL.md or references.
3. All referenced `references/*.md` exist (no dangling links).
4. Report each job's gate exit code.

## Notes

- J2/J3/J4 are independent files → dispatched concurrently (max 2 per
  surgical-orchestration; the third waits for a free slot).
- J5 must wait for J2–J4 (it links them).
- No code (TS/JS) is produced; gates are `rg`/`test` assertions with real exit
  codes. Subagents edit Markdown only, scoped to their single file.
- Do NOT edit the V2 package (BANNED scope); do NOT push/commit unless asked.
