#!/usr/bin/env bash
#
# install_surgical_audit.sh — One-command installer for the surgical-audit skill.
#
# Deploys the complete skill directory
#   (SKILL.md, scripts/preflight_telemetry.py,
#    references/stack_failure_matrices.md, references/test_mutation_rubric.md)
# into ~/.hermes/skills/surgical-audit/ on Linux, WSL, or Termux PRoot.
#
# Because OpenCode reads ~/.config/opencode/skills and Cursor reads
# ~/.cursor/skills, install those copies too (see the OpenCode / Cursor
# sections below). Antigravity syncs from ~/.hermes/skills/.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main/install_surgical_audit.sh | bash
#   # or
#   bash install_surgical_audit.sh
set -eo pipefail

SKILL_NAME="surgical-audit"
HERMES_SKILL_DIR="$HOME/.hermes/skills/$SKILL_NAME"
RAW_BASE="https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main"

# Resolve the source directory.
# - When run as a local file, BASH_SOURCE[0] names the script; use its dir.
# - When piped via `curl | bash`, BASH_SOURCE[0] is empty; fall back to
#   downloading the raw files from GitHub.
LOCAL_MODE=0
SOURCE="${BASH_SOURCE[0]:-}"
if [[ -n "$SOURCE" && -r "$SOURCE" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    LOCAL_MODE=1
fi

fetch_file() {
    # fetch_file <dest_path> <source>
    # source is either a local path or a raw GitHub URL.
    local dest="$1" src="$2"
    if [[ "$LOCAL_MODE" -eq 1 && "$src" != http* ]]; then
        cp "$src" "$dest"
    else
        curl -fsSL "$src" -o "$dest"
    fi
}

echo "[install_surgical_audit] Deploying $SKILL_NAME skill..."

mkdir -p "$HERMES_SKILL_DIR/scripts"
mkdir -p "$HERMES_SKILL_DIR/references"

# Core skill manifest.
fetch_file "$HERMES_SKILL_DIR/SKILL.md" "${SCRIPT_DIR:-$RAW_BASE}/SKILL.md"

# Polyglot static scanner.
fetch_file "$HERMES_SKILL_DIR/scripts/preflight_telemetry.py" "${SCRIPT_DIR:-$RAW_BASE}/scripts/preflight_telemetry.py"
chmod +x "$HERMES_SKILL_DIR/scripts/preflight_telemetry.py"

# Reference matrices.
fetch_file "$HERMES_SKILL_DIR/references/stack_failure_matrices.md" "${SCRIPT_DIR:-$RAW_BASE}/references/stack_failure_matrices.md"
fetch_file "$HERMES_SKILL_DIR/references/test_mutation_rubric.md" "${SCRIPT_DIR:-$RAW_BASE}/references/test_mutation_rubric.md"

chmod 755 "$HERMES_SKILL_DIR/scripts"

echo "[install_surgical_audit] Installed to $HERMES_SKILL_DIR"
echo "[install_surgical_audit] Files:"
find "$HERMES_SKILL_DIR" -type f -not -path '*/__pycache__/*' | sort

echo
echo "[install_surgical_audit] Done. The skill is now indexed by Nous Hermes Agent."
echo "[install_surgical_audit] OpenCode: copy into ~/.config/opencode/skills/surgical-audit/"
echo "[install_surgical_audit] Cursor:   copy into ~/.cursor/skills/surgical-audit/"
