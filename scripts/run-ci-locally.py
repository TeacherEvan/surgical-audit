#!/usr/bin/env python3
"""Replay .github/workflows/skill-ci.yml locally, step by step.

Reads the workflow directly so there is no second copy of checks to drift.
Skips ``pip install`` steps when all required CI tools and Python modules are
already available on PATH/host (avoiding PEP 668 externally-managed errors) and
reports every failing step rather than aborting on the first failure.

Exit 0 = every step passed, 1 = one or more steps failed.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parent.parent  # scripts/ -> repo root
WORKFLOW = REPO / ".github/workflows/skill-ci.yml"
LOCAL_CLI_TOOLS = (
    "pytest",
    "ruff",
    "mypy",
    "shellcheck",
    "yamllint",
    "check-jsonschema",
)
PYTHON_MODULES = ("yaml", "jsonschema")


def _pytest_python() -> pathlib.Path | None:
    """Return the Python interpreter colocated with the pytest CLI, if any."""
    pytest_bin = shutil.which("pytest")
    if pytest_bin is None:
        return None
    probe_dir = pathlib.Path(pytest_bin).resolve().parent
    for candidate in (probe_dir / "python3", probe_dir / "python"):
        if candidate.exists():
            return candidate
    return None


def _tool_environment_ready() -> bool:
    """Return True when required CLI tools and runtime modules exist locally."""
    if not all(shutil.which(cmd) for cmd in LOCAL_CLI_TOOLS):
        return False
    if all(importlib.util.find_spec(mod) is not None for mod in PYTHON_MODULES):
        return True
    pytest_py = _pytest_python()
    if pytest_py is None:
        return False
    check = subprocess.run(
        [str(pytest_py), "-c", "import yaml, jsonschema"],
        check=False,
        capture_output=True,
        text=True,
    )
    return check.returncode == 0


def _load_yaml(text: str) -> dict[str, Any]:
    """Load workflow YAML via active Python or the pytest interpreter."""
    try:
        yaml_mod = importlib.import_module("yaml")

        loaded: dict[str, Any] = yaml_mod.safe_load(text)
        return loaded
    except ImportError:
        pytest_py = _pytest_python()
        if pytest_py is not None:
            script = (
                "import json, sys, yaml; "
                "print(json.dumps(yaml.safe_load(sys.stdin.read())))"
            )
            out = subprocess.run(
                [str(pytest_py), "-c", script],
                check=False,
                input=text,
                capture_output=True,
                text=True,
            )
            if out.returncode == 0:
                parsed: dict[str, Any] = json.loads(out.stdout)
                return parsed
        raise


def _run_step(index: int, step: dict[str, Any], tools_ready: bool) -> bool:
    """Execute one workflow step; return True on pass or intentional skip."""
    name = str(step.get("name") or step.get("uses", "?"))
    if "run" not in step:
        print(f"  [skip] {index:2}. {name}  (uses: {step.get('uses', '')})")
        return True

    run_script = str(step["run"])
    if ("pip install" in run_script or "apt-get install" in run_script) and tools_ready:
        print(f"  [skip] {index:2}. {name}  (tools ready; skipped package install)")
        return True

    run_script = run_script.replace("python3 -m pytest", "pytest").replace(
        "python -m pytest", "pytest"
    )
    env = os.environ.copy()
    extra_bins = [
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/.npm-global/bin"),
        "/home/linuxbrew/.linuxbrew/bin",
    ]
    current_path = env.get("PATH", "")
    path_parts = [p for p in current_path.split(os.pathsep) if p]
    for bin_dir in reversed(extra_bins):
        if os.path.isdir(bin_dir) and bin_dir not in path_parts:
            path_parts.insert(0, bin_dir)
    env["PATH"] = os.pathsep.join(path_parts)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    proc = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", run_script],
        check=False,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    tag = "PASS" if proc.returncode == 0 else "FAIL"
    print(f"  [{tag}] {index:2}. {name}")

    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    for ln in lines[-2:]:
        print(f"          {ln}")

    if proc.returncode != 0:
        for label, blob in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            tail = blob.strip().splitlines()[-12:]
            if tail:
                print(f"          --- {label} ---")
                for ln in tail:
                    print(f"          {ln}")
        return False
    return True


def main() -> int:
    """Run every validate step from .github/workflows/skill-ci.yml."""
    if not WORKFLOW.is_file():
        print(f"workflow not found: {WORKFLOW}", file=sys.stderr)
        return 1

    try:
        wf = _load_yaml(WORKFLOW.read_text(encoding="utf-8"))
    except ImportError:
        print("pyyaml missing — activate a venv with pyyaml", file=sys.stderr)
        return 1

    job_name, job_cfg = next(iter(wf["jobs"].items()))
    steps: list[dict[str, Any]] = job_cfg["steps"]
    tools_ready = _tool_environment_ready()

    print(f"workflow : {WORKFLOW.relative_to(REPO)}")
    print(f"python   : {sys.executable}")
    print(f"job      : {job_name} ({len(steps)} steps)\n")

    failed = sum(
        0 if _run_step(i, step, tools_ready) else 1 for i, step in enumerate(steps, 1)
    )

    print()
    if failed:
        print(f"CI would FAIL — {failed} step(s) failed.")
        return 1
    print(f"CI would PASS — all {job_name} steps succeeded locally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
