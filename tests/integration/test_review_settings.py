"""The CLI, stored settings and HTTP API share one comparison-settings contract."""

import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from tests.integration.corpus import case as corpus
from tests.integration.corpus.__main__ import main
from tests.integration.review import app as panel


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(corpus, "SETTINGS", path)
    corpus.save_settings(corpus.Settings("max", 0))
    return path


@pytest.mark.parametrize("value", [-1, 256, float("inf"), float("nan")])
def test_domain_rejects_impossible_channel_error_budgets(value: float) -> None:
    with pytest.raises(ValueError, match="tolerance"):
        corpus.Settings("max", value)


@pytest.mark.parametrize("value", ["-1", "256", "inf", "nan"])
def test_cli_cannot_write_an_invalid_comparison_budget(
    settings: Path, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = settings.read_bytes()
    monkeypatch.setattr(sys, "argv", ["corpus", "settings", "--tolerance", value])
    with pytest.raises(ValueError, match="tolerance"):
        main()
    assert settings.read_bytes() == before


@pytest.mark.parametrize(
    ("metric", "tolerance"),
    [("absent", 0), ("max", -1), ("max", 256), ("max", "Infinity"), ("max", "NaN")],
)
def test_http_rejects_invalid_settings_with_422_without_writing(
    settings: Path, metric: str, tolerance: float | str
) -> None:
    before = settings.read_bytes()

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=panel.app), base_url="http://review.test"
        ) as client:
            return await client.put(
                "/api/settings", json={"metric": metric, "tolerance": tolerance}
            )

    response = asyncio.run(request())
    assert response.status_code == 422, response.text
    assert settings.read_bytes() == before


def test_http_and_stored_settings_keep_the_existing_response_shape(
    settings: Path,
) -> None:
    async def request() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=panel.app), base_url="http://review.test"
        ) as client:
            written = await client.put(
                "/api/settings", json={"metric": "mae", "tolerance": 255}
            )
            return written, await client.get("/api/settings")

    written, read = asyncio.run(request())
    assert written.status_code == read.status_code == 200
    assert (
        written.json()
        == read.json()
        == {"metric": "mae", "tolerance": 255, "metrics": list(corpus.METRICS)}
    )
    assert corpus.settings() == corpus.Settings("mae", 255)
    settings.write_text('{"metric":"max","tolerance":-1}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="tolerance"):
        corpus.settings()
