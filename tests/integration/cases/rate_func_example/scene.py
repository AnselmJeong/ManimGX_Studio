# Source: manim/utils/rate_functions.py
# ruff: noqa: B023
import manimgx as m

RATE_FUNCTIONS = (
    m.linear,
    m.smooth,
    m.smoothstep,
    m.smootherstep,
    m.rush_into,
    m.rush_from,
    m.slow_into,
    m.double_smooth,
    m.there_and_back,
    m.there_and_back_with_pause,
    m.running_start,
    m.wiggle,
    m.lingering,
    m.exponential_decay,
    m.ease_in_sine,
    m.ease_out_sine,
    m.ease_in_out_sine,
    m.ease_in_quad,
    m.ease_out_quad,
    m.ease_in_out_quad,
    m.ease_in_cubic,
    m.ease_out_cubic,
    m.ease_in_out_cubic,
    m.ease_in_quart,
    m.ease_out_quart,
    m.ease_in_out_quart,
    m.ease_in_quint,
    m.ease_out_quint,
    m.ease_in_out_quint,
    m.ease_in_expo,
    m.ease_out_expo,
    m.ease_in_out_expo,
    m.ease_in_circ,
    m.ease_out_circ,
    m.ease_in_out_circ,
    m.ease_in_back,
    m.ease_out_back,
    m.ease_in_out_back,
    m.ease_in_elastic,
    m.ease_out_elastic,
    m.ease_in_out_elastic,
    m.ease_in_bounce,
    m.ease_out_bounce,
    m.ease_in_out_bounce,
)


class RateFuncExample(m.Scene):
    def construct(self):
        x = m.VGroup()
        for rate_func in RATE_FUNCTIONS:
            plot = (
                m.ParametricFunction(
                    lambda x: [
                        x,
                        rate_func(x),
                        0,
                    ],
                    t_range=[
                        0,
                        1,
                        0.01,
                    ],
                    use_smoothing=False,
                    color=m.YELLOW,
                )
                .stretch_to_fit_width(1.5)
                .stretch_to_fit_height(1)
            )
            plot_bg = m.SurroundingRectangle(plot).set_color(m.WHITE)
            plot_title = (
                m.Text(rate_func.__name__, weight=m.BOLD)
                .scale(0.5)
                .next_to(plot_bg, m.UP, buff=0.1)
            )
            x.add(m.VGroup(plot_bg, plot, plot_title))
        x.arrange_in_grid(cols=8)
        x.height = m.config.frame_height
        x.width = m.config.frame_width
        x.move_to(m.ORIGIN).scale(0.95)
        self.add(x)
        self.wait()
