# Project management

## What is project management?

The repository is the package, ManimGX, and holds more than its code:

```text
.
├── src/manimgx/             ← the package: the scene API and the command line
├── rust/                    ← the engine's crates: the engine, compiled into the package as
│                              manimgx._engine, and the crates it is built with from others'
│                              sources, which they fetch
├── tests/                   ← the package's tests and the integration corpus
├── fonts/                   ← the fonts text is set in, packages of their own:
│   ├── manimgx-fonts/         the Noto fonts
│   └── manimgx-fonts-cjk/     Noto Sans CJK (not in the browser)
├── browser/                 ← ManimGX for the browser, published on npm, with its tests
├── docker/                  ← the Docker image
├── docs/                    ← the docs site: its pages, its settings, what its build loads
├── examples/                ← thirty example films, a Python file each
├── benchmarks/              ← the README's benchmark against Manim CE, ManimGL and Blender:
│                              its scenes, its runner and its recorded results
├── scripts/                 ← what writes and builds: the release's scripts, the docs' generated
│                              pages and pictures, and the engine's DFG table
├── skills/                  ← the agent skill
├── pyproject.toml           ← the package, its workspace (with fonts/), the tools and their settings
├── uv.lock                  ← the exact version of every Python package
├── justfile                 ← the development tasks
├── .pre-commit-config.yaml  ← the checks
├── README.md                ← the front page: GitHub's, PyPI's, and the docs' Welcome
├── AGENTS.md                ← this guide's commands and rules in brief, for coding agents
├── CITATION.cff             ← how to cite ManimGX
├── LICENSE                  ← ManimGX's license, the MIT License
├── LICENSE-THIRD-PARTY      ← what the wheels hold that others hold the copyright in
├── LICENSE-LAVAPIPE         ← the notices of the lavapipe the Linux wheels bundle
├── LICENSES/                ← the text of each license a file of the repository is under
├── REUSE.toml               ← whose each file is, and under which license, where it doesn't say
└── .github/                 ← the workflows, deployment configs, the
                               contributing guide, issue forms and pull request template
```

Project management is everything but the code, in `src/`, `rust/` and `browser/src/`: what
makes the code installable, the same on every machine, and checked the same way by everyone.
The repository's root is the package; what is published apart from it (the font packages, the
browser package, the Docker image) has a folder of its own.

## Why isn't code enough?

Code alone leaves two problems open: how users get it, and how developers work on it.

### Distribution

A user wants `pip install manimgx` and a working `manimgx` command. ManimGX is harder to
ship than pure Python: its engine is compiled, so every platform needs a build of its own,
with the engine inside. A release publishes ManimGX in five forms:

