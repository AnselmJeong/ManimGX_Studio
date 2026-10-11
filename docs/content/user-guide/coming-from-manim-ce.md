# Coming from Manim CE

ManimGX has the API of [Manim Community Edition](https://www.manim.community): its scenes,
mobjects, animations and constants, with the same names and parameters. Most Manim CE code
runs on ManimGX after you replace `manim` with `manimgx`. But ManimGX decides how that
code behaves. This page shows where it is different.

## Imports and rendering

- Every name is in the package: `import manimgx as m`, then `m.Circle`, or
  `from manimgx import *`. Manim CE's modules are not there: write
  `from manimgx import polylabel`, not `from manimgx.utils.polylabel import polylabel`.
- Render with `manimgx render scene.py MyScene`. Manim CE's quality flags (`-ql`, `-qh`,
  …) become `-r` (`--resolution`) and `--fps`. `manimgx inspect` writes a storyboard and checks 2D layouts without a video. See
  [Rendering and sharing](rendering.md).
- You don't install LaTeX. `Tex` and `MathTex` convert their LaTeX to
  [Typst](https://typst.app), which the engine sets. LaTeX packages and `\def` don't
  convert.

## The frame

A wide video's frame is the same as in Manim CE: 8 units high, about 14.2 wide. A tall
video's frame (9:16) is 8 units wide and about 14.2 high, where Manim CE's is 4.5 wide:
in ManimGX, the frame's short side is 8 units, unless you set `config.frame_height`. So
a scene made for a wide video fits a tall one if it stays in the middle 8 × 8 square.

## Time and animations

- Each frame shows the scene at its own exact time, in plays and in waits, at every frame
  rate. The video ends with a last frame at the scene's end.
- Updaters get the exact time since their last call. They keep running while an
  animation plays their mobject. Updaters that take `dt` run on a clock of their own, so
  a simulation gives the same result at every frame rate.
- `.animate` applies its calls when its animation starts. In a `Succession`, each
  `.animate` starts where the one before it ended.
- A rotation turns the mobject as one rigid piece, about one point.
- Animations of one mobject that start at the same time combine: their movements add.

See [Animations](animations.md) and [Updaters](updaters.md).

## One name for each thing

For most things that Manim CE names twice, ManimGX keeps one name. The other still
works, but your editor marks it deprecated and names the one to use:

- `MovingCameraScene` is `Scene`: every scene's camera moves.
- `ApplyMethod(square.scale, 2)`, `ScaleInPlace(square, 2)` and
  `FadeToColor(square, m.RED)` are `.animate`: `square.animate.scale(2)`,
  `square.animate.set_color(m.RED)`.
- `arrange_submobjects` is `arrange`, `rotate_about_origin(angle)` is
  `rotate(angle, about_point=m.ORIGIN)`, and `get_edge_center(m.UP)` is `get_top()`.
- `PGroup` is `Group`, and the singular `add_foreground_mobject` is
  `add_foreground_mobjects`.

`VGroup` and `Group` are the same class too, and `c2p` is `coords_to_point`, but both
names of these are everywhere in Manim code, so both stay. These docs use `VGroup` and
`c2p`.

## Types

Every keyword argument has a type, and so do `.animate` chains. So a type checker such as
[ty](https://docs.astral.sh/ty/) finds these mistakes before you render: a name that
ManimGX doesn't have, a keyword that a mobject or an animation doesn't take
(`m.Circle(colour=m.BLUE)`), or an argument of the wrong type. When the scene runs, most
mobjects and animations ignore a keyword they don't take, so only ty tells you about a
misspelled one. Through `.animate`, ty knows ManimGX's methods only. To animate a method of
your own class, give `.animate` a function: `box.animate(lambda b: b.grow(2))`. The
[Quickstart](quickstart.md#2-set-up-your-editor) sets up ty in your editor.

## Sound, slides and voiceover

ManimGX does the work of manim-voiceover and manim-slides, without plugins:

- [`add_sound`][manimgx.Scene.add_sound] puts a sound in the video. A
  [`Sound`][manimgx.Sound] can also be a part of a play.
- A voiceover is `self.say("The derivative of [x squared] is [two x].", anim1, anim2)`.
  Each animation plays during its words in brackets, and the scene waits until the line
  ends. This replaces `with self.voiceover(...) as tracker:`, bookmarks and
  `run_time=tracker.duration`. Any text-to-speech service can be a voice.
- [`next_section`][manimgx.Scene.next_section] starts a section of one video, not a
  separate file. `manimgx present` shows the sections as slides. Use
  `self.next_section()` instead of `self.next_slide()`, and `"presentation.loop"` instead
  of `loop=True`. `notes=` works as before.
- [`add_subcaption`][manimgx.Scene.add_subcaption] adds captions. `manimgx render` writes
  them next to the video, as subtitles.

See [Sound and voice](sound-and-voice.md) and [Rendering and sharing](rendering.md#present).
