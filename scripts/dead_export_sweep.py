#!/usr/bin/env python3
"""Dead-export sweep: find exported symbols that nothing else references.

Usage:
    python3 dead_export_sweep.py <repo_root> [--src DIR] [--max N] [--verbose] [--json]

Buckets
-------
DEAD VALUE   exported const/let/var/function/class/enum with zero references
             outside its own file  -> delete it, or wire it up
TEST-ONLY    referenced only by test files: the suite is green and the app
             never calls it  -> invisible debt masquerading as coverage
DEAD TYPE    interface/type with zero references -> usually noise in TS,
             counted separately and only listed with --verbose

Limits (state these in the audit report)
----------------------------------------
* Textual matching (comments and static strings masked), not a full module
  graph. A symbol reached only via `export *` barrels or dynamic property
  access counts as dead unless some consumer names it.
* Name shadowing inflates the reference count, so treat output as candidates to
  confirm with `ast-grep` / `grep -rn "<symbol>" src/ tests/ e2e/`, never as a
  blind delete list.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import TypedDict

PRUNE: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        "dist",
        "build",
        ".next",
        "out",
        "coverage",
        "vendor",
        ".venv",
        "venv",
        "__pycache__",
        "target",
        ".turbo",
        ".cache",
        ".svelte-kit",
        ".nuxt",
        "storybook-static",
    }
)
DEFAULT_EXTS: tuple[str, ...] = (
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".svelte",
    ".vue",
)

DECL_RE = re.compile(
    r"^[ \t]*export[ \t]+(?:declare[ \t]+)?(?:default[ \t]+)?"
    r"(?:async[ \t]+)?"
    r"(?P<kind>const|let|var|function|class|enum|interface|type|abstract[ \t]+class)"
    r"(?:[ \t]*\*[ \t]*|[ \t]+)(?P<name>[A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
DESTRUCT_DECL_RE = re.compile(
    r"^[ \t]*export[ \t]+(?:declare[ \t]+)?"
    r"(?P<kind>const|let|var)[ \t]*\{(?P<body>[^}]+)\}",
    re.MULTILINE,
)
NAMED_EXPORT_RE = re.compile(
    r"^[ \t]*export[ \t]+(?:(?P<type>type)[ \t]+)?\{(?P<body>[^}]+)\}"
    r"(?![ \t]*from\b)",
    re.MULTILINE,
)
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
TEST_FILE_RE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$")
TEST_DIR_PARTS: frozenset[str] = frozenset(
    {"__tests__", "__mocks__", "tests", "test", "e2e", "spec", "cypress"}
)

ExportRow = tuple[str, int, str, str, int]


class SweepSummary(TypedDict):
    files_scanned: int
    source_files_scanned: int
    distinct_exports: int
    dead_value: list[ExportRow]
    test_only: list[ExportRow]
    dead_type: list[ExportRow]
    duplicates: dict[str, list[str]]


def is_test_path(path: str) -> bool:
    """Return True if path resides in a test directory or matches test suffix."""
    parts = path.replace(os.sep, "/").split("/")
    return bool(TEST_FILE_RE.search(path)) or bool(TEST_DIR_PARTS & set(parts))


def _scan_quoted_literal(text: str, start: int, quote: str) -> tuple[list[str], int]:
    """Mask string literal contents with spaces while keeping newlines."""
    out = [" "]
    i = start + 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            nxt = text[i + 1] if i + 1 < n else ""
            out.append(" ")
            if nxt:
                out.append("\n" if nxt == "\n" else " ")
            i += 2 if nxt else 1
            continue
        if ch == quote:
            out.append(" ")
            return out, i + 1
        out.append("\n" if ch == "\n" else " ")
        i += 1
    return out, i


def _scan_template_literal(text: str, start: int) -> tuple[list[str], int]:
    """Mask static template text while preserving ${...} code expressions."""
    out = [" "]
    i = start + 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            nxt = text[i + 1] if i + 1 < n else ""
            out.append(" ")
            if nxt:
                out.append("\n" if nxt == "\n" else " ")
            i += 2 if nxt else 1
            continue
        if ch == "`":
            out.append(" ")
            return out, i + 1
        if ch == "$" and i + 1 < n and text[i + 1] == "{":
            out.extend(["$", "{"])
            expr, i = _mask_code_segment(text, i + 2, stop_on_rbrace=True)
            out.extend(expr)
            continue
        out.append("\n" if ch == "\n" else " ")
        i += 1
    return out, i


def _scan_block_comment(text: str, start: int) -> tuple[list[str], int]:
    """Mask /* ... */ comment preserving newlines."""
    out = [" ", " "]
    i = start + 2
    n = len(text)
    while i < n:
        if text[i] == "*" and i + 1 < n and text[i + 1] == "/":
            out.extend([" ", " "])
            return out, i + 2
        out.append("\n" if text[i] == "\n" else " ")
        i += 1
    return out, i


def _mask_code_segment(
    text: str,
    start: int = 0,
    *,
    stop_on_rbrace: bool = False,
) -> tuple[list[str], int]:
    """Mask comments and static strings from start, preserving line numbers."""
    out: list[str] = []
    i = start
    n = len(text)
    brace_depth = 1 if stop_on_rbrace else 0

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if stop_on_rbrace and ch in ("{", "}"):
            brace_depth += 1 if ch == "{" else -1
            out.append(ch)
            i += 1
            if brace_depth == 0:
                return out, i
            continue
        if ch == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch == "/" and nxt == "*":
            chunk, i = _scan_block_comment(text, i)
            out.extend(chunk)
            continue
        if ch in ("'", '"', "`"):
            chunk, i = (
                _scan_quoted_literal(text, i, ch)
                if ch in ("'", '"')
                else _scan_template_literal(text, i)
            )
            out.extend(chunk)
            continue
        out.append(ch)
        i += 1
    return out, i


def mask_comments_and_strings(text: str) -> str:
    """Return text with comments and static string literals replaced by spaces."""
    out, _ = _mask_code_segment(text, 0, stop_on_rbrace=False)
    return "".join(out)


def collect(root: str, ext_filter: tuple[str, ...]) -> dict[str, str]:
    """Collect all non-pruned source and test files across root."""
    texts: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            d for d in dirnames if d not in PRUNE and not d.startswith(".")
        )
        for fn in sorted(filenames):
            if not fn.endswith(ext_filter):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            try:
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    texts[rel] = fh.read()
            except OSError:
                continue
    return texts


def _in_src_scope(rel: str, src_filter: str) -> bool:
    if not src_filter:
        return True
    norm_rel = rel.replace(os.sep, "/")
    norm_src = src_filter.replace(os.sep, "/").strip("/")
    return norm_rel == norm_src or norm_rel.startswith(norm_src + "/")


def _extract_destructured_names(body: str) -> list[str]:
    names: list[str] = []
    for part in body.split(","):
        item = part.strip()
        if not item:
            continue
        item = item.split("=", 1)[0].strip()
        if ":" in item:
            item = item.split(":", 1)[1].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", item):
            names.append(item)
    return names


def _extract_named_export_names(body: str) -> list[str]:
    names: list[str] = []
    for part in body.split(","):
        item = part.strip()
        if not item:
            continue
        if item.startswith("type "):
            item = item[5:].strip()
        if " as " in item:
            item = item.rsplit(" as ", 1)[1].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", item):
            names.append(item)
    return names


def _extract_exports(masked_text: str) -> list[tuple[int, str, str]]:
    """Return sorted list of (line_no, name, kind) declarations in masked_text."""
    found: list[tuple[int, str, str]] = []
    seen_entries: set[tuple[int, str]] = set()

    for match in DECL_RE.finditer(masked_text):
        name = match.group("name")
        raw_kind = match.group("kind")
        kind = "class" if raw_kind.startswith("abstract") else raw_kind
        line = masked_text.count("\n", 0, match.start()) + 1
        if (line, name) not in seen_entries:
            seen_entries.add((line, name))
            found.append((line, name, kind))

    for match in DESTRUCT_DECL_RE.finditer(masked_text):
        kind = match.group("kind")
        line = masked_text.count("\n", 0, match.start()) + 1
        for name in _extract_destructured_names(match.group("body")):
            if (line, name) not in seen_entries:
                seen_entries.add((line, name))
                found.append((line, name, kind))

    for match in NAMED_EXPORT_RE.finditer(masked_text):
        kind = "type" if match.group("type") else "const"
        line = masked_text.count("\n", 0, match.start()) + 1
        for name in _extract_named_export_names(match.group("body")):
            if (line, name) not in seen_entries:
                seen_entries.add((line, name))
                found.append((line, name, kind))

    found.sort(key=lambda item: (item[0], item[1]))
    return found


def analyze_exports(
    texts: dict[str, str],
    src_filter: str = "",
) -> SweepSummary:
    """Compute dead-value, test-only, and dead-type export buckets."""
    masked_by_file: dict[str, str] = {
        rel: mask_comments_and_strings(text) for rel, text in texts.items()
    }
    file_tokens: dict[str, Counter[str]] = {}
    code_tokens: Counter[str] = Counter()
    test_tokens: Counter[str] = Counter()

    for rel, masked in masked_by_file.items():
        toks = Counter(IDENT_RE.findall(masked))
        file_tokens[rel] = toks
        if is_test_path(rel):
            test_tokens.update(toks)
        else:
            code_tokens.update(toks)

    dead_value: list[ExportRow] = []
    test_only: list[ExportRow] = []
    dead_type: list[ExportRow] = []
    seen: dict[str, list[str]] = defaultdict(list)
    scoped_files = 0

    for rel, masked in masked_by_file.items():
        if is_test_path(rel) or not _in_src_scope(rel, src_filter):
            continue
        scoped_files += 1
        own_tokens = file_tokens[rel]
        for line, name, kind in _extract_exports(masked):
            seen[name].append(rel)
            own = own_tokens.get(name, 0)
            code_refs = max(0, code_tokens.get(name, 0) - own)
            test_refs = test_tokens.get(name, 0)
            if code_refs > 0:
                continue
            row: ExportRow = (rel, line, name, kind, test_refs)
            if test_refs > 0:
                test_only.append(row)
            elif kind in ("interface", "type"):
                dead_type.append(row)
            else:
                dead_value.append(row)

    return {
        "files_scanned": len(texts),
        "source_files_scanned": scoped_files,
        "distinct_exports": len(seen),
        "dead_value": sorted(dead_value),
        "test_only": sorted(test_only),
        "dead_type": sorted(dead_type),
        "duplicates": {n: p for n, p in seen.items() if len(p) > 1},
    }


def _row_to_dict(row: ExportRow) -> dict[str, object]:
    rel, line, name, kind, test_refs = row
    return {
        "path": rel,
        "line": line,
        "name": name,
        "kind": kind,
        "test_refs": test_refs,
    }


def _print_text_report(
    summary: SweepSummary,
    *,
    max_rows: int,
    verbose: bool,
) -> None:
    dead_value = summary["dead_value"]
    test_only = summary["test_only"]
    dead_type = summary["dead_type"]
    dupes = summary["duplicates"]

    print(
        f"scanned {summary['files_scanned']} files, "
        f"{summary['distinct_exports']} distinct export declarations\n"
    )
    print(
        f"DEAD VALUE EXPORTS ({len(dead_value)})"
        " - zero references outside their own file"
    )
    for rel, line, name, kind, _ in dead_value[:max_rows]:
        print(f"  {rel}:{line}  {kind} {name}")

    print(f"\nTEST-ONLY EXPORTS ({len(test_only)}) - referenced only by tests")
    for rel, line, name, kind, refs in test_only[:max_rows]:
        print(f"  {rel}:{line}  {kind} {name}  ({refs} test refs)")

    header = f"\nDEAD TYPE EXPORTS ({len(dead_type)})"
    print(header + ("" if verbose else " - pass --verbose to list"))
    if verbose:
        for rel, line, name, kind, _ in dead_type[:max_rows]:
            print(f"  {rel}:{line}  {kind} {name}")

    if dupes:
        print(
            f"\nNOTE: {len(dupes)} symbol name(s) declared in more than one file - "
            "reference counts are shared, confirm before deleting"
        )

    print(
        "\nTextual match only: barrels and dynamic access are not followed. "
        "Treat every row as a candidate, not a verdict."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Find exported symbols with no references outside their file."
    )
    ap.add_argument("repo_root")
    ap.add_argument(
        "--src",
        default="",
        help="only emit export declarations under this subdirectory, e.g. src",
    )
    ap.add_argument("--max", type=int, default=200, help="max rows per bucket")
    ap.add_argument(
        "--verbose", action="store_true", help="also list dead type exports"
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--ext",
        default="",
        help="comma-separated extensions to override the default set",
    )
    args = ap.parse_args(argv)

    if args.max < 0:
        print("--max must be >= 0", file=sys.stderr)
        return 2

    root = os.path.abspath(args.repo_root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    ext_filter = DEFAULT_EXTS
    if args.ext:
        ext_filter = tuple(
            e if e.startswith(".") else f".{e}"
            for e in args.ext.split(",")
            if e.strip()
        )

    texts = collect(root, ext_filter)
    src_filter = args.src.replace("/", os.sep)
    if not texts or (
        src_filter and not any(_in_src_scope(rel, src_filter) for rel in texts)
    ):
        print("no matching files found", file=sys.stderr)
        return 2

    summary = analyze_exports(texts, src_filter=src_filter)
    if args.json:
        payload = {
            "repo_root": root,
            "src_filter": args.src,
            "files_scanned": summary["files_scanned"],
            "source_files_scanned": summary["source_files_scanned"],
            "distinct_exports": summary["distinct_exports"],
            "dead_value_exports": [
                _row_to_dict(r) for r in summary["dead_value"][: args.max]
            ],
            "test_only_exports": [
                _row_to_dict(r) for r in summary["test_only"][: args.max]
            ],
            "dead_type_exports": [
                _row_to_dict(r) for r in summary["dead_type"][: args.max]
            ],
            "duplicate_export_names": summary["duplicates"],
        }
        print(json.dumps(payload, indent=2))
        return 0

    _print_text_report(summary, max_rows=args.max, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
