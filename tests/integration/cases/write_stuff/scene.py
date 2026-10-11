# Source: example_scenes/basic.py
import manimgx as m


class WriteStuff(m.Scene):
    def construct(self):
        example_text = m.Tex("This is a some text", tex_to_color_map={"text": m.YELLOW})
        example_tex = m.MathTex(
            r"\sum_{k=1}^\infty {1 \over k^2} = {\pi^2 \over 6}",
        )
        group = m.VGroup(example_text, example_tex)
        group.arrange(m.DOWN)
        group.width = m.config["frame_width"] - 2 * m.LARGE_BUFF

        self.play(m.Write(example_text))
        self.play(m.Write(example_tex))
        self.wait()
