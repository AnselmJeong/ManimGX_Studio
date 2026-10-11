"""The shared banner continuously interpolates vector geometry, then rests at its logo."""

import re
import xml.etree.ElementTree as ET
from itertools import pairwise

import numpy as np
import pytest
from scripts.showcase import logo

SVG = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize("ground", logo.INK)
def test_committed_logos_are_reproducible_and_the_header_stays_static(
    ground: str,
) -> None:
    assert logo.logo(ground, width=900) == (
        logo.CONTENT / "showcase" / f"logo-{ground}.svg"
    ).read_text(encoding="utf-8")
    still = logo.logo(ground, height=logo.HEADER, opening=False)
    assert still == (logo.CONTENT / "images" / f"logo-{ground}.svg").read_text(
        encoding="utf-8"
    )
    assert not ET.fromstring(still).findall(f".//{SVG}animate")


def test_favicon_is_unchanged() -> None:
    assert logo.favicon() == (logo.CONTENT / "images" / "favicon.svg").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("ground", logo.INK)
def test_the_byline_and_word_have_the_same_typeset_baseline(ground: str) -> None:
    byline = logo.byline(ground)
    assert byline == (logo.CONTENT / "images" / f"byline-{ground}.svg").read_text(
        encoding="utf-8"
    )
    word = ET.fromstring(logo.logo(ground, height=logo.HEADER, opening=False))
    parts, height, _ = logo.word()
    run = [s * logo.BYLINE * height for g in logo.glyphs(logo.BY)[:2] for s in g]

    def baseline(svg: ET.Element, outline: logo.Outline) -> float:
        # Recover the baseline from the serialized glyph coordinates: SVG y = b - scale*y.
        # This checks the actual artwork, including its crop, not just matching image sizes.
        path = svg.find(f"{SVG}path")
        assert path is not None
        points = np.array(re.findall(r"-?\d+(?:\.\d+)?", path.attrib["d"]), float)
        drawn = points.reshape(-1, 2)[:, 1]
        glyph = np.concatenate(
            [np.vstack([s[0, :1], s[:, 1:].reshape(-1, 2)]) for s in outline]
        )[:, 1]
        scale, intercept = np.linalg.lstsq(
            np.column_stack([-glyph, np.ones_like(glyph)]), drawn, rcond=None
        )[0]
        assert scale > 0
        assert np.max(np.abs(drawn - (intercept - scale * glyph))) < 0.06
        top = float(svg.attrib["viewBox"].split()[1])
        return float(intercept - top)

    assert baseline(ET.fromstring(byline), run) == pytest.approx(
        baseline(word, parts[0]), abs=0.1
    )


def test_faces_enter_when_they_turn_toward_the_camera() -> None:
    scene = logo.scene()
    for solid in (scene.cube, scene.tetrahedron):
        turn = logo.turn_keys(solid, scene.camera)
        for progress in np.linspace(0, 1, 601):
            frame = logo.turn_frame(solid, scene.camera, float(progress))
            seen = {i for i, face in enumerate(frame) if face.facing > 1e-9}
            displayed = {i for i in turn.visible if progress >= turn.onsets.get(i, 0)}
            assert seen == displayed
        for index, onset in turn.onsets.items():
            assert onset in turn.times
            assert logo.turn_frame(solid, scene.camera, onset - 1e-6)[index].facing < 0
            assert logo.turn_frame(solid, scene.camera, onset + 1e-6)[index].facing > 0


