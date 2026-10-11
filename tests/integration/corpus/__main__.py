"""The corpus tool: render references, compare them, review them.

    python -m tests.integration.corpus render [CASE…] [--all | --stale] [--engine E] [-j N]
    python -m tests.integration.corpus compare [CASE…] [--all] [-j N]
    python -m tests.integration.corpus status [--list STATE…]
    python -m tests.integration.corpus review CASE VERDICT [--note TEXT]
    python -m tests.integration.corpus settings [--metric M] [--tolerance T]
    python -m tests.integration.corpus diff CASE [--frames N]
    python -m tests.integration.corpus types
    python -m tests.integration.corpus leaks

`render` rewrites a video only when its pixels change, and a `case.json` only when its facts
do: rendering an unchanged corpus changes no file. The review panel
(`python -m tests.integration.review`) does the same by hand.
"""

import argparse
import collections
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image
from tests.integration.corpus import baseline, engines, references, typecheck
from tests.integration.corpus.case import (
    ENGINES,
    METRICS,
    VERDICTS,
    Case,
    Engine,
    Facts,
    Failure,
    Settings,
    State,
    discover,
    save_settings,
    settings,
)
from tests.integration.corpus.frames import decode

DIFFS = Path(__file__).resolve().parents[1] / "_diffs"
STATES: tuple[State, ...] = (*VERDICTS, "stale", "unrendered")


def _verdict(facts: Facts, current: Settings) -> str:
    reasons = facts.reasons(current)
    worst = (
        f", worst {facts.comparison.worst(current.metric):.1f} {current.metric}"
        if facts.comparison is not None
        else ""
    )
    said = f" ({', '.join(reasons)})" if reasons else ""
    return f"{facts.verdict(current)}{said}{worst}"


def _select(names: list[str], every: bool, stale: bool = False) -> list[Case]:
    cases = discover()
    if names:
        known = {case.name: case for case in cases}
        unknown = [name for name in names if name not in known]
        if unknown:
            sys.exit(f"unknown case(s): {', '.join(unknown)}")
        return [known[name] for name in names]
    if stale:
        return [case for case in cases if not case.current(case.facts())]
    if every:
        return cases
    sys.exit("name the cases, or pass --all")


def _parallel(cases: list[Case], jobs: int, work: Callable[[Case], str]) -> int:
    """Run `work` on every case, a line per case as it finishes; how many raised."""
    failures = 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(work, case): case for case in cases}
        for n, future in enumerate(as_completed(futures), 1):
            case = futures[future]
            try:
                line = future.result()
            except Exception as error:
                failures += 1
                line = f"ERROR {type(error).__name__}: {error}"
            print(f"[{n}/{len(cases)}] {case.name}: {line}", flush=True)
    return failures


def status(listed: list[str]) -> None:
    current = settings()
    names: dict[str, list[str]] = collections.defaultdict(list)
    reasons: collections.Counter[str] = collections.Counter()
    reviewed = 0
    for case in discover():
        standing = case.standing(current)
        names[standing.state].append(case.name)
        reviewed += standing.reviewed
        if standing.facts is not None and standing.state == "not_matching":
            reasons.update(standing.facts.reasons(current))
    trusted = len(names["working"])
    print(f"{sum(map(len, names.values()))} cases, {trusted} trusted (working)")
    print(f"comparison: {current.metric} <= {current.tolerance}; {reviewed} reviewed")
    for state in STATES:
        print(f"  {state:13s} {len(names[state]):4d}")
    if reasons:
        print(
            "not matching: " + ", ".join(f"{k} {v}" for k, v in reasons.most_common())
        )
    for state in listed:
        print(f"\n{state}:")
        for name in names.get(state, []):
            print(f"  {name}")


