# AGENTS.md

ManimGX is an animation engine with Manim Community Edition's API. The Python package
(`src/manimgx`) is typed throughout; the engine under it (`rust/engine`,
built by maturin into `manimgx._engine`) typesets text with Typst, draws on the GPU with wgpu,
and encodes video with x264. Setup and conventions are in the Developer Guide
(`docs/content/developer-guide/`, published at https://manimgx.academa.ai/developer-guide/);
this is the short version.

## Commands

- `just sync`: the environment, `.venv`, with the engine built into it, and the browser package's
  locked development dependencies.
- `just format`: ruff's fixes and formatter (the Python, and the Python in the Markdown), and
  Prettier for the browser package.
- `just check`: every pre-commit check (ruff, ty, TypeScript, Prettier, reuse and the files'
  hygiene). It must pass.
- `just test [PYTEST ARGS]`: the suite, in parallel; `just test-thorough`: the unit tests'
  properties on 2,000 examples each; `just mutate`: mutation testing (`[tool.mutmut]`).
- `just test-rust`: the Rust core and native libraries; the Python suite tests the bindings.
- `just test-typescript`: the browser package's tests, including its compiled worker and
  public declarations.
- `just corpus …`: render, compare and review the integration corpus (`just corpus --help`).
- `just bench [REF]`: the timed benchmarks, this checkout against REF's ManimGX (main unless
  named), side by side.
- `just build-docs`, `just serve-docs`: the docs site.

Run Python through `uv run --frozen`. uv rebuilds the engine when its Rust sources, shaders or
manifests change, so there is no separate build step.

## Rules

- No `Any` in public signatures: keyword arguments are a `TypedDict` taken with `Unpack`.
- ty honors `# ty: ignore[rule]` and a bare `# type: ignore`, not `# type: ignore[code]`, and
  an unused suppression is an error. ruff's formatter splits a line too long without its
  trailing suppression and moves the suppression to the last line, so run `just check` after
  `just format`.
- Manim CE is the source of the API, not of the behavior: don't copy CE's behavior, or its
  bugs, for compatibility. The corpus is the specification.
- Measure before and after any change to the engine or the render path (`just bench main`);
  don't lose speed without a reason.
- A test comes with every fix and feature. A corpus reference changes only when a change means
  it to, and after someone has looked at the new frames.
- Docstrings are Google style: the API reference is generated from them.
- `docs/content/changelog.md` says only "First release of ManimGX." until 0.1.0, the first
  release, is out. After it, a user-visible change gets a line under "Unreleased".
- Code from elsewhere says whose it is in its first lines (`SPDX-FileCopyrightText`, one per
  holder, and `SPDX-License-Identifier`); data or an image, in `REUSE.toml`. `LICENSES/` holds
  the licenses' texts.
- Don't install git hooks; run the checks by hand (`just check`).

## Layout

