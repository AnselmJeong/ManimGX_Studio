"""Array aliases, by rank: a point is 1-D, an array of points 2-D (numpy types the rank, not the 3)."""

from collections.abc import Callable, Sequence
from os import PathLike
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from manimgx.mobjects.text import Typst

type Float = np.float64
type Vec = np.ndarray[tuple[int], np.dtype[np.float64]]  # 1-D
type Rows = np.ndarray[tuple[int, int], np.dtype[np.float64]]  # 2-D
type Point3D = Vec
type Point3D_Array = Rows
type Vector3D = Vec
# an input: any array of floats (as CE's docs pass a tracker's `points`), a tuple or a sequence
type Point3DLike = (
    npt.NDArray[np.floating] | tuple[float, float, float] | Sequence[float]
)
type Vector3DLike = Point3DLike
type Point3DLike_Array = Point3D_Array | Sequence[Point3DLike]
type RGBA_Array = Rows
type MatrixMN = Rows
type RateFunc = Callable[[float], float]
type PathFunc = Callable[[Point3D_Array, Point3D_Array, float], Point3D_Array]
type PointsFunc = Callable[[Point3D_Array], Point3D_Array]
type Point2D = Vec
type Point2DLike = Point2D | tuple[float, float] | Sequence[float]
type Vector2D = Point2D
type Vector2DLike = Point2DLike
type Vector3D_Array = Point3D_Array
type ManimFloat = np.float64
type ManimTextLabel = Typst  # every text class typesets through Typst
type MappingFunction = Callable[[Point3D], Point3D]  # a point to a point (CE)
type StrPath = str | PathLike[str]
type Point2D_Array = Point3D_Array
type Point2DLike_Array = Point3DLike_Array
type PointND = Point3D
type PointND_Array = Point3D_Array
type FloatRGB = Vec
type FloatRGB_Array = Rows
type FloatRGBA_Array = RGBA_Array
type QuadraticSpline = Point3D_Array
