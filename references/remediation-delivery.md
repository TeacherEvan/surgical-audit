# Remediation Delivery — landing a verified fix as a green commit series

Use at the end of **Pass 4.5**, once the fixes pass their probes and the user asks to ship or merge. The audit produced evidence; this file turns it into history that survives review, bisect, and deployment.

---

## 1. Order the series so every tree is green

- **Fix before the assertion that depends on it.** If a new test asserts behaviour that lands in a different commit, the earlier commit is red. That breaks `git bisect`, and any reviewer or CI job that checks out that SHA sees a failure with no context. Order the mechanism first, or land both in one commit.
- **One concern per commit.** Conventional-commit scopes make the history legible; a mixed commit cannot be reverted selectively when one half turns out to be wrong.
- **Run the repository's documented gate order verbatim** on the final tree — whatever its `AGENTS.md`/CI defines, in that order. Do not substitute a shorter personal gate, and do not skip the typecheck/e2e step because "only JS changed".
- **Check installability before reading code.** Run the lockfile install first (`npm ci` / `uv sync --frozen` / `cargo fetch`). If it fails, no gate can run at all, so "the tests pass" is unknowable and every later observation is unverified. An `ERESOLVE`-style peer conflict is a P0 in its own right, not a footnote.
- **Multiple independent red gates justify one atomic commit.** When install, lint, typecheck, tests and build each fail for unrelated reasons, no ordering makes an intermediate commit green. Land them together and name the reason in the body; several red commits poison `git bisect` worse than one honest atomic fix.
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

## 2b. Prove each commit green on its **own** tree

Running the gates at the tip only proves the tip. Verify every commit in the series independently — no checkout, no stashing, no writes to the repo:

```bash
REPO=$(git rev-parse --show-toplevel); WORK=$(mktemp -d)
for SHA in $(git log --format=%H -5); do
  SHORT=$(git log -1 --format=%h "$SHA"); DIR="$WORK/$SHORT"
  mkdir -p "$DIR"; git archive "$SHA" | tar -x -C "$DIR"
  ln -s "$REPO/node_modules" "$DIR/node_modules"   # reuse deps, don't reinstall
  rm -rf "$REPO/node_modules/.tmp"                  # defeat incremental-build cache
  ( cd "$DIR" && npx tsc -b >/dev/null 2>&1; echo "$SHORT tsc=$?"
                 npx vitest run --reporter=dot 2>&1 | grep -E 'Test Files|Tests ' )
  rm -f "$DIR/node_modules"
done
```

Delete the incremental build-info directory before each run, or `tsc -b` reuses the previous tree's cache and reports a false green. Symlinking `node_modules` keeps this cheap; never delete or replace the repo's real one.

Report the per-commit table (`sha · tsc · test counts`) in the close-out. "Green at the tip" and "green on every commit" are different claims, and only the second one survives a bisect.

---

## 3. Verify the deployed artefact, not the push

Green CI proves the branch merged. It does not prove the live bundle changed. **A `200` from the site proves even less: every host serves the previous successful deployment, so the origin answers `200` whether or not your push ever built.** Establish real state before reporting anything shipped.

```bash
# 1. Does the automation run at all? A workflow file is not a running gate.
gh api repos/OWNER/REPO/actions/permissions   # {"enabled": false} => ci.yml is decorative
gh run list --workflow=ci.yml --limit 5        # empty => it has never executed once
```

A repo can carry a complete CI pipeline that has never run. That is how a red `main` sits unnoticed for weeks, and it invalidates any "CI will catch it" reasoning you were about to use.

```bash
# 2. Ask the platform, not the origin, what is live.
#    Vercel: project.live + latestDeployment.readyState / createdAt
#    readyState ERROR or live:false => the push did NOT deploy, whatever the site serves
```

```bash
# 3. Compare content hashes — the only unambiguous proof
LOCAL=$(basename "$(ls dist/assets/app-*.js | head -1)")          # from YOUR build
REMOTE=$(curl -s "$SITE/" | grep -oE 'assets/app-[A-Za-z0-9_-]+\.js' | head -1 | xargs basename)
[ "$LOCAL" = "$REMOTE" ] && echo "deployed" || echo "STALE: serving $REMOTE, built $LOCAL"
```

Different hash = old deployment, full stop. Report both hashes.

