# Patch and validate the supplied PISP.jl repository

<context>

Materialise and patch the supplied PISP.jl repository using files under `/mnt/data`.

Expected inputs:

```text
# directly passed to the chat
/mnt/data/pisp-<date-or-version>.zip

# optional task, if not exist use the blank kanban-card.md
/mnt/data/<task-card>.md

# runtime
/mnt/data/julia-runtime-linux-x86_64-1.12.4.tar.zst
/mnt/data/julia-env-pisp-linux-x86_64-julia-1.12.4.tar.zst

# gitignored pisp data
/mnt/data/2024-isp-model.zip
/mnt/data/2024-isp-generation-and-storage-outlook.zip
/mnt/data/2024-pisp-downloads-Auxiliary.zip
/mnt/data/2026-isp-model.zip
/mnt/data/2026-isp-generation-and-storage-outlook.zip
/mnt/data/pisp-downloads-2024-xls.zip
/mnt/data/pisp-downloads-2026-xls.zip
```

A repository example that is zipped and passed directly to chat is:

```text
/mnt/data/pisp-260728-v5.zip
```

The prompt will always be accompanied by the latest PISP.jl repository ZIP and may also include one task card.

Do not use Quarto for PISP.jl works.

</context>

<artefact_roles>

## Artefact roles

* `pisp-<date-or-version>.zip` contains the authoritative PISP.jl repository baseline.
* The optional task card defines additional or narrower work.
* `julia-runtime-linux-x86_64-1.12.4.tar.zst` contains the bundled Julia runtime.
* `julia-env-pisp-linux-x86_64-julia-1.12.4.tar.zst` contains the offline PISP environment used for package loading and documentation rendering.
* The ISP model and outlook ZIPs contain local source data used for execution and validation.
* `2024-pisp-downloads-Auxiliary.zip` contains PISP-generated preprocessing intermediates, not original AEMO publications.

Local data may be extracted into the working tree for execution, but it is not repository deliverable content.

</artefact_roles>

<authority>

## Authority

Use instructions in this order:

1. safety, cleanup, and packaging rules in this prompt;
2. repository-local instructions, including `AGENTS.md`;
3. the accompanying task card, when supplied;
4. implementation, tests, and documentation in the supplied repository;
5. supporting runtime, environment, and data inputs;
6. generic skill conventions.

Use the newest user-supplied PISP.jl ZIP as the baseline.

Do not patch an older assistant-generated copy when a newer user-supplied repository is available.

Before extraction, state the exact selected repository ZIP path.

Do not add the external task card to the repository unless the task explicitly requires it.

</authority>

<workspace>

## Workspace

Use a fresh run-specific workspace:

```text
/mnt/data/apply_zip_patch/runs/<unique-run>/
├── original/
├── work/
├── changed/
└── reports/
```

Definitions:

* `original/` — safely extracted and immutable repository baseline;
* `work/` — current editable working tree;
* `changed/` — cumulative additions and modifications relative to `original/`;
* `reports/` — temporary execution and validation output, not repository content.

Requirements:

1. locate the actual repository ZIP under `/mnt/data`;
2. validate its member paths before extraction;
3. extract it into `original/`;
4. identify the actual repository root;
5. confirm expected repository files exist;
6. copy `original/` to `work/` using a real recursive filesystem copy;
7. never edit files under `original/`;
8. perform all repository edits under `work/`.

</workspace>

<archive_cleanup>

## Delete input ZIPs after extraction

After each selected input archive has been successfully extracted:

1. confirm the expected extracted files or directories exist;
2. record the original input path in the run notes;
3. immediately delete that exact input archive from `/mnt/data`;
4. delete any temporary or reconstructed copy of that archive.

Apply this to the selected:

* PISP.jl repository ZIP;
* Julia runtime archive;
* Julia environment archive;
* data ZIPs used by this run.

Do not retain an input ZIP merely for later reporting.

Do not delete:

* unrelated ZIPs that were not selected for this run;
* archives whose extraction has not succeeded;
* the final worktree ZIP;
* the final cumulative-changes ZIP.

Deleting an input archive must not delete or alter the extracted files.

