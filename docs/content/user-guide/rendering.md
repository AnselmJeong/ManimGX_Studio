# Rendering and sharing

The `manimgx` command makes the video of a scene. It also plays the scene in a window,
checks it for problems, and presents it as slides:

| Command | What it does |
| --- | --- |
| `manimgx render scene.py` | Makes the video, an MP4 file. |
| `manimgx preview scene.py` | Plays the scene in a window, and plays it again each time that you save. |
| `manimgx inspect scene.py` | Writes a storyboard, lists the timeline, and checks 2D layouts. |
| `manimgx present scene.py` | Makes the video, and shows it as slides in your browser. |

Each command writes its files next to the scene's file. If the file has several scenes,
give the scene's name after the file: `manimgx render scene.py Intro`. The
[command line reference](../reference/rendering/command-line.md) shows all the options.

## Render

```console
$ manimgx render square_to_circle.py
SquareToCircle.mp4  3.00 s, 1920x1080 at 60 fps, 0.4 MB (rendered in 0.7 s)
storyboard: SquareToCircle.storyboard.png
layout: no problems in 3 samples
```

The video is named after the scene. It is 1920 × 1080 pixels, at 60 frames each second,
with the scene's sound. `-o` gives it a different name. For a quick draft, make it
smaller: `-r 1280x720 --fps 30`.

`render` also writes a storyboard, with the picture at the end of each play that
changes it, and the captions of a voice, as subtitles (`.srt`).

### Settings

Set the video's settings on `m.config`, after the import: its size in pixels,
`pixel_width` and `pixel_height`; its `frame_rate`; and its `background_color`:

```python
import manimgx as m

m.config.background_color = m.WHITE


class OnWhite(m.Scene):
    def construct(self) -> None:
        circle = m.Circle(radius=2, color=m.BLUE, fill_opacity=0.5)
        label = m.Text("On white", color=m.BLACK)
        label.next_to(circle, m.DOWN)
        self.play(m.Create(circle), m.Write(label))
```

On the command line, `-r` and `--fps` set the size and the frame rate over the file's.

### Tall videos

For Shorts, Reels and TikTok, make the video tall: 1080 × 1920. Give the size to the
command:

```sh
manimgx render scene.py -r 1080x1920
```

Or, to make every video of the file tall, put this line after `import manimgx as m`:

```py
m.config.pixel_width, m.config.pixel_height = 1080, 1920
```

A tall frame is 8 units wide and about 14.2 units high: the wide frame, turned. Both have
the same square of 8 by 8 units in their middle, so a scene that stays in that square is
the same in both. [Positions](positions.md#the-frame) shows the two frames. A square
video, `-r 1080x1080`, is that square alone.

### From Python

A scene can make its own video: `SquareToCircle().render("square_to_circle.mp4")`
returns its [`Film`][manimgx.Film] and writes the video. Without a path, it runs the
scene quickly, without drawing it, for example in a test.

## Preview

`manimgx preview scene.py` plays the scene in a window. Each time that you save the file,
the window plays the new version, from the same moment. If the new version has an error,
the window shows the error.

The window's keys are a video player's: Space plays and pauses, ← and → go back and
forward 5 seconds, and ? shows all the keys. Its timeline shows each play of the scene,
named by its line of code, or each section, if the scene has sections.

## Inspect

`manimgx inspect scene.py` writes a storyboard and lists each play with its time and
line of code. It runs the scene without encoding video and draws only the pictures it
inspects: by default, the end of each play or wait. In 2D scenes it checks for:

- a mobject that the frame cuts off;
- texts that cover each other, a line through a text, or a fill over it;
- text too small to read.

```console
$ manimgx inspect crowded.py
crowded.py: Crowded, 3.00 s, 2 plays
storyboard: Crowded.storyboard.png
  #0   0.00– 2.00s  crowded.py:8  Write(Text 'A title much too long for t…')
  #1   2.00– 3.00s  crowded.py:9  FadeIn(Text 'a note')
layout: 2 problems
  [1] t=2–3s (crowded.py:8)  title (Text 'A title much too long for the…'): 1.35 past the left edge, 1.35 past the right edge
  [2] t=3s (crowded.py:9)  title (Text 'A title much too long for the…') and note (Text 'a note'): texts overlap
```

Each problem names the mobjects as your code names them, such as `title`. The
storyboard outlines and numbers each problem in red. Layout problems give exit code 1;
notes, such as a graph continuing off screen, do not. 3D scenes get the pictures and
timeline, with layout checks marked as skipped.

To inspect specific moments, including during an animation:

```sh
manimgx inspect scene.py -t 1.5,8,end
```

Each time selects the frame a video player shows then; `end` selects the last frame.
The same layout checks apply to those pictures. Repeat `-t` or separate times with
commas. Without `end`, the scene stops after the play containing the last requested
frame, which keeps inspection focused even in a long video.

Pictures go in chronological order to `<Scene>.storyboard.png`, six per sheet, then
`<Scene>.storyboard-2.png`, and so on. Use `-o detail.png` to choose the name. Default
inspection leaves out consecutive identical pictures; explicit times keep every
requested picture. Checks cover the sampled moments, not every frame of the video.

## Present

A video can be a talk: it plays to the end of a slide, and waits until you continue.
`self.next_section()` starts a new slide:

```python
import manimgx as m
import numpy as np


def two_sines(x: float) -> float:
    return np.sin(x) + np.sin(3 * x) / 3


class Talk(m.Scene):
    def construct(self) -> None:
        title = m.Text("Fourier series", font_size=72)
        self.play(m.Write(title))
        self.next_section("a sine", notes="Start with one sine.")
        self.play(title.animate.to_edge(m.UP))
        wave = m.FunctionGraph(np.sin, x_range=[-6, 6], color=m.BLUE)
        self.play(m.Create(wave))
        self.next_section("a sum")
        total = m.FunctionGraph(two_sines, x_range=[-6, 6], color=m.YELLOW)
        self.play(m.Transform(wave, total))
```

`manimgx present talk.py` makes the video, writes a web page next to it, and opens the
page in your browser. → or a click goes to the next slide, ← goes back, F shows the full
screen, and Shift+P opens the presenter view, with your notes, the next slide and a
timer. To share the talk,
send the page and the video together. `--pdf` also writes a handout, with a page for each
slide.

## Embed in a web page

ManimGX runs in a web page, with no server: the page makes the video from your scene,
and plays it. Install the npm package `manimgx`, import it in your page's script
through your bundler, and put a scene in a `<manimgx-player>`:

```html
<script type="module">
  import "manimgx";
</script>

<manimgx-player autoplay>
  <script type="text/python">
    import manimgx as m

    class Euler(m.Scene):
        def construct(self):
            circle = m.Circle(color=m.BLUE, fill_opacity=0.5)
            formula = m.MathTex(r"e^{i\pi} + 1 = 0").next_to(circle, m.DOWN)
            self.play(m.Create(circle), m.Write(formula))
  </script>
</manimgx-player>
```

The player has the keys of the preview window. The first video on a page downloads
Python ([Pyodide](https://pyodide.org)) and ManimGX, about 26 MB; the browser keeps them
for later. It needs WebGPU: Chrome and Edge 113 or later, or Safari 26. Two things don't
work in the browser yet: shapes made from other shapes, such as `Union`, and Chinese,
Japanese and Korean text.
