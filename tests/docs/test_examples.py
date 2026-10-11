"""The docs' examples, as the site's build renders them (`docs/examples.py`): the build has
no voice's key (its workflow has none), so a narrated example says what `docs/voice/` keeps."""

import sys
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from unittest.mock import Mock

import numpy as np
import pytest
from docs import examples
from examples.cherenkov_cone import CherenkovCone

from manimgx.rendering.film import Cut


@pytest.mark.parametrize(
    "root", [PurePosixPath("/project"), PureWindowsPath("C:/project")]
)
def test_block_locations_use_repository_paths_on_each_platform(
    root: PurePath, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(examples, "DOCS", root / "docs")
    blocks = examples.blocks(
        "A story.\n\n```python\nclass Example(Scene): pass\n```\n",
        root / "src" / "manimgx" / "example.py",
        line=40,
    )
    assert blocks == [
        examples.Example("class Example(Scene): pass\n", "src/manimgx/example.py:42")
    ]


def test_a_broken_runtime_stops_before_workers_start_or_films_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    film = tmp_path / "previous.webp"
    film.write_bytes(b"previous film")
    pool = Mock(side_effect=AssertionError("a broken runtime must not start workers"))
    monkeypatch.setattr(examples, "FILMS", tmp_path)
    monkeypatch.setattr(examples, "ProcessPoolExecutor", pool)
    monkeypatch.setitem(sys.modules, "manimgx", None)

    with pytest.raises(ModuleNotFoundError, match="manimgx"):
        examples.main([])

    pool.assert_not_called()
    assert film.read_bytes() == b"previous film"


def test_an_unimportable_native_failure_keeps_its_cause_across_processes() -> None:
    example = examples.Example(
        "class NativeFailure(BaseException):\n"
        "    pass\n"
        "raise NativeFailure('buffer exceeds the device limit')\n",
        "native-failure.py:1",
    )
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        result = pool.submit(examples._render, example, False)
        with pytest.raises(
            RuntimeError, match="buffer exceeds the device limit"
        ) as caught:
            result.result(timeout=60)
    assert "NativeFailure" in str(caught.value)
    assert "native-failure.py:1" in str(caught.value)


def test_a_narrated_example_says_what_docs_voice_keeps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FAL_KEY", raising=False)
    narrated = [e for e in examples.examples() if ".say(" in e.code]
    assert narrated
    for example in narrated:
        examples.load(example)().render()  # its frames counted, not drawn


def test_unborn_cherenkov_photons_have_no_invalid_numerical_state() -> None:
    # Below the emission threshold every photon slot is empty. Its -inf timestamp
    # must be excluded before periodic arithmetic, not masked after cos(-inf).
    with np.errstate(invalid="raise"):
        film = CherenkovCone().render(plays=Mock(side_effect=Cut))
    assert film.frame_count > 0
