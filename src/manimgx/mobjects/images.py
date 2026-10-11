"Pictures on meshes: decoded pixels and live camera views."

from pathlib import Path
from typing import TYPE_CHECKING, Self, Unpack
from warnings import deprecated

import numpy as np

from manimgx.config import config
from manimgx.constants import DOWN, LEFT, RIGHT, UP, Resampling
from manimgx.drawing.paint import (
    WHITE,
    YELLOW_C,
    Fill,
    Look,
    ManimColor,
    ParsableManimColor,
    Style,
    _Style,
)
from manimgx.mobject import MeshMobject

__all__ = ["ImageMobject", "ImageMobjectFromCamera"]

if TYPE_CHECKING:
    from manimgx.mobjects.annotations import FrameOptions
    from manimgx.scene import Camera


class ImageMobject(MeshMobject):
    """A picture: an image file or an array of pixels, on a rectangle as tall as its
    pixels make it.

    An image `scale_to_resolution` pixels tall (1080 unless given) is as tall as the
    frame's short side (8 scene units by default), and any other in proportion. Shown
    larger than its pixels, the picture is reconstructed from them by
    `resampling_algorithm`: by default a smooth cubic through every pixel; linear blends
    neighboring pixels; nearest shows each pixel as a square of its color. Shown smaller,
    it is sampled, not averaged. The mobject's opacity multiplies its pixels' own.

    Args:
        filename_or_array: The picture: an image file's path, the file's contents
            (bytes), or an array of pixel values from 0 to 255: (h, w) gray, (h, w, 3)
            RGB or (h, w, 4) RGBA.
        scale_to_resolution: How many pixels tall an image as tall as the frame's
            short side is; 0 for an image 3 units tall, whatever its size.
        invert: Whether its colors are inverted (not its transparency).
        image_mode: The mode, as the Pillow library names them, a file is read in:
            "RGBA", or "L" for gray.
        resampling_algorithm: How the picture is reconstructed from its pixels, by the
            Pillow library's number: 0, nearest; 2, linear; 3, cubic (Keys' cubic
            convolution, Pillow's bicubic);
            [RESAMPLING_ALGORITHMS][manimgx.RESAMPLING_ALGORITHMS] gives them by name.
        stroke_width: The width of a border around the picture, in hundredths of a
            scene unit; 0 for none.
        stroke_color: The border's color.

    Examples:
        ```python
        import numpy as np

        import manimgx as m


        class ImageMobjectExample(m.Scene):
            def construct(self) -> None:
                ramp = np.linspace(0, 255, 256)
                pixels = np.zeros((256, 256, 3), dtype=np.uint8)
                pixels[..., 0] = ramp  # red grows to the right
                pixels[..., 2] = ramp[:, np.newaxis]  # blue grows downward
                image = m.ImageMobject(pixels, scale_to_resolution=400)
                self.play(m.FadeIn(image))
        ```

        ```python
        import numpy as np

        import manimgx as m


        class ImageMobjectResamplingExample(m.Scene):
            def construct(self) -> None:
                pixels = np.full((3, 3), 60, dtype=np.uint8)
                pixels[1, 1] = 255  # one white pixel, amid gray ones
                images = m.Group()
                for name in ("nearest", "linear", "cubic"):
                    image = m.ImageMobject(
                        pixels,
                        scale_to_resolution=6,
                        resampling_algorithm=m.RESAMPLING_ALGORITHMS[name],
                    )
                    images.add(m.Group(image, m.Text(name).next_to(image, m.DOWN)))
                self.add(images.arrange(buff=0.5))
        ```
    """

    # a textured quad, CE's four corners (UL, UR, DL, DR) its vertices; the opacity lives
    # in the paint, a multiplier
    def __init__(
        self,
        filename_or_array: str | Path | bytes | np.ndarray,
        scale_to_resolution: int = 1080,
        invert: bool = False,
        image_mode: str = "RGBA",
        resampling_algorithm: Resampling = 3,
        stroke_width: float = 0,  # a border's (the picture is the texture)
        stroke_color: ParsableManimColor = WHITE,
        **kwargs: Unpack[Look],
    ) -> None:
        import io

        from PIL import Image

        if isinstance(filename_or_array, (str, Path, bytes)):
            source = (
                io.BytesIO(filename_or_array)
                if isinstance(filename_or_array, bytes)
                else filename_or_array
            )
            pixels = np.array(Image.open(source).convert(image_mode))
        else:
            pixels = np.array(filename_or_array)
        pixels = _to_rgba(pixels)
        if invert:
            pixels[:, :, :3] = 255 - pixels[:, :, :3]
        pixels.flags.writeable = False
        self.scale_to_resolution = scale_to_resolution
        self.resampling_algorithm = resampling_algorithm
        super().__init__(
            np.array([UP + LEFT, UP + RIGHT, DOWN + LEFT, DOWN + RIGHT], dtype=float),
            np.array([[0, 1, 2], [1, 3, 2]]),
            uvs=np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float),
            texture=pixels,
            **kwargs,
        )
        if (
            stroke_width > 0
        ):  # a border is just a rectangle child that follows every transform
            from manimgx.mobjects.shapes import Polygon

            self.add(
                Polygon(
                    *self.points[[0, 1, 3, 2]],
                    stroke_width=stroke_width,
                    stroke_color=stroke_color,
                )
            )

    @property
    def pixel_array(self) -> np.ndarray:
        """The current picture's (h, w, 4) RGBA pixels, from 0 to 255.

        Pictures decoded or tinted by this image are read-only. Becoming another
        textured mesh adopts its texture, including whether it is writable.
        """
        texture = self.paint.texture
        assert isinstance(texture, np.ndarray)
        return texture

    def generate_points(self) -> Self:
        super().generate_points()
        self.center()
        texture = self._texture
        assert isinstance(texture, np.ndarray)
        h, w = texture.shape[:2]
        # an image `scale_to_resolution` pixels high spans the frame's short side
        short = min(config.frame_width, config.frame_height)
        height = h / self.scale_to_resolution * short if self.scale_to_resolution else 3
        return self.stretch_to_fit_height(height).stretch_to_fit_width(height * w / h)

    def set_color(  # pyright: ignore[reportIncompatibleMethodOverride]  # ty: ignore[invalid-method-override]  # CE's: an image's tint, then its alpha
        self,
        color: ParsableManimColor = YELLOW_C,
        alpha: float | None = None,
        family: bool = True,
    ) -> Self:
        """Paint every pixel `color`, keeping its opacity: the picture becomes a
        silhouette in that color.

        Args:
            alpha: Every pixel's opacity too, from 0 to 1; None keeps each one's.
            family: Accepted for Manim compatibility; ignored: the picture alone is
                painted.
        """
        pixels = self.pixel_array.copy()
        pixels[:, :, :3] = (ManimColor(color).to_rgb() * 255).astype(np.uint8)
        if alpha is not None:
            pixels[:, :, 3] = int(255 * alpha)
        pixels.flags.writeable = False
        self.paint = self.paint.but(texture=pixels)
        return self

    def set_opacity(
        self, opacity: float = 1.0, family: bool = True, *, alpha: float | None = None
    ) -> Self:
        """Set the picture's opacity, which multiplies its pixels' own.

        Args:
            opacity: The opacity, from 0 to 1.
            family: Whether its whole family is set (a border too), or the picture
                alone.
            alpha: The opacity, by the name Manim's images give it; given, it wins over
                `opacity`.
        """
        return super().set_opacity(opacity if alpha is None else alpha, family)

    def set_resampling_algorithm(self, resampling_algorithm: Resampling) -> Self:
        """Set how the picture is reconstructed from its pixels where it is shown larger
        than they are.

        Args:
            resampling_algorithm: The filter, by the Pillow library's number: 0, nearest
                (each pixel a square of its color); 2, linear; 3, cubic (smooth, and
                through every pixel);
                [RESAMPLING_ALGORITHMS][manimgx.RESAMPLING_ALGORITHMS] gives them by
                name.
        """
        self.resampling_algorithm = resampling_algorithm
        return self

    @deprecated("Manim CE's machinery: ManimGX calls it itself", category=None)
    def get_style(self) -> Fill:
        """The picture's style, as fill keywords: its color and its opacity.

        Returns:
            A dict of `fill_color` and `fill_opacity`.
        """
        return Fill(fill_color=self.get_color(), fill_opacity=self.get_fill_opacity())


