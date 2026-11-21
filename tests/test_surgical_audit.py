"""Unit and integration tests for the surgical-audit skill toolchain."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import jsonschema
import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
SCHEMAS_DIR = SKILL_ROOT / "schemas"
TEMPLATES_DIR = SKILL_ROOT / "templates"


def _load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"sa_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


telemetry = _load_script("preflight_telemetry")
dead_sweep = _load_script("dead_export_sweep")
conform = _load_script("conform")


def _load_schema(filename: str) -> dict[str, Any]:
    raw = (SCHEMAS_DIR / filename).read_text(encoding="utf-8")
    return cast(dict[str, Any], json.loads(raw))


def test_python_isolated_function_cc_no_slice_bleed() -> None:
    """5-line sha256_file right above a branch-heavy function must score CC == 1."""
    branch_lines = "\n".join(
        f"    elif x == {i} and (y > {i} or z < {i}):\n        return {i}"
        for i in range(1, 25)
    )
    src = (
        "import hashlib\nfrom pathlib import Path\n\n\n"
        "def sha256_file(path: str) -> str:\n"
        '    """Compute hex digest."""\n'
        "    return hashlib.sha256(Path(path).read_bytes()).hexdigest()\n\n\n"
        "def mega_router(x: int, y: int, z: int) -> int:\n"
        "    if x == 0:\n"
        "        return 0\n"
        f"{branch_lines}\n"
        "    return -1\n"
    )
    res = telemetry.analyze_python(src)
    by_name = {f["name"]: f for f in res["functions"]}
    assert by_name["sha256_file"]["estimated_cc"] == 1
    assert by_name["sha256_file"]["loc"] <= 4
    assert by_name["mega_router"]["estimated_cc"] >= 45
    assert res["parse_error"] is None


def test_python_nested_function_and_control_flow_depth() -> None:
    """Nested helper CC must stay isolated and DepthCounter must track CF only."""
    flat_expr = (
        "def arithmetic_expression(a: int, b: int, c: int, d: int) -> int:\n"
        "    return ((a + b) * (c - d)) + ((a * c) - (b + d))\n\n"
        "def nested_cf(items: list[int]) -> int:\n"
        "    if items:\n"
        "        for x in items:\n"
        "            try:\n"
        "                if x > 0:\n"
        "                    return x\n"
        "            except ValueError:\n"
        "                continue\n"
        "    return 0\n\n"
        "def outer(flag: bool) -> int:\n"
        "    def inner(a: bool, b: bool, c: bool) -> int:\n"
        "        if a and b:\n"
        "            return 1\n"
        "        return 2 if c else 0\n"
        "    return inner(flag, flag, flag)\n"
    )
    res = telemetry.analyze_python(flat_expr)
    by_name = {f["name"]: f for f in res["functions"]}
    assert by_name["arithmetic_expression"]["estimated_cc"] == 1
    assert by_name["outer"]["estimated_cc"] == 1
    assert by_name["inner"]["estimated_cc"] == 4
    assert res["max_nesting"] == 4


def test_python_hot_loc_threshold_and_docstring_exclusion(tmp_path: Path) -> None:
    """Multi-line docstrings must not inflate LOC; 65-LOC func triggers flag."""
    doc_body = "\n".join(f"Doc line {i}" for i in range(12))
    src = (
        f'"""\n{doc_body}\n"""\n\n'
        "class Box:\n"
        '    """\n    Class doc line 1\n    Class doc line 2\n    """\n\n'
        "    def value(self) -> int:\n"
        '        """Method doc."""\n'
        "        return 1\n"
    )
    assert telemetry.effective_loc(src, ".py") == 3

    long_body = "\n".join(f"    total += {i}" for i in range(62))
    long_fn = (
        f"def long_linear(x: int) -> int:\n"
        f"    total = x\n{long_body}\n    return total\n"
    )
    mod_file = tmp_path / "long_mod.py"
    mod_file.write_text(long_fn, encoding="utf-8")
    rec = telemetry.scan_file(str(mod_file))
    assert rec["cyclomatic_complexity"] == 1
    assert rec["max_function_loc"] >= 60
    assert rec["high_complexity"] is True


def test_polyglot_ternary_short_circuit_and_ts_optional() -> None:
    """Ternaries, nullish, && and || increment JS/TS CC while ?. and ?: do not."""
    ts_src = (
        "interface Opt { name?: string; }\n"
        "export function decide(a: boolean, b: boolean, opt?: Opt): number {\n"
        "  const label = opt?.name ?? 'fallback';\n"
        "  const ok = a && (b || label.length > 0);\n"
        "  // if (ignored && comment || a ? 1 : 2)\n"
        "  const s = '&& || ? if while';\n"
        "  return ok ? 1 : 0;\n"
        "}\n"
    )
    # Real branch operators: ?? (+1), && (+1), || (+1), ? (+1) = 4 branches => CC 5
    analysis = telemetry.analyze_polyglot_structure(ts_src, ".ts")
    assert analysis["cc"] == 5
    assert analysis["high_complexity_functions"][0]["name"] == "decide"


def test_prune_dirs_skipped_count_and_broken_symlink(tmp_path: Path) -> None:
    """Vendored/cache dirs are pruned from hash + LOC; broken symlinks don't fail."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    app = src_dir / "app.py"
    app.write_text("def ok() -> int:\n    return 1\n", encoding="utf-8")

    for d in (
        "node_modules/pkg",
        ".pytest_cache/v",
        "dist",
        ".venv/lib",
        ".mypy_cache",
    ):
        p = tmp_path / d
        p.mkdir(parents=True)
        (p / "ignored.js").write_text("if (a && b || c ? 1 : 2) {}\n", encoding="utf-8")

    broken = src_dir / "dangling.py"
    broken.symlink_to("/nonexistent/target/missing.py")

    first = telemetry.scan_directory(str(tmp_path))
    assert first["files_scanned"] == 1
    assert first["skipped_dirs_count"] >= 5

    (tmp_path / "node_modules/pkg/ignored.js").write_text(
        "export const changed = true;\n", encoding="utf-8"
    )
    second = telemetry.scan_directory(str(tmp_path))
    assert second["tree_integrity_sha256"] == first["tree_integrity_sha256"]


