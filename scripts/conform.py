#!/usr/bin/env python3
"""Conformance gate for an Agent-Surgery skill.

Validates one skill directory against the Hermes authoring standard
(references/skill-authoring-standards.md), including the constraints that
standard distils from the vendor spec but does not itself enforce:

  * description <= 60 chars, starts with "Use when", ends with a period
    (docs/external-research/hermes-agent-skill-spec.md:23)
  * exactly one SKILL.md per skill dir (no nested frontmatter-less copies)
  * bare portable related_skills (^[a-z0-9-]+$, no ':' or '/')
  * every references/*.md, templates/*, and scripts/* named in the body exists on disk

Uses yaml.safe_load when PyYAML is installed, with a zero-dependency fallback
so CI and portable runs work wherever python3 exists.

CANONICAL COPY: Surgical-Investigation/scripts/conform.py
This script is mirrored into each skill repo because the repos are independent
git remotes with no shared tooling. To stop all 7 family repos drifting silently
(the exact failure this family's "Mirrored Installs" rule was written for), each
copy self-checks: it hashes its own bytes with CANONICAL_SHA256 blanked out and
warns if that differs from the pinned value. After editing ANY copy:

    python3 scripts/conform.py --print-digest     # prints the new digest
    # then update CANONICAL_SHA256 in EVERY copy (all 7 family repos must match)

A mismatch is a warning, not a hard failure, so a legitimate in-flight edit in
one repo never blocks unrelated CI in another.

Usage:
    python3 scripts/conform.py [skill_dir]     # default: this skill's root
    python3 scripts/conform.py --print-digest  # emit the self-digest
Exit 0 = conformant, 1 = at least one violation.
"""

from __future__ import annotations

import hashlib
import importlib
import re
import sys
from pathlib import Path

# Blank-out sentinel: the digest excludes this line, so it can be edited
# without invalidating itself. Keep the assignment on ONE line.
CANONICAL_SHA256 = "d33d36aa57008291a7bf2740ccfd98cf0c82fdd1022f8a02700d9264d02ab5b2"

MAX_DESC = 60
MAX_NAME = 64
MAX_SKILL_BYTES = 100_000
REQUIRED_FIELDS = ("name", "description", "version", "author", "license", "platforms")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LOWER_HYPHEN = re.compile(r"^[a-z0-9-]+$")
ASSET_REF = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?:\./)?(references|templates|scripts)/([A-Za-z0-9._*?<>/-]+)"
)
SKIP_SKILL_DIRS = frozenset({"node_modules", ".git", ".venv", "venv"})


def self_digest() -> str:
    """Return sha256 of this file with the CANONICAL_SHA256 value blanked out."""
    text = Path(__file__).read_text(encoding="utf-8")
    masked = re.sub(
        r'^CANONICAL_SHA256 = "[0-9a-f]*"$',
        'CANONICAL_SHA256 = ""',
        text,
        flags=re.MULTILINE,
    )
    return hashlib.sha256(masked.encode("utf-8")).hexdigest()


def mirror_warning() -> str | None:
    """Warn if this file differs from the pinned canonical digest."""
    digest = self_digest()
    if digest == CANONICAL_SHA256:
        return None
    return (
        "WARN  MIRROR DRIFT: this conform.py differs from the canonical copy "
        f"(self-digest {digest[:12]}..., pinned {CANONICAL_SHA256[:12]}...). "
        "Re-sync from Surgical-Investigation/scripts/conform.py, or run "
        "--print-digest and update CANONICAL_SHA256 in all 7 family repos."
    )


def _strip_quotes(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        return val[1:-1]
    return val


def _parse_inline_list(raw: str) -> list[str]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(item) for item in inner.split(",") if item.strip()]


def _handle_continuation(
    stripped: str, active_list: list[str] | None, in_flow: bool
) -> tuple[bool, bool]:
    """Consume `- item` or wrapped `[...]` list lines; return (handled, in_flow)."""
    if active_list is None:
        return False, False
    if in_flow:
        end = stripped.endswith("]")
        body = stripped[:-1] if end else stripped
        active_list.extend(_strip_quotes(x) for x in body.split(",") if x.strip())
        return True, not end
    if stripped.startswith("- "):
        active_list.append(_strip_quotes(stripped[2:]))
        return True, False
    if stripped.startswith("["):
        if stripped.endswith("]"):
            active_list.extend(_parse_inline_list(stripped))
            return True, False
        inner = stripped[1:].strip()
        if inner:
            active_list.extend(_strip_quotes(x) for x in inner.split(",") if x.strip())
        return True, True
    return False, False


