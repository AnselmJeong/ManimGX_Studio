# Source: manim/mobject/mobject.py
import manimgx as m


def _drift_updater(mob, dt):
    mob.shift(0.05 * dt * m.RIGHT)


class MobjectHelpersUpdatersFamilyStyleExample(m.Scene):
    def construct(self):
        leader = m.Square().to_edge(m.LEFT)
        leader.add_updater(_drift_updater)
        self.add(leader)

        sibling = m.Square().to_edge(m.RIGHT)
        sibling.match_updaters(leader)
        self.add(sibling)

        readout = m.Text(
            f"updaters={len(leader.get_updaters())} "
            f"time_based={len(leader.get_time_based_updaters())} "
            f"has_time={leader.has_time_based_updater()} "
            f"family={len(leader.get_family())} "
            f"fam_updaters={len(leader.get_family_updaters())}",
            font_size=16,
        ).to_corner(m.UR)
        self.add(readout)

        leader.suspend_updating()
        leader.resume_updating()

        group_class_label = m.Text(
            f"group={leader.get_group_class().__name__} "
            f"mob_type={leader.get_mobject_type_class().__name__}",
            font_size=14,
        ).to_corner(m.UL)
        self.add(group_class_label)

        gradient_group = m.Group(
            m.Square(side_length=0.4),
            m.Square(side_length=0.4),
            m.Square(side_length=0.4),
            m.Square(side_length=0.4),
        )
        gradient_group.arrange(m.RIGHT, buff=0.1).to_edge(m.DOWN)
        gradient_group.set_submobject_colors_by_gradient(m.RED, m.YELLOW, m.BLUE)
        self.add(gradient_group)

        radial_group = m.Group(
            m.Circle(radius=0.2),
            m.Circle(radius=0.2),
            m.Circle(radius=0.2),
        )
        radial_group.arrange(m.RIGHT, buff=0.3).next_to(gradient_group, m.UP, buff=0.5)
        radial_group.set_submobject_colors_by_radial_gradient(
            radius=1.5, inner_color=m.WHITE, outer_color=m.BLACK
        )
        radial_group.set_colors_by_radial_gradient(
            radius=2.0, inner_color=m.RED, outer_color=m.BLUE
        )
        self.add(radial_group)

        faded = m.Circle().shift(m.DOWN * 1.5)
        faded.fade_to(m.RED, 0.5)
        faded.to_original_color()
        self.add(faded)

        a = m.Square().set_color(m.RED)
        b = m.Square().set_color(m.BLUE)
        mid = m.Square().shift(m.UP)
        mid.interpolate_color(a, b, 0.5)
        self.add(mid)

        point_target = m.Square().shift(m.DOWN * 2)
        derived = point_target.get_point_mobject()
        self.add(derived)

        movable = m.Group(
            m.Dot([0.0, 0.0, 0.0]),
            m.Dot([0.3, 0.0, 0.0]),
            m.Dot([0.6, 0.0, 0.0]),
        ).shift(m.UP * 2)
        movable.apply_function_to_position(lambda p: p + m.RIGHT * 0.1)
        movable.apply_function_to_submobject_positions(lambda p: p + m.UP * 0.05)
        movable.apply_to_family(lambda mob: mob.set_opacity(0.8))
        self.add(movable)

        self.wait()
