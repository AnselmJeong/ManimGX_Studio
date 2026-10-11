# Source: manim/mobject/text/tex_mobject.py
import manimgx as m


class BulletedListExample(m.Scene):
    def construct(self):
        blist = m.BulletedList("Item 1", "Item 2", "Item 3", height=2, width=2)
        blist.set_color_by_tex("Item 1", m.RED)
        blist.set_color_by_tex("Item 2", m.GREEN)
        blist.set_color_by_tex("Item 3", m.BLUE)
        self.add(blist)
        self.wait()
