#!/usr/bin/env python3
"""preflight_telemetry.py (v3.0.0) — Surgical Audit polyglot static scanner.

Zero-mutation, read-only repository telemetry for the surgical-audit skill.
Scans a target directory and emits:
  * tree_integrity_sha256  — pre-audit state digest (Merkle-style over sorted
                             file paths + contents, build/vendor dirs pruned)
  * skipped_dirs_count     — count of pruned vendor/build/cache directories
  * effective LOC per file (excluding comments and Python docstrings)
  * per-function Cyclomatic Complexity (CC) & control-flow/brace nesting depth
  * God-file flags (>400 effective LOC), high-complexity functions,
    silent catch blocks, hot-loop allocation markers
  * Risk-ranked hotspot list:
        Risk = LOC_effective * (1 + BranchDensity) + 50 * N_silent_catches
  * Optional OASIS SARIF 2.1.0 output via `--sarif`

Usage:
    python3 preflight_telemetry.py <target_dir> [--out report.json] [--sarif]

All operations are read-only. No file under target_dir is ever created,
edited, or deleted.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import re
import sys
import tokenize
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "3.0.0"
SARIF_SCHEMA_URL = "https://json.schemastore.org/sarif-2.1.0.json"

GOD_FILE_LOC = 400
HIGH_CC_THRESHOLD = 10
BRACE_DEPTH_THRESHOLD = 5
HOT_LOC_THRESHOLD = 60
MAX_COMPLEXITY_SPANS = 50

PRUNE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        ".next",
        ".turbo",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "venv",
        ".venv",
        "target",
        "vendor",
        ".svelte-kit",
        ".nuxt",
        "coverage",
        "out",
        ".cache",
        "storybook-static",
    }
)

PYTHON_EXTENSIONS: frozenset[str] = frozenset({".py", ".pyw"})

BRACE_EXTENSIONS: frozenset[str] = frozenset(
    {
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
        ".cs",
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
    }
)

CODE_EXTENSIONS: frozenset[str] = (
    PYTHON_EXTENSIONS | BRACE_EXTENSIONS | frozenset({".gd", ".lua", ".sh"})
)

BRANCH_KEYWORDS = re.compile(
    r"\b(?:if|elif|for|while|match|case|catch|except|and|or)\b"
)
BRANCH_OPERATORS = re.compile(r"(?<!\?)\?(?![.:?])|\?\?|&&|\|\|")

POLYGLOT_FUNC_REGEX = re.compile(
    r"(?:(?:async\s+)?(?:function\s*\*?\s+|def\s+|func\s+|fn\s+|sub\s+)"
    r"([A-Za-z_$][A-Za-z0-9_$]*)(?:<[^>]*>)?\s*[\((]"
    r"|(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
    r"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>)"
)

_CONTROL_FLOW_NODES: tuple[type[ast.AST], ...] = tuple(
    node_cls
    for node_cls in (
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
        getattr(ast, "Match", None),
        getattr(ast, "TryStar", None),
    )
    if node_cls is not None
)

_CC_SIMPLE_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
)

_MATCH_CASE_TYPE: type[ast.AST] | None = getattr(ast, "MatchCase", None)

_HOT_LOOP_UNCOND = re.compile(
    r"\b(?:requestAnimationFrame|_process|FixedUpdate|LateUpdate|Update|onDraw|render)"
    r"\s*\(|\bnew\s+(?:Vector[234]|Color|Quaternion|Matrix[34])\b",
    re.IGNORECASE,
)
_HOT_LOOP_GATED = re.compile(r"\.(?:map|filter|forEach)\s*\(", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Hashing / repository traversal
# ---------------------------------------------------------------------------


def sha256_file(path: str) -> str:
    """Return the SHA-256 hex digest of a file using streaming 64 KiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _walk_repository(root: str) -> tuple[str, int, list[tuple[str, str]]]:
    """Single read-only pass returning (tree_sha256, skipped_dirs, code_files)."""
    root_abs = os.path.abspath(root)
    entries: list[str] = []
    code_files: list[tuple[str, str]] = []
    skipped_dirs_count = 0

    for dirpath, dirnames, filenames in os.walk(root_abs, followlinks=False):
        skipped_dirs_count += sum(1 for d in dirnames if d in PRUNE_DIRS)
        dirnames[:] = sorted(d for d in dirnames if d not in PRUNE_DIRS)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root_abs).replace(os.sep, "/")
            if os.path.islink(full):
                try:
                    target = os.readlink(full)
                except OSError:
                    continue
                entries.append(f"{rel}\0symlink:{target}")
                continue
            try:
                digest = sha256_file(full)
            except OSError:
                continue
            entries.append(f"{rel}\0{digest}")
            if os.path.splitext(name)[1].lower() in CODE_EXTENSIONS:
                code_files.append((rel, full))

    entries.sort()
    combined = "\n".join(entries).encode("utf-8")
    return hashlib.sha256(combined).hexdigest(), skipped_dirs_count, code_files


