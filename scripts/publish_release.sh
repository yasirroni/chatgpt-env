#!/usr/bin/env bash
set -euo pipefail

[ "$#" -eq 1 ] || {
  echo "usage: $0 ENVIRONMENT_NAME" >&2
  exit 2
}

environment_name=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
dist_dir="$repo_root/dist/$environment_name"

[ -d "$dist_dir" ] || {
  echo "Build output not found: $dist_dir" >&2
  exit 2
}
command -v gh >/dev/null 2>&1 || {
  echo "GitHub CLI is not available" >&2
  exit 2
}

julia_version=${JULIA_VERSION:-1.12.4}
tag="julia-$julia_version-$environment_name-run-${GITHUB_RUN_NUMBER:-local}-${GITHUB_RUN_ATTEMPT:-1}"
title="Julia $julia_version $environment_name environment"
notes_file="$dist_dir/RELEASE_NOTES.md"

mapfile -d '' assets < <(
  find "$dist_dir" -maxdepth 1 -type f \
    ! -name 'build.log' \
    ! -name 'RELEASE_NOTES.md' \
    -print0 | sort -z
)

[ "${#assets[@]}" -gt 0 ] || {
  echo "No release assets found in $dist_dir" >&2
  exit 2
}

gh release create "$tag" "${assets[@]}" \
  --target "${GITHUB_SHA:-HEAD}" \
  --title "$title" \
  --notes-file "$notes_file"

echo "Published release: $tag"
