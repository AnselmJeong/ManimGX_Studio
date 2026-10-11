"""Recorded frames use the same decoder and renderer as native playback, in any order."""

import gc
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

import manimgx as m
from manimgx._engine import TAKE_VERSION, Player, Recorder, Replay, adapter_info
from manimgx.rendering.feed import Feeder


@pytest.mark.parametrize("collect", [False, True], ids=["render", "collect"])
def test_replay_ownership_can_cross_python_threads(collect: bool) -> None:
    recorder = Recorder(32, 24, 30)
    view, records, cameras = Feeder(32, 24, recorder).frame(
        m.Camera(), [m.Square(fill_opacity=1)]
    )
    recorder.frame(view, records, 1, cameras)
    recorder.end()
    replay = Replay(recorder.drain())
    expected = replay.render(0)  # Populate the decoded arrays and GPU resources.
    with ThreadPoolExecutor(max_workers=1) as pool:
        if not collect:
            assert pool.submit(replay.render, 0).result() == expected
            return
        enabled = gc.isenabled()
        gc.disable()
        try:
            # A traceback or any other Python cycle can retain a Replay until a
            # different thread triggers collection, without calling it there.
            cycle: list[object] = [replay]
            cycle.append(cycle)
            del replay, cycle
            assert pool.submit(gc.collect).result() > 0
        finally:
            if enabled:
                gc.enable()


def test_recorded_geometry_and_images_replay_exactly_in_any_order() -> None:
    adapter = adapter_info()
    assert set(adapter) == {
        "name",
        "vendor",
        "device",
        "device_type",
        "driver",
        "driver_info",
        "backend",
    }
    assert adapter["name"]
    assert adapter["backend"]
    assert int(adapter["vendor"]) >= 0
    assert int(adapter["device"]) >= 0
    width, height, fps = 130, 74, 29.97  # readback rows require padding
    player, recorder = Player(width, height), Recorder(width, height, fps)
    direct, recorded = Feeder(width, height, player), Feeder(width, height, recorder)
    camera = m.Camera(three_d=True, phi=0.4, theta=-1.2)
    path = m.VMobject(color=m.BLUE, stroke_width=8).set_points_as_corners(
        [(-3, -1, 0), (-2, 1, 0)]
    )
    mesh = m.MeshMobject(
        np.array([[-0.8, -1, 0.1], [0.9, -0.8, -0.2], [0.6, 1, 0.6], [-0.7, 0.9, 0]]),
        np.array([[0, 1, 2], [0, 2, 3]]),
        color=m.RED,
        shade_in_3d=True,
    )
    image = (
        m.ImageMobject(
            np.array(
                [
                    [[255, 0, 0, 255], [0, 255, 0, 255]],
                    [[0, 0, 255, 255], [255, 255, 0, 255]],
                ],
                dtype=np.uint8,
            )
        )
        .scale_to_fit_height(1.6)
        .shift(2 * m.RIGHT)
    )
    objects: list[m.Mobject] = [path, mesh, image]
    expected: list[bytes] = []
    for step, repeat in enumerate([3, 1, 2, 1]):
        path.add_points_as_corners([(-1.8 + step * 0.2, 0.5 - step * 0.3, 0)])
        mesh.rotate(0.1, axis=m.UP)
        expected.extend([player.render(*direct.frame(camera, objects))] * repeat)
        view, records, cameras = recorded.frame(camera, objects)
        recorder.frame(view, records, repeat, cameras)
    recorder.end()
    replay = Replay(recorder.drain())
    assert replay.size == (width, height)
    assert replay.frames == len(expected)
    assert replay.fps == fps
    assert replay.timeline == [(0, 3), (3, 1), (4, 2), (6, 1)]
    for frame in [6, 0, 4, 1, 3, 2, 5, 0, 6]:
        assert replay.render(frame) == expected[frame]
    for frame in [-1, replay.frames]:
        with pytest.raises(IndexError, match="outside"):
            replay.render(frame)
    assert adapter_info() == adapter


