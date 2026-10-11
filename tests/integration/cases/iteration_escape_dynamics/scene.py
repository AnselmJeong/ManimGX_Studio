import manimgx as m
from manimgx.typing import Point3D


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("$z_{n+1} = z_n^2 + c$: trapped vs escaping").to_edge(
            m.UP, buff=0.3
        )
        self.play(m.Write(title))

        plane = (
            m.NumberPlane(
                x_range=[-3, 3, 1],
                y_range=[-2.2, 2.2, 1],
                background_line_style={"stroke_opacity": 0.3, "stroke_color": m.GREY_B},
            )
            .scale(0.85)
            .shift(m.DOWN * 0.3)
        )
        self.play(m.Create(plane))

        c_trap = -0.5 + 0.1j
        z_trap = 0.0j
        trap_pts = []
        for _ in range(12):
            trap_pts.append(plane.coords_to_point(z_trap.real, z_trap.imag))
            z_trap = z_trap * z_trap + c_trap

        c_esc = 0.6 + 0.6j
        z_esc = 0.0j
        esc_pts = []
        for _ in range(6):
            if abs(z_esc) < 3:
                esc_pts.append(plane.coords_to_point(z_esc.real, z_esc.imag))
            z_esc = z_esc * z_esc + c_esc

        def draw_orbit(pts: list[Point3D], color: str) -> m.VGroup:
            g = m.VGroup()
            for i in range(len(pts) - 1):
                g.add(
                    m.Arrow(
                        pts[i],
                        pts[i + 1],
                        color=color,
                        buff=0.04,
                        stroke_width=2.0,
                        max_tip_length_to_length_ratio=0.25,
                    )
                )
            for p in pts:
                g.add(m.Dot(p, color=color, radius=0.05))
            return g

        trap = draw_orbit(trap_pts, m.BLUE)
        esc = draw_orbit(esc_pts, m.RED)

        self.play(m.Create(trap), run_time=1.8)
        self.play(m.Create(esc), run_time=1.2)

        legend1 = (
            m.Tex("trapped", color=m.BLUE).scale(0.7).move_to(m.LEFT * 3 + m.DOWN * 2.8)
        )
        legend2 = (
            m.Tex("escapes to $\\infty$", color=m.RED)
            .scale(0.7)
            .move_to(m.RIGHT * 3 + m.DOWN * 2.8)
        )
        self.play(m.Write(legend1), m.Write(legend2))
        self.wait(1.5)
