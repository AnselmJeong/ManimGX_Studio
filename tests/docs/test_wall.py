"""Shared GIF previews: correct compositing, bounded files and evenly timed playback."""

import re
from pathlib import Path

import pytest
from PIL import Image
from PIL.GifImagePlugin import GifImageFile
from scripts.showcase import wall

README = Path(__file__).parents[2] / "README.md"


def test_every_clip_s_box_lies_in_its_film() -> None:
    for clip in wall.CLIPS:
        left, top, right, bottom = clip.box
        assert 0 <= left < right <= wall.FILM[0], clip.name
        assert 0 <= top < bottom <= wall.FILM[1], clip.name
        assert abs((right - left) * 9 / 16 - (bottom - top)) < 1, clip.name


def test_a_box_that_leaves_its_film_is_refused() -> None:
    with pytest.raises(ValueError, match="leaves the film"):
        _ = wall.Clip("too-wide", 0, 1000, 0, 1000).box


def test_compositing_preserves_opaque_and_partially_transparent_colors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wall, "TILE", (3, 1))
    crop = Image.frombytes(
        "RGBa", (3, 1), bytes([0, 0, 0, 0, 64, 32, 16, 128, 12, 34, 56, 255])
    )
    shown = wall.composite(crop)
    assert shown.mode == "RGB"
    assert shown.tobytes() == bytes([13, 17, 23, 70, 40, 27, 12, 34, 56])


def test_resize_filters_premultiplied_pixels_before_compositing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wall, "TILE", (1, 1))
    crop = Image.frombytes("RGBa", (2, 1), bytes([255, 0, 0, 255, 0, 0, 0, 0]))
    assert wall.composite(crop).tobytes() == bytes([134, 8, 11])
    with pytest.raises(ValueError, match="premultiplied"):
        wall.composite(crop.convert("RGBA"))


@pytest.mark.parametrize("clip", wall.CLIPS, ids=lambda clip: clip.name)
def test_committed_gif_has_even_timing_and_stays_below_budget(clip: wall.Clip) -> None:
    path = wall.SHOWCASE / wall.name(clip)
    wall.validate(path)
    with Image.open(path) as image:
        assert isinstance(image, GifImageFile)
        assert image.info["loop"] == 0
        total = 0
        for index in range(image.n_frames):
            image.seek(index)
            image.load()
            duration = image.info["duration"]
            assert duration > 0
            assert duration % 20 == 0
            total += duration
            assert image.convert("RGBA").getchannel("A").getextrema() == (255, 255)
        assert total == 5000


def test_the_complete_committed_wall_stays_below_budget() -> None:
    wall.validate_set([wall.SHOWCASE / wall.name(clip) for clip in wall.CLIPS])


def save_gif(
    images: list[Image.Image], path: Path, duration: int = 20, loop: int = 0
) -> None:
    """Small independent fixtures exercise validation without the production encoder."""
    images[0].save(
        path,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=loop,
        disposal=2,
        optimize=False,
    )


@pytest.mark.parametrize(
    ("size", "frame_count", "duration", "transparent", "loop", "message"),
    [
        ((3, 2), 50, 20, False, 0, "must be a"),
        ((2, 2), 1, 1000, False, 0, "must remain animated"),
        ((2, 2), 49, 20, False, 0, "must last exactly 1000 ms"),
        ((2, 2), 50, 40, False, 0, "must last exactly 1000 ms"),
        ((2, 2), 50, 30, False, 0, "positive multiple of 20 ms"),
        ((2, 2), 50, 0, False, 0, "positive multiple of 20 ms"),
        ((2, 2), 50, 20, True, 0, "must be opaque"),
        ((2, 2), 50, 20, False, 1, "must loop forever"),
    ],
)
def test_validation_rejects_changed_playback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    size: tuple[int, int],
    frame_count: int,
    duration: int,
    transparent: bool,
    loop: int,
    message: str,
) -> None:
    monkeypatch.setattr(wall, "TILE", (2, 2))
    monkeypatch.setattr(wall, "SECONDS", 1)
    images = [
        Image.new("RGBA", size, (index, 50, 100, 255)) for index in range(frame_count)
    ]
    if transparent:
        for image in images:
            image.putpixel((0, 0), (0, 0, 0, 0))
    path = tmp_path / "invalid.gif"
    save_gif(images, path, duration, loop)
    with pytest.raises(ValueError, match=message):
        wall.validate(path)


