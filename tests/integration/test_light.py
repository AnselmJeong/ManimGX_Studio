"""A mobject with a material is lit by the scene's lights, as a physical surface is: a white
matte surface facing a light of intensity 1 shows white, a point light falls off with the
square of the distance, an ambient light lights every side alike, what is brighter than white
is clipped or rolled off as the camera says, and a highlight narrower than a pixel shows its
light over the pixel, steady as the camera turns. An environment lights with a picture of the
surroundings: a uniform one as an ambient light of its light does, its picture turning with
it, a mirror showing each direction's light where it reflects that direction, and a sun in it
as a sun of its light does, casting shadows. A path (a filled
shape) with a material is lit as a mesh with it is (its material alone: not Manim's shading
too), and shadows fall on it; what a path shows casts a shadow, as a mesh does. With ambient
occlusion, the light from all around is shut out where the surfaces near a point block it — a
floor inside a ring, beside a wall — by paths and meshes alike, but not by or from what can be
seen through, and a sun's light is left as it was. With bloom, a light brighter than white glows
into the dark around it, more with more strength and less farther off; what the glow spreads,
the light leaves; it is spread from the light the view shows (what hides a light hides its
glow) and lies over everything the view shows, paint and what is fixed in the frame too, and
alone where it shows nothing; paint never glows; and a moving light's glow moves with it
unchanged. A mobject without a material is shaded as it always was, whatever the lights.
"""

import itertools
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from tests import scenes

import manimgx as m

SIZE = (160, 90)
MATTE = m.Material(roughness=1.0)
pytestmark = pytest.mark.config(pixel_width=SIZE[0], pixel_height=SIZE[1])


def frames(build: Callable[[m.ThreeDScene], None]) -> list[np.ndarray]:
    """Every frame a 3D scene shows, looking straight down the z axis (RGB rows)."""

    def construct(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
        build(scene)

    shown = scenes.frames(scenes.scene_3d(construct))
    return [rgba[..., :3] for rgba in shown]


def plane(material: m.Material | None = MATTE, z: float = 0.0) -> m.Mobject:
    """A white plane filling the view, facing the camera (and the z axis)."""
    surface = m.Surface(
        lambda u, v: np.array([u, v, z]),
        u_range=[-9, 9],
        v_range=[-5, 5],
        resolution=(2, 2),
        stroke_width=0,
    )
    surface.set_color(m.WHITE)
    return surface if material is None else surface.set_material(material)


def center(picture: np.ndarray) -> np.ndarray:
    return picture[SIZE[1] // 2, SIZE[0] // 2].astype(float)


def linear(value: float) -> float:
    """An sRGB-encoded level (0-255) in linear light."""
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


@pytest.mark.parametrize(
    ("light", "level"),
    [((0.0, 0.0, 1e8), 255), ((0.0, 0.0, -1e8), 64), ((0.0, 0.0, 0.0), 128)],
)
def test_a_surface_without_a_material_keeps_signed_camera_shading(
    light: tuple[float, float, float], level: int
) -> None:
    # Along the normal, shading adds 1/2; from behind, it subtracts 1/4. The distant
    # light makes the cosine round to exactly ±1 at every vertex: grey 128 becomes
    # clipped white 255 or round(128 - 255/4) = 64. A light in the plane adds nothing,
    # including at its coincident vertex, where the light has no direction.
    def build(scene: m.ThreeDScene) -> None:
        surface = plane(None).set_color("#808080")
        assert (surface.get_all_points() == m.ORIGIN).all(axis=1).any()
        scene.camera.light_source.move_to(light)
        scene.add(surface)
        scene.wait(0.1)

    assert (frames(build)[0] == level).all()


def test_a_white_matte_surface_facing_a_light_of_intensity_one_shows_white() -> None:
    def build(scene: m.ThreeDScene) -> None:
        scene.add(plane(), m.SunLight(5 * m.OUT, intensity=1.0))
        scene.wait(0.1)

    assert (center(frames(build)[0]) >= 254).all()


def test_half_the_exposure_shows_half_the_light() -> None:
    def build(scene: m.ThreeDScene) -> None:
        scene.camera.exposure = 0.5
        scene.add(plane(), m.SunLight(5 * m.OUT, intensity=1.0))
        scene.wait(0.1)

    level = center(frames(build)[0])
    assert abs(linear(level[0]) - 0.5) < 0.02


def test_a_point_light_falls_off_with_the_square_of_the_distance() -> None:
    def at(distance: float) -> float:
        def build(scene: m.ThreeDScene) -> None:
            scene.camera.exposure = 0.25  # nothing clips
            scene.add(
                plane(), m.PointLight(distance * m.OUT, intensity=1.0, radius=100.0)
            )
            scene.wait(0.1)

        return linear(center(frames(build)[0])[0])

    near, far = at(1.0), at(2.0)
    assert abs(near / far - 4.0) < 0.25


def test_an_ambient_light_lights_every_side_alike() -> None:
    def build(scene: m.ThreeDScene) -> None:
        sphere = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0).set_color(
            m.WHITE
        )
        scene.add(
            sphere.set_material(m.Material(roughness=1.0)),
            m.AmbientLight(intensity=0.5),
        )
        scene.wait(0.1)

    picture = frames(build)[0]
    y, x = np.mgrid[: SIZE[1], : SIZE[0]]
    radius = 2.0 / 8.0 * SIZE[1]  # (the frame is 8 units tall)
    inside = (x + 0.5 - SIZE[0] / 2) ** 2 + (y + 0.5 - SIZE[1] / 2) ** 2 < (
        0.8 * radius
    ) ** 2
    seen = picture[inside]
    assert seen.max() - seen.min() <= 3


def test_a_surface_is_brightest_where_it_faces_the_sun() -> None:
    def build(scene: m.ThreeDScene) -> None:
        sphere = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0).set_color(
            m.WHITE
        )
        scene.add(
            sphere.set_material(m.Material(roughness=1.0)),
            m.SunLight(5 * m.RIGHT + m.OUT),
        )
        scene.wait(0.1)

    picture = frames(build)[0]
    row = picture[SIZE[1] // 2, :, 0].astype(float)
    lit, unlit = row[SIZE[0] // 2 + 10], row[SIZE[0] // 2 - 10]
    assert lit > unlit + 40


def test_a_white_rough_metal_in_a_uniform_light_shows_that_light_at_any_roughness() -> (
    None
):
    # a white furnace: a surface that loses no energy shows its surroundings' light and no
    # more, rough metal as smooth (the light single scattering loses on a rough surface is
    # given back)
    def level(roughness: float) -> float:
        def build(scene: m.ThreeDScene) -> None:
            sphere = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0)
            sphere.set_color(m.WHITE).set_material(
                m.Material(metallic=1.0, roughness=roughness)
            )
            scene.add(sphere, m.AmbientLight(intensity=0.5))
            scene.wait(0.1)

        return linear(center(frames(build)[0])[0])

    for roughness in (0.25, 0.5, 0.75, 1.0):
        assert abs(level(roughness) - 0.5) < 0.01


def radiance_file(path: Path, light: np.ndarray) -> Path:
    """A Radiance (.hdr) file of a grey picture's light (rows from the top), its pixels flat."""
    height, width = light.shape
    mantissa, exponent = np.frexp(light)
    rgbe = np.zeros((height, width, 4), np.uint8)
    rgbe[..., :3] = np.where(light > 0, mantissa * 256, 0).astype(np.uint8)[..., None]
    rgbe[..., 3] = np.where(light > 0, exponent + 128, 0)
    head = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n" % (height, width)
    path.write_bytes(head + rgbe.tobytes())
    return path


def ball(material: m.Material, light: m.Light) -> np.ndarray:
    """A white ball with a material, seen from above, lit by one light."""

    def build(scene: m.ThreeDScene) -> None:
        sphere = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0)
        scene.add(sphere.set_color(m.WHITE).set_material(material), light)
        scene.wait(0.1)

    return frames(build)[0].astype(int)


