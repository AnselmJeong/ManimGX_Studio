# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Ported from Manim CE 0.21 (MIT); `expand` re-derived as a function of its progress."""

from __future__ import annotations

from warnings import deprecated

__all__ = ["ManimBanner"]
from typing import ClassVar, Literal, Unpack

import numpy as np

from manimgx import constants as cst
from manimgx.animation.easing import ease_in_out_cubic, linear, smooth, squish_rate_func
from manimgx.animation.motion import Create, FadeIn, SpiralIn
from manimgx.animation.timeline import Animation, AnimationGroup, AnimationOptions
from manimgx.mobject import VGroup, override_animation
from manimgx.mobjects.shapes import Circle, Square, Triangle
from manimgx.mobjects.svg import VMobjectFromSVGPath

# the logo's letters as SVG path data, parsed when a banner is made
MANIM_SVG_PATHS = (
    (
        "M4.64259-2.092154L2.739726-6.625156C2.660025-6.824408 2.650062-6.824408"
        " 2.381071-6.824408H.52802C.348692-6.824408 .199253-6.824408"
        " .199253-6.645081C.199253-6.475716 .37858-6.475716"
        " .428394-6.475716C.547945-6.475716 .816936-6.455791"
        " 1.036115-6.37609V-1.05604C1.036115-.846824 1.036115-.408468"
        " .358655-.348692C.169365-.328767 .169365-.18929 .169365-.179328C.169365 0"
        " .328767 0 .508095 0H2.052304C2.231631 0 2.381071 0"
        " 2.381071-.179328C2.381071-.268991 2.30137-.33873"
        " 2.221669-.348692C1.454545-.408468 1.454545-.826899"
        " 1.454545-1.05604V-6.017435L1.464508-6.027397L3.895392-.209215C3.975093-.029888"
        " 4.044832 0 4.104608 0C4.224159 0 4.254047-.079701"
        " 4.303861-.199253L6.744707-6.027397L6.75467-6.017435V-1.05604C6.75467-.846824"
        " 6.75467-.408468 6.07721-.348692C5.88792-.328767 5.88792-.18929"
        " 5.88792-.179328C5.88792 0 6.047323 0 6.22665 0H8.886675C9.066002 0 9.215442 0"
        " 9.215442-.179328C9.215442-.268991 9.135741-.33873"
        " 9.05604-.348692C8.288917-.408468 8.288917-.826899"
        " 8.288917-1.05604V-5.768369C8.288917-5.977584 8.288917-6.41594"
        " 8.966376-6.475716C9.066002-6.485679 9.155666-6.535492"
        " 9.155666-6.645081C9.155666-6.824408 9.006227-6.824408"
        " 8.826899-6.824408H6.90411C6.645081-6.824408 6.625156-6.824408"
        " 6.535492-6.615193L4.64259-2.092154ZM4.343711-1.912827C4.423412-1.743462"
        " 4.433375-1.733499"
        " 4.552927-1.693649L4.11457-.637609H4.094645L1.823163-6.057285C1.77335-6.1868"
        " 1.693649-6.356164"
        " 1.554172-6.475716H2.420922L4.343711-1.912827ZM1.334994-.348692H1.165629C1.185554-.37858"
        " 1.205479-.408468 1.225405-.428394C1.235367-.438356 1.235367-.448319"
        " 1.24533-.458281L1.334994-.348692ZM7.103362-6.475716H8.159402C7.940224-6.22665"
        " 7.940224-5.967621 7.940224-5.788294V-1.036115C7.940224-.856787"
        " 7.940224-.597758 8.169365-.348692H6.884184C7.103362-.597758 7.103362-.856787"
        " 7.103362-1.036115V-6.475716Z"
    ),
    (
        "M1.464508-4.024907C1.464508-4.234122 1.743462-4.393524"
        " 2.092154-4.393524C2.669988-4.393524 2.929016-4.124533"
        " 2.929016-3.516812V-2.789539C1.77335-2.440847 .249066-2.042341"
        " .249066-.916563C.249066-.308842 .71731 .139477 1.354919 .139477C1.92279"
        " .139477 2.381071-.059776 2.929016-.557908C3.038605-.049813 3.257783 .139477"
        " 3.745953 .139477C4.174346 .139477 4.483188-.019925"
        " 4.861768-.428394L4.712329-.637609L4.612702-.537983C4.582814-.508095"
        " 4.552927-.498132 4.503113-.498132C4.363636-.498132 4.293898-.587796"
        " 4.293898-.747198V-3.347447C4.293898-4.184309 3.536737-4.712329"
        " 2.321295-4.712329C1.195517-4.712329 .438356-4.204234"
        " .438356-3.457036C.438356-3.048568 .67746-2.799502"
        " 1.085928-2.799502C1.484433-2.799502 1.763387-3.038605"
        " 1.763387-3.377335C1.763387-3.676214 1.464508-3.88543"
        " 1.464508-4.024907ZM2.919054-.996264C2.650062-.687422 2.450809-.56787"
        " 2.211706-.56787C1.912827-.56787 1.703611-.836862"
        " 1.703611-1.235367C1.703611-1.8132 2.122042-2.231631"
        " 2.919054-2.440847V-.996264Z"
    ),
    (
        "M2.948941-4.044832C3.297634-4.044832 3.466999-3.775841"
        " 3.466999-3.217933V-.806974C3.466999-.438356 3.337484-.278954"
        " 2.998755-.239103V0H5.339975V-.239103C4.951432-.268991 4.851806-.388543"
        " 4.851806-.806974V-3.307597C4.851806-4.164384 4.323786-4.712329"
        " 3.506849-4.712329C2.909091-4.712329 2.450809-4.433375"
        " 2.082192-3.845579V-4.592777H.179328V-4.353674C.617684-4.283935"
        " .707347-4.184309 .707347-3.765878V-.836862C.707347-.418431 .627646-.328767"
        " .179328-.239103V0H2.580324V-.239103C2.211706-.288917 2.092154-.438356"
        " 2.092154-.806974V-3.466999C2.092154-3.576588 2.530511-4.044832"
        " 2.948941-4.044832Z"
    ),
    (
        "M2.15193-4.592777H.239103V-4.353674C.67746-4.26401 .767123-4.174346"
        " .767123-3.765878V-.836862C.767123-.428394 .697385-.348692"
        " .239103-.239103V0H2.6401V-.239103C2.291407-.288917 2.15193-.428394"
        " 2.15193-.806974V-4.592777ZM1.454545-6.884184C1.026152-6.884184"
        " .67746-6.535492 .67746-6.117061C.67746-5.668742 1.006227-5.339975"
        " 1.444583-5.339975S2.221669-5.668742 2.221669-6.107098C2.221669-6.535492"
        " 1.882939-6.884184 1.454545-6.884184Z"
    ),
    (
        "M2.929016-4.044832C3.317559-4.044832 3.466999-3.815691"
        " 3.466999-3.217933V-.806974C3.466999-.398506 3.35741-.268991"
        " 2.988792-.239103V0H5.32005V-.239103C4.971357-.278954 4.851806-.428394"
        " 4.851806-.806974V-3.466999C4.851806-3.576588 5.310087-4.044832"
        " 5.69863-4.044832C6.07721-4.044832 6.22665-3.805729"
        " 6.22665-3.217933V-.806974C6.22665-.388543 6.117061-.268991"
        " 5.738481-.239103V0H8.109589V-.239103C7.721046-.259029 7.611457-.37858"
        " 7.611457-.806974V-3.307597C7.611457-4.164384 7.083437-4.712329"
        " 6.266501-4.712329C5.69863-4.712329 5.32005-4.483188"
        " 4.801993-3.845579C4.503113-4.473225 4.154421-4.712329"
        " 3.526775-4.712329S2.440847-4.443337"
        " 2.062267-3.845579V-4.592777H.179328V-4.353674C.617684-4.293898"
        " .707347-4.174346 .707347-3.765878V-.836862C.707347-.428394 .617684-.318804"
        " .179328-.239103V0H2.550436V-.239103C2.201743-.288917 2.092154-.428394"
        " 2.092154-.806974V-3.466999C2.092154-3.58655 2.530511-4.044832"
        " 2.929016-4.044832Z"
    ),
)