def test_validation_rejects_a_truncated_gif(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wall, "TILE", (2, 2))
    monkeypatch.setattr(wall, "SECONDS", 1)
    images = [Image.new("RGB", (2, 2), (index, 50, 100)) for index in range(50)]
    path = tmp_path / "truncated.gif"
    save_gif(images, path)
    wall.validate(path)
    data = path.read_bytes()
    path.write_bytes(data[: len(data) // 2])
    with pytest.raises((ValueError, OSError, EOFError)):
        wall.validate(path)


def test_validation_accepts_combined_identical_frame_holds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wall, "TILE", (2, 2))
    monkeypatch.setattr(wall, "SECONDS", 1)
    images = [Image.new("RGB", (2, 2), (index, 50, 100)) for index in range(25)]
    path = tmp_path / "combined.gif"
    save_gif(images, path, duration=40)
    wall.validate(path)


def test_gifski_combines_holds_without_moving_color_transitions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gifski = wall.shutil.which("gifski")
    if gifski is None:
        pytest.skip("Gifski is needed only to regenerate the previews")
    monkeypatch.setattr(wall, "TILE", (2, 2))
    monkeypatch.setattr(wall, "SECONDS", 1)
    colors = [(17, 34, 51)] * 10 + [(230, 160, 90)] * 40
    images = [Image.new("RGB", (2, 2), color) for color in colors]
    path = tmp_path / "encoded.gif"
    wall.encode(images, path, gifski)
    wall.validate(path)
    with Image.open(path) as image:
        assert isinstance(image, GifImageFile)
        assert image.n_frames < len(images)
        timeline = []
        for index in range(image.n_frames):
            image.seek(index)
            image.load()
            color = image.convert("RGB").getpixel((0, 0))
            timeline.extend([color] * (image.info["duration"] // 20))
        assert timeline == colors
    assert list(tmp_path.iterdir()) == [path]


def test_encode_requires_the_complete_source_timeline_before_starting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wall, "SECONDS", 1)
    path = tmp_path / "incomplete.gif"
    with pytest.raises(ValueError, match="must encode 50 source frames"):
        wall.encode([Image.new("RGB", (2, 2))] * 49, path, "unused-encoder")
    assert not list(tmp_path.iterdir())


def test_the_per_file_budget_is_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "too-large.gif"
    path.write_bytes(b"1234")
    monkeypatch.setattr(wall, "MAX_BYTES", 4)
    with pytest.raises(ValueError, match="must be below 4 bytes"):
        wall.validate(path)


def test_the_combined_budget_is_checked_before_replacing_any_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wall, "SHOWCASE", tmp_path)
    monkeypatch.setattr(wall, "TILE", (2, 2))
    monkeypatch.setattr(wall, "SECONDS", 1)
    monkeypatch.setattr(wall, "CLIPS", wall.CLIPS[:2])
    images = [Image.new("RGB", (2, 2), (index, 50, 100)) for index in range(50)]
    monkeypatch.setattr(wall, "frames", lambda _clip: images)
    monkeypatch.setattr(wall.shutil, "which", lambda _name: "unused-encoder")
    monkeypatch.setattr(
        wall, "encode", lambda tiles, path, _gifski: save_gif(tiles, path)
    )
    reference = tmp_path / "reference.gif"
    save_gif(images, reference)
    wall.validate(reference)
    monkeypatch.setattr(wall, "MAX_TOTAL_BYTES", reference.stat().st_size * 2)
    reference.unlink()
    paths = [tmp_path / wall.name(clip) for clip in wall.CLIPS]
    for path in paths:
        path.write_bytes(b"previous asset")
    with pytest.raises(ValueError, match="the complete wall must be below"):
        wall.main()  # Individually valid images, whose sum equals the strict limit.
    assert all(path.read_bytes() == b"previous asset" for path in paths)
    assert set(tmp_path.iterdir()) == set(paths)


def test_a_failed_later_encode_does_not_publish_an_earlier_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wall, "SHOWCASE", tmp_path)
    monkeypatch.setattr(wall, "CLIPS", wall.CLIPS[:2])
    monkeypatch.setattr(wall, "frames", lambda _clip: [])
    monkeypatch.setattr(wall.shutil, "which", lambda _name: "unused-encoder")
    paths = [tmp_path / wall.name(clip) for clip in wall.CLIPS]
    for path in paths:
        path.write_bytes(b"previous asset")

    def fail_later(_tiles: list[Image.Image], path: Path, _gifski: str) -> None:
        if path.name == paths[-1].name:
            raise RuntimeError("encoder failed")
        path.write_bytes(b"new asset")

    monkeypatch.setattr(wall, "encode", fail_later)
    with pytest.raises(RuntimeError, match="encoder failed"):
        wall.main()
    assert all(path.read_bytes() == b"previous asset" for path in paths)
    assert set(tmp_path.iterdir()) == set(paths)


def test_missing_gifski_is_reported_before_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wall.shutil, "which", lambda _name: None)
    monkeypatch.setattr(wall, "SHOWCASE", tmp_path / "not-created")
    with pytest.raises(RuntimeError, match="Install Gifski and put gifski on PATH"):
        wall.main()
    assert not wall.SHOWCASE.exists()


def test_the_readme_shows_every_film_linked_to_its_file() -> None:
    readme = README.read_text(encoding="utf-8")
    for clip in wall.CLIPS:
        assert (
            "https://raw.githubusercontent.com/academa-labs/manimgx/main/"
            f"docs/content/showcase/{wall.name(clip)}"
        ) in readme
        assert f"/blob/main/examples/{clip.name}.py" in readme


def test_the_readme_shows_nine_films_in_three_equal_rows() -> None:
    names = [
        "quadratic_formula",
        "fourier_pi",
        "linear_maps",
        "derivative",
        "complex_maps",
        "lorenz_attractor",
        "heavy_top",
        "hopf_fibration",
        "catenoid_helicoid",
    ]
    assert [clip.name for clip in wall.CLIPS] == names
    heavy_top = next(clip for clip in wall.CLIPS if clip.name == "heavy_top")
    assert heavy_top.start == 24
    assert heavy_top.box == (0, 0, *wall.FILM)
    assert wall.scene("heavy_top").__name__ == "HeavyTop"
    readme = README.read_text(encoding="utf-8")
    first = readme.index("/examples/quadratic_formula.py")
    start = readme.rfind('<p align="center">', 0, first)
    end = readme.index("</p>", first)
    assert start >= 0
    rows = [
        re.findall(r'/showcase/([^"/]+\.gif)" width="([^"]+)"', row)
        for row in readme[start:end].split("<br>")
    ]
    assert rows == [
        [(f"{name}.gif", "32%") for name in names[:3]],
        [(f"{name}.gif", "32%") for name in names[3:6]],
        [(f"{name}.gif", "32%") for name in names[6:9]],
    ]


@pytest.mark.parametrize("name", ["hopf_fibration", "catenoid_helicoid"])
def test_the_added_examples_are_three_dimensional_scenes(name: str) -> None:
    assert issubclass(wall.scene(name), wall.m.ThreeDScene)