def test_silent_catches_python_and_js() -> None:
    """Detect single-line/multi-line Python pass catches and avoid JS double-count."""
    py_src = (
        "def risky(x: int) -> None:\n"
        "    try:\n"
        "        _ = 1 / x\n"
        "    except ZeroDivisionError: pass\n"
        "    try:\n"
        "        _ = int('bad')\n"
        "    except ValueError:\n"
        "        ...\n"
    )
    assert telemetry.silent_catches(py_src, ".py") == 2

    js_src = (
        "function quiet() {\n"
        "  try { a(); } catch () {}\n"
        "  try { b(); } catch (err) { /* ignore */ }\n"
        "}\n"
    )
    assert telemetry.silent_catches(js_src, ".js") == 2


def test_sarif_cli_and_template_validity(tmp_path: Path) -> None:
    """`--sarif` and `templates/report.sarif` produce valid SARIF 2.1.0 documents."""
    bad = tmp_path / "noisy.py"
    bad.write_text(
        "def swallowed() -> None:\n"
        "    try:\n        pass\n    except Exception: pass\n",
        encoding="utf-8",
    )
    out_sarif = tmp_path / "report.sarif"
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "preflight_telemetry.py"),
            str(tmp_path),
            "--sarif",
            "--out",
            str(out_sarif),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "wrote" in proc.stdout

    sarif_doc = json.loads(out_sarif.read_text(encoding="utf-8"))
    assert sarif_doc["$schema"] == "https://json.schemastore.org/sarif-2.1.0.json"
    assert sarif_doc["version"] == "2.1.0"
    run = sarif_doc["runs"][0]
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert {"SA-GOD-FILE", "SA-HIGH-COMPLEXITY", "SA-SILENT-CATCH"}.issubset(rule_ids)
    assert any(res["ruleId"] == "SA-SILENT-CATCH" for res in run["results"])

    template_sarif = json.loads((TEMPLATES_DIR / "report.sarif").read_text("utf-8"))
    assert template_sarif["version"] == "2.1.0"
    assert template_sarif["runs"][0]["tool"]["driver"]["rules"]