@pytest.mark.parametrize(
    ("metallic", "roughness"), [(0.0, 1.0), (0.0, 0.3), (1.0, 0.2), (1.0, 0.8)]
)
def test_a_uniform_environment_lights_as_an_ambient_light_of_its_light_does(
    tmp_path: Path, metallic: float, roughness: float
) -> None:
    grey = radiance_file(tmp_path / "grey.hdr", np.full((64, 128), 0.5))
    material = m.Material(metallic=metallic, roughness=roughness)
    around = ball(material, m.EnvironmentLight(grey))
    ambient = ball(material, m.AmbientLight(intensity=0.5))
    assert np.abs(around - ambient).max() <= 1


def bright_spot(u: float, v: float = 0.5) -> np.ndarray:
    """A dark picture with a soft bright spot at (u, v) (fractions of its width and height)."""
    height, width = 64, 128
    y, x = np.mgrid[:height, :width] + 0.5
    across = (
        x - u * width + width / 2
    ) % width - width / 2  # (around the picture's seam)
    return 0.02 + 8.0 * np.exp(-(across**2 + (y - v * height) ** 2) / (2 * 4.0**2))


def test_an_environment_turns_with_its_light(tmp_path: Path) -> None:
    # a quarter turn about the scene's up moves the picture's centre (seen along RIGHT) to UP:
    # as the same picture with its spot a quarter of its width to the left
    ahead = radiance_file(tmp_path / "ahead.hdr", bright_spot(0.5))
    left = radiance_file(tmp_path / "left.hdr", bright_spot(0.25))
    shiny = m.Material(metallic=1.0, roughness=0.3)
    turned = ball(shiny, m.EnvironmentLight(ahead).rotate(m.PI / 2, axis=m.OUT))
    assert np.abs(turned - ball(shiny, m.EnvironmentLight(left))).max() <= 3
    assert np.abs(turned - ball(shiny, m.EnvironmentLight(ahead))).max() > 60


def test_a_mirror_shows_each_direction_where_it_reflects_it(tmp_path: Path) -> None:
    # a spot on the horizon to the right of the picture's centre (seen along RIGHT) is DOWN
    # in the scene, turning right as one looks across it: a mirror ball seen from above
    # shows it on its DOWN side, halfway out (where its surface faces between up and DOWN)
    spot = radiance_file(tmp_path / "spot.hdr", bright_spot(0.75))
    shown = ball(m.Material(metallic=1.0, roughness=0.1), m.EnvironmentLight(spot))
    # where the spot shows: the middle of what is brighter than most of the ball
    level = shown.sum(axis=2).astype(float)
    weight = np.clip(level - np.median(level[level > 0]) - 60, 0, None)
    y, x = np.mgrid[: SIZE[1], : SIZE[0]] + 0.5
    radius = 2.0 / 8.0 * SIZE[1]  # (the frame is 8 units tall)
    below = ((y * weight).sum() / weight.sum() - SIZE[1] / 2) / radius  # rows run down
    across = ((x * weight).sum() / weight.sum() - SIZE[0] / 2) / radius
    assert abs(below - np.sqrt(0.5)) < 0.1
    assert abs(across) < 0.1