def compute_tree_integrity_sha256(root: str) -> str:
    """Merkle-style digest: sha256 over sorted 'relpath\\0sha256' lines."""
    digest, _, _ = _walk_repository(root)
    return digest


# ---------------------------------------------------------------------------
# Comment & string masking (line-number preserving)
# ---------------------------------------------------------------------------


def _consume_quoted(
    source: str,
    start: int,
    quote: str,
    *,
    mask_strings: bool,
) -> tuple[list[str], int]:
    """Consume a quoted literal (or template string) preserving newlines."""
    n = len(source)
    out: list[str] = [quote if not mask_strings else " "]
    i = start + 1
    while i < n:
        ch = source[i]
        if ch == "\\":
            nxt = source[i + 1] if i + 1 < n else ""
            if mask_strings:
                out.append(" ")
                if nxt:
                    out.append("\n" if nxt == "\n" else " ")
            else:
                out.append(ch)
                if nxt:
                    out.append(nxt)
            i += 2 if nxt else 1
            continue
        if ch == quote:
            out.append(quote if not mask_strings else " ")
            return out, i + 1
        out.append("\n" if ch == "\n" else (" " if mask_strings else ch))
        i += 1
    return out, i


_REGEX_PREFIX_CHARS = frozenset("(,=:[!&|?{};+-*%~^<>")
_REGEX_KEYWORD_RE = re.compile(
    r"\b(?:return|case|throw|in|of|typeof|void|delete|await|yield|new|else|do|"
    r"export|default)\s*$"
)


def _regex_can_start(prev: str, source: str, i: int) -> bool:
    """Disambiguate a regex literal from division using the preceding token."""
    if prev == "":
        return True
    if prev in ("string", "regex"):
        return False
    if prev in _REGEX_PREFIX_CHARS:
        return not (prev in "+-" and i >= 2 and source[i - 2] == prev)
    if prev in ")]" or prev.isalnum() or prev in "_$":
        return bool(_REGEX_KEYWORD_RE.search(source[max(0, i - 16) : i]))
    return False


def _consume_regex(
    source: str, start: int, *, mask_strings: bool
) -> tuple[list[str], int]:
    """Consume a /.../flags regex literal, honouring [...] character classes."""
    out = [" " if mask_strings else "/"]
    i = start + 1
    n = len(source)
    in_class = False
    while i < n:
        ch = source[i]
        if ch == "\\":
            nxt = source[i + 1] if i + 1 < n else ""
            out.append(" " if mask_strings else ch)
            if nxt:
                out.append("\n" if nxt == "\n" else (" " if mask_strings else nxt))
            i += 2 if nxt else 1
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            out.append(" " if mask_strings else "/")
            i += 1
            while i < n and source[i].isalpha():
                out.append(" " if mask_strings else source[i])
                i += 1
            return out, i
        if ch == "\n":
            out.append("\n")
            return out, i + 1
        out.append(" " if mask_strings else ch)
        i += 1
    return out, i


def _consume_template(
    source: str, start: int, *, mask_strings: bool
) -> tuple[list[str], int]:
    """Mask static template text while preserving ${...} code expressions."""
    out = [" " if mask_strings else "`"]
    i = start + 1
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "\\":
            nxt = source[i + 1] if i + 1 < n else ""
            out.append(" " if mask_strings else ch)
            if nxt:
                out.append("\n" if nxt == "\n" else (" " if mask_strings else nxt))
            i += 2 if nxt else 1
            continue
        if ch == "`":
            out.append(" " if mask_strings else "`")
            return out, i + 1
        if ch == "$" and i + 1 < n and source[i + 1] == "{":
            out.extend(("$", "{"))
            expr, i = _mask_c_segment(
                source, i + 2, mask_strings=mask_strings, stop_on_rbrace=True
            )
            out.extend(expr)
            continue
        out.append("\n" if ch == "\n" else (" " if mask_strings else ch))
        i += 1
    return out, i


