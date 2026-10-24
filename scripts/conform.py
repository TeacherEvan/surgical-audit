#!/usr/bin/env python3
"""Conformance gate for an Agent-Surgery skill.

Validates one skill directory against the Hermes authoring standard
(references/skill-authoring-standards.md), including the constraints that
standard distils from the vendor spec but does not itself enforce:

  * description <= 60 chars, starts with "Use when", ends with a period
    (docs/external-research/hermes-agent-skill-spec.md:23)
  * exactly one SKILL.md per skill dir (no nested frontmatter-less copies)
  * every references/*.md named in the body exists on disk

No third-party deps: deliberately regex-based so it runs wherever python3
exists (the same constraint that shaped run-ci-locally.py's fallback).

CANONICAL COPY: Surgical-Investigation/scripts/conform.py
This script is mirrored into each skill repo because the repos are independent
git remotes with no shared tooling. To stop the four copies drifting silently
(the exact failure this family's "Mirrored Installs" rule was written for), each
copy self-checks: it hashes its own bytes with CANONICAL_SHA256 blanked out and
warns if that differs from the pinned value. After editing ANY copy:

    python3 scripts/conform.py --print-digest     # prints the new digest
    # then update CANONICAL_SHA256 in EVERY copy (all 4 must match)

A mismatch is a warning, not a hard failure, so a legitimate in-flight edit in
one repo never blocks unrelated CI in another.

Usage:
    python3 scripts/conform.py [skill_dir]     # default: this skill's root
    python3 scripts/conform.py --print-digest  # emit the self-digest
Exit 0 = conformant, 1 = at least one violation.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

# Blank-out sentinel: the digest excludes this line, so it can be edited
# without invalidating itself. Keep the assignment on ONE line.
CANONICAL_SHA256 = "d634da49159dd64757875c914a29436151a9f8a4914d5afc2bb16b55c3185005"

MAX_DESC = 60
MAX_NAME = 64
MAX_SKILL_BYTES = 100_000
REQUIRED_FIELDS = ("name", "description", "version", "author", "license", "platforms")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LOWER_HYPHEN = re.compile(r"^[a-z0-9-]+$")


def self_digest() -> str:
    """sha256 of this file with the CANONICAL_SHA256 value blanked out."""
    text = Path(__file__).read_text(encoding="utf-8")
    masked = re.sub(
        r'^CANONICAL_SHA256 = "[0-9a-f]*"$',
        'CANONICAL_SHA256 = ""',
        text,
        flags=re.MULTILINE,
    )
    return hashlib.sha256(masked.encode("utf-8")).hexdigest()


def mirror_warning() -> str | None:
    digest = self_digest()
    if digest == CANONICAL_SHA256:
        return None
    return (
        "WARN  MIRROR DRIFT: this conform.py differs from the canonical copy "
        f"(self-digest {digest[:12]}..., pinned {CANONICAL_SHA256[:12]}...). "
        "Re-sync from Surgical-Investigation/scripts/conform.py, or run "
        "--print-digest and update CANONICAL_SHA256 in all four repos."
    )


def _field(fm: str, key: str) -> str | None:
    """Return the raw scalar for `key:` in the frontmatter, if present."""
    m = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else None


def check(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"no SKILL.md in {skill_dir}"]

    text = skill_md.read_text(encoding="utf-8", errors="replace")

    if len(text.encode()) > MAX_SKILL_BYTES:
        problems.append(f"SKILL.md is {len(text.encode())} bytes (> {MAX_SKILL_BYTES})")

    if not text.startswith("---"):
        return problems + ["SKILL.md does not start with frontmatter '---'"]
    close = re.search(r"\n---\s*\n", text[3:])
    if not close:
        return problems + ["frontmatter never closes with '---'"]
    fm, body = text[3 : close.start() + 3], text[close.start() + 3 :]

    for key in REQUIRED_FIELDS:
        if _field(fm, key) is None:
            problems.append(f"missing required frontmatter field: {key}")

    name = _field(fm, "name")
    if name is not None:
        if not LOWER_HYPHEN.match(name):
            problems.append(f"name must be lowercase-hyphenated: {name!r}")
        if len(name) > MAX_NAME:
            problems.append(f"name longer than {MAX_NAME} chars: {len(name)}")

    desc = _field(fm, "description")
    if desc is not None:
        if not desc.startswith("Use when"):
            problems.append('description must start with "Use when"')
        if not desc.endswith("."):
            problems.append("description must end with a period")
        if len(desc) > MAX_DESC:
            problems.append(f"description is {len(desc)} chars (> {MAX_DESC}): {desc[:70]!r}")

    version = _field(fm, "version")
    if version is not None and not SEMVER.match(version):
        problems.append(f"version is not SemVer: {version!r}")

    # tags / related_skills may sit top-level or under metadata.hermes
    if not re.search(r"^\s*tags:\s*\[.+\]", fm, re.MULTILINE):
        problems.append("tags missing or empty")
    if not re.search(r"^\s*related_skills:\s*\[.+\]", fm, re.MULTILINE):
        problems.append("related_skills missing or empty")

    # every references/*.md named in the body must exist on disk
    for ref in sorted(set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", body))):
        if not (skill_dir / "references" / ref).exists():
            problems.append(f"body references references/{ref} but it does not exist")

    # exactly one SKILL.md per skill dir
    nested = [
        p.relative_to(skill_dir)
        for p in skill_dir.rglob("SKILL.md")
        if p != skill_md and "node_modules" not in p.parts
    ]
    for extra in nested:
        problems.append(f"nested SKILL.md (breaks any **/SKILL.md glob): {extra}")

    return problems


def main(argv: list[str]) -> int:
    if "--print-digest" in argv:
        print(self_digest())
        return 0

    root = Path(argv[1]).resolve() if len(argv) > 1 and not argv[1].startswith("-") else Path(__file__).resolve().parents[1]
    problems = check(root)
    label = root.name

    # Mirror drift is reported but never fails the run: the four copies are
    # pinned, yet a legitimate edit in one repo must not turn a *different*
    # repo's CI red. It is a loud warning so the drift cannot stay invisible.
    warning = mirror_warning()
    if warning:
        print(warning)

    if problems:
        print(f"FAIL  {label}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"PASS  {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

