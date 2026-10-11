# Examples

Forty-eight short films made with ManimGX, each one Python file that needs only numpy. Every
number on screen is computed as the film plays.

With ManimGX installed (`pip install manimgx`), render one at 1920×1080, 60 fps:

```sh
manimgx render examples/quadratic_formula.py   # writes examples/QuadraticFormula.mp4
```

## Equations and proofs

- [The quadratic formula](quadratic_formula.py): Completing the square turns an equation
  into a picture. Each term keeps its color as rectangles move and the quadratic formula
  emerges.
- [Pythagoras by rearrangement](pythagoras.py): Moving four right triangles reveals why
  a² + b² = c². The triangles and their enclosing square keep the same area throughout.
- [Unrolling a circle](circle_area.py): Thin rings unroll into strips that stack into a
  triangle. Its base is 2πr and its height is r, so its area is πr².
- [Euler's identity as a walk](euler_identity.py): The terms of the exponential series
  spiral toward −1 in the complex plane. Letting the angle vary carries their sum around
  the unit circle.

## Calculus

- [What a derivative measures](derivative.py): A secant becomes a tangent as two points on
  a curve come together. The tangent's changing slope traces the derivative's graph.
- [Rectangles become an integral](riemann_sums.py): Thinner rectangles bring a sum closer
  to the area under a curve. Each refinement splits the rectangles and updates the
  measured area.
- [Polynomials become the sine](taylor_series.py): Each new Taylor term makes a polynomial
  follow more of the sine wave. The growing formula and its graph change together.
- [A circle draws sine and cosine](unit_circle.py): A rotating radius traces sine and
  cosine from its height and reach. The right triangle inside the circle also shows why
  sin²θ + cos²θ = 1.

## Planes and surfaces

- [A matrix moves the plane](linear_maps.py): A matrix carries a grid, its basis arrows
  and a unit square together. The determinant measures the changing area as the plane
  shears, rotates, flattens and turns over.
- [Complex functions bend the plane](complex_maps.py): A grid bends under z², the
  exponential and the sine. Straight lines become parabolas, circles and rays as each
  point travels to its image.
- [Landscapes from formulas](surface_plots.py): A flat grid rises into an egg crate, a
  saddle and a bell. Each surface is computed from its formula and bends into the next
  as the camera turns.

## Patterns and surprises

- [Circles draw π](fourier_pi.py): A chain of rotating arrows traces the outline of π.
  The arrows' lengths and phases come from the letter's Fourier coefficients, and the
  camera follows the pen for a closer look.
- [Times tables on a circle](times_tables.py): Joining numbers to their multiples around
  a circle draws cardioids and other curves. Changing the multiplier continuously makes
  the pattern turn, split and fold.
- [Two blocks count π](colliding_blocks.py): Elastic collisions between two blocks and
  a wall count out digits of π. Every collision is simulated, with the mass ratio setting
  how many digits appear.
- [Prime spirals](prime_spirals.py): Plotting primes at distance p and angle p reveals
  spirals that become rays as the camera pulls back. Close approximations to 2π explain
  the changing patterns.
- [Hilbert's space-filling curve](hilbert_curve.py): A path visits every cell of a finer
  and finer square grid. Four smaller copies, turned and joined, form the next order of
  the Hilbert curve.
- [A Galton board](galton_board.py): Repeated left-or-right bounces build a bell-shaped
  pile of balls. The measured counts approach the binomial distribution beneath the pegs.
- [The Lorenz attractor](lorenz_attractor.py): Eight nearly identical starting points
  trace a butterfly and then drift apart. Both paths follow the Lorenz equations, showing
  how a deterministic system can be chaotic.

## Geometry and topology

- [The Hopf fibration](hopf_fibration.py): The 3-sphere is made of circles, and every two of
  them link once. Each circle lies over one point of the ordinary sphere, and the film
  measures how every pair links.
- [A torus turned inside out](clifford_torus.py): A quarter turn in four dimensions turns a
  torus inside out. Halfway, it passes through infinity as a plane with a handle.
- [Bending without stretching](catenoid_helicoid.py): A helicoid rolls up into a catenoid
  without stretching. Distances and curvature stay the same at every step (Gauss's Theorema
  Egregium).
- [A kaleidoscope on the sphere](kaleidoscope_sphere.py): Three mirrors tile the sphere with
  120 triangles. One point and its reflections make the icosahedron, the dodecahedron and the
  solids between them.
- [Stars in the Menger sponge](menger_slice.py): Cut through its center, the Menger sponge
  is full of six-pointed stars. The cut, across a long diagonal, is a hexagon.
- [Cubes and the arctic circle](lozenge_cubes.py): A random tiling by rhombi is a pile of
  cubes seen along a diagonal. Outside a circle, the tiling freezes.
- [Where √z lives](riemann_surfaces.py): The square root changes sign after one loop around
  0, so it lives on two sheets. The logarithm climbs with every loop: an endless staircase.
- [Prince Rupert's cube](rupert_cube.py): A cube can pass through a hole in an identical cube
  (Prince Rupert, 1693). In 2025, the Noperthedron became the first convex solid that cannot.
- [Why a Taylor series stops](taylor_poles.py): The Taylor series of 1/(1 + x²) stops
  converging at |x| = 1. Two poles at ±i are the reason, and only the complex plane shows
  them.
- [Crystals and cones](voronoi_cones.py): Voronoi cells are crystals grown from seeds. Seen
  from above, they are also a field of cones.
- [Period doubling in the Mandelbrot set](bifurcation_mandelbrot.py): The logistic map's
  period doubling rises out of the Mandelbrot set. Each doubling sits on a pinch between two
  bulbs.
- [Circle or square?](sugihara_cylinder.py): A tube's rim is a circle from the front and a
  square in the mirror (Sugihara, 2016). It is one 3D curve, solved from the two views.
- [Stacking oranges](sphere_packing.py): Oranges stack in two ways, and one is a cube standing
  on its corner. A knife through both piles measures that each fills 74.05% of space, the most
  any stack of spheres can (Kepler, 1611; Hales, 1998).

## Physics

- [A spinning top](heavy_top.py): A spinning top doesn't fall: it precesses and nods. Its tip
  traces cusps, loops or waves, depending on how it is launched.
- [The tennis racket flip](tennis_racket.py): A handle spun about its middle axis flips over
  and over (the Dzhanibekov effect). The curves of constant energy show why.
- [Lagrange points](lagrange_points.py): Seen turning with the Earth and the Moon, the
  Lagrange points L4 and L5 are hilltops. Yet the Coriolis force keeps a probe parked on them.
- [The Van Allen belts](van_allen.py): Charged particles spin, bounce and drift in Earth's
  magnetic field. The field is a magnetic bottle, and it holds the radiation belts.
- [Leapfrogging smoke rings](vortex_rings.py): Two smoke rings take turns passing through
  each other (Helmholtz, 1858). Kelvin's impulse, r₁² + r₂², stays the same.
- [Quantum tunneling](wave_packet.py): A quantum particle tunnels through a wall it can't
  cross classically. The measured transmission matches the formula.
- [Cherenkov light](cherenkov_cone.py): A charge moving faster than light does in water
  leaves a cone of blue light. The film measures the cone's angle against the formula.
- [Turing patterns on a torus](turing_torus.py): Two chemicals react and spread on a doughnut,
  and paint it with spots and stripes (Gray–Scott; Turing, 1952).
- [Fireflies in sync](kuramoto_fireflies.py): Past a critical coupling, 2,000 fireflies fall
  into step. How in step they are matches the exact curve.
- [A coral of random walkers](dla_coral.py): 18,000 random walkers wander until they touch
  the cluster and stick. The coral they build has fractal dimension 2.5, measured from how its
  mass grows.

## Engineering

- [Steering a beam with phase](phased_array.py): Fixed antennas steer a beam by phase alone.
  The film shows the live wave field, then the beam in 3D.
- [Miura-ori](miura_ori.py): One pull folds the whole sheet, and no facet bends. It opens in
  both directions at once (a negative Poisson ratio).
- [A harmonic drive](harmonic_drive.py): Strain-wave gearing makes a 30:1 reduction in one
  flat ring. A flexible ring of 60 teeth, inside one of 62, creeps back two teeth per turn.
- [A traffic jam from nowhere](traffic_helix.py): With time as a third dimension, a traffic
  jam is a knot of paths. It moves backward while every car moves forward.

## Computing and learning

- [Noise into a word](score_diffusion.py): Noise flows into a word along the exact score of
  the data. It is a diffusion model with no neural network.
- [A network untangles spirals](neural_untangle.py): A small network, trained as the scene
  starts, lifts one spiral over the other. Then a flat plane separates them.
- [The Game of Life in spacetime](life_spacetime.py): Stack the Game of Life's generations,
  and the glider gun's gliders are staircases. They climb at c/4, a quarter of Life's top
  speed.
