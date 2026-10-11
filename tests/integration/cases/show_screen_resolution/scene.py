# Source: docs/source/guides/configuration.rst
import manimgx as m


class ShowScreenResolution(m.Scene):
    def construct(self):
        pixel_height = m.config["pixel_height"]  #  1080 is default
        pixel_width = m.config["pixel_width"]  # 1920 is default
        frame_width = m.config["frame_width"]
        frame_height = m.config["frame_height"]
        self.add(m.Dot())
        d1 = m.Line(frame_width * m.LEFT / 2, frame_width * m.RIGHT / 2).to_edge(m.DOWN)
        self.add(d1)
        self.add(m.Text(str(pixel_width)).next_to(d1, m.UP))
        d2 = m.Line(frame_height * m.UP / 2, frame_height * m.DOWN / 2).to_edge(m.LEFT)
        self.add(d2)
        self.add(m.Text(str(pixel_height)).next_to(d2, m.RIGHT))
        self.wait()
