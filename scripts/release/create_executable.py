# /// script
# requires-python = ">=3.14"
# ///
"""Create ManimGX's executable for this machine, from its wheel in dist/: one file holding a
Python with ManimGX and its locked dependencies installed.

The file is PyApp (https://ofek.dev/pyapp). Its first run unpacks the Python it holds; every
run then runs `manimgx` there, with no network and no Python on the machine. `manimgx self`
manages it: `self pip install PACKAGE` adds a package a scene imports, `self remove` deletes
what it unpacked, `self cache dist --remove` the copy of the Python it keeps.

Run it with `just create-executable`; it writes dist/manimgx-<os>-<arch>.tar.gz (a .zip on
Windows), after running what it made once.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

PYAPP = "0.29.0"
PYAPP_SHA256 = "0ad1267db069a83e16dad2a42b0d01c727f5a9da7614330f44b66876da2d15f6"
PYTHON = "3.14.8"
PBS_RELEASE = "20261003"
PBS_COMMIT = "5e46737f6480fc315ebfea83866910cbfcc772f0"
PBS_SOURCE_SHA256 = "2c4bc5e43a0276046f080f40f0bd9586b10f2a6aa1714c592557f57ef0821e0c"
# The full archives retain PYTHON.json and notices that install-only archives omit.
PYTHONS = {
    "linux-x86_64": (
        "x86_64-unknown-linux-gnu",
        "pgo+lto",
        "43b8c1b02e3daefbbbf4b5714b656ea00a5cae24f55c4589fb87468bcac682ed",
    ),
    "linux-arm64": (
        "aarch64-unknown-linux-gnu",
        "pgo+lto",
        "72cee1a99dfde64850dd5ffde8d96f84b0d352fd694cc1e92dad78abae6b8f29",
    ),
    "macos-arm64": (
        "aarch64-apple-darwin",
        "pgo+lto",
        "6bb6e246d6c2bdfef5b33e833541c232d99afb37b67a08872f233649f4b64ca7",
    ),
    "windows-x86_64": (
        "x86_64-pc-windows-msvc",
        "pgo",
        "c2d2aee5613fbdc2e178b0c90f5f7b16fb5f0d452f1f09c63ff09043c9a1cde3",
    ),
}

# Selected by PBS targets.yml/Makefile and cpython-windows/build.py, not by
# license_paths (which intentionally lists alternatives across Python versions).
PYTHON_COMMON_SOURCES = (
    "cpython-3.14",
    "pip",
    "bzip2",
    "mpdecimal",
    "openssl-3.5",
    "sqlite",
    "xz",
    "zstd",
)
PYTHON_UNIX_SOURCES = ("expat", "libffi", "tcl", "tk", "uuid")
PYTHON_LINUX_SOURCES = (
    "bdb",
    "libedit",
    "libX11",
    "libXau",
    "libxcb",
    "ncurses",
    "zlib",
    "xorgproto",
)
# PBS builds Windows libffi from this commit; CPython3.14.8 get_externals.bat
# selects these Tcl/Tk source tags alongside its tcltk-9.0.4.0 binary bundle.
PYTHON_WINDOWS_SOURCES = {
    "libffi": (
        "16fad4855b3d8c03b5910e405ff3a04395b39a98",
        "f21ae7b0cce58cf9428e01d4d22aac9c3b70722a4e9b2c92b3a97d490a1b401c",
    ),
    "tcl": (
        "53c758cbf2cc178b359abc03fdd912c5e66ed74f",
        "2ec3a0db72d1eb15096940ce67e226bc16a0719e12e554c7feb920eb40bd6f36",
    ),
    "tk": (
        "a6a5bee1ef4b526b0d11200c84bc02e85d8ecc83",
        "b913ff99cc8e0a930d1f3d6064b751fbd4180fa850fa287e6e25e26c379ab73e",
    ),
}

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
WINDOWS = sys.platform == "win32"
INTERPRETER = "python.exe" if WINDOWS else "bin/python3"  # in the Python's directory
SYSTEM = {"linux": "linux", "darwin": "macos", "win32": "windows"}[sys.platform]
MACHINE = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}[
    platform.machine().lower()
]


def run(
    *command: str | Path,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> None:
    print("$", *command, flush=True)
    subprocess.run([str(part) for part in command], check=True, env=env, cwd=cwd)


def the_wheel() -> Path:
    """The one ManimGX wheel in dist/ (the workflows put this machine's there)."""
    wheels = sorted(DIST.glob("manimgx-*.whl"))
    if len(wheels) != 1:
        sys.exit(f"expected one ManimGX wheel in {DIST}, found {len(wheels)}")
    return wheels[0]


def fetch(url: str, digest: str, directory: Path, *, source: bool = True) -> Path:
    """Use the release's verified acquisition, without retaining binary inputs as source."""
    env = os.environ | {"OUT_DIR": str(directory)}
    if not source:
        env.pop("MANIMGX_SOURCES", None)
    run(
        "cargo", "run", "--locked", "--manifest-path", ROOT / "rust/Cargo.toml",
        "-p", "fetch", "--bin", "fetch-file", "--", url, digest, env=env,
    )  # fmt: skip
    path = directory / digest
    if sha256(path) != digest:
        raise ValueError(f"download changed: {url}")
    return path


def license_paths(value: object) -> set[str]:
    """Every declared notice, including extension variants, in upstream metadata."""
    if isinstance(value, dict):
        result = set()
        for key, item in value.items():
            if key == "license_path" and isinstance(item, str):
                result.add(item)
            elif key == "license_paths" and isinstance(item, list):
                result.update(path for path in item if isinstance(path, str))
            else:
                result.update(license_paths(item))
        return result
    if isinstance(value, list):
        return set().union(*(license_paths(item) for item in value))
    return set()


def python_sources(
    recipe: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, str]]:
    """The actual runtime source graph, with build scripts retained in PBS/CPython."""
    names = list(PYTHON_COMMON_SOURCES)
    names += ["zlib-ng"] if SYSTEM == "windows" else list(PYTHON_UNIX_SOURCES)
    if SYSTEM == "linux":
        names += PYTHON_LINUX_SOURCES
    inputs = {}
    for name in names:
        url, digest = recipe[name]["url"], recipe[name]["sha256"]
        if not isinstance(url, str) or not isinstance(digest, str):
            raise ValueError(f"invalid source recipe: {name}")
        inputs[name] = {"url": url, "sha256": digest, "purpose": "runtime"}
    if SYSTEM == "windows":
        for name, (commit, digest) in PYTHON_WINDOWS_SOURCES.items():
            inputs[name] = {
                "url": f"https://codeload.github.com/python/cpython-source-deps/tar.gz/{commit}",
                "sha256": digest,
                "purpose": "runtime",
            }
    return inputs


