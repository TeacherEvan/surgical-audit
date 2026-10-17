#!/usr/bin/env bash
#
# install_surgical_audit.sh — One-command local installer for the surgical-audit skill.
#
# Deploys the complete skill directory
#   (SKILL.md, scripts/preflight_telemetry.py,
#    references/stack_failure_matrices.md, references/test_mutation_rubric.md)
# into ~/.hermes/skills/surgical-audit/ on Linux, WSL, or Termux PRoot.
#
# Because ~/.opencode/skills is symlinked to ~/.hermes/skills and the Antigravity
# skill bundle is synced from ~/.hermes/skills/, this single install also makes
# the skill available to Nous Hermes Agent, OpenCode, and Antigravity.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main/install_surgical_audit.sh | bash
#   # or
#   bash install_surgical_audit.sh
set -euo pipefail

SKILL_NAME="surgical-audit"
HERMES_SKILL_DIR="$HOME/.hermes/skills/$SKILL_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[install_surgical_audit] Deploying $SKILL_NAME skill..."

mkdir -p "$HERMES_SKILL_DIR/scripts"
mkdir -p "$HERMES_SKILL_DIR/references"

# Core skill manifest.
cp "$SCRIPT_DIR/SKILL.md" "$HERMES_SKILL_DIR/SKILL.md"

# Polyglot static scanner.
cp "$SCRIPT_DIR/scripts/preflight_telemetry.py" "$HERMES_SKILL_DIR/scripts/preflight_telemetry.py"
chmod +x "$HERMES_SKILL_DIR/scripts/preflight_telemetry.py"

# Reference matrices.
cp "$SCRIPT_DIR/references/stack_failure_matrices.md" "$HERMES_SKILL_DIR/references/stack_failure_matrices.md"
cp "$SCRIPT_DIR/references/test_mutation_rubric.md" "$HERMES_SKILL_DIR/references/test_mutation_rubric.md"

chmod 755 "$HERMES_SKILL_DIR/scripts"

echo "[install_surgical_audit] Installed to $HERMES_SKILL_DIR"
echo "[install_surgical_audit] Files:"
find "$HERMES_SKILL_DIR" -type f | sort

echo
echo "[install_surgical_audit] Done. The skill is now indexed by Nous Hermes Agent."
echo "[install_surgical_audit] OpenCode picks it up via ~/.opencode/skills -> ~/.hermes/skills."
echo "[install_surgical_audit] Antigravity picks it up via the ~/.hermes/skills/ sync bundle."
