"""Compare the frozen authoring package and today's wheel on the same host.

    python -m tests.integration.corpus.frozen_probe OUTPUT [CASE...] \
        --wheel WHEEL --sha256 SHA --lock FROZEN_UV_LOCK

Diagnostic only: canonical movies, case facts and human reviews are never changed. Both
packages use the ordinary corpus runner in fresh processes. The candidate compares every RGB
pixel against a transient lossless reference and still passes the product's MP4 count check.
"""

import argparse
import concurrent.futures
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from tests.integration.corpus import baseline
from tests.integration.corpus.case import (
    ROOT,
    Case,
    Failure,
    Json,
    discover,
)
from tests.integration.corpus.frozen import dependencies, prepare
from tests.integration.corpus.probe import _metadata


def compare(
    case: Case, package: Path, output: Path, *, negative: bool = False
) -> dict[str, Json]:
    """Exercise the production comparison, optionally with a deliberate source mutation."""
    output.mkdir(parents=True, exist_ok=True)
    source = None
    if negative:
        original = case.scene.read_bytes()
        changed = original.replace(
            b"def construct(self):\n",
            b"def construct(self):\n        self.camera.background_color = m.PINK\n",
            1,
        )
        if changed == original:
            raise ValueError("the negative source control did not edit its fixture")
        source = output / "source.py"
        source.write_bytes(changed)
    started = time.monotonic()
    result = baseline.compare(case, package, output, source=source)
    if isinstance(result.frames, Failure):
        return {"case": case.name, "status": "error", "error": result.frames.error}
    return {
        "case": case.name,
        "status": "different" if result.differences else "exact",
        "source": result.source,
        "source_override": negative,
        "adapter": dict[str, Json](result.adapter or {}),
        "frames": result.frames.count,
        "duration": str(result.duration),
        "changed_frames": sum(d.repeat for d in result.differences),
        "mismatches": [asdict(d) for d in result.differences],
        "seconds": time.monotonic() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("cases", nargs="*")
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--negative-source", action="store_true")
    parser.add_argument("--expect-different", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.jobs <= 4:
        parser.error("use between one and four independent case comparisons")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    known = {case.name: case for case in discover()}
    names = args.cases or list(known)
    if missing := set(names) - known.keys():
        parser.error(f"unknown cases: {sorted(missing)}")
    if args.negative_source and names != ["basic_usage"]:
        parser.error("the negative source control requires basic_usage alone")
    lock = dependencies(args.lock, ROOT / "uv.lock")
    package = prepare(args.wheel, args.sha256, out / "reference-wheel")
    _metadata(out)
    (out / "reference.json").write_text(
        json.dumps({"wheel": args.sha256, "dependency_lock": lock}), encoding="utf-8"
    )
    results: dict[str, Json] = {}

    def run(name: str) -> tuple[str, dict[str, Json]]:
        result = compare(
            known[name], package, out / name, negative=args.negative_source
        )
        (out / name / "result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return name, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for name, result in pool.map(run, names):
            results[name] = result
            (out / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )
            print(f"{len(results)}/{len(names)} {name}: {result['status']}", flush=True)
    wanted = "different" if args.negative_source or args.expect_different else "exact"
    sys.exit(
        any(
            isinstance(result, dict) and result.get("status") != wanted
            for result in results.values()
        )
    )


if __name__ == "__main__":
    main()