@deprecated("Manim's logo, kept for Manim CE's examples", category=None)
class ManimBanner(VGroup):
    """The Manim logo: a large "M" beside a green circle, a blue square and a red
    triangle, which [create][manimgx.ManimBanner.create] brings in and
    [expand][manimgx.ManimBanner.expand] opens into the banner: the wordmark "Manim"
    beside the shapes.

    The letters are light, for a dark background, unless `dark_theme` is False. The
    letters "anim" are not submobjects until `expand` sets them after the "M", at the
    banner's size wherever it is. Playing [Create][manimgx.Create] on the banner plays
    its `create`.

    Args:
        dark_theme: Whether the letters are light (`#ece6e2`), for a dark background,
            or dark (`#343434`), for a light one.

    Examples:
        ```python
        import manimgx as m


        class ManimBannerExample(m.Scene):
            def construct(self) -> None:
                banner = m.ManimBanner()
                self.play(banner.create())
                self.play(banner.expand())
        ```
    """

    def __init__(self, dark_theme: bool = True):
        import svgelements as se

        super().__init__()
        logo_green = "#81b29a"
        logo_blue = "#454866"
        logo_red = "#e07a5f"
        self.font_color = "#ece6e2" if dark_theme else "#343434"
        self.M = (
            VMobjectFromSVGPath(se.Path(MANIM_SVG_PATHS[0])).flip(cst.RIGHT).center()
        )
        self.M.set(stroke_width=0).scale(
            7 * cst.DEFAULT_FONT_SIZE * cst.SCALE_FACTOR_PER_FONT_POINT
        )
        self.M.set_fill(color=self.font_color, opacity=1).shift(
            2.25 * cst.LEFT + 1.5 * cst.UP
        )
        self.built_m_height = (
            self.M.height
        )  # the banner's scale: its M's height over this
        self.circle = Circle(color=logo_green, fill_opacity=1).shift(cst.LEFT)
        self.square = Square(color=logo_blue, fill_opacity=1).shift(cst.UP)
        self.triangle = Triangle(color=logo_red, fill_opacity=1).shift(cst.RIGHT)
        self.shapes = VGroup(self.triangle, self.square, self.circle)
        self.add(self.shapes, self.M)
        self.move_to(cst.ORIGIN)
        anim = VGroup()  # "anim": sized and set beside the M when the banner expands
        for ind, path in enumerate(MANIM_SVG_PATHS[1:]):
            tex = VMobjectFromSVGPath(se.Path(path)).flip(cst.RIGHT).center()
            tex.set(stroke_width=0).scale(
                cst.DEFAULT_FONT_SIZE * cst.SCALE_FACTOR_PER_FONT_POINT
            )
            if ind > 0:
                tex.next_to(anim, buff=0.01)
            tex.align_to(self.M, cst.DOWN)
            anim.add(tex)
        anim.set_fill(color=self.font_color, opacity=1)
        self.anim = anim

    @override_animation(Create)
    def create(self, run_time: float = 2) -> AnimationGroup:
        """Make the animation that brings the logo in: the shapes spiral in while the
        "M" fades in, from a tenth to six tenths of the run time.

        Both begin at once, so the logo starts from nothing, even if it is already
        shown. [Create][manimgx.Create] plays it for the banner.

        Args:
            run_time: How long it takes, in seconds.

        Returns:
            A new animation.
        """
        return AnimationGroup(
            SpiralIn(self.shapes, run_time=run_time),
            FadeIn(
                self.M,
                run_time=0.6 * run_time,
                rate_func=squish_rate_func(smooth, 1 / 6, 1),
            ),
        )

    def expand(
        self,
        run_time: float = 1.5,
        direction: Literal["left", "right", "center"] = "center",
    ) -> Animation:
        """Make the animation that opens the logo into the banner: the "M" and the
        shapes part, a little too far and back, uncovering "anim" after the "M" to spell
        "Manim".

        It plays from the banner as it is when it begins, scaled or moved: the "M" and
        the shapes part along x over the first two thirds of the run time, eased in and
        out, then settle back by an overshoot, every length in proportion to the
        banner's size. The letters travel with the "M", behind the shapes, each shown
        once the square's middle has passed its own, and come in front where the parts
        are furthest apart and nothing overlaps. Once open, the banner's parts are the
        shapes, the "M" and "anim", in that order.

        Args:
            run_time: How long it takes, in seconds.
            direction: What holds still: the "M" ("right": the banner opens to the
                right), the shapes ("left"), or the banner's middle ("center": each
                moves half as far).

        Returns:
            A new animation.

        Examples:
            ```python
            import manimgx as m


            class ManimBannerExpandExample(m.Scene):
                def construct(self) -> None:
                    banners = [m.ManimBanner().scale(0.5) for _ in range(3)]
                    for banner, y in zip(banners, (2.5, 0, -2.5)):
                        self.add(banner.shift(y * m.UP))
                    self.play(
                        banners[0].expand(direction="left"),
                        banners[1].expand(direction="center"),
                        banners[2].expand(direction="right"),
                    )
            ```
        """
        return _Expand(self, _SHARES[direction], run_time=run_time)