</archive_cleanup>

<task>

## Main task

1. Materialise the bundled Julia runtime and offline PISP environment.
2. Inspect the extracted PISP.jl repository before editing.
3. Populate local edition data only when required for execution or validation.
4. Execute the optional task card when supplied.
5. Correct only verified defects or explicitly requested behaviour.
6. Preserve already-correct implementation.
7. Run relevant package and Literate checks. Run Documenter only when HTML output or HTML-specific validation is in scope.
8. Audit documentation changes.
9. Return:

   * the latest clean state of `work/`;
   * the cumulative changes between `original/` and `work/`.

</task>

<skills>

## Skills

Use relevant installed skills, particularly:

* `julia-runtime-chatgpt`;
* `apply-zip-patch`;
* `project-folder-structure`;
* `docs-writing`;
* `docs-data-writing`;
* `docs-audit`;
* `docs-writing-chatgpt`;
* `preservation-first-surgical-editing`;
* `julia-literate-documenter`.

Apply the Documenter stage of `julia-literate-documenter` only when HTML output
or HTML-specific validation is in scope.

For documentation work, follow:

```text
write
→ render
→ audit
→ repair
→ rebuild
→ re-audit
```

</skills>

<runtime>

## Julia runtime

Use only the supplied Julia runtime and offline environment.

Discover the exact:

* Julia executable;
* environment project;
* Julia depot.

Set:

```sh
JULIA_DEPOT_PATH=<exact-extracted-depot>
JULIA_PKG_OFFLINE=true
```

For documentation-only work, activate the packaged PISP environment directly:

```sh
<bundled-julia> --project=<exact-extracted-pisp-environment> ...
```

Do not activate the uploaded repository's `Project.toml` or `docs/Project.toml` merely to render documentation. Those environments may select the uploaded PISP source tree and invalidate the packaged PISP cache.

Do not run `Pkg.precompile()` by default. When no files under `src/` have changed, use the packaged PISP installation and its existing cache; PISP precompilation is not required for documentation-only work.

When PISP source code has changed, point the active environment to that repository source and allow Julia to invalidate or rebuild the package cache automatically when required. An explicit `Pkg.precompile()` command is still unnecessary unless the task specifically requires preparing a reusable cache.

First test:

```julia
using PISP
using Literate
```

When no files under `src/` changed, use the exact extracted runtime,
environment, and depot for a documentation-only render. Select one or more
affected pages explicitly by their stable IDs from
`docs/page-registry.toml`; separate multiple IDs with commas.

```sh
PISP_REPO="<exact-extracted-pisp-repository-root>"
JULIA_BIN="<exact-bundled-julia-executable>"
PISP_ENV="<exact-extracted-pisp-environment-directory>"
PISP_DEPOT="<exact-extracted-pisp-depot>"
PISP_PAGE_IDS="<page-id-1>,<page-id-2>"

# Example:
# PISP_PAGE_IDS="isp2024-parameters-and-mappings,isp2024-temperature-data-coverage"

(
    set -eu
    cd "$PISP_REPO"

    test -x "$JULIA_BIN" || {
        printf '%s\n' "bundled Julia executable not found: $JULIA_BIN" >&2
        exit 1
    }
    test -f "$PISP_ENV/Project.toml" || {
        printf '%s\n' "packaged PISP Project.toml not found under: $PISP_ENV" >&2
        exit 1
    }
    test -d "$PISP_DEPOT" || {
        printf '%s\n' "packaged Julia depot not found: $PISP_DEPOT" >&2
        exit 1
    }
    test -f "docs/render_literate.jl" || {
        printf '%s\n' "PISP docs renderer not found under: $PISP_REPO" >&2
        exit 1
    }
    test -n "$PISP_PAGE_IDS" || {
        printf '%s\n' "PISP_PAGE_IDS must contain one or more registry page IDs" >&2
        exit 1
    }

    # Prevent inherited selectors or project settings from changing the command.
    unset JULIA_PROJECT PISP_LITERATE_SET PISP_DOCS_TRACK
    export JULIA_DEPOT_PATH="$PISP_DEPOT"
    export JULIA_LOAD_PATH="@:@stdlib"
    export JULIA_PKG_OFFLINE=true
    export JULIA_PKG_PRECOMPILE_AUTO=0

    # Prove that Julia selected the packaged environment and packaged PISP,
    # rather than the repository root or docs/ environment.
    "$JULIA_BIN" \
        --startup-file=no \
        --history-file=no \
        --compiled-modules=existing \
        --project="$PISP_ENV" \
        -e '
            expected_project = realpath(joinpath(ARGS[1], "Project.toml"))
            active_project = realpath(Base.active_project())
            active_project == expected_project || error(
                "wrong active project: $active_project; expected $expected_project",
            )

            using PISP
            using Literate

            loaded_pisp = realpath(pathof(PISP))
            loaded_literate = realpath(pathof(Literate))
            repository_pisp = realpath(joinpath(ARGS[2], "src", "PISP.jl"))
            loaded_pisp == repository_pisp && error(
                "the packaged environment resolved PISP from the editable repository",
            )

            println("active_project=", active_project)
            println("pisp_source=", loaded_pisp)
            println("pisp_version=", pkgversion(PISP))
            println("literate_source=", loaded_literate)
        ' "$PISP_ENV" "$PISP_REPO"

    # Render only the explicitly selected affected pages.
    PISP_LITERATE_PAGES="$PISP_PAGE_IDS" \
    "$JULIA_BIN" \
        --startup-file=no \
        --history-file=no \
        --compiled-modules=existing \
        --project="$PISP_ENV" \
        docs/render_literate.jl
)
```

