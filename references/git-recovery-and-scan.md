# Git recovery + plan-scan reference

## Recovering a corrupted `.git` (caused by `git checkout -b <name> .`)

A trailing `.` turns branch-create into a pathspec and can invalidate the index
or destroy `.git` tracking. Symptoms: `git status` says "not a git repository",
`.git/` directory missing or partial, `fatal: not a git repository`.

**Recovery (history is preserved on the remote):**

```bash
cd /path/to/repo
git init                                          # recreate .git metadata
git remote add origin https://github.com/OWNER/REPO.git
git fetch origin                                  # pulls ALL history back
git reset --mixed origin/main                     # reattach index to remote tip
# working-tree edits are intact; only .git metadata was lost
```

After re-init, the working tree shows as fully modified/untracked because git
lost its index. Do NOT `git add -A`. Instead:
- `git status` to see what's actually changed
- stage ONLY the intended files: `git add path/to/file1 path/to/file2`
- commit on a fresh branch: `git checkout -b fix/thing` (NO trailing dot)
- push and open PR

If `git reset --mixed origin/main` is too aggressive (huge untracked tree),
skip the reset and just `git checkout -b fix/thing`, then `git add` only the
specific files, commit, push.

## Plan-scan command (ASCII-safe)

```bash
# catches plan docs by ASCII tokens (unicode ☑/✅ BREAKS rg and yields 0 matches)
rg -l -g 'docs/**/*.md' -i 'todo|objective|tick|plan|WIP|\[x\]|\[ \]' .

# second pass only if you must match checked boxes (separate, unicode-safe)
rg -l -g 'docs/**/*.md' '☑|✅' .
```

Also accept `agentplan`/`blueprint` JSON in `docs/plans/`.

## Resolving a user's loose path string to a real repo

```bash
# user says "Documents/VS/GAMES/Devil's Delight" — case/separator often wrong
ls -ld "/home/ewaldt/Documents/VS/GAMES/Devil-sDelight"   # hyphen, not space
cd /that/real/path && git remote -v                       # confirm GitHub repo
```

Never cross-wire two checkouts of the same repo (e.g. `GAMES/Devil-sDelight`
vs `Lea/.../Devil-sDelight(Lea)`). The active working copy is usually the one
holding the open PR branch.
