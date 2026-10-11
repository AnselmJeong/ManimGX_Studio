# Source: manim/mobject/mobject.py
import manimgx as m


class MobjectHelpersLayoutExample(m.Scene):
    def construct(self):
        bordered = m.Square(side_length=1).set_color(m.YELLOW)
        bordered.align_on_border(m.UP + m.LEFT, buff=0.4)
        self.add(bordered)

        wide = m.Rectangle(width=4.0, height=1.0).set_color(m.BLUE)
        wide.rescale_to_fit(2.0, 0)
        wide.rescale_to_fit(0.6, 1, stretch=True)
        self.add(wide)

        anchor_point = m.Dot(m.ORIGIN).set_color(m.RED)
        target = m.Square(side_length=1).set_color(m.GREEN)
        target.stretch_about_point(2.0, 0, [0.0, 0.0, 0.0])
        self.add(anchor_point, target)

        spread = m.Group(
            m.Circle(radius=0.2),
            m.Circle(radius=0.2),
            m.Circle(radius=0.2),
        )
        spread.arrange(m.RIGHT, buff=0.2)
        spread.space_out_submobjects(1.5)
        self.add(spread)

        off_screen_text = m.Text(
            f"off_screen={bordered.is_off_screen()}", font_size=18
        ).to_corner(m.DR)
        self.add(off_screen_text)

        stack = m.Group(
            m.Square(side_length=0.5).set_color(m.RED),
            m.Square(side_length=0.5).set_color(m.GREEN),
        )
        stack.arrange(m.RIGHT, buff=0.2)
        stack.insert(1, m.Square(side_length=0.5).set_color(m.BLUE))
        stack.arrange(m.RIGHT, buff=0.2)
        stack.to_edge(m.DOWN)
        self.add(stack)

        sortable = m.Group(
            m.Dot([2.0, -1.5, 0.0]).set_color(m.YELLOW),
            m.Dot([-2.0, -1.5, 0.0]).set_color(m.PURPLE),
            m.Dot([0.0, -1.5, 0.0]).set_color(m.ORANGE),
        )
        sortable.sort()
        sortable.sort_submobjects(submob_func=lambda mob: mob.get_x())
        sortable.shuffle()
        self.add(sortable)

        self.wait()
