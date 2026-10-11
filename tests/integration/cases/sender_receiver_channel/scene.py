import manimgx as m


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = m.Tex("Information channel").to_edge(m.UP, buff=0.3)
        self.play(m.Write(title))

        sender = m.Rectangle(
            width=2.2,
            height=1.2,
            color=m.BLUE,
            fill_color=m.BLUE,
            fill_opacity=0.3,
            stroke_width=2,
        ).shift(m.LEFT * 4.5)
        sender_label = m.Tex("Sender", color=m.BLUE).move_to(sender.get_center())

        channel = m.Rectangle(
            width=2.6,
            height=1.2,
            color=m.RED,
            fill_color=m.RED,
            fill_opacity=0.3,
            stroke_width=2,
        )
        channel_label = (
            m.Tex("Channel (noise)", color=m.RED)
            .scale(0.7)
            .move_to(channel.get_center())
        )

        receiver = m.Rectangle(
            width=2.2,
            height=1.2,
            color=m.GREEN,
            fill_color=m.GREEN,
            fill_opacity=0.3,
            stroke_width=2,
        ).shift(m.RIGHT * 4.5)
        receiver_label = m.Tex("Receiver", color=m.GREEN).move_to(receiver.get_center())

        arr1 = m.Arrow(sender.get_right(), channel.get_left(), buff=0.1)
        arr2 = m.Arrow(channel.get_right(), receiver.get_left(), buff=0.1)

        self.play(m.Create(sender), m.Write(sender_label))
        self.play(m.GrowArrow(arr1))
        self.play(m.Create(channel), m.Write(channel_label))
        self.play(m.GrowArrow(arr2))
        self.play(m.Create(receiver), m.Write(receiver_label))
        self.wait(2.0)
