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

notes_file="$dist_dir/RELEASE_NOTES.md"

metadata_output=$(python3 "$script_dir/release_metadata.py" "$environment_name")
mapfile -t release_metadata <<< "$metadata_output"
[ "${#release_metadata[@]}" -eq 2 ] || {
  echo "Release metadata generator returned unexpected output" >&2
  exit 2
}
tag=${release_metadata[0]}
title=${release_metadata[1]}

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