def test_serialized_path_interpolation_stays_within_one_svg_pixel() -> None:
    """Compare the actual, rounded SVG key coordinates against exact 3D projections."""
    root = ET.fromstring(logo.logo("light", width=900))
    faces = [
        p
        for p in root.iter(f"{SVG}path")
        if p.find(f"{SVG}animate[@attributeName='d']") is not None
    ]
    assert len(faces) == 5  # one persistent path for each visible cube/pyramid face
    scene = logo.scene()
    parts, height, _ = logo.word()
    canvas = logo.Canvas(logo.box(parts, height, scene), width=900)
    bx0, _, _, by1 = scene.bounds()
    left, scale, bottom = logo.beside(parts, height, scene)
    cursor = 0
    for solid, begin in ((scene.cube, 2.95), (scene.tetrahedron, 3.45)):
        turn = logo.turn_keys(solid, scene.camera)
        for face in turn.visible:
            path = faces[cursor]
            track = path.find(f"{SVG}animate[@attributeName='d']")
            assert track is not None
            cursor += 1
            times = [float(t) for t in track.attrib["keyTimes"].split(";")]
            values = track.attrib["values"].split(";")
            initial = path.find(f"{SVG}set[@attributeName='d']")
            assert initial is not None
            assert initial.attrib["to"] == values[0]
            assert initial.attrib["begin"] == "0s"
            assert initial.attrib["dur"] == track.attrib["begin"] == f"{begin}s"
            visibility = path.find(f"{SVG}set[@attributeName='visibility']")
            if face in turn.onsets:
                assert visibility is not None
                assert visibility.attrib["to"] == "hidden"
                assert visibility.attrib["begin"] == "0s"
                assert float(
                    visibility.attrib["dur"].removesuffix("s")
                ) == pytest.approx(
                    begin + logo.TURN_SECONDS * turn.onsets[face], abs=5e-7
                )
            else:
                assert visibility is None
            commands = [re.findall("[MLZ]", value) for value in values]
            assert all(command == commands[0] for command in commands)
            points = [
                np.array(
                    [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", value)]
                ).reshape(-1, 2)
                for value in values
            ]
            for progress in np.linspace(0, 1, 301):
                i = min(
                    max(int(np.searchsorted(times, progress)) - 1, 0), len(times) - 2
                )
                alpha = (progress - times[i]) / (times[i + 1] - times[i])
                interpolated = points[i] * (1 - alpha) + points[i + 1] * alpha
                exact = logo.turn_frame(solid, scene.camera, float(progress))[
                    face
                ].points
                placed = np.column_stack(
                    [
                        left + (exact[:, 0] - bx0) * scale,
                        bottom + (by1 - exact[:, 1]) * scale,
                    ]
                )
                assert (
                    np.linalg.norm(interpolated - canvas.xy(placed), axis=1).max()
                    < 0.65
                )


@pytest.mark.parametrize("ground", logo.INK)
def test_fallbacks_show_the_final_art_and_every_timeline_finishes(ground: str) -> None:
    root = ET.fromstring(logo.logo(ground, width=900))
    motion = root.find(f"{SVG}g[@class='logo-motion']")
    still = root.find(f"{SVG}g[@class='logo-still']")
    assert motion is not None
    assert still is not None
    style = root.find(f"{SVG}style")
    assert style is not None
    assert style.text is not None
    assert ".logo-still{display:none}" in style.text
    assert "@media(prefers-reduced-motion:reduce)" in style.text
    assert ".logo-motion{display:none}.logo-still{display:inline}" in style.text
    expected = ET.fromstring(logo.logo(ground, width=900, opening=False))
    assert [ET.tostring(e) for e in still] == [ET.tostring(e) for e in expected]

    # A reader without SMIL sees the same filled word and projected faces, in the same
    # painter's order. The drawing strokes' base stroke-opacity is zero.
    def filled_paths(group: ET.Element) -> list[tuple[str, str]]:
        return [
            (p.attrib["d"], p.attrib.get("color", p.attrib["fill"]))
            for p in group.findall(f".//{SVG}path[@fill]")
        ]

    assert filled_paths(motion) == filled_paths(still)
    for group in motion.findall(f".//{SVG}g[@stroke-dasharray]"):
        assert group.attrib["stroke-opacity"] == "0"
    # Three word parts, the two silhouettes and the circle share six stroke tracks,
    # independent of the number of contours and holes in the letters.
    assert (
        len(motion.findall(f".//{SVG}animate[@attributeName='stroke-dashoffset']")) == 6
    )
    for parent in root.iter():
        for track in parent:
            if track.tag not in (f"{SVG}animate", f"{SVG}set"):
                continue
            assert "repeatCount" not in track.attrib
            assert "repeatDur" not in track.attrib
            begin = float(track.get("begin", "0s").removesuffix("s"))
            duration = float(track.attrib["dur"].removesuffix("s"))
            assert 0 <= begin < begin + duration <= logo.SECONDS
            if track.tag == f"{SVG}animate":
                assert track.attrib["fill"] == "freeze"
                times = [float(t) for t in track.attrib["keyTimes"].split(";")]
                values = track.attrib["values"].split(";")
                assert len(times) == len(values)
                assert times[0] == 0
                assert times[-1] == 1
                assert all(a < b for a, b in pairwise(times))
                attribute = track.attrib["attributeName"]
                assert values[-1] == parent.get(attribute, "1")
                assert track.attrib["calcMode"] in ("linear", "spline")


def test_banner_is_self_contained_vector_art() -> None:
    root = ET.fromstring(logo.logo("dark", width=900))
    tags = {e.tag.removeprefix(SVG) for e in root.iter()}
    assert tags == {
        "svg",
        "style",
        "g",
        "path",
        "animate",
        "set",
        "defs",
        "radialGradient",
        "stop",
        "circle",
    }
    ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
    assert len(ids) == len(set(ids))
    for element in root.iter():
        for name, value in element.attrib.items():
            assert "href" not in name
            for target in re.findall(r"url\((.*?)\)", value):
                assert target.startswith("#")
                assert target[1:] in ids
