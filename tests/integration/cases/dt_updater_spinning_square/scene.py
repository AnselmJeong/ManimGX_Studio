"""Show a square spinning in place for 2 seconds."""

import manimgx as m

# Eval metadata (most evals leave these empty)
EVAL_MUST_NOT_USE: set[str] = set()
EVAL_EXEMPT: set[str] = set()
EVAL_NOTES: str = (
    "Tests the (mob, dt) signature for autonomous motion -- agent must use this "
    "signature, not (mob) alone with no tracker."
)


class TeacherScene(m.Scene):
    def construct(self):
        sq = m.Square(color=m.BLUE).scale(1.3)
        sq.add_updater(lambda mob, dt: mob.rotate(dt * 90 * m.DEGREES))

        self.add(sq)
        self.wait(2.0)
        self.wait(0.5)
