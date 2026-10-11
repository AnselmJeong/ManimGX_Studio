"""Compare the corpus with a verified wheel from the latest stable GitHub release."""

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Self

from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from tests.integration.corpus import baseline, engines
from tests.integration.corpus.case import Case, Failure, Frames, _list, _object, _str
from tests.integration.corpus.frozen import prepare

LATEST = "https://api.github.com/repos/academa-labs/manimgx/releases/latest"
DOWNLOADS = "https://github.com/academa-labs/manimgx/releases/download/"


@dataclass(frozen=True, slots=True)
class Release:
    tag: str
    wheels: tuple[baseline.Artifact, ...]

    @classmethod
    def latest(cls) -> Self | None:
        """Only an absent stable release permits the first-release bootstrap."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "manimgx-corpus",
        }
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(LATEST, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = _object(json.load(response))
        except urllib.error.HTTPError as error:
            error.close()
            if error.code == 404:
                return None
            raise
        if data.get("draft") is not False or data.get("prerelease") is not False:
            raise ValueError("the corpus reference must be a published stable release")
        tag = _str(data["tag_name"])
        version = Version(tag.removeprefix("v"))
        if not tag.startswith("v") or version.is_prerelease or version.is_devrelease:
            raise ValueError("the corpus reference needs a stable version tag")
        wheels = []
        for value in _list(data["assets"]):
            asset = _object(value)
            name = _str(asset["name"])
            if not name.endswith(".whl"):
                continue
            distribution, wheel_version, _, _ = parse_wheel_filename(name)
            if distribution != "manimgx":
                continue
            if wheel_version != version:
                raise ValueError(f"{name}: wheel version does not match {tag}")
            digest = _str(asset.get("digest"))
            if not digest.startswith("sha256:"):
                raise ValueError(f"{name}: release asset has no SHA256 identity")
            url = _str(asset["browser_download_url"])
            if url != f"{DOWNLOADS}{tag}/{name}":
                raise ValueError(f"{name}: unexpected release download URL")
            wheels.append(baseline.Artifact(name, digest.removeprefix("sha256:"), url))
        if not wheels:
            raise ValueError(f"{tag}: the release has no ManimGX wheels")
        return cls(tag, tuple(wheels))

    def wheel(self) -> baseline.Artifact:
        """Choose the most specific wheel compatible with this Python and platform."""
        ranks = {tag: index for index, tag in enumerate(sys_tags())}
        compatible = [
            (min(ranks[tag] for tag in tags), wheel)
            for wheel in self.wheels
            if (tags := parse_wheel_filename(wheel.filename)[3].intersection(ranks))
        ]
        if not compatible:
            raise ValueError(f"{self.tag}: no wheel for this Python/platform")
        return min(compatible, key=lambda item: item[0])[1]

    @classmethod
    def read(cls, path: Path) -> Self | None:
        """Read the release identity already resolved for this test run."""
        data = json.loads(path.read_text(encoding="utf-8"))
        if data is None:
            return None
        value = _object(data)
        wheels = []
        for entry in _list(value["wheels"]):
            item = _object(entry)
            wheels.append(
                baseline.Artifact(
                    _str(item["filename"]), _str(item["sha256"]), _str(item["url"])
                )
            )
        return cls(_str(value["tag"]), tuple(wheels))


class References:
    """One release package per worker; no old corpus artifact is required."""

    def __init__(self, release: Release | None, directory: Path) -> None:
        self.release = release
        self.directory = directory
        self._package: Path | None = None

    def compare(self, case: Case, output: Path) -> engines.Result:
        output.mkdir(parents=True, exist_ok=True)
        if self.release is None:
            (output / "reference.json").write_text(
                json.dumps({"release": None, "mode": "render-and-export"}) + "\n",
                encoding="utf-8",
            )
            result = engines.run(case, "manimgx", mp4=True, log=output / "actual.log")
            if isinstance(result.frames, Frames) and not (
                result.frames.count == result.film_frames == result.mp4_frames
            ):
                return replace(
                    result, frames=Failure("rendered and exported frame counts differ")
                )
            return result
        wheel = self.release.wheel()
        if self._package is None:
            self._package = prepare(
                wheel.acquire(baseline.CACHE),
                wheel.sha256,
                self.directory / wheel.sha256,
            )
        (output / "release.json").write_text(
            json.dumps({"tag": self.release.tag, **asdict(wheel)}, indent=2) + "\n",
            encoding="utf-8",
        )
        return baseline.compare(case, self._package, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    release = Release.latest()
    if release is not None:
        release.wheel().acquire(baseline.CACHE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(None if release is None else asdict(release), indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "No stable release yet: corpus renders and exports remain enabled."
        if release is None
        else f"Corpus reference: {release.tag}"
    )


if __name__ == "__main__":
    main()
