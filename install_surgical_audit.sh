#!/usr/bin/env bash
# install_surgical_audit.sh — Installs or refreshes the surgical-audit skill cleanly.
#
# Runtime assets are discovered dynamically (matching scripts/sync-skill.sh) so
# new scripts/schemas are picked up without editing a hardcoded manifest:
#   SKILL.md, README.md, LICENSE, AGENTS.md
#   references/*.md, templates/*, schemas/*.json
#   scripts/* except repo-only tooling (conform.py, sync-skill.sh, run-ci-locally.py)
# Only files with a #! shebang are made executable; libraries stay 0644.
#
# Usage:
#   ./install_surgical_audit.sh           # install to default Hermes skill dir
#   ./install_surgical_audit.sh /custom/dir

set -euo pipefail

: "${HOME:?HOME environment variable must be set}"
HERMES_SKILL_DIR="${1:-${HOME}/.hermes/skills/surgical-audit}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[install_surgical_audit] Installing Surgical Audit (v3.0.0) to:"
echo "  ${HERMES_SKILL_DIR}"
echo

mkdir -p \
  "${HERMES_SKILL_DIR}/scripts" \
  "${HERMES_SKILL_DIR}/references" \
  "${HERMES_SKILL_DIR}/templates" \
  "${HERMES_SKILL_DIR}/schemas"

copy_asset() {
  local rel="$1"
  local src="$SCRIPT_DIR/$rel"
  local dest="$HERMES_SKILL_DIR/$rel"
  if [ ! -f "$src" ]; then
    echo "ERROR: Missing source file '$rel' relative to $SCRIPT_DIR" >&2
    exit 1
  fi
  if command -v realpath >/dev/null 2>&1; then
    if [ "$(realpath "$src")" = "$(realpath -m "$dest")" ]; then
      echo "  [OK] Already in place: $rel"
      return 0
    fi
  fi
  cp "$src" "$dest"
  echo "  [INSTALLED] $rel"
}

for rel in SKILL.md README.md LICENSE AGENTS.md; do
  if [ -f "$SCRIPT_DIR/$rel" ]; then
    copy_asset "$rel"
  fi
done

for src in "$SCRIPT_DIR"/references/*.md "$SCRIPT_DIR"/templates/* "$SCRIPT_DIR"/schemas/*.json; do
  [ -f "$src" ] || continue
  copy_asset "${src#"$SCRIPT_DIR"/}"
done

REPO_ONLY_SCRIPTS="conform.py sync-skill.sh run-ci-locally.py"
for src in "$SCRIPT_DIR"/scripts/*; do
  [ -f "$src" ] || continue
  base="$(basename "$src")"
  case " $REPO_ONLY_SCRIPTS " in
    *" $base "*) continue ;;
  esac
  copy_asset "scripts/$base"
  if head -c 2 "$src" | grep -q '#!'; then
    chmod +x "$HERMES_SKILL_DIR/scripts/$base"
  fi
done

if [ "${HERMES_SKILL_DIR%/}" = "${HOME}/.hermes/skills/surgical-audit" ] \
  && [ -x "${SCRIPT_DIR}/scripts/sync-skill.sh" ] \
  && git -C "${SCRIPT_DIR}" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo
  echo "[install_surgical_audit] Syncing all agent skill mirrors..."
  bash "${SCRIPT_DIR}/scripts/sync-skill.sh" sync
fi

echo
echo "[install_surgical_audit] Verification:"
if command -v python3 >/dev/null 2>&1; then
  echo "  python3 -B ${HERMES_SKILL_DIR}/scripts/preflight_telemetry.py --sarif <target_repo>"
  echo "  python3 -B ${HERMES_SKILL_DIR}/scripts/score_audit.py --loc 1000 --p1 1"
else
  echo "  NOTE: python3 not found on PATH; telemetry scanner requires Python 3.10+."
fi
echo
echo "Done. Also run 'bash scripts/sync-skill.sh verify' from the git repo to confirm mirrors match."
