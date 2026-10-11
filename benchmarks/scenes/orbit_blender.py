"""A surface plot on 3D axes, a curve drawn across it with a ball riding its tip, and the
camera circling the whole time: every frame is new. (Blender, run headless:
`blender -b --factory-startup -P orbit_blender.py -- --engine EEVEE|WORKBENCH --out FILE`.)

Built the way Manim draws it: the axes' units (7 wide for x and y from -3 to 3, 4 tall for
z from -2 to 2), a 48 x 48 checkerboard surface, the curve drawn by its bevel's end, the
ball keyed along the curve, and Manim's camera: 20 units from the origin, a frame 8 units
tall there, at phi = 65 degrees, theta = -45 degrees + 0.3 rad/s.
"""

import argparse
import math
import sys

import bpy
import numpy as np

FPS, SECONDS, DRAW = 60, 10, 6  # the curve is drawn over the first six seconds
YELLOW, BLUE_D, BLUE_E, AXES = "#F7D96F", "#29ABCA", "#236B8E", "#FFFFFF"
# scene units per axis unit, as ThreeDAxes(x_length=7, z_length=4) has them
X, Z = 7 / 6, 1.0


def c2p(u: np.ndarray, v: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Axis coordinates to scene points."""
    return np.stack([X * u, X * v, Z * w], -1)


def material(name: str, color: str) -> bpy.types.Material:
    """A plain material of a color given in hex (sRGB)."""
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear, 1)  # Workbench's color
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        *linear,
        1,
    )
    return mat


def surface() -> bpy.types.Object:
    """The 48 x 48 checkerboard surface z = sin(u) cos(v), as one mesh."""
    n = 48
    u, v = np.meshgrid(
        np.linspace(-3, 3, n + 1), np.linspace(-3, 3, n + 1), indexing="ij"
    )
    points = c2p(u, v, np.sin(u) * np.cos(v)).reshape(-1, 3)
    i, j = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    corner = (i * (n + 1) + j).ravel()
    quads = np.stack([corner, corner + n + 1, corner + n + 2, corner + 1], -1)
    mesh = bpy.data.meshes.new("surface")
    mesh.from_pydata(points.tolist(), [], quads.tolist())
    mesh.polygons.foreach_set("material_index", ((i + j) % 2).ravel().astype(np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(n * n, bool))
    mesh.materials.append(material("blue_d", BLUE_D))
    mesh.materials.append(material("blue_e", BLUE_E))
    obj = bpy.data.objects.new("surface", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def axes() -> None:
    """Three thin shafts with cone tips, from -3 to 3 (x, y) and -2 to 2 (z)."""
    white = material("axes", AXES)
    for axis, (low, high) in enumerate(
        [(-3 * X, 3 * X), (-3 * X, 3 * X), (-2 * Z, 2 * Z)]
    ):
        rotation = [(0, math.pi / 2, 0), (-math.pi / 2, 0, 0), (0, 0, 0)][axis]
        center = [0.0, 0.0, 0.0]
        center[axis] = (low + high) / 2
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.01,
            depth=high - low,
            location=center,
            rotation=rotation,
            vertices=12,
        )
        bpy.context.object.data.materials.append(white)
        tip = [0.0, 0.0, 0.0]
        tip[axis] = high
        bpy.ops.mesh.primitive_cone_add(
            radius1=0.06, depth=0.18, location=tip, rotation=rotation, vertices=16
        )
        bpy.context.object.data.materials.append(white)


def curve_points(count: int = 629) -> np.ndarray:
    """The curve across the surface, as Manim samples it (t from 0 to 2 pi, step 0.01)."""
    t = np.linspace(0, 2 * np.pi, count)
    r = 2.4
    return c2p(
        r * np.cos(t),
        r * np.sin(t),
        np.sin(r * np.cos(t)) * np.cos(r * np.sin(t)) + 0.08,
    )


def curve(points: np.ndarray) -> None:
    """The yellow curve, drawn by animating the end of its bevel over the first six
    seconds (a stroke 6 wide in Manim is 0.06 units: a tube of radius 0.03)."""
    data = bpy.data.curves.new("curve", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth, data.bevel_resolution = 0.03, 2
    data.bevel_factor_mapping_end = "SPLINE"
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    spline.points.foreach_set(
        "co", np.hstack([points, np.ones((len(points), 1))]).ravel()
    )
    data.materials.append(material("yellow", YELLOW))
    obj = bpy.data.objects.new("curve", data)
    bpy.context.collection.objects.link(obj)
    data.bevel_factor_end = 0
    data.keyframe_insert("bevel_factor_end", frame=1)
    data.bevel_factor_end = 1
    data.keyframe_insert("bevel_factor_end", frame=1 + DRAW * FPS)


def ball(points: np.ndarray) -> None:
    """The ball, keyed at the drawn tip of the curve on every frame of the drawing."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, segments=24, ring_count=12)
    obj = bpy.context.object
    obj.data.materials.append(bpy.data.materials["yellow"])
    lengths = np.concatenate(
        [[0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    )
    for frame in range(DRAW * FPS + 1):
        at = frame / (DRAW * FPS) * lengths[-1]
        obj.location = [np.interp(at, lengths, points[:, k]) for k in range(3)]
        obj.keyframe_insert("location", frame=1 + frame)


def camera() -> None:
    """Manim's camera: 20 units from the origin, 8 units of frame height there, at
    phi = 65 degrees, orbiting from theta = -45 degrees at 0.3 rad/s."""
    pivot = bpy.data.objects.new("pivot", None)
    bpy.context.collection.objects.link(pivot)
    data = bpy.data.cameras.new("camera")
    data.sensor_fit = "VERTICAL"
    data.angle = 2 * math.atan(4 / 20)
    data.clip_end = 100
    cam = bpy.data.objects.new("camera", data)
    bpy.context.collection.objects.link(cam)
    phi, theta = math.radians(65), math.radians(-45)
    cam.location = (
        20 * math.sin(phi) * math.cos(theta),
        20 * math.sin(phi) * math.sin(theta),
        20 * math.cos(phi),
    )
    track = cam.constraints.new("TRACK_TO")
    track.target, track.track_axis, track.up_axis = pivot, "TRACK_NEGATIVE_Z", "UP_Y"
    cam.parent = pivot
    pivot.rotation_euler = (0, 0, 0)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1)
    pivot.rotation_euler = (0, 0, 0.3 * SECONDS)
    pivot.keyframe_insert("rotation_euler", index=2, frame=1 + SECONDS * FPS)
    bpy.context.scene.camera = cam


def light() -> None:
    """A sun from above the camera's side, and a dim world, for shading in EEVEE."""
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (math.radians(40), 0, math.radians(-30))
    bpy.context.collection.objects.link(sun)


def output(engine: str, path: str) -> None:
    """1920 x 1080 at 60 fps, 600 frames, straight to an H.264 MP4 with Blender's
    settings for it; black background and the Standard view (colors as sRGB)."""
    scene = bpy.context.scene
    scene.render.engine = {"EEVEE": "BLENDER_EEVEE", "WORKBENCH": "BLENDER_WORKBENCH"}[
        engine
    ]
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, SECONDS * FPS
    scene.view_settings.view_transform = "Standard"
    scene.world = scene.world or bpy.data.worlds.new("world")
    scene.world.color = (0, 0, 0)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0,
        0,
        0,
        1,
    )
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    settings = scene.render.image_settings
    settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "CUSTOM"
    scene.render.ffmpeg.custom_constant_rate_factor = 23
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    scene.render.filepath = path
    scene.render.use_file_extension = False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=["EEVEE", "WORKBENCH"], default="EEVEE")
    parser.add_argument("--out", default="orbit.mp4")
    parser.add_argument("--frames", type=int, default=SECONDS * FPS)  # fewer, to try it
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    points = curve_points()
    surface()
    axes()
    curve(points)
    ball(points)
    camera()
    light()
    output(args.engine, args.out)
    bpy.context.scene.frame_end = args.frames
    bpy.ops.render.render(animation=True)


main()
