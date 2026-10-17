#!/usr/bin/env python3
"""
preflight_telemetry.py (v2.1.0) — Surgical Audit polyglot static scanner.

Zero-mutation, read-only repository telemetry for the surgical-audit skill.
Scans a target directory and emits:
  * tree_integrity_sha256  — pre-audit state digest (Merkle-style over sorted
                             file paths + contents, .git excluded)
  * effective LOC per file
  * Cyclomatic Complexity (CC) windows & brace/indent nesting depth
  * God-file flags (>400 effective LOC), high-complexity functions,
    silent catch blocks, hot-loop allocation markers
  * Risk-ranked hotspot list:
        Risk = LOC_effective * (1 + BranchDensity) + 50 * N_silent_catches

Usage:
    python3 preflight_telemetry.py <target_dir> [--out report.json]

All operations are read-only. No file under target_dir is ever created,
edited, or deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from ast import (
    AsyncFunctionDef,
    For,
    FunctionDef,
    If,
    While,
    Try,
    With,
    AsyncWith,
    walk,
)
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOD_FILE_LOC = 400
HIGH_CC_THRESHOLD = 10
BRACE_DEPTH_THRESHOLD = 5
HOT_LOC_THRESHOLD = 60
MAX_COMPLEXITY_SPANS = 15

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".svelte",
    ".cs",
    ".gd",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".glsl",
    ".vert",
    ".frag",
    ".rs",
    ".go",
    ".lua",
    ".pyw",
}

BRANCH_KEYWORDS = re.compile(
    r"\b(if|elif|else|for|while|match|case|catch|except|and|or|&&|\|\||\?\s*|:)\b"
)

POLYGLOT_FUNC_REGEX = re.compile(
    r"(?:(?:async\s+)?(?:function\s+|def\s+|func\s+|fn\s+|sub\s+))"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*[\((]"
)

# ---------------------------------------------------------------------------
# Hashing / integrity
# ---------------------------------------------------------------------------


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_tree_integrity_sha256(root: str) -> str:
    """Merkle-style digest: sha256 over sorted "relpath\0content_sha256" lines."""
    root = os.path.abspath(root)
    entries: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip version-control directories entirely (read-only traversal).
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            entries.append(f"{rel}\0{sha256_file(full)}")
    entries.sort()
    combined = "\n".join(entries).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


# ---------------------------------------------------------------------------
# Language-agnostic helpers
# ---------------------------------------------------------------------------


def strip_comments(source: str, ext: str) -> str:
    """Crude comment stripping for non-Python brace/indent languages."""
    if ext == ".py":
        return source  # Python handled by the AST path.
    out: List[str] = []
    in_block = False
    in_string = None  # None | "'" | '"'
    i = 0
    n = len(source)
    while i < n:
        c = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_block:
            if c == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            out.append(c)
            if c == "\\":
                out.append(source[i + 1] if i + 1 < n else "")
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue
        if c == "/" and nxt == "/":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if c == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        if c in ("'", '"'):
            in_string = c
            out.append(c)
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def effective_loc(source: str, ext: str) -> int:
    """Count non-blank lines that are not solely comments."""
    count = 0
    for raw in source.splitlines():
        line = raw.strip()
        if not line:
            continue
        if ext == ".py":
            if line.startswith("#"):
                continue
        else:
            if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
                continue
        count += 1
    return count


def silent_catches(source: str, ext: str) -> int:
    """Approximate count of empty/silent exception handlers."""
    count = 0
    if ext == ".py":
        # `except:` / `except Exception:` followed by `pass` on the next line.
        pattern = re.compile(
            r"^\s*except(?:\s+(?:[A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*)"
            r"(?:\s+as\s+[A-Za-z_]\w*)?)?\s*:\s*$",
            re.MULTILINE,
        )
        lines = source.splitlines()
        for m in pattern.finditer(source):
            start = source[: m.start()].count("\n")
            nxt = lines[start + 1].strip() if start + 1 < len(lines) else ""
            if nxt in ("pass", "...", "") or nxt.startswith("#"):
                count += 1
    else:
        count += len(re.findall(r"catch\s*\(\s*\)\s*\{\s*\}", source))
        count += len(re.findall(r"catch\s*\{\s*\}", source))
        count += len(re.findall(r"catch\s*\([^)]*\)\s*\{\s*\}", source))
    return count


def hot_loop_markers(source: str, ext: str) -> int:
    """Crude per-frame / hot-loop allocation markers."""
    markers = 0
    low = source.lower()
    triggers = [
        "requestanimationframe",
        "_process(",
        "update(",
        "void update(",
        "fixedupdate(",
        "ondraw(",
        "render(",
        "foreach(",
        ".map(",
        ".filter(",
        "new vector2",
        "new color",
    ]
    for trig in triggers:
        markers += low.count(trig)
    return markers


# ---------------------------------------------------------------------------
# Per-file scanning
# ---------------------------------------------------------------------------


def analyze_python(source: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "cc": 1,
        "max_nesting": 0,
        "functions": [],
        "parse_error": None,
    }
    try:
        tree = compile(source, "<ast>", "exec", flags=0, dont_inherit=True)
        # compile() only checks syntax; use ast for structure.
        import ast as _ast

        tree = _ast.parse(source)
    except SyntaxError as exc:
        result["parse_error"] = str(exc)
        return result

    import ast as _ast

    max_depth = 0

    class DepthCounter(_ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0

        def generic_visit(self, node):
            self.depth += 1
            nonlocal max_depth
            if self.depth > max_depth:
                max_depth = self.depth
            super().generic_visit(node)
            self.depth -= 1

    DepthCounter().visit(tree)

    for node in walk(tree):
        if isinstance(node, (FunctionDef, AsyncFunctionDef)):
            cc = 1
            name = node.name
            start = node.lineno
            # Capture up to ~120 lines for windowed CC estimate.
            lines = source.splitlines()[start - 1 : start + 119]
            snippet = "\n".join(lines)
            cc = 1 + len(BRANCH_KEYWORDS.findall(snippet))
            result["functions"].append(
                {
                    "name": name,
                    "start_line": start,
                    "estimated_cc": cc,
                }
            )
            if cc > result["cc"]:
                result["cc"] = cc

    result["max_nesting"] = max_depth
    result["functions"] = sorted(
        result["functions"], key=lambda f: f["estimated_cc"], reverse=True
    )[:MAX_COMPLEXITY_SPANS]
    return result


def analyze_polyglot_structure(source: str) -> Dict[str, Any]:
    """Brace & indentation depth + function complexity scanner for
    non-Python languages (TypeScript/JavaScript/React/Svelte, C#/Unity,
    GDScript/Godot, C/C++, GLSL shaders, Rust, Go, Lua, and Python)."""
    lines = source.splitlines()
    max_nesting = 0
    current_brace_depth = 0
    high_complexity_spans = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "/*", "*")):
            continue
        opens = stripped.count("{")
        closes = stripped.count("}")
        current_brace_depth = max(0, current_brace_depth + opens - closes)
        if current_brace_depth > max_nesting:
            max_nesting = current_brace_depth

    for match in POLYGLOT_FUNC_REGEX.finditer(source):
        fn_name = match.group(1)
        start_line = source[: match.start()].count("\n") + 1
        snippet_lines = lines[start_line - 1 : min(len(lines), start_line + 120)]
        snippet = "\n".join(snippet_lines)
        cc_est = 1 + len(BRANCH_KEYWORDS.findall(snippet))
        if cc_est >= HIGH_CC_THRESHOLD:
            high_complexity_spans.append(
                {
                    "name": fn_name,
                    "start_line": start_line,
                    "estimated_cc_window": cc_est,
                }
            )

    return {
        "max_brace_nesting_depth": max_nesting,
        "high_complexity_functions": high_complexity_spans[:MAX_COMPLEXITY_SPANS],
    }


def scan_file(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    if ext not in CODE_EXTENSIONS:
        return {"skipped": True, "reason": "non-code extension"}

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        source = fh.read()

    loc = effective_loc(source, ext)
    catches = silent_catches(source, ext)
    hot = hot_loop_markers(source, ext)

    if ext == ".py":
        py = analyze_python(source)
        cc = py["cc"]
        nesting = py["max_nesting"]
        funcs = py["functions"]
        parse_error = py["parse_error"]
    else:
        poly = analyze_polyglot_structure(source)
        cc = max(
            (f["estimated_cc_window"] for f in poly["high_complexity_functions"]),
            default=1,
        )
        nesting = poly["max_brace_nesting_depth"]
        funcs = poly["high_complexity_functions"]
        parse_error = None

    branch_density = (cc - 1) / max(loc, 1)
    risk = loc * (1 + branch_density) + 50 * catches

    return {
        "path": path,
        "ext": ext,
        "effective_loc": loc,
        "cyclomatic_complexity": cc,
        "nesting_depth": nesting,
        "silent_catches": catches,
        "hot_loop_markers": hot,
        "branch_density": round(branch_density, 4),
        "risk_score": round(risk, 2),
        "high_complexity_functions": funcs,
        "parse_error": parse_error,
        "god_file": loc > GOD_FILE_LOC,
        "high_complexity": cc >= HIGH_CC_THRESHOLD
        or nesting > BRACE_DEPTH_THRESHOLD
        or loc >= HOT_LOC_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Directory scan & reporting
# ---------------------------------------------------------------------------


def scan_directory(target_dir: str) -> Dict[str, Any]:
    target_dir = os.path.abspath(target_dir)
    if not os.path.isdir(target_dir):
        raise SystemExit(f"[preflight_telemetry] not a directory: {target_dir}")

    tree_hash = compute_tree_integrity_sha256(target_dir)
    records: List[Dict[str, Any]] = []
    total_loc = 0
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(target_dir):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, target_dir)
            if os.path.splitext(name)[1].lower() not in CODE_EXTENSIONS:
                continue
            record = scan_file(full)
            record["path"] = rel
            if record.get("skipped"):
                continue
            total_loc += record["effective_loc"]
            total_files += 1
            records.append(record)

    records.sort(key=lambda r: r["risk_score"], reverse=True)

    return {
        "target_dir": target_dir,
        "tree_integrity_sha256": tree_hash,
        "files_scanned": total_files,
        "effective_loc_total": total_loc,
        "risk_formula": "LOC_effective * (1 + BranchDensity) + 50 * N_silent_catches",
        "god_files": [r["path"] for r in records if r["god_file"]],
        "high_complexity_files": [r["path"] for r in records if r["high_complexity"]],
        "files": records,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Surgical Audit preflight telemetry scanner (read-only)."
    )
    parser.add_argument("target_dir", help="Directory to scan")
    parser.add_argument(
        "--out",
        help="Write JSON report to this path (default: print to stdout)",
    )
    args = parser.parse_args(argv)

    report = scan_directory(args.target_dir)
    payload = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
        print(f"[preflight_telemetry] wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
