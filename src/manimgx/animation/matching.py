# SPDX-FileCopyrightText: 2026 Academa, Inc.
# SPDX-FileCopyrightText: 2024 the Manim Community Developers
# SPDX-FileCopyrightText: 2018 3Blue1Brown LLC
# SPDX-License-Identifier: MIT

"""Ported from Manim CE 0.21 (MIT)."""

from __future__ import annotations

from warnings import deprecated

__all__ = [
    "TransformMatchingAbstractBase",
    "TransformMatchingShapes",
    "TransformMatchingTex",
]
from collections.abc import Hashable, Mapping
from typing import TYPE_CHECKING, Unpack

import numpy as np

from manimgx.animation.motion import FadeIn, FadeOut, FadeTransformPieces
from manimgx.animation.transform import Transform, TransformOptions
from manimgx.mobject import Group, Mobject
from manimgx.mobjects.text import MathTexPart

from .timeline import AnimationGroup

if TYPE_CHECKING:
    from manimgx.scene import Scene


@deprecated(
    "the base of TransformMatchingShapes and TransformMatchingTex: use either",
    category=None,
)
class TransformMatchingAbstractBase(AnimationGroup):
    """The base of the transforms that match the parts of two mobjects: the parts that
    match move to their counterparts, and the others fade.

    Each part of `mobject` and of `target_mobject` has a key
    ([`get_mobject_key`][manimgx.TransformMatchingAbstractBase.get_mobject_key]). The
    parts of `mobject` whose key a part of the target has transform into the target's
    parts with that key; the others fade out, moving to where the target's unmatched
    parts are, as those fade in in their places (unless `transform_mismatches` or
    `fade_transform_mismatches` has them transform). Parts are matched in their own
    order, so the result is the same in every run. When the animation finishes,
    `target_mobject` is in the scene in the place of `mobject`, which is left out of it
    as it was. A subclass says what the parts are
    ([`get_mobject_parts`][manimgx.TransformMatchingAbstractBase.get_mobject_parts]) and
    what their keys are.

    Args:
        mobject: The mobject to transform.
        target_mobject: The mobject it becomes.
        transform_mismatches: Whether the unmatched parts transform into the target's
            unmatched parts, rather than fade.
        fade_transform_mismatches: Whether they cross-fade into the target's unmatched
            parts (see [`FadeTransformPieces`][manimgx.FadeTransformPieces]), rather
            than fade.
        key_map: Pairs of keys to match although they differ: the parts of `mobject`
            with the first key cross-fade into the target's parts with the second.
            These matches take precedence over equal keys.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
            each of the animations it plays.
    """

    # the parts are matched in their own order, so the result is the same in every run
    # (CE matched through salted hashes, in set order)

    def __init__[Key: Hashable](
        self,
        mobject: Mobject,
        target_mobject: Mobject,
        transform_mismatches: bool = False,
        fade_transform_mismatches: bool = False,
        key_map: Mapping[Key, Hashable] | None = None,
        **kwargs: Unpack[TransformOptions],
    ):
        source_map = self.get_shape_map(mobject)
        target_map = self.get_shape_map(target_mobject)
        key_mapped_source, key_mapped_target = Group(), Group()
        for key1, key2 in (key_map or {}).items():
            if key1 in source_map and key2 in target_map:
                key_mapped_source.add(source_map.pop(key1))
                key_mapped_target.add(target_map.pop(key2))
        matched = [key for key in source_map if key in target_map]
        anims: list[AnimationGroup | Transform] = [
            Transform(
                Group(*(source_map[k] for k in matched)),
                Group(*(target_map[k] for k in matched)),
                **kwargs,
            )
        ]
        if len(key_mapped_source) > 0:
            anims.append(
                FadeTransformPieces(key_mapped_source, key_mapped_target, **kwargs)
            )
        fade_source = Group(
            *(part for key, part in source_map.items() if key not in target_map)
        )
        fade_target = Group(
            *(part for key, part in target_map.items() if key not in source_map)
        )
        fade_target_copy = fade_target.copy()
        if transform_mismatches:
            kwargs.setdefault("replace_mobject_with_target_in_scene", True)
            anims.append(Transform(fade_source, fade_target, **kwargs))
        elif fade_transform_mismatches:
            anims.append(FadeTransformPieces(fade_source, fade_target, **kwargs))
        else:
            anims.append(FadeOut(fade_source, target_position=fade_target, **kwargs))
            anims.append(
                FadeIn(fade_target_copy, target_position=fade_target, **kwargs)
            )
        super().__init__(*anims)
        self.to_remove = [mobject, fade_target_copy]
        self.to_add = target_mobject

    def get_shape_map(self, mobject: Mobject) -> dict[Hashable, Group]:
        """Gather the parts of a mobject by their keys.

        Returns:
            For each key, in the order its first part comes, a group of the parts with
            that key, in order.
        """
        groups: dict[Hashable, tuple[Group, list[Mobject]]] = {}
        for part in self.get_mobject_parts(mobject):
            key = self.get_mobject_key(part)
            if (bucket := groups.get(key)) is None:
                groups[key] = bucket = Group(), []
            bucket[1].append(part)
        return {key: group.add(*parts) for key, (group, parts) in groups.items()}

    def _end(self, i: int) -> None:
        # its parts leave the scene with the whole, as it finishes (`clean_up_from_scene`)
        self.done.add(i)
        self.animations[i].finish()

    def clean_up_from_scene(self, scene: Scene) -> None:
        for anim in self.animations:
            anim.interpolate(0)
        # what its parts brought into the scene, and every part of the mobject it
        # transformed, wherever the parts brought them
        scene.remove(
            *(anim.mobject for anim in self.animations),
            *(part for mob in self.to_remove for part in mob.get_family()),
        )
        scene.add(self.to_add)

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        """The parts of a mobject that are matched: a subclass says what they are.

        Returns:
            Its parts, in order.
        """
        raise NotImplementedError("To be implemented in subclass.")

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        """The key a part is matched by: a subclass says what it is.

        Args:
            mobject: A part.

        Returns:
            Its key: parts with equal keys match.
        """
        raise NotImplementedError("To be implemented in subclass.")


