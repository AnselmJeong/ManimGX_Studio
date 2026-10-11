# Benchmarks

How long ManimGX, ManimGL, Manim Community Edition (ManimCE) and Blender take to make the
same five scenes into 1080p60 MP4 videos, each with its own renderer. The
[README](../README.md)'s numbers, chart and comparison images all come from this folder: the
scenes, the runner, its recorded results, and the scripts that draw the chart and the images.

## Results

Times are in seconds, from launching the engine to its finished MP4. Lower is better.

| Scene | Video | ManimGX | ManimGL | ManimCE | Blender Workbench | Blender EEVEE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Surface and orbiting camera (`orbit`) | 10 s | 1.184 | 6.463 | 211.809 | 16.563 | 220.242 |
| Matrix-vector multiplication (`matrix`) | 7.2 s | 0.360 | 8.287 | 7.140 | 11.045 | 90.798 |
| Twelve pendulums (`pendulums`) | 13 s | 0.756 | 16.812 | 4.745 | 19.860 | 165.890 |
| Planets and moons (`hierarchy`) | 3 s | 0.334 | 1.789 | 16.169 | 4.979 | 62.265 |
| Linked rings (`linked_rings`) | 3 s | 0.443 | 1.933 | 38.962 | 5.163 | 62.200 |
| Total | 36.2 s | 3.078 | 35.284 | 278.826 | 57.611 | 601.395 |
| Relative to ManimGX | | 1× | 11.5× | 90.6× | 18.7× | 195.4× |

A scene's time is the mean of three runs for ManimGX and ManimGL, and a single run for
ManimCE and each Blender renderer. A total adds an engine's five scene times.
[`results.json`](results.json) holds all 45 runs: the command of each, its wall and CPU
times, and the checks of its video.

Measured on October 7, 2026, on an Apple M4 Pro (12 CPU cores, 24 GB of memory) with macOS
15.7.9: ManimGX 0.1.0, ManimGL 1.7.2, ManimCE 0.21.0 and Blender 5.2.2 LTS.

## Scenes

| Scene | What it shows |
| --- | --- |
| `orbit` | A 48 × 48 surface on three axes, a curve drawn across it with a ball riding its tip, and an orbiting camera. |
| `matrix` | A matrix-vector product, its arithmetic written out, and the resulting vector. |
| `pendulums` | Twelve pendulums of different lengths, their rods and bobs swinging, under a title. |
| `hierarchy` | Five planets and five moons moving around a central sphere, seen by an orbiting camera. |
| `linked_rings` | Eight linked rings (tori of 32 × 8 faces) moving under one key light, seen by an orbiting camera. |

Each engine makes the scenes with its own API: geometry, animation, text and shading. In
[`scenes/`](scenes), `orbit`, `matrix` and `pendulums` have a file for each Manim engine
(`orbit_manimgx.py`, `orbit_manimgl.py`, `orbit_manim_ce.py`, …); `hierarchy` and
`linked_rings` share one for the three (`suite_manim.py`). Blender's scenes are scripts for
its Python API (`*_blender.py`). `suite_data.py` holds what the engines share: the
scenes' lengths, the output's size and frame rate, and the shapes' positions over time.

## Method

- **The same videos.** Every engine makes each scene at 1920 × 1080 and 60 frames a second,
  as H.264 video (`yuv420p`) in an MP4, with its own renderer and exporter: `manimgx
  render`, ManimCE's `manim render`, `manimgl -w`, and Blender in the background
  (`blender -b`), with Workbench or EEVEE. EEVEE takes 64 samples a pixel; Workbench draws
  with its rasterizer.
- **The fastest encoding.** ManimGX, ManimGL and ManimCE encode with x264's `ultrafast`
  preset at CRF 23: ManimGX through its command's options, ManimCE and ManimGL through
  `scenes/ce_cli.py` and `scenes/ffmpeg.py`, which hand those options to their encoders.
  Blender's fastest preset is `REALTIME`, also at CRF 23; the options it encodes with
  correspond to x264's `superfast`.