def _consume_c_comment(source: str, i: int) -> tuple[list[str], int] | None:
    """Consume a // or /* */ comment at i, or return None when not a comment."""
    n = len(source)
    nxt = source[i + 1] if i + 1 < n else ""
    if source[i] == "/" and nxt == "/":
        line_out: list[str] = []
        while i < n and source[i] != "\n":
            line_out.append(" ")
            i += 1
        return line_out, i
    if source[i] == "/" and nxt == "*":
        block_out: list[str] = [" ", " "]
        i += 2
        while i < n:
            if source[i] == "*" and i + 1 < n and source[i + 1] == "/":
                block_out.extend((" ", " "))
                i += 2
                break
            block_out.append("\n" if source[i] == "\n" else " ")
            i += 1
        return block_out, i
    return None


def _consume_c_literal(
    source: str, i: int, ch: str, prev: str, *, mask_strings: bool
) -> tuple[list[str], int, str] | None:
    """Consume a regex/quote/template literal at i, returning (out, i, prev)."""
    if ch == "/" and _regex_can_start(prev, source, i):
        regex_out, j = _consume_regex(source, i, mask_strings=mask_strings)
        return regex_out, j, "regex"
    if ch in ("'", '"'):
        quote_out, j = _consume_quoted(source, i, ch, mask_strings=mask_strings)
        return quote_out, j, "string"
    if ch == "`":
        tpl_out, j = _consume_template(source, i, mask_strings=mask_strings)
        return tpl_out, j, "string"
    return None


def _mask_c_segment(
    source: str,
    start: int,
    *,
    mask_strings: bool,
    stop_on_rbrace: bool = False,
) -> tuple[list[str], int]:
    """Mask C-style comments/strings/regex/templates, preserving line numbers."""
    out: list[str] = []
    i = start
    n = len(source)
    brace_depth = int(stop_on_rbrace)
    prev = ""
    while i < n:
        ch = source[i]
        if stop_on_rbrace and ch in ("{", "}"):
            brace_depth += 1 if ch == "{" else -1
            out.append(ch)
            prev = ch
            i += 1
            if brace_depth == 0:
                return out, i
            continue
        comment = _consume_c_comment(source, i)
        if comment is not None:
            chunk, i = comment
            out.extend(chunk)
            continue
        literal = _consume_c_literal(source, i, ch, prev, mask_strings=mask_strings)
        if literal is not None:
            chunk, i, prev = literal
            out.extend(chunk)
            continue
        out.append(ch)
        if not ch.isspace():
            prev = ch
        i += 1
    return out, i


def _strip_c_style(source: str, *, mask_strings: bool) -> str:
    """Strip // and /* */ comments, strings, regex and templates keeping newlines."""
    out, _ = _mask_c_segment(source, 0, mask_strings=mask_strings)
    return "".join(out)