The repository is the package, ManimGX: its `pyproject.toml` (with the uv workspace, the
dependency groups and every tool's settings), its sources and its tests are at the root. What
is published apart from it has a folder of its own, with its own tests.

- `src/manimgx/`: the package. `__init__.py` exports the authoring API. `mobject.py` is the
  mutable object kernel; `mobjects/` is its catalog of constructors. `drawing/` owns geometry,
  paint and typesetting data. `scene.py` owns cameras and scene execution; `animation/` owns
  time and changes; `rendering/` turns evaluated state into native records, films and window
  playback. `audio/` owns sound, speech and providers. `cli/` contains scene loading, export,
  preview, diagnostics and storyboards, with the presentation template in `cli/present.html`.
  `config.py`, `constants.py`, `typing.py` and `caches.py` hold the shared configuration,
  vocabulary, types and reuse policy. `LICENSE-THIRD-PARTY` (`just licenses` writes it) and
  `LICENSE-LAVAPIPE`, at the root, hold the notices for what others own in the wheels.
- `rust/`: the engine's crates, a Cargo workspace (`rust/Cargo.toml`; cargo runs there).
  `engine/` is the engine: the Python extension (with the player in a window, natively), and
  the player for a page, the engine built for the browser, which Pyodide's extension carries.
  The other crates build what the engine takes from other projects, whose sources their build
  scripts fetch, each pinned by the hash of its files (`fetch/`), so the repository holds none
  of them: `x264/` the H.264 encoder, with NASM (`nasm/`) for its x86-64 assembly; `ffmpeg/`
  FFmpeg's audio decoders, with libopus; `mitex-spec-gen/` mitex's Typst package, which the
  engine serves to Typst, and the command spec of the LaTeX-to-Typst converter made from it.
- `fonts/`: `manimgx-fonts/` and `manimgx-fonts-cjk/`, the Noto fonts text is set in, published
  apart and required at exact versions (the CJK one not in the browser); the uv workspace's
  other members.
- `browser/`: ManimGX for the browser, published on npm: strict TypeScript in
  `src/`, its tests in `tests/`, and its pinned tools in `bun.lock`. Bun bundles the player
  and compiled worker into one JavaScript file; TypeScript 7 generates the public declarations.
- `docker/`: the Docker image, ManimGX from PyPI.
- `tests/unit/`: properties of each module, mirroring `src/manimgx/`, drawn
  with Hypothesis (the shared kit: `tests/strategies.py`, `tests/oracles.py`, `tests/scenes.py`).
- `tests/integration/`: stories per subject (`test_*.py`) and the corpus, `cases/` (per case: `scene.py`, hashes of the local `manimgx.mkv` and `ce.mkv` references, `case.json`, and once reviewed `review.json`), with its tools in `corpus/` and the review panel in `review/`.
  `tests/docs/`: `llms.txt`'s hand-written primer for agents, checked against the API, and
  the narrated examples, which say what `docs/voice/` keeps (the site is built with no key).
- `tests/benchmarks/`: laws of what work costs (with the suite) and timed benchmarks against
  another commit (`just bench`): `manimgx render` of three scenes (`scenes/`) and of example
  films, from launch to exit.
- `docs/`: the Zensical site and what its build loads. Pages are in `docs/content/`, the
  first, Welcome, being the README, included; `docs/examples.py` renders the examples in
  them and in the docstrings, and shows each above its code; `docs/links.py` makes the
  README's URLs of the site its paths; `docs/previews.py` marks a reference to the API to
  preview its target on hover, as a link does; `docs/deprecated.py` leaves what is
  `@deprecated` out of the API reference; `docs/films.py` shows a card's film by its scene's
  name; `docs/mkdocstrings.py` lets mkdocstrings find `docs/templates/`, which shows each
  entry of the reference. The reference is written by hand (`docs/content/reference/`), a
  story whose pages render the API with mkdocstrings; `tests/docs/test_reference.py` keeps it
  whole. `docs/zensical.toml` sets the site; its llmstxt plugin
  writes each page's Markdown beside it, and `llms.txt`, whose primer for agents it holds.
- `examples/`: example films.
- `benchmarks/`: the README's benchmark, ManimGX against Manim CE, ManimGL and Blender on
  five scenes (`scenes/`). Its `README.md` is the method and the results, the source of the
  README's numbers; `run.py` times the engines into `results.json`, `chart.py` draws the
  README's chart from it into `docs/content/images/`, and `quality.py` renders the README's
  comparison images (`docs/content/images/benchmark-quality/`).
- `scripts/`: what writes and builds, a folder for each thing it makes. `release/`: lavapipe
  for the Linux wheels, the wheels' third-party notice, the executables, and the smoke test a
  wheel or an executable passes. `docs/`: the pages the docs build generates (not committed),
  the command line's reference (`reference.py`) and the Gallery from `examples/`
  (`gallery.py`). `showcase/`: the README's pictures (committed), the logo (`logo.py`: the
  banner, the header's, the favicon) and the wall of films (`wall.py`). `engine/`: the DFG
  table the engine is compiled with (`dfg_table.py`).
- `skills/manimgx/`: the agent skill, which `npx skills add academa-labs/manimgx` installs;
  `tests/docs/test_skill.py` checks its front matter.
