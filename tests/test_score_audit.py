"""Deterministic Pass-4 scorer tests: boundary math, risk bands, CLI, schema."""

from __future__ import annotations

import importlib.util
import json
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


def _load_scorer() -> ModuleType:
    path = SCRIPTS_DIR / "score_audit.py"
    spec = importlib.util.spec_from_file_location("sa_score_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


scorer = _load_scorer()


def _score(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "effective_loc": 1000,
        "p0": 0,
        "p1": 0,
        "p2": 0,
        "p3": 0,
        "killed": 0,
        "evaluated": 0,
    }
    base.update(overrides)
    return cast(dict[str, Any], scorer.compute_score(**base))


def test_clean_repo_no_mutants_scores_low() -> None:
    """Zero findings, zero evaluated mutants: P_test=15, S=85 -> LOW."""
    res = _score(effective_loc=100)
    assert res["d_raw"] == 0
    assert res["m_kill_pct"] == 0.0
    assert res["p_test"] == 15.0
    assert res["s_health"] == 85
    assert res["risk_level"] == "LOW"


def test_full_mutation_kill_removes_test_penalty() -> None:
    """killed == evaluated -> M_kill=100 -> P_test=0 -> S=100."""
    res = _score(killed=8, evaluated=8)
    assert res["m_kill_pct"] == 100.0
    assert res["p_test"] == 0.0
    assert res["s_health"] == 100
    assert res["risk_level"] == "LOW"


def test_p0_count_forces_risk_bands() -> None:
    """One P0 forces HIGH; two P0 force CRITICAL regardless of score."""
    assert _score(p0=1)["risk_level"] == "HIGH"
    assert _score(p0=2)["risk_level"] == "CRITICAL"
    assert _score(p0=1, killed=10, evaluated=10)["risk_level"] == "HIGH"


def test_d_raw_weights_and_scale_floor() -> None:
    """D_raw uses 18/8/3/1 weights; scale floors LOC at 500."""
    res = _score(effective_loc=10, p0=1, p1=1, p2=1, p3=1)
    assert res["d_raw"] == 18 + 8 + 3 + 1
    small = _score(effective_loc=10)["scale_factor"]
    floor = _score(effective_loc=500)["scale_factor"]
    assert small == floor == pytest.approx((2.0) ** 0.5)
    big = _score(effective_loc=4000)["scale_factor"]
    assert big == pytest.approx((1000.0 / 4000.0) ** 0.5)


def test_negative_and_overkilled_inputs_rejected() -> None:
    """Negative counts or killed>evaluated raise ValueError."""
    with pytest.raises(ValueError):
        _score(p0=-1)
    with pytest.raises(ValueError):
        _score(killed=5, evaluated=4)


def test_cli_json_validates_against_schema_and_rejects_extra(
    tmp_path: Path,
) -> None:
    """CLI JSON output is schema-valid; extra keys are rejected."""
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "score_audit.py"),
            "--loc",
            "1200",
            "--p1",
            "1",
            "--p2",
            "3",
            "--killed",
            "7",
            "--evaluated",
            "8",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    schema = json.loads(
        (SCHEMAS_DIR / "audit-score.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(payload)
    assert payload["risk_level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}

    mutated = dict(payload)
    mutated["unexpected_extra_key"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(mutated)


def test_cli_telemetry_and_html_loc_and_markdown(tmp_path: Path) -> None:
    """--telemetry reads LOC, --html-loc adds to it, --markdown renders."""
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps({"effective_loc_total": 900}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "score_audit.py"),
            "--telemetry",
            str(telemetry),
            "--html-loc",
            "100",
            "--markdown",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "1000" in proc.stdout
    assert "Risk level" in proc.stdout


def test_cli_missing_loc_and_bad_args_exit_two(tmp_path: Path) -> None:
    """No LOC source or negative counts exit cleanly with code 2."""
    script = str(SCRIPTS_DIR / "score_audit.py")
    missing = subprocess.run(
        [sys.executable, "-B", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2
    negative = subprocess.run(
        [sys.executable, "-B", script, "--loc", "100", "--p0", "-1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert negative.returncode == 2
