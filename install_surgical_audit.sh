#!/usr/bin/env bash
# install_surgical_audit.sh — Installs or refreshes the surgical-audit skill cleanly.
#
# Installs:
#   SKILL.md
#   README.md
#   LICENSE
#   AGENTS.md
#   scripts/preflight_telemetry.py
#   scripts/dead_export_sweep.py
#   scripts/canvas_geometry_probe.mjs
#   references/stack_failure_matrices.md
#   references/test_mutation_rubric.md
#   references/runtime-probe-harness.md
#   references/remediation-delivery.md
#   references/engagement-and-game-feel-audit.md
#   references/document-audit.md
#   templates/report.md
#   templates/report.sarif
#   schemas/telemetry.schema.json
#   schemas/dead-export-sweep.schema.json
#   schemas/canvas-probe.schema.json
#
# Usage:
#   ./install_surgical_audit.sh           # install to default Hermes skill dir
#   ./install_surgical_audit.sh /custom/dir

set -euo pipefail

HERMES_SKILL_DIR="${1:-${HOME}/.hermes/skills/surgical-audit}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[install_surgical_audit] Installing Surgical Audit (v2.4.0) to:"
echo "  ${HERMES_SKILL_DIR}"
echo

mkdir -p \
  "${HERMES_SKILL_DIR}/scripts" \
  "${HERMES_SKILL_DIR}/references" \
  "${HERMES_SKILL_DIR}/templates" \
  "${HERMES_SKILL_DIR}/schemas"

ASSETS=(
  "SKILL.md"
  "README.md"
  "LICENSE"
  "AGENTS.md"
  "scripts/preflight_telemetry.py"
  "scripts/dead_export_sweep.py"
  "scripts/canvas_geometry_probe.mjs"
  "references/stack_failure_matrices.md"
  "references/test_mutation_rubric.md"
  "references/runtime-probe-harness.md"
  "references/remediation-delivery.md"
  "references/engagement-and-game-feel-audit.md"
  "references/document-audit.md"
  "templates/report.md"
  "templates/report.sarif"
  "schemas/telemetry.schema.json"
  "schemas/dead-export-sweep.schema.json"
  "schemas/canvas-probe.schema.json"
)

copy_asset() {
  local rel="$1"
  local dest="$HERMES_SKILL_DIR/$rel"
  local src
  if [ -f "$SCRIPT_DIR/$rel" ]; then
    src="$SCRIPT_DIR/$rel"
  elif [ -f "./$rel" ]; then
    src="./$rel"
  else
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

for asset in "${ASSETS[@]}"; do
  copy_asset "$asset"
done

chmod +x \
  "${HERMES_SKILL_DIR}/scripts/preflight_telemetry.py" \
  "${HERMES_SKILL_DIR}/scripts/dead_export_sweep.py" \
  "${HERMES_SKILL_DIR}/scripts/canvas_geometry_probe.mjs"

if [ "${HERMES_SKILL_DIR%/}" = "${HOME}/.hermes/skills/surgical-audit" ] \
  && [ -x "${SCRIPT_DIR}/scripts/sync-skill.sh" ] \
  && git -C "${SCRIPT_DIR}" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo
  echo "[install_surgical_audit] Syncing all 8 agent skill mirrors..."
  bash "${SCRIPT_DIR}/scripts/sync-skill.sh" sync
fi

echo
echo "[install_surgical_audit] Verification:"
if command -v python3 >/dev/null 2>&1; then
  echo "  python3 -B ${HERMES_SKILL_DIR}/scripts/preflight_telemetry.py --sarif <target_repo>"
else
  echo "  NOTE: python3 not found on PATH; telemetry scanner requires Python 3.10+."
fi
echo
echo "Done. Also run 'bash scripts/sync-skill.sh verify' from the git repo to confirm all 8 agent mirrors match."
