#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENTS = ROOT / "environments"
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_JULIA = "1.12.4"
ALLOWED_EXTRA_WORKFLOWS = {"runtime"}

errors: list[str] = []
warnings: list[str] = []


def normalise_name(name: str) -> str:
    return name.lower().replace("_", "-")


def fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


environment_names = sorted(path.name for path in ENVIRONMENTS.iterdir() if path.is_dir())
if not environment_names:
    errors.append("No environments found")

fingerprints: dict[str, str] = {}
julia_environments: list[str] = []
python_environments: list[str] = []

for name in environment_names:
    env_dir = ENVIRONMENTS / name
    project_path = env_dir / "Project.toml"
    manifest_path = env_dir / "Manifest.toml"
    pyproject_path = env_dir / "pyproject.toml"
    lock_path = env_dir / "uv.lock"
    model_path = env_dir / "model.toml"

    has_julia = project_path.is_file() or manifest_path.is_file()
    has_python = pyproject_path.is_file() or lock_path.is_file()

    if has_julia and has_python:
        errors.append(f"{name}: mixed Julia and Python environment inputs")
        continue

    if has_julia:
        julia_environments.append(name)
        if not project_path.is_file() or not manifest_path.is_file():
            errors.append(f"{name}: Project.toml or Manifest.toml missing")
            continue

        with project_path.open("rb") as stream:
            project = tomllib.load(stream)
        with manifest_path.open("rb") as stream:
            manifest = tomllib.load(stream)

        if manifest.get("julia_version") != EXPECTED_JULIA:
            errors.append(
                f"{name}: expected Julia {EXPECTED_JULIA}, "
                f"found {manifest.get('julia_version')}"
            )

        manifest_deps = manifest.get("deps", {})
        for dependency in project.get("deps", {}):
            if dependency not in manifest_deps:
                errors.append(f"{name}: direct dependency absent from manifest: {dependency}")

        fingerprints[name] = fingerprint([project_path, manifest_path])
        continue

    if has_python:
        python_environments.append(name)
        if not pyproject_path.is_file() or not lock_path.is_file():
            errors.append(f"{name}: pyproject.toml or uv.lock missing")
            continue
        if not model_path.is_file():
            errors.append(f"{name}: model.toml missing")
            continue

        with pyproject_path.open("rb") as stream:
            pyproject = tomllib.load(stream)
        with lock_path.open("rb") as stream:
            lock = tomllib.load(stream)
        with model_path.open("rb") as stream:
            model = tomllib.load(stream)

        project = pyproject.get("project", {})
        if project.get("name") != name:
            errors.append(
                f"{name}: project name does not match directory: {project.get('name')!r}"
            )
        if not str(project.get("requires-python", "")).startswith("==3.13"):
            errors.append(f"{name}: expected Python 3.13 requires-python constraint")
        if pyproject.get("tool", {}).get("uv", {}).get("package") is not False:
            errors.append(f"{name}: tool.uv.package must be false")

        locked_packages = {
            normalise_name(package["name"]): package
            for package in lock.get("package", [])
        }
        root_package = locked_packages.get(normalise_name(name))
        if not root_package or root_package.get("source", {}).get("virtual") != ".":
            errors.append(f"{name}: uv.lock virtual root package missing")
            root_dependencies: set[str] = set()
        else:
            root_dependencies = {
                normalise_name(item["name"])
                for item in root_package.get("dependencies", [])
            }

        declared_dependencies: dict[str, str] = {}
        for requirement in project.get("dependencies", []):
            dependency_name, separator, version = requirement.partition("==")
            if separator != "==" or not dependency_name or not version:
                errors.append(f"{name}: dependency must be exactly pinned: {requirement}")
                continue
            declared_dependencies[normalise_name(dependency_name)] = version

        if set(declared_dependencies) != root_dependencies:
            errors.append(
                f"{name}: pyproject dependencies and uv.lock root dependencies differ"
            )

        for dependency, expected_version in declared_dependencies.items():
            locked = locked_packages.get(dependency)
            if locked is None:
                errors.append(f"{name}: dependency absent from uv.lock: {dependency}")
                continue
            if locked.get("version") != expected_version:
                errors.append(
                    f"{name}: {dependency} expected {expected_version}, "
                    f"found {locked.get('version')}"
                )
            wheels = locked.get("wheels", [])
            if len(wheels) != 1:
                errors.append(f"{name}: expected one locked wheel for {dependency}")
                continue
            wheel = wheels[0]
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", wheel.get("hash", "")):
                errors.append(f"{name}: invalid wheel hash for {dependency}")
            if not isinstance(wheel.get("size"), int) or wheel["size"] <= 0:
                errors.append(f"{name}: invalid wheel size for {dependency}")

        revision = model.get("revision", "")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            errors.append(f"{name}: model revision must be a 40-character Git commit")
        if not model.get("repository"):
            errors.append(f"{name}: model repository missing")
        if not model.get("files"):
            errors.append(f"{name}: model file list missing")
        if model.get("embedding_dimensions") != 384:
            errors.append(f"{name}: expected 384 embedding dimensions")

        uv = shutil.which("uv")
        if uv is None:
            errors.append(f"{name}: uv is required to validate uv.lock")
        else:
            with tempfile.TemporaryDirectory() as temporary_directory:
                output_path = Path(temporary_directory) / "requirements.txt"
                result = subprocess.run(
                    [
                        uv,
                        "export",
                        "--frozen",
                        "--project",
                        str(env_dir),
                        "--no-emit-project",
                        "--output-file",
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    errors.append(
                        f"{name}: uv export failed: "
                        f"{(result.stderr or result.stdout).strip()}"
                    )

        fingerprints[name] = fingerprint([pyproject_path, lock_path, model_path])
        continue

    errors.append(f"{name}: unrecognised environment layout")

for index, left in enumerate(environment_names):
    for right in environment_names[index + 1 :]:
        if fingerprints.get(left) and fingerprints.get(left) == fingerprints.get(right):
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
print(f"Julia environments: {len(julia_environments)}")
print(f"Python environments: {len(python_environments)}")
print(f"Manual workflows: {len(workflow_files)}")
for warning in warnings:
    print(f"WARNING: {warning}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository validation passed")
