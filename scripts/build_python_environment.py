#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import zipfile


def die(message: str) -> "NoReturn":
    raise SystemExit(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, *, expected_hash: str | None = None,
             expected_size: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "chatgpt-env/python-environment"})

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            digest = hashlib.sha256()
            size = 0
            with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
                    digest.update(block)
                    size += len(block)
            actual_hash = digest.hexdigest()
            if expected_hash and actual_hash != expected_hash:
                die(
                    f"SHA-256 mismatch for {destination.name}: "
                    f"expected {expected_hash}, found {actual_hash}"
                )
            if expected_size is not None and size != expected_size:
                die(
                    f"Size mismatch for {destination.name}: "
                    f"expected {expected_size}, found {size}"
                )
            temporary.replace(destination)
            return
        except Exception as error:  # pragma: no cover - network retry path
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt * 2)
    die(f"Failed to download {url}: {last_error}")


def normalise_name(name: str) -> str:
    return name.lower().replace("_", "-")


def main() -> None:
    if len(sys.argv) != 2:
        die(f"usage: {Path(sys.argv[0]).name} ENVIRONMENT_NAME")

    environment_name = sys.argv[1]
    repo_root = Path(__file__).resolve().parents[1]
    source_environment = repo_root / "environments" / environment_name
    pyproject_path = source_environment / "pyproject.toml"
    lock_path = source_environment / "uv.lock"
    model_path = source_environment / "model.toml"

    for required in (pyproject_path, lock_path, model_path):
        if not required.is_file():
            die(f"Missing Python environment input: {required}")

    if sys.platform != "linux" or platform.machine() not in {"x86_64", "amd64"}:
        die(
            "This bundle must be built on Linux x86-64; "
            f"found: {platform.system()} {platform.machine()}"
        )
    if shutil.which("uv") is None:
        die("uv is not available on PATH")

    with pyproject_path.open("rb") as stream:
        pyproject = tomllib.load(stream)
    with lock_path.open("rb") as stream:
        lock = tomllib.load(stream)
    with model_path.open("rb") as stream:
        model = tomllib.load(stream)

    project = pyproject.get("project", {})
    if project.get("name") != environment_name:
        die(
            f"Environment directory {environment_name!r} does not match "
            f"project name {project.get('name')!r}"
        )

    requires_python = project.get("requires-python", "")
    if not requires_python.startswith("==3.13"):
        die(f"Expected a Python 3.13 lock, found requires-python={requires_python!r}")
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info[:2] != (3, 13):
        die(f"Expected Python 3.13, found {actual_python}")

    with tempfile.TemporaryDirectory() as temporary_directory:
        export_path = Path(temporary_directory) / "requirements.txt"
        export_result = subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--project",
                str(source_environment),
                "--no-emit-project",
                "--output-file",
                str(export_path),
            ],
            capture_output=True,
            text=True,
        )
        if export_result.returncode != 0:
            die(
                "uv export failed: "
                + (export_result.stderr or export_result.stdout).strip()
            )

    packages = {normalise_name(item["name"]): item for item in lock.get("package", [])}
    root_package = packages.get(normalise_name(environment_name))
    if not root_package or root_package.get("source", {}).get("virtual") != ".":
        die("uv.lock does not contain the expected virtual root package")

    direct_names = sorted(
        normalise_name(item["name"]) for item in root_package.get("dependencies", [])
    )
    if not direct_names:
        die("uv.lock contains no direct bundle dependencies")

    work_parent = Path(os.environ.get("RUNNER_TEMP", repo_root / "build"))
    work_root = work_parent / f"chatgpt-env-{environment_name}"
    bundle_root = work_root / environment_name
    wheel_dir = bundle_root / "wheels"
    dist_dir = repo_root / "dist" / environment_name

    shutil.rmtree(work_root, ignore_errors=True)
    shutil.rmtree(dist_dir, ignore_errors=True)
    wheel_dir.mkdir(parents=True)
    dist_dir.mkdir(parents=True)

    package_versions: dict[str, str] = {}
    wheel_records: list[tuple[str, str, str, int]] = []
    for name in direct_names:
        package = packages.get(name)
        if package is None:
            die(f"Direct package missing from uv.lock: {name}")
        wheels = package.get("wheels", [])
        if len(wheels) != 1:
            die(f"Expected exactly one locked wheel for {name}, found {len(wheels)}")
        wheel = wheels[0]
        url = wheel["url"]
        filename = Path(urlparse(url).path).name
        expected_hash = wheel["hash"].removeprefix("sha256:")
        expected_size = int(wheel["size"])
        destination = wheel_dir / filename
        download(
            url,
            destination,
            expected_hash=expected_hash,
            expected_size=expected_size,
        )
        with zipfile.ZipFile(destination) as archive:
            bad_member = archive.testzip()
            if bad_member:
                die(f"Corrupt wheel member in {filename}: {bad_member}")
        package_versions[name] = package["version"]
        wheel_records.append((name, filename, expected_hash, expected_size))

    repository = model["repository"]
    revision = model["revision"]
    huggingface_base_url = os.environ.get(
        "CHATGPT_ENV_HUGGINGFACE_BASE_URL", "https://huggingface.co"
    ).rstrip("/")
    model_destination = bundle_root / model["destination"]
    model_files = model.get("files", [])
    minimum_sizes = model.get("minimum_size_bytes", {})
    if not model_files:
        die("model.toml contains no files")

    for relative_name in model_files:
        encoded_path = quote(relative_name, safe="/")
        url = (
            f"{huggingface_base_url}/{repository}/resolve/{revision}/"
            f"{encoded_path}?download=true"
        )
        destination = model_destination / relative_name
        download(url, destination)
        minimum_size = minimum_sizes.get(relative_name)
        if minimum_size is not None and destination.stat().st_size < int(minimum_size):
            die(
                f"Model file {relative_name} is unexpectedly small: "
                f"{destination.stat().st_size} bytes"
            )

    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pyproject_sha = sha256_file(pyproject_path)
    lock_sha = sha256_file(lock_path)
    model_sha = sha256_file(model_path)
    excluded = pyproject.get("tool", {}).get("uv", {}).get("exclude-dependencies", [])

    quoted_excluded = ", ".join(f'"{item}"' for item in excluded)
    package_lines = "\n".join(
        f'{name.replace("-", "_")} = "{version}"'
        for name, version in sorted(package_versions.items())
    )
    (bundle_root / "BUNDLE_INFO.toml").write_text(
        f'name = "{environment_name}"\n'
        f'python_version = "3.13"\n'
        f'platform = "linux-x86_64"\n'
        f'created_at_utc = "{created_at}"\n'
        f'pyproject_sha256 = "{pyproject_sha}"\n'
        f'uv_lock_sha256 = "{lock_sha}"\n'
        f'model_config_sha256 = "{model_sha}"\n'
        f'model_repository = "{repository}"\n'
        f'model_revision = "{revision}"\n'
        f'embedding_dimensions = {int(model["embedding_dimensions"])}\n'
        f'chatgpt_supplied_dependencies = [{quoted_excluded}]\n\n'
        f'[packages]\n{package_lines}\n',
        encoding="utf-8",
    )

    uv_version = subprocess.run(
        ["uv", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    validation_lines = [
        f"{environment_name} bundle validation",
        "=" * (len(environment_name) + 19),
        f"Environment: {environment_name}",
        f"Python: {actual_python}",
        f"uv: {uv_version}",
        "Platform: linux-x86_64",
        f"Model: {repository}@{revision}",
        f"Embedding dimensions: {int(model['embedding_dimensions'])}",
        "",
        "Locked wheels:",
    ]
    validation_lines.extend(
        f"- {name} {package_versions[name]}: {filename} ({size} bytes, sha256:{digest})"
        for name, filename, digest, size in wheel_records
    )
    validation_lines.extend(["", "Model files:"])
    validation_lines.extend(
        f"- {relative_name}: {(model_destination / relative_name).stat().st_size} bytes"
        for relative_name in model_files
    )
    (bundle_root / "VALIDATION.txt").write_text(
        "\n".join(validation_lines) + "\n", encoding="utf-8"
    )

    checksum_lines = []
    for path in sorted(bundle_root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{sha256_file(path)}  {path.relative_to(bundle_root)}")
    (bundle_root / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    archive_name = f"{environment_name}-linux-x86_64-py313.zip"
    archive_path = dist_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(bundle_root.rglob("*")):
            if path.is_file():
                archive.write(path, Path(environment_name) / path.relative_to(bundle_root))
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            die(f"Corrupt bundle member: {bad_member}")

    archive_hash = sha256_file(archive_path)
    (dist_dir / f"{archive_name}.sha256").write_text(
        f"{archive_hash}  {archive_name}\n", encoding="utf-8"
    )
    for source in (pyproject_path, lock_path, model_path):
        shutil.copy2(source, dist_dir / source.name)
    shutil.copy2(bundle_root / "BUNDLE_INFO.toml", dist_dir / "BUNDLE_INFO.toml")
    shutil.copy2(bundle_root / "VALIDATION.txt", dist_dir / "VALIDATION.txt")
    (dist_dir / "RELEASE_NOTES.md").write_text(
        f"Built from `environments/{environment_name}/pyproject.toml`, `uv.lock`, "
        f"and `model.toml` for Python 3.13 on Linux x86-64.\n\n"
        f"The archive contains {len(wheel_records)} locked wheels and "
        f"`{repository}` at revision `{revision}`.\n\n"
        "The target ChatGPT sandbox supplies the dependencies listed in "
        "`tool.uv.exclude-dependencies`.\n",
        encoding="utf-8",
    )

    print(f"Built {environment_name}")
    print(f"Output directory: {dist_dir}")
    for path in sorted(dist_dir.iterdir()):
        if path.is_file():
            print(f"{path.name} {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
