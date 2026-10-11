# ManimGX's tasks: `just` lists them. The GitHub workflows run these same recipes, so a task
# does the same on your machine as in CI.

# List the recipes
[private]
default:
    @just --list

# Development:

# Make .venv and install the browser package's locked development tools
[group('development')]
sync:
    uv sync
    cd browser && bun install --frozen-lockfile

# Update uv.lock after a change to pyproject.toml's dependencies
[group('development')]
lock:
    uv lock

# Upgrade the locked Python and Rust dependencies to the newest versions the manifests allow
[group('development')]
upgrade:
    uv lock --upgrade
    cargo update --manifest-path rust/Cargo.toml
    uv run --frozen scripts/release/licenses.py

# Write the wheels' third-party licenses (LICENSE-THIRD-PARTY), checking ManimGX's `license`
[group('development')]
licenses:
    uv run --frozen scripts/release/licenses.py

# Format the code: ruff's fixes and formatter, and Prettier for the browser package
[group('development')]
format:
    uv run --frozen ruff check --fix
    uv run --frozen ruff format
    cd browser && bun install --frozen-lockfile && bun run format

# Format one file or directory
[group('development')]
format-file target:
    uv run --frozen ruff check --fix {{ target }}
    uv run --frozen ruff format {{ target }}

# Run every pre-commit check: formatting, linting, type checking, licensing and the files' hygiene
[group('development')]
check:
    uv run --frozen prek run --all-files --show-diff-on-failure

# Check the browser package's TypeScript and formatting with its locked tools
[group('development')]
check-typescript:
    cd browser && bun install --frozen-lockfile && bun run check

# Check the browser engine without the native extension's features (target installed by CI)
[group('development')]
check-rust-web:
    cargo check --locked --manifest-path rust/Cargo.toml -p manimgx-engine \
        --target wasm32-unknown-unknown --no-default-features --features web

# Testing:

# Run the tests in parallel; arguments go to pytest (`just test tests/docs -x`)
[group('testing')]
test *args:
    uv run --frozen pytest -n auto {{ args }}

# Test the Rust core and native libraries; the installed-wheel suite tests Python's bindings
[group('testing')]
test-rust:
    cargo test --locked --release --manifest-path rust/Cargo.toml --workspace \
        --no-default-features \
        --features manimgx-engine/render,manimgx-engine/export,manimgx-engine/typeset,manimgx-engine/player

# Exercise native browser ownership with real Web Audio (wasm-bindgen-test-runner and a browser driver).
[group('testing')]
test-rust-web:
    CARGO_TARGET_WASM32_UNKNOWN_UNKNOWN_RUNNER=wasm-bindgen-test-runner \
        cargo test --locked --manifest-path rust/Cargo.toml -p manimgx-engine \
        --target wasm32-unknown-unknown --no-default-features --features web --lib

# Test the browser package, its worker and declarations, and the corpus review panel
[group('testing')]
test-typescript:
    cd browser && bun install --frozen-lockfile && bun run test
    cd tests/integration/review/web && bun install --frozen-lockfile && bun run test

# Run the tests and measure their coverage: a summary here, every line in htmlcov/
[group('testing')]
test-coverage *args:
    MANIMGX_COVERAGE_SOURCE="$(uv run --frozen python -c 'import manimgx; print(manimgx.__path__[0])')" \
        uv run --frozen pytest -n auto --cov --cov-report=term --cov-report=html {{ args }}

# Combine the coverage of several test runs (their .coverage.* files) into htmlcov/ and a table
[group('testing')]
combine-coverage directory:
    uv run --frozen coverage combine --quiet {{ directory }}
    uv run --frozen coverage html --quiet
    uv run --frozen coverage report --format=markdown

# Run the unit tests' properties on 2,000 examples each (the `thorough` Hypothesis profile)
[group('testing')]
test-thorough *args:
    uv run --frozen pytest -n auto tests/unit --hypothesis-profile=thorough {{ args }}

# Time the benchmarks on this machine: this checkout against REF's ManimGX, main unless named
[group('testing')]
bench ref="main" *args:
    uv run --frozen pytest tests/benchmarks/test_speed.py -n 0 --timeout=3600 --bench={{ ref }} {{ args }}

# (mutmut keeps its mutants in mutants/)
# Run mutation testing on what `[tool.mutmut]` lists: the changes to the code the tests let through
[group('testing')]
mutate *args:
    uv run --frozen --with mutmut mutmut run {{ args }}
    uv run --frozen --with mutmut mutmut results

# Render, compare and review the integration corpus (`just corpus --help`)
[group('testing')]
corpus *args:
    uv run --frozen python -m tests.integration.corpus {{ args }}

# Open the corpus's review panel at http://127.0.0.1:8000
[group('testing')]
review:
    cd tests/integration/review/web && bun install --frozen-lockfile && bun run build
    uv run --frozen fastapi run --host 127.0.0.1 --port 8000

# Docs (their environment is the package and the docs tools; `python -m` puts the repository
# root on the path, which the scripts, `scripts.docs`, and the site's formatter,
# `docs.examples.fence`, are imported from):

