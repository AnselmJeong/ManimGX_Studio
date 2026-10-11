"""An image's pixels are the picture it shows: `pixel_array` is that picture, read-only,
however the image was made, recolored, copied or became another. Recoloring paints a
silhouette in the color, keeping each pixel's opacity unless it is given one; a copy recolors
apart from its original; and the array an image was made of stays the caller's: the image
holds a copy, which the array's changing later never reaches."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest

import manimgx as m

PICTURE = np.array([[[10, 20, 30, 41], [50, 60, 70, 83]]], dtype=np.uint8)
OTHER = np.full((2, 3, 4), 191, dtype=np.uint8)


@dataclass(frozen=True)
class Change:
    do: Callable[[m.ImageMobject], m.ImageMobject]
    source: np.ndarray  # the picture it shows
    color: m.ManimColor | None = None  # the silhouette's, once recolored
    alpha: float | None = None  # every pixel's opacity, once one was given


CHANGES = {
    "made": Change(lambda image: image, PICTURE),
    "recolored": Change(lambda image: image.set_color(m.BLUE), PICTURE, m.BLUE),
    "recolored, at an opacity": Change(
        lambda image: image.set_color(m.BLUE, alpha=0.5), PICTURE, m.BLUE, 0.5
    ),
    "recolored twice": Change(
        lambda image: image.set_color(m.BLUE, alpha=0.5).set_color(m.RED),
        PICTURE,
        m.RED,
        0.5,
    ),
    "become another": Change(lambda image: image.become(m.ImageMobject(OTHER)), OTHER),
    "become another, recolored": Change(
        lambda image: image.become(m.ImageMobject(OTHER)).set_color(m.BLUE),
        OTHER,
        m.BLUE,
    ),
    "copied, recolored": Change(
        lambda image: image.copy().set_color(m.GREEN, alpha=0.25),
        PICTURE,
        m.GREEN,
        0.25,
    ),
}


@pytest.mark.parametrize("name", sorted(CHANGES))
def test_an_images_pixels_are_the_picture_it_shows(name: str) -> None:
    change = CHANGES[name]
    pixels = PICTURE.copy()
    original = m.ImageMobject(pixels)
    image = change.do(original)
    shown = np.asarray(image.paint.texture)
    np.testing.assert_array_equal(image.pixel_array, shown)
    assert not image.pixel_array.flags.writeable
    expected = change.source.astype(int)
    if change.color is not None:
        expected[:, :, :3] = np.round(change.color.to_rgb() * 255)
    if change.alpha is not None:
        expected[:, :, 3] = round(255 * change.alpha)
    np.testing.assert_allclose(shown.astype(int), expected, atol=1)  # (to a level)
    if image is not original:  # (a copy recolors apart)
        np.testing.assert_array_equal(original.pixel_array, PICTURE)
    assert pixels.flags.writeable  # (the array it was made of stays the caller's)


TRIANGLE = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
GIVEN = ("an array", "a read-only view", "read-only, with a writable alias")


@pytest.mark.parametrize("size", [2, 8])
@pytest.mark.parametrize("given", GIVEN)
@pytest.mark.parametrize("meshed", [False, True], ids=["alone", "a mesh's texture too"])
def test_an_images_pixels_are_its_own(given: str, size: int, meshed: bool) -> None:
    owner = np.full((size, size, 4), 29, dtype=np.uint8)
    alias = owner.view()  # writable, whatever becomes of the rest
    pixels = owner.view() if given == "a read-only view" else owner
    if given != "an array":
        pixels.flags.writeable = False
    if meshed:  # (a mesh textured with them first)
        m.MeshMobject(TRIANGLE, np.array([[0, 1, 2]]), texture=pixels)
    image = m.ImageMobject(pixels)
    assert image.pixel_array is image.paint.texture
    assert not np.shares_memory(image.pixel_array, owner)
    alias[:] = 101
    again = m.ImageMobject(np.full_like(owner, 29))  # (the pixels as they were)
    for picture in (image, again):
        np.testing.assert_array_equal(picture.pixel_array, np.full_like(owner, 29))
