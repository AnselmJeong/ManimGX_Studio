# The basics

With ManimGX, you write a short Python program, and ManimGX makes a video of it. This
page shows how.

## A program makes a video

Here is a ManimGX program:

```python title="hello.py" show="code"
import manimgx as m


class Hello(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        self.play(m.Create(circle))
        self.wait()
```

Save it in a file named `hello.py`. Then, in a terminal, in the same folder, run this
command:

```sh
manimgx render hello.py
```

ManimGX makes this video, `Hello.mp4`, next to the file:

```python show="film"
import manimgx as m


class Hello(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        self.play(m.Create(circle))
        self.wait()
```

That is how you work with ManimGX: you write a program, and ManimGX makes a video of it.

## The program, line by line

`import manimgx as m`
:   gives you all of ManimGX under a short name, `m`: `m.Scene`, `m.Circle`, `m.Create`.

`class Hello(m.Scene):`
:   makes a **scene**. A scene is one video. Its name is the name of the video: the
    scene `Hello` makes `Hello.mp4`.

`def construct(self) -> None:`
:   tells what happens in the video. ManimGX runs `construct` from top to bottom, and
    each line adds to the video in that order.

`circle = m.Circle()`
:   makes a circle. A circle is a **mobject**: anything that you can show in a video is
    a mobject. Shapes, lines, text, formulas and graphs are mobjects. But making a mobject
    doesn't show it: at this line, the video is still empty.

`self.play(m.Create(circle))`
:   plays an **animation**: `m.Create(circle)` draws the circle, in one second. After
    that, the circle is in the video, and it stays there.

`self.wait()`
:   keeps the picture still for one second. So the video is two seconds long.

## One step after another

Each `self.play` starts when the one before it ends. Time passes only in `play` and in
`wait`:

```python
import manimgx as m


class Steps(m.Scene):
    def construct(self) -> None:
        circle = m.Circle()
        words = m.Text("Hello!")
        self.play(m.Create(circle))  # from 0 to 1 second
        self.play(m.FadeOut(circle))  # from 1 to 2 seconds
        self.play(m.Write(words))  # from 2 to 3 seconds
        self.wait(2)  # from 3 to 5 seconds
```

These animations show and hide mobjects. You will use them most:

- `m.Create(...)` draws a shape.
- `m.Write(...)` writes a text or a formula.
- `m.FadeIn(...)` fades a mobject in. `m.FadeOut(...)` fades it out, and removes it.

`self.wait(2)` waits 2 seconds. Without a number, it waits 1 second.

## Show a mobject at once

To show a mobject with no animation, add it: `self.add(circle)`. The circle is in the
video from that moment. `self.remove(circle)` removes it at once.

## Several scenes in one file

A file can have several scenes, and each one is a video. To make one of them, give its
name after the file:

```sh
manimgx render hello.py Steps
```

## Next

So far, every mobject appears in the middle of the video. [Positions](positions.md) shows
how to put each one where you want it.
