import manimgx as m

NUM_BLOCKS = 4


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Blockchain: each block hashes the previous").to_edge(
            m.UP, buff=0.4
        )
        self.play(m.Write(title))

        blocks: list[m.VGroup] = []
        arrows = m.VGroup()
        for i in range(NUM_BLOCKS):
            outer = m.Rectangle(width=2.2, height=1.9, color=m.BLUE, stroke_width=2)
            header = m.Tex(f"Block {i}", color=m.WHITE).scale(0.7)
            data = m.Tex("data...", color=m.GREY).scale(0.5)
            prev = m.Tex(
                f"prev: {('0' * 4) if i == 0 else f'a{i - 1}f3'}",
                color=m.GREEN,
            ).scale(0.45)
            inner = m.VGroup(header, data, prev).arrange(m.DOWN, buff=0.18)
            block = m.VGroup(outer, inner)
            inner.move_to(outer.get_center())
            block.move_to([-5 + i * 3.0, 0, 0])
            blocks.append(block)
            if i > 0:
                arrows.add(
                    m.Arrow(
                        blocks[i - 1].get_right(),
                        block.get_left(),
                        color=m.YELLOW,
                        buff=0.1,
                        stroke_width=4,
                    )
                )

        for i, block in enumerate(blocks):
            self.play(m.FadeIn(block), run_time=0.4)
            if i > 0:
                self.play(m.GrowArrow(arrows[i - 1]), run_time=0.3)
        self.wait(2.0)