def sun_picture(
    path: Path, toward: tuple[float, float], glow: float
) -> tuple[Path, float]:
    """A Radiance file of a dark sky with a sun toward (azimuth, elevation) in degrees, a disc
    as wide as the Sun (0.53 degrees) of light `glow`, each pixel's share of it found by 8 x 8
    points; and what the sun shows on a white matte surface facing it."""
    height, width = 256, 512
    az, el = np.radians(toward)
    sun = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    inside = np.zeros((height, width))
    for k in range(64):
        u = (np.arange(width) + (k % 8 + 0.5) / 8) / width
        v = (np.arange(height) + (k // 8 + 0.5) / 8) / height
        phi, theta = np.meshgrid((0.5 - u) * 2 * np.pi, v * np.pi)
        d = np.stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)],
            -1,
        )
        inside += (d @ sun > np.cos(np.radians(0.265))) / 64
    solid = (
        np.sin((np.arange(height) + 0.5) / height * np.pi)[:, None]
        * (2 * np.pi / width)
        * (np.pi / height)
    )
    shown = float((inside * glow * solid).sum() / np.pi)
    return radiance_file(path, 0.001 + inside * glow), shown


def test_an_environments_sun_lights_as_a_sun_of_its_light_does(tmp_path: Path) -> None:
    # its light comes from its direction alone, all of it: as a sun's of the light it sends
    picture, shown = sun_picture(tmp_path / "sun.hdr", (30.0, 60.0), 22_000.0)
    toward = np.array(
        [
            np.cos(np.radians(60)) * np.cos(np.radians(30)),
            np.cos(np.radians(60)) * np.sin(np.radians(30)),
            np.sin(np.radians(60)),
        ]
    )

    def view(light: m.Light) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.add(plane(), light)
            scene.wait(0.1)

        return center(frames(build)[0])

    around = view(m.EnvironmentLight(picture, shadows=False))
    sun = view(m.SunLight(toward, intensity=shown, shadows=False))
    assert sun.min() > 100
    assert np.abs(around - sun).max() <= 1


def test_an_environments_sun_casts_a_shadow(tmp_path: Path) -> None:
    # a sun 45 degrees up over LEFT: a ball 2 above the floor shadows the floor 2 to the right
    picture, _ = sun_picture(tmp_path / "sun.hdr", (180.0, 45.0), 30_000.0)

    def view(shadows: bool) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            ball = m.Sphere(radius=0.6, resolution=(24, 24), stroke_width=0).shift(
                2 * m.OUT
            )
            scene.add(
                plane(),
                ball.set_material(m.Material()),
                m.EnvironmentLight(picture, shadows=shadows),
            )
            scene.wait(0.1)

        return frames(build)[0]

    lit, shadowed = view(False), view(True)
    assert shadowed[floor_at(2.0)].max() < lit[floor_at(2.0)].max() - 100
    assert (shadowed[floor_at(-2.0)] == lit[floor_at(-2.0)]).all()


def test_agx_rolls_off_what_clipping_saturates() -> None:
    def shown(tone: str) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.camera.tone_mapping = tone  # type: ignore
            scene.add(plane(), m.SunLight(5 * m.OUT, intensity=4.0))
            scene.wait(0.1)

        return center(frames(build)[0])

    clipped, rolled = shown("linear"), shown("agx")
    assert (clipped >= 254).all()
    assert (rolled < 250).all()
    assert (rolled > 200).all()


def test_a_material_tweens() -> None:
    def sphere(roughness: float) -> m.Mobject:
        mob = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0).set_color(m.RED)
        return mob.set_material(m.Material(roughness=roughness))

    def still(roughness: float) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.add(sphere(roughness), m.SunLight(5 * m.OUT + m.RIGHT))
            scene.wait(0.1)

        return frames(build)[0]

    def build(scene: m.ThreeDScene) -> None:
        mob = sphere(0.1)
        scene.add(mob, m.SunLight(5 * m.OUT + m.RIGHT))
        scene.play(mob.animate.set_material(m.Material(roughness=0.9)), run_time=0.5)

    tween = frames(build)
    assert np.array_equal(tween[0], still(0.1))
    assert np.array_equal(tween[-1], still(0.9))
    assert (
        len({picture.tobytes() for picture in tween}) > 10
    )  # through every roughness between


def test_a_scene_without_lights_lights_its_materials_by_its_camera() -> None:
    def build(scene: m.ThreeDScene) -> None:
        sphere = m.Sphere(radius=2.0, resolution=(48, 48), stroke_width=0).set_color(
            m.WHITE
        )
        scene.add(sphere.set_material(m.Material()))
        scene.wait(0.1)

    assert center(frames(build)[0]).max() > 60


def test_a_path_with_a_material_is_lit_as_a_mesh_with_it() -> None:
    def view(kind: str) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            if kind == "path":
                mob: m.Mobject = m.Square(side_length=6, stroke_width=0, fill_opacity=1)
            else:
                mob = m.Surface(
                    lambda u, v: np.array([u, v, 0]),
                    u_range=[-3, 3],
                    v_range=[-3, 3],
                    resolution=(2, 2),
                    stroke_width=0,
                )
            mob.set_color(m.BLUE_D).rotate(40 * m.DEGREES, axis=m.RIGHT)
            scene.add(
                mob.set_material(m.Material(roughness=0.4)),
                m.PointLight(2 * m.OUT + m.LEFT, intensity=3.0),
                m.AmbientLight(intensity=0.1),
            )
            scene.wait(0.1)

        return frames(build)[0].astype(int)

    path, mesh = view("path"), view("mesh")
    # where both cover their pixels whole: away from their edges
    inside = (path.sum(axis=2) > 0) & (mesh.sum(axis=2) > 0)
    for _ in range(2):
        inside &= np.roll(inside, 1, 0) & np.roll(inside, -1, 0)
        inside &= np.roll(inside, 1, 1) & np.roll(inside, -1, 1)
    assert inside.sum() > 1000
    assert np.abs(path - mesh).max(axis=2)[inside].max() <= 2