Do not invoke `docs/render_literate.jl` without `PISP_LITERATE_PAGES` during a
targeted documentation task. An omitted selector renders the default published
set and may require unrelated local data.

Choose affected page IDs as follows:

* when one or more registered files under `docs/literate/` changed, select the
  corresponding `id` values from `docs/page-registry.toml`;
* when a shared documentation helper, package behaviour, or local input changed,
  identify every registry page whose generated evidence depends on that change
  and list all of those IDs explicitly;
* when only handwritten Markdown under `docs/src/` changed, do not run Literate;
* use `docs/render_changed.jl` only in a real Git checkout and only as a
  convenience for direct `docs/literate/**/*.jl` edits. It does not detect all
  pages affected by shared helpers, package code, or data changes.

A proper subset of selected pages updates its outputs in place and does not
provide the atomic full-set replacement used by a complete published render.
If the explicit IDs happen to equal the complete published registry set, the
renderer switches to its full-set staging and atomic-replacement path. For a
targeted subset, inspect every selected generated Markdown file and figure
before accepting the result.

If repository policy requires a complete published render before commit, report
that full-set check as not run when its unrelated data prerequisites are
unavailable. Do not present a selected-page render as full-set validation.

The `--compiled-modules=existing` option makes this docs-only path consume the
already packaged caches without creating a replacement compiled-module cache.
When no files under `src/` changed, this path does not require `Pkg.precompile()`.
If the supplied existing cache cannot be loaded, treat that as a runtime or
environment materialisation problem; do not silently switch to the repository
or `docs/` environment.

If a supplied cache refers to build-time absolute paths, create compatibility
paths outside the repository only after verifying that each target is absent
and that every link resolves to the extracted runtime or environment. Never
overwrite an existing system path, and never package these compatibility links.

When files under `src/` changed and the generated documentation must reflect
those changes, do not use the packaged-PISP command above. Point a copied
environment explicitly to the editable repository source, keep resolution
offline, and let Julia invalidate or rebuild the affected package cache on the
next load. Do not run `Pkg.precompile()` manually unless the task specifically
requires producing a reusable cache.

Load `Documenter` only when an HTML site or HTML-specific behaviour must be built or checked.

Run `Pkg.instantiate()` only when required by the repository environment and keep package resolution offline.

Do not silently use:

* system Julia;
* online package resolution;
* another environment;
* another depot.

Do not copy runtime, environment, depot, cache, or precompilation files into the repository deliverables.

</runtime>

<repository_inspection>

## Inspect before editing

Inspect at least:

