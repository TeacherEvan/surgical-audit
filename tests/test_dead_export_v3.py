"""v3.0.0 barrel-aware dead-export regression tests.

Pins the P0 defects from the v2.4 self-audit: barrel re-exports must not mask
dead exports, duplicate dead export names must not mask each other, and unused
pure barrels are reported in a first-class dead_barrels bucket.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
SCHEMAS_DIR = SKILL_ROOT / "schemas"


def _sweep(tmp_path: Path) -> dict[str, Any]:
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
    data: dict[str, Any] = json.loads(proc.stdout)
    schema = json.loads(
        (SCHEMAS_DIR / "dead-export-sweep.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(data)
    return data


def test_barrel_reexport_does_not_mask_dead_export(tmp_path: Path) -> None:
    """An unused index.ts re-export must not make a dead export look live."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "feature.ts").write_text(
        "export function foo() { return 1; }\n", encoding="utf-8"
    )
    (src / "index.ts").write_text(
        "export { foo } from './feature';\n", encoding="utf-8"
    )
    data = _sweep(tmp_path)
    dead = {(r["path"], r["name"]) for r in data["dead_value_exports"]}
    assert ("src/feature.ts", "foo") in dead
    assert "src/index.ts" in data["dead_barrels"]


def test_live_export_through_barrel_chain(tmp_path: Path) -> None:
    """A production import via a barrel keeps the export live and barrel used."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "feature.ts").write_text(
        "export function used() { return 1; }\n", encoding="utf-8"
    )
    (src / "index.ts").write_text(
        "export { used } from './feature';\n", encoding="utf-8"
    )
    (src / "app.ts").write_text(
        "import { used } from './index';\nconsole.log(used());\n", encoding="utf-8"
    )
    data = _sweep(tmp_path)
    dead = {r["name"] for r in data["dead_value_exports"]}
    assert "used" not in dead
    assert "src/index.ts" not in data["dead_barrels"]


def test_duplicate_dead_names_do_not_mask_each_other(tmp_path: Path) -> None:
    """Two files declaring the same dead export must both be reported dead."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.ts").write_text("export const dup = 1;\n", encoding="utf-8")
    (src / "b.ts").write_text("export const dup = 2;\n", encoding="utf-8")
    data = _sweep(tmp_path)
    dead = {(r["path"], r["name"]) for r in data["dead_value_exports"]}
    assert ("src/a.ts", "dup") in dead
    assert ("src/b.ts", "dup") in dead
    assert data["duplicate_export_names"]["dup"] == ["src/a.ts", "src/b.ts"]


def test_wildcard_barrel_and_namespace_import(tmp_path: Path) -> None:
    """export * from + import * as ns resolves liveness through the barrel."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "feature.ts").write_text(
        "export function wild() { return 1; }\n", encoding="utf-8"
    )
    (src / "index.ts").write_text("export * from './feature';\n", encoding="utf-8")
    (src / "app.ts").write_text(
        "import * as ns from './index';\nns.wild();\n", encoding="utf-8"
    )
    data = _sweep(tmp_path)
    dead = {r["name"] for r in data["dead_value_exports"]}
    assert "wild" not in dead
    assert "src/index.ts" not in data["dead_barrels"]