def test_telemetry_cli_validates_against_schema_and_rejects_extra(
    tmp_path: Path,
) -> None:
    """Telemetry JSON output validates cleanly against Draft 2020-12 schema."""
    (tmp_path / "sample.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
    )
    (tmp_path / "widget.ts").write_text(
        "export function ok(flag: boolean): number { return flag ? 1 : 0; }\n",
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
    schema = _load_schema("telemetry.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(payload)

    mutated = dict(payload)
    mutated["unexpected_extra_key"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)


def test_dead_export_sweep_async_generator_destructured_and_src_scope(
    tmp_path: Path,
) -> None:
    """Sweep catches async/generator/destructured exports and preserves test refs."""
    src = tmp_path / "src"
    tests = tmp_path / "tests"
    src.mkdir()
    tests.mkdir()

    (src / "mod.ts").write_text(
        "export async function fetchData(): Promise<number> { return 1; }\n"
        "export function* genIds(): Generator<number> { yield 1; }\n"
        "export const { alpha, beta } = { alpha: 1, beta: 2 };\n"
        "export type DeadType = string;\n"
        "export function usedInProd(): number { return 42; }\n"
        "export function helperForTests(): number { return 7; }\n"
        'const decoy = "fetchData genIds alpha";\n',
        encoding="utf-8",
    )
    (src / "app.ts").write_text(
        "import { usedInProd } from './mod';\nconsole.log(usedInProd());\n",
        encoding="utf-8",
    )
    (tests / "mod.test.ts").write_text(
        "import { helperForTests } from '../src/mod';\nhelperForTests();\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "dead_export_sweep.py"),
            str(tmp_path),
            "--src",
            "src",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    schema = _load_schema("dead-export-sweep.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(data)

    dead_names = {row["name"] for row in data["dead_value_exports"]}
    assert {"fetchData", "genIds", "alpha", "beta"}.issubset(dead_names)
    assert "usedInProd" not in dead_names

    test_only = {row["name"]: row for row in data["test_only_exports"]}
    assert "helperForTests" in test_only
    assert test_only["helperForTests"]["test_refs"] >= 1

    dead_types = {row["name"] for row in data["dead_type_exports"]}
    assert "DeadType" in dead_types


def test_dead_export_sweep_cli_max_validation(tmp_path: Path) -> None:
    """Negative --max exits cleanly with code 2 instead of silently slicing."""
    (tmp_path / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "dead_export_sweep.py"),
            str(tmp_path),
            "--max",
            "-1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "--max must be >= 0" in proc.stderr


def test_canvas_probe_syntax_cli_errors_and_schema() -> None:
    """Canvas probe compiles with node --check, validates bad args, matches schema."""
    probe = SCRIPTS_DIR / "canvas_geometry_probe.mjs"
    syntax = subprocess.run(
        ["node", "--check", str(probe)], capture_output=True, text=True, check=False
    )
    assert syntax.returncode == 0, syntax.stderr

    for bad_args in ([], ["http://127.0.0.1:9", "-10"]):
        proc = subprocess.run(
            ["node", str(probe), *bad_args],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 2

    schema = _load_schema("canvas-probe.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    sample_output = {
        "url": "http://127.0.0.1:8000",
        "threshold": 300,
        "pageErrors": [],
        "consoleErrors": [],
        "requestFailures": [],
        "geometry": {
            "game-canvas": {
                "segments": 120,
                "longCount": 0,
                "longest": 24.5,
                "horizontal": 0,
                "vertical": 0,
                "rectEdges": 16,
                "sample": [],
            }
        },
        "hues": {
            "vivid": 1500,
            "hueBands": {
                "red": 12.0,
                "orange": 8.0,
                "amber": 5.0,
                "lime": 5.0,
                "green": 10.0,
                "spring": 5.0,
                "cyan": 15.0,
                "azure": 10.0,
                "blue": 10.0,
                "violet": 8.0,
                "magenta": 7.0,
                "pink": 5.0,
            },
        },
    }
    validator.validate(sample_output)

    bad_payload = dict(sample_output)
    bad_payload["extraField"] = 1
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad_payload)


def test_conform_passes_matches_canonical_digest_and_rejects_drift(
    tmp_path: Path,
) -> None:
    """conform.py passes surgical-audit cleanly and catches malformed skills."""
    assert conform.check(SKILL_ROOT) == []
    assert conform.self_digest() == conform.CANONICAL_SHA256

    bad_skill = tmp_path / "broken-skill"
    bad_skill.mkdir()
    (bad_skill / "SKILL.md").write_text(
        "---\n"
        "name: broken-skill\n"
        'description: "Too short without prefix."\n'
        "version: 1.0.0\n"
        'author: "Test"\n'
        "license: MIT\n"
        "platforms: [linux]\n"
        "metadata:\n"
        "  hermes:\n"
        "    category: software-development\n"
        "    tags: [test]\n"
        "    related_skills: [bad:scope]\n"
        "---\n"
        "See references/does-not-exist.md.\n",
        encoding="utf-8",
    )
    problems = conform.check(bad_skill)
    assert any("Use when" in p for p in problems)
    assert any("related_skills" in p for p in problems)
    assert any("references/does-not-exist.md" in p for p in problems)


def test_zero_pii_across_repo() -> None:
    """Enforce generic zero-PII/secret invariants across every tracked text file.

    Only synthetic-placeholder rules are used (RFC 2606 email domains, generic
    home-path placeholders, token-shaped secret prefixes), so this test embeds
    no private identifiers and scans tests/ and scripts/ as well.
    """
    allowed_domains = {"example.com", "example.org", "example.net", "local"}
    email_re = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
    home_re = re.compile(r"(?:/home/|/Users/|C:\\Users\\)([A-Za-z0-9_.-]+)")
    home_placeholders = {
        "user",
        "username",
        "name",
        "example",
        "test",
        "runner",
        "linuxbrew",
        "<user>",
        "<name>",
        "<username>",
    }
    secret_res = (
        re.compile(r"ghp_[A-Za-z0-9]{36}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    )
    phantom_scripts = ("verify_cv_" + "consistency.py",)
    skip_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
    text_suffixes = {
        ".md",
        ".py",
        ".mjs",
        ".js",
        ".ts",
        ".json",
        ".sarif",
        ".sh",
        ".toml",
        ".yml",
        ".yaml",
        ".txt",
    }
    targets: list[Path] = []
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(SKILL_ROOT).parts
        if any(part in skip_dirs for part in rel_parts):
            continue
        if path.suffix in text_suffixes or path.name == "LICENSE":
            targets.append(path)
    assert targets, "no tracked text files discovered for the PII scan"
    for path in targets:
        rel = path.relative_to(SKILL_ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        for domain in email_re.findall(text):
            assert domain in allowed_domains, (
                f"non-placeholder email domain {domain!r} in {rel}"
            )
        for segment in home_re.findall(text):
            assert segment.lower() in home_placeholders, (
                f"non-placeholder home directory segment {segment!r} in {rel}"
            )
        for secret_re in secret_res:
            assert not secret_re.search(text), (
                f"secret-shaped token matching {secret_re.pattern!r} in {rel}"
            )
        for phantom in phantom_scripts:
            assert phantom not in text, f"phantom script {phantom!r} in {rel}"


def test_sync_skill_check_sync_verify_in_isolated_home(tmp_path: Path) -> None:
    """Verify sync-skill.sh mirrors runtime assets while excluding repo tooling."""
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["SKILL_TARGETS"] = (
        ".hermes/skills/surgical-audit:.copilot/skills/surgical-audit"
    )

    sync_script = str(SCRIPTS_DIR / "sync-skill.sh")
    res_sync = subprocess.run(
        ["bash", sync_script, "sync"],
        cwd=SKILL_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_sync.returncode == 0, res_sync.stdout + res_sync.stderr

    for rel_target in (
        ".hermes/skills/surgical-audit",
        ".copilot/skills/surgical-audit",
    ):
        installed = tmp_path / rel_target
        assert (installed / "SKILL.md").is_file()
        assert (installed / "references/document-audit.md").is_file()
        assert (installed / "scripts/preflight_telemetry.py").is_file()
        assert (installed / "scripts/dead_export_sweep.py").is_file()
        assert (installed / "scripts/canvas_geometry_probe.mjs").is_file()
        assert not (installed / "scripts/conform.py").exists()
        assert not (installed / "scripts/sync-skill.sh").exists()
        assert not (installed / "tests").exists()

    res_verify = subprocess.run(
        ["bash", sync_script, "verify"],
        cwd=SKILL_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_verify.returncode == 0, res_verify.stdout + res_verify.stderr
    shutil.rmtree(tmp_path / ".hermes", ignore_errors=True)
