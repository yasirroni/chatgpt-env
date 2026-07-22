#!/usr/bin/env bash
# Build a portable Julia runtime bundle for Linux x86-64.
#
# Downloads the official Julia tarball, verifies its SHA-256, adds a test
# script, and repackages as a single .tar.gz for release.
#
# Usage: build_runtime_bundle.sh
#
# Output goes to dist/runtime/.
set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
dist_dir="$repo_root/dist/runtime"
work_root="${RUNNER_TEMP:-$repo_root/build}/julia-runtime-bundle"

JULIA_VERSION="${JULIA_VERSION:-1.12.4}"
ARCH="linux-x86_64"
JULIA_SHA256="c57baf178fe140926acb1a25396d482f325af9d7908d9b066d2fbc0d6639985d"
TARBALL_NAME="julia-${JULIA_VERSION}-${ARCH}.tar.gz"
DOWNLOAD_URL="https://julialang-s3.julialang.org/bin/linux/x64/1.12/${TARBALL_NAME}"
BUNDLE_NAME="julia-runtime-${ARCH}-${JULIA_VERSION}"

command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 2; }
command -v zstd >/dev/null 2>&1 || { echo "zstd is required" >&2; exit 2; }

rm -rf "$work_root" "$dist_dir"
mkdir -p "$work_root" "$dist_dir"

echo "Downloading Julia ${JULIA_VERSION} for ${ARCH}..."
curl -fsSL "$DOWNLOAD_URL" -o "$work_root/$TARBALL_NAME"

echo "Verifying SHA-256..."
echo "${JULIA_SHA256}  ${work_root}/${TARBALL_NAME}" | sha256sum -c -

echo "Extracting..."
tar -xzf "$work_root/$TARBALL_NAME" -C "$work_root"
julia_dir="$work_root/julia-${JULIA_VERSION}"

# Add a test script into the bundle
cat > "$julia_dir/test_runtime.jl" <<'JULIA'
using Pkg

println("Julia VERSION = ", VERSION)
println("Sys.MACHINE = ", Sys.MACHINE)
println("Pkg available = yes")
println("DEPOT_PATH = ", DEPOT_PATH)
JULIA

echo "Repackaging as ${BUNDLE_NAME}.tar.zst ..."
output_archive="$dist_dir/${BUNDLE_NAME}.tar.zst"
{
  cd "$work_root"
  tar -cf - "$(basename "$julia_dir")" | zstd -19 -T0 -q -o "$output_archive"
}

zstd -t -q "$output_archive"

archive_sha=$(sha256sum "$output_archive" | awk '{print $1}')
archive_size=$(stat -c '%s' "$output_archive")

echo "${archive_sha}  ${BUNDLE_NAME}.tar.zst" > "$dist_dir/${BUNDLE_NAME}.tar.zst.sha256"

cat > "$dist_dir/RELEASE_NOTES.md" <<EOF_NOTES
Julia ${JULIA_VERSION} portable runtime for Linux x86-64.

Downloaded from ${DOWNLOAD_URL}
SHA-256: ${JULIA_SHA256}

The bundle contains the full Julia binary distribution (bin/, lib/, share/)
plus a test_runtime.jl script for verification.
EOF_NOTES

printf 'Built %s\n' "$BUNDLE_NAME"
printf 'Archive size: %d bytes\n' "$archive_size"
printf 'Output directory: %s\n' "$dist_dir"
find "$dist_dir" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
