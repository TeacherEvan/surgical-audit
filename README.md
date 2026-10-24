# surgical-audit

Read-only 10-principal-engineer code, test, and refactor audit skill (v2.2.0)
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
| `SKILL.md` | Skill manifest + 5-pass audit protocol |
| `scripts/preflight_telemetry.py` | Polyglot static scanner (Python, TS/JS, C#, GDScript, C/C++, GLSL, Rust, Go, Lua) |
| `scripts/canvas_geometry_probe.mjs` | Playwright probe for rendered-artefact audits (segment counts per canvas) |
| `references/stack_failure_matrices.md` | Matrix A/B/C domain failure matrices |
| `references/test_mutation_rubric.md` | Mental mutation testing + MVTH blueprint |
| `references/runtime-probe-harness.md` | Pass 2.5 recipe: serves, probes, hit-tests, colour histograms |
| `references/remediation-delivery.md` | Pass 4.5 recipe: green commit series, verify the deployed artefact |
| `install_surgical_audit.sh` | One-command installer (fails if any listed asset is missing) |

## Install

### Nous Hermes Agent

```bash
bash install_surgical_audit.sh
```

### Every other agent (OpenCode, Antigravity, Cursor, Gemini CLI)

Each reads its own tree. `~/.config/opencode/skills` is a symlink to
`~/.hermes/skills` on many installs, so check before copying:

```bash
ls -ld ~/.config/opencode/skills
# symlink -> already covered by the Hermes install
# real dir -> copy the skill directory into it

cp -r ~/.hermes/skills/surgical-audit ~/.gemini/antigravity-cli/skills/
cp -r ~/.hermes/skills/surgical-audit ~/.cursor/skills/
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
