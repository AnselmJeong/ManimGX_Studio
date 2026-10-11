# Source: manim/animation (multiple files)
import manimgx as m


class AnimationKwargAliasesExample(m.Scene):
    def construct(self):
        # AnimatedBoundary accepts `vmobject=` (CE positional name).
        text = m.Text("hello")
        boundary = m.AnimatedBoundary(vmobject=text, cycle_rate=2)
        self.add(text, boundary)

        # GrowArrow accepts `arrow=` (CE positional name).
        arrow = m.Arrow(m.LEFT * 2 + m.UP * 2, m.UP * 2)
        self.add(arrow)
        self.play(m.GrowArrow(arrow=arrow), run_time=0.4)

        # Flash accepts `point=` (CE positional name).
        self.play(m.Flash(point=m.RIGHT * 2 + m.UP), run_time=0.4)

        # AnimationGroup accepts `group=` to set the group attribute.
        sq = m.Square().shift(m.DOWN * 2)
        cir = m.Circle().shift(m.DOWN * 2 + m.RIGHT * 2)
        self.play(
            m.AnimationGroup(
                m.FadeIn(sq),
                m.FadeIn(cir),
                group=m.VGroup(sq, cir),
                run_time=0.4,
            )
        )

        # ChangeDecimalToValue and ChangingDecimal accept `decimal_mob=`.
        dec1 = m.DecimalNumber(0).shift(m.LEFT * 3 + m.DOWN * 2)
        dec2 = m.DecimalNumber(0).shift(m.LEFT * 3 + m.DOWN * 3)
        self.add(dec1, dec2)
        self.play(
            m.ChangeDecimalToValue(decimal_mob=dec1, target_number=5.0),
            m.ChangingDecimal(decimal_mob=dec2, number_update_func=lambda a: 3 * a),
            run_time=0.4,
        )

        # ChangeSpeed accepts `anim=`.
        spinner = m.Square().shift(m.RIGHT * 3 + m.DOWN * 2)
        self.add(spinner)
        self.play(
            m.ChangeSpeed(
                anim=m.Rotate(spinner, angle=m.PI, run_time=0.4),
                speedinfo={0.5: 0.5},
            )
        )

        # UpdateFromFunc accepts `update_function=` (CE name).
        marker = m.Square(side_length=0.4).shift(m.LEFT * 2 + m.DOWN * 3)
        self.add(marker)
        self.play(
            m.UpdateFromFunc(
                marker,
                update_function=lambda mob: mob.set_fill(m.RED, opacity=1.0),
            ),
            run_time=0.2,
        )
