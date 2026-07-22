# chatgpt-env

`chatgpt-env` builds reproducible Julia package-environment bundles for Linux x86-64 ChatGPT sandboxes.
Each environment is built from a committed `Project.toml` and `Manifest.toml` using Julia 1.12.4 on a GitHub-hosted Linux runner.
The repository keeps a small number of workflow-oriented environments rather than creating one environment for every downstream project.

## Environments

| Environment | Purpose |
|---|---|
| `docs-and-eda` | Data wrangling, EDA, plotting, and documentation (CSV, DataFrames, Arrow, Plots, PlotlyJS, Literate, Documenter) |
| `optimisation-and-solver-oss` | Optimisation with open-source solvers only — HiGHS, Ipopt, SCS (JuMP, OrdinaryDiffEq) |
| `optimisation-and-solver-gurobi` | Optimisation with any solver — Gurobi, HiGHS, Ipopt, SCS (JuMP, OrdinaryDiffEq) |
| `power-systems` | Power-systems simulation and analysis (PowerSystems, PowerSimulations, PowerModels, PowerAnalytics, PRAS, Gurobi, HiGHS) |
| `power-systems-dynamics` | Power-systems stack plus dynamic simulation (adds PowerSimulationsDynamics, OrdinaryDiffEq, Sundials) |
| `matlab` | MATLAB interoperability with the optimisation and power-systems stack (MATLAB, JuMP, PowerModels, Gurobi, HiGHS) |

A separate **runtime** workflow (no environment directory) produces a portable Julia 1.12.4 binary archive (`julia-runtime-linux-x86_64-1.12.4.tar.zst`).

The TOML files under `environments/` are the authoritative dependency inputs.
Generated depots and compressed bundles are release assets, not repository source files.

## Build a bundle

All workflows are manual-only.
No workflow runs on push, pull request, or a schedule.

1. Push this repository to GitHub.
2. Open **Actions**.
3. Select the workflow:
   - **Build Julia runtime bundle** — run once per Julia version
   - Any environment workflow — run once per environment
4. Select **Run workflow**.
5. Download the resulting assets from the release created by the workflow.

Each environment workflow calls `scripts/build_environment.sh`.
The runtime workflow calls `scripts/build_runtime_bundle.sh`.

### Example: get a working docs-and-eda bundle

To use the `docs-and-eda` environment in ChatGPT, you need **two** bundles: the Julia runtime (once per Julia version) and the environment itself.

