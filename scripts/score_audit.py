#!/usr/bin/env python3
"""score_audit.py (v3.0.0) — deterministic Pass-4 Health Score calculator.

Implements the exact Surgical Audit scoring formula documented in SKILL.md so
the agent never performs floating-point scoring by hand:

    D_raw   = 18*P0 + 8*P1 + 3*P2 + P3
    M_kill  = 100 * killed / evaluated        (0.0 when evaluated == 0)
    P_test  = 15 * (1 - M_kill / 100)
    scale   = sqrt(1000 / max(500, LOC_effective))
    S_health= max(0, min(100, round(100 - D_raw*scale - P_test)))

Risk bands: CRITICAL (S<40 or P0>=2), HIGH (40<=S<=64 or P0==1),
MODERATE (65<=S<=84 and P0==0), LOW (S>=85 and P0==0).

Usage:
    python3 score_audit.py --loc 1200 --p0 0 --p1 1 --p2 3 --p3 2 \
        --killed 7 --evaluated 8 [--json|--markdown] [--out report.json]
    python3 score_audit.py --telemetry telemetry.json --html-loc 80 --p1 1

Read-only and standard-library only. Output validates against
schemas/audit-score.schema.json (Draft 2020-12, unevaluatedProperties: false).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

VERSION = "3.0.0"

P0_WEIGHT = 18
P1_WEIGHT = 8
P2_WEIGHT = 3
P3_WEIGHT = 1
LOC_FLOOR = 500
LOC_SCALE_NUMERATOR = 1000.0
TEST_PENALTY_MAX = 15.0


def _risk_level(s_health: int, p0: int) -> str:
    """Classify the risk band from the health score and P0 count."""
    if s_health < 40 or p0 >= 2:
        return "CRITICAL"
    if p0 == 1 or s_health <= 64:
        return "HIGH"
    if s_health >= 85:
        return "LOW"
    return "MODERATE"


def compute_score(
    *,
    effective_loc: int,
    p0: int,
    p1: int,
    p2: int,
    p3: int,
    killed: int,
    evaluated: int,
) -> dict[str, Any]:
    """Compute the deterministic health score payload (schema-conformant)."""
    if min(effective_loc, p0, p1, p2, p3, killed, evaluated) < 0:
        raise ValueError("all counts and LOC must be >= 0")
    if killed > evaluated:
        raise ValueError("killed mutants cannot exceed evaluated mutants")

    d_raw = P0_WEIGHT * p0 + P1_WEIGHT * p1 + P2_WEIGHT * p2 + P3_WEIGHT * p3
    m_kill = (100.0 * killed / evaluated) if evaluated > 0 else 0.0
    p_test = TEST_PENALTY_MAX * (1.0 - m_kill / 100.0)
    scale = math.sqrt(LOC_SCALE_NUMERATOR / max(LOC_FLOOR, effective_loc))
    raw_score = 100.0 - d_raw * scale - p_test
    s_health = max(0, min(100, round(raw_score)))

    return {
        "effective_loc": effective_loc,
        "counts": {"p0": p0, "p1": p1, "p2": p2, "p3": p3},
        "d_raw": d_raw,
        "scale_factor": scale,
        "mutants_killed": killed,
        "mutants_evaluated": evaluated,
        "m_kill_pct": round(m_kill, 4),
        "p_test": round(p_test, 4),
        "s_health": s_health,
        "risk_level": _risk_level(s_health, p0),
    }


def _resolve_loc(args: argparse.Namespace) -> int:
    """Resolve effective LOC from --telemetry or --loc, adding --html-loc."""
    if args.telemetry:
        data = json.loads(Path(args.telemetry).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "effective_loc_total" not in data:
            raise ValueError("telemetry JSON lacks effective_loc_total")
        base = int(data["effective_loc_total"])
    elif args.loc is not None:
        base = int(args.loc)
    else:
        raise ValueError("provide --telemetry PATH or --loc N")
    return base + int(args.html_loc)


def _markdown_report(score: dict[str, Any]) -> str:
    """Render the score payload as a compact Markdown summary."""
    counts = score["counts"]
    lines = [
        "## Deterministic Health Score",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Effective LOC | {score['effective_loc']} |",
        (
            f"| P0 / P1 / P2 / P3 | {counts['p0']} / {counts['p1']} / "
            f"{counts['p2']} / {counts['p3']} |"
        ),
        f"| D_raw | {score['d_raw']} |",
        f"| Scale factor | {score['scale_factor']:.6f} |",
        (
            f"| M_kill | {score['m_kill_pct']}% "
            f"({score['mutants_killed']}/{score['mutants_evaluated']}) |"
        ),
        f"| P_test | {score['p_test']} |",
        f"| **S_health** | **{score['s_health']} / 100** |",
        f"| **Risk level** | **{score['risk_level']}** |",
        "",
    ]
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Deterministic Surgical Audit Pass-4 health scorer."
    )
    parser.add_argument("--telemetry", help="telemetry JSON to read LOC from")
    parser.add_argument("--loc", type=int, help="effective LOC (if no telemetry)")
    parser.add_argument(
        "--html-loc", type=int, default=0, help="inline HTML LOC to add"
    )
    parser.add_argument("--p0", type=int, default=0)
    parser.add_argument("--p1", type=int, default=0)
    parser.add_argument("--p2", type=int, default=0)
    parser.add_argument("--p3", type=int, default=0)
    parser.add_argument("--killed", type=int, default=0)
    parser.add_argument("--evaluated", type=int, default=0)
    parser.add_argument(
        "--markdown", action="store_true", help="emit Markdown instead of JSON"
    )
    parser.add_argument("--out", help="write output to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 0 on success, 2 on invalid arguments."""
    args = _build_parser().parse_args(argv)
    try:
        loc = _resolve_loc(args)
        score = compute_score(
            effective_loc=loc,
            p0=int(args.p0),
            p1=int(args.p1),
            p2=int(args.p2),
            p3=int(args.p3),
            killed=int(args.killed),
            evaluated=int(args.evaluated),
        )
    except (ValueError, OSError) as exc:
        print(f"[score_audit] {exc}", file=sys.stderr)
        return 2

    payload = _markdown_report(score) if args.markdown else json.dumps(score, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        print(f"[score_audit] wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