def _strip_hash_or_lua(
    source: str,
    line_prefix: str,
    *,
    mask_strings: bool,
) -> str:
    """Strip single-line prefix comments (# or --) while preserving newlines."""
    out: list[str] = []
    i = 0
    n = len(source)
    plen = len(line_prefix)
    while i < n:
        ch = source[i]
        if source.startswith(line_prefix, i):
            out.extend([" "] * plen)
            i += plen
            while i < n and source[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if ch in ("'", '"'):
            chunk, i = _consume_quoted(source, i, ch, mask_strings=mask_strings)
            out.extend(chunk)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_python_tokens(source: str) -> str:
    """Replace Python comments and string literal payloads with spaces."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError):
        return source
    lines = source.splitlines(keepends=True)
    grid = [list(line) for line in lines]
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        s_row, s_col = tok.start
        e_row, e_col = tok.end
        for row_idx in range(s_row - 1, min(e_row, len(grid))):
            row = grid[row_idx]
            col_start = s_col if row_idx == s_row - 1 else 0
            col_end = e_col if row_idx == e_row - 1 else len(row)
            for col_idx in range(col_start, min(col_end, len(row))):
                if row[col_idx] not in ("\n", "\r"):
                    row[col_idx] = " "
    return "".join("".join(row) for row in grid)


_SFC_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
SFC_EXTENSIONS: frozenset[str] = frozenset({".svelte", ".vue"})


def _mask_keep_newlines(text: str) -> str:
    """Replace every character with a space except newlines (line-preserving)."""
    return "".join("\n" if ch == "\n" else " " for ch in text)


def _extract_sfc_scripts(source: str) -> str:
    """Isolate <script> blocks in .svelte/.vue, masking markup/CSS outside them."""
    out: list[str] = []
    last = 0
    for match in _SFC_SCRIPT_RE.finditer(source):
        out.append(_mask_keep_newlines(source[last : match.start(1)]))
        out.append(match.group(1))
        last = match.end(1)
    out.append(_mask_keep_newlines(source[last:]))
    return "".join(out)


def strip_comments(source: str, ext: str) -> str:
    """Strip comments for the given extension while keeping line numbers."""
    if ext in PYTHON_EXTENSIONS:
        return source
    if ext in (".gd", ".sh"):
        return _strip_hash_or_lua(source, "#", mask_strings=False)
    if ext == ".lua":
        return _strip_hash_or_lua(source, "--", mask_strings=False)
    if ext in SFC_EXTENSIONS:
        source = _extract_sfc_scripts(source)
    return _strip_c_style(source, mask_strings=False)


def strip_comments_and_strings(source: str, ext: str) -> str:
    """Strip comments and string literals while keeping line numbers."""
    if ext in PYTHON_EXTENSIONS:
        return _strip_python_tokens(source)
    if ext in (".gd", ".sh"):
        return _strip_hash_or_lua(source, "#", mask_strings=True)
    if ext == ".lua":
        return _strip_hash_or_lua(source, "--", mask_strings=True)
    if ext in SFC_EXTENSIONS:
        source = _extract_sfc_scripts(source)
    return _strip_c_style(source, mask_strings=True)


# ---------------------------------------------------------------------------
# LOC, silent catches, and hot-loop metrics
# ---------------------------------------------------------------------------


def _python_docstring_lines(source: str) -> set[int]:
    """Return 1-based line numbers belonging to module/class/func docstrings."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    doc_lines: set[int] = set()
    scoped = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, scoped) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = first.end_lineno if first.end_lineno is not None else first.lineno
            doc_lines |= set(range(first.lineno, end + 1))
    return doc_lines


def effective_loc(source: str, ext: str) -> int:
    """Count non-blank lines that are not solely comments or Python docstrings."""
    if ext in PYTHON_EXTENSIONS:
        doc_lines = _python_docstring_lines(source)
        count = 0
        for idx, raw in enumerate(source.splitlines(), start=1):
            if idx in doc_lines:
                continue
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            count += 1
        return count

    cleaned = strip_comments(source, ext)
    return sum(1 for raw in cleaned.splitlines() if raw.strip())


def _is_noop_stmt(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return stmt.value.value is ... or isinstance(stmt.value.value, str)
    return False


def _python_silent_catch_lines_fallback(source: str) -> list[int]:
    pattern = re.compile(
        r"^\s*except(?:\s+[^:\n]+)?\s*:\s*(?:pass|\.\.\.)?\s*(?:#.*)?$",
        re.MULTILINE,
    )
    lines = source.splitlines()
    found: list[int] = []
    for match in pattern.finditer(source):
        matched_text = match.group(0).strip()
        line_idx = source[: match.start()].count("\n")
        if matched_text.endswith(("pass", "...")):
            found.append(line_idx + 1)
            continue
        nxt = lines[line_idx + 1].strip() if line_idx + 1 < len(lines) else ""
        if nxt in ("pass", "...", "") or nxt.startswith("#"):
            found.append(line_idx + 1)
    return found


def silent_catch_lines(source: str, ext: str) -> list[int]:
    """Return 1-based line numbers of empty or no-op exception handlers."""
    if ext in PYTHON_EXTENSIONS:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return _python_silent_catch_lines_fallback(source)
        return sorted(
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and all(_is_noop_stmt(stmt) for stmt in node.body)
        )
    cleaned = strip_comments(source, ext)
    return sorted(
        cleaned[: m.start()].count("\n") + 1
        for m in re.finditer(r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}", cleaned)
    )


def silent_catches(source: str, ext: str) -> int:
    """Count empty or no-op exception handlers."""
    return len(silent_catch_lines(source, ext))


def _hot_loop_hits(source: str, ext: str) -> list[int]:
    """Return 1-based hot-loop marker lines; gated callbacks require a loop."""
    cleaned = strip_comments_and_strings(source, ext)
    uncond = list(_HOT_LOOP_UNCOND.finditer(cleaned))
    hits = [cleaned[: m.start()].count("\n") + 1 for m in uncond]
    if uncond:
        hits.extend(
            cleaned[: m.start()].count("\n") + 1
            for m in _HOT_LOOP_GATED.finditer(cleaned)
        )
    return sorted(hits)


def hot_loop_markers(source: str, ext: str) -> int:
    """Count per-frame / hot-loop allocation markers outside comments/strings."""
    return len(_hot_loop_hits(source, ext))


def hot_loop_lines(source: str, ext: str) -> list[int]:
    """Return 1-based line numbers of hot-loop allocation markers."""
    return _hot_loop_hits(source, ext)


def count_polyglot_branches(snippet: str) -> int:
    """Count keyword branches and non-word operator branches separately."""
    return len(BRANCH_KEYWORDS.findall(snippet)) + len(
        BRANCH_OPERATORS.findall(snippet)
    )


# ---------------------------------------------------------------------------
# Python AST complexity & control-flow nesting
# ---------------------------------------------------------------------------


class DepthCounter(ast.NodeVisitor):
    """Measure maximum control-flow nesting depth in a Python AST."""

    def __init__(self) -> None:
        self.depth = 0
        self.max_depth = 0

    def _enter_block(self, node: ast.AST) -> None:
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        super().generic_visit(node)
        self.depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        curr: ast.If | None = node
        while curr is not None:
            self.visit(curr.test)
            for stmt in curr.body:
                self.visit(stmt)
            if (
                len(curr.orelse) == 1
                and isinstance(curr.orelse[0], ast.If)
                and curr.orelse[0].col_offset == curr.col_offset
            ):
                curr = curr.orelse[0]
            else:
                for stmt in curr.orelse:
                    self.visit(stmt)
                curr = None
        self.depth -= 1

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _CONTROL_FLOW_NODES):
            self._enter_block(node)
            return
        super().generic_visit(node)


