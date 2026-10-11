# Source: manim/animation (multiple files)
import manimgx as m


class AnimationSuspendMobjectUpdatingExample(m.Scene):
    def construct(self):
        # Each animation accepts `suspend_mobject_updating=` to pause
        # user updaters on the target during the animation.
        a = m.Square().shift(m.LEFT * 3)
        a.add_updater(lambda mob, dt: mob.shift(m.UP * dt * 0.5))
        self.add(a)

        b = m.DecimalNumber(0.0).shift(m.LEFT * 1)
        b.add_updater(lambda mob, dt: mob.set_color(m.YELLOW))
        self.add(b)

        c = m.Square().shift(m.RIGHT * 3)
        c.add_updater(lambda mob, dt: mob.set_color(m.GREEN))
        self.add(c)

        path = m.Circle(radius=1).shift(m.LEFT * 3)

        self.play(
            m.MoveAlongPath(a, path, suspend_mobject_updating=True),
            m.ChangingDecimal(
                b, lambda alpha: 4 * alpha, suspend_mobject_updating=True
            ),
            m.UpdateFromFunc(
                c,
                lambda mob: mob.set_fill(m.PURPLE, opacity=1.0),
                suspend_mobject_updating=True,
            ),
            run_time=1.0,
        )