def diff(case: Case, count: int) -> None:
    """Write the most different CE/manimgx pairs side by side, with their difference."""
    facts = case.facts()
    if facts is None or facts.comparison is None:
        sys.exit(f"{case.name}: nothing compared yet")
    column = METRICS.index(settings().metric)
    worst = sorted(facts.comparison.pairs, key=lambda p: -p[2][column])[:count]
    wanted_ce = {i for i, _, _ in worst}
    wanted_mx = {k for _, k, _ in worst}
    ce = {
        i: f
        for i, f in enumerate(decode(case.video("ce"), facts.size))
        if i in wanted_ce
    }
    mx = {
        k: f
        for k, f in enumerate(decode(case.video("manimgx"), facts.size))
        if k in wanted_mx
    }
    out = DIFFS / case.name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    width, height = facts.size
    for i, k, errors in worst:
        d = np.abs(ce[i].astype(np.int16) - mx[k].astype(np.int16)).max(axis=2)
        heat = np.stack([d, d, d], axis=2).clip(0, 255).astype(np.uint8)
        sheet = Image.new("RGB", (width * 3, height))
        for x, frame in enumerate((ce[i], mx[k], heat)):
            sheet.paste(Image.fromarray(frame), (x * width, 0))
        name = f"ce{i:04d}_manimgx{k:04d}_err{errors[column]:.0f}.png"
        sheet.save(out / name)
        print(out / name)


