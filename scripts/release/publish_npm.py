"""Publish a built npm tarball, accepting a retry only when the registry has its exact bytes."""

import argparse
import base64
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from time import monotonic, sleep


def publish(archive: Path) -> None:
    # npm interprets relative names such as dist/package.tgz as GitHub package specs.
    archive = archive.resolve()
    with tarfile.open(archive) as package:
        metadata = package.extractfile("package/package.json")
        if metadata is None:
            raise ValueError("npm archive has no package.json")
        manifest = json.load(metadata)
    name = f"{manifest['name']}@{manifest['version']}"
    integrity = "sha512-" + base64.b64encode(
        hashlib.sha512(archive.read_bytes()).digest()
    ).decode("ascii")

    def exists(timeout: float | None = None) -> bool:
        result = subprocess.run(
            ["npm", "view", name, "dist.integrity", "--json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        record = json.loads(result.stdout)
        if result.returncode:
            if (
                isinstance(record, dict)
                and record.get("error", {}).get("code") == "E404"
            ):
                return False
            raise RuntimeError(f"cannot inspect {name}: {result.stdout}{result.stderr}")
        if record != integrity:
            raise ValueError(f"{name} already exists with different artifact bytes")
        return True

    if not exists():
        subprocess.run(
            ["npm", "publish", str(archive), "--provenance", "--access", "public"],
            check=True,
        )
        # Acceptance precedes registry visibility while npm processes a publication.
        deadline = monotonic() + 300
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"{name} was not available within five minutes of publication"
                )
            if exists(timeout=remaining):
                break
            sleep(min(5, max(0, deadline - monotonic())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    publish(parser.parse_args().archive)
