"""A pending PyPI publisher identifies one project by its workflow and environment.
The release must route only that project's distributions to it, and publish the fonts
before anything that installs ManimGX from PyPI.
"""

import base64
import hashlib
import io
import json
import runpy
import subprocess
import tarfile
import tomllib
import zipfile
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TextIO

import pytest
import yaml
from scripts.release import create_executable, linux_sources, publish_npm, smoke_test

ROOT = Path(__file__).parents[1]
JOBS = yaml.safe_load(
    (ROOT / ".github/workflows/release.yaml").read_text(encoding="utf-8")
)["jobs"]
NPM = yaml.load(
    (ROOT / ".github/workflows/publish-npm.yaml").read_text(encoding="utf-8"),
    Loader=yaml.BaseLoader,
)


@pytest.mark.parametrize("autocrlf", ["false", "true", "input"])
def test_complete_source_exports_the_committed_project_without_checkout_artifacts(
    tmp_path: Path,
    autocrlf: str,
) -> None:
    checkout, output = tmp_path / "checkout", tmp_path / "source with spaces"
    checkout.mkdir()
    git = [
        "git",
        "-C",
        str(checkout),
        "-c",
        "user.name=Source test",
        "-c",
        "user.email=source@example.invalid",
    ]
    subprocess.run([*git, "init", "--quiet"], check=True, capture_output=True)
    subprocess.run(
        [*git, "config", "core.autocrlf", autocrlf], check=True, capture_output=True
    )
    inputs = {
        ".gitattributes": (ROOT / ".gitattributes").read_bytes(),
        "scripts/release/build_lavapipe.sh": b"#!/bin/sh\nexit 0\n",
        "scripts/release/llvm/regression.ll": b"; compiler regression\n",
        "browser/src/index.ts": b"export {}\n",
        "fonts/example/font.bin": b"\x00\xff\r\n",
        "justfile": b"build:\n    true\n",
    }
    for name, content in inputs.items():
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    subprocess.run([*git, "add", "."], check=True, capture_output=True)
    subprocess.run(
        [*git, "commit", "--quiet", "-m", "Source"], check=True, capture_output=True
    )
    revision = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    committed = {
        name: subprocess.check_output([*git, "show", f"HEAD:{name}"]) for name in inputs
    }
    assert committed == inputs
    # The same clean source may have different newline bytes in its working copy.
    recipe = checkout / "scripts/release/build_lavapipe.sh"
    recipe.write_bytes(
        inputs["scripts/release/build_lavapipe.sh"].replace(b"\n", b"\r\n")
    )
    (checkout / "untracked-binary").write_bytes(b"not source")
    command = [
        "just",
        "--justfile",
        str(ROOT / "justfile"),
        "--working-directory",
        str(checkout),
        "_source-tree",
        output.as_posix(),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert {
        p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()
    } == {
        *inputs,
        "SOURCE_COMMIT",
    }
    assert {name: (output / name).read_bytes() for name in inputs} == committed
    assert (output / "SOURCE_COMMIT").read_text(encoding="utf-8").strip() == revision
    (checkout / "justfile").write_bytes(b"uncommitted recipe\n")
    failed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert failed.returncode != 0
    assert "Commit tracked changes" in failed.stderr
    assert (output / "justfile").read_bytes() == inputs["justfile"]


def test_pending_publishers_have_distinct_environments() -> None:
    publishers = {"manimgx": JOBS["pypi"]["environment"]["name"]}
    fonts = JOBS["pypi-fonts"]
    assert fonts["environment"]["name"] == "${{ matrix.environment }}"
    for entry in fonts["strategy"]["matrix"]["include"]:
        assert entry["package"] not in publishers
        publishers[entry["package"]] = entry["environment"]

    # These are the identities registered on PyPI, including the first-release publishers.
    assert publishers == {
        "manimgx": "pypi",
        "manimgx-fonts": "pypi-fonts",
        "manimgx-fonts-cjk": "pypi-fonts-cjk",
    }
    assert len(set(publishers.values())) == len(publishers)


def test_wheel_jobs_expand_platform_in_the_same_shell_on_every_os() -> None:
    wheel = yaml.safe_load(
        (ROOT / ".github/workflows/create-wheels.yaml").read_text(encoding="utf-8")
    )["jobs"]["wheel"]
    assert wheel["defaults"]["run"]["shell"] == "bash"
    build = next(step for step in wheel["steps"] if "PLATFORM" in step.get("env", {}))
    assert "${PLATFORM}" in build["run"]


def test_native_and_embedded_browser_builds_require_the_committed_cargo_lock() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["maturin"]["locked"] is True
    build = (ROOT / "rust/engine/build.rs").read_text(encoding="utf-8")
    assert '.args(["build", "--locked",' in build


@pytest.mark.parametrize("package", ["manimgx-fonts", "manimgx-fonts-cjk"])
def test_font_artifacts_contain_only_their_own_package(
    package: str, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    expected = set()
    for manifest in sorted((ROOT / "fonts").glob("*/pyproject.toml")):
        project = tomllib.loads(manifest.read_text(encoding="utf-8"))["project"]
        name = project["name"].replace("-", "_")
        version = project["version"]
        for suffix in [".tar.gz", "-py3-none-any.whl"]:
            filename = f"{name}-{version}{suffix}"
            (dist / filename).touch()
            if project["name"] == package:
                expected.add(filename)

    upload = next(
        step["with"]
        for step in JOBS["sdist"]["steps"]
        if step.get("with", {}).get("name") == package
    )
    assert expected
    assert {path.name for path in tmp_path.glob(upload["path"])} == expected

    download = next(
        step["with"]
        for step in JOBS["pypi-fonts"]["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert download["name"] == "${{ matrix.package }}"


def _wheel_artifacts(workflow: str, dimension: str) -> dict[str, str]:
    job = yaml.safe_load(
        (ROOT / f".github/workflows/{workflow}.yaml").read_text(encoding="utf-8")
    )["jobs"]["wheel"]
    upload = next(
        step["with"]
        for step in job["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
        and step["with"]["path"] == "dist/*.whl"
    )
    matrix = job["strategy"]["matrix"]
    values = (
        [entry[dimension] for entry in matrix["include"]]
        if "include" in matrix
        else matrix[dimension]
    )
    return {
        value: upload["name"].replace(f"${{{{ matrix.{dimension} }}}}", value)
        for value in values
    }


def _selected_artifacts(pattern: str, artifacts: set[str]) -> set[str]:
    # These action selectors use brace alternatives over artifact names, not filenames.
    return {
        artifact
        for artifact in artifacts
        if any(
            fnmatchcase(artifact, choice) for choice in pattern.strip("{}").split(",")
        )
    }


@pytest.mark.parametrize(
    ("job", "other"),
    [
        ("pypi", {"sdist"}),
        ("draft-release", {"sdist", "source", "executable-linux-x86_64", "npm"}),
    ],
)
def test_release_publishers_exclude_test_wheels(job: str, other: set[str]) -> None:
    download = next(
        step["with"]
        for step in JOBS[job]["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    wheels = set(_wheel_artifacts("create-wheels", "platform").values())
    test_wheels = set(_wheel_artifacts("test", "os").values())
    assert wheels.isdisjoint(test_wheels)
    # A tag calls both producers in one run. Manual release dry runs omit Test.
    artifacts = (
        wheels
        | test_wheels
        | {
            "sdist",
            "source",
            "manimgx-fonts",
            "manimgx-fonts-cjk",
            "executable-linux-x86_64",
            "npm",
        }
    )
    assert _selected_artifacts(download["pattern"], artifacts) == wheels | other


@pytest.mark.parametrize(
    ("workflow", "job", "dimension"),
    [
        ("create-executables", "executable", "platform"),
        ("release", "docker-build", "wheel"),
    ],
)
def test_platform_consumers_use_their_release_wheel(
    workflow: str, job: str, dimension: str
) -> None:
    consumer = yaml.safe_load(
        (ROOT / f".github/workflows/{workflow}.yaml").read_text(encoding="utf-8")
    )["jobs"][job]
    download = next(
        step["with"]
        for step in consumer["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    wheels = _wheel_artifacts("create-wheels", "platform")
    artifacts = set(wheels.values()) | set(_wheel_artifacts("test", "os").values())
    for entry in consumer["strategy"]["matrix"]["include"]:
        value = entry[dimension]
        selector = download.get("name", download.get("pattern")).replace(
            f"${{{{ matrix.{dimension} }}}}", value
        )
        platform = f"linux-{value}" if job == "docker-build" else value
        assert _selected_artifacts(selector, artifacts) == {wheels[platform]}


def test_consumers_wait_for_the_font_packages() -> None:
    assert "pypi-fonts" in JOBS["pypi"]["needs"]
    for job in ["npm", "publish"]:
        assert "pypi" in JOBS[job]["needs"]


def test_every_artifact_is_built_before_public_source_and_registry_uploads() -> None:
    def ancestors(name: str) -> set[str]:
        needs = JOBS[name].get("needs", [])
        parents = {needs} if isinstance(needs, str) else set(needs)
        return parents | {parent for item in parents for parent in ancestors(item)}

    builds = {"test", "wheels", "sdist", "executables", "npm-build", "docker-build"}
    assert builds <= ancestors("github-release")
    for publisher in ["pypi-fonts", "pypi", "npm", "docker"]:
        assert "github-release" in ancestors(publisher)
    public_source = "\n".join(
        step.get("run", "") for step in JOBS["github-release"]["steps"]
    )
    assert "--draft=false" in public_source


def test_registry_uploads_use_built_artifacts_without_rebuilding() -> None:
    npm = NPM["jobs"]["publish"]["steps"]
    command = "\n".join(step.get("run", "") for step in npm)
    assert 'gh release download --repo "$GITHUB_REPOSITORY"' in command
    assert '--pattern "manimgx-${TAG#v}.tgz" -- "$TAG"' in command
    assert not any(build in command for build in ["build-npm", "npm pack", "bun run"])
    docker = JOBS["docker"]["steps"]
    assert any(step.get("with", {}).get("pattern") == "docker-*" for step in docker)
    command = "\n".join(step.get("run", "") for step in docker)
    assert "skopeo copy --all --preserve-digests" in command
    assert "docker buildx build" not in command
    image = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    release = image.split("FROM runtime AS release", 1)[1].split(
        "FROM runtime AS published", 1
    )[0]
    assert "--require-hashes --requirements /wheels/requirements.txt" in release
    assert "--no-deps /wheels/*.whl" in release


def test_npm_release_and_manual_recovery_share_the_publisher() -> None:
    assert JOBS["npm"]["uses"] == "$/.github/workflows/publish-npm.yaml"
    assert JOBS["npm"]["with"] == {"tag": "${{ github.ref_name }}"}
    for event in ["workflow_call", "workflow_dispatch"]:
        tag = NPM["on"][event]["inputs"]["tag"]
        assert tag["required"] == "true"
        assert tag["type"] == "string"
    publisher = NPM["jobs"]["publish"]
    assert publisher["if"] == (
        "github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main'"
    )
    assert publisher["environment"]["name"] == "npm"


def test_npm_publication_authenticates_the_release_before_uploading() -> None:
    steps = NPM["jobs"]["publish"]["steps"]
    acquire = next(
        step for step in steps if "gh attestation verify" in step.get("run", "")
    )
    assert acquire["env"]["TAG"] == "${{ inputs.tag }}"
    source = acquire["run"]
    assert '--json isDraft --jq .isDraft -- "$TAG")" = false' in source
    assert (
        'commit="$(gh api "repos/$GITHUB_REPOSITORY/commits/$TAG" --jq .sha)"' in source
    )
    assert (
        '--signer-workflow "$GITHUB_REPOSITORY/.github/workflows/release.yaml"'
        in source
    )
    assert '--source-ref "refs/tags/$TAG" --source-digest "$commit"' in source
    assert (
        'curl --fail --silent --show-error "https://pypi.org/pypi/manimgx/${TAG#v}/json"'
        in source
    )
    assert "jq -e '.urls | any(.filename | endswith(\"_wasm32.whl\"))'" in source
    command = "\n".join(step.get("run", "") for step in steps)
    positions = [
        command.index(gate)
        for gate in [
            "gh release view",
            "gh release download",
            "commit=",
            "gh attestation verify",
            "https://pypi.org/pypi/manimgx/",
            "python3 scripts/release/publish_npm.py dist/*.tgz",
        ]
    ]
    assert positions == sorted(positions)


@pytest.mark.parametrize("state", ["new", "identical", "different", "unauthorized"])
@pytest.mark.parametrize("relative", [False, True], ids=["absolute", "relative"])
def test_npm_retry_requires_the_exact_tarball(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, relative: bool
) -> None:
    archive = tmp_path / "dist" / "package.tgz"
    archive.parent.mkdir()
    monkeypatch.chdir(tmp_path)
    argument = archive.relative_to(tmp_path) if relative else archive
    with tarfile.open(archive, "w:gz") as package:
        body = json.dumps({"name": "manimgx", "version": "0.1.0"}).encode()
        member = tarfile.TarInfo("package/package.json")
        member.size = len(body)
        package.addfile(member, io.BytesIO(body))
    integrity = (
        "sha512-"
        + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    )
    uploaded = []

    def run(command: list[str], **_options: object) -> subprocess.CompletedProcess[str]:
        if command[1] == "publish":
            assert Path(command[2]).is_absolute(), "npm must receive a local file path"
            uploaded.append(Path(command[2]).read_bytes())
            return subprocess.CompletedProcess(command, 0, "", "")
        assert command == ["npm", "view", "manimgx@0.1.0", "dist.integrity", "--json"]
        if state == "new" and not uploaded:
            return subprocess.CompletedProcess(
                command, 1, '{"error":{"code":"E404"}}', ""
            )
        if state == "unauthorized":
            return subprocess.CompletedProcess(
                command, 1, '{"error":{"code":"E401"}}', ""
            )
        return subprocess.CompletedProcess(
            command, 0, json.dumps("other" if state == "different" else integrity), ""
        )

    monkeypatch.setattr(subprocess, "run", run)
    if state == "different":
        with pytest.raises(ValueError, match="different artifact bytes"):
            publish_npm.publish(argument)
    elif state == "unauthorized":
        with pytest.raises(RuntimeError, match="cannot inspect"):
            publish_npm.publish(argument)
    else:
        publish_npm.publish(argument)
    assert uploaded == ([archive.read_bytes()] if state == "new" else [])


@pytest.mark.parametrize("outcome", ["visible", "timeout", "unauthorized", "different"])
def test_npm_waits_for_visibility_after_one_accepted_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    archive = tmp_path / "package.tgz"
    with tarfile.open(archive, "w:gz") as package:
        body = b'{"name":"manimgx","version":"0.1.0"}'
        member = tarfile.TarInfo("package/package.json")
        member.size = len(body)
        package.addfile(member, io.BytesIO(body))
    integrity = (
        "sha512-"
        + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    )
    now = 0.0
    uploads = []
    inspections = []

    def sleep(seconds: float) -> None:
        nonlocal now
        assert 0 < seconds <= 5
        now += seconds

    def run(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        if command[1] == "publish":
            uploads.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        if not uploads:
            return subprocess.CompletedProcess(
                command, 1, '{"error":{"code":"E404"}}', ""
            )
        inspections.append((now, options.get("timeout")))
        if outcome == "timeout" or (outcome == "visible" and len(inspections) < 3):
            return subprocess.CompletedProcess(
                command, 1, '{"error":{"code":"E404"}}', ""
            )
        if outcome == "unauthorized":
            return subprocess.CompletedProcess(
                command, 1, '{"error":{"code":"E401"}}', ""
            )
        return subprocess.CompletedProcess(
            command, 0, json.dumps("other" if outcome == "different" else integrity), ""
        )

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(publish_npm, "monotonic", lambda: now)
    monkeypatch.setattr(publish_npm, "sleep", sleep)
    if outcome == "timeout":
        with pytest.raises(TimeoutError, match="not available"):
            publish_npm.publish(archive)
        assert now == 300
    elif outcome == "unauthorized":
        with pytest.raises(RuntimeError, match="cannot inspect"):
            publish_npm.publish(archive)
        assert now == 0
    elif outcome == "different":
        with pytest.raises(ValueError, match="different artifact bytes"):
            publish_npm.publish(archive)
        assert now == 0
    else:
        publish_npm.publish(archive)
        assert now == 10
    assert len(uploads) == 1
    assert inspections
    assert all(timeout == 300 - instant for instant, timeout in inspections)


def test_release_smoke_records_decoded_audio_and_a_complete_versioned_take(
    tmp_path: Path,
) -> None:
    assert (ROOT / "rust/ffmpeg/tests/silence.opus").read_bytes() == smoke_test.OPUS
    # Docker and installed-wheel tests carry this script alone, outside the source tree.
    script = tmp_path / "smoke_test.py"
    script.write_bytes(Path(smoke_test.__file__).read_bytes())
    relocated = runpy.run_path(str(script))
    scene: dict[str, object] = {}
    exec(relocated["scene_source"](), scene)
    chunks: list[bytes] = []
    film = scene["Smoke"]().render(take=chunks.append)  # ty: ignore[call-non-callable]
    take = b"".join(chunks)
    smoke_test.validate_take(take, film.frame_count)
    # A nonempty/truncated/failed take used to pass the artifact smoke gate.
    for bad in [take[:-6], take[:-1], take[:-1] + b"\x01"]:
        with pytest.raises((AssertionError, ValueError)):
            smoke_test.validate_take(bad, film.frame_count)


@pytest.mark.parametrize("known", [0, 1, 2])
def test_linux_source_inventory_covers_every_library_that_was_bundled(
    tmp_path: Path, known: int
) -> None:
    wheel = tmp_path / "wheel.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in ["libone.so", "libtwo.so"]:
            archive.writestr(f"manimgx.libs/{name}", b"library")
        archive.writestr(
            "manimgx.dist-info/sboms/auditwheel.cdx.json",
            json.dumps(
                {
                    "components": [{"name": "manimgx"}]
                    + [
                        {
                            "name": name,
                            "version": "1.0-2.el8",
                            "purl": f"pkg:rpm/almalinux/{name}@1.0-2.el8",
                        }
                        for name in ["one", "two"][:known]
                    ]
                }
            ),
        )
    if known < 2:
        with pytest.raises(ValueError, match="every bundled library"):
            linux_sources.bundled_packages(wheel)
    else:
        assert linux_sources.bundled_packages(wheel) == {
            "one-1.0-2.el8",
            "two-1.0-2.el8",
        }


def test_source_archive_waits_for_the_platform_builds_that_choose_its_sources() -> None:
    assert set(JOBS["sdist"]["needs"]) == {"wheels", "executables"}
    download = next(
        step["with"]
        for step in JOBS["sdist"]["steps"]
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    assert download["pattern"] == "sources-*"


def test_executable_sources_reject_missing_and_changed_platform_archives(
    tmp_path: Path,
) -> None:
    pool = tmp_path / "python"
    pool.mkdir()
    shared = pool / "input"
    shared.write_bytes(b"actual common interpreter source")
    digest = create_executable.sha256(shared)
    shared = shared.rename(pool / digest)
    for platform in ("linux-x86_64", "linux-arm64", "macos-arm64", "windows-x86_64"):
        source = tmp_path / f"executable-{platform}"
        source.mkdir()
        archive = source / "pyapp.tar.xz"
        archive.write_bytes(b"the actual launcher sources and locked dependencies")
        (source / "python-inputs.tar.xz").write_bytes(archive.read_bytes())
        (source / "manifest.json").write_text(
            json.dumps(
                {
                    "source_sha256": create_executable.sha256(archive),
                    "python": {
                        "inputs_sha256": create_executable.sha256(archive),
                        "sources": {"cpython": {"sha256": digest}},
                    },
                }
            ),
            encoding="utf-8",
        )
        if platform != "windows-x86_64":
            with pytest.raises(FileNotFoundError):
                create_executable.verify_sources(tmp_path)
    create_executable.verify_sources(tmp_path)
    shared.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="retained Python source changed"):
        create_executable.verify_sources(tmp_path)
    shared.write_bytes(b"actual common interpreter source")
    python_inputs = source / "python-inputs.tar.xz"
    original = python_inputs.read_bytes()
    python_inputs.write_bytes(b"changed Python provenance")
    with pytest.raises(ValueError, match="retained Python inputs changed"):
        create_executable.verify_sources(tmp_path)
    python_inputs.write_bytes(original)
    archive.write_bytes(b"other sources")
    with pytest.raises(ValueError, match="retained source changed"):
        create_executable.verify_sources(tmp_path)


def test_launcher_build_keeps_compiled_output_out_of_its_source_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "Cargo.lock").write_text("locked sources", encoding="utf-8")

    def install(
        *command: str | Path,
        env: dict[str, str] | None = None,
        cwd: Path = ROOT,
    ) -> None:
        assert cwd == source
        assert env is not None
        target = Path(env["CARGO_TARGET_DIR"])
        assert not target.is_relative_to(source)
        assert env["PYAPP_PYTHON_VERSION"] == "3.14"
        assert "--offline" in command
        assert "--locked" in command
        target.mkdir()
        (target / "compiled.o").write_bytes(b"not source")
        binary = (
            tmp_path
            / "pyapp/bin"
            / ("pyapp.exe" if create_executable.WINDOWS else "pyapp")
        )
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"the built launcher")

    monkeypatch.setattr(create_executable, "run", install)
    executable = create_executable.build_pyapp(
        tmp_path / "python.tar.gz", "0.1.0", tmp_path, source
    )
    assert executable.read_bytes() == b"the built launcher"
    archive = tmp_path / "source.tar.xz"
    with tarfile.open(archive, "w:xz") as output:
        output.add(source, arcname="pyapp")
    with tarfile.open(archive) as packed:
        assert packed.getnames() == ["pyapp", "pyapp/Cargo.lock"]


def test_launcher_vendoring_preserves_upstream_target_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = tmp_path / "upstream"
    (upstream / ".cargo").mkdir(parents=True)
    original = '[target.windows]\nrustflags = ["-C", "target-feature=+crt-static"]\n'
    (upstream / ".cargo/config.toml").write_text(original, encoding="utf-8")

    def download(*_args: object, **_kwargs: object) -> Path:
        with tarfile.open(tmp_path / create_executable.PYAPP_SHA256, "w:gz") as out:
            out.add(upstream, arcname=f"pyapp-{create_executable.PYAPP}")
        return tmp_path / create_executable.PYAPP_SHA256

    def vendor(command: list[str], *, cwd: Path, stdout: TextIO, check: bool) -> None:
        assert command == ["cargo", "vendor", "--locked", "vendor"]
        assert check
        assert (
            (cwd / ".cargo/config.toml")
            .read_text(encoding="utf-8")
            .startswith(original)
        )
        stdout.write('[source.crates-io]\nreplace-with = "vendored-sources"\n')

    monkeypatch.setattr(create_executable, "fetch", download)
    monkeypatch.setattr(create_executable.subprocess, "run", vendor)
    source = create_executable.launcher_sources(tmp_path)
    config = tomllib.loads((source / ".cargo/config.toml").read_text(encoding="utf-8"))
    assert config["target"]["windows"]["rustflags"] == [
        "-C",
        "target-feature=+crt-static",
    ]
    assert config["source"]["crates-io"]["replace-with"] == "vendored-sources"


def test_source_archive_rejects_missing_platforms_and_changed_sources(
    tmp_path: Path,
) -> None:
    for machine in ["x86_64", "aarch64"]:
        directory = tmp_path / f"linux-{machine}"
        directory.mkdir()
        source = directory / "library-1.0.src.rpm"
        source.write_bytes(b"the verified source")
        (directory / "manifest.json").write_text(
            json.dumps(
                {
                    "packages": [
                        {
                            "source": source.name,
                            "sha256": linux_sources.digest(source),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        if machine == "x86_64":
            with pytest.raises(FileNotFoundError):
                linux_sources.verify(tmp_path)
    linux_sources.verify(tmp_path)
    source.write_bytes(b"a different source")
    with pytest.raises(ValueError, match="retained source changed"):
        linux_sources.verify(tmp_path)


def test_a_wheel_without_bundled_distribution_libraries_has_no_source_rpms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "wheel.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("manimgx/__init__.py", "")
    monkeypatch.setattr(
        linux_sources.platform, "freedesktop_os_release", lambda: {"ID": "almalinux"}
    )
    for machine in ["x86_64", "aarch64"]:
        monkeypatch.setattr(
            linux_sources.platform, "machine", lambda machine=machine: machine
        )
        linux_sources.collect(wheel, tmp_path)
        manifest = json.loads(
            (tmp_path / f"linux-{machine}" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert manifest["packages"] == []
        assert manifest["sha256"] == linux_sources.digest(wheel)
    linux_sources.verify(tmp_path)


@pytest.mark.parametrize("fault", ["", "version", "signature"])
def test_only_the_installed_librarys_verified_source_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    source = "libdrm-2.4.115-1.el8.src.rpm"
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(b"the wheel")
    monkeypatch.setattr(
        linux_sources, "bundled_packages", lambda _: {"libdrm-2.4.115-1.el8"}
    )
    monkeypatch.setattr(linux_sources.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(
        linux_sources.platform, "freedesktop_os_release", lambda: {"ID": "almalinux"}
    )

    def output(*args: str) -> str:
        if "--checksig" in args:
            return "digests OK" if fault == "signature" else "digests signatures OK"
        assert args[-1] == "libdrm-2.4.115-1.el8"
        return f"libdrm 1 2.4.115 1.el8 aarch64 {source}"

    def download(
        command: list[str], *, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert check
        assert command[-1] == source.removesuffix(".rpm")
        filename = "libdrm-2.4.116.src.rpm" if fault == "version" else source
        (Path(command[-2]) / filename).write_bytes(b"the exact source RPM")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(linux_sources, "output", output)
    monkeypatch.setattr(linux_sources.subprocess, "run", download)
    store = tmp_path / "sources"
    if fault:
        with pytest.raises(
            ValueError, match=r"installed package's source|verified signature"
        ):
            linux_sources.collect(wheel, store)
        assert not list(store.rglob("*.rpm"))
        assert not list(store.rglob("manifest.json"))
    else:
        linux_sources.collect(wheel, store)
        archive = store / "linux-aarch64" / source
        manifest = json.loads(
            archive.with_name("manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["sha256"] == linux_sources.digest(wheel)
        assert manifest["packages"] == [
            {
                "binary": "libdrm-1:2.4.115-1.el8.aarch64",
                "source": source,
                "sha256": linux_sources.digest(archive),
            }
        ]


@pytest.mark.parametrize("target", create_executable.PYTHONS)
@pytest.mark.parametrize("failure", ["", "metadata", "notice", "unsafe"])
def test_standalone_python_retains_exact_input_metadata_and_every_declared_notice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, failure: str
) -> None:
    system, machine = target.split("-", 1)
    monkeypatch.setattr(create_executable, "SYSTEM", system)
    monkeypatch.setattr(create_executable, "MACHINE", machine)
    triple, options, digest = create_executable.PYTHONS[target]
    metadata = {
        "python_version": create_executable.PYTHON,
        "target_triple": triple,
        "build_options": options,
        "license_path": "licenses/LICENSE.cpython.txt",
        "build_info": {
            "extensions": {
                "_zstd": [
                    {
                        "license_paths": ["licenses/LICENSE.zstd.txt"],
                    }
                ]
            }
        },
    }
    if failure == "metadata":
        metadata["python_version"] = "3.14.0"
    elif failure == "notice":
        metadata["license_path"] = "licenses/LICENSE.missing.txt"
    elif failure == "unsafe":
        metadata["license_path"] = "../outside"
    original = json.dumps(metadata).encode()
    downloads = tmp_path / "fixtures"
    downloads.mkdir()

    def pack(name: str, files: dict[str, bytes]) -> Path:
        result = downloads / name
        with tarfile.open(result, "w:gz") as archive:
            for path, data in files.items():
                member = tarfile.TarInfo(path)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return result

    dependency = pack(
        "zstd", {"cpython-source-deps-zstd-1.5.7/LICENSE": b"actual zstd notice"}
    )
    recipe = {
        "zstd": {
            "version": "1.5.7",
            "url": "https://source.invalid/zstd",
            "sha256": "zstd",
        }
    }
    tcl_commit, tcl_sha = create_executable.PYTHON_WINDOWS_SOURCES["tcl"]
    tcl = pack(
        "tcl",
        {
            f"cpython-source-deps-{tcl_commit}/compat/zlib/LICENSE": b"actual Tcl zlib notice",
            f"cpython-source-deps-{tcl_commit}/libtommath/LICENSE": b"actual Tommath notice",
        },
    )
    source_inputs = {"zstd": {"url": recipe["zstd"]["url"], "sha256": "zstd"}}
    if system == "windows":
        source_inputs["tcl"] = {"url": "https://source.invalid/tcl", "sha256": tcl_sha}
    monkeypatch.setattr(
        create_executable, "python_sources", lambda _recipe: source_inputs
    )
    archives = {
        tcl_sha: tcl,
        digest: pack(
            "runtime",
            {
                "python/PYTHON.json": original,
                "python/install/bin/python3": b"runtime",
                "python/licenses/LICENSE.cpython.txt": b"actual Python notice",
                "python/build/compiled.o": b"not source, not runtime",
            },
        ),
        create_executable.PBS_SOURCE_SHA256: pack(
            "recipe",
            {
                f"python-build-standalone-{create_executable.PBS_COMMIT}/pythonbuild/downloads.json": json.dumps(
                    recipe
                ).encode(),
            },
        ),
        "zstd": dependency,
    }

    def fetch(url: str, sha: str, directory: Path, *, source: bool = True) -> Path:
        assert source == (sha != digest)
        if not source:
            assert (
                f"{create_executable.PYTHON}+{create_executable.PBS_RELEASE}-{triple}-{options}"
                in url
            )
        directory.mkdir(parents=True, exist_ok=True)
        result = directory / sha
        result.write_bytes(archives[sha].read_bytes())
        return result

    monkeypatch.setattr(create_executable, "fetch", fetch)
    retained = tmp_path / "retained"
    if failure:
        with pytest.raises(
            ValueError,
            match={
                "metadata": "unexpected metadata",
                "notice": "omits declared notice",
                "unsafe": "unsafe Python notice path",
            }[failure],
        ):
            create_executable.install_python(tmp_path, retained)
        assert not (retained / "python-inputs.tar.xz").exists()
        return
    runtime, receipt = create_executable.install_python(tmp_path, retained)
    assert (runtime / "bin/python3").read_bytes() == b"runtime"
    assert not (runtime.parent / "build").exists()
    assert (runtime / "share/manimgx-python/PYTHON.json").read_bytes() == original
    assert (tmp_path / "PYTHON.json").read_bytes() == original
    notice = (tmp_path / "LICENSE-PYTHON").read_bytes()
    assert b"actual Python notice" in notice
    assert b"actual zstd notice" in notice
    assert receipt["sha256"] == digest
    assert (tmp_path / "python/zstd").read_bytes() == dependency.read_bytes()
    assert not (tmp_path / "python" / digest).exists()
    if system == "windows":
        assert b"actual Tcl zlib notice" in notice
        assert b"actual Tommath notice" in notice
    with tarfile.open(retained / "python-inputs.tar.xz") as archive:
        assert "python-inputs/python-build-standalone.tar.gz" in archive.getnames()
        assert "python-inputs/zstd.tar.gz" not in archive.getnames()
        assert not any(
            "install/" in name or "compiled.o" in name for name in archive.getnames()
        )


def test_python_binary_acquisition_is_verified_and_never_retained_as_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MANIMGX_SOURCES", str(tmp_path / "sources"))
    downloaded = tmp_path / "download"
    downloaded.write_bytes(b"verified input")
    digest = create_executable.sha256(downloaded)

    def run(
        *command: str | Path, env: dict[str, str] | None = None, cwd: Path = ROOT
    ) -> None:
        assert env is not None
        assert "MANIMGX_SOURCES" not in env
        assert command[-2:] == ("https://example.invalid/input", digest)
        (tmp_path / digest).write_bytes(downloaded.read_bytes())

    monkeypatch.setattr(create_executable, "run", run)
    assert (
        create_executable.fetch(
            "https://example.invalid/input", digest, tmp_path, source=False
        ).read_bytes()
        == b"verified input"
    )
    downloaded.write_bytes(b"changed input")
    with pytest.raises(ValueError, match="download changed"):
        create_executable.fetch(
            "https://example.invalid/input", digest, tmp_path, source=False
        )


def test_executable_installs_authenticated_dependencies_before_local_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str | Path, ...]] = []
    monkeypatch.setattr(create_executable, "run", lambda *args: calls.append(args))
    runtime, wheel = tmp_path / "python", tmp_path / "product.whl"
    create_executable.install_manimgx(runtime, wheel, tmp_path)
    export, dependencies, product = calls
    assert export[:2] == ("uv", "export")
    assert "--no-hashes" not in export
    assert "--no-emit-workspace" in export
    assert "--require-hashes" in dependencies
    assert "--no-deps" in dependencies
    assert "--requirements" in dependencies
    assert wheel not in dependencies
    assert "--no-deps" in product
    assert "--requirements" not in product
    assert product[-3:] == (
        wheel,
        ROOT / "fonts/manimgx-fonts",
        ROOT / "fonts/manimgx-fonts-cjk",
    )


@pytest.mark.parametrize("changed", [False, True])
def test_uv_hash_gate_rejects_changed_dependency_bytes_before_installation(
    tmp_path: Path, changed: bool
) -> None:
    wheel = tmp_path / "audited_dependency-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("audited_dependency.py", "value = 'verified'\n")
        archive.writestr(
            "audited_dependency-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: audited-dependency\nVersion: 1.0\n",
        )
        archive.writestr(
            "audited_dependency-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("audited_dependency-1.0.dist-info/RECORD", "")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if changed:
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.writestr("unexpected.py", "value = 'changed'\n")
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        f"audited-dependency @ {wheel.as_uri()} --hash=sha256:{digest}\n",
        encoding="utf-8",
    )
    target = tmp_path / "installed"
    result = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--target",
            str(target),
            "--no-index",
            "--no-deps",
            "--require-hashes",
            "--requirements",
            str(requirements),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) != changed, result.stdout + result.stderr
    assert (target / "audited_dependency.py").exists() != changed
    if changed:
        assert "Hash mismatch" in result.stderr


@pytest.mark.parametrize("system", ["linux", "macos", "windows"])
def test_python_sources_follow_the_build_graph_not_alternative_license_entries(
    monkeypatch: pytest.MonkeyPatch, system: str
) -> None:
    monkeypatch.setattr(create_executable, "SYSTEM", system)
    keys = set(
        create_executable.PYTHON_COMMON_SOURCES
        + create_executable.PYTHON_UNIX_SOURCES
        + create_executable.PYTHON_LINUX_SOURCES
    ) | {"zlib-ng", "openssl-1.1"}
    recipe = {
        name: {"url": f"https://source.invalid/{name}", "sha256": name} for name in keys
    }
    sources = create_executable.python_sources(recipe)
    assert ("bdb" in sources) == (system == "linux")
    assert "openssl-1.1" not in sources
    assert "openssl-3.5" in sources
    assert ("zlib-ng" in sources) == (system == "windows")
    assert ("zlib" in sources) == (system == "linux")
    if system == "windows":
        assert sources["libffi"]["sha256"] != recipe["libffi"]["sha256"]
        assert "/16fad4855b3d8c03b5910e405ff3a04395b39a98" in sources["libffi"]["url"]
        assert "/53c758cbf2cc178b359abc03fdd912c5e66ed74f" in sources["tcl"]["url"]
        assert "/a6a5bee1ef4b526b0d11200c84bc02e85d8ecc83" in sources["tk"]["url"]
    else:
        assert sources["libffi"]["sha256"] == recipe["libffi"]["sha256"]
