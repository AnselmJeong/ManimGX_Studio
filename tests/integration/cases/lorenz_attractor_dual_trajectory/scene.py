import numpy as np

import manimgx as m

# ==========================================
# DESIGN AND CONTENT TOKENS (TUNEABLE)
# ==========================================
BG_COLOR = "#0A0B10"  # Dark space-like background
AXIS_COLOR = "#222530"  # Subdued color for 3D coordinate grid
COLOR_TRAJECTORY_1 = "#17FFF7"  # Glowing vibrant cyan/blue for first particle
COLOR_TRAJECTORY_2 = "#FF2E93"  # Glowing pink/magenta for second particle

# Lorenz System Parameters
SIGMA = 10.0
RHO = 28.0
BETA = 8.0 / 3.0

# Integration Settings
DT = 0.012
NUM_STEPS = 2200
TAIL_LEN = 150  # Shortened to 150 for a clear, elegant "comet with fading tail" look
# ==========================================


class LorenzAttractor(m.ThreeDScene):
    def construct(self):
        # Set dark background
        self.camera.background_color = BG_COLOR

        # Initialize camera orientation
        self.set_camera_orientation(phi=65 * m.DEGREES, theta=-60 * m.DEGREES)

        # -------------------------------------------------------------
        # 1. 2D Fixed Overlay Element Creation (3b1b style)
        # -------------------------------------------------------------
        # Header
        title = m.Tex("The Lorenz Attractor", font_size=36, color="#E8E8E8")
        subtitle = m.Tex(
            "Chaos and the Butterfly Effect", font_size=20, color=COLOR_TRAJECTORY_1
        )
        title.to_edge(m.UP, buff=0.4)
        subtitle.next_to(title, m.DOWN, buff=0.12)
        title_group = m.VGroup(title, subtitle)

        # Scientific Equations
        lorenz_eq = m.MathTex(
            r"\begin{aligned}",
            r"\dot{x} &= \sigma(y - x)\\",
            r"\dot{y} &= x(\rho - z) - y\\",
            r"\dot{z} &= xy - \beta z",
            r"\end{aligned}",
            font_size=16,
            color="#E8E8E8",
        )
        lorenz_eq.to_corner(m.UR, buff=0.4)

        lorenz_params = m.MathTex(
            r"\sigma=10, \ \rho=28, \ \beta=8/3", font_size=14, color=COLOR_TRAJECTORY_1
        ).next_to(lorenz_eq, m.DOWN, buff=0.1)
        eq_group = m.VGroup(lorenz_eq, lorenz_params)

        # Interactive Explanation / Narrative Notes
        note_title = m.Tex(
            "The Butterfly Effect", font_size=20, color=COLOR_TRAJECTORY_2
        )
        note_desc = m.Tex(
            "A deviation of only 0.001 in z-start leads to total divergence.",
            font_size=14,
            color="#A0A5B5",
        )
        note_title.to_corner(m.DL, buff=0.5)
        note_desc.next_to(note_title, m.DOWN, buff=0.1, aligned_edge=m.LEFT)
        note_group = m.VGroup(note_title, note_desc)

        # Register overlay objects so they remain stationary
        self.add_fixed_in_frame_mobjects(title_group, eq_group, note_group)

        # Hide the second explanation note initially
        note_group.set_opacity(0)

        # Show main titles
        self.play(m.Write(title_group), run_time=1.2)
        self.wait(0.3)

        # Show Equations
        self.play(m.FadeIn(eq_group, shift=m.DOWN * 0.1), run_time=1.0)
        self.wait(0.5)

        # -------------------------------------------------------------
        # 2. Coordinate System Preparation (Subtle 3D Grid)
        # -------------------------------------------------------------
        axes = m.ThreeDAxes(
            x_range=[-25, 25, 10],
            y_range=[-25, 25, 10],
            z_range=[-25, 25, 10],
            x_length=6,
            y_length=6,
            z_length=6,
        )
        axes.set_color(AXIS_COLOR)
        axes.set_stroke(width=1.2)
        self.play(m.Create(axes), run_time=1.2)

        # -------------------------------------------------------------
        # 3. Trajectory Pre-computation (RK4 Solver)
        # -------------------------------------------------------------
        def lorenz_deriv(state):
            x, y, z = state
            return np.array([SIGMA * (y - x), x * (RHO - z) - y, x * y - BETA * z])

        def solve_lorenz(start, num_steps, dt):
            points = np.zeros((num_steps, 3))
            points[0] = start
            for i in range(1, num_steps):
                state = points[i - 1]
                k1 = lorenz_deriv(state)
                k2 = lorenz_deriv(state + 0.5 * dt * k1)
                k3 = lorenz_deriv(state + 0.5 * dt * k2)
                k4 = lorenz_deriv(state + dt * k3)
                points[i] = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            return points

        def transform_coords(pts, scale=0.11, shift_z=-25.0):
            transformed = np.zeros_like(pts)
            transformed[:, 0] = pts[:, 0] * scale
            transformed[:, 1] = pts[:, 1] * scale
            transformed[:, 2] = (pts[:, 2] + shift_z) * scale
            return transformed

        # Compute trajectories
        start_1 = np.array([10.0, 10.0, 10.0])
        start_2 = np.array([10.0, 10.0, 10.001])  # 0.001 delta for divergence

        points_1 = transform_coords(solve_lorenz(start_1, NUM_STEPS, DT))
        points_2 = transform_coords(solve_lorenz(start_2, NUM_STEPS, DT))

        # -------------------------------------------------------------
        # 4. Phase 1: Unfolding the First Trajectory
        # -------------------------------------------------------------
        # Start ambient camera rotation
        self.begin_ambient_camera_rotation(rate=0.04)

        time_tracker = m.ValueTracker(1)

        # Path 1 setups: ThreeDVMobject preserves true Z coordinates in ThreeDScene
        path_1 = m.ThreeDVMobject()
        path_1.set_stroke(color=COLOR_TRAJECTORY_1, width=2.4, opacity=0.9)
        self.add(path_1)

        # Updaters for single trace
        def update_path_1(p):
            k = min(int(time_tracker.get_value()), len(points_1))
            if k < 2:
                p.set_points_as_corners([points_1[0], points_1[1]])
                return
            window = points_1[max(0, k - TAIL_LEN) : k]
            p.set_points_as_corners(list(window))

        path_1.add_updater(update_path_1)

        particle_1 = m.always_redraw(
            lambda: m.Dot3D(
                point=points_1[min(int(time_tracker.get_value()), len(points_1) - 1)],
                color="#FFFFFF",
                radius=0.10,
            )
        )
        self.add(particle_1)

        # Play single trace (first 1000 steps)
        self.play(
            time_tracker.animate.set_value(1000), run_time=5.0, rate_func=m.linear
        )
        self.wait(1.0)

        # -------------------------------------------------------------
        # 5. Phase 2: Double Trajectory & Divergence (The Butterfly Effect)
        # -------------------------------------------------------------
        # Fade out Phase 1 items and reveal butterfly notes
        self.play(
            m.FadeOut(path_1),
            m.FadeOut(particle_1),
            note_group.animate.set_opacity(1.0),
            run_time=1.0,
        )

        # Reset time tracking
        time_tracker.set_value(1)

        # Reconstruct path_1, construct path_2 as ThreeDVMobjects
        path_1 = m.ThreeDVMobject()
        path_1.set_stroke(color=COLOR_TRAJECTORY_1, width=2.2, opacity=0.9)

        path_2 = m.ThreeDVMobject()
        path_2.set_stroke(color=COLOR_TRAJECTORY_2, width=2.2, opacity=0.9)

        self.add(path_1, path_2)

        # Updaters for dual trace
        def update_path_1_dual(p):
            k = min(int(time_tracker.get_value()), len(points_1))
            if k < 2:
                p.set_points_as_corners([points_1[0], points_1[1]])
                return
            window = points_1[max(0, k - TAIL_LEN) : k]
            p.set_points_as_corners(list(window))

        def update_path_2_dual(p):
            k = min(int(time_tracker.get_value()), len(points_2))
            if k < 2:
                p.set_points_as_corners([points_2[0], points_2[1]])
                return
            window = points_2[max(0, k - TAIL_LEN) : k]
            p.set_points_as_corners(list(window))

        path_1.add_updater(update_path_1_dual)
        path_2.add_updater(update_path_2_dual)

        particle_1 = m.always_redraw(
            lambda: m.Dot3D(
                point=points_1[min(int(time_tracker.get_value()), len(points_1) - 1)],
                color="#FFFFFF",
                radius=0.09,
            )
        )
        particle_2 = m.always_redraw(
            lambda: m.Dot3D(
                point=points_2[min(int(time_tracker.get_value()), len(points_2) - 1)],
                color="#FFFFFF",
                radius=0.09,
            )
        )
        self.add(particle_1, particle_2)

        # Trace both from the beginning all the way to complete divergence
        self.play(
            time_tracker.animate.set_value(NUM_STEPS), run_time=11.0, rate_func=m.linear
        )
        self.wait(1.5)