def source_notice(archive: Path, member: str, destination: Path) -> None:
    """Recover the actual upstream notice without extracting any source executable."""
    with tarfile.open(archive) as packed:
        text = packed.extractfile(member)
        if text is None:
            raise ValueError(f"missing source notice: {member}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(text.read())


def install_python(work: Path, retained: Path) -> tuple[Path, dict[str, object]]:
    """Extract the pinned runtime and preserve its original metadata and declared notices.

    Open-source runtime inputs share one verified pool across platform artifacts.
    Microsoft's Windows runtime DLLs remain separately identified binary inputs.
    """
    target, options, digest = PYTHONS[f"{SYSTEM}-{MACHINE}"]
    name = f"cpython-{PYTHON}+{PBS_RELEASE}-{target}-{options}-full.tar.zst"
    url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{PBS_RELEASE}/{name}"
    packed = fetch(url, digest, work / "downloads", source=False)
    directory = work / "standalone"
    with tarfile.open(packed) as archive:
        archive.extractall(
            directory,
            members=(
                member
                for member in archive
                if member.name == "python/PYTHON.json"
                or member.name.startswith(("python/install/", "python/licenses/"))
            ),
            filter="data",
        )
    standalone = directory / "python"
    metadata = standalone / "PYTHON.json"
    info = json.loads(metadata.read_text(encoding="utf-8"))
    if (info["python_version"], info["target_triple"], info["build_options"]) != (
        PYTHON,
        target,
        options,
    ):
        raise ValueError("the pinned Python distribution has unexpected metadata")
    provenance = work / "python-inputs"
    provenance.mkdir()
    source_url = f"https://codeload.github.com/astral-sh/python-build-standalone/tar.gz/{PBS_COMMIT}"
    source = fetch(source_url, PBS_SOURCE_SHA256, work / "downloads")
    shutil.copyfile(source, provenance / "python-build-standalone.tar.gz")
    with tarfile.open(source) as archive:
        recipe_file = archive.extractfile(
            f"python-build-standalone-{PBS_COMMIT}/pythonbuild/downloads.json"
        )
        if recipe_file is None:
            raise ValueError("the Python build recipe is missing")
        recipe_bytes = recipe_file.read()
    (provenance / "downloads.json").write_bytes(recipe_bytes)
    recipe = json.loads(recipe_bytes)
    inputs = python_sources(recipe)
    # A common digest path merges identical platform contributions without copying
    # the interpreter binary or four copies of the common dependency sources.
    pool = retained.parent / "python"
    sources = {
        name: fetch(entry["url"], entry["sha256"], pool)
        for name, entry in inputs.items()
    }
    repairs = []
    notices = license_paths(info)
    if SYSTEM == "windows":
        # The prebuilt Tcl/Tk bundle's dependencies are absent from PYTHON.json.
        # Their DLLs are byte-identical to the ones in the pinned Tcl source tree.
        commit = PYTHON_WINDOWS_SOURCES["tcl"][0]
        for component, path in (
            ("zlib", "compat/zlib/LICENSE"),
            ("libtommath", "libtommath/LICENSE"),
        ):
            notice = f"licenses/LICENSE.{component}.txt"
            source_notice(
                sources["tcl"],
                f"cpython-source-deps-{commit}/{path}",
                standalone / notice,
            )
            notices.add(notice)
            repairs.append({"notice": notice, **inputs["tcl"]})
    for notice in sorted(notices):
        path = PurePosixPath(notice)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "licenses":
            raise ValueError(f"unsafe Python notice path: {notice}")
        original = standalone / notice
        if not original.is_file():
            # These two declared notices are absent in the pinned full archives.
            # Recover their actual text from the source inputs of that same build.
            component = {
                "LICENSE.zstd.txt": "zstd",
                "LICENSE.zlib-ng.txt": "zlib-ng",
            }.get(path.name)
            if component is None:
                raise ValueError(f"Python distribution omits declared notice: {notice}")
            entry = recipe[component]
            # Unix metadata declares zlib-ng even though the Unix build uses zlib.
            # Keep its notice source as provenance, separately from the runtime graph.
            dependency = sources.get(component)
            if dependency is None:
                dependency = fetch(entry["url"], entry["sha256"], pool)
                inputs[component] = {
                    "url": entry["url"],
                    "sha256": entry["sha256"],
                    "purpose": "declared notice",
                }
            filename = "LICENSE.md" if component == "zlib-ng" else "LICENSE"
            source_notice(
                dependency,
                f"cpython-source-deps-{component}-{entry['version']}/{filename}",
                original,
            )
            repairs.append(
                {"notice": notice, "url": entry["url"], "sha256": entry["sha256"]}
            )
        destination = provenance / notice
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
    shutil.copyfile(metadata, provenance / "PYTHON.json")
    shutil.copyfile(metadata, work / "PYTHON.json")
    notice_file = work / "LICENSE-PYTHON"
    with notice_file.open("wb") as output:
        for notice in sorted(notices):
            output.write(f"{notice}\n{'=' * len(notice)}\n".encode())
            output.write((provenance / notice).read_bytes())
            output.write(b"\n\n")
    # Notices also remain available when only the executable itself is copied.
    runtime = standalone / "install"
    included = runtime / "share/manimgx-python"
    included.mkdir(parents=True, exist_ok=True)
    for path in (metadata, notice_file):
        shutil.copyfile(path, included / path.name)
    retained.mkdir(parents=True, exist_ok=True)
    with tarfile.open(retained / "python-inputs.tar.xz", "w:xz") as archive:
        archive.add(provenance, arcname="python-inputs")
    return runtime, {
        "version": PYTHON,
        "release": PBS_RELEASE,
        "target": target,
        "url": url,
        "sha256": digest,
        "metadata_sha256": sha256(metadata),
        "build_recipe": {"url": source_url, "sha256": PBS_SOURCE_SHA256},
        "notice_repairs": repairs,
        "sources": inputs,
        "binary_runtime": info.get("crt_features", []),
        "inputs_sha256": sha256(retained / "python-inputs.tar.xz"),
    }


def install_manimgx(python: Path, wheel: Path, work: Path) -> None:
    """ManimGX, from its wheel, with its fonts (fonts/manimgx-fonts*, as this commit has
    them) and the dependencies uv.lock pins."""
    requirements = work / "requirements.txt"
    run(
        "uv", "export", "--frozen", "--package", "manimgx", "--no-default-groups",
        "--no-emit-workspace", "--output-file", requirements,
    )  # fmt: skip
    fonts = sorted((ROOT / "fonts").glob("manimgx-fonts*"))
    run(
        "uv", "pip", "install", "--python", python / INTERPRETER, "--break-system-packages",
        "--compile-bytecode", "--no-deps", "--require-hashes", "--requirements", requirements,
    )  # fmt: skip
    run(
        "uv", "pip", "install", "--python", python / INTERPRETER, "--break-system-packages",
        "--compile-bytecode", "--no-deps", wheel, *fonts,
    )  # fmt: skip
    # the Python is ManimGX's own: `manimgx self pip install` may add packages to it
    for marker in python.glob("**/EXTERNALLY-MANAGED"):
        marker.unlink()


def launcher_sources(work: Path) -> Path:
    """The exact launcher input, including its own complete locked Cargo graph."""
    url = f"https://static.crates.io/crates/pyapp/pyapp-{PYAPP}.crate"
    with tarfile.open(fetch(url, PYAPP_SHA256, work)) as archive:
        archive.extractall(work, filter="data")
    source = work / f"pyapp-{PYAPP}"
    config = source / ".cargo" / "config.toml"
    config.parent.mkdir(exist_ok=True)
    # Keep upstream target flags, including Windows' static C runtime.
    with config.open("a", encoding="utf-8") as output:
        output.write("\n")
        output.flush()
        subprocess.run(
            ["cargo", "vendor", "--locked", "vendor"],
            cwd=source,
            stdout=output,
            check=True,
        )
    return source


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def build_pyapp(distribution: Path, version: str, work: Path, source: Path) -> Path:
    """PyApp, built with the distribution inside it: it unpacks it and runs `manimgx`."""
    # the distribution itself runs ManimGX, installed in it already: no virtual environment,
    # no installation at runtime
    env = os.environ | {
        # Keep compiled output outside the source closure retained for the release.
        "CARGO_TARGET_DIR": str(work / "target"),
        "PYAPP_PROJECT_NAME": "manimgx",
        "PYAPP_PROJECT_VERSION": version,
        "PYAPP_PYTHON_VERSION": PYTHON.rsplit(".", 1)[0],
        "PYAPP_DISTRIBUTION_PATH": str(distribution),
        "PYAPP_DISTRIBUTION_PYTHON_PATH": INTERPRETER,
        "PYAPP_FULL_ISOLATION": "1",
        "PYAPP_SKIP_INSTALL": "1",
        "PYAPP_EXEC_SPEC": "manimgx.cli:main",
        "PYAPP_EXPOSE_PIP": "1",
        "PYAPP_EXPOSE_PYTHON": "1",
        "PYAPP_EXPOSE_CACHE": "1",
    }
    run(
        "cargo", "install", "--path", source, "--locked", "--offline", "--force",
        "--root", work / "pyapp", env=env, cwd=source,
    )  # fmt: skip
    binary = work / "pyapp" / "bin" / ("pyapp.exe" if WINDOWS else "pyapp")
    executable = work / ("manimgx.exe" if WINDOWS else "manimgx")
    binary.rename(executable)
    return executable


def smoke_test(executable: Path) -> None:
    """Render a scene with it (scripts/release/smoke_test.py), then delete what it unpacked."""
    run(sys.executable, ROOT / "scripts" / "release" / "smoke_test.py", executable)
    run(executable, "self", "remove")
    run(executable, "self", "cache", "dist", "--remove")


def main() -> None:
    wheel = the_wheel()
    version = wheel.name.split("-")[1]
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        retained = ROOT / "release-sources" / f"executable-{SYSTEM}-{MACHINE}"
        python, python_input = install_python(work, retained)
        install_manimgx(python, wheel, work)
        distribution = work / "python.tar.gz"
        with tarfile.open(distribution, "w:gz") as archive:
            for path in python.iterdir():
                archive.add(path, arcname=path.name)
        source = launcher_sources(work)
        # PyApp's build script copies the binary distribution into its source tree.
        # Retain the input before that generated payload is written.
        with tarfile.open(retained / "pyapp.tar.xz", "w:xz") as out:
            out.add(source, arcname="pyapp")
        executable = build_pyapp(distribution, version, work, source)
        target = next(
            line.removeprefix("host: ")
            for line in subprocess.check_output(
                ["rustc", "-vV"], text=True, encoding="utf-8"
            ).splitlines()
            if line.startswith("host: ")
        )
        notice = work / "LICENSE-PYAPP"
        run(
            sys.executable,
            ROOT / "scripts/release/licenses.py",
            "--crate",
            source,
            target,
            notice,
        )
        receipt = work / "build-inputs.json"
        receipt.write_text(
            json.dumps(
                {
                    "wheel": {"name": wheel.name, "sha256": sha256(wheel)},
                    "python": python_input,
                    "launcher": {
                        "version": PYAPP,
                        "url": f"https://static.crates.io/crates/pyapp/pyapp-{PYAPP}.crate",
                        "sha256": PYAPP_SHA256,
                        "lock_sha256": sha256(source / "Cargo.lock"),
                        "target": target,
                    },
                    "distribution_sha256": sha256(distribution),
                    "executable_sha256": sha256(executable),
                    "source_sha256": sha256(retained / "pyapp.tar.xz"),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (retained / "manifest.json").write_bytes(receipt.read_bytes())
        smoke_test(executable)
        # an archive keeps the file executable
        name = f"manimgx-{SYSTEM}-{MACHINE}"
        files = (
            executable,
            notice,
            receipt,
            work / "LICENSE-PYTHON",
            work / "PYTHON.json",
        )
        if WINDOWS:
            created = DIST / f"{name}.zip"
            with zipfile.ZipFile(created, "w", zipfile.ZIP_DEFLATED) as out:
                for path in files:
                    out.write(path, path.name)
        else:
            created = DIST / f"{name}.tar.gz"
            with tarfile.open(created, "w:gz") as out:
                for path in files:
                    out.add(path, arcname=path.name)
    print(f"created {created}")


def verify_sources(directory: Path) -> None:
    """Every executable retained its unchanged launcher sources and Python inputs."""
    for target in ("linux-x86_64", "linux-arm64", "macos-arm64", "windows-x86_64"):
        source = directory / f"executable-{target}"
        receipt = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        if (
            sha256(source / "python-inputs.tar.xz")
            != receipt["python"]["inputs_sha256"]
        ):
            raise ValueError(
                f"{target}: the executable's retained Python inputs changed"
            )
        for name, entry in receipt["python"]["sources"].items():
            if sha256(directory / "python" / entry["sha256"]) != entry["sha256"]:
                raise ValueError(f"{target}: retained Python source changed: {name}")
        if sha256(source / "pyapp.tar.xz") != receipt["source_sha256"]:
            raise ValueError(f"{target}: the executable's retained source changed")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--verify-sources"]:
        verify_sources(Path(sys.argv[2]))
    else:
        main()