def _assign_yaml_entry(
    target: dict[str, object], key: str, val: str
) -> tuple[list[str] | None, bool]:
    """Assign scalar or list starter into target; return (active_list, in_flow)."""
    if val.startswith("[") and val.endswith("]"):
        target[key] = _parse_inline_list(val)
        return None, False
    if not val or val == "[":
        new_list: list[str] = []
        target[key] = new_list
        return new_list, val == "["
    target[key] = _strip_quotes(val)
    return None, False


def _parse_frontmatter_fallback(raw_fm: str) -> dict[str, object]:
    """Parse minimal YAML frontmatter without third-party dependencies."""
    fm: dict[str, object] = {}
    hermes: dict[str, object] = {}
    hermes_indent: int | None = None
    active_list: list[str] | None = None
    in_flow = False

    for raw_line in raw_fm.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        handled, in_flow = _handle_continuation(stripped, active_list, in_flow)
        if handled:
            active_list = active_list if in_flow or stripped.startswith("- ") else None
            continue
        active_list = None
        if ":" not in stripped:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, val = (p.strip() for p in stripped.split(":", 1))
        if hermes_indent is not None and indent <= hermes_indent:
            hermes_indent = None
        if key == "hermes" and not val:
            hermes_indent = indent
            continue
        target = hermes if hermes_indent is not None else fm
        active_list, in_flow = _assign_yaml_entry(target, key, val)

    if hermes:
        fm["metadata"] = {"hermes": hermes}
    return fm


def _load_frontmatter_dict(raw_fm: str) -> tuple[dict[str, object] | None, str | None]:
    """Load YAML frontmatter via PyYAML when available, else stdlib fallback."""
    try:
        yaml_mod = importlib.import_module("yaml")
    except ImportError:
        return _parse_frontmatter_fallback(raw_fm), None

    try:
        loaded = yaml_mod.safe_load(raw_fm)
    except Exception as exc:
        return None, f"invalid YAML frontmatter: {exc}"
    if not isinstance(loaded, dict):
        return None, "YAML frontmatter must decode to a mapping"
    return {str(k): v for k, v in loaded.items()}, None


def _parse_frontmatter(
    text: str,
) -> tuple[dict[str, object] | None, str, str, list[str]]:
    """Extract and parse YAML frontmatter and body from SKILL.md."""
    problems: list[str] = []
    size = len(text.encode("utf-8"))
    if size > MAX_SKILL_BYTES:
        problems.append(f"SKILL.md is {size} bytes (> {MAX_SKILL_BYTES})")

    if not text.startswith("---"):
        problems.append("SKILL.md does not start with frontmatter '---'")
        return None, "", text, problems

    close = re.search(r"\n---\s*(?:\n|$)", text[3:])
    if not close:
        problems.append("frontmatter never closes with '---'")
        return None, "", text, problems

    raw_fm = text[3 : close.start() + 3]
    body = text[close.end() + 3 :]
    fm, err = _load_frontmatter_dict(raw_fm)
    if err is not None:
        problems.append(err)
    return fm, raw_fm, body, problems


def _check_name_and_desc(fm: dict[str, object]) -> list[str]:
    problems: list[str] = []
    name = fm.get("name")
    if isinstance(name, str) and name:
        if not LOWER_HYPHEN.match(name):
            problems.append(f"name must be lowercase-hyphenated: {name!r}")
        if len(name) > MAX_NAME:
            problems.append(f"name longer than {MAX_NAME} chars: {len(name)}")

    desc = fm.get("description")
    if isinstance(desc, str) and desc:
        if not desc.startswith("Use when"):
            problems.append('description must start with "Use when"')
        if not desc.endswith("."):
            problems.append("description must end with a period")
        if len(desc) > MAX_DESC:
            problems.append(
                f"description is {len(desc)} chars (> {MAX_DESC}): {desc[:70]!r}"
            )
    return problems


