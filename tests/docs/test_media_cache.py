"""Rendered media is reused by its inputs, and only complete outputs can be reused."""

import json
import os
import shutil
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from docs import examples

SCENE = "class Alpha(Scene):\n    pass\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def source_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    docs = tmp_path / "docs"
    for name, path in {
        "ROOT": tmp_path,
        "DOCS": docs,
        "PAGES": docs / "content",
        "README": tmp_path / "README.md",
        "SOURCE": tmp_path / "src" / "manimgx",
        "FILMS": docs / "content" / "films",
        "RECORDS": docs / ".cache" / "films",
    }.items():
        monkeypatch.setattr(examples, name, path)
    write(tmp_path / "README.md", "# Welcome\n")
    write(tmp_path / "examples" / "alpha.py", SCENE)
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "sample"\nversion = "0.1.0"\nrequires-python = ">=3.13"\n'
        'dependencies = ["painter"]\n'
        '[dependency-groups]\ndev = ["linter"]\ndocs = ["site"]\n'
        '[tool.uv]\ndefault-groups = ["dev", "docs"]\n',
    )
    write(
        tmp_path / "uv.lock",
        'version = 1\nrevision = 3\nrequires-python = ">=3.13"\n'
        '[[package]]\nname = "sample"\nversion = "0.1.0"\nsource = { virtual = "." }\n'
        'dependencies = [{ name = "painter" }]\n'
        '[package.dev-dependencies]\ndev = [{ name = "linter" }]\ndocs = [{ name = "site" }]\n'
        '[[package]]\nname = "painter"\nversion = "1.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        'dependencies = [{ name = "pigment" }]\n'
        '[[package]]\nname = "pigment"\nversion = "2.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        f'sdist = {{ url = "https://example.org/pigment.tar.gz", hash = "sha256:{"0" * 64}" }}\n'
        '[[package]]\nname = "linter"\nversion = "3.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        '[[package]]\nname = "site"\nversion = "4.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n',
    )
    examples.render_context.cache_clear()
    yield tmp_path
    examples.render_context.cache_clear()


@pytest.mark.parametrize(
    "name",
    [
        "src/manimgx/scene.py",
        "rust/engine/src/render.rs",
        "rust/engine/src/stroke.wgsl",
        "rust/engine/Cargo.toml",
        "rust/ffmpeg/build.rs",
        "rust/Cargo.lock",
        "rust/mitex-spec-gen/lib.typ",
        "rust/mitex-spec-gen/spec.rkyv",
        "fonts/manimgx-fonts/src/manimgx_fonts/font.ttf",
        "docs/assets/input.svg",
        "docs/voice/line.mp3",
        "docs/render.py",
        "docs/svg.py",
    ],
)
def test_shared_input_changes_invalidate_films(source_tree: Path, name: str) -> None:
    original = examples.render_context()
    path = write(source_tree / name, "first")
    examples.render_context.cache_clear()
    added = examples.render_context()
    assert added != original
    path.write_text("second", encoding="utf-8")
    examples.render_context.cache_clear()
    assert examples.render_context() not in {original, added}
    path.unlink()
    examples.render_context.cache_clear()
    assert examples.render_context() == original


def test_tooling_and_orchestration_do_not_invalidate_media(source_tree: Path) -> None:
    before = examples.cache_key()
    project = source_tree / "pyproject.toml"
    project.write_text(
        project.read_text(encoding="utf-8") + "\n[tool.ruff]\nline-length = 99\n",
        encoding="utf-8",
    )
    lock = source_tree / "uv.lock"
    updated = (
        lock.read_text(encoding="utf-8")
        .replace('version = "3.0"', 'version = "3.1"')
        .replace('version = "4.0"', 'version = "4.1"')
    )
    lock.write_text(updated, encoding="utf-8")
    write(source_tree / "docs" / "examples.py", "# New scheduling or HTML logic.\n")
    examples.render_context.cache_clear()
    assert examples.cache_key() == before
    assert lock.read_text(encoding="utf-8") == updated


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('version = "1.0"', 'version = "1.1"'),
        ('version = "2.0"', 'version = "2.1"'),
        ("0" * 64, "1" * 64),
        ('dependencies = [{ name = "pigment" }]', "dependencies = []"),
    ],
)
def test_locked_runtime_changes_invalidate_media(
    source_tree: Path, old: str, new: str
) -> None:
    before = examples.cache_key()
    lock = source_tree / "uv.lock"
    lock.write_text(
        lock.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
    )
    examples.render_context.cache_clear()
    assert examples.cache_key() != before


