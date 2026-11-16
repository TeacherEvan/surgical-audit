#!/usr/bin/env bash
# sync-skill.sh — mirror this repo's runtime skill assets into all 8 local agent installs.
#
# Canonical source of truth is THIS git checkout. Installs are copies and drift
# silently when edited directly, so after any change here:
#
#   ./scripts/sync-skill.sh check    # rsync dry-run + byte cross-check (exit 1 if missing/stale)
#   ./scripts/sync-skill.sh sync     # prune orphans, sync installs, then self-verify them
#   ./scripts/sync-skill.sh verify   # byte compare only (diff -r / cmp; exit 1 if missing/stale)
#   ./scripts/sync-skill.sh list     # show targets and file counts
#
# Every check/sync/verify ends with the same authoritative byte comparison, so a pass
# is evidence rather than rsync agreeing with itself.
#
# Mirrored by default (when present):
#   SKILL.md, README.md, LICENSE, AGENTS.md, SECURITY_MODEL.md,
#   references/, templates/, schemas/
# Optional runtime code dirs (opt-in via .sync-include-scripts, one dir per line):
#   scripts/ (excluding conform.py, sync-skill.sh, run-ci-locally.py),
#   runtime/, surgical_building/, examples/
# Excluded & pruned from installs:
#   .git/, .github/, tests/, benchmarks/, docs/, workspace/, workspace_test/,
#   GLE_*/, node_modules/, conform.py, sync-skill.sh, run-ci-locally.py
# Preserved: anything matching _archive* (local-only artifacts), __pycache__/, *.pyc.
#
# Must run FROM a git checkout (git rev-parse --show-toplevel == REPO_DIR).
# The skill name comes from SKILL.md YAML frontmatter, NOT from the directory name.
#
# Override targets with SKILL_TARGETS, colon-separated, relative to $HOME:
#   SKILL_TARGETS=".hermes/skills/DOCTOR/surgical-investigation" ./scripts/sync-skill.sh check
#
# Exit codes: 0 = in sync / success, 1 = missing target or drift detected (check, verify),
#             2 = usage error, or not run from a git checkout.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-check}"

case "$MODE" in
  check|sync|verify|list) ;;
  -h|--help|help)
    awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
    exit 0
    ;;
  *)
    printf 'usage: %s [check|sync|verify|list]\n' "$(basename "$0")" >&2
    exit 2
    ;;
esac

# --- refuse to run outside a real checkout -------------------------------------
TOPLEVEL="$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ "$TOPLEVEL" != "$REPO_DIR" ]; then
  printf 'ERROR: not a git checkout of this skill repo.\n' >&2
  printf '       dir      : %s\n' "$REPO_DIR" >&2
  printf '       toplevel : %s\n' "${TOPLEVEL:-<none>}" >&2
  printf '       Clone the repo and run scripts/sync-skill.sh from inside the clone.\n' >&2
  exit 2
fi

