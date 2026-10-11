# The engine

The engine is the Rust crate in [`rust/engine/`](https://github.com/academa-labs/manimgx/tree/main/rust/engine), one of the
crates of the Rust workspace, [`rust/`](https://github.com/academa-labs/manimgx/tree/main/rust).
maturin compiles it into the package as `manimgx._engine`, a Python extension module. It
does three things: it draws frames on the GPU, encodes them into an MP4, and typesets text.
Python decides what each frame shows; the engine makes the pixels. It also records a film as
a *take*, the same work written down, for ManimGX's player to play: one player, the same in a
window of its own on this machine's screen (`manimgx preview`) and on a page's canvas, where
the engine itself, compiled to WebAssembly, is the player.

## Why a compiled engine?

Drawing a frame means computing millions of pixels, and a GPU does that through native
APIs (Metal, Vulkan) that Python cannot reach directly. Typst is a Rust library, and x264
a C library. A compiled extension module holds all of them in the Python process: no
subprocess, and no files passed between programs.

The crate's dependencies do the heavy lifting:

- [wgpu](https://wgpu.rs): one GPU API over Metal, Vulkan and the others.
- [PyO3](https://pyo3.rs): the Python module, its classes and its functions.
- [wasm-bindgen](https://wasm-bindgen.github.io/wasm-bindgen/): the player's bindings to
  JavaScript, and wgpu's to the browser's WebGPU and Web Audio.
- [Typst](https://github.com/typst/typst) (`typst`, `typst-kit`, `typst-layout`): the
  typesetter, as a library.
- [mitex](https://github.com/mitex-rs/mitex): LaTeX converted to Typst.
- [x264](https://www.videolan.org/developers/x264.html): the H.264 encoder, a C library,
  built from its source with the engine (`rust/x264/`).
- [FFmpeg](https://ffmpeg.org)'s audio decoders, with [libopus](https://opus-codec.org) for
  Opus: C libraries, built from their sources with the engine (`rust/ffmpeg/`).
- [winit](https://github.com/rust-windowing/winit): the window `manimgx preview` plays in;
  [cpal](https://github.com/RustAudio/cpal): its sound, on macOS and Windows.
- [rustybuzz](https://github.com/harfbuzz/rustybuzz), the shaper Typst sets text with, and
  [unicode-bidi](https://github.com/servo/unicode-bidi): the player's face's text, in lines.

## Files

| File | What it holds |
| --- | --- |
| [`src/lib.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/lib.rs) | The crate: its builds (features), and the content key |
| [`src/render.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/render.rs) | The GPU's player (`Player`, Python's too): the store of shapes, a frame's passes, the GPU |
| [`src/lavapipe.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/lavapipe.rs) | Mesa's lavapipe, which a Linux wheel bundles, loaded where no GPU driver is |
| [`src/python.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/python.rs) | The Python module: the `Player` and `Recorder` classes and the functions Python calls |
| [`src/take.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/take.rs) | A take's messages, written and read |
| [`src/pack.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/pack.rs) | A take's arrays, each coded against the one it replaces |
| [`src/project.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/project.rs) | The projector: takes as they come, any frame of them drawn on demand, in bounded memory |
| [`src/player.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/player.rs) | ManimGX's player, on any screen: the projector on a clock, its face and sound, its viewer's input |
| [`src/chrome.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/chrome.rs) | The player's face (its controls, its text), drawn by the engine itself |
| [`src/text.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/text.rs) | The face's text: lines shaped as Typst shapes them, in ManimGX's fonts |
| [`src/speaker.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/speaker.rs) | The player's sound, following its clock: a window's (cpal), a page's (Web Audio) |
| [`src/window.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/window.rs) | The player in a window on this machine's screen (winit) |
| [`src/web.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/web.rs) | The player on a page's canvas (WebAssembly) |
| [`src/export.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/export.rs) | A film's video: frames converted and handed to the encoder |
| [`src/vector.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/vector.rs), [`src/vector.wgsl`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/vector.wgsl) | Path coverage and the view's composite |
| [`src/blend.wgsl`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/blend.wgsl) | The raster pipeline: point clouds and meshes |
| [`src/paint.wgsl`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/paint.wgsl) | Paint, as both pipelines evaluate it |
| [`src/nv12.wgsl`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/nv12.wgsl) | A frame's changed macroblocks, converted for the encoder |
| [`src/encode.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/encode.rs) | H.264 through x264 |
| [`src/mp4.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/mp4.rs) | The MP4 file |
| [`src/audio.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/audio.rs) | Sound read from its files (FFmpeg), and resampled |
| [`src/aac.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/aac.rs) | A film's sound, as AAC |
| [`src/typeset.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/src/typeset.rs) | Typst as a library, and mitex |
| [`build.rs`](https://github.com/academa-labs/manimgx/blob/main/rust/engine/build.rs) | The player for a page, built beside Pyodide's module and carried inside it |
| [`../mitex-spec-gen/`](https://github.com/academa-labs/manimgx/tree/main/rust/mitex-spec-gen) | mitex's Typst package (fetched), and the LaTeX command spec made from it |
| [`../x264/`](https://github.com/academa-labs/manimgx/tree/main/rust/x264) | x264, built from its source (fetched), behind a C shim and a few safe calls |
| [`../nasm/`](https://github.com/academa-labs/manimgx/tree/main/rust/nasm) | NASM, built from its source (fetched), for x264's x86-64 assembly |
| [`../ffmpeg/`](https://github.com/academa-labs/manimgx/tree/main/rust/ffmpeg) | FFmpeg's audio decoders and libopus, built from their sources (fetched), behind a C shim and one safe call |
| [`../fetch/`](https://github.com/academa-labs/manimgx/tree/main/rust/fetch) | The sources the other crates build from, fetched by their build scripts and pinned by the hash of their files |

Each file begins with a comment that states its design.

## The boundary with Python

[`src/manimgx/_engine.pyi`](https://github.com/academa-labs/manimgx/blob/main/src/manimgx/_engine.pyi)
is the engine's interface as Python sees it, typed: the `Player` and `Recorder` classes,
the typesetting functions, `digest` (the content key that names what is uploaded), `note`
and `TypstError`. It is
written by hand, so a change to the engine's interface changes it too; ty checks the Python
code against it.

- **One module for every Python from 3.13 on.** The crate builds against Python's stable
  ABI (PyO3's `abi3-py313`).
- **Bytes, not objects.** What crosses is packed arrays: control points as float64,
  records of 336 bytes, a view of float32s. Python packs them with numpy
  ([`rendering/feed.py`](https://github.com/academa-labs/manimgx/blob/main/src/manimgx/rendering/feed.py));
  the engine reads them as they are. A shape crosses as its object defines it, and the
  engine derives what drawing needs: it flattens a path's curves, and sums a mesh's faces
  into its vertices' normals.
- **Upload once, then per frame.** `add_path`, `add_points`, `add_mesh`, `add_rows` and
  `add_texture` store a shape, a set of color rows or an image under a key; `grow_path`
  extends a path, and `evict` forgets what no frame shows any more. A frame is then a view
  and its records: `render` draws one and reads it back as RGBA, and `push` sends one to
  the video that `begin_export` started and `end_export` finishes.
- **A take is the same calls, written down.** `Recorder` takes the uploads a `Player` takes,
  then `frame` for each frame, and writes them as messages: a take, which the projector reads
  back (see [The player](#the-player) and [The browser](#the-browser)). A film given `take`
  records into one.
- **The GIL is released** while the engine draws and encodes, so other Python threads run.
- **One GPU per process**, brought up on a thread of its own once the process knows it will
  draw (`start_gpu`): a drawing command starts it before the rest of the command line loads,
  and a film with a video or frames as it begins. It comes up meanwhile, and the first frame
  waits for it; a process that never draws (`manimgx --version`, a take, a film that only
  counts its frames) never brings it up. A process that ends before the GPU is up waits for
  it, as Python exits: exit unloads the drivers, and must not unload one while it starts.

## Drawing

wgpu takes the high-performance adapter: Metal on macOS, Direct3D 12 on Windows (WARP,
on the CPU, where there is no GPU), Vulkan on Linux. The engine needs one that can blend
float32 render targets, since a 2D view adds up its coverage in one.

On Linux, where no adapter will do (no GPU driver: a server, a container), the engine draws
with Mesa's lavapipe, Vulkan on the CPU, which the Linux wheels bundle beside it
(`manimgx/lavapipe/libvulkan_lvp.so`, built from Mesa's source with LLVM linked in by
[`scripts/release/build_lavapipe.sh`](https://github.com/academa-labs/manimgx/blob/main/scripts/release/build_lavapipe.sh)).
`src/lavapipe.rs` loads it as Vulkan's loader loads a driver, and gives wgpu an instance of
it: neither the system's loader nor the environment is involved, and a machine with a GPU
never loads it. An engine built from source has none of its own; there, the system's Mesa
draws.

### Path coverage and compositing

Paths use analytic coverage of flattened segments instead of counting multisample hits.
The same pipeline draws paths in 2D and through a 3D camera.

1. A compute pass flattens every curve of every path into as many segments as its size on
   screen needs (Wang's bound targets 1/32 of a pixel, with at most 256 segments per curve),
   every frame, at the size it is drawn.
2. A raster pass adds each segment's exact area into the object's rectangle of a float
   atlas: a fill by its winding, a stroke as pieces along the curve's normals, with
   its joints and caps.
3. A compute pass composites each 16×16 tile of the view over the objects that reach it,
   in depth order, with draw order breaking ties. It keeps each pixel as two regions split
   by a line to retain the overlap of shared edges.

The segment areas are analytic; the complete image is an approximation. Curves are
flattened, coverage is accumulated in floating point, and each partially covered layer's
boundary is reconstructed as a half-plane. Two regions cannot retain every intersection
of several partial layers. The composite also approximates nearly parallel boundaries
as parallel, and merges its regions between atlas groups. These limits matter when
several edges or transparent surfaces meet inside one pixel.

A 2D view's point clouds and meshes are drawn by the raster pipeline, into layers that the
composite lays in their place in the order.

See `vector.rs` and `vector.wgsl`.

### The raster pipeline

The raster pipeline draws point clouds and meshes, with per-sample depth. In a 3D view,
their raster base is combined with the paths' analytic coverage and depth planes.
A vertex is placed by the blend itself:
clip = C₁·S₁ + C₂·S₂, where Cₖ = camera · Mₖ is composed on the CPU once per object (the
second term only while a shape morphs). The kinds differ only in how their vertices become
triangles:

- A point is a disk that faces the camera.
- A mesh is its triangles, optionally textured.

Transparent mesh fragments are collected in lists and composited in depth order. Point
sprites are sorted and drawn between the other geometry's depth layers. Raster sample
coverage and the paths' reconstructed coverage are different representations; their
combination does not preserve every subpixel overlap.

A camera's picture, as a [`ZoomedScene`][manimgx.ZoomedScene] shows it, is a view drawn
first into a texture, which the frame then samples by its key.

See `blend.wgsl`, and the `Player` in `render.rs`.

### Paint

`paint.wgsl` is shared by both pipelines. Colors mix in OKLab, weighted by opacity, as
Python's colors mix. A gradient is evenly spaced stops. A tween's paint is two paints and
how far the second is mixed in: the engine mixes them, so a tween uploads nothing.

## Encoding

**The problem:** encoding a video frame by frame repeats work where nothing changed, and
most of an animation's frame does not change: a moving square touches a few blocks of the
picture.

**The engine's answer:** the records say what changed, so only that is converted, read
back and analyzed.

1. For each frame, the engine finds the 16×16 macroblocks that can differ from the
   previous frame: the old and new footprints of every record that changed. A new camera,
   objects added or removed, or anything that cannot be bounded makes it the whole frame.
2. It converts only those macroblocks to NV12 on the GPU (`nv12.wgsl`), and reads only
   those back.
3. x264, on a thread of its own, is told which macroblocks are unchanged and skips its
   analysis there (`encode.rs`).
4. `mp4.rs` writes each picture as a sample of an MP4; a held frame is one sample that
   lasts longer. Each sample keeps its duration when B-frames change the decoding order.
   The decode clock accumulates those durations; signed composition offsets preserve the
   authored display times. This is the MP4 timing contract: sample-table timing determines
   presentation, including the final hold, independently of the encoder's decode timestamps.
   The header is written first, so a player can start before the file has arrived.

[`Film.export`][manimgx.Film.export] reports how it went: the seconds taken, the part of
them in x264, the share of macroblocks converted, and the file's size.

x264 is built with the engine, from its source (r3223, 8-bit, without its command line), so
nothing is installed and the engine links it statically. Its build
script writes the configuration x264's `configure` would for the target, then compiles its
C and its assembly with the `cc` crate: NEON and SVE with the C compiler on AArch64; on
x86-64, SSE to AVX-512 with NASM, which x264's x86 code is written for. NASM comes from its
source too (`rust/nasm/`): compiled into x264's build script, which runs it as a process of
itself. Elsewhere, x264's C alone; assembly makes x264 two to five times faster. Rust sees
x264 through `x264/src/shim.c`, which sets x264's parameters and moves pictures in and samples
out, so x264's structs never cross into Rust. The build takes a few seconds, and makes the
same bytes as a `configure`-built x264.

## Typesetting

`typeset.rs` runs Typst as a library. `typeset` takes Typst source and returns its layout,
read straight off Typst's frames: every glyph with its outline's key, its placement, its
paint and the bytes of the source it draws; every shape as cubic curves; every labelled
group as the items inside it. A glyph's outline comes separately, by key
(`glyph_outlines`), so it crosses once.

Fonts come from the folders Python passes, ManimGX's own among them: the font packages'
([`fonts/manimgx-fonts/`](https://github.com/academa-labs/manimgx/tree/main/fonts/manimgx-fonts)
and
[`fonts/manimgx-fonts-cjk/`](https://github.com/academa-labs/manimgx/tree/main/fonts/manimgx-fonts-cjk),
published apart and required at exact versions), then from Typst's embedded fonts. The
system's fonts are read only for a family a text names: their scan is cached on disk, and
they are memory-mapped, not read whole (a CJK font can be 60 MB).

LaTeX reaches Typst through mitex (`mitex_math`, `mitex_text`). mitex converts by a
*command spec*: which LaTeX commands it knows, and how many arguments each takes. mitex's
own spec crate reads the spec from a git submodule or makes it with a `typst` on the PATH;
`rust/Cargo.toml` replaces that crate with
[`mitex-spec-gen`](https://github.com/academa-labs/manimgx/tree/main/rust/mitex-spec-gen),
which fetches mitex's Typst package (with its own `lib.typ`, which imports only the scope the
converted LaTeX calls) and holds the spec (`spec.rkyv`) made from it. The engine serves the
package to Typst itself, as `@preview/mitex:0.2.7`, so
the converted code finds its scope with no files on disk, and the converter and the Typst
code it converts for come from the same files. `cargo test -p mitex-spec-gen`, in `rust/`,
checks that the committed spec is still what the package makes, and that the engine serves
every file of it; after an upgrade of mitex, `MITEX_SPEC=write cargo test -p mitex-spec-gen`
writes the new spec. The Test workflow checks the spec with the rest of the Rust workspace
through `just test-rust`; it never regenerates it.

## The player

ManimGX's player plays takes: [`manimgx preview`](../user-guide/rendering.md#preview) and
[`Window`][manimgx.Window] in a window of its own on this machine's screen, the npm package on
a page's canvas. It is one player, `player.rs`, the same code on both screens: a screen gives
it a surface, hands on its viewer's input, draws it when it is due and does what it asks. The
window's screen is winit's (`window.rs`); a page's is the engine compiled to WebAssembly
(`web.rs`), with the page's element handing on its events
([`browser/src/player.ts`](https://github.com/academa-labs/manimgx/blob/main/browser/src/player.ts)).

- **Any frame, at once.** The player keeps the take as sent (`project.rs`), and draws the frame
  its clock is at, at the size it is shown, in the screen's own pixels. A newer take, the scene
  run again, replaces the one shown once it has the moment shown, or ends: an edit never loses
  the place. A take ends with a message of its own (END), which says whether its scene failed:
  a failed take replaces the shown one only if it got to the moment shown. A save cuts a run it
  makes out of date (the take raises `Cut`), and the scene runs again at once. A frame whose
  see-through layers overflow the lists is drawn again once its count is back: the player never
  waits for the GPU.
- **One clock.** It runs from an instant at a rate, waits at the last frame made while the take
  is being recorded, and stops at the end; a frame is drawn for the moment it is seen (a
  refresh of the screen ahead). The sound follows it (`speaker.rs`), continuous while the clock
  runs, again from the clock after a jump or 30 ms of drift: in a window, written for the
  instant it is heard (cpal; on Linux the window is silent, as the system's audio would be
  linked, ALSA); in a page, a Web Audio source started at the context's moment that is heard
  when the clock is there (its output timestamp ties the context's clock to the page's).
- **Its face is the engine's own drawing.** The controls, the time, the plays (its chapters,
  named by the lines that played them), the captions, the error and the keys are shapes and
  text, records of a 2D view over the film, drawn exactly (`chrome.rs`): no toolkit, and one
  face on both screens. Its text is set in lines, in ManimGX's fonts (`text.rs`), shaped by
  rustybuzz, the shaper Typst sets text with: a test sets the face's lines both ways and finds
  the same glyphs in the same places. Typst itself, a typesetter of documents, would be 28 MB
  of WebAssembly in a page; the lines take 0.7 MB. The player composites the film, at its
  place, and the face in one pass. A control is where the layout put it, so a click, a tap and
  a key do the same thing.
- **Input in the web's words.** A key comes as its `KeyboardEvent.key` value (winit names keys
  as the web does), a pointer as its place in pixels, a wheel's turn in points, the web's way
  round. Each input says whether the player took it, so that a page lets the rest go by: a
  vertical scroll over a film scrolls the page, a sideways one moves the playhead.
- **Notes, both ways.** The director's notes (JSON) give it the plays, sections and captions,
  and between takes the file's scenes and the scene's error. The player asks for another of the
  file's scenes: the window writes the ask as a line of JSON on its standard output, the page
  posts it to its director.

The window is a process of its own (`python -m manimgx.rendering.window`, whose main
thread runs the window's event loop, `_engine.window`), and the take reaches it through a pipe, on its
standard input: so the scene keeps its process — its main thread, its signals — as
`manimgx render` gives them, a script or a notebook can open one, and a scene that crashes
leaves the window up. A `Window` is a take: `Scene.render(take=window)`. Closing it cuts the
film sent to it (`Cut`); it closes when its director closes it, or goes. On a page, the player
runs on the page's own thread, as the window's runs on its own: its events, its clock, its
drawing and its sound on one thread, so it says at once whether it took an input.

Measured on an M4 Pro: a save is on screen 43-79 ms later; the window draws the heaviest
example film (the Hopf fibration, 2560×1440) in 0.5-1.7 ms a frame (the median), using 5-17%
of a core at 60 Hz in 150-320 MB. In Chrome, a page's thread spends 0.7 ms a frame on it, face
included (the median; 1.2 ms at the 95th percentile, at 1920×1080).

## The browser

In the browser, Python runs in [Pyodide](https://pyodide.org), which has no GPU, and the
engine is two WebAssembly builds of the same crate:

- **The Python module, without the GPU** (features `python` and `typeset`): typesetting, the
  content keys, sound read, and `Recorder`, but no `Player`. Pyodide's toolchain compiles it for
  `wasm32-unknown-emscripten`, and it ships as ManimGX's wheel for the browser
  (`pyemscripten_2026_0_wasm32`, [PEP 783](https://peps.python.org/pep-0783/)). There, every
  film is recorded as a take.
- **The player** (feature `web`, for `wasm32-unknown-unknown`): `player.rs` on a page's canvas,
  drawing with WebGPU and sounding with Web Audio (`web.rs`). The page's element hands it the
  take as it comes (`feed`), its viewer's input (`key`, `pointer`, `press`, `release`, `cancel`,
  `wheel`) and its canvas's size, and draws it when it is due (`wake`, `draw`). It keeps the
  take as sent, coded, and makes a frame's shapes from it when the frame is drawn; the GPU's
  player keeps what the frames drawn lately drew, up to a budget. Its face's fonts come from
  Pyodide, the ones the window's face is set in: `_engine.face_fonts` gives ManimGX's font
  files and Typst's monospace font.
  [`browser/`](https://github.com/academa-labs/manimgx/tree/main/browser) holds the
  page's side: the element and the director's worker (Pyodide).

A take is the protocol between Python and the player: `manimgx preview` sends one through a
pipe to its window, and in the browser the director hands one from Pyodide to the page. What
its uploads hold goes as arrays (`pack.rs`), each under a key of its
kind and content, sent once, and coded against the array it replaces: the same role's in what
the same record slot drew the frame before, which the writer reads off the frames' records. A
film whose shapes change a little every frame is sent as their changes: the example films'
takes are 14 times smaller for it (50 GB in all before, 3.6 GB after), and a 3D film of 30
seconds is tens of megabytes, where it was gigabytes. A mesh's points, uvs and normals go as
float32, the precision the GPU draws them at; everything else goes exactly as Python gave it.
The browser and native player share the take decoder and renderer. Replay and direct
rendering are checked for identical pixels on the same adapter and runtime. Different
GPU backends, drivers, and authoring runtimes can produce different floating-point results;
sharing the renderer does not guarantee identical pixels across them.

Each take starts with its format version, exposed to Python as `_engine.TAKE_VERSION`.
It covers the layouts of views, records, uploads and coded arrays. The shared projector
checks it before reading resources, so a native window, browser and headless replay reject
unsupported or unversioned recordings with an explicit error. A change to those layouts
that alters their meaning needs a new format version; package releases and reference
manifests have their own versions.

## Others' sources

The repository holds only ManimGX's code. What the engine is built from that others wrote —
x264 and NASM, FFmpeg's audio decoders and libopus, mitex's Typst package — its crates' build
scripts fetch from where each project publishes it (`fetch::tree`, in `rust/fetch/`), each
pinned by the SHA-256 of its files: their paths and bytes, not an archive's, which hosts
regenerate, so any copy of the same files passes. A tree is fetched once into the crate's
build folder and found again by that hash. The first build needs the network, as cargo does
for crates. `MANIMGX_SOURCES` names a folder for the archives (an absolute path): a build reads
an archive there, and downloads it there first if it isn't. A folder that holds them builds
offline; one shared by your checkouts downloads each archive once; and a build into an empty
one gathers what it was built from. A build script fetches the same archives on every target,
whatever it compiles of them, so one build gathers what every build reads.

The release ships `manimgx-X.Y.Z-source.tar.xz` beside the wheels (`just build-source` makes it).
It is the committed repository, identified by `SOURCE_COMMIT`, with `vendor/`, every crate `rust/Cargo.lock` names
(`cargo vendor`), `sources/`, the archives, and a `.cargo/config.toml` that reads them,
offline. Mesa, glslang and LLVM use the same store through `fetch-file`, pinned by their
archive hashes. LLVM is built with its native target and a source correction that preserves
register-class constraints during rematerialization; its patch and build recipe are in
`scripts/release/`. The Linux wheel jobs also retain the exact source RPMs of libraries
auditwheel actually bundles, identified by auditwheel's SBOM. Each
platform's manifest records its wheel hash, binary package versions and source hashes.
`just build-source` consumes both Linux source artifacts, merged into `release-sources/`,
and checks those hashes before adding them to the source archive.

The archive supplies the distributed components' source; it does not freeze the operating
system or compiler toolchain. Rebuilding lavapipe uses its checked archives, source patch
and build recipe with the required Linux build tools. The engine itself builds without fetching
native sources or Cargo crates once Rust, a C compiler and the Python build dependencies
(including maturin) are installed:

```sh
tar -xf manimgx-X.Y.Z-source.tar.xz
cd manimgx-X.Y.Z && uv build --wheel --no-build-isolation --offline
```

Each is built by its crate's build script with the `cc` crate, the C compiler alone, the same
way on every target: no project's own build system runs. x264's and NASM's scripts write the
configuration their `configure` would for the target. FFmpeg's `configure` resolved the
components ManimGX decodes with once, and `rust/ffmpeg/build.rs` keeps what it resolved (the
names it turns on, the files it compiles; the command is in the script's comment): its
configuration is written from that, in portable C (no assembly, no threads: one file decodes
at a time), the same on every target, the browser's included. Opus goes to libopus, the
reference decoder, which passes all of RFC 8251's test vectors (FFmpeg's own fails four).
`rust/ffmpeg/src/shim.c` decodes a file from memory into float samples, at most two channels
(wider sound is downmixed to stereo, scaled so it can't clip), starting and ending where the
file declares.

On Windows, `rust/dxc/` prepares the exact upstream DirectX Shader Compiler archive, verifies
its SHA-256, and places `dxcompiler.dll` beside the installed extension. The engine loads it
from that package location. Its separately pinned source tree and source dependencies are
retained for source distribution, with their notices in `LICENSE-DXC`; the DLL is an official
binary input, not a compiler rebuilt by every wheel installation.

## Building

- `uv sync`, and every `uv run`, rebuild the engine when one of its sources changes, with
  maturin's release build: see
  [Project management](project-management.md#rebuilding-the-engine).
- `just build-wheel` builds this machine's wheel as a release does, with cibuildwheel, and
  tests it on every supported Python (see
  [Project management](project-management.md#distribution)); `just build-wheel pyodide`
  builds the browser's, with Pyodide's toolchain.
- `build.rs` builds the player for a page with Pyodide's module (a cargo of its own, in
  `rust/target/web-player/`), and the module carries it: `_engine.web()` gives its JavaScript
  and WebAssembly (`engine.js`, `engine_bg.wasm`), which the director hands to the page. It
  needs Rust's WebAssembly target (`rustup target add wasm32-unknown-unknown`); without it the
  module builds, with a warning. A native module carries none: natively, a film plays in a
  window.
- Cargo run by hand in `rust/` (`cargo clippy`, `cargo test -p mitex-spec-gen`,
  `cargo test -p fetch`) uses the `dev` profile, which is optimized too (`opt-level = 2`).
- `rust/engine/Cargo.toml` denies Clippy's correctness lints and warns on its suspicious and
  performance ones. No recipe, check or workflow runs Clippy: run `cargo clippy` in `rust/`.

The installed-wheel suite and integration corpus test the Python boundary (see
[Testing](testing.md)). `just test-rust` tests the Rust workspace on Linux, macOS and Windows,
with the render, export, typeset and player features, without embedding Python. These tests
check that a take reads back as it was written, that its arrays' codings decode exactly, and how the projector
takes takes in: a newer one replacing the shown one at the frame shown, a failed one dropped
or ended, the stream read whole however it is cut. They also check the player: its keys by the
web's names, its chapters, a take's sound read as it was written, and the face's lines, set as
Typst sets them. `just check-rust-web` checks the browser feature boundary, and
`just test-rust-web` runs its browser tests with wasm-bindgen-test-runner and a browser
driver; CI uses Chrome. These focused laws complement manual playback of full scenes in a
browser. The fetch crate's tests, also part of `just test-rust`, check `MANIMGX_SOURCES`: an
empty folder gathers an archive, whole, and a full one builds with the archive gone from its URL.