@pytest.mark.parametrize(
    "settings",
    [
        '[build-system]\nrequires = ["maturin"]\nbuild-backend = "maturin"\n',
        '[tool.maturin]\nfeatures = ["render"]\n',
    ],
)
def test_build_settings_are_render_inputs(source_tree: Path, settings: str) -> None:
    before = examples.render_context()
    project = source_tree / "pyproject.toml"
    project.write_text(project.read_text(encoding="utf-8") + settings, encoding="utf-8")
    examples.render_context.cache_clear()
    assert examples.render_context() != before


def test_prose_styles_and_generated_files_do_not_change_the_key(
    source_tree: Path,
) -> None:
    before = examples.cache_key()
    for name in (
        "README.md",
        "docs/content/guide.md",
        "docs/content/stylesheets/theme.css",
        "docs/content/javascripts/newsletter.js",
        "docs/content/gallery/old.md",
        "docs/content/films/old.webp",
        "docs/.cache/films/old.json",
        "fonts/manimgx-fonts/src/manimgx_fonts/__pycache__/fonts.pyc",
    ):
        write(source_tree / name, "changed prose")
    examples.render_context.cache_clear()
    assert examples.cache_key() == before


def test_only_the_edited_example_changes_identity(source_tree: Path) -> None:
    write(source_tree / "examples" / "beta.py", SCENE.replace("Alpha", "Beta"))
    before = {name: e.stem for name, e in examples.scenes().items()}
    key = examples.cache_key()
    write(source_tree / "examples" / "alpha.py", SCENE.replace("pass", "value = 1"))
    after = {name: e.stem for name, e in examples.scenes().items()}
    assert after["Alpha"] != before["Alpha"]
    assert after["Beta"] == before["Beta"]
    assert examples.cache_key()["prefix"] == key["prefix"]
    assert examples.cache_key()["key"] != key["key"]


def test_gallery_is_discovered_without_generated_pages(source_tree: Path) -> None:
    assert list(examples.scenes()) == ["Alpha"]
    write(
        source_tree / "docs" / "content" / "gallery" / "stale.md",
        "```python\nclass Stale(Scene):\n    pass\n```\n",
    )
    assert list(examples.scenes()) == ["Alpha"]


def test_readme_svg_requirement_changes_the_snapshot_key(source_tree: Path) -> None:
    before = examples.cache_key()
    stem = examples.scenes()["Alpha"].stem
    write(source_tree / "README.md", f"```python\n{SCENE}```\n")
    assert examples.scenes()["Alpha"].stem == stem
    assert examples.cache_key()["key"] != before["key"]


