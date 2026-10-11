# Quickstart

There are two ways to start. Choose one.

## With an AI agent

Paste this into Claude Code or Codex:

``` { .text .mx-prompt }
Follow https://manimgx.academa.ai/llms.txt to make me a short animation of a square turning into a circle, and open it.
```

That's it. The agent installs ManimGX, writes the code, makes the video and opens it. To
get a different video, change the words after "make me". If the agent asks to use the
network or the GPU, allow it.

## By hand

### 1. Install ManimGX

With [Python](https://www.python.org/downloads/) 3.13 or later, run this in a terminal:

```sh
pip install manimgx
```

It installs ManimGX and its command, `manimgx`.

### 2. Set up your editor

Set up [ty](https://docs.astral.sh/ty/) in your editor. ty checks your code as you type.
It completes ManimGX's names, shows what each one does, and underlines many of your
mistakes before you make a video.

=== "VS Code"

    Install the [ty extension](https://marketplace.visualstudio.com/items?itemName=astral-sh.ty).
    Cursor, Windsurf and the other editors made from VS Code have it in their Extensions
    view too. Then make a folder for your videos, and open it with **File > Open Folder**.

=== "Zed"

    Zed includes ty. To turn it on, open your settings file (++cmd+alt+comma++ on a Mac,
    ++ctrl+alt+comma++ on Windows and Linux), and paste these lines right after its first
    `{`:

    ```json
      "languages": {
        "Python": {
          "language_servers": ["ty", "!basedpyright", "..."]
        }
      },
    ```

    Then make a folder for your videos, and open it with **File > Open**.

### 3. Write a scene

In your folder, make a file named `scene.py`, and write this code in it:

```python title="scene.py"
import manimgx as m


class SquareToCircle(m.Scene):
    def construct(self) -> None:
        square = m.Square(side_length=3, color=m.BLUE, fill_opacity=0.5)
        circle = m.Circle(radius=1.6, color=m.PINK, fill_opacity=0.5)
        self.play(m.Create(square))
        self.play(m.Transform(square, circle))
        self.wait()
```

### 4. Preview it

Open your editor's terminal (++ctrl+grave++), and run:

```sh
manimgx preview scene.py
```

A window plays your scene. Put it next to your editor. Each time that you save
`scene.py`, the window plays the new version. Try it: change `m.PINK` to `m.YELLOW`, and
save.

### 5. Make the video

```sh
manimgx render scene.py
```

ManimGX writes the video, `SquareToCircle.mp4`, next to `scene.py`. It's the video above
the code in step 3. For a tall video (Shorts, Reels, TikTok), add `-r 1080x1920`.

You are ready. Next, [The basics](the-basics.md) explains how a scene makes a video.