# Build the docs site into docs/site/: render its examples, write its reference, build its pages
[group('docs')]
build-docs: render-docs build-docs-pages

# Render missing or changed examples; optional source paths or --jobs limit the work
[group('docs')]
render-docs *args:
    uv run --frozen --no-default-groups --group docs python -m docs.examples {{ args }}

# Build the pages from completed films (CI saves the films before this stage)
[group('docs')]
build-docs-pages:
    uv run --frozen --no-default-groups --group docs python -m scripts.docs.gallery
    uv run --frozen --no-default-groups --group docs python -m scripts.docs.reference
    uv run --frozen --no-default-groups --group docs python -m zensical build --strict \
        --config-file docs/zensical.toml

# (an example that fails to render is reported, and served without its film)
# Serve the docs site at http://localhost:8000, rebuilt as its pages change
[group('docs')]
serve-docs:
    -uv run --frozen --no-default-groups --group docs python -m docs.examples
    uv run --frozen --no-default-groups --group docs python -m scripts.docs.gallery
    uv run --frozen --no-default-groups --group docs python -m scripts.docs.reference
    uv run --frozen --no-default-groups --group docs python -m zensical serve \
        --config-file docs/zensical.toml

# Release:

# (cibuildwheel; `just build-wheel pyodide` builds the browser's)
# Build this machine's wheel into dist/ and test it on every supported Python
[group('release')]
build-wheel platform="auto":
    uvx cibuildwheel@4.2.1 --output-dir dist --platform {{ platform }}

# (the player's element and the director's worker in one file, installing the ManimGX of its version from PyPI;
# with ManimGX's license, which it carries)
# Build the npm package into browser/dist/
[group('release')]
build-npm:
    cd browser && bun install --frozen-lockfile
    cd browser && bun pm pkg set version="$(uv version --short)"
    cp LICENSE browser/LICENSE
    cd browser && bun run build

# Build ManimGX's source distribution into dist/
[group('release')]
build-sdist:
    uv build --sdist --out-dir dist

# (the platform builds' source artifacts merged into release-sources/, with the repository,
# every crate and each checked archive the engine uses. System build tools are prerequisites;
# distribution source RPMs describe the exact libraries bundled by the Linux builds)
# Build the wheels' and launchers' complete source into dist/, from the committed repository
[group('release')]
build-source sources="release-sources": build-sdist
    #!/usr/bin/env bash
    set -euo pipefail
    version="$(uv version --short)"
    sources="$(realpath "{{ sources }}")"
    uv run --no-project scripts/release/linux_sources.py --verify "${sources}"
    uv run --no-project scripts/release/create_executable.py --verify-sources "${sources}"
    work="$(mktemp -d)"
    trap 'rm -rf "${work}"' EXIT
    just _source-tree "${work}/manimgx-${version}"
    cd "${work}/manimgx-${version}"
    cp -R "${sources}" sources
    mkdir .cargo
    cargo vendor --locked --manifest-path rust/Cargo.toml vendor > .cargo/config.toml
    printf '\n[net]\noffline = true\n\n[env]\nMANIMGX_SOURCES = { value = "sources", relative = true }\n' \
        >> .cargo/config.toml
    CARGO_TARGET_DIR="${work}/target" MANIMGX_SOURCES="$PWD/sources" \
        sh scripts/release/build_lavapipe.sh "${work}/lavapipe" --sources-only
    CARGO_TARGET_DIR="${work}/target" uv build --wheel --out-dir "${work}/wheel" .
    tar -cf - -C "${work}" "manimgx-${version}" | xz -T0 -9 \
        > "{{ justfile_directory() }}/dist/manimgx-${version}-source.tar.xz"

# A release's complete project source, including build recipes the pip sdist does not need.
_source-tree directory:
    #!/usr/bin/env bash
    set -euo pipefail
    git diff --quiet HEAD -- || { echo "Commit tracked changes before exporting release source." >&2; exit 1; }
    mkdir -p "{{ directory }}"
    git archive HEAD | tar -xf - -C "{{ directory }}"
    git rev-parse HEAD > "{{ directory }}/SOURCE_COMMIT"

# Build the font packages, their wheels and source distributions, into dist/
[group('release')]
build-fonts:
    uv build --package manimgx-fonts --out-dir dist
    uv build --package manimgx-fonts-cjk --out-dir dist

# Build this machine's executable into dist/ from its wheel in dist/: one file, Python included
[group('release')]
create-executable:
    uv run --no-project scripts/release/create_executable.py

# Build the Docker image of a version published on PyPI
[group('release')]
build-docker-image version:
    docker build --build-arg VERSION={{ version }} --tag ghcr.io/academa-labs/manimgx:{{ version }} \
        docker

# Print a version's section of the changelog: its release notes
[group('release')]
release-notes version:
    awk '/^## / { if (found) exit } $0 == "## {{ version }}" { found = 1; next } found' \
        docs/content/changelog.md

# Tag ManimGX's version and push the tag: the Release workflow publishes it
[confirm("Tag manimgx's version and push the tag?")]
[group('release')]
release:
    git tag --annotate "v$(uv version --short)" --message "manimgx $(uv version --short)"
    git push origin "v$(uv version --short)"
