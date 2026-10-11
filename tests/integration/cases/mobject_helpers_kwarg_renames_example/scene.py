# Source: manim/mobject/mobject.py
import manimgx as m


def _noop_updater(mob, dt):
    del mob, dt


class _OverrideClass(m.Square):
    def fancy_action(self):
        return self


def _fancy_override(self):
    return m.Wait(run_time=0)


_OverrideClass.add_animation_override(m.FadeIn, _fancy_override)


class MobjectHelpersKwargRenamesExample(m.Scene):
    def construct(self):
        anchor = m.Square(side_length=1).set_color(m.YELLOW)
        anchor.move_to(point_or_mobject=[-2.0, 0.0, 0.0])
        self.add(anchor)

        follower = m.Circle(radius=0.5).set_color(m.BLUE)
        follower.next_to(mobject_or_point=anchor, direction=m.RIGHT, buff=0.3)
        self.add(follower)

        edge_pinned = m.Square(side_length=0.6).set_color(m.RED)
        edge_pinned.to_edge(edge=m.UP)
        corner_pinned = m.Square(side_length=0.6).set_color(m.GREEN)
        corner_pinned.to_corner(corner=m.UR)
        self.add(edge_pinned, corner_pinned)

        scaled = m.Square(side_length=1).set_color(m.PURPLE)
        scaled.scale(scale_factor=0.5, about_edge=m.LEFT)
        self.add(scaled)

        rotated = m.Square(side_length=0.8).set_color(m.ORANGE).shift(m.DOWN)
        rotated.rotate(0.6, about_edge=m.LEFT)
        self.add(rotated)

        flipped = m.Triangle().scale(0.4).shift(m.DOWN * 2)
        flipped.flip(axis=m.UP, about_point=[0.0, -2.0, 0.0])
        self.add(flipped)

        stretched = m.Square(side_length=1).set_color(m.PINK).shift(m.DOWN * 3)
        stretched.stretch(2.0, 0, about_edge=m.LEFT)
        self.add(stretched)

        aligned = m.Square(side_length=0.5).set_color(m.WHITE)
        aligned.align_to(mobject_or_point=anchor, direction=m.UP)
        self.add(aligned)

        layered = m.Square(side_length=0.5).set_color(m.RED)
        layered.set_z_index(z_index_value=2)
        self.add(layered)

        coord_setter = m.Square(side_length=0.3).set_color(m.WHITE)
        coord_setter.set_x(1.5, direction=m.LEFT)
        coord_setter.set_y(0.5, direction=m.UP)
        coord_setter.set_z(0.0, direction=m.OUT)
        self.add(coord_setter)

        applied = m.Square(side_length=0.5).set_color(m.GREEN).shift(m.UP * 2)
        applied.apply_function(
            lambda p: p, about_point=[0.0, 2.0, 0.0], about_edge=None
        )
        self.add(applied)

        becomes = m.Square().set_color(m.BLUE)
        becomes.become(
            mobject=m.Circle(),
            match_height=True,
            match_width=True,
            match_depth=False,
            match_center=True,
            stretch=False,
        )
        self.add(becomes)

        carrier = m.Square().set_color(m.WHITE).shift(m.LEFT * 3)
        carrier.add_updater(update_function=_noop_updater, index=0, call_updater=False)
        carrier.remove_updater(update_function=_noop_updater)
        carrier.add_updater(_noop_updater)
        carrier.clear_updaters(recursive=True)
        self.add(carrier)

        named = m.Mobject(target=None, name="anchor_mobject")
        self.add(named)

        override_demo = _OverrideClass(side_length=0.4).set_color(m.YELLOW)
        override_demo.to_corner(m.DL)
        self.add(override_demo)

        self.wait()
