---
title: "Camera and 3D"
description: "What the frame shows: pan and zoom over a flat scene, or look at a three-dimensional one from any angle, lit by lights."
---

# Camera and 3D

```python fold title="The film's code"
import manimgx as m


class CameraAnd3DHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
        axes = m.ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-2, 2])
        sphere = m.Sphere(radius=1.2, resolution=(32, 32)).set_color(m.BLUE)
        torus = m.Torus(major_radius=2.2, minor_radius=0.2).set_color(m.YELLOW)
        self.add(m.SunLight(4 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.3))
        self.add(axes, sphere, torus)
        self.begin_ambient_camera_rotation(rate=0.4)
        self.wait(4)
```

The camera decides what the video shows. Its frame is a rectangle in the scene: the frame
that positions are measured in. Move the frame, and the view moves with it; scale it, and
the view zooms. In three dimensions, the camera looks at the frame from an angle that you
choose, and turns around it while the scene plays.

Every mobject has three coordinates, so flat mobjects show in 3D too. Surfaces and solids are
made for it, and lights shade them.

<div class="grid cards mx-cards" markdown>

-   ![](film:CameraHero)

    [**Camera**](camera.md)

    ---

    The frame: pan and zoom. The look of the picture, and what stays fixed on the screen.

-   ![](film:ThreeDScenesHero)

    [**3D scenes**](three-d-scenes.md)

    ---

    Look at a scene from any angle, move the camera, turn it around the scene.

-   ![](film:SurfacesHero)

    [**Surfaces and solids**](surfaces-and-solids.md)

    ---

    Surfaces of functions, spheres, tori, cylinders, cones, cubes and polyhedra.

-   ![](film:LightsHero)

    [**Lights and materials**](lights-and-materials.md)

    ---

    Sun, bulbs, spotlights and the sky, and how surfaces reflect them.

</div>
