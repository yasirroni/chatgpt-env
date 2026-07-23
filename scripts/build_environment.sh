#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 ENVIRONMENT_NAME" >&2
  exit 2
}

[ "$#" -eq 1 ] || usage

environment_name=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
source_environment="$repo_root/environments/$environment_name"

[ -f "$source_environment/Project.toml" ] || {
  echo "Unknown environment: $environment_name" >&2
  exit 2
}
[ -f "$source_environment/Manifest.toml" ] || {
  echo "Manifest.toml is missing for: $environment_name" >&2
  exit 2
}
command -v julia >/dev/null 2>&1 || {
  echo "Julia is not available on PATH" >&2
  exit 2
}
command -v zstd >/dev/null 2>&1 || {
  echo "zstd is not available on PATH" >&2
  exit 2
}

machine=$(uname -m)
case "$machine" in
  x86_64|amd64) ;;
  *)
    echo "This bundle must be built on Linux x86-64; found: $machine" >&2
    exit 2
    ;;
esac

julia_version=$(python3 - "$source_environment/Manifest.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], 'rb') as f:
    manifest = tomllib.load(f)
print(manifest['julia_version'])
PY
)

expected_version=${JULIA_VERSION:-$julia_version}
actual_version=$(julia --startup-file=no --history-file=no -e 'print(VERSION)')
[ "$actual_version" = "$expected_version" ] || {
  echo "Julia version mismatch: expected $expected_version, found $actual_version" >&2
  exit 2
}

work_parent=${RUNNER_TEMP:-$repo_root/build}
work_root="$work_parent/chatgpt-env-$environment_name"
bundle_name="julia-env-$environment_name"
bundle_root="$work_root/$bundle_name"
dist_dir="$repo_root/dist/$environment_name"

rm -rf "$work_root" "$dist_dir"
mkdir -p "$bundle_root/environment" "$bundle_root/depot" "$dist_dir"
cp "$source_environment/Project.toml" "$bundle_root/environment/Project.toml"
cp "$source_environment/Manifest.toml" "$bundle_root/environment/Manifest.toml"

export JULIA_DEPOT_PATH="$bundle_root/depot"
export JULIA_CPU_TARGET=${JULIA_CPU_TARGET:-generic}
export JULIA_PKG_PRECOMPILE_AUTO=0
export JULIA_CI=true
export JULIA_NUM_PRECOMPILE_TASKS=${JULIA_NUM_PRECOMPILE_TASKS:-4}

allow_build=true
skip_load_packages=""
case "$environment_name" in
  matlab)
    allow_build=false
    skip_load_packages="MATLAB"
    ;;
esac
export SKIP_LOAD_PACKAGES="$skip_load_packages"

build_log="$dist_dir/build.log"
validation_log="$bundle_root/VALIDATION.txt"

{
  echo "Environment: $environment_name"
  echo "Julia: $actual_version"
  echo "Machine: $(uname -srm)"
  echo "JULIA_CPU_TARGET: $JULIA_CPU_TARGET"
  echo "Allow package build scripts: $allow_build"
  echo "Skipped package loads: ${skip_load_packages:-none}"
  echo
  echo "Instantiating exact manifest..."
} | tee "$build_log"

if [ "$allow_build" = true ]; then
  julia --startup-file=no --history-file=no \
    --project="$bundle_root/environment" \
    -e 'using Pkg; Pkg.instantiate(; verbose=true, allow_build=true, allow_autoprecomp=false)' \
    2>&1 | tee -a "$build_log"

  julia --startup-file=no --history-file=no \
    --project="$bundle_root/environment" \
    -e 'using Pkg; Pkg.precompile(; strict=false)' \
    2>&1 | tee -a "$build_log"
else
  julia --startup-file=no --history-file=no \
    --project="$bundle_root/environment" \
    -e 'using Pkg; Pkg.instantiate(; verbose=true, allow_build=false, allow_autoprecomp=false)' \
    2>&1 | tee -a "$build_log"
fi

julia --startup-file=no --history-file=no \
  --project="$bundle_root/environment" \
  "$repo_root/scripts/warm_environment.jl" "$bundle_root/environment" \
  2>&1 | tee -a "$build_log"

rm -rf \
  "$bundle_root/depot/clones" \
  "$bundle_root/depot/dev" \
  "$bundle_root/depot/logs"

