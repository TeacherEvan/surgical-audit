#!/usr/bin/env bash
#
# install_surgical_audit.sh — One-command installer for the surgical-audit skill.
#
# Deploys EVERY asset the SKILL.md names:
#   SKILL.md
#   scripts/preflight_telemetry.py
#   scripts/canvas_geometry_probe.mjs
#   references/stack_failure_matrices.md
#   references/test_mutation_rubric.md
#   references/runtime-probe-harness.md
#   references/remediation-delivery.md
#
# into ~/.hermes/skills/surgical-audit/ on Linux, macOS, WSL, or Termux PRoot.
#
# The asset list is the contract: the installer fails if any listed file is
# missing from the source, and re-checks every destination after copying. A
# partial install (manifest present, helper missing) is worse than no install,
# because it looks valid to the loader.
#
# Usage:
#   bash install_surgical_audit.sh
#   # or from remote (the script downloads each asset individually, so it does
#   # not depend on sibling files being present):
#   curl -fsSL https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main/install_surgical_audit.sh | bash
#
# Other agents read their own trees; mirror the same directory there:
#   OpenCode     ~/.config/opencode/skills/surgical-audit/   (may be a symlink to Hermes)
#   Antigravity  ~/.gemini/antigravity-cli/skills/surgical-audit/
#   Cursor       ~/.cursor/skills/surgical-audit/
set -eo pipefail

SKILL_NAME="surgical-audit"
HERMES_SKILL_DIR="$HOME/.hermes/skills/$SKILL_NAME"
RAW_BASE="https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main"

ASSETS=(
    "SKILL.md"
    "scripts/preflight_telemetry.py"
    "scripts/canvas_geometry_probe.mjs"
    "references/stack_failure_matrices.md"
    "references/test_mutation_rubric.md"
    "references/runtime-probe-harness.md"
    "references/remediation-delivery.md"
)

# Resolve the source directory.
# - Run as a local file: BASH_SOURCE[0] names the script; use its dir.
# - Piped via `curl | bash`: BASH_SOURCE[0] is empty; fall back to GitHub raw.
LOCAL_MODE=0
SOURCE="${BASH_SOURCE[0]:-}"
if [[ -n "$SOURCE" && -r "$SOURCE" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    LOCAL_MODE=1
fi

fetch_file() {
    # fetch_file <relative_path>
    local rel="$1" dest="$HERMES_SKILL_DIR/$rel" src
    src="${SCRIPT_DIR:-$RAW_BASE}/$rel"
    mkdir -p "$(dirname "$dest")"
    if [[ "$LOCAL_MODE" -eq 1 ]]; then
        if [[ ! -f "$src" ]]; then
            echo "[install_surgical_audit] MISSING SOURCE: $rel (expected at $src)" >&2
            exit 1
        fi
        cp "$src" "$dest"
    else
        curl -fsSL "$src" -o "$dest"
    fi
}

echo "[install_surgical_audit] Deploying $SKILL_NAME skill..."

# Fail before copying anything if the source tree is incomplete.
if [[ "$LOCAL_MODE" -eq 1 ]]; then
    for rel in "${ASSETS[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$rel" ]]; then
            echo "[install_surgical_audit] ABORT: source is missing $rel" >&2
            exit 1
        fi
    done
fi

for rel in "${ASSETS[@]}"; do
    fetch_file "$rel"
done

chmod +x "$HERMES_SKILL_DIR/scripts/preflight_telemetry.py" 2>/dev/null || true
chmod 755 "$HERMES_SKILL_DIR/scripts" 2>/dev/null || true

# Verify the destination: every asset present and non-empty.
missing=0
for rel in "${ASSETS[@]}"; do
    if [[ ! -s "$HERMES_SKILL_DIR/$rel" ]]; then
        echo "[install_surgical_audit] VERIFY FAILED: $rel is missing or empty" >&2
        missing=$((missing + 1))
    fi
done
if [[ "$missing" -gt 0 ]]; then
    echo "[install_surgical_audit] FAILED: $missing asset(s) not installed." >&2
    exit 1
fi

echo "[install_surgical_audit] Installed to $HERMES_SKILL_DIR"
echo "[install_surgical_audit] Files:"
find "$HERMES_SKILL_DIR" -type f -not -path '*/__pycache__/*' | sort

echo
echo "[install_surgical_audit] Done. The skill is now indexed by Nous Hermes Agent."
echo "[install_surgical_audit] Mirror the same directory into:"
echo "[install_surgical_audit]   OpenCode     ~/.config/opencode/skills/$SKILL_NAME/"
echo "[install_surgical_audit]   Antigravity  ~/.gemini/antigravity-cli/skills/$SKILL_NAME/"
echo "[install_surgical_audit]   Cursor       ~/.cursor/skills/$SKILL_NAME/"
