"""The engine in a process: the GPU comes up only in a process that will draw, on a thread of
its own, started as early as the process knows it will (a film that draws, the command line's
drawing commands), so that the first frame need not wait for it; a process that never draws
never brings it up. One that exits before the GPU is up waits for it, rather than unload a
driver while it starts (lavapipe crashed a process that did)."""

import subprocess
import sys
from pathlib import Path

from manimgx import _engine

SCENE = """
import manimgx as m


class Square(m.Scene):
    def construct(self):
        self.play(m.Create(m.Square()))
"""


def run(code: str, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    """`code` run by a fresh Python."""
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, check=False, cwd=cwd
    )


def assert_ran(done: subprocess.CompletedProcess[bytes]) -> None:
    assert done.returncode == 0, done.stderr.decode(errors="replace")


def test_importing_manimgx_does_not_start_the_gpu() -> None:
    # start_gpu says whether it began the GPU: nothing had
    assert_ran(
        run("import manimgx\nfrom manimgx import _engine\nassert _engine.start_gpu()")
    )


def test_a_film_that_only_counts_or_records_its_frames_does_not_start_the_gpu() -> None:
    code = f"""{SCENE}
from manimgx import _engine

Square().render()  # its frames counted
Square().render(take=lambda data: None)  # recorded, for the player to draw
assert _engine.start_gpu()
"""
    assert_ran(run(code))


def test_a_film_that_draws_starts_the_gpu_as_it_begins() -> None:
    code = """
from manimgx import _engine
from manimgx.rendering.film import Film

Film(frames=lambda frame: None)
assert not _engine.start_gpu()
"""
    assert_ran(run(code))


def test_the_command_line_starts_the_gpu_for_a_command_that_draws(
    tmp_path: Path,
) -> None:
    # the scene's file checks, as the command loads it, that the GPU has been started
    (tmp_path / "scene.py").write_text(
        "from manimgx import _engine\n\nassert not _engine.start_gpu()\n" + SCENE,
        encoding="utf-8",
    )
    command = (
        "from manimgx.cli import main\ntry:\n    main()\nexcept SystemExit as e:\n"
    )
    drawn = run(
        "import sys\nsys.argv = ['manimgx', 'inspect', 'scene.py']\n"
        + command
        + "    assert not e.code, e.code",
        cwd=tmp_path,
    )
    assert_ran(drawn)
    shown = run(
        "import sys\nsys.argv = ['manimgx', '--version']\n"
        + command
        + "    pass\nfrom manimgx import _engine\nassert _engine.start_gpu()"
    )
    assert_ran(shown)


def test_the_commands_that_draw_are_every_command_but_preview() -> None:
    from manimgx.cli import DRAWING, app

    commands = {
        c.name or getattr(c.callback, "__name__", "") for c in app.registered_commands
    }
    assert set(DRAWING) == commands - {"preview"}  # its window draws its takes


def test_a_process_that_starts_the_gpu_and_exits_at_once_exits_cleanly() -> None:
    # the engine alone, loaded from its file (the package's imports would give the GPU a head
    # start), the GPU started, and the process ended at once: Python waits for it as it exits
    code = f"""
import atexit, importlib.util
waiting = atexit._ncallbacks()
spec = importlib.util.spec_from_file_location("manimgx._engine", {_engine.__file__!r})
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
assert atexit._ncallbacks() == waiting + 1, "nothing waits for the GPU at exit"
assert engine.start_gpu()
"""
    for _ in range(5):
        assert_ran(run(code))