- **From launch to finished MP4.** A run's time starts when its process launches and ends
  when the process exits: starting up, building the scene, rendering, encoding and
  finishing the MP4. ManimGX's time includes the storyboard and the layout checks that
  `manimgx render` always makes.
- **Fresh processes.** Each run starts a new process, with an output folder and a cache of
  its own (ManimCE's cache is off). The runs go one after another. The operating system's
  and the GPU driver's caches are not cleared between them.
- **Checked videos.** After the timer stops, the runner decodes every frame of the video and
  checks its size, pixel format, frame rate, timestamps and length, and the x264 options
  the file records. ManimGX's MP4 doesn't record them; its command sets them
  (`--preset ultrafast --crf 23`).
- **The same length.** A video must last as long as its scene, to within one frame.
  ManimGX's ends with one more frame, the scene's last moment. Where the picture holds
  still, ManimGX encodes it once, as a longer frame: its `matrix` and `pendulums` videos
  have 243 and 721 frames over 433 and 781 frames of time. The other engines encode every
  frame.

## Run it

The runner works on macOS and Linux. It needs this repository's environment (`just sync`),
whose ManimGX it measures; FFmpeg, with `ffprobe`; a LaTeX distribution, for ManimCE and
ManimGL; Blender 5.2.2 LTS; and an OpenGL context, for ManimGL.

Make an environment each for ManimCE and ManimGL, from the repository's root:

```sh
uv venv --python 3.13 .cache/benchmark-envs/ce
uv pip install --python .cache/benchmark-envs/ce/bin/python 'manim==0.21.0'
uv venv --python 3.12 .cache/benchmark-envs/gl
uv pip install --python .cache/benchmark-envs/gl/bin/python 'manimgl==1.7.2' 'setuptools==80.9.0'
```

Then run every scene on every engine, with the path to Blender:

```sh
uv run --frozen python -m benchmarks.run \
  --out .cache/comparison/five-scenes \
  --ce-python .cache/benchmark-envs/ce/bin/python \
  --manimgl .cache/benchmark-envs/gl/bin/manimgl \
  --blender /path/to/blender
```

The output folder must not exist yet. It receives each run's MP4 and log, and
`results.json`, with each run's command, times and checks, written again after every run. A
run that fails, makes an invalid video or runs out of time stops the command, and stays
recorded. An engine has a total only once all its runs are complete.

`--scenes orbit linked_rings` chooses the scenes, and `--tools manimgx manimgl` the engines.
`--rounds 1` sets the number of runs for every engine. `--timeout 900` sets the seconds a
render may take. `--gx` measures another `manimgx`, such as one installed with pip.
`--dry-run` writes the plan of commands without starting a renderer.

## The chart

Draw the README's chart, dark and light, from the recorded results:

```sh
uv run --frozen python -m benchmarks.chart
```

It writes `docs/content/images/benchmark-dark.svg` and `benchmark-light.svg`: each engine's
total time in seconds, on one linear scale. To chart a new complete run into a folder of its
own:

```sh
uv run --frozen python -m benchmarks.chart \
  --results .cache/comparison/five-scenes/results.json \
  --out .cache/comparison/five-scenes/charts
```

## The comparison images

The README compares the engines on one frame: the linked rings at 2.5 seconds. Render it
with each engine:

```sh
uv run --frozen python -m benchmarks.quality \
  --out .cache/comparison/linked-rings-images \
  --ce-python .cache/benchmark-envs/ce/bin/python \
  --gl-python .cache/benchmark-envs/gl/bin/python \
  --blender /path/to/blender
```

`scenes/quality_manim.py` makes the frame with the three Manim engines, and
`scenes/linked_rings_blender.py` with Blender's two renderers. Each engine keeps its own
shading. ManimGX and Blender color the rings with the scenes' colors; ManimCE's and
ManimGL's are darker, by 0.24 and 0.18 of each RGB channel.

`native/` receives each engine's frame, 1920 × 1080 and transparent, with its log and
command. `images/` receives the README's ten images, the files of
`docs/content/images/benchmark-quality/`: the same 302 × 524 part of each frame, the part
that holds the rings, on the site's dark (`#0B0C0F`) and light (`#FFFFFF`) backgrounds.