def _node_cc_increment(node: ast.AST) -> int:
    if isinstance(node, _CC_SIMPLE_NODES):
        return 1
    if isinstance(node, ast.BoolOp):
        return max(1, len(node.values) - 1)
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    if _MATCH_CASE_TYPE is not None and isinstance(node, _MATCH_CASE_TYPE):
        return 1
    return 0


def _compute_python_function_cc(
    fn_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    """Compute CC strictly from fn_node's own subtree, ignoring nested defs."""
    cc = 1
    stack: list[ast.AST] = list(ast.iter_child_nodes(fn_node))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        cc += _node_cc_increment(node)
        stack.extend(ast.iter_child_nodes(node))
    return cc


def analyze_python(source: str) -> dict[str, Any]:
    """Analyze Python AST for per-function CC, nesting depth, and span LOC."""
    result: dict[str, Any] = {
        "cc": 1,
        "max_nesting": 0,
        "max_func_loc": 0,
        "functions": [],
        "parse_error": None,
    }
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        result["parse_error"] = str(exc)
        return result

    counter = DepthCounter()
    counter.visit(tree)

    functions: list[dict[str, Any]] = []
    max_cc = 1
    max_func_loc = 0
    fn_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    fn_nodes.sort(key=lambda n: (n.lineno, n.col_offset))

    for node in fn_nodes:
        cc = _compute_python_function_cc(node)
        end_line = node.end_lineno if node.end_lineno is not None else node.lineno
        fn_loc = max(1, end_line - node.lineno + 1)
        max_cc = max(max_cc, cc)
        max_func_loc = max(max_func_loc, fn_loc)
        functions.append(
            {
                "name": node.name,
                "start_line": node.lineno,
                "end_line": end_line,
                "loc": fn_loc,
                "estimated_cc": cc,
            }
        )

    functions.sort(key=lambda f: (-int(f["estimated_cc"]), int(f["start_line"])))
    result["cc"] = max_cc
    result["max_nesting"] = counter.max_depth
    result["max_func_loc"] = max_func_loc
    result["functions"] = functions[:MAX_COMPLEXITY_SPANS]
    return result


# ---------------------------------------------------------------------------
# Polyglot structural scanner
# ---------------------------------------------------------------------------


def _extract_brace_span(lines: list[str], start_idx: int) -> tuple[int, str]:
    """Extract function body lines from start_idx until matching closing brace."""
    depth = 0
    seen_open = False
    limit = min(len(lines), start_idx + 400)
    for idx in range(start_idx, limit):
        line = lines[idx]
        opens = line.count("{")
        closes = line.count("}")
        if opens > 0:
            seen_open = True
        depth += opens - closes
        if seen_open and depth <= 0:
            return idx, "\n".join(lines[start_idx : idx + 1])
    end_idx = min(len(lines) - 1, start_idx + 119)
    return end_idx, "\n".join(lines[start_idx : end_idx + 1])


def analyze_polyglot_structure(source: str, ext: str = ".ts") -> dict[str, Any]:
    """Brace nesting depth and per-function CC scanner for non-Python files."""
    cleaned = strip_comments_and_strings(source, ext)
    lines = cleaned.splitlines()
    max_nesting = 0
    current_brace_depth = 0
    functions: list[dict[str, Any]] = []

    for line in lines:
        opens = line.count("{")
        closes = line.count("}")
        current_brace_depth = max(0, current_brace_depth + opens - closes)
        max_nesting = max(max_nesting, current_brace_depth)

    matches = list(POLYGLOT_FUNC_REGEX.finditer(cleaned))
    max_cc = 1 + count_polyglot_branches(cleaned) if not matches else 1
    max_func_loc = 0

    for idx, match in enumerate(matches):
        fn_name = match.group(1) or match.group(2) or "<anonymous>"
        start_line = cleaned[: match.start()].count("\n") + 1
        start_idx = start_line - 1
        if ext in BRACE_EXTENSIONS:
            end_idx, snippet = _extract_brace_span(lines, start_idx)
        else:
            next_start = (
                cleaned[: matches[idx + 1].start()].count("\n")
                if idx + 1 < len(matches)
                else len(lines)
            )
            end_idx = min(next_start - 1, start_idx + 119)
            snippet = "\n".join(lines[start_idx : end_idx + 1])
        fn_loc = max(1, end_idx - start_idx + 1)
        cc_est = 1 + count_polyglot_branches(snippet)
        max_cc = max(max_cc, cc_est)
        max_func_loc = max(max_func_loc, fn_loc)
        functions.append(
            {
                "name": fn_name,
                "start_line": start_line,
                "end_line": end_idx + 1,
                "loc": fn_loc,
                "estimated_cc_window": cc_est,
            }
        )

    functions.sort(key=lambda f: (-int(f["estimated_cc_window"]), int(f["start_line"])))
    return {
        "cc": max_cc,
        "max_brace_nesting_depth": max_nesting,
        "max_func_loc": max_func_loc,
        "high_complexity_functions": functions[:MAX_COMPLEXITY_SPANS],
    }


# ---------------------------------------------------------------------------
# Per-file & directory scanning
# ---------------------------------------------------------------------------


def scan_file(path: str) -> dict[str, Any]:
    """Scan a single source file and compute complexity/risk telemetry."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in CODE_EXTENSIONS:
        return {"skipped": True, "reason": "non-code extension"}

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError as exc:
        return {"skipped": True, "reason": str(exc)}

    loc = effective_loc(source, ext)
    catch_lines = silent_catch_lines(source, ext)
    hot_lines = hot_loop_lines(source, ext)
    catches = len(catch_lines)
    hot = len(hot_lines)

    if ext in PYTHON_EXTENSIONS:
        py = analyze_python(source)
        cc = int(py["cc"])
        nesting = int(py["max_nesting"])
        max_func_loc = int(py["max_func_loc"])
        funcs = py["functions"]
        parse_error = py["parse_error"]
    else:
        poly = analyze_polyglot_structure(source, ext)
        cc = int(poly["cc"])
        nesting = int(poly["max_brace_nesting_depth"])
        max_func_loc = int(poly["max_func_loc"])
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
        "max_function_loc": max_func_loc,
        "silent_catches": catches,
        "hot_loop_markers": hot,
        "silent_catch_lines": catch_lines,
        "hot_loop_lines": hot_lines,
        "branch_density": round(branch_density, 4),
        "risk_score": round(risk, 2),
        "high_complexity_functions": funcs,
        "parse_error": parse_error,
        "god_file": loc > GOD_FILE_LOC,
        "high_complexity": (
            cc >= HIGH_CC_THRESHOLD
            or nesting > BRACE_DEPTH_THRESHOLD
            or max_func_loc >= HOT_LOC_THRESHOLD
        ),
    }


def scan_directory(target_dir: str) -> dict[str, Any]:
    """Scan target_dir read-only and return repository telemetry."""
    target_abs = os.path.abspath(target_dir)
    if not os.path.isdir(target_abs):
        raise SystemExit(f"[preflight_telemetry] not a directory: {target_abs}")

    tree_hash, skipped_dirs_count, code_files = _walk_repository(target_abs)
    records: list[dict[str, Any]] = []
    total_loc = 0
    total_files = 0

    for rel, full in code_files:
        record = scan_file(full)
        if record.get("skipped"):
            continue
        record["path"] = rel
        total_loc += int(record["effective_loc"])
        total_files += 1
        records.append(record)

    records.sort(key=lambda r: float(r["risk_score"]), reverse=True)

    return {
        "target_dir": target_abs,
        "tree_integrity_sha256": tree_hash,
        "skipped_dirs_count": skipped_dirs_count,
        "files_scanned": total_files,
        "effective_loc_total": total_loc,
        "risk_formula": ("LOC_effective * (1 + BranchDensity) + 50 * N_silent_catches"),
        "god_files": [r["path"] for r in records if r["god_file"]],
        "high_complexity_files": [r["path"] for r in records if r["high_complexity"]],
        "files": records,
    }


# ---------------------------------------------------------------------------
# SARIF 2.1.0 emitter
# ---------------------------------------------------------------------------

_SARIF_RULES: list[dict[str, Any]] = [
    {
        "id": "SA-GOD-FILE",
        "name": "GodFileThresholdExceeded",
        "shortDescription": {
            "text": f"File exceeds {GOD_FILE_LOC} effective lines of code"
        },
        "defaultConfiguration": {"level": "warning"},
    },
    {
        "id": "SA-HIGH-COMPLEXITY",
        "name": "HighComplexityHotspot",
        "shortDescription": {
            "text": (
                f"Function or file exceeds complexity (CC >= {HIGH_CC_THRESHOLD}), "
                f"nesting (> {BRACE_DEPTH_THRESHOLD}), or span LOC "
                f"(>= {HOT_LOC_THRESHOLD})"
            )
        },
        "defaultConfiguration": {"level": "warning"},
    },
    {
        "id": "SA-SILENT-CATCH",
        "name": "SilentExceptionHandler",
        "shortDescription": {
            "text": "Empty or pass-only exception catch handler swallows errors"
        },
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "SA-HOT-LOOP",
        "name": "HotLoopAllocationMarker",
        "shortDescription": {
            "text": "Per-frame or hot-loop allocation/callback marker detected"
        },
        "defaultConfiguration": {"level": "note"},
    },
    {
        "id": "SA-PARSE-ERROR",
        "name": "SyntaxParseError",
        "shortDescription": {"text": "Syntax error prevented full AST inspection"},
        "defaultConfiguration": {"level": "error"},
    },
]

_RULE_INDEX: dict[str, int] = {rule["id"]: idx for idx, rule in enumerate(_SARIF_RULES)}


def _sarif_result(
    rule_id: str,
    level: str,
    message: str,
    rel_path: str,
    start_line: int = 1,
    properties: dict[str, Any] | None = None,
    end_line: int | None = None,
) -> dict[str, Any]:
    region: dict[str, Any] = {"startLine": max(1, start_line)}
    if end_line is not None:
        region["endLine"] = max(region["startLine"], end_line)
    item: dict[str, Any] = {
        "ruleId": rule_id,
        "ruleIndex": _RULE_INDEX[rule_id],
        "level": level,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": rel_path,
                        "uriBaseId": "%SRCROOT%",
                    },
                    "region": region,
                }
            }
        ],
    }
    if properties:
        item["properties"] = properties
    return item


def _fn_cc(fn: dict[str, Any]) -> int:
    """Read a function span's CC regardless of Python/polyglot field naming."""
    return int(fn.get("estimated_cc", fn.get("estimated_cc_window", 1)))


def _complexity_sarif_results(record: dict[str, Any], rel: str) -> list[dict[str, Any]]:
    """Emit SA-HIGH-COMPLEXITY with exact per-function start/end line spans."""
    if not record.get("high_complexity"):
        return []
    props = {
        "cyclomatic_complexity": record["cyclomatic_complexity"],
        "nesting_depth": record["nesting_depth"],
        "max_function_loc": record["max_function_loc"],
    }
    funcs = record.get("high_complexity_functions") or []
    hot_funcs = [
        f
        for f in funcs
        if _fn_cc(f) >= HIGH_CC_THRESHOLD or int(f["loc"]) >= HOT_LOC_THRESHOLD
    ]
    if hot_funcs:
        return [
            _sarif_result(
                "SA-HIGH-COMPLEXITY",
                "warning",
                f"{rel}:{f['start_line']} {f['name']} exceeds complexity thresholds.",
                rel,
                start_line=int(f["start_line"]),
                end_line=int(f["end_line"]),
                properties=props,
            )
            for f in hot_funcs
        ]
    top_line = int(funcs[0]["start_line"]) if funcs else 1
    cc_val = record["cyclomatic_complexity"]
    return [
        _sarif_result(
            "SA-HIGH-COMPLEXITY",
            "warning",
            (
                f"{rel} flagged for complexity (CC={cc_val}, "
                f"nesting={record['nesting_depth']}, "
                f"max_function_loc={record['max_function_loc']})."
            ),
            rel,
            start_line=top_line,
            properties=props,
        )
    ]


def _marker_sarif_results(
    record: dict[str, Any],
    rel: str,
    lines_key: str,
    count_key: str,
    rule_id: str,
    level: str,
    label: str,
) -> list[dict[str, Any]]:
    """Emit one SARIF result per exact line, falling back to an aggregate."""
    lines = record.get(lines_key) or []
    if lines:
        return [
            _sarif_result(
                rule_id, level, f"{rel}:{line} {label}.", rel, start_line=int(line)
            )
            for line in lines
        ]
    count = int(record.get(count_key, 0))
    if count > 0:
        return [
            _sarif_result(
                rule_id,
                level,
                f"{rel} contains {count} {label}(s).",
                rel,
                properties={count_key: count},
            )
        ]
    return []


def _file_sarif_results(record: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    rel = str(record["path"])
    if record.get("parse_error"):
        results.append(
            _sarif_result(
                "SA-PARSE-ERROR",
                "error",
                f"Syntax error in {rel}: {record['parse_error']}",
                rel,
            )
        )
    if record.get("god_file"):
        eff_loc = record["effective_loc"]
        results.append(
            _sarif_result(
                "SA-GOD-FILE",
                "warning",
                f"{rel} has {eff_loc} effective LOC (> {GOD_FILE_LOC}).",
                rel,
                properties={"effective_loc": eff_loc},
            )
        )
    results.extend(_complexity_sarif_results(record, rel))
    results.extend(
        _marker_sarif_results(
            record,
            rel,
            "silent_catch_lines",
            "silent_catches",
            "SA-SILENT-CATCH",
            "error",
            "silent catch handler swallows errors",
        )
    )
    results.extend(
        _marker_sarif_results(
            record,
            rel,
            "hot_loop_lines",
            "hot_loop_markers",
            "SA-HOT-LOOP",
            "note",
            "hot-loop allocation/callback marker",
        )
    )
    return results


def build_sarif_report(report: dict[str, Any]) -> dict[str, Any]:
    """Convert a telemetry scan report to OASIS SARIF 2.1.0 JSON."""
    results: list[dict[str, Any]] = []
    for record in report.get("files", []):
        results.extend(_file_sarif_results(record))

    return {
        "$schema": SARIF_SCHEMA_URL,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "surgical-audit-preflight",
                        "version": VERSION,
                        "informationUri": "https://github.com/TeacherEvan/surgical-audit",
                        "rules": _SARIF_RULES,
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "properties": {
                            "tree_integrity_sha256": report["tree_integrity_sha256"],
                            "skipped_dirs_count": report["skipped_dirs_count"],
                            "files_scanned": report["files_scanned"],
                            "effective_loc_total": report["effective_loc_total"],
                        },
                    }
                ],
                "results": results,
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Surgical Audit preflight telemetry scanner (read-only)."
    )
    parser.add_argument("target_dir", help="Directory to scan")
    parser.add_argument(
        "--out",
        help="Write JSON/SARIF report to this path (default: print to stdout)",
    )
    parser.add_argument(
        "--sarif",
        action="store_true",
        help="Emit OASIS SARIF 2.1.0 JSON instead of raw telemetry JSON",
    )
    parser.add_argument(
        "--format",
        choices=("json", "sarif"),
        default="json",
        help="Output format (default: json; overridden by --sarif)",
    )
    args = parser.parse_args(argv)

    report = scan_directory(args.target_dir)
    emit_sarif = args.sarif or args.format == "sarif"
    output_obj = build_sarif_report(report) if emit_sarif else report
    payload = json.dumps(output_obj, indent=2)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
        print(f"[preflight_telemetry] wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