class TransformMatchingShapes(TransformMatchingAbstractBase):
    """Transform a mobject into another by matching their shapes: each part moves to a
    part of the same shape, and the others fade.

    The parts are the members with points (the letters of a text); two match when they
    have the same shape, whatever their size and place (their points, centered and
    scaled to a height of 1, agree to 3 decimals). So a text becomes its anagram letter
    by letter. When the animation finishes, `target_mobject` is in the scene in the
    place of `mobject`.

    Args:
        mobject: The mobject to transform.
        target_mobject: The mobject it becomes.
        transform_mismatches: Whether the unmatched parts transform into the target's
            unmatched parts, rather than fade.
        fade_transform_mismatches: Whether they cross-fade into the target's unmatched
            parts (see [`FadeTransformPieces`][manimgx.FadeTransformPieces]), rather
            than fade.
        key_map: Pairs of keys to match although they differ: the parts of `mobject`
            with the first key cross-fade into the target's parts with the second.
            These matches take precedence over equal keys.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
            each of the animations it plays.

    Examples:
        ```python
        import manimgx as m


        class TransformMatchingShapesExample(m.Scene):
            def construct(self) -> None:
                source = m.Text("the morse code", font_size=96)
                target = m.Text("here come dots", font_size=96, color=m.YELLOW)
                self.add(source)
                self.play(
                    m.TransformMatchingShapes(source, target, path_arc=m.PI / 2),
                    run_time=2,
                )
                self.wait(0.5)
        ```
    """

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        return mobject.family_members_with_points()

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        # the shape itself (centered, unit height, to 3 decimals): its bytes, not their
        # hash
        shape = mobject.copy().center().set(height=1)
        return (np.round(shape.points, 3) + 0.0).tobytes()


class TransformMatchingTex(TransformMatchingAbstractBase):
    """Transform a formula into another by matching their parts: each part moves to a
    part written the same way, and the others fade.

    The parts of a [`MathTex`][manimgx.MathTex] are the strings it is made of: the
    arguments it is given and what `{{…}}` sets apart in them, split further at its
    `substrings_to_isolate` and at the strings of its `tex_to_color_map` (a group's
    parts are its members'). Two parts
    match when their strings are the same, so give each term that should travel as an
    argument of its own. When the animation finishes, `target_mobject` is in the scene
    in the place of `mobject`.

    Args:
        mobject: The formula to transform: a `MathTex`, or a group of them.
        target_mobject: The formula it becomes.
        transform_mismatches: Whether the unmatched parts transform into the target's
            unmatched parts, rather than fade.
        fade_transform_mismatches: Whether they cross-fade into the target's unmatched
            parts (see [`FadeTransformPieces`][manimgx.FadeTransformPieces]), rather
            than fade.
        key_map: Pairs of strings to match although they differ: the parts of `mobject`
            written the first way cross-fade into the target's parts written the second.
            These matches take precedence over equal keys.
        **kwargs: [Transform options][manimgx.animation.transform.TransformOptions] for
            each of the animations it plays.

    Examples:
        ```python
        import manimgx as m


        class TransformMatchingTexExample(m.Scene):
            def construct(self) -> None:
                before = m.MathTex("a^2", "+", "b^2", "=", "c^2", font_size=120)
                after = m.MathTex("a^2", "=", "c^2", "-", "b^2", font_size=120)
                self.add(before)
                self.play(
                    m.TransformMatchingTex(before, after, path_arc=m.PI / 2), run_time=2
                )
                self.wait(0.5)
        ```
    """

    @staticmethod
    def get_mobject_parts(mobject: Mobject) -> list[Mobject]:
        if isinstance(mobject, Group):
            return [
                p
                for s in mobject.submobjects
                for p in TransformMatchingTex.get_mobject_parts(s)
            ]
        return mobject.submobjects

    @staticmethod
    def get_mobject_key(mobject: Mobject) -> Hashable:
        assert isinstance(mobject, MathTexPart)
        return mobject.tex_string
