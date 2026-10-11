"""Matrix multiplication and twelve pendulums in Blender."""

import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import suite_blender as base

WHITE = "#FFFFFF"
YELLOW = "#FFFF00"


def flat_material(color):
    mat = base.material(color)
    nodes = mat.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = mat.diffuse_color
    output = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return mat


def text(value, x, y, size=0.5, color=WHITE):
    data = bpy.data.curves.new(value, "FONT")
    data.body, data.size = value, size
    data.align_x, data.align_y = "CENTER", "CENTER"
    data.resolution_u = 12
    data.materials.append(flat_material(color))
    obj = bpy.data.objects.new(value, data)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, y, 0.01)
    return obj


def stroke(points, width=0.015, color=WHITE):
    obj = base.line([(x, y, 0) for x, y in points], color, width / 0.005)
    obj.data.materials.clear()
    obj.data.materials.append(flat_material(color))
    return obj


def brackets(left, right, center=0.6, height=1.65):
    top, bottom = center + height / 2, center - height / 2
    return [
        stroke(
            [(left + 0.12, top), (left, top), (left, bottom), (left + 0.12, bottom)]
        ),
        stroke(
            [(right - 0.12, top), (right, top), (right, bottom), (right - 0.12, bottom)]
        ),
    ]


def reveal(objects, alpha):
    for i, obj in enumerate(objects):
        local = max(0.0, min(1.0, alpha * len(objects) - i))
        obj.hide_render = local <= 0
        obj.scale = (max(0.001, local),) * 3


def build_matrix():
    first = brackets(-2.1, 0.1)
    first += [
        text(str(n), x, y)
        for n, x, y in [(1, -1.6, 1), (2, -0.4, 1), (3, -1.6, 0.2), (1, -0.4, 0.2)]
    ]
    first += brackets(0.4, 1.35)
    first += [text("2", 0.875, 1), text("1", 0.875, 0.2), text("=", 1.85, 0.6, 0.6)]
    step = brackets(2.35, 5.95)
    for row, formula in enumerate(("1 · 2 + 2 · 1", "3 · 2 + 1 · 1")):
        for i, char in enumerate(formula):
            if char != " ":
                step.append(text(char, 2.65 + i * 0.25, 1 - row * 0.8, 0.425))
    result = brackets(2.35, 3.25)
    result += [text("4", 2.8, 1, 0.55, YELLOW), text("7", 2.8, 0.2, 0.55, YELLOW)]
    for obj in result[:2]:
        obj.data.materials.clear()
        obj.data.materials.append(flat_material(YELLOW))

    def update(t):
        reveal(first, min(1, t))
        alpha = max(0, min(1, (t - 4.2)))
        reveal(step, max(0, min(1, (t - 1.4) / 2)))
        if t >= 4.2:
            for obj in step:
                obj.hide_render = alpha >= 1
                obj.scale = (max(0.001, 1 - alpha),) * 3
        reveal(result, alpha)

    return update


def build_pendulums():
    title_string = "Pendulums of varying lengths"
    title = [
        text(c, (i - (len(title_string) - 1) / 2) * 0.25, 3.45, 0.5)
        for i, c in enumerate(title_string)
    ]
    objects = []
    for i in range(12):
        rod = stroke([(0, 0), (0, 1)], 0.0075)
        bpy.ops.mesh.primitive_circle_add(vertices=32, radius=0.08, fill_type="NGON")
        dot = bpy.context.object
        dot.data.materials.append(flat_material(YELLOW))
        objects.append((rod, dot))

    def update(t):
        reveal(title, min(1, t / 2))
        clock = max(0, min(14, (t - 2) * 1.4))
        for i, (rod, dot) in enumerate(objects):
            length = 1.5 + i * 0.15
            theta = 0.55 * math.cos(math.sqrt(9.8 / length) * clock)
            pivot = (-5 + i * 0.85, 2.5, 0)
            bob = (
                pivot[0] + length * math.sin(theta),
                pivot[1] - length * math.cos(theta),
                0,
            )
            rod.hide_render = dot.hide_render = t < 2
            base.update_line(rod, [pivot, bob])
            dot.location = bob

    return update


parser = argparse.ArgumentParser()
parser.add_argument("--scene", required=True, choices=["matrix", "pendulums"])
parser.add_argument("--engine", required=True, choices=["workbench", "eevee"])
parser.add_argument("--out", required=True)
parser.add_argument("--preview", type=float)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = {"workbench": "BLENDER_WORKBENCH", "eevee": "BLENDER_EEVEE"}[
    args.engine
]
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.render.fps = 60
scene.frame_start = 1
scene.frame_end = 432 if args.scene == "matrix" else 780
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("world")
scene.world.color = (0, 0, 0)
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.background_type = "WORLD"
scene.display.render_aa = "8"
data = bpy.data.cameras.new("camera")
data.type = "ORTHO"
data.ortho_scale = 128 / 9
camera = bpy.data.objects.new("camera", data)
bpy.context.collection.objects.link(camera)
camera.location = (0, 0, 20)
scene.camera = camera
update = build_matrix() if args.scene == "matrix" else build_pendulums()


def frame(current, *_):
    update((current.frame_current - 1) / 60)


bpy.app.handlers.frame_change_pre.append(frame)
scene.frame_set(1)
scene.render.filepath = args.out
scene.render.use_file_extension = False
if args.preview is not None:
    scene.frame_set(round(args.preview * 60) + 1)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
else:
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
    bpy.ops.render.render(animation=True)