def test_paths_and_timestamps_are_not_render_inputs(
    source_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write(source_tree / "src" / "manimgx" / "scene.py", '"""Runtime docs."""\n')
    before = examples.render_context()
    os.utime(path, (1, 1))
    examples.render_context.cache_clear()
    assert examples.render_context() == before
    copied = source_tree.parent / f"{source_tree.name}-copy"
    shutil.copytree(source_tree, copied)
    monkeypatch.setattr(examples, "ROOT", copied)
    examples.render_context.cache_clear()
    assert examples.render_context() == before


def test_driver_profile_and_format_are_render_inputs(
    source_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = examples.Example(SCENE).stem
    monkeypatch.setenv("MANIMGX_DOCS_RENDER_PROFILE", "another-driver")
    examples.render_context.cache_clear()
    changed_driver = examples.Example(SCENE).stem
    assert changed_driver != before
    monkeypatch.setattr(examples, "FORMAT", "another format")
    assert examples.Example(SCENE).stem not in {before, changed_driver}


@pytest.mark.parametrize("animated", [False, True])
def test_real_renders_record_static_and_animated_outputs(
    source_tree: Path, animated: bool
) -> None:
    code = (
        "from manimgx import Scene, Square\n"
        "class Tiny(Scene):\n"
        "    def construct(self):\n"
        "        square = Square()\n"
        "        self.add(square)\n"
    )
    if animated:
        code += "        self.play(square.animate.set_opacity(0.5), run_time=0.05)\n"
    example = examples.Example(code)
    assert not examples._rendered(example, False)
    examples.render(example, readme=True)
    assert examples._rendered(example, True)
    assert (examples.FILMS / f"{example.stem}.mp4").exists() == animated
    assert not list(examples.FILMS.glob("*.json"))
    assert not list(examples.RECORDS.parent.glob("render-*"))


@pytest.fixture
def draw(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    rendered: list[str] = []

    def make(example: examples.Example, folder: Path, readme: bool) -> None:
        rendered.append(str(example.scene))
        for suffix in examples.OUTPUTS if readme else (".webp", ".mp4"):
            (folder / f"{example.stem}{suffix}").write_bytes(b"complete output")

    monkeypatch.setattr(examples, "_draw", make)
    return rendered


@pytest.mark.parametrize("damage", ["delete", "truncate", "modify"])
def test_missing_or_damaged_video_is_rendered_again(
    source_tree: Path, draw: list[str], damage: str
) -> None:
    example = examples.Example(SCENE)
    examples.render(example)
    video = examples.FILMS / f"{example.stem}.mp4"
    if damage == "delete":
        video.unlink()
    elif damage == "truncate":
        video.write_bytes(b"complete")
    else:
        video.write_bytes(b"Complete output")
    assert not examples._rendered(example, False)
    examples.render(example)
    assert examples._rendered(example, False)
    assert draw == ["Alpha", "Alpha"]


def test_failed_render_preserves_previous_complete_output(
    source_tree: Path, draw: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    example = examples.Example(SCENE)
    examples.render(example)

    def fail(example: examples.Example, folder: Path, readme: bool) -> None:
        (folder / f"{example.stem}.webp").write_bytes(b"unfinished")
        raise RuntimeError("render interrupted")

    monkeypatch.setattr(examples, "_draw", fail)
    with pytest.raises(RuntimeError, match="render interrupted"):
        examples.render(example)
    assert examples._rendered(example, False)
    assert not list(examples.RECORDS.parent.glob("render-*"))


def test_interrupted_publication_is_not_a_completed_render(
    source_tree: Path, draw: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    example = examples.Example(SCENE)
    replace = Path.replace

    def fail_record(path: Path, target: Path) -> Path:
        if path.suffix == ".json":
            raise OSError("publication interrupted")
        return replace(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_record)
        with pytest.raises(OSError, match="publication interrupted"):
            examples.render(example)
    assert (examples.FILMS / f"{example.stem}.webp").exists()
    assert not examples._rendered(example, False)
    examples.render(example)
    assert examples._rendered(example, False)


@pytest.mark.parametrize("record", ["{", "null", "[]", "{}", '{"../../outside": "x"}'])
def test_invalid_completion_record_is_a_miss(
    source_tree: Path, draw: list[str], record: str
) -> None:
    example = examples.Example(SCENE)
    examples.render(example)
    write(examples.RECORDS / f"{example.stem}.json", record)
    assert not examples._rendered(example, False)


def test_snapshot_tracks_names_and_damage_but_not_timestamps_or_staging(
    source_tree: Path, draw: list[str]
) -> None:
    before = examples.cache_state()
    example = examples.Example(SCENE)
    examples.render(example)
    complete = examples.cache_state()
    assert complete != before
    video = examples.FILMS / f"{example.stem}.mp4"
    os.utime(video, (1, 1))
    write(examples.RECORDS.parent / "render-interrupted" / "unfinished.mp4", "partial")
    assert examples.cache_state() == complete
    renamed = video.rename(video.with_stem("same-pixels-new-name"))
    assert examples.cache_state() != complete
    renamed.rename(video)
    assert examples.cache_state() == complete
    video.write_bytes(b"damaged")
    assert examples.cache_state() != complete
    examples.render(example)
    assert examples.cache_state() == complete


def test_build_reuses_unchanged_scenes_and_prunes_removed_ones(
    source_tree: Path, draw: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Use the actual scheduler and filesystem with cheap fake renders in this process.
    monkeypatch.setattr(
        examples, "ProcessPoolExecutor", lambda **_: ThreadPoolExecutor(max_workers=1)
    )
    beta = write(source_tree / "examples" / "beta.py", SCENE.replace("Alpha", "Beta"))
    examples.main([])
    assert draw == ["Alpha", "Beta"]
    before = {name: e.stem for name, e in examples.scenes().items()}
    draw.clear()
    examples.main([])
    assert draw == []
    write(source_tree / "examples" / "alpha.py", SCENE.replace("pass", "value = 1"))
    examples.main([])
    assert draw == ["Alpha"]
    assert not (examples.FILMS / f"{before['Alpha']}.mp4").exists()
    assert not (examples.RECORDS / f"{before['Alpha']}.json").exists()
    draw.clear()
    beta.unlink()
    examples.main([])
    assert draw == []
    assert not (examples.FILMS / f"{before['Beta']}.mp4").exists()
    assert len(list(examples.RECORDS.glob("*.json"))) == 1
    assert set(
        json.loads(next(examples.RECORDS.glob("*.json")).read_text(encoding="utf-8"))
    ) == {
        ".webp",
        ".mp4",
    }


def test_restored_partial_build_resumes_and_repairs_only_missing_or_damaged_films(
    source_tree: Path, draw: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        examples, "ProcessPoolExecutor", lambda **_: ThreadPoolExecutor(max_workers=1)
    )
    write(source_tree / "examples" / "beta.py", SCENE.replace("Alpha", "Beta"))
    make = examples._draw

    def fail_beta(example: examples.Example, folder: Path, readme: bool) -> None:
        if example.scene == "Beta":
            (folder / f"{example.stem}.mp4").write_bytes(b"unfinished")
            raise RuntimeError("interrupted")
        make(example, folder, readme)

    with monkeypatch.context() as patch:
        patch.setattr(examples, "_draw", fail_beta)
        with pytest.raises(SystemExit):
            examples.main([])
    alpha, beta = examples.scenes().values()
    assert examples._rendered(alpha, False)
    assert not examples._rendered(beta, False)

    # An archive transported to a fresh runner contains completed work, even though
    # the overall build failed. Progress is not part of any film's identity.
    archive = shutil.make_archive(str(source_tree / "snapshot"), "tar", examples.DOCS)
    shutil.rmtree(examples.DOCS)
    shutil.unpack_archive(archive, examples.DOCS, filter="data")
    draw.clear()
    examples.main([])
    assert draw == ["Beta"]
    assert examples._rendered(alpha, False)
    assert examples._rendered(beta, False)

    (examples.FILMS / f"{alpha.stem}.mp4").write_bytes(b"damaged")
    draw.clear()
    examples.main([])
    assert draw == ["Alpha"]
    assert examples._rendered(alpha, False)
    draw.clear()
    examples.main([])
    assert draw == []