def encoded(light: float) -> float:
    """A linear light (0-1) as an sRGB-encoded level (0-255)."""
    c = 12.92 * light if light <= 0.0031308 else 1.055 * light ** (1 / 2.4) - 0.055
    return 255 * c


def lit_rectangle(
    kind: str, x: tuple[float, float], y: tuple[float, float], color: str
) -> m.Mobject:
    """A matte rectangle in the xy plane, `x` and `y` its sides' ranges: a mesh or a path."""
    (x0, x1), (y0, y1) = x, y
    if kind == "mesh":
        mob: m.Mobject = m.Surface(
            lambda u, v: np.array([u, v, 0]),
            u_range=[x0, x1],
            v_range=[y0, y1],
            resolution=(1, 1),
            stroke_width=0,
        )
    else:
        corners = [[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]]
        mob = m.Polygon(*corners, stroke_width=0, fill_opacity=1)
    return mob.set_color(color).set_material(MATTE)


def mixes_light(left: int, middle: int, right: int) -> bool:
    """Whether a pixel half one level, half another shows the mean of their light (as a camera
    does), not the mean of the levels."""
    light = 0.5 * (linear(left) + linear(right))
    return abs(middle - encoded(light)) <= 2 and abs(middle - 0.5 * (left + right)) > 20