project_sha=$(sha256sum "$bundle_root/environment/Project.toml" | awk '{print $1}')
manifest_sha=$(sha256sum "$bundle_root/environment/Manifest.toml" | awk '{print $1}')
created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "$bundle_root/BUNDLE_INFO.toml" "$environment_name" "$actual_version" \
  "$project_sha" "$manifest_sha" "$created_at" "$allow_build" "$skip_load_packages" <<'PY'
from pathlib import Path
import sys

path, name, julia_version, project_sha, manifest_sha, created_at, allow_build, skipped = sys.argv[1:]
skipped_values = [item for item in skipped.split(',') if item]
quoted_skipped = ', '.join(f'"{item}"' for item in skipped_values)
Path(path).write_text(
    f'name = "{name}"\n'
    f'julia_version = "{julia_version}"\n'
    'platform = "linux-x86_64"\n'
    'cpu_target = "generic"\n'
    f'created_at_utc = "{created_at}"\n'
    f'project_sha256 = "{project_sha}"\n'
    f'manifest_sha256 = "{manifest_sha}"\n'
    f'package_build_scripts_enabled = {allow_build.lower()}\n'
    f'skipped_load_packages = [{quoted_skipped}]\n',
    encoding='utf-8',
)
PY

{
  echo "Offline validation"
  echo "=================="
  echo "Environment: $environment_name"
  echo "Julia: $actual_version"
  echo "Skipped package loads: ${skip_load_packages:-none}"
  echo
} > "$validation_log"

JULIA_PKG_OFFLINE=true julia --startup-file=no --history-file=no \
  --project="$bundle_root/environment" \
  "$repo_root/scripts/warm_environment.jl" "$bundle_root/environment" \
  2>&1 | tee -a "$validation_log" "$build_log"

archive_base="julia-env-$environment_name-linux-x86_64-julia-$actual_version.tar.zst"
archive_path="$dist_dir/$archive_base"

(
  cd "$work_root"
  tar -cf - "$bundle_name" | zstd -19 -T0 -q -o "$archive_path"
)

zstd -t -q "$archive_path"
tar --use-compress-program=unzstd -tf "$archive_path" >/dev/null

archive_sha=$(sha256sum "$archive_path" | awk '{print $1}')
archive_size=$(stat -c '%s' "$archive_path")
max_bytes=${CHATGPT_MAX_BYTES:-536870912}
part_bytes=${CHATGPT_PART_BYTES:-524288000}

printf '%s  %s\n' "$archive_sha" "$archive_base" > "$dist_dir/$archive_base.sha256"
cp "$source_environment/Project.toml" "$dist_dir/Project.toml"
cp "$source_environment/Manifest.toml" "$dist_dir/Manifest.toml"
cp "$bundle_root/BUNDLE_INFO.toml" "$dist_dir/BUNDLE_INFO.toml"
cp "$validation_log" "$dist_dir/VALIDATION.txt"

if [ "$archive_size" -ge "$max_bytes" ]; then
  part_base=$(basename "$archive_path" .tar.zst)
  split_prefix="$dist_dir/$part_base.part-"
  split -b "$part_bytes" -d -a 3 "$archive_path" "$split_prefix"
  rm "$archive_path"

  {
    echo "archive=$archive_base"
    echo "archive_size_bytes=$archive_size"
    echo "archive_sha256=$archive_sha"
    echo "reconstruct_command=cat $part_base.part-* > $archive_base"
    echo
    echo "parts:"
    for part in "$split_prefix"*; do
      part_name=$(basename "$part")
      part_size=$(stat -c '%s' "$part")
      part_sha=$(sha256sum "$part" | awk '{print $1}')
      echo "$part_name $part_size $part_sha"
    done
  } > "$dist_dir/$part_base.parts.txt"
fi

cat > "$dist_dir/RELEASE_NOTES.md" <<EOF_NOTES
Built from the committed \
\`environments/$environment_name/Project.toml\` and \
\`environments/$environment_name/Manifest.toml\` using Julia $actual_version on Linux x86-64.

- CPU target: generic
- Project SHA-256: $project_sha
- Manifest SHA-256: $manifest_sha
- Package build scripts enabled: $allow_build
- Skipped load validation: ${skip_load_packages:-none}

Use the published SHA-256 and validation files to verify the downloaded bundle.
EOF_NOTES

printf 'Built %s\n' "$environment_name"
printf 'Output directory: %s\n' "$dist_dir"
find "$dist_dir" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
