import argparse
import math
import sys
from pathlib import Path

import numpy as np
from lighting import LIGHTS, PHI, ROUGHNESS, THETA, TIME
from PIL import Image
from suite_data import COLORS, ring_pose, torus_point

parser = argparse.ArgumentParser()
parser.add_argument("--engine", required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
sys.argv = [sys.argv[0]]

if args.engine == "manimgl":
    import manimlib as m
elif args.engine == "manim_ce":
    import manim as m
else:
    import manimgx as m

GL = args.engine == "manimgl"
GX = args.engine == "manimgx"
if not GL:
    m.config.pixel_width, m.config.pixel_height = 1920, 1080
    m.config.frame_rate = 60
    m.config.background_color = "#000000"
    m.config.background_opacity = 0


class Still(m.ThreeDScene):
    def construct(self):
        if GL:
            self.frame.reorient(math.degrees(THETA) + 90, math.degrees(PHI))
            self.frame.set_focal_distance(20)
        else:
            self.set_camera_orientation(phi=PHI, theta=THETA, focal_distance=20)
        self.camera.light_source.move_to(LIGHTS[0][0] * 10000)
        for i in range(8):
            if GL:
                obj = m.ParametricSurface(
                    torus_point,
                    u_range=(0, 2 * np.pi),
                    v_range=(0, 2 * np.pi),
                    resolution=(33, 9),
                    color=m.Color(
                        rgb=np.clip(
                            np.array(m.Color(COLORS[i % 5]).get_rgb()) - 0.18, 0, 1
                        )
                    ),
                )
            else:
                obj = m.Surface(
                    torus_point,
                    u_range=(0, 2 * np.pi),
                    v_range=(0, 2 * np.pi),
                    resolution=(32, 8),
                    fill_color=COLORS[i % 5]
                    if GX
                    else m.ManimColor(
                        np.clip(m.ManimColor(COLORS[i % 5]).to_rgb() - 0.24, 0, 1)
                    ),
                    fill_opacity=1,
                    stroke_width=0,
                    checkerboard_colors=False,
                )
            rotation, position = ring_pose(i, TIME)
            obj.apply_matrix(rotation).move_to(position)
            if GX:
                obj.set_material(
                    m.Material(metallic=0, roughness=ROUGHNESS, reflectance=0.5)
                )
            self.add(obj)
        if GX:
            self.camera.tone_mapping = "linear"
            self.camera.exposure = 1
            self.camera.bloom = 0
            self.camera.ambient_occlusion = 0
            for direction, intensity, shadows in LIGHTS:
                self.add(m.SunLight(direction, intensity=intensity, shadows=shadows))
            self.wait(1 / 60)


args.out.parent.mkdir(parents=True, exist_ok=True)
if GX:

    def keep(frame):
        pixels = np.frombuffer(frame.pixels(), np.uint8).reshape(1080, 1920, 4)
        Image.fromarray(pixels).save(args.out)

    Still().render(None, frames=keep)
elif GL:
    scene = Still(
        window=None,
        camera_config={
            "resolution": (1920, 1080),
            "fps": 60,
            "background_color": "#000000",
            "background_opacity": 0,
        },
        file_writer_config={"write_to_movie": False, "save_last_frame": False},
    )
    scene.construct()
    scene.update_frame(force_draw=True)
    scene.get_image().save(args.out)
else:
    m.config.media_dir = str(args.out.parent / "ce-media")
    m.config.disable_caching = True
    m.config.write_to_movie = False
    scene = Still()
    scene.construct()
    scene.renderer.update_frame(scene)
    Image.fromarray(scene.renderer.get_frame()).save(args.out)
print(args.out)