# of the parting, what the wordmark and the shapes each move
_SHARES = {"right": (0.0, 1.0), "center": (-0.5, 0.5), "left": (-1.0, 0.0)}


class _Expand(Animation[ManimBanner]):
    """The logo opening into the banner: a function of its progress, from the banner as it
    begins.

    The wordmark (the M, "anim" set after it) and the shapes part along x by (6.25 + 0.8)·s over
    the first two thirds, eased in and out, then settle back by the 0.8·s overshoot (s: the
    banner's scale, its M's height over the height it is built at). The letters travel with the
    M behind the shapes, each shown once the square's middle has passed its own. Furthest apart
    nothing overlaps: there the letters come in front of the shapes, as the M is. It reorders
    the banner's parts, so it acts on the banner itself, updaters and all (no model).
    """

    defaults: ClassVar[AnimationOptions] = {
        "rate_func": linear,  # its two phases ease themselves
        "suspend_mobject_updating": False,
    }
    parting = 2 / 3  # of its progress; then it settles

    def __init__(
        self,
        banner: ManimBanner,
        shares: tuple[float, float],
        **kwargs: Unpack[AnimationOptions],
    ) -> None:
        self.shares = shares
        super().__init__(banner, **kwargs)

    def begin(self) -> None:
        b = self.mobject
        scale = b.M.height / b.built_m_height
        b.anim.height = 0.75748 * b.M.height
        b.anim.next_to(b.M, buff=0.06 * scale).align_to(b.M, cst.DOWN)
        self.settled, self.overshoot = 6.25 * scale, 0.8 * scale
        square = b.square.get_x()
        self.letters = [  # each: how far apart the square passes it; its paints
            (letter, letter.get_x() - square, letter.paint, letter.set_opacity(0).paint)
            for letter in b.anim
        ]
        self.moving = [  # each leaf: where it begins, its share of the parting
            (leaf, leaf._geometry, share)
            for share, part in zip(self.shares, (VGroup(b.M, b.anim), b.shapes))
            for leaf in part.family_members_with_points()
        ]
        b.add_to_back(b.anim)
        self.take()

    def interpolate_mobject(self, alpha: float) -> None:
        t = self.rate_func(alpha)
        parting = t < self.parting
        furthest = self.settled + self.overshoot
        apart = (
            furthest * ease_in_out_cubic(t / self.parting)
            if parting
            else furthest
            - self.overshoot * smooth((t - self.parting) / (1 - self.parting))
        )
        for leaf, geometry, share in self.moving:
            leaf._geometry = geometry.translated(np.array([share * apart, 0.0, 0.0]))
        for letter, shown_at, shown, unseen in self.letters:
            letter.paint = shown if not parting or apart > shown_at else unseen
        b = self.mobject
        b.submobjects = [b.anim, b.shapes, b.M] if parting else [b.shapes, b.M, b.anim]
