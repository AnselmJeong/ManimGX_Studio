"""Blender geometry utilities and orbiting planets."""

import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from suite_data import (
    COLORS,
    FPS,
    HEIGHT,
    SECONDS,
    WIDTH,
    moon_position,
    planet_position,
)


def material(color):
    if color in bpy.data.materials:
        return bpy.data.materials[color]
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    rgb = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    result = bpy.data.materials.new(color)
    result.diffuse_color = (*rgb, 1)
    result.use_nodes = True
    result.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        *rgb,
        1,
    )
    result.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.45
    return result


def finish(color, smooth=False):
    obj = bpy.context.object
    obj.data.materials.append(material(color))
    if smooth:
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def sphere(radius, color, resolution=(16, 8)):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=resolution[0], ring_count=resolution[1], radius=radius
    )
    return finish(color, True)


def line(points, color, width=4):
    data = bpy.data.curves.new("stroke", "CURVE")
    data.dimensions = "3D"
    data.bevel_depth, data.bevel_resolution = (width * 0.005, 1)
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    obj = bpy.data.objects.new("stroke", data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material(color))
    update_line(obj, points)
    return obj


def update_line(obj, points):
    points = np.asarray(points)
    obj.data.splines[0].points.foreach_set(
        "co", np.column_stack([points, np.ones(len(points))]).ravel()
    )


def make_scene(name):
    updates = []
    sphere(0.65, COLORS[3])
    for i in range(5):
        planet, moon = (sphere(0.28, COLORS[i]), sphere(0.1, "#DDDDDD", (8, 4)))
        updates.extend(
            [
                lambda t, obj=planet, i=i: setattr(
                    obj, "location", planet_position(i, t)
                ),
                lambda t, obj=moon, i=i: setattr(obj, "location", moon_position(i, t)),
            ]
        )
    return updates


def setup(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = {"workbench": "BLENDER_WORKBENCH", "eevee": "BLENDER_EEVEE"}[
        args.engine
    ]
    scene.render.resolution_x, scene.render.resolution_y = (args.width, args.height)
    scene.render.resolution_percentage = 100
    scene.render.fps = args.fps
    scene.frame_start, scene.frame_end = (1, round(args.duration * args.fps))
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "CUSTOM"
    scene.render.ffmpeg.custom_constant_rate_factor = 23
    scene.render.ffmpeg.ffmpeg_preset = "REALTIME"
    scene.render.ffmpeg.gopsize = 250
    scene.render.ffmpeg.use_max_b_frames = False
    scene.render.ffmpeg.max_b_frames = 0
    scene.render.filepath = args.out
    scene.render.use_file_extension = False
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("world")
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
    scene.display.shading.background_type = "WORLD"
    scene.display.render_aa = "8"
    data = bpy.data.cameras.new("camera")
    data.sensor_fit = "VERTICAL"
    data.angle = 2 * math.atan(4 / 20)
    data.clip_end = 100
    camera = bpy.data.objects.new("camera", data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    light = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    light.data.energy = 3
    light.rotation_euler = (math.radians(40), 0, math.radians(-30))
    bpy.context.collection.objects.link(light)
    for name, energy, angles in (
        ("fill", 0.9, (55, 0, 150)),
        ("lower_fill", 0.6, (150, 0, 60)),
    ):
        fill = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        fill.data.energy = energy
        fill.data.use_shadow = False
        fill.rotation_euler = tuple(math.radians(value) for value in angles)
        bpy.context.collection.objects.link(fill)
    updates = make_scene(args.scene)

    def frame(current, *_):
        t = (current.frame_current - 1) / args.fps
        phi, theta = (math.radians(65), math.radians(-45) + 0.24 * t)
        camera.location = (
            20 * math.sin(phi) * math.cos(theta),
            20 * math.sin(phi) * math.sin(theta),
            20 * math.cos(phi),
        )
        camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
        for update in updates:
            update(t)

    bpy.app.handlers.frame_change_pre.append(frame)
    scene.frame_set(1)
    if args.validate:
        for number in (1, max(1, scene.frame_end // 2), scene.frame_end):
            scene.frame_set(number)
        print(
            f"Validated scene construction: {args.scene}, {len(scene.objects)} objects; no rendering"
        )
    else:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", choices=["hierarchy"], required=True)
    parser.add_argument("--engine", choices=["workbench", "eevee"], required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--duration", type=float, default=SECONDS)
    parser.add_argument("--validate", action="store_true")
    ARGS = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    setup(ARGS)
