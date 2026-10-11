"""The classic example films execute through the same loader the Gallery uses."""

from pathlib import Path

import pytest
from docs import examples

from manimgx.rendering.film import Frame

FILMS = (
    "circle_area",
    "colliding_blocks",
    "complex_maps",
    "derivative",
    "euler_identity",
    "fourier_pi",
    "galton_board",
    "hilbert_curve",
    "linear_maps",
    "lorenz_attractor",
    "prime_spirals",
    "pythagoras",
    "quadratic_formula",
    "riemann_sums",
    "surface_plots",
    "taylor_series",
    "times_tables",
    "unit_circle",
)
ROOT = Path(__file__).parents[2]


@pytest.mark.config(pixel_width=160, pixel_height=90, frame_rate=2)
@pytest.mark.parametrize("name", FILMS)
def test_classic_film_renders_to_the_end(name: str) -> None:
    code = (ROOT / "examples" / f"{name}.py").read_text(encoding="utf-8")
    scene = examples.load(examples.Example(code, f"examples/{name}.py"))
    samples: set[bytes] = set()

    def keep(frame: Frame) -> None:
        pixels = frame.pixels()  # draw every frame, including the final holds
        if len(samples) < 2:
            samples.add(pixels)

    scene().render(frames=keep)
    assert len(samples) == 2, f"{name} never changed its rendered image"
