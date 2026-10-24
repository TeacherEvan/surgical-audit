# Remediation Delivery — landing a verified fix as a green commit series

Use at the end of **Pass 4.5**, once the fixes pass their probes and the user asks to ship or merge. The audit produced evidence; this file turns it into history that survives review, bisect, and deployment.

---

## 1. Order the series so every tree is green

- **Fix before the assertion that depends on it.** If a new test asserts behaviour that lands in a different commit, the earlier commit is red. That breaks `git bisect`, and any reviewer or CI job that checks out that SHA sees a failure with no context. Order the mechanism first, or land both in one commit.
- **One concern per commit.** Conventional-commit scopes make the history legible; a mixed commit cannot be reverted selectively when one half turns out to be wrong.
- **Run the repository's documented gate order verbatim** on the final tree — whatever its `AGENTS.md`/CI defines, in that order. Do not substitute a shorter personal gate, and do not skip the typecheck/e2e step because "only JS changed".
- **Never rewrite pushed history** to split a commit after the fact. Split before push, or accept one atomic commit and say so in the report.

---

## 2. Split concerns that interleave inside one file

Two concerns often share a file (a rendering fix and a data-contract change in the same class). Hunk staging is fragile; reconstruct the intermediate state instead:

1. Back up the final file to scratch (`cp <file> <scratch>/<file>.final`).
2. In the working file, revert **concern B**'s hunks and keep concern A. Script the replacements with assertions (`assert old in s`) so a missed match fails loudly instead of silently shipping a half-reverted file.
3. Restore any test file that asserts concern B from `HEAD` (`git checkout HEAD -- <test>`), so the intermediate tree is coherent rather than half-migrated.
4. Run the focused tests plus lint at that state. **If red, stop** — the concerns are not separable, and one atomic commit is the correct answer.
5. `git add` only the concern-A files and commit.
6. Restore the final file and the concern-B test from scratch, run tests plus lint again, then commit.
7. Confirm `git status --short` is empty and `git log --oneline` reads as one concern per line.

A broken split is worse than a larger commit. When you keep things atomic, name the reason in the commit body.

---

## 3. Verify the deployed artefact, not the push

Green CI proves the branch merged. It does not prove the live bundle changed.

```bash
# 1. each NEW module path must exist on the deployment (200 once the build lands)
for i in 1 2 3 4 5 6; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$SITE/src/ui/new-module.js")
  echo "attempt $i: $code"; [ "$code" = "200" ] && break; sleep 25
done

# 2. a symbol the fix DELETED must be absent from the served bundle (expect 0)
curl -s "$SITE/renderer/effects.js" | grep -c "obsoleteFunction"

# 3. a symbol the fix ADDED must be present (expect > 0)
curl -s "$SITE/src/ui/patched.js" | grep -c "NEW_CONSTANT"
```

Report the URLs and the counts. "Deployed" is a claim; `200 / 0 / 3` is evidence.

---

## 4. Handle advisories the host volunteers, separately

Pushes to some hosts echo pre-existing security advisories (Dependabot and friends). Triage rather than ignore or absorb:

- Name the dependency chain (which direct dependency pulls it in) and whether it ships in the production artefact — dev-only tooling is a different risk class from a runtime dependency.
- Check whether an update branch already exists before proposing work.
- Offer it as its own PR. Never fold a lockfile bump into a visual or behavioural fix; it makes both harder to review and to revert.

---

## 5. Close-out ledger

End the turn with, in this order:

1. The commit range actually pushed (`<old>..<new>`) and the one-line subject of each commit.
2. The gate table with real results, in the repository's documented order.
3. The deployed-artefact verification counts.
4. What was deliberately **not** done — the queued follow-ups — so the user can prioritise them instead of discovering them later.
5. Confirmation that the working tree is clean (nothing stashed, nothing uncommitted).