```text
AGENTS.md
.gitignore                              # when present
README.md
Project.toml
docs/README.md
docs/Project.toml
docs/edition_profiles.jl
docs/render_literate.jl
docs/make.jl
docs/navigation.jl
docs/page-registry.toml
docs/literate/
docs/src/
docs/test/
src/
test/
```

Also inspect relevant preprocessing code, including:

```text
src/scrappers/PISP-scrapper-build.jl
```

Search for:

```text
pisp-downloads
pisp-datasets
Auxiliary
Core
Sensitivities
Core scenarios
Traces
```

Reject newly introduced inverted paths:

```text
data/pisp-downloads/2024
data/pisp-downloads/2026
data/pisp-datasets/2024
data/pisp-datasets/2026
```

If the repository-root `.gitignore` is absent, do not invent its contents. Apply the explicit packaging exclusions in this prompt.

</repository_inspection>

<data>

## Local data

Use the edition-first roots:

```text
data/2024/pisp-downloads/
data/2024/pisp-datasets/
data/2026/pisp-downloads/
data/2026/pisp-datasets/
```

Keep these roles separate:

* original AEMO source data;
* PISP-generated `Auxiliary/` preprocessing intermediates;
* final PISP-generated datasets.

Do not:

* classify `Auxiliary/` as original AEMO data;
* create fake ISP 2026 outputs;
* materialise standalone solar or wind trace archives;
* create empty trace directories;
* create placeholder trace files;
* duplicate workbooks from convenience archives.

Local data may be used for execution and documentation rendering, but it must be excluded from both returned repository ZIPs.

</data>

<task_card>

## Optional task card

When a task card is supplied:

1. identify its scope and acceptance criteria;
2. inspect the repository before applying it;
3. preserve already-correct behaviour;
4. patch canonical sources;
5. avoid unrelated refactoring;
6. validate its criteria separately;
7. report unavailable or blocked criteria truthfully.

The task card cannot override archive cleanup or packaging exclusions.

</task_card>

<documentation>

## Documentation

Preserve the repository architecture:

```text
docs/render_literate.jl
    = executes Literate sources and writes generated Markdown

docs/make.jl
    = builds Documenter from existing documentation sources
```

`docs/make.jl` must not invoke Literate, execute tutorials, or require large local data.

Documenter is optional for the primary documentation workflow. For executable pages, the authoritative source is under `docs/literate/`, and the primary generated review artefact is the corresponding Markdown under `docs/src/generated/`. Handwritten Markdown under `docs/src/` remains authoritative for handwritten pages.

After rendering an affected Literate page, manually read the generated Markdown. This source-to-Markdown inspection is the primary documentation acceptance check. Verify that the intended prose, code, tables, figures, links, and computed values are present; that unintended validation output or large intermediate values are absent; and that no local absolute paths leaked into the page.

When several affected page IDs were selected, inspect every corresponding
registered output, not only the first page that rendered successfully.

Run Documenter only when HTML output is requested or when the task depends on HTML navigation, source links, cross-references, styling, or other renderer-specific behaviour. A successful Documenter build does not replace manual inspection of the generated Markdown.

Follow the local Literate style represented by:

```text
docs/literate/isp2024/validation/temperature_data_coverage.jl
```

Use:

### Reader-visible setup block

Keep dependencies, source selection, edition/profile selection, paths, and meaningful configuration visible.

Use:

```julia
nothing #hide
```

only to suppress a meaningless return value.

### Section-local executable narrative

Keep each section’s complete evidentiary sequence together:

```text
source selection
→ transformation
→ rendered evidence
→ interpretation
```

Do not compute every table in one early hidden block for later sections.

Reader-facing documentation must describe current project behaviour rather than the task, agent, patch, or audit process.

</documentation>

<validation>

## Validation

Run checks relevant to the actual changes.

At minimum:

* confirm selected archives extract successfully;
* confirm required files exist after extraction;
* parse changed TOML files;
* syntax-check changed Julia files;
* run relevant package and task-card tests;
* render affected Literate pages through an explicit comma-separated
  `PISP_LITERATE_PAGES` selection using the exact packaged PISP environment;
