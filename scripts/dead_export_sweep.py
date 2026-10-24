#!/usr/bin/env python3
"""Dead-export sweep: find exported symbols that nothing else references.

Usage:
    python3 dead_export_sweep.py <repo_root> [--src DIR] [--max N] [--verbose]

Buckets
-------
DEAD VALUE   exported const/let/var/function/class/enum with zero references
             outside its own file  -> delete it, or wire it up
TEST-ONLY    referenced only by test files: the suite is green and the app
             never calls it  -> invisible debt masquerading as coverage
DEAD TYPE    interface/type with zero references -> usually noise in TS,
             counted separately and only listed with --verbose

Why this exists
---------------
In AI-maintained repos the most expensive debt is content that exists,
type-checks and is exported, yet is connected to nothing. A whole feature
module can carry a green test suite and still be unreachable from the app.
Coverage tooling reports those lines as "uncovered" rather than "unreachable",
so nothing ever flags them. This sweep does.

Limits (state these in the audit report)
----------------------------------------
* Textual matching, not a real AST or module graph. A symbol reached only via
  `export *` barrels or dynamic property access counts as dead unless some
  consumer names it.
* Name shadowing inflates the reference count, so treat output as candidates to
  confirm with `grep -rn "<symbol>" src/ tests/ e2e/`, never as a delete list.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

PRUNE = {
    "node_modules", ".git", "dist", "build", ".next", "out", "coverage",
    "vendor", ".venv", "venv", "__pycache__", "target", ".turbo", ".cache",
    ".svelte-kit", ".nuxt", "storybook-static",
}
DEFAULT_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".svelte", ".vue")

DECL_RE = re.compile(
    r"^[ \t]*export[ \t]+(?:declare[ \t]+)?(?:default[ \t]+)?"
    r"(?P<kind>const|let|var|function|class|enum|interface|type|abstract[ \t]+class)"
    r"[ \t]+(?:async[ \t]+)?(?P<name>[A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
TEST_FILE_RE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$")
TEST_DIR_PARTS = {"__tests__", "__mocks__", "tests", "test", "e2e", "spec", "cypress"}


def is_test_path(path: str) -> bool:
    parts = path.replace(os.sep, "/").split("/")
    return bool(TEST_FILE_RE.search(path)) or bool(TEST_DIR_PARTS & set(parts))


def collect(root: str, ext_filter: tuple[str, ...], src_filter: str) -> dict[str, str]:
    texts: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in PRUNE and not d.startswith(".")
        )
        for fn in filenames:
            if not fn.endswith(ext_filter):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if src_filter and not (
                rel == src_filter or rel.startswith(src_filter + os.sep)
            ):
                continue
            try:
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    texts[rel] = fh.read()
            except OSError:
                continue
    return texts


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Find exported symbols with no references outside their file."
    )
    ap.add_argument("repo_root")
    ap.add_argument("--src", default="", help="only scan this subdirectory, e.g. src")
    ap.add_argument("--max", type=int, default=200, help="max rows per bucket")
    ap.add_argument("--verbose", action="store_true", help="also list dead type exports")
    ap.add_argument(
        "--ext",
        default="",
        help="comma-separated extensions to override the default set",
    )
    args = ap.parse_args()

    root = os.path.abspath(args.repo_root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    ext_filter = DEFAULT_EXTS
    if args.ext:
        ext_filter = tuple(
            e if e.startswith(".") else "." + e for e in args.ext.split(",") if e.strip()
        )

    texts = collect(root, ext_filter, args.src.replace("/", os.sep))
    if not texts:
        print("no matching files found", file=sys.stderr)
        return 2

    code_tokens: Counter[str] = Counter()
    test_tokens: Counter[str] = Counter()
    for rel, text in texts.items():
        target = test_tokens if is_test_path(rel) else code_tokens
        target.update(IDENT_RE.findall(text))

    dead_value: list[tuple] = []
    test_only: list[tuple] = []
    dead_type: list[tuple] = []
    seen: dict[str, list[str]] = defaultdict(list)

    for rel, text in texts.items():
        if is_test_path(rel):
            continue
        for match in DECL_RE.finditer(text):
            name = match.group("name")
            kind = "class" if match.group("kind").startswith("abstract") else match.group("kind")
            seen[name].append(rel)
            own = len(re.findall(r"(?<![\w$])%s(?![\w$])" % re.escape(name), text))
            code_refs = code_tokens.get(name, 0) - own
            test_refs = test_tokens.get(name, 0)
            if code_refs > 0:
                continue
            line = text.count("\n", 0, match.start()) + 1
            row = (rel, line, name, kind, test_refs)
            if test_refs > 0:
                test_only.append(row)
            elif kind in ("interface", "type"):
                dead_type.append(row)
            else:
                dead_value.append(row)

    total = len(seen)
    print(f"scanned {len(texts)} files, {total} distinct export declarations\n")

    print(f"DEAD VALUE EXPORTS ({len(dead_value)}) - zero references outside their own file")
    for rel, line, name, kind, _ in sorted(dead_value)[: args.max]:
        print(f"  {rel}:{line}  {kind} {name}")

    print(f"\nTEST-ONLY EXPORTS ({len(test_only)}) - referenced only by tests")
    for rel, line, name, kind, refs in sorted(test_only)[: args.max]:
        print(f"  {rel}:{line}  {kind} {name}  ({refs} test refs)")

    header = f"\nDEAD TYPE EXPORTS ({len(dead_type)})"
    print(header + ("" if args.verbose else " - pass --verbose to list"))
    if args.verbose:
        for rel, line, name, kind, _ in sorted(dead_type)[: args.max]:
            print(f"  {rel}:{line}  {kind} {name}")

    dupes = {n: p for n, p in seen.items() if len(p) > 1}
    if dupes:
        print(
            f"\nNOTE: {len(dupes)} symbol name(s) declared in more than one file - "
            "reference counts are shared, confirm before deleting"
        )

    print(
        "\nTextual match only: barrels and dynamic access are not followed. "
        "Treat every row as a candidate, not a verdict."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
