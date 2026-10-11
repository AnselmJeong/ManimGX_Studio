"""Window: ManimGX's player in a window of its own, on this machine's screen, drawn by its GPU.

A window plays the takes it is sent (see [`Film`][manimgx.Film]): each frame as soon as it is
recorded, any frame again at once. A newer take — the scene run again — replaces the one shown
at the same moment, once it gets there: an edit never loses the place.

    with m.Window() as window:
        MyScene().render(take=window)
        window.wait()  # until it is closed

The window is a process of its own, which the take reaches through a pipe: it plays on while
the scene runs, and a scene's process stays free for the scene. It closes when it is closed, or
when the process that opened it closes it, or ends.
"""

import contextlib
import json
import queue
import subprocess
import sys
import threading
from collections.abc import Sequence
from types import TracebackType
from typing import Self
from warnings import deprecated

from manimgx import _engine
from manimgx.rendering.film import Cut


class Window:
    """ManimGX's player in a window on this machine's screen, which plays the takes it is sent.

    A window is a [`Take`][manimgx.rendering.film.Take]: hand it to
    [`Scene.render`][manimgx.Scene.render] as `take`, and it plays the film as it is recorded.
    Once it is closed, a film sent to it is cut (see [`Cut`][manimgx.rendering.film.Cut]).

    Its viewer can ask for another of the file's scenes (N and P).

    Args:
        title: The window's title.
        time: Where its playhead starts, in seconds.
    """

    def __init__(self, title: str = "ManimGX", *, time: float = 0.0) -> None:
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from manimgx.rendering.window import _main; _main()",
            ]
            + [title, repr(float(time))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._asked: queue.Queue[str] = queue.Queue()
        self.failure: str | None = None
        """Why the window failed, if it did (no screen to open on, no GPU): it is closed."""
        self._listening = threading.Thread(target=self._listen, daemon=True)
        self._listening.start()

    def __call__(self, data: bytes) -> None:
        """Send the window the take's next bytes.

        Raises:
            Cut: The window is closed: the film is cut there.
        """
        pipe = self._process.stdin
        if pipe is None or pipe.closed:
            raise Cut
        try:
            pipe.write(data)  # whole: a buffered pipe writes it all
            pipe.flush()
        except (BrokenPipeError, ValueError):
            with contextlib.suppress(OSError):
                pipe.close()
            raise Cut from None

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def scenes(self, names: Sequence[str], playing: str) -> None:
        """Tell the window the file's scenes, and the one it plays: its viewer can ask for
        the others (N, P; see [`asked`][manimgx.Window.asked]).

        Args:
            names: The file's scenes, in order.
            playing: The one its takes are of now.
        """
        self._say({"scenes": list(names), "scene": playing})

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def failed(self, error: BaseException, trace: str, line: int | None = None) -> None:
        """Show the scene's error over the last picture it made, until the next take.

        Args:
            trace: What to show: the lines of the scene's code it went through, and the error.
            line: The line of the scene's file it failed at, if any.
        """
        fault = {"message": str(error), "type": type(error).__name__}
        self._say({"error": {**fault, "trace": trace, "line": line}})

    def _say(self, note: dict[str, object]) -> None:
        """A note between takes (the director's JSON, see `Film`): nothing, to a closed
        window."""
        with contextlib.suppress(Cut):
            self(_engine.note(json.dumps(note)))

    @property
    def open(self) -> bool:
        """Whether the window is open: until its viewer closes it, or it is closed."""
        return self._process.poll() is None

    @deprecated("ManimGX's machinery: ManimGX preview calls it", category=None)
    def asked(self) -> str | None:
        """The scene the viewer asked for last, if they asked since (N, P: the next or the
        previous of the file's scenes)."""
        name = None
        while not self._asked.empty():
            name = self._asked.get_nowait()
        return name

    def wait(self, timeout: float | None = None) -> bool:
        """Wait until the window is closed, at most `timeout` seconds; whether it was."""
        try:
            self._process.wait(timeout)
        except subprocess.TimeoutExpired:
            return False
        self._listening.join()  # what it said before it closed, `failure` among it
        return True

    def close(self) -> None:
        """Close the window."""
        pipe = self._process.stdin
        if pipe is not None and not pipe.closed:
            with contextlib.suppress(OSError):
                pipe.close()  # its end of the take: it closes
        if not self.wait(10):
            self._process.kill()
            self.wait()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.close()

    def _listen(self) -> None:
        """What the window says, a line of JSON each, as it comes: a scene its viewer asks
        for, or why it failed; its end of the pipe closed once it has said all."""
        assert self._process.stdout is not None
        with self._process.stdout as lines:
            for line in lines:
                try:
                    said = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(said, dict):
                    continue
                if isinstance(scene := said.get("scene"), str):
                    self._asked.put(scene)
                if isinstance(failure := said.get("failure"), str):
                    self.failure = failure


def _main() -> None:
    """The window's own process (`Window` starts it): the window, until it is closed."""
    import signal

    from manimgx.drawing.typesetting import FONTS

    # Ctrl+C reaches every process of the terminal: the window's director closes it
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    title, time = sys.argv[1], float(sys.argv[2])
    try:
        _engine.window(title, time, list(FONTS))
    except BaseException as failed:  # a panic of the engine's too
        print(json.dumps({"failure": str(failed) or type(failed).__name__}), flush=True)
        sys.exit(1)
