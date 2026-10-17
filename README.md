# surgical-audit

Read-only 10-principal-engineer code, test, and refactor audit skill (v2.1.0)
for Nous Hermes Agent, OpenCode, Antigravity, and Cursor.

## What it is

`surgical-audit` is a zero-mutation, deterministic architectural and code audit
equivalent to a 10-Principal-Engineer review board. It combines:

- Polyglot static AST / complexity scanning (`scripts/preflight_telemetry.py`)
- Stack-specific failure matrices (`references/stack_failure_matrices.md`)
- Mental mutation testing rubric (`references/test_mutation_rubric.md`)
- Context-compaction batching & quantitative health scoring
- A mandatory Markdown report template

It never mutates the target repository and proves non-mutation with a
SHA-256 tree-integrity digest captured before and after the audit.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Hermes/OpenCode/Cursor skill manifest + 5-pass audit protocol |
| `scripts/preflight_telemetry.py` | Polyglot static scanner (Python, TS/JS, C#, GDScript, C/C++, GLSL, Rust, Go, Lua) |
| `references/stack_failure_matrices.md` | Matrix A/B/C domain failure matrices |
| `references/test_mutation_rubric.md` | Mental mutation testing + MVTH blueprint |
| `install_surgical_audit.sh` | One-command installer |

## Install

### Nous Hermes Agent (also OpenCode & Antigravity)

OpenCode's `~/.opencode/skills` is symlinked to `~/.hermes/skills`, and the
Antigravity skill bundle syncs from `~/.hermes/skills/`, so one install covers
all three:

```bash
bash install_surgical_audit.sh
```

Or one-liner from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/TeacherEvan/surgical-audit/main/install_surgical_audit.sh | bash
```

### Cursor

Copy the skill into Cursor's skills directory:

```bash
mkdir -p ~/.cursor/skills/surgical-audit
cp SKILL.md references/stack_failure_matrices.md references/test_mutation_rubric.md scripts/preflight_telemetry.py ~/.cursor/skills/surgical-audit/
chmod +x ~/.cursor/skills/surgical-audit/scripts/preflight_telemetry.py
```

## Usage

Invoke the skill in Nous Hermes Agent (`/surgical-audit` or natural language),
then run the preflight scanner against a target repo:

```bash
python3 ~/.hermes/skills/surgical-audit/scripts/preflight_telemetry.py /path/to/target
```

See `SKILL.md` for the full Pass 1–5 protocol and the mandatory Markdown report
template.

## License

MIT
