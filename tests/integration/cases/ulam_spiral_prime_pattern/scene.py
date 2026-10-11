import numpy as np

import manimgx as m


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def spiral_pos(n: int) -> np.ndarray:
    if n == 1:
        return np.array([0.0, 0.0, 0.0])
    k = int((np.sqrt(n - 1) + 1) / 2)
    if (2 * k - 1) ** 2 >= n:
        k -= 1
    inner = (2 * k + 1) ** 2
    while inner < n:
        k += 1
        inner = (2 * k + 1) ** 2
    side = 2 * k
    offset = (2 * k - 1) ** 2
    pos_along = (n - offset - 1) % side
    side_idx = (n - offset - 1) // side
    if side_idx == 0:
        return np.array([k - pos_along, -k + 1, 0.0])
    if side_idx == 1:
        return np.array([-k + 1, -k + 1 + pos_along, 0.0])
    if side_idx == 2:
        return np.array([-k + 1 + pos_along, k, 0.0])
    return np.array([k, k - pos_along, 0.0])


class TeacherScene(m.Scene):
    def construct(self) -> None:
        title = (
            m.Tex("Ulam spiral: primes highlighted").scale(0.85).to_edge(m.UP, buff=0.3)
        )
        self.play(m.Write(title))

        N = 169
        SCALE = 0.35
        dots = m.VGroup()
        for n in range(1, N + 1):
            pos = spiral_pos(n) * SCALE
            if is_prime(n):
                dots.add(m.Dot(pos, color=m.YELLOW, radius=0.09))
            else:
                dots.add(m.Dot(pos, color=m.GREY, radius=0.04))
        self.play(m.FadeIn(dots), run_time=2.0)
        self.wait(2.0)