```bash
# 4. a symbol the fix DELETED must be absent (expect 0), one it ADDED present (> 0)
curl -s "$SITE/assets/app-<hash>.js" | grep -c "removedHelperName"   # 0
curl -s "$SITE/assets/app-<hash>.js" | grep -c "game-object"        # > 0
```

Grep for strings that ship, not identifiers you renamed: CSS class names, literal keys and user-facing copy survive minification; local variable names do not.

Report the URLs, the two hashes and the counts. "Deployed" is a claim; `app-ABC123 == app-ABC123 / 0 / 3` is evidence.

---

## 3b. When the host build fails but your local build passes

Do not "fix" code that is not broken. Reproduce the host's environment from the pushed SHA first — the host runtime that differs from yours, then the host's `installCommand` and `buildCommand`, verbatim:

```bash
# host Node major as a tar-dist: no root, no package manager, scratch only
FILE=$(curl -s https://nodejs.org/dist/latest-v22.x/ | grep -oE 'node-v22\.[0-9]+\.[0-9]+-linux-x64\.tar\.xz' | head -1)
mkdir -p "$SCRATCH/node22"
curl -sL "https://nodejs.org/dist/latest-v22.x/$FILE" | tar -xJ -C "$SCRATCH/node22" --strip-components=1
export PATH="$SCRATCH/node22/bin:$PATH"

git archive HEAD | tar -x -C "$SCRATCH/tree" && cd "$SCRATCH/tree"
npm install && npm run build      # the host's commands, not yours
```

Green here means the diff is innocent and the failure is project configuration — build root, output directory, ignored build step, missing env var, runtime version — not the commit. Say exactly that instead of guessing at a fix. Docker is frequently unavailable and only one Node major installed; the tar-dist above needs neither.

Then name the blocker and what you need (platform log access, a team grant, a settings change only the user can make). An unresolved deploy is reported as unresolved, with the gate that stopped it — never dressed up as shipped.

---

## 3c. Read the host's deployment record, and check who authored the commit

When the platform CLI is not authenticated (no `vercel`, no token), the git host's Deployments API still carries the platform's verdict, because the Git integration opens a Deployment per push:

```bash
gh api repos/OWNER/REPO/deployments --jq '.[0:3][] | [.environment,.created_at,.sha[0:7]] | @tsv'
ID=$(gh api repos/OWNER/REPO/deployments --jq '.[0].id')
gh api repos/OWNER/REPO/deployments/$ID/statuses --jq '.[0] | {state,description,environment_url}'
```

Read the `description`, because the two failure states need different fixes:

- `"Deployment was blocked"` is an **authorisation** refusal, not a build error. Hosts such as Vercel block a deployment whose commit author is not a member of the team/project, which is what happens when an agent commits as `Name <name@local>`. Sign the commit with an identity the host recognises, or have the owner deploy; do not rewrite pushed history just to change the author — land the fix from the right identity and say which one authored the pushed commits.
- `"Deployment has failed"` is a **build** failure: reproduce it per §3b before touching code.
- Check the previous deployment too. A chain of failures and blocks means there is no live build at all, so "the site answers 200" is the host's placeholder, not your artefact.
- A `302` to the host's SSO endpoint (`vercel.com/sso-api`) means the deployment is access-protected. Never quote that URL as a production host.

## 3d. Ship the server before the client when the contract changed

A new optional argument or field is backward-compatible in exactly one direction. Strict validators — Convex mutation args, protobuf with required fields, JSON Schema with `additionalProperties: false` — reject unknown keys, so a **new client against the old backend fails every call**, while an old client against the new backend keeps working because the new input is optional.

Release order: (1) deploy the server/backend, (2) build and deploy the client, (3) run one real round-trip per role and read it back from the server's own record. If the backend deploy is blocked, do **not** ship the client "to get something live" — it breaks the very feature the fix repaired. State the order in the close-out so the next operator does not reverse it.

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
3. The deployed-artefact verification: served-vs-built bundle hashes and the symbol counts — or, when the deploy failed, the platform's `readyState` plus the exact gate that stopped it, and what you need from the user to unblock it.
4. What was deliberately **not** done — the queued follow-ups — so the user can prioritise them instead of discovering them later.
5. Confirmation that the working tree is clean (nothing stashed, nothing uncommitted).
