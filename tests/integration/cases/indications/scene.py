# Source: manim/animation/indication.py
import manimgx as m


class Indications(m.Scene):
    def construct(self):
        indications = [
            m.ApplyWave,
            m.Circumscribe,
            m.Flash,
            m.FocusOn,
            m.Indicate,
            m.ShowPassingFlash,
            m.Wiggle,
        ]
        names = [m.Tex(i.__name__).scale(3) for i in indications]

        self.add(names[0])
        for i in range(len(names)):
            if indications[i] is m.Flash:
                self.play(m.Flash(m.UP))
            elif indications[i] is m.ShowPassingFlash:
                self.play(m.ShowPassingFlash(m.Underline(names[i])))
            else:
                self.play(indications[i](names[i]))
            self.play(
                m.AnimationGroup(
                    m.FadeOut(names[i], shift=m.UP * 1.5),
                    m.FadeIn(names[(i + 1) % len(names)], shift=m.UP * 1.5),
                )
            )
