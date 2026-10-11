# Source: manim/mobject/types/vectorized_mobject.py
from collections.abc import Hashable

import manimgx as m


class ShapesWithVDict(m.Scene):
    def construct(self):
        square = m.Square().set_color(m.RED)
        circle = m.Circle().set_color(m.YELLOW).next_to(square, m.UP)

        # create dict from list of tuples each having key-mobject pair
        pairs = [("s", square), ("c", circle)]
        my_dict = m.VDict(pairs, show_keys=True)

        # display it just like a VGroup
        self.play(m.Create(my_dict))
        self.wait()

        text = m.Tex("Some text").set_color(m.GREEN).next_to(square, m.DOWN)

        # add a key-value pair by wrapping it in a single-element list of tuple
        # after attrs branch is merged, it will be easier like `.add(t=text)`
        my_dict.add([("t", text)])
        self.wait()

        rect = m.Rectangle().next_to(text, m.DOWN)
        # can also do key assignment like a python dict
        my_dict["r"] = rect

        # access submobjects like a python dict
        my_dict["t"].set_color(m.PURPLE)
        self.play(my_dict["t"].animate.scale(3))
        self.wait()

        # also supports python dict styled reassignment
        my_dict["t"] = m.Tex("Some other text").set_color(m.BLUE)
        self.wait()

        # remove submobject by key
        my_dict.remove("t")
        self.wait()

        self.play(m.Uncreate(my_dict["s"]))
        self.wait()

        self.play(m.FadeOut(my_dict["c"]))
        self.wait()

        self.play(m.FadeOut(my_dict["r"], shift=m.DOWN))
        self.wait()

        # you can also make a VDict from an existing dict of mobjects
        plain_dict: dict[Hashable, m.Mobject] = {
            1: m.Integer(1).shift(m.DOWN),
            2: m.Integer(2).shift(2 * m.DOWN),
            3: m.Integer(3).shift(3 * m.DOWN),
        }

        vdict_from_plain_dict = m.VDict(plain_dict)
        vdict_from_plain_dict.shift(1.5 * (m.UP + m.LEFT))
        self.play(m.Create(vdict_from_plain_dict))

        # you can even use zip
        vdict_using_zip = m.VDict(
            zip(["s", "c", "r"], [m.Square(), m.Circle(), m.Rectangle()])
        )
        vdict_using_zip.shift(1.5 * m.RIGHT)
        self.play(m.Create(vdict_using_zip))
        self.wait()
