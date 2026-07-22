#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENTS = ROOT / "environments"
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_JULIA = "1.12.4"
ALLOWED_EXTRA_WORKFLOWS = {"runtime"}

errors: list[str] = []
warnings: list[str] = []

environment_names = sorted(path.name for path in ENVIRONMENTS.iterdir() if path.is_dir())
if not environment_names:
    errors.append("No environments found")

fingerprints: dict[tuple[str, str], str] = {}
for name in environment_names:
    env_dir = ENVIRONMENTS / name
    project_path = env_dir / "Project.toml"
    manifest_path = env_dir / "Manifest.toml"

    if not project_path.is_file() or not manifest_path.is_file():
        errors.append(f"{name}: Project.toml or Manifest.toml missing")
        continue

    with project_path.open("rb") as f:
        project = tomllib.load(f)
    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)

    if manifest.get("julia_version") != EXPECTED_JULIA:
        errors.append(
            f"{name}: expected Julia {EXPECTED_JULIA}, "
            f"found {manifest.get('julia_version')}"
        )

    manifest_deps = manifest.get("deps", {})
    for dependency in project.get("deps", {}):
        if dependency not in manifest_deps:
            errors.append(f"{name}: direct dependency absent from manifest: {dependency}")

    fingerprints[(name, "project")] = hashlib.sha256(project_path.read_bytes()).hexdigest()
    fingerprints[(name, "manifest")] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

for index, left in enumerate(environment_names):
    for right in environment_names[index + 1 :]:
        if (
            fingerprints.get((left, "project")) == fingerprints.get((right, "project"))
            and fingerprints.get((left, "manifest")) == fingerprints.get((right, "manifest"))
        ):
            warnings.append(f"Duplicate environments: {left} and {right}")

workflow_files = sorted(WORKFLOWS.glob("build-*.yml"))
workflow_environments: set[str] = set()
for workflow in workflow_files:
    text = workflow.read_text(encoding="utf-8")
    if not re.search(r"(?m)^on:\s*\n\s{2}workflow_dispatch:\s*$", text):
        errors.append(f"{workflow.name}: not manual-only workflow_dispatch")
    for forbidden in ("push:", "pull_request:", "schedule:", "workflow_run:"):
        if re.search(rf"(?m)^\s{{2}}{re.escape(forbidden)}", text):
            errors.append(f"{workflow.name}: forbidden automatic trigger {forbidden}")
    match = re.search(r"(?m)^\s{6}ENVIRONMENT_NAME:\s*(\S+)\s*$", text)
    if not match:
        errors.append(f"{workflow.name}: ENVIRONMENT_NAME not found")
    else:
        workflow_environments.add(match.group(1))

missing_workflows = sorted(set(environment_names) - workflow_environments)
extra_workflows = sorted(
    (workflow_environments - set(environment_names)) - ALLOWED_EXTRA_WORKFLOWS
)
if missing_workflows:
    errors.append("Missing environment workflows: " + ", ".join(missing_workflows))
if extra_workflows:
    errors.append("Unknown environment workflows: " + ", ".join(extra_workflows))

print(f"Environments: {len(environment_names)}")
print(f"Manual workflows: {len(workflow_files)}")
for warning in warnings:
    print(f"WARNING: {warning}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository validation passed")
