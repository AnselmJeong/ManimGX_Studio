# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2015 The Android Open Source Project
# SPDX-License-Identifier: Apache-2.0
# Modified by Academa, Inc.

# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy"]
# ///
"""Write the DFG table the engine lights with (rust/engine/src/dfg.bin): the split-sum terms of the GGX specular lobe
with height-correlated Smith visibility, 128 x 128, NoV across (x) and perceptual roughness down (y), at the texels'
centres, each texel two half floats: x = the integral of Fc V (Fc = (1 - VoH)^5), y = the integral of V, by 1024
Hammersley samples of the GGX distribution. A surface's specular albedo is mix(x, y, f0), and its single scattering
keeps y of a white conductor's light (the rest the energy compensation gives back).

    uv run scripts/engine/dfg_table.py
"""

from pathlib import Path

import numpy as np

SIZE = 128
SAMPLES = 1024
OUT = Path(__file__).resolve().parents[2] / "rust" / "engine" / "src" / "dfg.bin"


def hammersley(n: int) -> tuple[np.ndarray, np.ndarray]:
    i = np.arange(n, dtype=np.uint32)
    bits = i.copy()
    bits = (bits << 16) | (bits >> 16)
    bits = ((bits & 0x55555555) << 1) | ((bits & 0xAAAAAAAA) >> 1)
    bits = ((bits & 0x33333333) << 2) | ((bits & 0xCCCCCCCC) >> 2)
    bits = ((bits & 0x0F0F0F0F) << 4) | ((bits & 0xF0F0F0F0) >> 4)
    bits = ((bits & 0x00FF00FF) << 8) | ((bits & 0xFF00FF00) >> 8)
    return i / n, bits.astype(np.float64) * 2.3283064365386963e-10


def row(perceptual: float, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The table's row at a perceptual roughness: (x, y) for each NoV."""
    a = perceptual * perceptual
    a2 = a * a
    no_v = ((np.arange(SIZE) + 0.5) / SIZE)[:, None]
    view = np.stack([np.sqrt(1 - no_v**2), np.zeros_like(no_v), no_v])  # 3 x SIZE x 1
    phi = 2 * np.pi * u
    cos_t = np.sqrt((1 - v) / (1 + (a2 - 1) * v))
    sin_t = np.sqrt(1 - cos_t**2)
    half = np.stack([sin_t * np.cos(phi), sin_t * np.sin(phi), cos_t])[
        :, None, :
    ]  # 3 x 1 x SAMPLES
    vo_h = (view * half).sum(axis=0)
    light = 2 * vo_h * half - view
    no_l = np.clip(light[2], 0, 1)
    no_h = np.clip(half[2], 0, 1)
    vo_h = np.clip(vo_h, 0, 1)
    ggx_l = no_v * np.sqrt((no_l - no_l * a2) * no_l + a2)
    ggx_v = no_l * np.sqrt((no_v - no_v * a2) * no_v + a2)
    with np.errstate(divide="ignore", invalid="ignore"):
        vis = np.where(no_l > 0, 0.5 / (ggx_v + ggx_l) * no_l * (vo_h / no_h), 0.0)
    fc = (1 - vo_h) ** 5
    return np.stack([(vis * fc).sum(axis=1), vis.sum(axis=1)], axis=1) * 4 / SAMPLES


def main() -> None:
    u, v = hammersley(SAMPLES)
    table = np.stack(
        [row((y + 0.5) / SIZE, u, v) for y in range(SIZE)]
    )  # SIZE x SIZE x 2
    OUT.write_bytes(table.astype("<f2").tobytes())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    for pr in (0.25, 0.5, 0.75, 1.0):
        y = min(int(pr * SIZE), SIZE - 1)
        print(
            f"  roughness {pr}: at NoV 1 x {table[y, -1, 0]:.4f} y"
            f" {table[y, -1, 1]:.4f}"
        )


if __name__ == "__main__":
    main()