1. Go to [Build Julia runtime bundle](https://github.com/yasirroni/chatgpt-env/actions/workflows/build-runtime.yml) and click **Run workflow**.
   This produces `julia-runtime-linux-x86_64-1.12.4.tar.zst`.
   You only need to do this once — the same runtime works with every environment.

2. Go to [Build docs and eda environment](https://github.com/yasirroni/chatgpt-env/actions/workflows/build-docs-and-eda.yml) and click **Run workflow**.
   This produces `julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst`.

3. Wait for both workflows to finish, then download the assets from their respective Releases pages.

You now have the engine (runtime) and the fuel (environment).
Upload both to ChatGPT as described under [Use in ChatGPT](#use-in-chatgpt).

The same pattern applies to any other environment: run the runtime workflow once, then run the environment workflow for the environment you need.

## Build process

A workflow:

1. installs Julia 1.12.4 on Ubuntu x86-64;
2. creates a clean environment-specific Julia depot;
3. instantiates the exact committed manifest;
4. precompiles and loads direct dependencies;
5. validates package loading again with Julia package offline mode enabled;
6. removes transient `logs/`, `clones/`, and `dev/` directories;
7. creates a `.tar.zst` archive and SHA-256 metadata; and
8. publishes the result as a GitHub Release.

Compiled caches use `JULIA_CPU_TARGET=generic` so they are not tied to a particular x86-64 CPU model.

The **runtime** workflow follows a simpler process: it downloads the official Julia tarball from `julialang.org`, verifies the SHA-256 checksum, adds a `test_runtime.jl` script, creates a `.tar.zst` archive, and publishes the release.

## Bundle size

All current bundles fit under 512 MiB and are published as single `.tar.zst` files:

```text
julia-runtime-linux-x86_64-1.12.4.tar.zst
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst
```

Each release also includes a `.sha256` checksum file for verification.

If a bundle exceeds 512 MiB, the build script automatically splits it into 500 MiB parts (`.part-001`, `.part-002`, ...) and publishes a `.parts.txt` manifest with the reconstruction command and per-part checksums.
The split parts are named `julia-env-<name>-linux-x86_64-julia-1.12.4.part-001` (no intermediate `.tar.zst`) so ChatGPT does not misidentify the file type.

## Use in ChatGPT

### Download from GitHub

Each workflow publishes a GitHub Release with the bundle archive and metadata.

1. Open your repository on **github.com**.
2. Go to the **Releases** page.
3. Find the release for the runtime and the environment you need.
4. Download the `.tar.zst` asset(s) to your local machine.

The release tag follows the format `julia-1.12.4-<env>-run-<run_number>-<attempt>`.

Example release (docs-and-eda):

- Release page: [julia-1.12.4-docs-and-eda](https://github.com/yasirroni/chatgpt-env/releases/tag/julia-1.12.4-docs-and-eda-run-1-1)
- Direct download: [julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst](https://github.com/yasirroni/chatgpt-env/releases/download/julia-1.12.4-docs-and-eda-run-1-1/julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst)

The runtime release follows the same pattern:

- Release page: [julia-1.12.4-runtime](https://github.com/yasirroni/chatgpt-env/releases/tag/julia-1.12.4-runtime-run-2-1)
- Direct download: [julia-runtime-linux-x86_64-1.12.4.tar.zst](https://github.com/yasirroni/chatgpt-env/releases/download/julia-1.12.4-runtime-run-2-1/julia-runtime-linux-x86_64-1.12.4.tar.zst)

Download the **runtime bundle** once per Julia version, plus one **environment bundle** per project.
Example downloaded files:

```text
julia-runtime-linux-x86_64-1.12.4.tar.zst
julia-runtime-linux-x86_64-1.12.4.tar.zst.sha256
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst.sha256
```

To verify checksums locally before uploading:

```sh
sha256sum -c *.sha256
```

### Store the bundles in ChatGPT Library

ChatGPT saves uploaded and generated files to **Library**, where they can be found and reused in later chats.
Library is available from the sidebar on ChatGPT web.

1. Open **Library**.
2. Select **Upload**, or drag the downloaded files into Library.
3. Upload the runtime archive (`julia-runtime-linux-x86_64-1.12.4.tar.zst`), environment archive (`julia-env-<name>-linux-x86_64-julia-1.12.4.tar.zst`), and optionally their `.sha256` files.
4. Keep the published filenames unchanged so the checksum instructions continue to match.

Files uploaded in a Temporary Chat are not saved to Library.
For current Library behaviour and limits, see [File storage and Library in ChatGPT](https://help.openai.com/en/articles/20001052-file-storage-and-library-in-chatgpt).

### Add the bundles to a ChatGPT Project

A file stored in Library is not automatically a source for every ChatGPT Project.
For project work, add the required runtime and environment files to the Project before starting the working chat:

1. Open the Project.
2. In the Project sources area, select **Add source**.
3. Choose **Add from Library** and select the runtime, environment, and checksum files required for the work.
4. If **Add from Library** is not available in the current interface, upload the same files directly to the Project sources area.
5. Confirm that the files appear in the Project sources list.

Do not assume that a Project chat can materialise and extract a binary archive merely because the archive exists in Library.
Add the archive as a Project source or attach it directly to the current chat.
For general Project file behaviour, see [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt).

### Refer to Library files with `@`

In interfaces that provide the file picker, type `@` in the chat composer and select the uploaded file or folder.
This is a quick way to identify the intended source without typing its full name.

The available `@` items can vary by ChatGPT surface, plan, and workspace configuration.
If the required item is not offered, use the attachment menu and select **Add from Library**.
For a Project workflow, `@` is a reference shortcut; it does not replace adding required binary bundles to the Project sources.

### Start the ChatGPT task

After attaching the files to the current chat or adding them to the Project sources, paste the prompt below.

Before sending it, replace each `[EDIT: ...]` field.
Type `@` and select the corresponding Library file, folder, or Project source when the picker is available.

```text
Use these sources:

- Julia runtime: [EDIT: type @ and select the runtime archive, checksum file, or containing folder]
- Julia environment: [EDIT: type @ and select the environment archive, checksum file, or containing folder]
- Project files or script: [EDIT: type @ and select the project folder or file, or write "none"]

Materialise all required runtime and environment archives and checksum files under `/mnt/data/chatgpt-env-inputs`.

If SHA-256 checksum is provided, verify the checksum of every archive before extraction.
If an archive is split into `.part-*` files, follow the `.parts.txt` manifest to reconstruct the complete `.tar.zst` first.

Extract the runtime and environment under `/mnt/data/chatgpt-env-extracted`.
Identify the exact extracted runtime and environment paths instead of assuming their directory names.

Use the bundled Julia executable, not a system Julia installation.
Set `JULIA_DEPOT_PATH` to the extracted environment depot and set `JULIA_PKG_OFFLINE=true`.

If no project files or scripts provided, run a small Julia command with `--project` pointing to the extracted environment to confirm the Julia version, active project, and package status. If project files or scripts is provided, read and run the julia scripts.


Report:

1. the materialised files;
2. checksum and (if applicable) reconstruction results;
3. extracted runtime and environment paths;
4. the Julia version and active project;
5. the validation command and result; and
6. any package-loading failure or fallback action.
```

The prompt deliberately asks ChatGPT to discover the materialised and extracted paths.
Files referenced from Library or Project sources are not guaranteed to appear under their display names in `/mnt/data`.

### Extract and use

If the archives have already been materialised inside the ChatGPT sandbox, the following commands perform the checksum, extraction, and activation steps.
For split archives, reconstruct the complete `.tar.zst` first by following the `.parts.txt` manifest.

Edit the `SCRIPT` value near the end of the block, or omit the final command when no project script should be run.

```sh
export INPUT=/mnt/data/chatgpt-env-inputs
export EXTRACT=/mnt/data/chatgpt-env-extracted

mkdir -p "$EXTRACT"

# Verify all uploaded checksum files
cd "$INPUT"
sha256sum -c ./*.sha256

# Locate the complete archives
RUNTIME_ARCHIVE=$(find "$INPUT" -maxdepth 1 -type f -name 'julia-runtime-*.tar.zst' -print -quit)
ENV_ARCHIVE=$(find "$INPUT" -maxdepth 1 -type f -name 'julia-env-*.tar.zst' -print -quit)

test -n "$RUNTIME_ARCHIVE"
test -n "$ENV_ARCHIVE"

# Extract runtime
tar -I zstd -xf "$RUNTIME_ARCHIVE" -C "$EXTRACT"

# Extract environment
tar -I zstd -xf "$ENV_ARCHIVE" -C "$EXTRACT"

# Find the extracted directory names
JULIA_DIR=$(find "$EXTRACT" -maxdepth 1 -type d -name 'julia-runtime-*' -print -quit)
ENV_DIR=$(find "$EXTRACT" -maxdepth 1 -type d -name 'julia-env-*' -print -quit)

test -n "$JULIA_DIR"
test -n "$ENV_DIR"

# Set the bundled environment
export JULIA_DEPOT_PATH="$ENV_DIR/depot"
export JULIA_PKG_OFFLINE=true

JULIA_BIN="$JULIA_DIR/julia/bin/julia"

# Validate the runtime and project activation
"$JULIA_BIN" "$JULIA_DIR/test_runtime.jl"
"$JULIA_BIN" --project="$ENV_DIR/environment" -e '
using Pkg
println("Julia version: ", VERSION)
println("Active project: ", Base.active_project())
Pkg.status()
'

# EDIT: replace this with the materialised project script path
SCRIPT=/mnt/data/path/to/script.jl

# Run the project script; omit these lines when no script should be run
test -f "$SCRIPT"
"$JULIA_BIN" --project="$ENV_DIR/environment" "$SCRIPT"
```

### Quick validation

For local validation, use:

```sh
"$JULIA_DIR/julia/bin/julia" "$JULIA_DIR/test_runtime.jl"
```

This should print the Julia version, architecture (`x86_64`), and depot path.

## Licensed or external software

### MATLAB

The GitHub-hosted runner does not contain a licensed MATLAB installation.
The `matlab` workflow therefore instantiates package sources with package build scripts disabled and skips loading `MATLAB.jl`.
The resulting bundle preserves the Julia environment, but it does not provide MATLAB itself and cannot validate MATLAB Engine integration.

### Gurobi

The relevant environments include `Gurobi.jl` and its binary artifact.
Running licensed Gurobi optimisation still requires a valid Gurobi licence.

## Local validation

Repository structure, TOML consistency, workflow coverage, and manual-only triggers can be checked without Julia:

```sh
make validate
```

Building an environment locally is intentionally restricted to Linux x86-64:

```sh
scripts/build_environment.sh docs-and-eda
```

On an Apple Silicon Mac, use the GitHub Actions workflows rather than producing a ChatGPT bundle locally.

## Contributing

### Shell scripts

Executable shell scripts must be committed with Git mode `100755`.

```sh
git update-index --chmod=+x path/to/script.sh
git ls-files --stage path/to/script.sh
```