def _to_rgba(pixels: np.ndarray) -> np.ndarray:
    if pixels.ndim == 2:
        pixels = np.stack([pixels] * 3, axis=-1)
    if pixels.shape[2] == 3:
        pixels = np.concatenate(
            [pixels, np.full((*pixels.shape[:2], 1), 255, dtype=pixels.dtype)], axis=2
        )
    return pixels.astype(np.uint8)


class ImageCameraOptions(_Style, total=False):
    """A camera picture's keywords, for the scenes that pass them on: a
    [ZoomedScene][manimgx.ZoomedScene]'s display.

    Beyond these, they take the [style keywords][manimgx.drawing.paint.Style].
    """

    default_display_frame_config: "FrameOptions | None"
    """[Surrounding rectangle
    keywords][manimgx.mobjects.annotations.FrameOptions] for the picture's
    outline, over a white outline 3 wide with no margin (default None)."""


@deprecated("Manim CE's machinery for ZoomedScene: use ZoomedScene", category=None)
class ImageMobjectFromCamera(MeshMobject):
    """What a camera sees, as a picture: a rectangle showing the camera's view, drawn
    anew every frame.

    The picture is 3 units tall, in the frame's proportions. Move the camera's
    [frame][manimgx.Camera.frame] to look elsewhere, scale it to zoom: the picture
    follows. The camera sees everything but this picture; a
    [ZoomedScene][manimgx.ZoomedScene] shows its zoomed camera's view with one.

    Args:
        camera: The camera whose view the picture shows.
        default_display_frame_config: [Surrounding rectangle
            keywords][manimgx.mobjects.annotations.FrameOptions] for the
            outline [add_display_frame][manimgx.ImageMobjectFromCamera.add_display_frame]
            draws, over a white outline 3 wide with no margin.

    Examples:
        ```python
        import manimgx as m


        class ImageMobjectFromCameraExample(m.Scene):
            def construct(self) -> None:
                square = m.Square(side_length=4, color=m.BLUE, fill_opacity=0.5)
                self.add(square.shift(2 * m.LEFT + 0.5 * m.DOWN))
                camera = m.Camera()
                frame = camera.frame.scale(0.25).move_to(square.get_corner(m.UL))
                frame.set_stroke(m.YELLOW, 3)
                picture = m.ImageMobjectFromCamera(camera).add_display_frame()
                self.add(frame, picture.to_corner(m.UR))
                self.play(frame.animate.move_to(square.get_corner(m.DR)), run_time=3)
        ```
    """

    # a quad textured with the camera's view (a camera's view is a texture)

    def __init__(
        self,
        camera: "Camera",
        default_display_frame_config: "FrameOptions | None" = None,
        **kwargs: Unpack[Style],
    ) -> None:
        self.camera = camera
        """The camera whose view the picture shows."""
        frame: FrameOptions = {"stroke_width": 3, "stroke_color": WHITE, "buff": 0}
        self.default_display_frame_config = frame | (default_display_frame_config or {})
        w = (
            1.5 * config.frame_width / config.frame_height
        )  # CE: 3 units high, the frame's aspect
        super().__init__(
            np.array(
                [[-w, 1.5, 0], [w, 1.5, 0], [-w, -1.5, 0], [w, -1.5, 0]], dtype=float
            ),
            np.array([[0, 1, 2], [1, 3, 2]]),
            uvs=np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float),
            texture=camera,
            **kwargs,
        )

    def add_display_frame(self, **kwargs: "Unpack[FrameOptions]") -> Self:
        """Outline the picture: a surrounding rectangle, added as a submobject.

        Args:
            **kwargs: [Surrounding rectangle
                keywords][manimgx.mobjects.annotations.FrameOptions], over
                `default_display_frame_config`.
        """
        from manimgx.mobjects.annotations import SurroundingRectangle

        self.display_frame = SurroundingRectangle(
            self, **(self.default_display_frame_config | kwargs)
        )
        return self.add(self.display_frame)
