# Testing

A test is code that checks that other code does what it should. Written once, it runs
again after every change, and says whether the change broke something.

ManimGX's Python and integration tests are in
[`tests/`](https://github.com/academa-labs/manimgx/tree/main/tests).
Most of them render scenes, so the suite needs what rendering needs: a GPU the engine can
draw with (see [Setup](index.md#a-gpu)). Rendering the corpus's Manim references again
needs Manim Community Edition too (see
[Setup](index.md#manim-community-edition)).

The browser package's tests live beside it, in
[`browser/tests/`](https://github.com/academa-labs/manimgx/tree/main/browser/tests).
Run them with `just test-typescript`: it builds the package, tests the compiled player and
embedded worker with browser and Pyodide doubles, and type-checks a consumer of the generated
public declarations. These tests need Bun; they do not need a GPU or download Pyodide.

## [pytest](https://docs.pytest.org): the test runner

pytest finds the files named `test_*.py` under `tests/` and runs the functions in them
named `test_*`. [pytest-xdist](https://pytest-xdist.readthedocs.io) runs them in parallel,
a worker per CPU core. `just test` runs them, and passes its arguments on to pytest:

```sh
just test                                      # the whole suite
just test tests/integration/test_time.py       # one module
just test -k add_subpath_example               # the tests whose name matches: one case's
just test tests/integration/test_time.py -x    # stop at the first failure
```

The whole suite renders every case of the integration corpus, so it takes a while; while
you work, run the part your change touches. `pyproject.toml` puts the repository's root on
the path, so the tests import their own tools as `tests.integration.corpus`.

The Test workflow runs the suite on every push to `main` and every pull request, on Linux,
macOS and Windows, with Python 3.13 and 3.14 (see
[GitHub workflows](github-workflows.md#1-testyaml-the-checks-and-the-tests)).
The nine benchmark films run on Linux and macOS. Windows still runs the functional
corpus, native rendering tests, packaging checks and laws of work; its software GPU's
cost on these long films is outside the performance gate.

## What the tests are

```text
tests/
├── unit/                 ← properties of each module: unit/<path>/test_<module>.py
├── conftest.py           ← each test's fresh world, its `config` marks, Hypothesis's profiles
├── strategies.py         ← what Hypothesis draws, and a registry of every mobject class
├── oracles.py            ← slow, plainly correct computations to compare with
├── scenes.py             ← scenes made of functions, drawn or probed; random stories
├── test_tests.py         ← the suite's own rules
├── integration/
│   ├── test_*.py         ← stories: what a comparison with Manim cannot see
│   ├── test_corpus.py    ← the corpus's three checks, for every case
│   ├── test_corpus_tools.py ← the corpus's tools keep their rules
│   ├── cases/            ← the corpus: a folder per case
│   ├── corpus/           ← the corpus's tools: render, compare, review
│   ├── review/           ← the review panel: a FastAPI server and its web page
│   └── settings.json     ← the comparison's metric and tolerance
├── docs/
│   ├── test_llms.py      ← llms.txt's primer, checked against the API; every page's Markdown
│   ├── test_skill.py     ← the agent skill, checked against its specification
│   ├── test_reference.py ← the API reference shows every name the package documents, once
│   ├── test_hidden.py    ← no example in the docs uses a name manimgx hides
│   ├── test_deprecated.py ← what is deprecated is left out of the reference
│   └── test_examples.py  ← the narrated examples say what docs/voice/ keeps
└── benchmarks/
    ├── test_laws.py      ← laws of cost: work grows as what is made does
    ├── test_speed.py     ← timed: this checkout against another commit (just bench)
    ├── scenes/           ← three scenes, which test_speed.py times
    ├── harness.py        ← the trees compared, a render measured, and their rounds
    └── work.py           ← work, counted
```

[`tests/docs/test_llms.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_llms.py)
checks the primer of the docs' `llms.txt`, written by hand for AI agents (see
[Documentation](documentation.md#markdown-for-agents)): its scene runs, and every name it
teaches exists. It also checks that every page is in a section of `llms.txt`, so that every
page has its Markdown.
[`tests/docs/test_skill.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_skill.py)
checks the agent skill's front matter (see
[Documentation](documentation.md#the-agent-skill)).
[`tests/docs/test_examples.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_examples.py)
runs the narrated examples with no voice's key, as the site is built (see
[Documentation](documentation.md#examples-films-rendered-from-the-code)).
[`tests/docs/test_reference.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_reference.py)
keeps the API reference, written by hand, whole: every name the package documents is on a
page, once, and no name it hides is (see [Documentation](documentation.md#the-api-reference)).
[`tests/docs/test_hidden.py`](https://github.com/academa-labs/manimgx/blob/main/tests/docs/test_hidden.py)
type-checks every example the docs show, and fails on a name ManimGX hides (`@deprecated`).
The unit tests are in `tests/unit/`, the benchmarks in `tests/benchmarks/` (see
[Benchmarks](#benchmarks)), and the rest of the suite is in `tests/integration/`.

### Unit tests

[`tests/unit/`](https://github.com/academa-labs/manimgx/tree/main/tests/unit) mirrors the
package: `tests/unit/<path>/test_<module>.py` tests
`src/manimgx/<path>/<module>.py`, and opens with a docstring listing the
properties it checks. [`tests/test_tests.py`](https://github.com/academa-labs/manimgx/blob/main/tests/test_tests.py)
holds the suite to both, and its registries to every public mobject and animation class.

The unit tests check properties of the public API, not examples, and not how the code is
built inside: no test reads private storage, counts calls or orders hooks to pin how a result
is reached. With [Hypothesis](https://hypothesis.readthedocs.io), a test states what holds for
every input, and Hypothesis draws hundreds of inputs, then shrinks any that fails to the
simplest one that still does. The properties that do the work:

- agreement with a slow and plainly correct computation from
  [`tests/oracles.py`](https://github.com/academa-labs/manimgx/blob/main/tests/oracles.py):
  de Casteljau's construction, numpy's root finder, Gauss–Legendre quadrature, `decimal`
  arithmetic for a number's digits, the tight box of what is drawn;
- laws: `AnimationGroup(x)` plays as `x`, nested successions play as one, `Rotate` is
  `.animate.rotate`, moves played together end as applied in turn;
- laws every public class keeps, over the registries in
  [`tests/strategies.py`](https://github.com/academa-labs/manimgx/blob/main/tests/strategies.py):
  `MOBJECTS` (a copy, a target, a saved state or a construction made again is an independent
  replica of the same object graph, reaching nothing of its original; its inputs and outputs
  are values; its box is what it draws) and `ANIMATIONS` (made, it changes nothing; begun, it
  shows what it showed; it is a function of its progress);
- state machines checked against a plain model, over any history of public calls: a family's
  edits, transforms, updaters and their clocks, a scene's membership, a graph's edits, the
  feeder's books, what a paint remembers;
- remembered work is invisible: anything made with ManimGX's memories warm is what it is made
  cold (a test marked `cold` starts and ends with nothing remembered);
- for time, random stories told on a headless scene
  ([`tests/scenes.py`](https://github.com/academa-labs/manimgx/blob/main/tests/scenes.py)):
  a play computed ahead of time shows what the same play computed frame by frame shows,
  and the world at an instant is the same at every frame rate.

[`tests/conftest.py`](https://github.com/academa-labs/manimgx/blob/main/tests/conftest.py)
starts every test from the same world: the scene clock at 0 and the configuration as it ships,
restored after the test. A test that needs another configuration says so with a mark,
`pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180)` for a module, or
`@pytest.mark.config(frame_rate=30)` on a test, never by setting and restoring it by hand. It
also holds Hypothesis's profiles: `default`; `thorough`, 2,000 examples a property
(`just test-thorough`); and `mutation`. On CI, Hypothesis loads its own `ci` profile.

A fix comes with the property it broke, stated so that it fails without the fix. A bug found
on one input is that input added to the law it broke (an `@example`, or an entry of a
registry), not a test of its own; work that grew too fast is a row of the laws of cost. A law
that a known bug breaks marks exactly the cases it breaks `xfail(strict=True)`, its reason the
bug in a sentence: the day the bug is fixed, the mark has to go.

### Mutation testing

A test that passes proves little unless it would fail were the code wrong.
[mutmut](https://mutmut.readthedocs.io) checks that: it changes the code in small ways (a
`<` for a `<=`, a `+` for a `-`), one mutant at a time, and runs the tests against each. A
mutant that no test fails is a change the tests let through. `just mutate` runs it on the
modules `[tool.mutmut]` in `pyproject.toml` lists, under the `mutation` profile and with
everything ManimGX remembers forgotten between tests (`manimgx.caches.clear`), so that a
cache cannot hide a mutant. It is slow, so it runs by hand, not on CI.

### Stories

Each `test_*.py` module in
[`tests/integration/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration)
but `test_corpus.py` tells stories about one subject: time, motion, what the engine draws
(strokes, fills, images), light, perspective, 3D compositing, the film's hooks, its video,
sound and takes, the window and the preview, the banner. A story renders a scene and probes
it at every instant the scene computes, often at several frame rates. Its module's docstring
lists what it shows. `tests/scenes.py` makes a scene of a function (`scene`, `scene_3d`),
draws one and keeps its frames as arrays (`frames`), or keeps what a probe sees of it at
every instant (`instants`).

Stories check what a comparison with Manim cannot.
[`test_time.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_time.py),
for one, checks that what a frame shows does not depend on the frame rate: at 10, 30 and 60
frames per second, a dot moved by an updater is where its exact trajectory puts it at every
instant.

A fix or a feature comes with a test that shows it: a story in the module it belongs to,
or a new corpus case (see [Working with the corpus](#working-with-the-corpus)).

## The integration corpus

### The problem

ManimGX implements Manim Community Edition's API. Scenes written for Manim must work, and
keep working as the engine changes. A test of one function does not see a wrong frame, and
reference images are too many to check by hand. And "the same as Manim" is not "correct":
Manim has bugs of its own, and ManimGX differs from it on purpose (the exact clock, for
one).

So the corpus renders real scenes in both engines, compares them, lets a person decide
what is right, and holds ManimGX to every stored render so a change cannot pass unnoticed.

### A case

A case is a folder in
[`tests/integration/cases/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/cases):

- `scene.py`: the only source. It is Manim code, and it reaches the engine only through
  `import manimgx`. A file the scene reads (an SVG, a sound) sits beside it.
- `manimgx.mkv` and `ce.mkv`: each engine's lossless frames, generated locally and ignored by Git. Their `.sha256` sidecars record the exact reviewed video files.
- `case.json`: the facts, written by the tools. The hash of the source both renders came
  from, the hash of every frame, and how the two engines' frames compare.
- `review.json`, once a person has reviewed the case: their verdict and note, pinned to the
  renders they were shown.

The cases are the examples of Manim's documentation and docstrings (the first line of
`scene.py` names its source), scenes written to cover ManimGX's API, regressions, and
scenes written in answer to a question (the question is their docstring). The corpus is
the specification: what its working cases show is what ManimGX does.

### Two engines, one source

Both engines run the same bytes. ManimGX runs `scene.py` as it is. Manim runs it with
`manimgx` resolved to `manim`, and the run fails if the real ManimGX is ever imported
([`run_ce.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/run_ce.py)).
Each render runs in a process of its own, with a fixed hash seed.

A frame is identified by the hash of its pixels, and locally stored in lossless video (x264 in RGB, written and read with [PyAV](https://pyav.basswood-io.com), FFmpeg's libraries in a wheel). A video is rewritten only when its pixels change, so rendering an unchanged scene again changes no file. The committed `.sha256` sidecars identify each reviewed video without putting the video in clone history. The corpus renders at 960 × 540, 10 frames per second.

### Comparing at the same scene time

Frames are paired by scene time, never by index. ManimGX's frame _k_ shows the scene at
exactly _k_/fps. Manim rounds each play to whole frames and never shows a scene's last
animation landing; none of that may count against ManimGX. So each ManimGX frame is
compared with the frame Manim has on screen at the same scene time.

Each pair is measured in four metrics, from 0 to 255: `local_max`, `mae`, `rmse` and `max`.
[`settings.json`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/settings.json)
picks the one that decides, and its tolerance: `local_max` up to 30. `local_max` is the
largest mean, over any 7 × 7 window, of each pixel's largest channel difference: a lone
wrong pixel fades to 1/49 of itself, while a wrong stroke or shape stands out.

See [`compare.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/compare.py).

### Verdicts

A case is in one of these states:

| State | Meaning |
| --- | --- |
| `working` | At every ManimGX frame, Manim's frame is within tolerance, and the scenes last as long. |
| `not_matching` | Otherwise, or Manim could not render the scene. |
| `not_working` | ManimGX could not render the scene. |
| `stale`, `unrendered` | The case has no current renders to judge. |

The comparison gives a verdict; a person's verdict on exactly these renders overrides it.
Manim is a reference to look at, not a definition of correct, so "Manim does it this way"
is a reason to look closely, not a reason to change ManimGX. A case is trusted when it is
working.

See [`case.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/case.py).

### The three checks

[`test_corpus.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_corpus.py)
checks every case three ways:

1. `test_same_source`: both references were rendered from this exact `scene.py`, which
   imports ManimGX, never Manim. So the two engines ran the same program.
2. `test_types`: the scene type-checks as written: ty with every rule, no way around the
   checker (suppression comments, `Any`, `cast`, …), and no value that ManimGX leaves
   `Any` or `Unknown`
   ([`typecheck.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/typecheck.py)).
3. `test_regression`: the latest stable ManimGX release and today's package render the scene in separate fresh processes on the same host and adapter, using the same installed dependencies and fonts. Every RGB pixel, exact duration, timeline and frame count must agree, and the exported MP4 must contain every frame. This covers every case, including those that differ from Manim or await review. Before the first stable release, every scene is still rendered and its exported frame count is checked.

CI resolves the latest stable GitHub release before testing and records its version and wheel SHA-256 identities in a manifest shared by the test workers. Downloads are verified before use. A published release without a compatible wheel, an invalid checksum or a failed download is an error; only the absence of a stable release enables the first-release bootstrap. Locally, the test fixture resolves the latest release, or reads the manifest named by `MANIMGX_CORPUS_RELEASE`.

Failures keep the release identity, reference movie, process logs and first differing frame pairs in `tests/integration/_diffs/<case>/`. Successful comparisons remove their transient films. No image tolerance is used for regression acceptance. A fresh clone needs the released package download, not archived corpus movies, to run these tests.

### Working with the corpus

`test_corpus.py` only checks; `just corpus` renders and reviews. A reference changes only
when a change means it to, and after someone has looked at the new frames.

The review panel and `just corpus diff CASE` use local movies identified by the committed sidecars. Verify restored movies against those sidecars. To create new review movies, use `just corpus render CASE`; changed pixels update the local facts and require a new review before committing them.

- **A new case** is a folder in `cases/` holding its `scene.py`. Render it with `just corpus render CASE`, which renders it in both engines and compares them; look at it (`just review`); and record your verdict with `just corpus review CASE working` (or `not_matching`, or `not_working`; `--note` says why). Commit the scene, facts, review and video hash sidecars; Git ignores the videos.
- **A change that is meant to change how cases look** renders their references again with
  `just corpus render CASE…`. A case's review is pinned to the renders it was given for,
  so it no longer speaks for the new ones: look at the new frames before you commit them,
  and renew the verdict (in the review panel, or with `just corpus review`).
- `just corpus status` says where every case stands, and `just corpus --help` lists the
  rest.

### The corpus's tools

`just corpus` runs
[`tests/integration/corpus`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/corpus):

| Command | What it does |
| --- | --- |
| `render [CASE…] [--all \| --stale] [--engine E] [-j N]` | Render references, then compare them |
| `compare [CASE…] [--all] [-j N]` | Compare the existing references again |
| `status [--list STATE…]` | Where every case stands |
| `review CASE VERDICT [--note TEXT]` | Record a verdict (`auto`: the comparison's) |
| `settings [--metric M] [--tolerance T]` | The comparison's metric and tolerance |
| `diff CASE [--frames N]` | Write the most different pairs of Manim's and ManimGX's frames as images |
| `types` | The type report for every scene |
| `leaks` | Scenes that render differently after others, in one process |

`render` rewrites a local video only when its pixels change, updating that video's SHA-256 sidecar, and a `case.json` only when its facts do. Rendering Manim's references (the `ce` engine, and both engines when a scene changed) needs Manim Community Edition: `uv sync --group ce` (see [Setup](index.md#manim-community-edition)).

### The review panel

Judging a case means looking at it. `just review` builds the panel's web page (Svelte,
built by bun with Vite into `web/dist`) and serves it, with its FastAPI server, at
<http://127.0.0.1:8000>. The panel browses the corpus, shows each case's frames from both
engines side by side, and records verdicts; it also changes the comparison's settings and
renders a case again.

For work on the panel itself, `uv run fastapi dev` serves the server alone, reloading as
it changes, and `bun run dev` in `tests/integration/review/web/` serves the page.

See [`tests/integration/review/`](https://github.com/academa-labs/manimgx/tree/main/tests/integration/review).

## Coverage

Coverage says which lines of ManimGX the tests run, and so which lines no test checks.
`just test-coverage` runs the suite with [pytest-cov](https://pytest-cov.readthedocs.io):
a summary in the terminal, and every line in `htmlcov/index.html`.

`[tool.coverage.run]` in `pyproject.toml` measures the package in the tests' processes and
in the ones they start (the corpus renders each case in its own), with paths relative to
the repository, so that runs on different systems combine: `just combine-coverage <folder>`
makes one report of their data files.

The Test workflow combines the coverage of its runs and publishes the report, served by
Cloudflare as
[`.github/deploy/coverage.jsonc`](https://github.com/academa-labs/manimgx/blob/main/.github/deploy/coverage.jsonc)
says: `main`'s at <https://coverage.manimgx.academa.ai>, a pull request's (from a branch of
this repository) at a preview address, and each commit's linked from its "coverage"
status.

## Benchmarks

Speed is a feature, and a change that slows ManimGX down is a regression like any other.
The benchmarks, in
[`tests/benchmarks/`](https://github.com/academa-labs/manimgx/tree/main/tests/benchmarks),
look for one in two ways: laws of cost, which run with the rest of the suite, and timed
benchmarks, which run alone.

### No benchmark holds a number of seconds

A test that asserts "this scene renders in under two seconds" checks the machine as much as
the code. A scene takes twice as long on one machine as on another (GitHub gives a single
runner label to machines 1.5 times apart), and on one machine one run differs from the next
by a few percent. So no benchmark compares a measurement with a number written down: each
compares two measurements taken side by side.

- **Work**, what a render does, is the same on every machine, and can be counted exactly:
  the Python functions ManimGX runs and its loops' iterations (counted with
  [`sys.monitoring`](https://docs.python.org/3/library/sys.monitoring.html)), the points
  computed from a geometry's pieces, the bytes hashed, the bytes handed to the engine
  ([`work.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/work.py)).
  The laws compare the work of two sizes of one thing.
- **Time** can only be compared with time measured on the same machine at the same time.
  The timed benchmarks run this checkout and another commit's ManimGX in turns, and
  compare them round by round.

### Laws of cost

[`test_laws.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/test_laws.py)
states how work may grow, and Hypothesis checks it:

- **Growth.** A thing made twice as big does at most twice the work, with a tenth to spare
  (a surface of twice the resolution, four times): a path built curve by curve, a group of
  shapes played, a text written, a graph redrawn every frame, a path traced for longer, a
  film held for longer, a table laid out. Some cost Python nothing more as they grow, their
  arrays doing the growing (`PYTHON`: no loop runs once an element). Each is a row,
  `law(build, sizes, power)`: `build(n)` sets a run of size n up and returns it, and only the
  run is counted. Hypothesis draws the size, and
  [`target`](https://hypothesis.readthedocs.io/en/latest/reference/api.html#hypothesis.target)
  climbs toward the worst ratio; the largest size always runs. A law that counts nothing of
  ManimGX's fails.
- **Sharing.** Copies of any mobject, moved, turned and scaled, upload what one does: a
  shape is uploaded once, and its copies and moves are placements of it. Hypothesis draws the
  class from the registry of every public mobject class, and the copies and the moves.
- **Stillness.** A scene that holds a mobject still (one with no updater) does as much work
  for a second as for half a minute: a held frame is sent once.
- **History.** A story told four times does twice the work of two tellings: nothing a scene
  keeps makes its later frames dearer.

They run with `just test`, in seconds, on every system. They find what changes how work
grows: when a path read all of its points to find where it ends (fixed in `eef74e37`), a
path of twice the curves computed four times the points, and the laws of paths and of
traced paths fail on that code. A law that fails today is marked
`xfail(strict=True)` with its reason, and the day the code is fixed the mark has to go.

Work cannot see an operation that became slower, the same calls each taking longer: that is
what the timed benchmarks are for.

### Timed benchmarks

A workload is a scene rendered as a user renders it: `manimgx render`, in a process of its
own, from launch to the finished video. The workloads, in
[`test_speed.py`](https://github.com/academa-labs/manimgx/blob/main/tests/benchmarks/test_speed.py),
are three scenes, at 1920 × 1080 and 60 frames per second as the README's
[benchmark](https://github.com/academa-labs/manimgx/tree/main/benchmarks) makes its own
([`scenes/`](https://github.com/academa-labs/manimgx/tree/main/tests/benchmarks/scenes):
a surface the camera circles, a surface rebuilt every frame, and a 2D explainer), and six
example films at 480 × 270 and 10 frames per second. In the suite, each is rendered once,
tiny: it still renders. `just bench` times them against another ManimGX:

```sh
just bench                # this checkout against main
just bench HEAD           # your uncommitted changes against the last commit
just bench v0.1.0         # against any commit, branch or tag
just bench ../manimgx-2   # against another checkout, as it is on disk
just bench main -k orbit  # some of the workloads (arguments go to pytest)
```

- REF's ManimGX is made in pytest's cache (`.pytest_cache/`), from git: with this checkout's
  engine when REF's engine sources (`rust/`) are this checkout's, else built (the first time
  takes a few minutes). A different engine owns its build directory, so compiled output
  cannot cross between the two source trees.
- Each run is a fresh process, with a fixed hash seed and an empty temporary directory, so no
  run finds another's Typst layouts. It is measured from launch to exit: what the README
  times, the imports, the GPU coming up, the storyboard and the encoder included.
- What is judged is the steadiest measure the host exposes. When every sample has a positive
  instruction count, the comparison uses the instructions a process retires, which do not
  change with the cores that ran it, or with what else the machine does. On a Mac whose GPU
  another program kept 90% busy, identical trees agreed to
  within 1.7% in every round; their CPU time differed by up to 36% and their wall time by 57%.
  If any counter is unavailable, as on hosted macOS VMs, every sample and retry uses CPU time,
  every thread's. Each workload's row names its measure. Wall time includes contention and
  waits; it and the process's peak memory are reported but not judged.
- A round runs both, in a random order. The first round is not kept: it reads each tree's
  files into the disk's cache (a tree made a minute before ran 12% slower until then). Then
  five rounds (`--bench-rounds`).
- A round's two measures make a ratio. A workload is slower when the median ratio is more
  than 5% above 1 and the rounds agree, every one of the five: a machine's noise sends ratios
  both ways, and a real change moves all of them. A workload that looks slower is timed five
  rounds more, and is judged on all ten: nine must agree. Then its test fails. A workload that
  REF cannot render (it uses what came after REF) is skipped.
- Each tree's work is counted too, once, and the table shows the counts that changed:
  "points ×7328" says what a slowdown did.

Put into the code, a slowdown is found where it costs 5% or more; nothing is found when
nothing changed. Measured on that busy Mac, commit `289730bd`:

| This checkout | Workloads found slower | Largest change, and its work |
| --- | --- | --- |
| Unchanged | none: every round within 1.7% | no count changed |
| A path read whole to append a curve (`eef74e37` reverted) | neural_untangle, of the 3 tried | +60%: 7,328 times the points |
| 0.5 ms of Python in every frame | 5 of 9 | +9% (explainer): loops ×6.2 |
| 150 ms of work as ManimGX is imported | 4 of 9 | +13% (taylor_poles) |
| A surface refined twice | morph | +50% |

Timing each scene's frames inside one process, as the benchmarks did before, saw none of the
work done as ManimGX is imported; judging CPU time on that Mac, an identical tree came out
12% faster, and a change to code a film never runs made it "5% slower", in every round. What
instructions cannot see, a wait (a process that sleeps until its GPU is done) or work done on
the GPU, shows in the wall-time column: read it on a quiet machine.

The [Benchmark workflow](github-workflows.md#2-benchmarkyaml-the-timed-benchmarks) runs them
on macOS for every pull request that changes the package, against its base, and for every
push to `main`, against the commit before it; its table is in the run's summary. The measure
is retired CPU instructions when available, otherwise CPU time, and Metal draws on the GPU.
This gates host work,
including geometry, typesetting and encoding; it does not gate GPU execution or waits.
For changes to shaders or GPU scheduling, review the paired wall times on a quiet machine;
`just bench` on Linux with lavapipe also includes software drawing in its CPU measure.
The nine workloads, their resolutions and their rounds are the same on either system.
A change that is meant to cost time (a feature) says so in its pull request, with the table.

## Learn more

- [`test_corpus.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/test_corpus.py):
  the three checks.
- [`corpus/case.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/case.py):
  what a case holds, and its states.
- [`corpus/__main__.py`](https://github.com/academa-labs/manimgx/blob/main/tests/integration/corpus/__main__.py):
  the corpus's tools.
