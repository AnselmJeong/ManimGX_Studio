---
title: "Lights and materials"
description: "The lights of a 3D scene, from the sun to a spotlight, and the materials that say how a surface reflects them."
---

# Lights and materials

```python fold title="The film's code"
import manimgx as m


class LightsHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=70 * m.DEGREES, theta=-45 * m.DEGREES)
        self.add(m.SunLight(5 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.2))
        spheres = m.Group()
        for roughness in [0.2, 0.5, 0.9]:
            sphere = m.Sphere(radius=0.8, resolution=(48, 48)).set_color(m.GOLD)
            spheres.add(
                sphere.set_material(m.Material(metallic=1, roughness=roughness))
            )
        spheres.arrange(buff=0.6)
        self.add(spheres)
        self.wait()
```

A 3D scene is lit by its lights: add them as you add mobjects. A sun lights everything from
one direction; a bulb lights around it, fading with distance; a spotlight lights a cone; the
sky lights everything a little, from all around. Without lights, a scene keeps Manim's
plain shading.

A mobject's material says how its surface reflects light: rough or smooth, plastic or metal.

## Lights

::: manimgx.Light
    options:
      heading_level: 3

::: manimgx.SunLight
    options:
      heading_level: 3

::: manimgx.PointLight
    options:
      heading_level: 3

::: manimgx.SpotLight
    options:
      heading_level: 3

::: manimgx.AmbientLight
    options:
      heading_level: 3

::: manimgx.EnvironmentLight
    options:
      heading_level: 3

## Materials

::: manimgx.Material
    options:
      heading_level: 3

::: manimgx.Mobject.set_material
    options:
      heading_level: 3

::: manimgx.VMobject.set_shade_in_3d
    options:
      heading_level: 3
