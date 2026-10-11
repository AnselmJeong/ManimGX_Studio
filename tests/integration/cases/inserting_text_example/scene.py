# Source: manim/animation/creation.py
import manimgx as m


class InsertingTextExample(m.Scene):
    def construct(self):
        text = m.Text("Inserting", color=m.PURPLE).scale(1.5).to_edge(m.LEFT)
        cursor = m.Rectangle(
            color=m.GREY_A,
            fill_color=m.GREY_A,
            fill_opacity=1.0,
            height=1.1,
            width=0.5,
        ).move_to(text[0])  # Position the cursor

        self.play(m.TypeWithCursor(text, cursor))
        self.play(m.Blink(cursor, blinks=2))