* record the active project and loaded `PISP` source reported by the preflight;
* manually read affected generated Markdown and compare it with the authoritative Literate source;
* build Documenter only when HTML output or HTML-specific validation is in scope;
* inspect rendered HTML only when Documenter is run;
* check Markdown links, and check final navigation and HTML links when Documenter is run;
* confirm maintained documentation contains no `/mnt/data/` paths;
* confirm `original/` remains unchanged;
* confirm both returned ZIPs exclude local ignored data;
* validate both returned ZIPs before linking them.

Run detailed checksums, duplicate-content investigations, or manifest reporting only when required by the repository, task card, or an observed problem.

Do not describe static inspection as a successful render or build.

</validation>

<packaging>

## Packaging exclusions

Exclude these paths from both returned ZIPs:

```text
data/2024/pisp-downloads/
data/2024/pisp-datasets/
data/2026/pisp-downloads/
data/2026/pisp-datasets/

.git/
.julia/
docs/build/
artifacts/
compiled/
scratchspaces/
logs/
tmp/
temp/
cache/
__pycache__/
.pytest_cache/
.mypy_cache/
.venv/
node_modules/
build/
dist/
coverage/
.DS_Store
__MACOSX/
._*
```

Also exclude:

* runtime files;
* environment files;
* Julia depot contents;
* package caches;
* precompilation output;
* input archives;
* local data archives;
* validation staging files;
* files outside the repository root.

A file’s presence under `work/` does not automatically authorise packaging it.

</packaging>

<deliverables>

No matter what, Deliverable must be provided, as zipped package, even when the `work/` is not yet finished or facing a blocker.

## Deliverable 1 — latest clean worktree

Return:

```text
PISP-jl-worktree-<UTC-timestamp>-<short-hash>.zip
```

This ZIP represents the latest maintained state of `work/`.

It must contain:

* the original repository source tree;
* intended additions and modifications;
* intended current repository documentation, tests, scripts, and configuration.

It must exclude all paths listed under `<packaging>`.

This is a **source-only worktree snapshot**. It is not self-contained with respect to ignored local ISP data.

## Deliverable 2 — cumulative changes

Return:

```text
PISP-jl-changes-<UTC-timestamp>-<short-hash>.zip
```

This ZIP contains only files that are:

* new in `work/`; or
* different in content from their corresponding file in `original/`.

The comparison is cumulative from the supplied repository baseline, not only from the latest editing step.

Do not include unchanged files.

Preserve repository-relative paths.

If files were deleted or renamed, list those operations in the final response because a ZIP overlay cannot directly remove an old path.

## ZIP validation

Before returning either ZIP:

1. inspect its member list;
2. confirm excluded paths are absent;
3. confirm the changes ZIP contains no unchanged files;
4. run `unzip -t` or an equivalent integrity check;
5. confirm the exact output path exists.

</deliverables>

<failure_handling>

## Failure handling

Do not ask for confirmation unless a required input remains unavailable after checking the supplied resources.

When a check cannot run:

* continue with independent checks;
* distinguish unavailable validation from failed validation;
* do not claim success for the unavailable layer;
* return the safest useful partial result when possible.

Do not weaken repository correctness merely to make a local test pass.

</failure_handling>

<final_report>

## Final response

Lead with exactly one status:

```text
PASS
PARTIAL
BLOCKED
FAIL
```

Report:

* exact selected `/mnt/data/pisp-...zip` input path;
* selected task-card path, when supplied;
* repository root;
* files added, modified, deleted, or renamed;
* relevant test results;
* selected Literate page IDs and their registered generated outputs;
* exact active Julia project and loaded `PISP` source used for the render;
* Literate result for every selected page;
* manual generated-Markdown inspection result;
* Documenter result when run, or `not run: optional and not required for this task`;
* checks that could not run;
* confirmation that ignored PISP data is absent from both ZIPs;
* confirmation that the worktree ZIP represents the latest maintained `work/`;
* confirmation that the changes ZIP is cumulative from `original/`;
* confirmation that selected input archives were deleted after successful extraction;
* ZIP integrity results;
* both download links.

Keep private reasoning, setup narration, and correction history out of repository documentation.

</final_report>