def leaks(cases: list[Case]) -> None:
    """Compare a sequence with fresh processes on this host: only preceding scenes differ."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sequence.json"

        def run(selected: list[Case]) -> dict[str, list[tuple[str, int]]]:
            if not selected:
                return {}
            subprocess.run(
                [sys.executable, "-m", "tests.integration.corpus.run_manimgx"]
                + [str(case.scene) for case in selected]
                + ["--out", str(out), "--sequence"],
                env=engines.environment(),
                timeout=engines.TIMEOUT["manimgx"] * len(selected),
                check=True,
            )
            return {
                name: [(str(h), int(n)) for h, n in runs]
                for name, runs in json.loads(out.read_text(encoding="utf-8")).items()
            }

        rendered = run(cases)
        leaked = [
            case.name for case in cases if rendered[case.name] != run([case])[case.name]
        ]
    print(f"{len(leaked)} of {len(cases)} scenes render differently after others:")
    for name in leaked:
        print(f"  {name}")


def types() -> None:
    cases = discover()
    report = typecheck.report(cases)
    failing = 0
    for case in cases:
        problems = report.problems(case)
        if problems:
            failing += 1
            print(f"{case.name}:")
            for line in problems:
                print(f"  {line}")
    print(
        f"\n{failing} of {len(cases)} scenes fail: {len(report.diagnostics)} with ty"
        f" diagnostics, {len(report.escapes)} with escapes, {len(report.imprecise)}"
        " with types manimgx leaves Any/Unknown"
    )


def baselines(args: argparse.Namespace) -> None:
    """Freeze artifact identities, stage promotions, or exercise the verified catalog."""
    if args.action == "freeze":
        generation = baseline.Generation(
            args.commit,
            baseline.runtime_lock(),
            baseline.fonts(),
            baseline.execution(),
            tuple(
                baseline.Artifact(Path(path).name, baseline.digest(Path(path)), url)
                for url, path in args.wheel
            ),
        )
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(asdict(generation), stream, indent=2)
            stream.write("\n")
        print(f"{generation.identity}: {args.output}")
        return
    catalog = (
        baseline.Catalog.load(args.catalog)
        if args.catalog.exists()
        else baseline.Catalog({}, {})
    )
    if args.action == "acquire":
        if not catalog.cases:
            sys.exit("no promoted baseline catalog")
        for generation in catalog.generations.values():
            generation.validate_runtime()
            print(generation.wheel().acquire(args.cache))
        return
    cases = _select(args.cases, args.all)
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        if args.action == "stage":
            if args.output.exists():
                raise FileExistsError(args.output)
            directory = args.output.with_suffix(".evidence")
            directory.mkdir()
            generation = baseline.Generation.read(
                json.loads(args.candidate.read_text(encoding="utf-8"))
            )
            promoted = baseline.promote(
                catalog, generation, cases, directory, args.cache
            )
            promoted.write(args.output)
            print(f"{len(cases)} movie-verified mappings staged in {args.output}")
        else:
            prepared = baseline.References(catalog, directory, args.cache)
            for case in cases:
                prepared.package(case)

            def work(case: Case) -> str:
                output = args.output / case.name
                result = prepared.compare(case, output)
                if isinstance(result.frames, Failure):
                    raise ValueError(result.frames.error)
                if result.differences:
                    changed = sum(d.repeat for d in result.differences)
                    raise ValueError(f"{changed} frames differ; see {output}")
                return "exact"

            sys.exit(1 if _parallel(cases, args.jobs, work) else 0)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tests.integration.corpus")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("render", help="render references, then compare them")
    p.add_argument("cases", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("--stale", action="store_true", help="unrendered or stale cases")
    p.add_argument("--engine", choices=("manimgx", "ce", "both"), default="both")
    p.add_argument("-j", "--jobs", type=int, default=8)
    p = commands.add_parser("compare", help="compare existing references again")
    p.add_argument("cases", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("-j", "--jobs", type=int, default=8)
    p = commands.add_parser("status", help="where every case stands")
    p.add_argument("--list", nargs="*", default=[], metavar="STATE")
    p = commands.add_parser("review", help="set a verdict (auto: the comparison's)")
    p.add_argument("case")
    p.add_argument("verdict", choices=("auto", *VERDICTS))
    p.add_argument("--note", default="")
    p = commands.add_parser("settings", help="the comparison's metric and tolerance")
    p.add_argument("--metric", choices=METRICS)
    p.add_argument("--tolerance", type=float)
    p = commands.add_parser("diff", help="write the most different pairs as images")
    p.add_argument("case")
    p.add_argument("--frames", type=int, default=5)
    commands.add_parser("types", help="the type report for every scene")
    commands.add_parser("leaks", help="scenes that render differently after others")
    p = commands.add_parser("baseline", help="verified frozen authoring baselines")
    actions = p.add_subparsers(dest="action", required=True)
    p = actions.add_parser("freeze", help="record immutable candidate wheel identities")
    p.add_argument("output", type=Path)
    p.add_argument("--commit", required=True)
    p.add_argument(
        "--wheel",
        nargs=2,
        action="append",
        required=True,
        metavar=("HTTPS_URL", "WHEEL"),
    )
    for action in ("stage", "check", "acquire"):
        p = actions.add_parser(action)
        p.add_argument("--catalog", type=Path, required=True)
        p.add_argument("--cache", type=Path, default=baseline.CACHE)
        if action == "stage":
            p.add_argument("candidate", type=Path)
            p.add_argument("output", type=Path)
        if action != "acquire":
            p.add_argument("cases", nargs="*")
            p.add_argument("--all", action="store_true")
        if action == "check":
            p.add_argument("--output", type=Path, default=DIFFS / "baseline")
            p.add_argument("-j", "--jobs", type=int, default=4)
    args = parser.parse_args()

    match args.command:
        case "baseline":
            baselines(args)
        case "render":
            wanted: set[Engine] = (
                set(ENGINES) if args.engine == "both" else {args.engine}
            )
            current = settings()

            def work(case: Case) -> str:
                facts, notes = references.render(case, wanted)
                return f"{notes}; {_verdict(facts, current)}"

            cases = _select(args.cases, args.all, args.stale)
            sys.exit(1 if _parallel(cases, args.jobs, work) else 0)
        case "compare":
            cases = _select(args.cases, args.all)
            sys.exit(1 if _parallel(cases, args.jobs, references.recompare) else 0)
        case "status":
            status(args.list)
        case "review":
            (case,) = _select([args.case], every=False)
            verdict = next((v for v in VERDICTS if v == args.verdict), None)
            review = case.write_review(verdict, args.note)
            reviewed = " (reviewed)" if review is not None else ""
            print(f"{case.name}: {case.state(settings())}{reviewed}")
        case "settings":
            current = settings()
            if args.metric is not None or args.tolerance is not None:
                tolerance = (
                    current.tolerance if args.tolerance is None else args.tolerance
                )
                current = Settings(args.metric or current.metric, tolerance)
                save_settings(current)
            print(f"{current.metric} <= {current.tolerance}")
        case "diff":
            (case,) = _select([args.case], every=False)
            diff(case, args.frames)
        case "types":
            types()
        case "leaks":
            leaks(discover())


if __name__ == "__main__":
    main()