def _check_related_skills(skills: object) -> list[str]:
    if not isinstance(skills, list) or not skills:
        return ["related_skills missing or empty"]
    problems: list[str] = []
    for entry in skills:
        if not isinstance(entry, str) or not entry:
            problems.append(f"related_skills entry must be a string: {entry!r}")
            continue
        if ":" in entry or "/" in entry:
            problems.append(
                f"related_skills entry must be bare portable id (no ':' or '/'): "
                f"{entry!r}"
            )
        elif not LOWER_HYPHEN.match(entry):
            problems.append(f"related_skills entry must match ^[a-z0-9-]+$: {entry!r}")
    return problems


def _hermes_block(fm: dict[str, object]) -> dict[str, object]:
    meta = fm.get("metadata")
    if isinstance(meta, dict):
        hermes = meta.get("hermes")
        if isinstance(hermes, dict):
            return {str(k): v for k, v in hermes.items()}
    return {}


def _check_metadata(fm: dict[str, object], raw_fm: str) -> list[str]:
    """Validate required frontmatter fields, SemVer, category, and related_skills."""
    problems: list[str] = []
    for key in REQUIRED_FIELDS:
        val = fm.get(key)
        if val is None or val == "" or val == []:
            problems.append(f"missing required frontmatter field: {key}")

    problems.extend(_check_name_and_desc(fm))

    version = fm.get("version")
    if version is not None and (
        not isinstance(version, str) or not SEMVER.match(version)
    ):
        problems.append(f"version is not SemVer: {version!r}")

    author_match = re.search(r"^author:\s*(.+?)\s*$", raw_fm, re.MULTILINE)
    if author_match:
        raw_author = author_match.group(1).strip()
        is_quoted = (
            len(raw_author) >= 2
            and raw_author[0] == raw_author[-1]
            and raw_author[0] in ('"', "'")
        )
        if "," in raw_author and not is_quoted:
            problems.append("author containing commas must be YAML-quoted")

    hermes = _hermes_block(fm)
    tags = hermes.get("tags", fm.get("tags"))
    if not isinstance(tags, list) or not tags:
        problems.append("tags missing or empty")

    category = hermes.get("category", fm.get("category"))
    if not isinstance(category, str) or not category.strip():
        problems.append("metadata.hermes.category missing or empty")

    related = hermes.get("related_skills", fm.get("related_skills"))
    problems.extend(_check_related_skills(related))
    return problems


def _check_references(skill_dir: Path, skill_md: Path, body: str) -> list[str]:
    """Verify referenced asset paths exist and no nested SKILL.md exists."""
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for folder, raw_rel in ASSET_REF.findall(body):
        rel = raw_rel.rstrip(".")
        if not rel or any(ch in rel for ch in "*?<>"):
            continue
        if folder == "references" and not rel.endswith(".md"):
            continue
        key = (folder, rel)
        if key in seen:
            continue
        seen.add(key)
        if not (skill_dir / folder / rel).exists():
            problems.append(f"body references {folder}/{rel} but it does not exist")

    nested = [
        p.relative_to(skill_dir)
        for p in skill_dir.rglob("SKILL.md")
        if p != skill_md and not any(part in SKIP_SKILL_DIRS for part in p.parts)
    ]
    for extra in sorted(nested):
        problems.append(f"nested SKILL.md (breaks any **/SKILL.md glob): {extra}")
    return problems


def check(skill_dir: Path) -> list[str]:
    """Validate a skill directory and return a list of conformance problems."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"no SKILL.md in {skill_dir}"]

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fm, raw_fm, body, problems = _parse_frontmatter(text)
    if fm is not None:
        problems.extend(_check_metadata(fm, raw_fm))
    problems.extend(_check_references(skill_dir, skill_md, body))
    return problems


def main(argv: list[str]) -> int:
    """CLI entry point for conform.py."""
    if "--print-digest" in argv:
        print(self_digest())
        return 0

    root = (
        Path(argv[1]).resolve()
        if len(argv) > 1 and not argv[1].startswith("-")
        else Path(__file__).resolve().parents[1]
    )
    problems = check(root)
    label = root.name

    # Mirror drift is reported but never fails the run: all 7 family repos are
    # pinned, yet a legitimate edit in one repo must not turn a *different*
    # repo's CI red. It is a loud warning so the drift cannot stay invisible.
    warning = mirror_warning()
    if warning:
        print(warning)

    if problems:
        print(f"FAIL  {label}")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"PASS  {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