@pytest.mark.parametrize(
    "kinds", [("mesh", "mesh"), ("path", "path"), ("mesh", "path"), ("path", "mesh")]
)
def test_lit_surfaces_meeting_in_a_pixel_mix_their_light_before_it_is_shown(
    kinds: tuple[str, str],
) -> None:
    # a white and a black matte surface meeting in the middle of a pixel, lit straight down: as a
    # camera integrates light, the pixel shows the mean of their light; mixing what each shows
    # would show the mean of their levels (here 141, 48 levels darker)
    # (the boundary: half a pixel right of the view's centre, in scene units)
    boundary = 0.5 * 8 / SIZE[1]

    def build(scene: m.ThreeDScene) -> None:
        white = lit_rectangle(kinds[0], (-9, boundary), (-5, 5), m.WHITE)
        black = lit_rectangle(kinds[1], (boundary, 9), (-5, 5), m.BLACK)
        scene.add(white, black, m.SunLight(m.OUT, intensity=1.0))
        scene.wait(0.1)

    shown = frames(build)[0].astype(int)
    row = SIZE[1] // 2
    assert mixes_light(*(shown[row, SIZE[0] // 2 + k, 0] for k in (-3, 0, 3)))


@pytest.mark.config(pixel_width=1920, pixel_height=1080)
def test_a_lit_shape_mixes_light_with_one_drawn_long_before_it() -> None:
    # a white matte plane, many large shapes (more than the composite lays in one pass: they reach
    # far past the 64 million pixels of coverage a pass holds), then a black matte rectangle over
    # half of a pixel of the plane: the pixel still mixes their light
    boundary = 0.5 * 8 / 1080

    def build(scene: m.ThreeDScene) -> None:
        scene.add(lit_rectangle("path", (-7, 7), (-4, -1), m.WHITE))
        for k in range(150):
            filler = m.Rectangle(width=14, height=4.4, stroke_width=0, fill_opacity=1)
            scene.add(filler.set_fill(m.GREY).shift(1.7 * m.UP + 0.001 * k * m.RIGHT))
        scene.add(lit_rectangle("path", (boundary, 7), (-4, -1), m.BLACK))
        scene.add(m.SunLight(m.OUT, intensity=1.0))
        scene.wait(1 / 60)

    shown = frames(build)[0].astype(int)
    row = 540 + int(2.5 / (8 / 1080))
    assert mixes_light(*(shown[row, 960 + k, 0] for k in (-3, 0, 3)))


def test_a_shape_shaded_in_3d_is_lit_by_its_material_alone() -> None:
    # a cube's faces are shaded in 3D (Manim's light, by which way each faces); with a material,
    # the scene's lights alone light them: under a light from all around, every face shows alike
    # (but for the specular lobe's share, which grows toward grazing angles: a few levels)
    def build(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=60 * m.DEGREES, theta=-50 * m.DEGREES)
        cube = m.Cube(side_length=3, fill_opacity=1, stroke_width=0).set_fill(m.GREY_B)
        scene.add(cube.set_material(MATTE), m.AmbientLight(intensity=1.0))
        scene.wait(0.1)

    shown = frames(build)[0].astype(int)
    cube = shown.sum(axis=2) > 0
    for _ in range(2):  # (away from its edges)
        cube &= np.roll(cube, 1, 0) & np.roll(cube, -1, 0)
        cube &= np.roll(cube, 1, 1) & np.roll(cube, -1, 1)
    assert cube.sum() > 1000
    levels = shown[..., 0][cube]
    assert levels.max() - levels.min() <= 6


def test_lights_leave_a_mobject_without_a_material_as_it_was() -> None:
    def build(lights: bool) -> Callable[[m.ThreeDScene], None]:
        def inner(scene: m.ThreeDScene) -> None:
            scene.add(m.Sphere(radius=2.0, resolution=(24, 24)).set_color(m.BLUE))
            scene.add(m.Square(side_length=2).shift(4 * m.RIGHT).set_fill(m.GREEN, 1))
            if lights:
                scene.add(
                    m.SunLight(),
                    m.PointLight(m.OUT, m.RED),
                    m.AmbientLight(intensity=0.5),
                    m.EnvironmentLight(),
                )
            scene.wait(0.1)

        return inner

    assert np.array_equal(frames(build(False))[0], frames(build(True))[0])


@pytest.mark.config(frame_rate=10)
@pytest.mark.parametrize("entrance", ["opaque", "transparent", "fade"])
@pytest.mark.parametrize("ordinary", ["mesh", "overlay", "points"])
def test_material_entrances_leave_other_rasters_as_they_are(
    entrance: str, ordinary: str
) -> None:
    # Disjoint objects must show exactly what each shows alone, even when no opaque
    # material mesh precedes the ordinary mesh, overlay, or sprite in its pass.
    def view(shown: tuple[bool, bool]) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            def quad(x: float) -> m.MeshMobject:
                return m.MeshMobject(
                    np.array(
                        [[x - 1, -1, 0], [x + 1, -1, 0], [x + 1, 1, 0], [x - 1, 1, 0]]
                    ),
                    np.array([[0, 1, 2], [0, 2, 3]]),
                    vertex_colors=np.tile([0.2, 0.6, 0.9, 1.0], (4, 1)),
                    shade_in_3d=False,
                )

            scene.add(m.AmbientLight(intensity=0.5))
            scene.camera.exposure = 0.5
            if shown[0]:
                if ordinary == "points":
                    scene.add(
                        m.PMobject(stroke_width=100).add_points(
                            [2 * m.LEFT], color=m.RED, alpha=0.5
                        )
                    )
                elif ordinary == "overlay":
                    scene.add_fixed_in_frame_mobjects(quad(-2))
                else:
                    scene.add(quad(-2))
            if shown[1]:
                material = quad(2).set_material(MATTE)
                if entrance == "fade":
                    scene.play(m.FadeIn(material), run_time=0.2, rate_func=m.linear)
                    return
                if entrance == "transparent":
                    material.set_opacity(0.5)
                scene.add(material)
            scene.wait(0.2)

        return np.array(frames(build))

    paint, light = view((True, False)), view((False, True))
    assert paint.max() > 0
    assert light.max() > 0
    assert not np.any(np.any(paint, axis=-1) & np.any(light, axis=-1))
    assert np.array_equal(view((True, True)), np.maximum(paint, light))


def test_a_mobject_fixed_in_the_frame_is_not_lit() -> None:
    def view(material: m.Material | None) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            badge = m.Square(side_length=2, stroke_width=0, fill_opacity=1)
            ball = m.Sphere(radius=0.6, resolution=(24, 24), stroke_width=0)
            badge.set_fill(m.BLUE).shift(3 * m.LEFT)
            ball.set_color(m.RED).shift(3 * m.RIGHT)
            if material is not None:
                badge.set_material(material)
                ball.set_material(material)
            scene.add_fixed_in_frame_mobjects(badge, ball)
            scene.add(m.SunLight(m.LEFT + 5 * m.OUT, intensity=3.0))
            scene.wait(0.1)

        return frames(build)[0]

    assert np.array_equal(view(m.Material()), view(None))


def floor_at(x: float) -> tuple[int, int]:
    """The pixel showing the floor (z = 0) at (x, 0), looking straight down."""
    return SIZE[1] // 2, int(SIZE[0] / 2 + x * SIZE[1] / 8)


def test_a_sun_casts_a_shadow_where_its_light_is_blocked() -> None:
    def view(shadows: bool) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            ball = m.Sphere(radius=0.6, resolution=(24, 24), stroke_width=0).shift(
                2 * m.OUT
            )
            sun = m.SunLight(
                m.LEFT + m.OUT, shadows=shadows
            )  # 45 degrees: a height of 2 casts 2 to the right
            scene.add(plane(), ball.set_material(m.Material()), sun)
            scene.wait(0.1)

        return frames(build)[0]

    lit, shadowed = view(False), view(True)
    assert shadowed[floor_at(2.0)].max() < lit[floor_at(2.0)].max() - 100
    assert (shadowed[floor_at(-2.0)] == lit[floor_at(-2.0)]).all()


def test_a_still_shadow_stays_still_while_other_things_move() -> None:
    # a ball's shadow on a floor while another ball flies off past the floor's edge (the
    # map's fit to what casts grows with it): the still shadow keeps every pixel
    def build(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=60 * m.DEGREES, theta=-70 * m.DEGREES)
        scene.add(plane(), m.SunLight(2 * m.LEFT + 3 * m.UP + 5 * m.OUT))
        still = m.Sphere(radius=0.6, resolution=(24, 24), stroke_width=0)
        moving = m.Sphere(radius=0.4, resolution=(24, 24), stroke_width=0)
        still.shift(2.5 * m.LEFT + 0.8 * m.OUT).set_material(m.Material())
        moving.shift(1.5 * m.RIGHT + 2 * m.DOWN + 0.6 * m.OUT).set_material(
            m.Material()
        )
        scene.add(still, moving)
        scene.play(moving.animate.shift(9 * m.RIGHT + 3 * m.OUT), run_time=1.0)

    shown = [rgb.astype(int)[:, : int(0.45 * SIZE[0])] for rgb in frames(build)]
    assert len(shown) > 20
    assert max(np.abs(b - a).max() for a, b in itertools.pairwise(shown)) <= 2


def test_a_spot_casts_a_shadow_within_its_cone() -> None:
    def view(shadows: bool) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            ball = m.Sphere(radius=0.4, resolution=(24, 24), stroke_width=0).shift(
                m.OUT
            )
            # from (-3, 0, 3) through the ball at (0, 0, 1) to the floor at (1.5, 0, 0)
            spot = m.SpotLight(
                3 * m.LEFT + 3 * m.OUT,
                toward=m.ORIGIN,
                intensity=20.0,
                angle=0.9,
                shadows=shadows,
            )
            scene.add(plane(), ball.set_material(m.Material()), spot)
            scene.wait(0.1)

        return frames(build)[0]

    lit, shadowed = view(False), view(True)
    assert shadowed[floor_at(1.5)].max() < lit[floor_at(1.5)].max() - 60
    assert (shadowed[floor_at(-1.5)] == lit[floor_at(-1.5)]).all()


def test_a_shadow_falls_on_a_path_with_a_material() -> None:
    def view(shadows: bool) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            floor = m.Square(side_length=12, stroke_width=0, fill_opacity=1)
            ball = m.Sphere(radius=0.6, resolution=(24, 24), stroke_width=0).shift(
                2 * m.OUT
            )
            scene.add(
                floor.set_fill(m.WHITE).set_material(MATTE),
                ball.set_material(m.Material()),
                m.SunLight(m.LEFT + m.OUT, shadows=shadows),
            )
            scene.wait(0.1)

        return frames(build)[0]

    lit, shadowed = view(False), view(True)
    assert shadowed[floor_at(2.0)].max() < lit[floor_at(2.0)].max() - 100
    assert (shadowed[floor_at(-2.0)] == lit[floor_at(-2.0)]).all()


def shadow_of(caster: Callable[[], m.Mobject]) -> tuple[np.ndarray, np.ndarray]:
    """A white matte floor under `caster`, lit by a sun at 45 degrees from the left (a height of 2
    casts 2 to the right), without and with shadows."""

    def view(shadows: bool) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.add(plane(), caster(), m.SunLight(m.LEFT + m.OUT, shadows=shadows))
            scene.wait(0.1)

        return frames(build)[0]

    return view(False), view(True)


def test_a_path_casts_a_shadow() -> None:
    lit, shadowed = shadow_of(
        lambda: m.Square(side_length=1.2, stroke_width=0, fill_opacity=1).shift(
            2 * m.OUT
        )
    )
    assert shadowed[floor_at(2.0)].max() < lit[floor_at(2.0)].max() - 100
    assert (shadowed[floor_at(-2.0)] == lit[floor_at(-2.0)]).all()


def test_a_stroke_casts_a_shadow_and_an_unfilled_shape_none_inside() -> None:
    # a ring of radius 0.8 at a height of 2: its shadow is a ring around the floor's (2, 0)
    lit, shadowed = shadow_of(
        lambda: (
            m.Circle(radius=0.8, stroke_width=24).set_stroke(m.WHITE).shift(2 * m.OUT)
        )
    )
    assert shadowed[floor_at(2.8)].max() < lit[floor_at(2.8)].max() - 100
    assert (shadowed[floor_at(2.0)] == lit[floor_at(2.0)]).all()


def grey(mob: m.Mobject) -> m.Mobject:
    """A matte grey surface (a quarter of the light it gets: lighter ones bounce more of it back
    into their creases, white ones nearly all)."""
    return mob.set_color(m.GREY).set_material(MATTE)


def ring(opacity: float = 1.0) -> m.Mobject:
    """A ring lying on the floor around the origin: its hole half a unit across."""
    torus = m.Torus(major_radius=1.0, minor_radius=0.5, resolution=(32, 16))
    return grey(torus.set_stroke(width=0).shift(0.5 * m.OUT)).set_opacity(opacity)


def resting(
    floor: m.Mobject, thing: m.Mobject, *lights: m.Light, phi: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """A floor with a thing resting on it, seen from above (or tilted `phi` toward the front),
    lit by `lights` (an ambient light of intensity 1 unless given): without and with ambient
    occlusion reaching a unit around."""

    def view(amount: float) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.set_camera_orientation(phi=phi, theta=-90 * m.DEGREES)
            scene.camera.ambient_occlusion = amount
            scene.camera.ambient_occlusion_radius = 1.0
            scene.add(floor.copy(), thing.copy())
            scene.add(
                *[light.copy() for light in lights or [m.AmbientLight(intensity=1.0)]]
            )
            scene.wait(0.1)

        return frames(build)[0].astype(int)

    return view(0.0), view(1.0)


HOLE = (SIZE[1] // 2, SIZE[0] // 2)  # the floor in the ring's hole (the view's centre)
TILT = (
    30 * m.DEGREES
)  # (from above, the ring's underside, which shuts light out of its hole, is hidden)


@pytest.mark.parametrize("kind", ["mesh", "path"])
def test_ambient_occlusion_shuts_light_out_of_the_floor_inside_a_ring(
    kind: str,
) -> None:
    floor = plane(None) if kind == "mesh" else m.Square(side_length=12, fill_opacity=1)
    off, on = resting(grey(floor.set_stroke(width=0)), ring(), phi=TILT)
    assert linear(on[HOLE].max()) < 0.9 * linear(off[HOLE].max())
    # in the open, the floor is as it was
    assert (on[floor_at(6.0)] == off[floor_at(6.0)]).all()


def test_a_shape_shuts_out_light_as_a_mesh_does() -> None:
    # a blue cube of six squares, seen from the front (screen-space occlusion knows what the view
    # shows: from above, its walls are edge-on): the floor just before its front wall
    cube = grey(m.Cube(side_length=2, fill_opacity=1, stroke_width=0).shift(m.OUT))
    off, on = resting(grey(plane(None)), cube.set_color(m.BLUE_E), phi=60 * m.DEGREES)
    column = off[:, SIZE[0] // 2]
    base = int(np.nonzero(column[:, 2] > column[:, 0] + 20)[0].max())
    before = (base + 2, SIZE[0] // 2)
    assert linear(on[before].max()) < 0.8 * linear(off[before].max())
    # far from it, the floor is as it was
    assert (on[SIZE[1] - 3, SIZE[0] - 3] == off[SIZE[1] - 3, SIZE[0] - 3]).all()


def test_what_can_be_seen_through_neither_shuts_out_light_nor_is_darkened() -> None:
    off, on = resting(grey(plane(None)), ring(opacity=0.5))
    assert np.array_equal(off, on)


def test_ambient_occlusion_takes_light_from_all_around_and_leaves_a_suns() -> None:
    # the hole's floor, lit from straight above by a sun too, loses what it loses without it
    def lost(*lights: m.Light) -> float:
        off, on = resting(grey(plane(None)), ring(), *lights, phi=TILT)
        return linear(off[HOLE].max()) - linear(on[HOLE].max())

    ambient = m.AmbientLight(intensity=0.6)
    alone = lost(ambient)
    assert alone > 0.01
    assert abs(lost(ambient, m.SunLight(m.OUT, intensity=0.6)) - alone) < 0.01


def light_of(picture: np.ndarray) -> float:
    """The light a picture shows: its levels in linear light, summed."""
    c = picture.astype(float) / 255
    return float(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).sum())


def test_a_polished_balls_glint_keeps_its_light_as_the_camera_turns() -> None:
    # a sun's glint on a polished ball is narrower than a pixel: the pixel shows its light over
    # the pixel (the ball's roughness widened by how far its normal turns across the pixel), not
    # its light at the pixel's centre, which the glint misses or hits as the camera turns (it
    # showed under a hundredth of its light, more on some frames); unclipped, the light it sends
    # into the view stays as it is
    def build(scene: m.ThreeDScene) -> None:
        scene.set_camera_orientation(phi=60 * m.DEGREES, theta=-90 * m.DEGREES)
        scene.camera.exposure = 0.002
        ball = m.Sphere(radius=1.0, resolution=(48, 48), stroke_width=0)
        polished = m.Material(metallic=1.0, roughness=0.05)
        scene.add(ball.set_color(m.WHITE).set_material(polished))
        scene.add(m.SunLight(m.OUT + m.LEFT))
        scene.begin_ambient_camera_rotation(rate=0.1)
        scene.wait(0.5)

    shown = frames(build)
    assert max(picture.max() for picture in shown) < 250  # (nothing clipped)
    lights = [light_of(picture) for picture in shown]
    assert min(lights) > 0.3
    assert max(lights) < 1.08 * min(lights)


def bright_disk(
    strength: float, *beside: m.Mobject, fixed: m.Mobject | None = None
) -> np.ndarray:
    """A small white disk lit straight on by a sun, twenty times as bright as white, at the view's
    centre on black, with bloom at `strength`; `beside` it, and `fixed` in the frame."""

    def build(scene: m.ThreeDScene) -> None:
        scene.camera.exposure = 20.0
        scene.camera.bloom = strength
        disk = m.Circle(radius=0.4, stroke_width=0, fill_opacity=1).set_fill(m.WHITE)
        scene.add(disk.set_material(MATTE), m.SunLight(m.OUT, intensity=1.0), *beside)
        if fixed is not None:
            scene.add_fixed_in_frame_mobjects(fixed)
            scene.add(fixed)
        scene.wait(0.1)

    return frames(build)[0].astype(int)


def off_centre(picture: np.ndarray, x: float) -> np.ndarray:
    """The pixel `x` scene units right of the view's centre."""
    return picture[SIZE[1] // 2, SIZE[0] // 2 + int(x * SIZE[1] / 8)]


def dark_square(x: float, z: float = 0.0) -> m.Mobject:
    """A dark blue square a unit across, without a material, at (x, 0, z)."""
    square = m.Square(side_length=1.0, stroke_width=0, fill_opacity=1)
    return square.set_fill(m.BLUE_E).move_to([x, 0.0, z])


def test_bloom_spreads_a_bright_lights_glow_into_the_dark_around_it() -> None:
    near, far = 1.0, 2.0  # (the disk's edge is 0.4 from its centre)
    none, faint, strong = (bright_disk(strength) for strength in (0.0, 0.05, 0.2))
    assert (off_centre(none, near) == 0).all()
    assert (off_centre(none, far) == 0).all()
    # the glow falls off with the distance from the light, and grows with the strength
    assert off_centre(faint, near)[0] > off_centre(faint, far)[0] > 0
    assert off_centre(strong, near)[0] > off_centre(faint, near)[0] + 20
    assert off_centre(strong, far)[0] > off_centre(faint, far)[0]


@pytest.mark.parametrize("kind", ["path", "mesh"])
def test_bloom_keeps_the_light_it_spreads(kind: str) -> None:
    # what the glow spreads, the light leaves: a white disk on a lit black floor (every pixel's
    # light is lit content's, shown as light: no display paint mixed into it), unclipped, shows
    # as much light with half of it spread as without
    def view(strength: float) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.camera.exposure = 0.9
            scene.camera.bloom = strength
            disk = (
                m.Circle(radius=0.6, stroke_width=0, fill_opacity=1)
                if kind == "path"
                else m.Sphere(radius=0.6, resolution=(32, 32), stroke_width=0)
            )
            floor = m.Square(side_length=20, stroke_width=0, fill_opacity=1)
            scene.add(floor.set_fill(m.BLACK).shift(0.01 * m.IN).set_material(MATTE))
            scene.add(disk.set_color(m.WHITE).set_material(MATTE))
            scene.add(m.SunLight(m.OUT, intensity=1.0))
            scene.wait(0.1)

        return frames(build)[0].astype(int)

    kept, spread = view(0.0), view(0.5)
    # the disk's light left it, and lies around it
    assert (off_centre(spread, 0.0) < off_centre(kept, 0.0) - 10).all()
    assert (off_centre(spread, 1.0) > off_centre(kept, 1.0) + 5).all()
    assert abs(light_of(spread) / light_of(kept) - 1) < 0.005


def test_bloom_spreads_light_not_paint() -> None:
    # display paint is not light: a view without materials shows as it did, and beside a bright
    # light, a white shape without a material has no glow of its own
    def unlit(strength: float) -> np.ndarray:
        def build(scene: m.ThreeDScene) -> None:
            scene.camera.bloom = strength
            scene.add(m.Sphere(radius=1.5, resolution=(24, 24)).set_color(m.BLUE))
            scene.add(m.Square(side_length=2).shift(4 * m.RIGHT).set_fill(m.WHITE, 1))
            scene.wait(0.1)

        return frames(build)[0]

    assert np.array_equal(unlit(0.0), unlit(0.5))
    white = dark_square(-4.5).set_fill(m.WHITE)
    glowing = bright_disk(0.2, white)
    assert (off_centre(glowing, -5.6) == 0).all()  # (0.6 past its edge)
    assert (off_centre(glowing, 1.0) > 40).all()  # (the disk's glow)


def test_the_glow_lies_over_paint_and_what_is_fixed_in_the_frame() -> None:
    # the glow is light over everything the view shows: beside the bright disk, a dark shape
    # without a material and a dark one fixed in the frame show it over their paint
    without, glowing = (
        bright_disk(strength, dark_square(1.2), fixed=dark_square(-1.2))
        for strength in (0.0, 0.2)
    )
    for x in (1.0, -1.0):
        assert (off_centre(glowing, x) > off_centre(without, x) + 40).all()


def test_where_the_view_shows_nothing_the_glow_shows_alone() -> None:
    # over a transparent background the glow is all a pixel shows, as opaque as it is bright (so
    # that laid over black it shows just the glow)
    def view(strength: float) -> np.ndarray:
        def construct(scene: m.ThreeDScene) -> None:
            scene.set_camera_orientation(phi=0.0, theta=-90 * m.DEGREES)
            scene.camera.background_opacity = 0.0
            scene.camera.exposure = 20.0
            scene.camera.bloom = strength
            disk = m.Circle(radius=0.4, stroke_width=0, fill_opacity=1)
            scene.add(disk.set_fill(m.WHITE).set_material(MATTE), m.SunLight(m.OUT))
            scene.wait(0.1)

        return scenes.frames(scenes.scene_3d(construct))[0].astype(int)

    without, glowing = view(0.0), view(0.2)
    assert (off_centre(without, 1.0) == 0).all()
    pixel = off_centre(glowing, 1.0)
    assert pixel[3] > 40
    assert (pixel[:3] <= pixel[3]).all()
    assert pixel[:3].max() == pixel[3]


def test_what_hides_a_light_hides_its_glow() -> None:
    # the glow is spread from the light the view shows: a shape nearer the camera, over the
    # bright disk, leaves no glow around it; beside the disk, it leaves the disk's
    over = dark_square(0.0, z=1.0).scale(1.2)
    assert np.array_equal(bright_disk(0.2, over), bright_disk(0.0, over))
    beside = dark_square(3.0, z=1.0).scale(1.2)
    assert (off_centre(bright_disk(0.2, beside), -1.0) > 40).all()


def test_a_moving_lights_glow_moves_with_it_unchanged() -> None:
    # the glow does not flicker as its light moves across the pixels: the light it spreads
    # around a small bright disk moving a third of a pixel a frame stays as it is
    def build(scene: m.ThreeDScene) -> None:
        scene.camera.exposure = 20.0
        scene.camera.bloom = 0.1
        disk = m.Circle(radius=0.15, stroke_width=0, fill_opacity=1).set_fill(m.WHITE)
        scene.add(disk.set_material(MATTE), m.SunLight(m.OUT, intensity=1.0))
        scene.play(disk.animate.shift(0.5 * m.RIGHT), run_time=0.5, rate_func=m.linear)

    shown = frames(build)
    y, x = np.mgrid[: SIZE[1], : SIZE[0]]
    glow = []
    for k, picture in enumerate(shown):
        # around the disk, from 0.6 to 1.6 units from its centre
        centre = (SIZE[0] / 2 + 0.5 * k / (len(shown) - 1) * SIZE[1] / 8, SIZE[1] / 2)
        r = np.hypot(x + 0.5 - centre[0], y + 0.5 - centre[1]) / (SIZE[1] / 8)
        glow.append(light_of(picture[..., 0][(r > 0.6) & (r < 1.6)]))
    assert min(glow) > 2.0
    assert max(glow) < 1.08 * min(glow)
