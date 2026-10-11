"""A film presented: each section begins on a keyframe of its video, so a player stops and starts
there exactly; the page holds the film's sections and captions; `manimgx present` writes the
video, the page and a handout of the pictures the slides end on.
"""

import json
from html.parser import HTMLParser
from pathlib import Path

import av
import pytest
from typer.testing import CliRunner

import manimgx as m
from manimgx.cli import app
from manimgx.cli.export import page

TALK = """
import manimgx as m


class Talk(m.Scene):
    def construct(self) -> None:
        self.play(m.Write(m.Text("Title")))
        self.next_section("points", notes="Say hello")
        self.play(m.FadeIn(m.Dot()), run_time=0.55)
        self.next_section("gear", "presentation.loop")
        self.play(m.Rotate(m.Square(), m.PI / 2))
"""


pytestmark = pytest.mark.config(pixel_width=320, pixel_height=180, frame_rate=10)


def keyframes(path: Path) -> list[int]:
    """The frames of an MP4 a player can start at: its keyframes' times, in frames."""
    with av.open(str(path)) as container:
        video = container.streams.video[0]
        base = video.time_base
        assert base is not None
        return [
            int(packet.pts * base * 10)
            for packet in container.demux(video)
            if packet.is_keyframe and packet.pts is not None
        ]


def test_each_section_begins_on_a_keyframe(tmp_path: Path) -> None:
    namespace: dict[str, object] = {}
    exec(TALK, namespace)
    talk = namespace["Talk"]
    assert isinstance(talk, type)
    assert issubclass(talk, m.Scene)
    film = talk().render(tmp_path / "talk.mp4")
    assert [s.frame for s in film.sections] == keyframes(tmp_path / "talk.mp4")
    html = page(film, "talk.mp4", "Talk")
    deck = json.loads(html.split("const deck = ", 1)[1].split(";", 1)[0])
    assert [s["name"] for s in deck["sections"]] == ["unnamed", "points", "gear"]
    assert deck["sections"][2]["type"] == "presentation.loop"
    assert deck["frames"] == film.frame_count
    assert deck["fps"] == 10


def test_the_pages_help_names_the_key_that_opens_the_presenter_view() -> None:
    # p goes back a slide, as a clicker's back key does: the presenter view is Shift+P
    html = (Path(m.__file__).parent / "cli" / "present.html").read_text(
        encoding="utf-8"
    )
    start = html.index('<div id="help">')
    shown = html[start : html.index("</div>", start)]
    assert 'case "P": openPresenter()' in html
    assert 'case "p": back()' in html
    assert "Shift+P: presenter view" in shown


@pytest.mark.parametrize(
    ("video", "expected"),
    [
        (
            'https://example.org/talk.mp4?a=1&label="DECK_JSON"',
            'https://example.org/talk.mp4?a=1&label="DECK_JSON"',
        ),
        (Path("slides/DECK_TITLE & #1.mp4"), "slides/DECK_TITLE%20%26%20%231.mp4"),
    ],
)
def test_the_page_preserves_urls_paths_and_text(
    video: str | Path, expected: str
) -> None:
    class Document(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.tags: list[tuple[str, dict[str, str | None]]] = []
            self.title = ""
            self.in_title = False

        def handle_starttag(
            self, tag: str, attrs: list[tuple[str, str | None]]
        ) -> None:
            self.tags.append((tag, dict(attrs)))
            self.in_title = tag == "title"

        def handle_endtag(self, tag: str) -> None:
            if tag == "title":
                self.in_title = False

        def handle_data(self, data: str) -> None:
            if self.in_title:
                self.title += data

    title = "A & B </title><img> DECK_VIDEO DECK_JSON"
    film = m.Film(take=lambda _: None)
    html = page(film, video, title)
    document = Document()
    document.feed(html)
    assert document.title == title
    assert "img" not in [tag for tag, _ in document.tags]
    assert [
        (attrs["src"], set(attrs)) for tag, attrs in document.tags if tag == "video"
    ] == [(expected, {"id", "src", "preload", "playsinline"})]
    deck = json.loads(html.split("const deck = ", 1)[1].split(";", 1)[0])
    assert deck["frames"] == film.frame_count


def test_present_writes_the_video_the_page_and_a_handout(tmp_path: Path) -> None:
    scene = tmp_path / "talk.py"
    scene.write_text(TALK, encoding="utf-8")
    result = CliRunner().invoke(
        app,
        ["present", str(scene), "--pdf", "--no-open", "-r", "320x180", "--fps", "10"],
    )
    assert result.exit_code == 0, result.output
    for suffix in (".mp4", ".html", ".pdf"):
        assert (tmp_path / f"Talk{suffix}").stat().st_size > 0
    # a page for each slide's end: the two sections' starts after the first, and the last frame
    assert b"/Count 3" in (tmp_path / "Talk.pdf").read_bytes()
