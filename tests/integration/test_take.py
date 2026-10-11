"""A film recorded as a take: the engine's work written down — each array of its shapes once,
then what changes of them, and each frame's view and records — for ManimGX's player to draw (in
its window, or in the browser). A take holds the frames a video would, and tells the player
what else it shows: the plays, each with the line that played it, its sections, its sound and
captions, and the end — or that its scene failed. Its taker may cut the film, as a frame sink
may. Where the engine has no GPU (Pyodide), every film is a take.
"""

import io
import json
import struct
import wave
from pathlib import Path

import numpy as np
import pytest

import manimgx as m
from manimgx import _engine
from manimgx.rendering import feed
from manimgx.rendering.film import Cut, Frame

START, FRAME, NOTE, SOUND, END = 14, 8, 9, 10, 12


class Held(m.Scene):
    def construct(self) -> None:
        square = m.Square()
        self.play(m.Create(square))
        self.play(square.animate.shift(m.RIGHT))
        self.wait()


pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180, frame_rate=30)


def messages(take: bytes) -> list[tuple[int, bytes]]:
    """The take's messages, in order: (op, fields). Each is its length (u32), op (u8), fields."""
    out, at = [], 0
    while at < len(take):
        (n,) = struct.unpack_from("<I", take, at)
        out.append((take[at + 4], take[at + 5 : at + 4 + n]))
        at += 4 + n
    assert at == len(take), "the take ends in the middle of a message"
    return out


def notes(take: bytes) -> list[str]:
    return [fields[4:].decode() for op, fields in messages(take) if op == NOTE]


def record(scene: m.Scene) -> tuple[bytes, int]:
    chunks: list[bytes] = []
    film = scene.render(take=chunks.append)
    return b"".join(chunks), film.frame_count


def test_a_take_holds_the_frames_a_video_would() -> None:
    sent: list[Frame] = []
    Held().render(frames=sent.append)
    take, count = record(Held())
    (op, start), *rest = messages(take)
    assert op == START
    assert struct.unpack("<IIId", start) == (_engine.TAKE_VERSION, 320, 180, 30.0)
    repeats = [
        struct.unpack_from("<I", fields)[0] for op, fields in rest if op == FRAME
    ]
    assert repeats == [frame.repeat for frame in sent]  # a hold is one frame, lasting
    assert sum(repeats) == count


def test_a_take_notes_each_play_with_its_line_and_its_end() -> None:
    take, _ = record(Held())
    plays = [json.loads(note) for note in notes(take)]
    source = Path(__file__).read_text(encoding="utf-8").splitlines()
    called = ["self.play(m.Create(square))", "self.play(square.animate.shift(m.RIGHT))"]
    lines = [source.index(f"        {call}") + 1 for call in [*called, "self.wait()"]]
    assert [p["play"]["where"] for p in plays] == [[__file__, line] for line in lines]
    assert messages(take)[-1] == (END, b"\x00")  # it ends, its scene ended


class Slides(m.Scene):
    def construct(self) -> None:
        self.next_section("Intro")
        self.play(m.Create(m.Square()))
        self.next_section("Proof", "presentation.loop", notes="Slowly.")
        self.wait(0.5)


def test_a_take_notes_each_section_where_the_film_begins_it() -> None:
    take, _ = record(Slides())
    sections = [
        json.loads(note)["section"] for note in notes(take) if '"section"' in note
    ]
    film = Slides().render()
    assert [
        (s["name"], s["start"], s["frame"], s["type"], s["notes"]) for s in sections
    ] == [(s.name, float(s.start), s.frame, s.type, s.notes) for s in film.sections]


class Said(m.Scene):
    def construct(self) -> None:
        self.add_subcaption("A tone.", duration=0.5)
        self.play(m.Sound.of(lambda t: 0.5 * np.sin(2 * np.pi * 440 * t), 0.5))
        self.wait(0.5)


def test_a_take_ends_with_the_film_s_sound_and_captions() -> None:
    take, count = record(Said())
    ((sound,),) = [(fields[4:],) for op, fields in messages(take) if op == SOUND]
    with wave.open(io.BytesIO(sound)) as wav:
        assert (wav.getsampwidth(), wav.getframerate()) == (2, 48_000)
        assert wav.getnframes() == count * 48_000 // 30  # as long as the film
        samples = np.frombuffer(wav.readframes(wav.getnframes()), "<i2")
    assert samples[:24_000].std() > 0.3 * 32767  # the tone
    assert not samples[24_000:].any()  # then nothing
    said = [json.loads(note) for note in notes(take)]
    assert {"captions": [{"start": 0.0, "end": 0.5, "text": "A tone."}]} in said
    assert messages(take)[-1][0] == END  # after them


