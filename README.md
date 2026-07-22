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

To use the `docs-and-eda` environment in ChatGPT, you need **two** bundles:
the Julia runtime (once per Julia version) and the environment itself.

1. Go to [Build Julia runtime bundle](https://github.com/yasirroni/chatgpt-env/actions/workflows/build-runtime.yml)
   and click **Run workflow**.
   This produces `julia-runtime-linux-x86_64-1.12.4.tar.zst`.
   You only need to do this once — the same runtime works with every environment.

2. Go to [Build docs and eda environment](https://github.com/yasirroni/chatgpt-env/actions/workflows/build-docs-and-eda.yml)
   and click **Run workflow**.
   This produces `julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst`.

3. Wait for both workflows to finish, then download the assets from their
   respective Releases pages.

You now have the engine (runtime) and the fuel (environment).
Upload both to ChatGPT as described under [Use in ChatGPT](#use-in-chatgpt).

The same pattern applies to any other environment: run the runtime workflow
once, then run the environment workflow for the env you need.

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

A bundle smaller than 512 MiB is published as one archive:

```text
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst
```

A larger archive is automatically split into parts below the per-file limit.
The release includes a `.parts.txt` file containing the reconstruction command, part sizes, part checksums, and the expected checksum of the reconstructed archive.

## Use in ChatGPT

### Download from GitHub

Each workflow publishes a GitHub Release with the bundle archive and metadata.
Tag format: `julia-1.12.4-<env>-run-<run_number>-<attempt>`.

1. Open your repository on **github.com**.
2. Go to the **Releases** page.
3. Find the release for the runtime and the environment you need.
4. Download the `.tar.zst` asset(s) to your local machine.

Download the **runtime bundle** once per Julia version, plus one **environment bundle** per project.
Example downloaded files:

```text
julia-runtime-linux-x86_64-1.12.4.tar.zst
julia-runtime-linux-x86_64-1.12.4.tar.zst.sha256
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst.sha256
```

Verify checksums locally before uploading:

```sh
sha256sum -c *.sha256
```

### Upload to ChatGPT

Open ChatGPT and use the file upload button to attach the downloaded files.
Upload both the runtime bundle and one environment bundle into the same conversation or Project:

1. **Upload** `julia-runtime-linux-x86_64-1.12.4.tar.zst`
2. **Upload** `julia-env-<name>-linux-x86_64-julia-1.12.4.tar.zst`
3. Optionally upload the corresponding `.sha256` files

Include the following prompt when you start working:

> I've uploaded a portable Julia runtime and a project environment bundle.
> Extract both under `/mnt/data`:
>
> ```sh
> tar -I zstd -xf julia-runtime-*.tar.zst -C /mnt/data
> tar -I zstd -xf julia-env-*.tar.zst -C /mnt/data
> ```
>
> Find the extracted directory names and set environment:
>
> ```sh
> JULIA_DIR=$(ls -d /mnt/data/julia-runtime-*)
> ENV_DIR=$(ls -d /mnt/data/julia-env-*)
> export JULIA_DEPOT_PATH="$ENV_DIR/depot"
> export JULIA_PKG_OFFLINE=true
> ```
>
> Use the bundled Julia, not system Julia:
>
> ```sh
> "$JULIA_DIR/julia/bin/julia" --project="$ENV_DIR/environment" script.jl
> ```

### Extract and use

If you prefer to run the extraction steps manually inside ChatGPT instead of using the prompt above:

```sh
export EXTRACT=/mnt/data

# Extract runtime
tar -I zstd -xf julia-runtime-*.tar.zst -C "$EXTRACT"

# Extract environment
tar -I zstd -xf julia-env-*.tar.zst -C "$EXTRACT"

# Find the extracted directory names
JULIA_DIR=$(ls -d "$EXTRACT"/julia-runtime-*)
ENV_DIR=$(ls -d "$EXTRACT"/julia-env-*)

# Set depot path and run
export JULIA_DEPOT_PATH="$ENV_DIR/depot"
export JULIA_PKG_OFFLINE=true

"$JULIA_DIR/julia/bin/julia" \
  --project="$ENV_DIR/environment" \
  script.jl
```

Do not run `Pkg.instantiate()` or `Pkg.precompile()` during routine ChatGPT use unless package loading fails.

### Quick validation

After download and extraction, verify the bundle works:

```sh
"$JULIA_DIR/julia/bin/julia" "$JULIA_DIR/test_runtime.jl"
```

This should print the Julia version, architecture (x86_64), and depot path.

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