# --- skill name: frontmatter wins over directory name --------------------------
SKILL_NAME="$(awk '
  NR==1 && /^---[[:space:]]*$/ { in_fm=1; next }
  in_fm && /^---[[:space:]]*$/ { exit }
  in_fm && /^name:[[:space:]]*/ {
    sub(/^name:[[:space:]]*/, "")
    gsub(/["'\''[:space:]]/, "")
    print
    exit
  }
' "$REPO_DIR/SKILL.md" 2>/dev/null || true)"
if [ -z "$SKILL_NAME" ]; then
  SKILL_NAME="$(basename "$REPO_DIR")"
fi

# --- install targets (all 8 roots, relative to $HOME) --------------------------
if [ -n "${SKILL_TARGETS:-}" ]; then
  IFS=':' read -r -a TARGETS <<< "$SKILL_TARGETS"
else
  TARGETS=()
  shopt -s nullglob
  for cand in "$HOME/.hermes/skills/$SKILL_NAME" "$HOME"/.hermes/skills/*/"$SKILL_NAME"; do
    rel_hermes="${cand#"$HOME/.hermes/skills/"}"
    case "$rel_hermes" in
      .*) continue ;;
    esac
    if [ -d "$cand" ] || [ -L "$cand" ]; then
      TARGETS+=("${cand#"$HOME"/}")
    fi
  done
  shopt -u nullglob
  if [ "${#TARGETS[@]}" -eq 0 ]; then
    TARGETS=(".hermes/skills/$SKILL_NAME")
  fi

  TARGETS+=(
    ".config/opencode/skills/$SKILL_NAME"               # OpenCode
    ".gemini/antigravity-cli/skills/$SKILL_NAME"        # Antigravity CLI
    ".gemini/skills/$SKILL_NAME"                        # Gemini CLI
    ".gemini/surgical/$SKILL_NAME"                      # Gemini CLI (bundle)
    ".cursor/skills/$SKILL_NAME"                        # Cursor
    ".copilot/skills/$SKILL_NAME"                       # Copilot
    ".agents/skills/$SKILL_NAME"                        # Agents
  )
fi

# --- de-duplicate by real path (both parent and leaf symlinks) -----------------
resolve_target() {
  local full="$HOME/$1" parent base real_parent
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$full"
    return
  fi
  if [ -L "$full" ] || [ -d "$full" ]; then
    if command -v realpath >/dev/null 2>&1; then
      realpath -m "$full" 2>/dev/null || realpath "$full"
      return
    fi
  fi
  parent="$(dirname "$full")"
  base="$(basename "$full")"
  if [ -d "$parent" ]; then
    real_parent="$(cd -P "$parent" && pwd)"
    printf '%s/%s\n' "$real_parent" "$base"
  else
    printf '%s/%s\n' "$parent" "$base"
  fi
}

UNIQUE=()
SEEN_REAL=()
for rel in "${TARGETS[@]}"; do
  real="$(resolve_target "$rel")"
  skip=0
  for seen in "${SEEN_REAL[@]}"; do
    if [ "$seen" = "$real" ]; then
      skip=1
      break
    fi
  done
  if [ "$skip" -eq 0 ]; then
    UNIQUE+=("$rel")
    SEEN_REAL+=("$real")
  else
    printf '[DEDUPE] %s -> same directory as an earlier target\n' "$rel" >&2
  fi
done
TARGETS=("${UNIQUE[@]}")

# --- what gets mirrored -------------------------------------------------------
INCLUDE=(
  SKILL.md
  README.md
  LICENSE
  AGENTS.md
  SECURITY_MODEL.md
  references
  templates
  schemas
)

if [ -f "$REPO_DIR/.sync-include-scripts" ]; then
  while IFS= read -r entry || [ -n "$entry" ]; do
    entry="${entry%%#*}"
    entry="$(printf '%s' "$entry" | tr -d '[:space:]')"
    entry="${entry%/}"
    [ -z "$entry" ] && continue
    already=0
    for inc in "${INCLUDE[@]}"; do
      if [ "$inc" = "$entry" ]; then
        already=1
        break
      fi
    done
    if [ "$already" -eq 0 ]; then
      INCLUDE+=("$entry")
    fi
  done < "$REPO_DIR/.sync-include-scripts"
fi

REPO_ONLY_SCRIPTS=(conform.py sync-skill.sh run-ci-locally.py)

RSYNC_EXCLUDES=(
  --exclude '_archive*'
  --exclude '__pycache__'
  --exclude '*.pyc'
  --exclude '.pytest_cache'
  --exclude '.ruff_cache'
  --exclude '.mypy_cache'
  --exclude 'node_modules'
  --exclude 'conform.py'
  --exclude 'sync-skill.sh'
  --exclude 'run-ci-locally.py'
)
DIFF_EXCLUDES=(
  --exclude='_archive*'
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='.pytest_cache'
  --exclude='.ruff_cache'
  --exclude='.mypy_cache'
  --exclude='node_modules'
  --exclude='conform.py'
  --exclude='sync-skill.sh'
  --exclude='run-ci-locally.py'
)

is_included_asset() {
  local name="$1" inc
  for inc in "${INCLUDE[@]}"; do
    if [ "$inc" = "$name" ] && [ -e "$REPO_DIR/$inc" ]; then
      return 0
    fi
  done
  return 1
}

prune_install() {
  local dest="$1" entry base s nm pruned=0
  shopt -s nullglob dotglob
  for entry in "$dest"/*; do
    base="$(basename "$entry")"
    case "$base" in
      _archive*|__pycache__|*.pyc|.DS_Store) continue ;;
    esac
    if ! is_included_asset "$base"; then
      rm -rf "$entry"
      pruned=$((pruned + 1))
    fi
  done
  shopt -u nullglob dotglob

  if [ -d "$dest/scripts" ]; then
    for s in "${REPO_ONLY_SCRIPTS[@]}"; do
      if [ -e "$dest/scripts/$s" ] || [ -L "$dest/scripts/$s" ]; then
        rm -f "$dest/scripts/$s"
        pruned=$((pruned + 1))
      fi
    done
  fi

  while IFS= read -r -d '' nm; do
    rm -rf "$nm"
    pruned=$((pruned + 1))
  done < <(find "$dest/" -name node_modules -print0 2>/dev/null || true)

  changed=$((changed + pruned))
}

# byte_compare <install-dir>
# Independent of rsync: prints every difference and returns 1 if any exist.
byte_compare() {
  local dest="$1" p d diffs="" entry base s nm
  for p in "${INCLUDE[@]}"; do
    [ -e "$REPO_DIR/$p" ] || continue
    if [ ! -e "$dest/$p" ]; then
      diffs+="missing in install: $p"$'\n'
    elif [ -d "$REPO_DIR/$p" ]; then
      if [ ! -d "$dest/$p" ]; then
        diffs+="expected directory in install: $p"$'\n'
      else
        d="$(diff -r -q "${DIFF_EXCLUDES[@]}" "$REPO_DIR/$p" "$dest/$p" 2>&1 || true)"
        if [ -n "$d" ]; then
          diffs+="$d"$'\n'
        fi
      fi
    else
      if ! cmp -s "$REPO_DIR/$p" "$dest/$p"; then
        diffs+="differs: $p"$'\n'
      fi
    fi
  done

  shopt -s nullglob dotglob
  for entry in "$dest"/*; do
    base="$(basename "$entry")"
    case "$base" in
      _archive*|__pycache__|*.pyc|.DS_Store) continue ;;
    esac
    if ! is_included_asset "$base"; then
      diffs+="unexpected in install: $base"$'\n'
    fi
  done
  shopt -u nullglob dotglob

  if [ -d "$dest/scripts" ]; then
    for s in "${REPO_ONLY_SCRIPTS[@]}"; do
      if [ -e "$dest/scripts/$s" ] || [ -L "$dest/scripts/$s" ]; then
        diffs+="unexpected repo-only script in install: scripts/$s"$'\n'
      fi
    done
  fi

  nm="$(find "$dest/" -name node_modules -print -quit 2>/dev/null || true)"
  if [ -n "$nm" ]; then
    diffs+="unexpected node_modules in install: $nm"$'\n'
  fi

  [ -n "$diffs" ] || return 0
  printf '%s' "$diffs"
  return 1
}

head_sha="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || printf 'uncommitted')"
head_ref="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
printf 'repo   : %s\n' "$REPO_DIR"
printf 'skill  : %s\n' "$SKILL_NAME"
printf 'commit : %s (%s)\n' "$head_sha" "${head_ref:-unborn}"
printf 'mode   : %s\n\n' "$MODE"

changed=0
dirty=0
missing=0
failed=0

for rel in "${TARGETS[@]}"; do
  dest="$HOME/$rel"

  if [ ! -d "$dest" ]; then
    if [ "$MODE" = sync ]; then
      if [ -L "$dest" ]; then
        mkdir -p "$(resolve_target "$rel")"
      else
        mkdir -p "$dest"
      fi
      printf '[NEW ] %s\n' "$rel"
    else
      printf '[SKIP] %s — not installed\n' "$rel"
      missing=$((missing + 1))
      continue
    fi
  fi

  if [ "$MODE" = list ]; then
    file_count="$(find "$dest/" -type f -not -path '*__pycache__*' -not -path '*_archive*' | wc -l | tr -d '[:space:]')"
    printf '[OK  ] %-56s %s file(s)\n' "$rel" "$file_count"
    continue
  fi

  # --- verify: byte comparison only -------------------------------------------
  if [ "$MODE" = verify ]; then
    if diffs="$(byte_compare "$dest")"; then
      printf '[OK  ] %s — byte-identical to repo\n' "$rel"
    else
      printf '[FAIL] %s — differs:\n' "$rel"
      printf '%s\n' "$diffs" | sed 's/^/        /'
      dirty=$((dirty + 1))
    fi
    continue
  fi

  # --- check / sync: rsync, then never trust it alone --------------------------
  flags=(-a --delete "${RSYNC_EXCLUDES[@]}" --itemize-changes)
  if [ "$MODE" = check ]; then
    flags+=(--dry-run)
  else
    prune_install "$dest"
  fi

  out=""
  for p in "${INCLUDE[@]}"; do
    [ -e "$REPO_DIR/$p" ] || continue
    out+="$(rsync "${flags[@]}" "$REPO_DIR/$p" "$dest/" 2>&1 || true)"$'\n'
  done

  n="$(printf '%s' "$out" | grep -c '^[<>ch*]' || true)"

  if diffs="$(byte_compare "$dest")"; then
    if [ "$n" -gt 0 ] && [ "$MODE" = check ]; then
      printf '[OK  ] %s — in sync (%s metadata-only change(s) pending)\n' "$rel" "$n"
    elif [ "$MODE" = sync ] && [ "$n" -gt 0 ]; then
      printf '[SYNC] %s — %s change(s) applied\n' "$rel" "$n"
    else
      printf '[OK  ] %s — in sync\n' "$rel"
    fi
    changed=$((changed + n))
  else
    if [ "$MODE" = sync ]; then
      printf '[FAIL] %s — sync incomplete, still differs:\n' "$rel"
      failed=$((failed + 1))
    else
      printf '[STALE] %s — out of date:\n' "$rel"
      dirty=$((dirty + 1))
    fi
    printf '%s\n' "$diffs" | sed 's/^/        /'
    if [ -n "$out" ]; then
      printf '%s\n' "$out" | sed 's/^/        rsync: /'
    fi
  fi
done

printf '\n'
case "$MODE" in
  sync)
    if [ "$failed" -gt 0 ]; then
      printf 'FAILED: %s install(s) still differ after syncing.\n' "$failed"
      exit 1
    fi
    printf 'Done. %s file operation(s); every install verified byte-identical.\n' "$changed"
    ;;
  list)
    printf '%s target(s) configured.\n' "${#TARGETS[@]}"
    ;;
  check|verify)
    if [ "$dirty" -eq 0 ] && [ "$missing" -eq 0 ]; then
      printf 'Verified: %s install(s) match the repo.\n' "${#TARGETS[@]}"
      exit 0
    fi
    if [ "$dirty" -gt 0 ]; then
      printf '%s install(s) out of date — run: %s sync\n' "$dirty" "$0"
    fi
    if [ "$missing" -gt 0 ]; then
      printf '%s target(s) not installed — run: %s sync\n' "$missing" "$0"
    fi
    exit 1
    ;;
esac
