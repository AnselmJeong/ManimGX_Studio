"""The README's static chart: total render times for the five-scene suite.

    uv run --frozen python -m benchmarks.chart

Reads `results.json` and writes `docs/content/images/benchmark-light.svg`
and `benchmark-dark.svg`. Every label and bar uses the recorded total in seconds,
from process launch to finished MP4. No normalization or animation is applied.
"""

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
IMAGES = HERE.parent / "docs" / "content" / "images"
LABELS = {
    "manimgx": "ManimGX",
    "manim_ce": "ManimCE",
    "manimgl": "ManimGL",
    "blender_workbench": "Blender (Workbench)",
    "blender_eevee": "Blender (EEVEE)",
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
THEMES = {
    "light": {
        "background": "#ffffff",
        "text": "#1f2328",
        "muted": "#59636e",
        "grid": "#d1d9e0",
        "bar": "#b8c0ca",
    },
    "dark": {
        "background": "#0b0c0f",
        "text": "#f0f6fc",
        "muted": "#9198a1",
        "grid": "#3d444d",
        "bar": "#4d5561",
    },
}
WIDTH, LEFT, RIGHT, TOP, ROW, BAR = 880, 180, 92, 44, 44, 22


def measured_rows(totals: dict[str, float]) -> list[tuple[str, float]]:
    """Label and sort the recorded totals without changing their units."""
    return sorted(
        ((LABELS[tool], seconds) for tool, seconds in totals.items()),
        key=lambda row: row[1],
    )


def chart(rows: list[tuple[str, float]], theme: dict[str, str]) -> str:
    """Static bars, fastest first, on a shared linear scale in seconds."""
    slowest = max(seconds for _, seconds in rows)
    magnitude = 10 ** math.floor(math.log10(slowest / 7))
    step = next(
        factor * magnitude
        for factor in (1, 2, 5, 10)
        if factor * magnitude >= slowest / 7
    )
    ticks = math.ceil(slowest / step)
    limit = ticks * step
    span = WIDTH - LEFT - RIGHT

    def x(seconds: float) -> float:
        """Where a time is on the chart."""
        return LEFT + span * seconds / limit

    height = TOP + ROW * len(rows) + 34
    parts = [
        f'<rect width="{WIDTH}" height="{height}" fill="{theme["background"]}"/>',
        f'<text x="{LEFT}" y="18" fill="{theme["muted"]}" font-size="13">'
        "Total render time (seconds)</text>",
    ]
    bottom = TOP + ROW * len(rows)
    for tick in range(ticks + 1):
        at = x(tick * step)
        parts.append(
            f'<line x1="{at:.1f}" y1="{TOP - 6}" x2="{at:.1f}" y2="{bottom}"'
            f' stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        label = f"{tick * step:g}s"
        parts.append(
            f'<text x="{at:.1f}" y="{bottom + 22}" fill="{theme["muted"]}"'
            f' font-size="13" text-anchor="middle">{label}</text>'
        )
    for i, (name, seconds) in enumerate(rows):
        y = TOP + ROW * i + (ROW - BAR) / 2
        ours = name == LABELS["manimgx"]
        weight = ' font-weight="700"' if ours else ""
        fill = "url(#manimgx)" if ours else theme["bar"]
        width = x(seconds) - LEFT
        parts.append(
            f'<text x="{LEFT - 16}" y="{y + BAR / 2 + 5:.1f}" fill="{theme["text"]}"'
            f' text-anchor="end"{weight}>{name}</text>'
        )
        parts.append(
            f'<rect id="b{i}" x="{LEFT}" y="{y:.1f}" width="{width:.3f}"'
            f' height="{BAR}" rx="4" fill="{fill}"/>'
        )
        parts.append(
            f'<text id="t{i}" x="{LEFT + width + 10:.1f}"'
            f' y="{y + BAR / 2 + 5:.1f}"'
            f' fill="{theme["text"] if ours else theme["muted"]}"{weight}>'
            f"{seconds:.2f} s</text>"
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}"'
        f' viewBox="0 0 {WIDTH} {height}" font-family="{FONT}" font-size="15">'
        "<title>Five-scene benchmark: total render times in seconds</title>"
        '<defs><linearGradient id="manimgx" x1="0" x2="1">'
        '<stop offset="0" stop-color="#58c4dd"/><stop offset="0.5"'
        ' stop-color="#5cd0b3"/>'
        '<stop offset="1" stop-color="#f7d96f"/></linearGradient></defs>'
        + "".join(parts)
        + "</svg>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw static render-time charts.")
    parser.add_argument("--results", type=Path, default=HERE / "results.json")
    parser.add_argument("--out", type=Path, default=IMAGES)
    args = parser.parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    if not results.get("complete") or set(results["totals"]) != set(LABELS):
        parser.error("The chart requires complete results for all five engines")
    if set(results["settings"]["scenes"]) != {
        "orbit",
        "matrix",
        "pendulums",
        "hierarchy",
        "linked_rings",
    }:
        parser.error("The chart requires all five scenes")
    args.out.mkdir(parents=True, exist_ok=True)
    rows = measured_rows(results["totals"])
    for name, theme in THEMES.items():
        path = args.out / f"benchmark-{name}.svg"
        path.write_text(chart(rows, theme), encoding="utf-8")
        print(f"{path}: {path.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
