# chatgpt-env

`chatgpt-env` builds reproducible Julia package-environment bundles for Linux
x86-64 ChatGPT sandboxes. Each environment is built from a committed
`Project.toml` and `Manifest.toml` using Julia 1.12.4 on a GitHub-hosted Linux
runner.

The repository keeps a small number of workflow-oriented environments rather
than creating one environment for every downstream project.

## Environments

| Environment | Purpose |
|---|---|
| `docs-and-eda` | Documentation, tables, data formats, plotting, and exploratory analysis |
| `optimisation-and-solver-oss` | JuMP, open-source solvers, differential equations, and common analysis packages |
| `optimisation-and-solver-gurobi` | Optimisation environment including Gurobi |
| `optimisation-and-solver` | Current general optimisation environment; presently identical to the Gurobi variant |
| `power-systems` | PowerSystems.jl, PowerSimulations.jl, PowerModels, reliability, and supporting tools |
| `power-systems-dynamics` | Power-systems stack plus dynamic simulation packages |
| `matlab` | MATLAB interoperability and the optimisation/power-model stack |

The TOML files under `environments/` are the authoritative dependency inputs.
Generated depots and compressed bundles are release assets, not repository
source files.

## Build a bundle

Every workflow is manual-only. No workflow runs on push, pull request, or a
schedule.

1. Push this repository to GitHub.
2. Open **Actions**.
3. Select the environment workflow.
4. Select **Run workflow**.
5. Download the resulting assets from the release created by the workflow.

Each environment has its own workflow, while all workflows call the same
`scripts/build_environment.sh` implementation.

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

Compiled caches use `JULIA_CPU_TARGET=generic` so they are not tied to a
particular x86-64 CPU model.

## Bundle size

A bundle smaller than 512 MiB is published as one archive:

```text
julia-env-docs-and-eda-linux-x86_64-julia-1.12.4.tar.zst
```

A larger archive is automatically split into parts below the per-file limit.
The release includes a `.parts.txt` file containing the reconstruction command,
part sizes, part checksums, and the expected checksum of the reconstructed
archive.

## Use in ChatGPT

Extract the Julia runtime and one environment bundle to stable paths. Point
`JULIA_DEPOT_PATH` at the bundled depot and run downstream projects with the
bundled environment:

```sh
export JULIA_DEPOT_PATH=/mnt/data/julia-env-docs-and-eda/depot
export JULIA_PKG_OFFLINE=true

/path/to/julia/bin/julia \
  --project=/mnt/data/julia-env-docs-and-eda/environment \
  project-script.jl
```

Do not run `Pkg.instantiate()` or `Pkg.precompile()` during routine ChatGPT use
unless package loading fails.

## Licensed or external software

### MATLAB

The GitHub-hosted runner does not contain a licensed MATLAB installation.
The `matlab` workflow therefore instantiates package sources with package build
scripts disabled and skips loading `MATLAB.jl`. The resulting bundle preserves
the Julia environment, but it does not provide MATLAB itself and cannot validate
MATLAB Engine integration.

### Gurobi

The relevant environments include `Gurobi.jl` and its binary artifact. Running
licensed Gurobi optimisation still requires a valid Gurobi licence.

## Local validation

Repository structure, TOML consistency, workflow coverage, and manual-only
triggers can be checked without Julia:

```sh
make validate
```

Building an environment locally is intentionally restricted to Linux x86-64:

```sh
scripts/build_environment.sh docs-and-eda
```

On an Apple Silicon Mac, use the GitHub Actions workflows rather than producing
a ChatGPT bundle locally.
