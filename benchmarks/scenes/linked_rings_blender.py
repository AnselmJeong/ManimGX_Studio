import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
import math

import numpy as np
from lighting import LIGHTS, PHI, ROUGHNESS, TIME, VIEW
from suite_data import COLORS, ring_pose

parser = argparse.ArgumentParser()
parser.add_argument("--engine", required=True, choices=["workbench", "eevee"])
parser.add_argument("--out", required=True)
parser.add_argument("--animate", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = {"workbench": "BLENDER_WORKBENCH", "eevee": "BLENDER_EEVEE"}[
    args.engine
]
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = args.out
scene.render.use_file_extension = False
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.world = bpy.data.worlds.new("world")
scene.world.color = (0, 0, 0)
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0, 0, 0, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
data = bpy.data.cameras.new("camera")
data.sensor_fit = "VERTICAL"
data.angle = 2 * math.atan(4 / 20)
camera = bpy.data.objects.new("camera", data)
bpy.context.collection.objects.link(camera)
camera.location = 20 * Vector(VIEW)
camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = camera
rings = []
for i in range(8):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=32, minor_segments=8, major_radius=0.58, minor_radius=0.11
    )
    obj = bpy.context.object
    rings.append(obj)
    rotation, position = ring_pose(i, TIME)
    obj.rotation_euler = Matrix(rotation.tolist()).to_euler()
    obj.location = position
    for face in obj.data.polygons:
        face.use_smooth = True
    color = COLORS[i % 5]
    rgb = [int(color[k : k + 2], 16) / 255 for k in (1, 3, 5)]
    rgb = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    mat = bpy.data.materials.new(color)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["IOR"].default_value = 1.5
    obj.data.materials.append(mat)
for i, (direction, intensity, shadows) in enumerate(LIGHTS):
    data = bpy.data.lights.new(f"light-{i}", "SUN")
    data.energy = math.pi * intensity
    data.color = (1, 1, 1)
    data.angle = 0
    data.use_shadow = shadows
    light = bpy.data.objects.new(data.name, data)
    light.rotation_euler = (-Vector(direction)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(light)
if args.engine == "eevee":
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_shadows = True
else:
    studio = Path(args.out).with_suffix(".sl")
    lines = [
        "version 1",
        "light_ambient.x 0.15",
        "light_ambient.y 0.15",
        "light_ambient.z 0.15",
    ]
    for i in range(4):
        direction, intensity, _ = (
            LIGHTS[i] if i < len(LIGHTS) else (np.zeros(3), 0, False)
        )
        lines += [f"light[{i}].flag {int(i < len(LIGHTS))}", f"light[{i}].smooth 0.25"]
        # Workbench studio coordinates are Y-up; its world-orientation transform maps (x,y,z) to (x,-z,y).
        direction = (direction[0], direction[2], -direction[1])
        for axis, v in zip("xyz", direction):
            lines += [
                f"light[{i}].vec.{axis} {v:.8f}",
                f"light[{i}].col.{axis} {intensity:.8f}",
                f"light[{i}].spec.{axis} {0.12 * intensity:.8f}",
            ]
    studio.write_text("\n".join(lines) + "\n", encoding="utf-8")
    loaded = bpy.context.preferences.studio_lights.load(str(studio), "STUDIO")
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.studio_light = loaded.name
    shading.use_world_space_lighting = True
    shading.studiolight_rotate_z = 0
    shading.color_type = "MATERIAL"
    shading.background_type = "WORLD"
    shading.show_shadows = True
    d = LIGHTS[0][0]
    scene.display.light_direction = (d[0], d[2], -d[1])
    scene.display.render_aa = "8"
if args.animate:
    scene.render.film_transparent = False
    scene.render.fps = 60
    scene.frame_start, scene.frame_end = 1, 180
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

    def frame(current, *_):
        t = (current.frame_current - 1) / 60
        theta = math.radians(-45) + 0.24 * t
        camera.location = (
            20 * math.sin(PHI) * math.cos(theta),
            20 * math.sin(PHI) * math.sin(theta),
            20 * math.cos(PHI),
        )
        camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
        for i, obj in enumerate(rings):
            rotation, position = ring_pose(i, t)
            obj.rotation_euler = Matrix(rotation.tolist()).to_euler()
            obj.location = position

    bpy.app.handlers.frame_change_pre.append(frame)
    scene.frame_set(1)
    bpy.ops.render.render(animation=True)
else:
    bpy.ops.render.render(write_still=True)