class Rippling(m.Scene):
    """A 50x50 mesh whose points move a little every frame, its triangles never."""

    def construct(self) -> None:
        u, v = np.meshgrid(np.linspace(-3, 3, 50), np.linspace(-2, 2, 50))
        cells = np.arange(50 * 50).reshape(50, 50)[:-1, :-1].ravel()
        triangles = np.concatenate(
            [
                np.stack([cells, cells + 1, cells + 51], 1),
                np.stack([cells, cells + 51, cells + 50], 1),
            ]
        )
        grid = m.MeshMobject(
            np.stack([u.ravel(), v.ravel(), 0 * u.ravel()], 1), triangles
        )
        time = m.ValueTracker(0)

        def ripple(mesh: m.MeshMobject) -> None:
            t = time.get_value()
            mesh.points = np.stack(
                [u.ravel(), v.ravel(), 0.2 * np.sin(2 * u.ravel() + t)], 1
            )

        grid.add_updater(ripple)
        self.add(grid)
        self.play(time.animate.set_value(3), run_time=2)


def test_a_shape_that_changes_a_little_is_sent_as_its_changes() -> None:
    take, count = record(Rippling())
    points_and_uvs = count * 50 * 50 * (3 + 2) * 8  # float64s, every frame
    triangles = count * 49 * 49 * 2 * 3 * 4
    assert count >= 60
    assert (
        len(take) * 10 < points_and_uvs + triangles
    )  # its triangles once, its changes


def test_without_a_gpu_every_film_is_a_take(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feed, "Player", None)  # the engine as Pyodide has it
    take, count = record(Held())
    assert count
    assert messages(take)[0][0] == START
    assert Held().render().frame_count == count  # recorded all the same, to nowhere
    with pytest.raises(ValueError, match="no GPU"):
        Held().render(frames=lambda _: None)


def test_a_take_is_not_also_a_video(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="drawn by ManimGX's player"):
        Held().render(tmp_path / "held.mp4", take=lambda _: None)


def test_a_note_between_takes_is_a_message_of_its_own() -> None:
    ((op, fields),) = messages(_engine.note('{"scenes": ["Held"]}'))
    assert (op, fields[4:]) == (NOTE, b'{"scenes": ["Held"]}')


def test_a_take_that_cuts_the_film_is_sent_nothing_more() -> None:
    _, whole = record(Held())
    sent: list[bytes] = []

    def take(data: bytes) -> None:
        sent.append(data)
        if len(sent) == 3:
            raise Cut

    film = Held().render(take=take)
    assert len(sent) == 3  # not even how the film ends
    assert 0 < film.frame_count < whole


class Failing(m.Scene):
    def construct(self) -> None:
        self.play(m.Create(m.Square()))
        raise RuntimeError("the scene's own mistake")


def test_a_take_whose_scene_fails_ends_saying_so() -> None:
    chunks: list[bytes] = []
    scene = Failing()
    with pytest.raises(RuntimeError, match="own mistake"):
        scene.render(take=chunks.append)
    sent = messages(b"".join(chunks))
    assert sent[-1] == (END, b"\x01")  # it ends, its scene failed
    frames = sum(
        struct.unpack_from("<I", fields)[0] for op, fields in sent if op == FRAME
    )
    assert frames == scene.film.frame_count  # with every frame made, the last one too


@pytest.mark.parametrize("points_first", [False, True])
def test_a_take_keeps_same_form_path_and_cloud_as_distinct_uploads(
    points_first: bool,
) -> None:
    points = np.array(
        [[-0.5, -0.5, 0.0], [-0.5, 0.5, 0.0], [0.5, 0.5, 0.0], [0.5, -0.5, 0.0]]
    )
    path = m.VMobject(color=m.BLUE, stroke_width=8).set_points(points).shift(2 * m.LEFT)
    cloud = (
        m.PMobject(stroke_width=20).add_points(points, color=m.RED).shift(2 * m.RIGHT)
    )
    assert path._geometry.terms[0][1].affine[0] == cloud._geometry.terms[0][1].affine[0]

    class Both(m.Scene):
        def construct(self) -> None:
            self.add(*(cloud, path) if points_first else (path, cloud))

    scene = Both()
    take, count = record(scene)
    sent = messages(take)
    # Upload opcodes carry the interpretation; identifiers themselves are opaque.
    uploads = [
        (op, struct.unpack_from("<Q", fields)[0]) for op, fields in sent if op in (1, 2)
    ]
    assert [op for op, _ in uploads] == ([2, 1] if points_first else [1, 2])
    assert len({key for _, key in uploads}) == 2

    # A single closing frame draws both resources, in scene order. Its record array
    # is exactly the content the feeder handed to the recorder, independently of
    # whichever numeric identifiers the native uploads received.
    assert count == 1
    (raw_records,) = scene.film.feeder.latest
    records = np.frombuffer(raw_records, feed.RECORD)
    assert list(records["key1"]) == [key for _, key in uploads]
    assert not records["key2"].any()
    (frame,) = [fields for op, fields in sent if op == FRAME]
    repeat, view_bytes = struct.unpack_from("<II", frame)
    record_key, cameras = struct.unpack_from("<QI", frame, 8 + view_bytes)
    assert repeat == 1
    assert cameras == 0
    # Packed array kind 9 is Records. Compare content identity, never a fixed hash.
    assert record_key == _engine.digest(b"\x09", raw_records)
    arrays = {
        struct.unpack_from("<Q", fields)[0]: fields[16]
        for op, fields in sent
        if op == 11
    }
    assert arrays[record_key] == 9