- **Wheels**, one per platform: Linux (x86_64 and arm64), macOS (arm64, and x86_64
  cross-compiled on arm64) and Windows (x86_64). The engine is built against Python's
  stable ABI, so a platform's one wheel serves every supported Python, and x264 is built
  into it, so a wheel needs nothing from the system. A Linux wheel bundles Mesa's lavapipe
  too, to draw on the CPU where there is no GPU driver
  ([`scripts/release/build_lavapipe.sh`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/build_lavapipe.sh)
  builds it in the manylinux image first: about 24 MB of the wheel).
  [cibuildwheel](https://cibuildwheel.pypa.io) builds each wheel and installs it on every
  supported Python, where it must render a scene
  ([`scripts/release/smoke_test.py`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/smoke_test.py))
  before it is kept: on Linux, with no driver in the image, so with the bundled lavapipe. Its
  settings are `[tool.cibuildwheel]` in `pyproject.toml`.
- **A source distribution**, which builds the engine on the machine that installs it: that
  needs Rust and a C compiler, nothing else (the engine's build fetches the sources it takes
  from others: see [Others' sources](engine.md#others-sources)).
- **Executables**, one per platform: one file that holds a Python with ManimGX installed,
  for a machine without Python (see [`scripts/`](#scripts)).
- **A Docker image**, `ghcr.io/academa-labs/manimgx` (see [`docker/`](#docker)).
- **The package for the browser**, `manimgx` on npm: the player in one file, which runs
  scenes with the wheel for the browser (see [`browser/`](#browser)).

The fonts text is set in are packages of their own, `manimgx-fonts` and `manimgx-fonts-cjk`:
a wheel for every platform, released when the fonts change, not with every ManimGX (see
[`fonts/`](#fonts)).

PyPI gets the wheels, the source distribution and the font packages; the GitHub release gets
the wheels, the source distribution, the wheels' complete source (`manimgx-X.Y.Z-source.tar.xz`:
see [Licenses](#licenses)) and the executables; npm gets the package for the browser; ghcr.io
gets the image. [Releases](#releases) says how a release is made.

### The development environment

Developer A installs the dependencies today and the tests pass. Developer B installs them
a month later, gets a newer Typst or numpy, and the tests fail. For ManimGX the risk is
sharper than usual: the integration corpus compares the current and frozen packages' frames
pixel for pixel, so any change in how a glyph is laid out or a color is rounded shows.

So everyone needs the same Python, the same version of every package and crate, and the
same tools with the same settings, in one command:

```sh
just sync
```

A bug from six months ago? Check out that commit and run `just sync`: its Python packages
and Rust crates come back as they were. The system's libraries and the Rust toolchain are
not pinned.

The rest of this page describes the files that make this work.

## Files in the root

### [`pyproject.toml`](https://github.com/academa-labs/manimgx/blob/main/pyproject.toml)

The package (see [The package](#the-package)), the workspace it is developed in, and what
developing it takes. [uv](https://docs.astral.sh/uv/concepts/projects/workspaces/) manages
the workspace as one:

- `[tool.uv.workspace]`: its other members, the font packages in `fonts/`, each with a
  `pyproject.toml` of its own (see [`fonts/`](#fonts)). One lockfile holds them all, and one
  environment, `.venv`, has them all installed.
- `[tool.uv.sources]`: the members as they are here. ManimGX requires its font packages
  at exact versions; in the workspace those are the ones in `fonts/`, installed editable,
  like ManimGX, whose engine uv builds.
- `[dependency-groups]`: what developing needs. `dev` holds the tools (ruff, ty, pytest and
  its plugins, prek), FastAPI for the review panel, and PyAV, with which the
  corpus writes and reads its videos. `docs` holds Zensical and mkdocstrings. `ce` holds
  Manim Community Edition, which renders the corpus's Manim references (see
  [Setup](index.md#manim-community-edition)). Each is installed with ManimGX.
- `[tool.uv]`: `dev` and `docs` are installed by default.
- The tools' settings: `[tool.pytest]`, `[tool.coverage.run]` (see
  [Testing](testing.md#coverage)), `[tool.mutmut]`, `[tool.fastapi]`, and those of the tools
  that keep the code's form and check its types, `[tool.ruff]` and `[tool.ty]` (below).

### [`uv.lock`](https://github.com/academa-labs/manimgx/blob/main/uv.lock)

The exact version of every Python package the project uses, down to the dependencies of
dependencies. `just sync` installs exactly these, not the latest ones.

Never edit it by hand: after changing a dependency in a `pyproject.toml`, run `just lock`,
and commit both files. `just upgrade` moves every package to the newest version the
`pyproject.toml` files allow. The recipes run their tools with `uv run --frozen`, which uses
the lockfile as it is, without checking it against the `pyproject.toml` files.

### [`justfile`](https://github.com/academa-labs/manimgx/blob/main/justfile)

[just](https://just.systems) runs commands defined once in a file. Without it, everyone
types the same long commands with different options. With it:

```sh
just test        # pytest, in parallel, in the locked environment
just test-rust   # the Rust core and native libraries, without embedding Python
just check       # every check of .pre-commit-config.yaml
just serve-docs  # render the docs' examples, write the reference, serve the site
```

The recipes are grouped (development, testing, docs, release), and a comment above a recipe
is its description in `just --list`. The GitHub workflows run these same recipes, so a
task does the same on a developer's machine as in CI. [Setup](index.md#commands) lists
every recipe.

### ruff

[ruff](https://docs.astral.sh/ruff/) keeps the code's form the same everywhere:

- it formats, in its stable style and 88 columns: the Python, the examples in the
  docstrings, and the Python in the Markdown. It does not split a long string.
- it lints: it finds likely bugs, unsorted imports and outdated idioms. `[tool.ruff]` in
  `pyproject.toml` selects its rules and gives the reason for each one it ignores; the
  package's re-exports in `__init__.py` may import with `*` and import names they do not
  use.

`just format` runs ruff's automatic fixes, then its formatter. `just check` runs both too
(below). Docstrings have a form of their own, the Google style, since the API reference is
generated from them: see [Documentation](documentation.md#docstrings).

### ty

[ty](https://docs.astral.sh/ty/) checks types. ManimGX is typed throughout, and ty reports
nothing on it: `just check` must pass with no errors, and a change keeps it that way. Two
rules follow:

- **No `Any` in a public signature.** Keyword options are a `TypedDict`, taken as
  `**kwargs: Unpack[…]`, never as `**kwargs: Any`, so a misspelled keyword fails the check,
  in ManimGX and in a user's scene alike. [`Style`][manimgx.drawing.paint.Style], in
  [`drawing/paint.py`](https://github.com/academa-labs/manimgx/blob/main/src/manimgx/drawing/paint.py),
  is the style keywords; [`Polygon`][manimgx.Polygon] takes `**kwargs: Unpack[Style]`.
- **Only live suppressions, in ty's form.** ty honors `# ty: ignore[rule]` and a bare
  `# type: ignore`, not `# type: ignore[code]`. A suppression that suppresses nothing is an
  error (`[tool.ty]` makes it one), so one that a fix has made useless fails the check.
  ruff's formatter does not count a trailing suppression comment in a line's width, but it
  splits a line too long without one and moves the comment to the last line, so run
  `just check` after `just format`.

`[tool.ty]` is the one list of what ty checks: the packages, the docs' scripts, the corpus's
tools and review server, and the tests it names. The hook that runs ty passes it no files,
so `just check` checks that list. It also reads `svgelements` as untyped (ty cannot read its
source's encoding).

A user's scene is held to more: every corpus case type-checks with every rule, and no
value ManimGX gives it may be `Any` (see [Testing](testing.md#the-three-checks)).

### [`.pre-commit-config.yaml`](https://github.com/academa-labs/manimgx/blob/main/.pre-commit-config.yaml) and `just check`

Every check the repository has, as hooks:

- file checks: no merge conflict markers, valid TOML and YAML, a final newline, no trailing
  whitespace;
- [check-jsonschema](https://check-jsonschema.readthedocs.io), which checks `CITATION.cff`
  against the [Citation File Format](https://citation-file-format.github.io)'s schema;
- [zizmor](https://docs.zizmor.sh), which finds security problems in the GitHub workflows;
- ruff and ty, run from the environment (`uv run --frozen`), so they are the versions
  `uv.lock` pins;
- TypeScript 7 and Prettier for the browser package, run with the versions its `bun.lock` pins;
- [reuse](https://reuse.software), from the environment too, which checks that the license
  and the copyright of every file are known (see [Licenses](#licenses)).

[prek](https://prek.j178.dev), a fast implementation of pre-commit, runs them: `just check`
is `prek run --all-files --show-diff-on-failure`. A hook that changes a file (ruff fixing
or formatting it, a final newline added) fails the check, shows the change,
and leaves the file changed; the next `just check` passes if nothing else is wrong.

The repository installs no git hooks: the checks run when you run them, and on every push
to `main` and every pull request, in the Test workflow (see
[GitHub workflows](github-workflows.md#1-testyaml-the-checks-and-the-tests)).

### Licenses

ManimGX is under the MIT License, in
[`LICENSE`](https://github.com/academa-labs/manimgx/blob/main/LICENSE): GitHub, PyPI and
npm show it. Some files are others': modules ported from Manim CE, the engine's 3D lighting
adapted from [Filament](https://github.com/google/filament)'s, the Noto fonts, the corpus's
scenes from CE's documentation, the command spec made from mitex's Typst package, a few
documents and images. The repository says whose each file is, and under which license, as
[REUSE](https://reuse.software) specifies:

- a file with code from elsewhere says it in its first lines: an `SPDX-FileCopyrightText`
  line for each copyright holder (ManimGX's, `2026 Academa, Inc.`, among them) and an
  `SPDX-License-Identifier` line, as the modules ported from Manim CE do;
- [`REUSE.toml`](https://github.com/academa-labs/manimgx/blob/main/REUSE.toml) says it for the
  rest: ManimGX's own files, in one annotation; the fonts, the corpus, data and images;
- [`LICENSES/`](https://github.com/academa-labs/manimgx/tree/main/LICENSES) holds each
  license's text, once, named by its SPDX identifier.

The license texts the engine's crates keep for the sources they fetch (`COPYING`, `LICENSE`;
see [Others' sources](engine.md#others-sources)) are their projects', as published: REUSE
leaves files of those names be. `reuse lint`, a hook of `just check`, fails while a file's
license or copyright is unknown, or a license has no text. A new file of ManimGX's needs
nothing; code brought from elsewhere needs its lines; data or an image needs an annotation.
What a wheel holds that others hold the copyright in comes with its notices (see
[The package](#the-package)).

A wheel holds FFmpeg's audio decoders, under the LGPL-2.1-or-later, and every wheel but the
browser's holds x264, under the GPL-2.0-or-later, with crates under the Apache-2.0 alone
(Typst, mitex), which only the GPL's third version takes in: such a wheel, as a whole, is under
the GPL-3.0-or-later. Its section 6 (and the LGPL's, which refers to it) asks
that whoever gets the wheels can get their complete source, from where the wheels are or from
a place the wheels point to, for as long as the wheels are offered: all of it, the crates too,
not links to where others publish them, which can go. Each GitHub release carries it,
`manimgx-X.Y.Z-source.tar.xz`, with the sources and build recipes (see
[Others' sources](engine.md#others-sources)); the wheels' notice, the README (PyPI's page) and
the release's notes point to it, and the README and the notes say what FFmpeg asks every page
that offers it to say. A release is never deleted while PyPI offers its wheels.

### [`scripts/`](https://github.com/academa-labs/manimgx/tree/main/scripts)

What writes and builds, a folder for each thing it makes:

- [`release/`](https://github.com/academa-labs/manimgx/tree/main/scripts/release): the release's scripts, which the recipes and
  cibuildwheel run.
  - [`create_executable.py`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/create_executable.py)
    (`just create-executable`) makes this machine's executable from its wheel in `dist/`:
    an exact, SHA-256-verified Python Build Standalone archive with the wheel, the font
    packages and the dependencies `uv.lock` pins installed, packed into one file by
    [PyApp](https://ofek.dev/pyapp). The file's
    first run unpacks the Python it holds; every run then runs `manimgx` there, with no
    network and no Python on the machine, and `manimgx self` manages it (`self pip install`
    adds a package a scene imports). The script writes
    `dist/manimgx-<os>-<arch>.tar.gz` (a `.zip` on Windows), after running what it made once.
  - [`smoke_test.py`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/smoke_test.py)
    renders a scene with an installed ManimGX: the check a wheel or an executable passes
    before it is kept. It decodes generated PCM and the reference Opus fixture, exports
    their soundtrack and reopens the MP4's AAC sound. Pyodide records the same scene and
    checks the take's version, frame count, sound and successful end, and its embedded player.
  - [`build_lavapipe.sh`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/build_lavapipe.sh)
    builds Mesa's lavapipe for a Linux wheel, in the manylinux image (cibuildwheel's
    `before-all`): Mesa, glslang and LLVM from their sources, checked against pinned hashes.
    LLVM carries the register-class correction in `scripts/release/llvm/`. The driver
    exports only what Vulkan's loader calls. The script writes
    `src/manimgx/lavapipe/libvulkan_lvp.so`, which the wheel then takes in. Its checked
    archives go through the engine's source store. After repair, `linux_sources.py` uses
    auditwheel's SBOM and RPM metadata to retain the exact distribution source packages
    for bundled libraries. These are sources and provenance; the system build
    tools are not a frozen, hermetic environment.
  - [`licenses.py`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/licenses.py)
    (`just licenses`) writes the wheels' third-party notice (see
    [The package](#the-package)).
- [`docs/`](https://github.com/academa-labs/manimgx/tree/main/scripts/docs): the docs' generated pages, which `just build-docs` writes
  before the site is built: the Gallery and the command-line reference (see
  [Documentation](documentation.md)).
- [`showcase/`](https://github.com/academa-labs/manimgx/tree/main/scripts/showcase): the README's pictures, made by hand and committed:
  the logo (the banner, the header's, the favicon) and the wall of example films.
- [`engine/`](https://github.com/academa-labs/manimgx/tree/main/scripts/engine): what the engine is compiled with, made by hand:
  [`dfg_table.py`](https://github.com/academa-labs/manimgx/blob/main/scripts/engine/dfg_table.py) writes `rust/engine/src/dfg.bin`, the
  split-sum table a lit surface's specular reflection is read from, run again only if the
  lighting changes.

### [`benchmarks/`](https://github.com/academa-labs/manimgx/tree/main/benchmarks)

The README's benchmark: ManimGX against Manim CE, ManimGL and Blender on five scenes, each
written in every engine's own API (`scenes/`). Its
[README](https://github.com/academa-labs/manimgx/blob/main/benchmarks/README.md) is the
method and the results, the source of the README's numbers. `run.py` times the engines into
`results.json`; `chart.py` draws the README's chart from it, and `quality.py` makes the
README's comparison images. `tests/benchmarks/test_comparison.py` checks that the numbers
both READMEs give are the recorded ones.

### The docs' and the coverage's hosting

[`docs/zensical.toml`](https://github.com/academa-labs/manimgx/blob/main/docs/zensical.toml) holds the
docs site's settings (see [Documentation](documentation.md)); the site is built into
`docs/site/`. Hosting is configured alongside
the workflows, in [`.github/deploy/`](https://github.com/academa-labs/manimgx/tree/main/.github/deploy):
`docs.jsonc` serves the docs site, and `coverage.jsonc` serves the tests' coverage report
(see [Testing](testing.md#coverage)).

### [`AGENTS.md`](https://github.com/academa-labs/manimgx/blob/main/AGENTS.md) and the contributing guide

`AGENTS.md` is this guide's commands, rules and layout in brief, for coding agents; the
assistant of the [AI workflow](github-workflows.md#7-aiyaml-claude-on-issues-and-pull-requests)
is told to follow it. The
[contributing guide](https://github.com/academa-labs/manimgx/blob/main/.github/CONTRIBUTING.md)
says how a change is proposed (an issue first, then a pull request) and links here for how
the project works. When a command or a rule changes, `AGENTS.md` changes with this guide.

### [`.gitignore`](https://github.com/academa-labs/manimgx/blob/main/.gitignore)

What is made, not written, stays out of git: the environment, the compiled engine, `rust/target/`, `dist/`, the built site, the docs' rendered films and generated reference, the coverage data and report, and render output (`media/`, `*.mp4`). The corpus's reference videos are `.mkv` files and are ignored by Git; their SHA-256 sidecars are committed.

## The package

The repository's root is the package, defined in
[`pyproject.toml`](https://github.com/academa-labs/manimgx/blob/main/pyproject.toml), in the
[standard format](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/):

- `[project]`: the name, version, supported Pythons (3.13 and 3.14), license, and the
  packages ManimGX needs at run time.
  [Understanding ManimGX](understanding-manimgx.md#dependencies) says what each is for.
  `license` names every license of what the distributions hold, as one SPDX expression:
  ManimGX's own MIT, those of the crates compiled into the engine (x264's GPL-2.0-or-later
  among them), of Typst's fonts and data, and of the lavapipe a Linux wheel bundles.
  `license-files` puts `LICENSE` and the three notices beside it into the wheel's metadata.
  Its README is the repository's, `README.md`.
- `[project.scripts]`: makes `manimgx` a command, running `manimgx.cli:main`.
- `[build-system]` and `[tool.maturin]`: [maturin](https://www.maturin.rs) builds the
  package. It compiles the crate in `rust/engine/` into the module `manimgx._engine` and
  puts it beside the Python sources from `src/`.
- `[tool.uv]`: `cache-keys` says when the engine is rebuilt (below).
- `[tool.cibuildwheel]`: how the wheels are built and tested ([Distribution](#distribution)).
  A wheel is tested with the fonts it is released with, this repository's, which PyPI may
  not have yet: they are installed before it.

Beside it, at the root, the notices `license-files` names besides `LICENSE`:

- [`LICENSE-THIRD-PARTY`](https://github.com/academa-labs/manimgx/blob/main/LICENSE-THIRD-PARTY):
  what the wheels hold that others hold the copyright in, with the licenses and notices it
  comes with: the package's and the engine's files that name others (the modules ported from
  Manim CE, the engine's 3D lighting), with their copyright lines and their licenses' texts
  from `LICENSES/`; and every crate compiled into the engine, in each build a wheel holds
  (each platform's extension, Pyodide's, the player for a page), with the license and notice
  files it ships, the workspace's crates those of what they fetch (x264's, FFmpeg's,
  libopus's, mitex's). `just licenses` writes it again after `Cargo.lock` changes (so does
  `just upgrade`), or after code carrying third-party notices moves between files. A test
  fails while the notice is stale, or while a license in it is not among ManimGX's.
- [`LICENSE-LAVAPIPE`](https://github.com/academa-labs/manimgx/blob/main/LICENSE-LAVAPIPE):
  the notices of the lavapipe the Linux wheels hold: Mesa's, with the copyright lines of the
  sources it is built from, and those of what it holds, of the libraries it links to and of
  LLVM. It is written by hand, from Mesa's sources: a test fails when
  `scripts/release/build_lavapipe.sh` builds another Mesa than the one it describes.
- [`LICENSE-DXC`](https://github.com/academa-labs/manimgx/blob/main/LICENSE-DXC):
  the notices of the pinned DirectX Shader Compiler the Windows wheel carries, including
  its source dependencies. The source archive retains the matching source closure.

In `src/manimgx/`, besides the Python:

- `py.typed`: marks the package as typed, so type checkers read its annotations.
- [`_engine.pyi`](https://github.com/academa-labs/manimgx/blob/main/src/manimgx/_engine.pyi):
  the engine's interface, typed (see [The engine](engine.md#the-boundary-with-python)).
- [`cli/present.html`](https://github.com/academa-labs/manimgx/blob/main/src/manimgx/cli/present.html):
  the page that presents a film's slides in a browser (`manimgx present`).

#### Rebuilding the engine

uv installs manimgx in editable mode: a change to a Python file applies the next time
Python runs. The engine is different: it is a compiled file (`_engine.abi3.so` in
`src/manimgx/` on macOS and Linux, ignored by git) that exists only once maturin has built
it.

uv rebuilds a package when one of its *cache keys* changes. `cache-keys` lists the engine's
sources: the crates' Rust files and shaders (`*.wgsl`, compiled into it), their manifests
and build scripts, the C shims, the lockfile, and mitex's `lib.typ` and command spec. What the
crates fetch changes only with their build scripts, which pin it.
`uv run` brings the environment up to date before it runs anything, so after an edit to
`rust/engine/src/vector.wgsl`, the next `just test` rebuilds the engine, then tests it.

The build is maturin's release build, optimized as `[profile.release]` in `rust/Cargo.toml`
says (full optimization, thin link-time optimization): slower to compile, fast to run. A file the engine is built from that no pattern in `cache-keys` matches needs an
entry of its own, or its changes are not seen. `uv sync --reinstall-package manimgx`
rebuilds the engine whatever changed.

## [`fonts/`](https://github.com/academa-labs/manimgx/tree/main/fonts)

The font packages, the workspace's other members:
[`manimgx-fonts/`](https://github.com/academa-labs/manimgx/tree/main/fonts/manimgx-fonts) and
[`manimgx-fonts-cjk/`](https://github.com/academa-labs/manimgx/tree/main/fonts/manimgx-fonts-cjk),
each with its manifest, its README and its license; what each holds is what its users get.

The Noto fonts text is set in, besides Typst's own, so that text is the same on every
machine: Noto Sans and the faces for the scripts Latin faces lack in `manimgx-fonts`, Noto
Sans CJK in `manimgx-fonts-cjk`, each under the SIL Open Font License (`LICENSE`). They are
data, 40 MB of it, and change rarely: packages of their own, built by uv's backend into one
wheel for every platform, and released when they change, not with every ManimGX, which
requires them at exact versions. A version is the date the fonts were taken from Noto.
`manimgx-fonts-cjk` is not required in the browser, where 33 MB is too much for a page to
download. ManimGX finds the fonts in them (`importlib.resources`), in whichever are
installed.

## [`rust/`](https://github.com/academa-labs/manimgx/tree/main/rust)

The engine's crates, as one workspace: [`rust/Cargo.toml`](https://github.com/academa-labs/manimgx/blob/main/rust/Cargo.toml)
lists them (every folder here), the build profiles they are compiled with, and the patch that
gives mitex ManimGX's own spec crate; `Cargo.lock` is to Rust what `uv.lock` is to Python, every
crate's exact version, committed (`just upgrade` moves it too). Cargo runs here, and builds into
`rust/target/`. [The engine](engine.md) says what the crates do:

- `engine/`: the engine, `manimgx._engine` — with the player, in a window natively, and in
  Pyodide carrying the player for a page; its manifest holds its dependencies (wgpu, PyO3,
  Typst, mitex, winit, rustybuzz) and the Clippy lints it answers to.
- `x264/`, `nasm/`: x264 and NASM, built from their sources.
- `ffmpeg/`: FFmpeg's audio decoders and libopus, built from their sources, behind one call.
- `dxc/`: the verified DirectX Shader Compiler binary and matching source closure for Windows.
- `mitex-spec-gen/`: mitex's Typst package, which the engine serves to Typst (with its own
  `lib.typ`, which imports only the scope the converted LaTeX calls), and the command spec made
  from it.
- `fetch/`: what the others' build scripts fetch with: a source tree, pinned by the SHA-256 of
  its files (see [The engine](engine.md#others-sources)).

The repository holds none of what others wrote but its license texts, which the crates keep
for the notices (`COPYING`, `LICENSE`), as their authors published them; the checks leave them
alone.

## [`browser/`](https://github.com/academa-labs/manimgx/tree/main/browser)

ManimGX for the browser, published to npm as `manimgx`: the player's element (`src/player.ts`)
and the director's worker (`src/director.ts`). `just build-npm` compiles the worker before
embedding it in one browser module (`dist/manimgx.js`), and TypeScript 7 generates the public
declarations from the implementation. The package installs ManimGX's wheel for the browser
from PyPI, at its own version, in Pyodide, and plays with the player that wheel's engine carries.

The development tools are pinned in `bun.lock`. `just check` checks the TypeScript and its
formatting; `just test-typescript` runs the package's tests, in `browser/tests/`.

## [`docker/`](https://github.com/academa-labs/manimgx/tree/main/docker)

The `Dockerfile` of an image that installs ManimGX from PyPI (the version it is built with,
or the latest) into `python:3.14-slim`, with Vulkan's loader and Mesa's drivers: lavapipe
draws on the CPU, and a GPU given to the container (`--device /dev/dri` for AMD and Intel,
`--gpus all` for NVIDIA) is used instead. Its entry point is the `manimgx` command, run in
`/work`:

```sh
docker run --rm -v "$PWD:/work" ghcr.io/academa-labs/manimgx:0.1 render scene.py
```

`just build-docker-image <version>` builds that `published` target for local use. A release
builds the separate `release` target from its already-tested wheel and font artifacts, with
runtime dependencies authenticated against `uv.lock`. It smoke-tests and retains OCI
archives before any registry publication; publishing copies those same image digests.

## Releases

The version is in `pyproject.toml` (`0.1.1`; the engine's crate carries the same number). ManimGX follows [Semantic Versioning](https://semver.org), and its [changelog](../changelog.md) [Keep a Changelog](https://keepachangelog.com): a change a user would notice adds a line under "Unreleased" (see [Documentation](documentation.md#the-changelog)).

A release takes three steps:

1. A commit on `main` sets the new version in `pyproject.toml`, and moves
   the changelog's "Unreleased" lines into a section of their own, `## X.Y.Z`.
2. `just release`, at that commit, asks for confirmation, tags it `vX.Y.Z`, and pushes the
   tag.
3. The tag starts the [Release workflow](github-workflows.md#4-releaseyaml-a-release). It
   stops unless the tag is ManimGX's version and the changelog has a section for it; then
   it runs the tests, builds everything, and publishes: the GitHub release, whose notes are
   the changelog's section (`just release-notes X.Y.Z` prints them), PyPI, npm and ghcr.io.
   PyPI gets the font packages' versions it doesn't have yet: a change to the fonts sets a
   new version in their `pyproject.toml` and in ManimGX's requirement, and is released with
   the next ManimGX.

A version that ends in `aN`, `bN` or `rcN` (`0.2.0rc1`, say) is a pre-release.

## Learn more

- [uv's documentation](https://docs.astral.sh/uv/): projects, lockfiles, dependency groups.
- [maturin's user guide](https://www.maturin.rs): mixed Rust and Python projects.
- [cibuildwheel's documentation](https://cibuildwheel.pypa.io): building and testing wheels.
- [just's manual](https://just.systems/man/en/).
