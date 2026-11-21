"""v3.0.0 regression tests for preflight_telemetry defect fixes.

Each test pins a concrete defect from the v2.4 self-audit (Gemini review) and
asserts the corrected behaviour: streaming hash, unified pruning, McCabe CC
exclusions, hot-loop double-count/gating, exact SARIF line spans, template
${} preservation, regex-literal masking, SFC <script> isolation, and generics.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import jsonschema

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
SCHEMAS_DIR = SKILL_ROOT / "schemas"


def _load() -> ModuleType:
    path = SCRIPTS_DIR / "preflight_telemetry.py"
    spec = importlib.util.spec_from_file_location("sa_preflight_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


t = _load()


def test_streaming_hash_matches_multichunk_file(tmp_path: Path) -> None:
    """A >64 KiB file hashes identically to hashlib over the full bytes."""
    blob = (b"x" * 65536) + (b"y" * 70000) + b"tail"
    f = tmp_path / "big.bin"
    f.write_bytes(blob)
    assert t.sha256_file(str(f)) == hashlib.sha256(blob).hexdigest()


def test_prune_dirs_unified_with_dead_export_sweep() -> None:
    """Telemetry prunes the same build/vendor dirs as the dead-export sweep."""
    for d in ("target", "vendor", ".svelte-kit", ".nuxt", "coverage", "out"):
        assert d in t.PRUNE_DIRS


def test_python_with_is_not_a_cyclomatic_branch() -> None:
    """`with` blocks add nesting but must not inflate McCabe CC."""
    src = (
        "def f(path: str) -> None:\n"
        "    with open(path) as fh:\n"
        "        with open(path) as g:\n"
        "            fh.read()\n"
    )
    res = t.analyze_python(src)
    assert res["functions"][0]["estimated_cc"] == 1


def test_polyglot_else_does_not_inflate_cc() -> None:
    """if / else if / else counts the ifs only, never the else keywords."""
    src = (
        "function f(x) {\n"
        "  if (x > 0) { return 1; }\n"
        "  else if (x < 0) { return -1; }\n"
        "  else { return 0; }\n"
        "}\n"
    )
    analysis = t.analyze_polyglot_structure(src, ".js")
    assert analysis["cc"] == 3  # base 1 + two ifs


def test_hot_loop_no_double_count_and_context_gating() -> None:
    """Update/FixedUpdate count once each; .map only counts inside a loop file."""
    loop_src = (
        "void Update() { transform.position += Vector3.up; }\n"
        "void FixedUpdate() { items.map(x => x + 1); }\n"
    )
    assert t.hot_loop_markers(loop_src, ".cs") == 3  # Update, FixedUpdate, .map

    plain_src = "const ys = xs.map(x => x + 1);\nconst zs = xs.filter(x => x);\n"
    assert t.hot_loop_markers(plain_src, ".ts") == 0  # no loop entry -> gated off


def test_silent_catch_and_hot_loop_exact_sarif_lines(tmp_path: Path) -> None:
    """SARIF pins SA-SILENT-CATCH / SA-HOT-LOOP to real lines, not line 1."""
    src = (
        "def a() -> None:\n"
        "    try:\n"
        "        pass\n"
        "    except Exception: pass\n"
        "\n"
        "def render_loop() -> None:\n"
        "    requestAnimationFrame(tick)\n"
    )
    f = tmp_path / "noisy.py"
    f.write_text(src, encoding="utf-8")
    rec = t.scan_file(str(f))
    assert rec["silent_catch_lines"] == [4]
    assert rec["hot_loop_lines"] == [7]
    out = tmp_path / "report.sarif"
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "preflight_telemetry.py"),
            str(tmp_path),
            "--sarif",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    sarif = json.loads(out.read_text(encoding="utf-8"))
    results = sarif["runs"][0]["results"]
    silent = [r for r in results if r["ruleId"] == "SA-SILENT-CATCH"]
    hot = [r for r in results if r["ruleId"] == "SA-HOT-LOOP"]
    assert silent[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 4
    assert hot[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 7


def test_template_expression_branches_are_counted() -> None:
    """${...} code inside a template literal contributes branches to CC."""
    src = (
        "function f(flag, raw) {\n"
        "  return `value=${flag && raw.length > 0 ? 1 : 0}`;\n"
        "}\n"
    )
    analysis = t.analyze_polyglot_structure(src, ".ts")
    assert analysis["cc"] >= 3  # && and ? inside ${} survive masking


def test_regex_literal_does_not_corrupt_masking() -> None:
    """A regex containing quotes/slashes must not desync the rest of the file."""
    src = (
        "const re = /['\"]/;\n"
        "const url = /https?:\\/\\//;\n"
        "function after(x) { return x ? 1 : 0; }\n"
    )
    cleaned = t.strip_comments_and_strings(src, ".ts")
    assert "function after" in cleaned
    analysis = t.analyze_polyglot_structure(src, ".ts")
    names = [f["name"] for f in analysis["high_complexity_functions"]]
    assert "after" in names


def test_svelte_markup_apostrophe_does_not_break_script() -> None:
    """An apostrophe in Svelte markup must not mask the <script> body."""
    src = (
        "<p>don't panic</p>\n"
        "<script>\n"
        "  export function go(x) { return x ? 1 : 0; }\n"
        "</script>\n"
    )
    cleaned = t.strip_comments_and_strings(src, ".svelte")
    assert "export function go" in cleaned
    analysis = t.analyze_polyglot_structure(src, ".svelte")
    names = [f["name"] for f in analysis["high_complexity_functions"]]
    assert "go" in names


def test_generic_function_is_detected() -> None:
    """function parse<T>(...) is captured as a named function span."""
    src = "export function parse<T>(raw: string): T { return raw as T; }\n"
    analysis = t.analyze_polyglot_structure(src, ".ts")
    names = [f["name"] for f in analysis["high_complexity_functions"]]
    assert "parse" in names


def test_telemetry_schema_includes_line_fields(tmp_path: Path) -> None:
    """CLI output carries the new line arrays and validates against the schema."""
    (tmp_path / "s.py").write_text(
        "def f() -> None:\n    try:\n        pass\n    except Exception: pass\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "preflight_telemetry.py"),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    schema = json.loads(
        (SCHEMAS_DIR / "telemetry.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(payload)
    rec = payload["files"][0]
    assert rec["silent_catch_lines"] == [4]
    assert isinstance(rec["hot_loop_lines"], list)
