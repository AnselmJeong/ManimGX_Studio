"""Keep the sources of the Linux wheel's bundled distribution libraries.

Run after auditwheel repair, inside the same manylinux image. auditwheel's SBOM names
the packages it actually copied. RPM identifies their exact source packages, and DNF
retrieves those versions. LLVM's checked archive is kept by build_lavapipe.sh. Compilers and
other build tools stay system prerequisites: this records source closure, not a hermetic
or bit-identical build environment.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def bundled_packages(wheel: Path) -> set[str]:
    """The exact distribution packages whose libraries auditwheel put in the wheel."""
    with zipfile.ZipFile(wheel) as archive:
        libraries = [
            n for n in archive.namelist() if ".libs/" in n and not n.endswith("/")
        ]
        sboms = [
            n for n in archive.namelist() if n.endswith("/sboms/auditwheel.cdx.json")
        ]
        if not libraries:
            return set()
        if len(sboms) != 1:
            raise ValueError(
                "the repaired wheel's libraries have no unique auditwheel SBOM"
            )
        components = json.loads(archive.read(sboms[0]))["components"][1:]
        if len(components) != len(libraries):
            raise ValueError(
                "auditwheel could not identify every bundled library's package"
            )
        if any(not c["purl"].startswith("pkg:rpm/") for c in components):
            raise ValueError(
                "a bundled library was not supplied by the manylinux RPM image"
            )
        return {f"{c['name']}-{c['version']}" for c in components}


def output(*args: str) -> str:
    return subprocess.check_output(
        args, text=True, env=os.environ | {"LC_ALL": "C"}
    ).strip()


def digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def collect(wheel: Path, sources: Path) -> None:
    packages = bundled_packages(wheel)
    destination = sources / f"linux-{platform.machine()}"
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for package in sorted(packages):
        # The installed NEVRA, including architecture, resolves exactly the binary which
        # auditwheel copied, rather than a newer source of the same name.
        name, epoch, version, release, arch, source = output(
            "rpm",
            "-q",
            "--qf",
            "%{NAME} %{EPOCH} %{VERSION} %{RELEASE} %{ARCH} %{SOURCERPM}",
            package,
        ).split()
        binary = (
            f"{name}-{0 if epoch == '(none)' else epoch}:{version}-{release}.{arch}"
        )
        with tempfile.TemporaryDirectory(dir=destination) as temporary:
            subprocess.run(
                [
                    "dnf",
                    "download",
                    "--source",
                    "--downloaddir",
                    temporary,
                    source.removesuffix(".rpm"),
                ],
                check=True,
            )
            archive = Path(temporary) / source
            # A repository cannot silently substitute another source version. Only the
            # exact signed RPM is published into the artifact; partial downloads stay private.
            if not archive.is_file():
                raise ValueError(
                    f"DNF did not supply the installed package's source: {source}"
                )
            if "signatures OK" not in output("rpm", "--checksig", str(archive)):
                raise ValueError(f"the source RPM has no verified signature: {source}")
            sha256 = digest(archive)
            archive.replace(destination / source)
        records.append({"binary": binary, "source": source, "sha256": sha256})
    manifest = {
        "wheel": wheel.name,
        "sha256": digest(wheel),
        "packages": records,
        "build_system": platform.freedesktop_os_release(),
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def verify(sources: Path) -> None:
    """Both Linux builds supplied their sources, unchanged since their wheels were made."""
    for machine in ["x86_64", "aarch64"]:
        directory = sources / f"linux-{machine}"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        for package in manifest["packages"]:
            if digest(directory / package["source"]) != package["sha256"]:
                raise ValueError(
                    f"{machine}: the retained source changed: {package['source']}"
                )


def main() -> None:
    if sys.argv[1] == "--verify":
        verify(Path(sys.argv[2]))
        return
    directory = Path(sys.argv[1])
    sources = Path(
        os.environ.get("MANIMGX_SOURCES")
        or Path(__file__).resolve().parents[2] / "sources"
    )
    (wheel,) = directory.glob("*.whl")
    collect(wheel, sources)


if __name__ == "__main__":
    main()