def test_independent_takes_own_their_resources_when_keys_overlap() -> None:
    image = m.ImageMobject(np.full((2, 2, 4), 255, np.uint8)).scale_to_fit_height(4)
    camera = m.Camera()

    def take(color: bytes) -> tuple[Replay, bytes, int]:
        player, recorder = Player(64, 36), Recorder(64, 36, 30)
        direct = Feeder(64, 36, player)
        recorded = Feeder(64, 36, recorder)
        direct_frame = direct.frame(camera, [image])
        view, records, cameras = recorded.frame(camera, [image])
        key = recorded.texture(image.pixel_array)
        assert direct.texture(image.pixel_array) == key
        # Identical keys intentionally name different pixels in independent takes. Both
        # receive ordinary native uploads; the test neither reads nor rewrites the format.
        player.add_texture(key, 2, 2, color * 4)
        recorder.add_texture(key, 2, 2, color * 4)
        recorder.frame(view, records, 1, cameras)
        recorder.end()
        return Replay(recorder.drain()), player.render(*direct_frame), key

    first, red, first_key = take(bytes([255, 0, 0, 255]))
    second, green, second_key = take(bytes([0, 255, 0, 255]))
    assert first_key == second_key
    assert red != green
    for _ in range(3):
        assert second.render(0) == green
        assert first.render(0) == red


@pytest.mark.config(pixel_width=960, pixel_height=540, frame_rate=10)
@pytest.mark.parametrize("closes", [False, True], ids=["curved", "closed-then-open"])
def test_growing_paths_keep_their_historical_picture_when_seeking(closes: bool) -> None:
    class Growing(m.Scene):
        def construct(self) -> None:
            starts = [m.LEFT + m.UP, m.LEFT + m.DOWN, 2 * m.LEFT]
            ends = [m.RIGHT, m.RIGHT + m.UP, m.RIGHT + m.DOWN]
            colors = [m.RED, m.GREEN, m.BLUE]
            dots = m.VGroup(
                *[m.Dot(point, color=color) for point, color in zip(starts, colors)]
            )
            targets = m.VGroup(
                *[m.Dot(point, color=color) for point, color in zip(ends, colors)]
            )
            self.add(dots, targets)
            for dot in dots:
                self.add(m.TracedPath(dot.get_center, stroke_color=dot.get_color()))
            self.wait()
            if closes:
                self.play(m.Rotate(dots, m.TAU), run_time=2)
                self.play(dots.animate.shift(m.RIGHT), run_time=1)
            else:
                self.play(
                    m.Transform(dots, targets, path_func=m.counterclockwise_path()),
                    run_time=2,
                )
            self.wait()

    expected: list[bytes] = []
    Growing().render(
        frames=lambda frame: expected.extend([frame.pixels()] * frame.repeat)
    )
    chunks: list[bytes] = []
    Growing().render(take=chunks.append)
    replay = Replay(b"".join(chunks))
    assert replay.frames == len(expected)
    forward = list(range(replay.frames))
    for index in [
        *reversed(forward),
        *forward,
        *np.random.default_rng(7).permutation(forward),
    ]:
        assert replay.render(int(index)) == expected[index]


def test_a_replay_rejects_incomplete_failed_and_multiple_takes() -> None:
    recorder = Recorder(32, 24, 30)
    view, records, cameras = Feeder(32, 24, recorder).frame(m.Camera(), [])
    recorder.frame(view, records, 2, cameras)
    unfinished = recorder.drain()
    recorder.end()
    complete = unfinished + recorder.drain()
    assert Replay(complete).frames == 2
    for data, message in [
        (b"", "exactly one"),
        (unfinished, "successfully"),
        (complete[:-1], "ends early"),
        (complete + complete, "exactly one"),
    ]:
        with pytest.raises(ValueError, match=message):
            Replay(data)
    failed = Recorder(32, 24, 30)
    failed.frame(view, records, 1, cameras)
    failed.end(failed=True)
    with pytest.raises(ValueError, match="successfully"):
        Replay(failed.drain())


def test_take_versions_are_explicit_and_rejected_before_playback() -> None:
    recorder = Recorder(32, 24, 30)
    start = bytearray(recorder.drain())
    assert int.from_bytes(start[5:9], "little") == TAKE_VERSION
    start[5:9] = (TAKE_VERSION + 1).to_bytes(4, "little")
    with pytest.raises(ValueError, match=f"unsupported take format {TAKE_VERSION + 1}"):
        Replay(bytes(start))
    # The old unversioned START: its length, opcode0, width, height and fps.
    with pytest.raises(ValueError, match="unversioned takes are unsupported"):
        Replay(bytes.fromhex("11000000 00 20000000 18000000 0000000000003e40"))
