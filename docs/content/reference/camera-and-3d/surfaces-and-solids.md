---
title: "Surfaces and solids"
description: "Surfaces of functions, spheres, tori, cylinders, cones, cubes and polyhedra, lines and arrows in space, and meshes."
---

# Surfaces and solids { #manimgx.mobjects.three_d }

```python fold title="The film's code"
import manimgx as m


class SurfacesHero(m.ThreeDScene):
    def construct(self) -> None:
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-50 * m.DEGREES)
        shapes = m.Group(
            m.Sphere(radius=0.9),
            m.Torus(major_radius=0.8, minor_radius=0.3),
            m.Cylinder(radius=0.7, height=1.6),
            m.Cone(base_radius=0.8, height=1.6),
            m.Cube(side_length=1.4),
            m.Icosahedron(edge_length=1.2),
        )
        shapes.arrange_in_grid(rows=2, buff=0.9)
        self.add(m.SunLight(4 * m.UP + 3 * m.OUT), m.AmbientLight(intensity=0.3))
        self.play(m.LaggedStart(*[m.FadeIn(shape) for shape in shapes], lag_ratio=0.15))
        self.wait()
```

A surface is the set of points a function of two numbers makes: `func(u, v)` for u and v over
their ranges. A sphere, a torus, a cylinder and a cone are surfaces with their functions
made for you. A solid with flat faces is a polyhedron, from a cube to an icosahedron. All
show in a [3D scene](three-d-scenes.md), shaded by its lights.

## Surfaces

::: manimgx.Surface
    options:
      heading_level: 3

::: manimgx.Sphere
    options:
      heading_level: 3

::: manimgx.Torus
    options:
      heading_level: 3

::: manimgx.Cylinder
    options:
      heading_level: 3
      inherited_members: [set_direction]

::: manimgx.Cone
    options:
      heading_level: 3
      inherited_members: [set_direction]

## Solids

::: manimgx.Cube
    options:
      heading_level: 3

::: manimgx.Prism
    options:
      heading_level: 3

::: manimgx.Polyhedron
    options:
      heading_level: 3

::: manimgx.Tetrahedron
    options:
      heading_level: 3

::: manimgx.Octahedron
    options:
      heading_level: 3

::: manimgx.Dodecahedron
    options:
      heading_level: 3

::: manimgx.Icosahedron
    options:
      heading_level: 3

::: manimgx.ConvexHull3D
    options:
      heading_level: 3

## Lines and points in space

::: manimgx.Line3D
    options:
      heading_level: 3

::: manimgx.Arrow3D
    options:
      heading_level: 3

::: manimgx.Dot3D
    options:
      heading_level: 3

## Meshes

::: manimgx.MeshMobject
    options:
      heading_level: 3

## Spherical coordinates

::: manimgx.spherical_to_cartesian
    options:
      heading_level: 3

::: manimgx.cartesian_to_spherical
    options:
      heading_level: 3
