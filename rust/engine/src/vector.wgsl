// A view's paths, drawn exactly: every pixel's coverage is the area of the object inside it, computed
// from the control points; no tessellation, no stencil, no multisampling. A path in a 3D view is the
// same path seen through the camera's projective map (lines stay lines: its exact area on screen is
// still its edges' trapezoids), lying at a depth plane over the view.
//
// Per frame, one compute pass flattens every curve of every path object into exactly as many
// segments as its size on screen needs (Wang's bound at 1/32 px; a curve wholly off the object's
// box as its chord, which casts the same winding into the box), each record in a slot its object
// reserves for it, a function of the slot alone (no counters: the same function runs wherever
// slots are filled). One raster pass adds each record's exact area into its object's rectangles of
// a float atlas (additive, in steps f32 adds exactly: the order is free): a fill edge its signed
// trapezoid down to the object's line y = r (the terms of the line cancel around a closed path, so
// the sum is the winding area); a stroke its pieces, which abut along their shared edges (their
// union: the sum, clamped): rectangles along the curve's exact normals, cut at its dashes' ends; a
// joint where it turns (a miter's kite, a bevel's triangle, a round's fan); a cap at each end of
// what it shows (a square's rectangle, a round's fan). One compute pass composites each 16×16 tile
// of the view over the objects whose boxes reach it, in depth order (the draw order among equal
// depths: all of a 2D view's), keeping each pixel as two regions split by a line: a partial layer is
// the half-plane with its coverage as area and its coverage gradient as normal, so shared and
// coincident edges do not leak what lies under them. A 2D view's points and meshes arrive as
// premultiplied layers drawn by the raster pipeline (`blend.wgsl`); a 3D view's raster base (its
// meshes and points, z-buffered) as one more layer, at its depth per pixel.

struct Frame {
    size: vec4<f32>,       // view width, height (pixels); atlas width, height
    tiles: vec4<u32>,      // tiles across, down; record slots (fill, stroke)
    counts: vec4<u32>,     // objects; 1: what lies under is the texture `base` (else the background); a 3D view's
                           // raster base: 0 none, 1 a layer (`base`, `base_depth`), 2 laid (what lies behind it is
                           // hidden); bit 1: what lies under carries light (`base_light`), bit 2: the group's pixels
                           // carry theirs to the next group or the view's glow (`light_out`), not shown yet
    background: vec4<f32>, // premultiplied
    depth: vec4<f32>,      // how near behind a 3D view's raster base a path still shows (drawn on it): a share of its depth
    lists: vec4<u32>,      // a 3D view's see-through fragments: listed (1), in rows [y, z) (heads cleared); samples
    // a 3D view's light, for its paths with a material (`light.wgsl`): clip -> world; the unit vector toward the
    // viewer; where it sees from (w = 1: in perspective); its lights, the exposure, the tone mapping, its bloom
    // (`bloom.rs`); the lights
    inverse: mat4x4<f32>,
    toward: vec4<f32>,
    eye: vec4<f32>,
    lighting: vec4<f32>,
    lights: array<Light, 8>,
    harmonics: array<vec4<f32>, 9>, // its environment's diffuse light (`environment.rs`)
    occlusion: vec4<f32>,           // its ambient occlusion: how much (0: none), how far (`occlusion.rs`)
};

struct Object {
    t1x: vec4<f32>, t1y: vec4<f32>, // term 1: canonical point -> local pixel (rows x, y)
    t2x: vec4<f32>, t2y: vec4<f32>, // term 2 (a morph's); zero otherwise
    t1w: vec4<f32>, t2w: vec4<f32>, // rows w of the projective map (a 2D view's: (0, 0, 0, 1) and 0): pixel = (x, y) / w
    rect: vec4<f32>,                // its box: corner in view pixels (y down), size
    atlas: vec4<u32>,               // coverage origins (x | y << 16): fill, stroke, background; a raster layer's origin (NONE: absent)
    ids: vec4<u32>,                 // first curve of term 1, of term 2 (NONE), first subpath, subpaths
    params: vec4<f32>,              // window lo, hi (u); stroke half-width, background half-width (px)
    dash: vec4<f32>,                // period, duty, phase (u); the fill's reference line r (local y)
    scale: vec4<f32>,               // pixels per canonical unit of term 1, 2; reach past the box (px); curves
    place: vec4<f32>,               // depth z = a x + b y + c over view pixels (a 2D view's: 0); CE's light for gradients
    flags: vec4<u32>,               // its strokes' depth per pixel (x: not planar); reaching behind the near plane (y)
    slots: vec4<u32>,               // its first fill slot, first stroke slot; segments a curve is cut into at most,
                                    // dash windows a segment meets at most (1: not dashed)
    pieces: vec4<u32>,              // records a joint takes, a cap; dash windows a subpath meets at most (1: not dashed)
    fill: vec4<f32>,                // straight RGBA; alpha < 0: gradient rows
    stroke: vec4<f32>,
    background: vec4<f32>,
    gradient: vec4<f32>,            // axis in view pixels (y up): origin, direction / |direction|²
    brush: vec4<u32>,               // fill rows (offset, count), stroke rows (offset, count)
    brush2: vec4<u32>,              // paint 2's fill rows, stroke rows offsets; how far it is mixed in (f32 bits)
    material: vec4<f32>,            // metallic, roughness, reflectance; 1 where its fill is lit by the view's lights
    normal: vec4<f32>,              // which way its plane faces, in the world (a lit fill's)
    t1z: vec4<f32>, t2z: vec4<f32>, // rows of terms 1, 2's depth from the far plane (z - w): a stroke's depth z / w
    near: vec4<f32>,                // a clipped object's shadows on the near plane (`shadow`)
};

const NONE: u32 = 0xffffffffu;

// The rest it reads (the CPU's arrays, the records, the lists, a non-planar path's strokes' depths, a 3D view's raster
// base sample by sample) comes through its head's loaders (`vector_buffers.wgsl`); its compute passes' entries are in
// `vector_compute.wgsl`.
@group(0) @binding(0) var<uniform> frame: Frame;
@group(1) @binding(0) var atlas: texture_2d<f32>;
@group(1) @binding(1) var layers: texture_2d<f32>;                  // points and meshes, premultiplied
@group(1) @binding(2) var base: texture_2d<f32>;                    // what lies under (counts.y = 1), or the raster base
@group(1) @binding(4) var base_depth: texture_2d<f32>;              // a 3D view's raster base's depth (else 1x1 far)
// its lights' shadow maps (`shadow.rs`; 1x1 where none) and their comparison
@group(1) @binding(10) var shadow_maps: texture_depth_2d_array;
@group(1) @binding(11) var shadow_compare: sampler_comparison;
// the DFG table, bilinearly (`light.wgsl`)
@group(1) @binding(12) var dfg_table: texture_2d<f32>;
@group(1) @binding(13) var dfg_linear: sampler;
@group(1) @binding(15) var environment: texture_cube<f32>;
@group(1) @binding(16) var occlusion: texture_2d<f32>; // its ambient occlusion (`occlusion.rs`; 1x1 where it has none)
// where what lies under carries light (`frame.counts.w` bit 1): the raster base's light (`blend.wgsl`'s `Base`), or
// what the group before left; `base` its paint then (1x1 where none)
@group(1) @binding(17) var base_light: texture_2d<f32>;
// a 3D view's see-through points among its layers (`points_before`): the depths of each pixel's nearest layers
// (`bound`), and its slabs, layer j - 1 the points between the j-th and the (j+1)-th of them (else 1x1)
@group(1) @binding(20) var slab_bounds: texture_2d<f32>;
@group(1) @binding(21) var slabs: texture_2d_array<f32>;

// A 3D view's see-through fragments (`blend.wgsl` appends them): per pixel a list, its head's index + 1 (0: none)
struct Node {
    depth: f32, // at the pixel's centre
    color: u32, // straight RGBA8
    key: u32,   // record << 11 | samples covered << 3 | winding sign << 2 | kind (0 mesh, 3 stroke)
    next: u32,  // the next node + 1 (0: none)
};

// A record: a fill edge (a = p0, p1; info.x = object) or a stroke piece (a, b = the quad's
// corners; info.xy = object, layer; info.zw = its depth where it begins and ends (f32 bits; negative: none): a
// non-planar path's).
struct Seg {
    a: vec4<f32>,
    b: vec4<f32>,
    info: vec4<u32>,
};

// The view's lights and shadow maps, as `light.wgsl` reads them.
fn light_count() -> u32 {
    return u32(frame.lighting.x);
}

fn light_at(i: u32) -> Light {
    return frame.lights[i];
}

fn shadow_compare_at(uv: vec2<f32>, layer: i32, depth: f32) -> f32 {
    return textureSampleCompareLevel(shadow_maps, shadow_compare, uv, layer, depth);
}

fn shadow_texel() -> vec2<f32> {
    return 1.0 / vec2<f32>(textureDimensions(shadow_maps));
}

fn dfg_at(NoV: f32, perceptual: f32) -> vec2<f32> {
    return textureSampleLevel(dfg_table, dfg_linear, vec2<f32>(NoV, perceptual), 0.0).xy;
}

fn environment_at(d: vec3<f32>, level: f32) -> vec3<f32> {
    return textureSampleLevel(environment, dfg_linear, d, level).rgb;
}

fn harmonic(i: u32) -> vec3<f32> {
    return frame.harmonics[i].xyz;
}

// Straight RGBA8 (a byte a channel, red lowest) as floats.
fn rgba8(c: u32) -> vec4<f32> {
    return vec4<f32>(f32(c & 0xffu), f32((c >> 8u) & 0xffu), f32((c >> 16u) & 0xffu), f32(c >> 24u)) / 255.0;
}

// ── curves ────────────────────────────────────────────────────────────────────

fn bernstein(t: f32) -> vec4<f32> {
    let s = 1.0 - t;
    return vec4<f32>(s * s * s, 3.0 * s * s * t, 3.0 * s * t * t, t * t * t);
}

fn dbernstein(t: f32) -> vec4<f32> {
    let s = 1.0 - t;
    return vec4<f32>(-3.0 * s * s, 3.0 * s * s - 6.0 * s * t, 6.0 * s * t - 3.0 * t * t, 3.0 * t * t);
}

// The four control points from `first` with weights w (Bernstein or its derivative).
fn weighted(first: u32, w: vec4<f32>) -> vec3<f32> {
    var acc = vec3<f32>(0.0);
    acc = fma(vec3<f32>(w.x), control(first).xyz, acc);
    acc = fma(vec3<f32>(w.y), control(first + 1u).xyz, acc);
    acc = fma(vec3<f32>(w.z), control(first + 2u).xyz, acc);
    acc = fma(vec3<f32>(w.w), control(first + 3u).xyz, acc);
    return acc;
}

// Curve c of object o with weights w (Bernstein or its derivative), homogeneous: (x, y, w) of a point
// (affine = true) or of a direction; local pixels are (x, y) / w. A morph adds its second term, curve
// by curve.
fn curve_h(o: u32, c: u32, w: vec4<f32>, affine: bool) -> vec3<f32> {
    let h = vec4<f32>(weighted(4u * (ids_of(o).x + c), w), select(0.0, 1.0, affine));
    var p = vec3<f32>(dot(t1x_of(o), h), dot(t1y_of(o), h), dot(t1w_of(o), h));
    if (ids_of(o).y != NONE) {
        // Bernstein weights sum to 1: term 2's translation (none of the camera's) once
        let g = vec4<f32>(weighted(4u * (ids_of(o).y + c), w), select(0.0, 1.0, affine));
        p += vec3<f32>(dot(t2x_of(o), g), dot(t2y_of(o), g), dot(t2w_of(o), g));
    }
    return p;
}

// A point of curve c (weights summing to 1), in local pixels.
fn curve(o: u32, c: u32, w: vec4<f32>, affine: bool) -> vec2<f32> {
    let h = curve_h(o, c, w, affine);
    return h.xy / h.z;
}

// The derivative of curve c at t on screen (local pixels per unit t): the quotient rule of the
// projective map (a 2D view's w is 1 and its derivative 0: the curve's own derivative).
fn derivative(o: u32, c: u32, t: f32) -> vec2<f32> {
    let p = curve_h(o, c, bernstein(t), true);
    let d = curve_h(o, c, dbernstein(t), false);
    return (d.xy * p.z - p.xy * d.z) / (p.z * p.z);
}

fn at(o: u32, c: u32, t: f32) -> vec2<f32> {
    return curve(o, c, bernstein(t), true);
}

// Whether curve c's control points all lie on one side beyond the object's box and its strokes' reach: no pixel of
// the box sees the curve or its stroke.
fn off_box(o: u32, c: u32) -> bool {
    var lo = vec2<f32>(1e30);
    var hi = vec2<f32>(-1e30);
    for (var k = 0u; k < 4u; k++) {
        var w = vec4<f32>(0.0);
        w[k] = 1.0;
        let p = curve(o, c, w, true);
        lo = min(lo, p);
        hi = max(hi, p);
    }
    let m = scale_of(o).z;
    return hi.x < -m || hi.y < -m || lo.x > rect_of(o).z + m || lo.y > rect_of(o).w + m;
}

// The segments curve c needs this frame: Wang's bound at 1/32 px (at most 256; at most the object's `slots.z`).
fn wang(o: u32, c: u32) -> u32 {
    var d = control(4u * (ids_of(o).x + c)).w * scale_of(o).x;
    if (ids_of(o).y != NONE) {
        d += control(4u * (ids_of(o).y + c)).w * scale_of(o).y;
    }
    return clamp(u32(ceil(sqrt(24.0 * d))), 1u, 256u);
}

// Whether curve c is off object o's box: its control points tell, unless the object reaches behind the near plane
// (where they do not project).
fn off(o: u32, c: u32) -> bool {
    return flags_of(o).y == 0u && off_box(o, c);
}

// A fill's segments of curve c: Wang's; one, the chord, off the box (it casts the same winding into it).
fn segments(o: u32, c: u32) -> u32 {
    return select(wang(o, c), 1u, off(o, c));
}

// Whether object o's strokes are dashed: a window over u of period dash.x, showing dash.y of it from dash.z.
fn dashed(o: u32) -> bool {
    let d = dash_of(o);
    return d.x > 0.0 && d.y < 1.0;
}

// A stroke's segments of curve c: Wang's; a dashed stroke's, as many as its object's most (`slots.z`), so that a
// segment meets a known number of dash windows.
fn stroke_segments(o: u32, c: u32) -> u32 {
    return select(wang(o, c), slots_of(o).z, dashed(o));
}

// The visible parameter range [t0, t1] of segment i of n of curve c (window applied); t1 <= t0: hidden.
fn piece(o: u32, c: u32, i: u32, n: u32) -> vec2<f32> {
    let w = params_of(o).xy - f32(c);
    let t0 = max(f32(i) / f32(n), clamp(w.x, 0.0, 1.0));
    let t1 = min(f32(i + 1u) / f32(n), clamp(w.y, 0.0, 1.0));
    return vec2<f32>(t0, t1);
}

// The point at parameter u (curve index + t) of object o's shape.
fn at_u(o: u32, u: f32, last_curve: u32) -> vec2<f32> {
    let c = min(u32(max(floor(u), 0.0)), last_curve);
    return at(o, c, clamp(u - f32(c), 0.0, 1.0));
}

// ── what reaches behind the camera ────────────────────────────────────────────
//
// An object whose box crosses the near plane (`flags.y`) shows what lies in front of it: a fill edge is cut where it
// crosses it, and what lies behind is replaced by its shadow on it (`shadow`), which encloses no point in front, so
// every winding in front is the shape's own; a stroke shows the pieces in front, cut square at the crossing.

// A point of an object's shape before its map: term 1's, term 2's (a morph's; else 0), homogeneous.
struct Spot {
    a: vec4<f32>,
    b: vec4<f32>,
};

fn spot(o: u32, c: u32, t: f32) -> Spot {
    let w = bernstein(t);
    var s = Spot(vec4<f32>(weighted(4u * (ids_of(o).x + c), w), 1.0), vec4<f32>(0.0));
    if (ids_of(o).y != NONE) {
        s.b = vec4<f32>(weighted(4u * (ids_of(o).y + c), w), 1.0);
    }
    return s;
}

fn spot_u(o: u32, u: f32, last_curve: u32) -> Spot {
    let c = min(u32(max(floor(u), 0.0)), last_curve);
    return spot(o, c, clamp(u - f32(c), 0.0, 1.0));
}

// Its clip z (its depth from the far plane, plus w): in front of the near plane where it is not negative.
fn spot_z(o: u32, s: Spot) -> f32 {
    return dot(t1z_of(o) + t1w_of(o), s.a) + dot(t2z_of(o) + t2w_of(o), s.b);
}

// Where it is on the view (local pixels).
fn spot_xy(o: u32, s: Spot) -> vec2<f32> {
    let h = vec3<f32>(dot(t1x_of(o), s.a) + dot(t2x_of(o), s.b), dot(t1y_of(o), s.a) + dot(t2y_of(o), s.b), dot(t1w_of(o), s.a) + dot(t2w_of(o), s.b));
    return h.xy / h.z;
}

// Its shadow on the near plane: term 1's point moved along clip z's gradient in its shape's plane, to z = 0.
fn shadow(o: u32, s: Spot) -> Spot {
    let n = near_of(o);
    return Spot(vec4<f32>(s.a.xyz - spot_z(o, s) * n.w * n.xyz, 1.0), s.b);
}

// The point of the chord from s0 to s1 (straight on the view: the map keeps lines) where it crosses the near plane.
fn crossing(o: u32, s0: Spot, s1: Spot) -> vec2<f32> {
    let z0 = spot_z(o, s0);
    let f = z0 / (z0 - spot_z(o, s1));
    return spot_xy(o, Spot(mix(s0.a, s1.a, f), mix(s0.b, s1.b, f)));
}

// Where a point of a clipped object shows: itself in front of the near plane, else its shadow on it.
fn shown(o: u32, s: Spot, front: bool) -> vec2<f32> {
    if (front) {
        return spot_xy(o, s);
    }
    return spot_xy(o, shadow(o, s));
}

// Record `half` of the fill edge from s0 to s1 of a clipped object, its ends where they show: whole (half 0) where
// it does not cross the near plane, else from s0 to the crossing (half 0) and from there to s1 (half 1).
fn clipped_edge(o: u32, s0: Spot, s1: Spot, half: u32) -> Seg {
    let front = vec2<bool>(spot_z(o, s0) >= 0.0, spot_z(o, s1) >= 0.0);
    let p0 = shown(o, s0, front.x);
    let p1 = shown(o, s1, front.y);
    if (front.x == front.y) {
        if (half == 0u) {
            return fill_edge(o, p0, p1);
        }
        return none();
    }
    let q = crossing(o, s0, s1);
    if (half == 0u) {
        return fill_edge(o, p0, q);
    }
    return fill_edge(o, q, p1);
}

// ── the exact area of an edge in a pixel ──────────────────────────────────────

fn ramp(t: f32) -> f32 {
    if (t <= 0.0) {
        return 0.0;
    }
    if (t < 1.0) {
        return 0.5 * t * t;
    }
    return t - 0.5;
}

// The signed area of pixel px (its corner) between the edge p0 -> p1 and the line y = r.
fn edge_area(p0: vec2<f32>, p1: vec2<f32>, px: vec2<f32>, r: f32) -> f32 {
    let lo = min(p0.x, p1.x);
    let hi = max(p0.x, p1.x);
    let xa = max(lo, px.x);
    let xb = min(hi, px.x + 1.0);
    if (xb <= xa) {
        return 0.0;
    }
    let m = (p1.y - p0.y) / (p1.x - p0.x);
    let ya = p0.y + m * (xa - p0.x) - px.y;
    let yb = p0.y + m * (xb - p0.x) - px.y;
    var mean: f32;
    if (abs(yb - ya) < 1e-5) {
        mean = clamp(0.5 * (ya + yb), 0.0, 1.0);
    } else {
        mean = (ramp(yb) - ramp(ya)) / (yb - ya);
    }
    let s = select(-1.0, 1.0, p0.x > p1.x);
    return s * (xb - xa) * (mean - clamp(r - px.y, 0.0, 1.0));
}

// ── pass 0: flatten (compute; a thread per slot) ──────────────────────────────
//
// An object reserves a slot for every record its flattening can write (`vector.rs` counts them): a fill edge per
// segment of each curve (as many as its most, `slots.z`) and a closing edge per subpath; for each stroke layer, a
// body piece per segment and dash window it meets (`slots.w`), a joint's records at each curve's start, and a cap's
// at each end of what each subpath shows in each dash window it meets. A slot's record is a function of the slot
// alone (no counter, no order: the atlas adds records exactly, in any order); a slot whose record is not there this
// frame (a curve cut into fewer segments, a piece hidden, a turn not taken) holds none, which draws nothing.

fn none() -> Seg {
    return Seg(vec4<f32>(0.0), vec4<f32>(0.0), vec4<u32>(NONE, 0u, 0u, 0u));
}

fn fill_edge(o: u32, p0: vec2<f32>, p1: vec2<f32>) -> Seg {
    if (p0.x == p1.x) {
        return none(); // a vertical edge adds no area
    }
    return Seg(vec4<f32>(p0, p1), vec4<f32>(0.0), vec4<u32>(o, 0u, 0u, 0u));
}

fn stroke_piece(o: u32, layer: u32, q0: vec2<f32>, q1: vec2<f32>, q2: vec2<f32>, q3: vec2<f32>, depth: vec2<f32>) -> Seg {
    return Seg(vec4<f32>(q0, q1), vec4<f32>(q2, q3), vec4<u32>(o, layer, bitcast<u32>(depth.x), bitcast<u32>(depth.y)));
}

// The depth at parameter t of curve c, where object o's strokes keep their depth per pixel (else NO_DEPTH).
fn curve_depth(o: u32, c: u32, t: f32) -> f32 {
    if (flags_of(o).x == 0u) {
        return NO_DEPTH;
    }
    let h = vec4<f32>(weighted(4u * (ids_of(o).x + c), bernstein(t)), 1.0);
    var zw = vec2<f32>(dot(t1z_of(o), h), dot(t1w_of(o), h));
    if (ids_of(o).y != NONE) {
        let g = vec4<f32>(weighted(4u * (ids_of(o).y + c), bernstein(t)), 1.0);
        zw += vec2<f32>(dot(t2z_of(o), g), dot(t2w_of(o), g));
    }
    return clamp(zw.x / zw.y, -1.0, 0.0);
}

// A direction's unit normal; none for a direction shorter than a thousandth of a pixel (below
// the rounding of the points it comes from: no direction at all).
fn perp(d: vec2<f32>) -> vec2<f32> {
    let l = length(d);
    return select(vec2<f32>(0.0), vec2<f32>(-d.y, d.x) / l, l > 1e-3);
}

// The unit normal of curve c at t (the chord's where the derivative vanishes).
fn normal_at(o: u32, c: u32, t: f32, chord: vec2<f32>) -> vec2<f32> {
    let d = derivative(o, c, t);
    return select(perp(chord), perp(d), dot(d, d) > 1e-6);
}

// The normal the stroke's body has at t of curve c (`normal_at` with the chord of its piece that
// begins there (ahead) or ends there).
fn body_normal(o: u32, c: u32, t: f32, ahead: bool) -> vec2<f32> {
    let d = derivative(o, c, t);
    if (dot(d, d) > 1e-6) {
        return perp(d);
    }
    let n = stroke_segments(o, c);
    let x = t * f32(n);
    let p = piece(o, c, min(u32(select(max(ceil(x) - 1.0, 0.0), floor(x), ahead)), n - 1u), n);
    return perp(at(o, c, p.y) - at(o, c, p.x));
}

// Whether curve c is a point on screen (its control points within a thousandth of a pixel): it has
// no direction, and a joint joins the curves on either side of it.
fn degenerate(o: u32, c: u32) -> bool {
    let p = at(o, c, 0.0);
    var spread = 0.0;
    for (var k = 1u; k < 4u; k++) {
        var w = vec4<f32>(0.0);
        w[k] = 1.0;
        spread = max(spread, length(curve(o, c, w, true) - p));
    }
    return spread <= 1e-3;
}

// A stroke's style (`Paint.brush2.w`): its cap | its joint << 2; 0 is a butt cap and a miter joint.
const ROUND: u32 = 1u; // a cap's or a joint's
const SQUARE: u32 = 2u; // a cap's
const BEVEL: u32 = 2u; // a joint's
const PI: f32 = 3.14159265358979;

// A piece of the stroke's body: from p0 to p1, across their normals, `half` to each side.
fn body(o: u32, layer: u32, half: f32, p0: vec2<f32>, n0: vec2<f32>, p1: vec2<f32>, n1: vec2<f32>, depth: vec2<f32>) -> Seg {
    return stroke_piece(o, layer, p0 - n0 * half, p0 + n0 * half, p1 + n1 * half, p1 - n1 * half, depth);
}

// The triangles of a round piece's fan over `angle` at radius `half`: its chords within 1/32 px of
// the arc (`vector.rs` reserves records for half a turn).
fn fan(angle: f32, half: f32) -> u32 {
    let step = 2.0 * acos(max(1.0 - 0.03125 / half, -1.0));
    return clamp(u32(ceil(angle / step)), 1u, 128u);
}

// Record r of a round piece: the sector of the disk of radius `half` at p from direction a to
// direction b, over `angle`, turning toward w (a ⟂ w); a fan, two triangles to a record.
fn fan_record(o: u32, layer: u32, p: vec2<f32>, a: vec2<f32>, w: vec2<f32>, b: vec2<f32>, angle: f32, half: f32, depth: f32, r: u32) -> Seg {
    let k = fan(angle, half);
    let i = 2u * r;
    if (i >= k) {
        return none();
    }
    let step = angle / f32(k);
    let e = step * f32(i);
    let f = step * f32(i + 1u);
    let g = step * f32(i + 2u);
    let first = select(p + half * (cos(e) * a + sin(e) * w), p + half * a, i == 0u);
    let q = select(p + half * (cos(f) * a + sin(f) * w), p + half * b, i + 1u >= k);
    let s = select(p + half * (cos(g) * a + sin(g) * w), p + half * b, i + 2u >= k);
    return stroke_piece(o, layer, p, first, q, s, vec2<f32>(depth));
}

// Record r of the joint at j where a curve arriving with normal m meets one leaving with normal
// nn, turning: the outer side between the bodies' square ends — a miter's kite (past the miter
// limit, 10: a miter ten widths long, a bevel), a bevel's triangle, a round's sector.
fn joint_record(o: u32, layer: u32, j: vec2<f32>, m: vec2<f32>, nn: vec2<f32>, half: f32, style: u32, depth: f32, r: u32) -> Seg {
    let cross = nn.x * m.y - nn.y * m.x;
    let side = select(-1.0, 1.0, cross > 0.0); // a right turn: the outer side is +n
    let u0 = side * m;
    let u1 = side * nn;
    if (style == ROUND) {
        // turning as the path does, from its heading (a reversal's lies ahead of it)
        return fan_record(o, layer, j, u0, vec2<f32>(m.y, -m.x), u1, atan2(abs(cross), dot(m, nn)), half, depth, r);
    }
    if (r > 0u) {
        return none();
    }
    let s = u1 + u0;
    let l = length(s);
    var tip = j + 0.5 * half * s; // the bevel's middle
    if (style != BEVEL && l >= 1e-6) {
        let dir = s / l;
        let sine = dot(dir, u1); // of half the angle between the pieces: the miter is 1 / sine widths long
        if (sine >= 0.1) {
            tip = j + dir * (half / sine);
        }
    }
    return stroke_piece(o, layer, j, j + side * half * m, tip, j + side * half * nn, vec2<f32>(depth));
}

// Record r of a cap at an end p of the stroke, whose body has normal n there and lies toward −e:
// a square's rectangle or a round's half-disk.
fn cap_record(o: u32, layer: u32, p: vec2<f32>, n: vec2<f32>, e: vec2<f32>, half: f32, style: u32, depth: f32, r: u32) -> Seg {
    if (style == ROUND) {
        return fan_record(o, layer, p, n, e, -n, PI, half, depth, r);
    }
    if (style != SQUARE || r > 0u) {
        return none();
    }
    return stroke_piece(o, layer, p - half * n, p + half * n, p + half * (n + e), p + half * (e - n), vec2<f32>(depth));
}

// Record r of the cap at the start (or end) of a shown stretch [lo, hi] of a subpath, where the
// stroke is drawn from, stepping in past curves that are a point. A stretch that is all one point
// has no direction: its caps face along x (a round pair is a dot).
fn end_cap(o: u32, layer: u32, half: f32, lo: f32, hi: f32, start: bool, style: u32, r: u32) -> Seg {
    var c = u32(select(ceil(hi) - 1.0, floor(lo), start));
    var t = select(hi - f32(c), lo - f32(c), start);
    var drawn = !degenerate(o, c);
    for (var k = 0u; k < 64u && !drawn; k++) {
        if (start && f32(c + 1u) < hi) {
            c += 1u;
            t = 0.0;
        } else if (!start && f32(c) > lo) {
            c -= 1u;
            t = 1.0;
        } else {
            break;
        }
        drawn = !degenerate(o, c);
    }
    if (flags_of(o).y != 0u && spot_z(o, spot(o, c, t)) < 0.0) {
        return none(); // behind the near plane: the stroke ends at its cut
    }
    let p = at(o, c, t);
    let out = select(1.0, -1.0, start);
    var n = vec2<f32>(0.0, 1.0);
    var toward = vec2<f32>(out, 0.0);
    if (drawn) {
        n = body_normal(o, c, t, start);
        toward = out * vec2<f32>(n.y, -n.x);
    }
    return cap_record(o, layer, p, n, toward, half, style, curve_depth(o, c, t), r);
}

// The curve the stroke continues into across the start (next = false) or end (next = true) of
// curve c; NONE where it ends there: an open end, or the reveal window's edge (a closed subpath's
// seam joins only when the whole loop shows).
fn neighbour(o: u32, c: u32, next: bool) -> u32 {
    let w = params_of(o).xy;
    for (var s = 0u; s < ids_of(o).w; s++) {
        let sub = subpath(ids_of(o).z + s);
        if (c >= sub.x && c < sub.y) {
            let whole = w.x <= f32(sub.x) && w.y >= f32(sub.y);
            if (next) {
                if (c + 1u < sub.y) {
                    return select(NONE, c + 1u, w.x < f32(c + 1u) && w.y > f32(c + 1u));
                }
                return select(NONE, sub.x, sub.z != 0u && whole);
            }
            if (c > sub.x) {
                return select(NONE, c - 1u, w.x < f32(c) && w.y > f32(c));
            }
            return select(NONE, sub.y - 1u, sub.z != 0u && whole);
        }
    }
    return NONE;
}

// Whether the dashes show the stroke on both sides of where one curve ends (u = end) and the next
// begins (u = start), and between: a joint is drawn only inside a dash (end > start: across a
// closed subpath's seam).
fn dashes_join(o: u32, end: f32, start: f32) -> bool {
    let d = dash_of(o);
    if (d.x <= 0.0 || d.y >= 1.0) {
        return true;
    }
    let a = (end - d.z) / d.x;
    let b = (start - d.z) / d.x;
    return fract(a) > 0.0 && fract(a) <= d.y && fract(b) < d.y && (end > start || floor(a) == floor(b));
}

// Whether a subpath of object o goes on across its seam: closed, shown whole, its dashes showing
// on both sides; one that is all one point has no seam to go on across (its caps make it a dot).
fn seam(o: u32, sub: vec4<u32>) -> bool {
    let w = params_of(o).xy;
    if (!(sub.z != 0u && w.x <= f32(sub.x) && w.y >= f32(sub.y) && dashes_join(o, f32(sub.y), f32(sub.x)))) {
        return false;
    }
    var c = sub.x;
    for (var k = 0u; k < 64u && c < sub.y && degenerate(o, c); k++) {
        c += 1u;
    }
    return c < sub.y;
}

// The object whose slots (k = 0: fill, 1: stroke) hold slot q: the last whose first is at most q.
fn owner(q: u32, k: u32) -> u32 {
    var lo = 0u;
    var hi = frame.counts.x;
    while (hi - lo > 1u) {
        let mid = (lo + hi) / 2u;
        if (slots_of(mid)[k] <= q) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    return lo;
}

// Fill slot q: segment i of curve c (a curve cut into fewer has none past them), or a subpath's
// closing edge, from where its window ends back to where it starts.
fn fill_slot(q: u32) -> Seg {
    let o = owner(q, 0u);
    let clipped = flags_of(o).y != 0u;
    var l = q - slots_of(o).x;
    let half = l % 2u;
    if (clipped) {
        l /= 2u;
    }
    let n = slots_of(o).z;
    let edges = u32(scale_of(o).w) * n;
    if (l < edges) {
        let c = l / n;
        let i = l % n;
        let m = segments(o, c);
        let t = piece(o, c, i, m);
        if (i >= m || t.y <= t.x) {
            return none();
        }
        if (clipped) {
            return clipped_edge(o, spot(o, c, t.x), spot(o, c, t.y), half);
        }
        return fill_edge(o, at(o, c, t.x), at(o, c, t.y));
    }
    let sub = subpath(ids_of(o).z + l - edges);
    let w = params_of(o).xy;
    let a = max(f32(sub.x), w.x);
    let b = min(f32(sub.y), w.y);
    if (a >= b) {
        return none();
    }
    if (clipped) {
        return clipped_edge(o, spot_u(o, b, sub.y - 1u), spot_u(o, a, sub.y - 1u), half);
    }
    return fill_edge(o, at_u(o, b, sub.y - 1u), at_u(o, a, sub.y - 1u));
}

// Body piece j of segment i of curve c: the segment's body (a dashed stroke's part of it in the
// j-th dash window it meets). A curve off the box has none: no pixel of the box sees it.
fn body_slot(o: u32, layer: u32, half: f32, c: u32, i: u32, j: u32) -> Seg {
    let m = stroke_segments(o, c);
    let t = piece(o, c, i, m);
    if (i >= m || t.y <= t.x || off(o, c)) {
        return none();
    }
    // the piece's ends (a dashed stroke's: of its j-th dash window's part of it; the depth taken where the window
    // starts and ends)
    var ta = t.x;
    var tb = t.y;
    var dt = t;
    if (dashed(o)) {
        let d = dash_of(o);
        let u0 = f32(c) + t.x;
        let u1 = f32(c) + t.y;
        let s = d.z + (floor((u0 - d.z) / d.x) + f32(j)) * d.x;
        let a = max(u0, s);
        let b = min(u1, s + d.y * d.x);
        if (s >= u1 || a >= b) {
            return none();
        }
        ta = select(t.x, a - f32(c), a > u0);
        tb = select(t.y, b - f32(c), b < u1);
        dt = vec2<f32>(a, b) - f32(c);
    }
    let chord = at(o, c, t.y) - at(o, c, t.x);
    var pa = at(o, c, ta);
    var pb = at(o, c, tb);
    var na = normal_at(o, c, ta, chord);
    var nb = normal_at(o, c, tb, chord);
    var depth = vec2<f32>(curve_depth(o, c, dt.x), curve_depth(o, c, dt.y));
    if (flags_of(o).y != 0u) {
        // a clipped object's piece: its part in front of the near plane, cut square where it crosses it (depth 0)
        let sa = spot(o, c, ta);
        let sb = spot(o, c, tb);
        let front = vec2<bool>(spot_z(o, sa) >= 0.0, spot_z(o, sb) >= 0.0);
        if (!any(front)) {
            return none();
        }
        if (!all(front)) {
            let q = crossing(o, sa, sb);
            let cut = select(NO_DEPTH, -1.0, flags_of(o).x != 0u); // the near plane's depth
            if (front.x) {
                pb = q;
                nb = perp(q - pa);
                depth.y = cut;
            } else {
                pa = q;
                na = perp(pb - q);
                depth.x = cut;
            }
        }
    }
    return body(o, layer, half, pa, na, pb, nb, depth);
}

// Record r of the joint where curve c begins, with the drawn curve before it (past curves that are
// a point), where the stroke turns.
fn joint_slot(o: u32, layer: u32, half: f32, c: u32, r: u32) -> Seg {
    if (piece(o, c, 0u, 1u).x != 0.0 || (flags_of(o).y != 0u && spot_z(o, spot(o, c, 0.0)) < 0.0)) {
        return none();
    }
    let nn = body_normal(o, c, 0.0, true);
    if (dot(nn, nn) < 0.5) {
        return none(); // a point
    }
    var prev = neighbour(o, c, false);
    for (var k = 0u; k < 64u && prev != NONE && prev != c && degenerate(o, prev); k++) {
        prev = neighbour(o, prev, false);
    }
    if (prev == NONE || !dashes_join(o, f32(prev + 1u), f32(c))) {
        return none();
    }
    let m = body_normal(o, prev, 1.0, false);
    let cross = nn.x * m.y - nn.y * m.x;
    if (!(dot(m, m) > 0.5 && (abs(cross) > 1e-6 || dot(nn, m) < 0.0))) {
        return none();
    }
    return joint_record(o, layer, at(o, c, 0.0), m, nn, half, (brush2_of(o).w >> 2u) & 3u, curve_depth(o, c, 0.0), r);
}

// Record r of a cap at end e of what a subpath shows in one of the dash windows it meets (e / 2:
// the subpath, then the window, from the one over where it shows from; not dashed, the one
// stretch it shows; e % 2: the stretch's start or end). A dash's ends inside a subpath are always
// the stroke's; the subpath's own, unless it goes on across its seam.
fn cap_slot(o: u32, layer: u32, half: f32, e: u32, r: u32) -> Seg {
    let windows = pieces_of(o).z;
    let sub = subpath(ids_of(o).z + e / 2u / windows);
    let start = e % 2u == 0u;
    let w = params_of(o).xy;
    let a = max(f32(sub.x), w.x);
    let b = min(f32(sub.y), w.y);
    let joined = seam(o, sub);
    var lo = a;
    var hi = b;
    if (dashed(o)) {
        let d = dash_of(o);
        let s = d.z + (floor((a - d.z) / d.x) + f32(e / 2u % windows)) * d.x;
        lo = max(a, s);
        hi = min(b, s + d.y * d.x);
        if (s >= b) {
            return none();
        }
    } else if (joined) {
        return none();
    }
    let inside = (start && lo > f32(sub.x)) || (!start && hi < f32(sub.y)); // a dash's end, not the subpath's
    if (lo >= hi || !(inside || !joined)) {
        return none();
    }
    return end_cap(o, layer, half, lo, hi, start, brush2_of(o).w & 3u, r);
}

// Stroke slot q: in its layer's slots (the stroke's, then the background stroke's), a body piece,
// a joint's record or a cap's.
fn stroke_slot(q: u32) -> Seg {
    let o = owner(q, 1u);
    var l = q - slots_of(o).y;
    let curves = u32(scale_of(o).w);
    let n = slots_of(o).z;
    let k = slots_of(o).w;
    let joint = pieces_of(o).x;
    let cap = pieces_of(o).y;
    let bodies = curves * n * k;
    let joints = curves * joint;
    let per_layer = bodies + joints + 2u * ids_of(o).w * pieces_of(o).z * cap;
    var layer = 1u;
    if (atlas_of(o).y == NONE) {
        layer = 2u;
    } else if (l >= per_layer) {
        layer = 2u;
        l -= per_layer;
    }
    let half = select(params_of(o).z, params_of(o).w, layer == 2u);
    if (l < bodies) {
        return body_slot(o, layer, half, l / (n * k), l / k % n, l % k);
    }
    if (l < bodies + joints) {
        return joint_slot(o, layer, half, (l - bodies) / joint, (l - bodies) % joint);
    }
    return cap_slot(o, layer, half, (l - bodies - joints) / cap, (l - bodies - joints) % cap);
}

// ── pass 1: accumulate (raster, additive, into the atlas) ──────────────────────

fn corner(k: u32) -> vec2<f32> {
    let c = array<vec2<f32>, 6>(vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(1.0, 1.0), vec2(0.0, 0.0), vec2(1.0, 1.0), vec2(0.0, 1.0));
    return c[k];
}

fn to_atlas(o: u32, layer: u32, local: vec2<f32>) -> vec4<f32> {
    let packed = atlas_of(o)[layer];
    let at = vec2<f32>(f32(packed & 0xffffu), f32(packed >> 16u)) + local;
    return vec4<f32>(at.x / frame.size.z * 2.0 - 1.0, 1.0 - at.y / frame.size.w * 2.0, 0.0, 1.0);
}

struct Piece {
    @builtin(position) position: vec4<f32>,
    @location(0) @interpolate(flat) a: vec4<f32>, // fill: the edge; stroke: corners 0, 1
    @location(1) @interpolate(flat) b: vec4<f32>, // fill: (r, 0, 0, 0); stroke: corners 2, 3
    @location(2) @interpolate(flat) o: vec4<u32>, // object, layer, box size (f32 bits)
    @location(3) @interpolate(flat) depth: vec2<f32>, // a stroke piece's depth where it begins and ends (or NO_DEPTH)
};

fn nothing() -> Piece {
    var out: Piece;
    out.position = vec4<f32>(2.0, 2.0, 0.0, 1.0);
    return out;
}

// A fill edge's trapezoid down to r: the pixels of its columns between it and r, in the box.
@vertex
fn vs_fill(@builtin(vertex_index) v: u32, @builtin(instance_index) i: u32) -> Piece {
    if (i >= frame.tiles.z) {
        return nothing();
    }
    let seg = fill_record(i);
    let o = seg.info.x;
    if (o == NONE) {
        return nothing(); // an empty slot
    }
    let p0 = seg.a.xy;
    let p1 = seg.a.zw;
    let r = dash_of(o).w;
    let size = rect_of(o).zw;
    let lo = floor(vec2<f32>(min(p0.x, p1.x), min(min(p0.y, p1.y), r)));
    let hi = ceil(vec2<f32>(max(p0.x, p1.x), max(max(p0.y, p1.y), r)));
    var out: Piece;
    out.position = to_atlas(o, 0u, clamp(mix(lo, hi, corner(v)), vec2<f32>(0.0), size));
    out.a = seg.a;
    out.b = vec4<f32>(r, 0.0, 0.0, 0.0);
    out.o = vec4<u32>(o, 0u, 0u, 0u);
    out.depth = vec2<f32>(NO_DEPTH);
    return out;
}

// An area as the atlas adds it: in 1/65536ths, whose sums (below 256) f32 adds exactly, so a
// pixel's sum does not depend on the order the records were written in (it varies from run to run).
fn exact(a: f32) -> vec4<f32> {
    return vec4<f32>(round(a * 65536.0) / 65536.0, 0.0, 0.0, 0.0);
}

@fragment
fn fs_fill(in: Piece) -> @location(0) vec4<f32> {
    let packed = atlas_of(in.o.x)[0];
    let px = floor(in.position.xy) - vec2<f32>(f32(packed & 0xffffu), f32(packed >> 16u));
    return exact(edge_area(in.a.xy, in.a.zw, px, in.b.x));
}

// A stroke piece's quad, rasterized as its box oriented along it, grown by a pixel: every pixel
// the quad touches, however sharp or folded its corners (a miter's).
@vertex
fn vs_stroke(@builtin(vertex_index) v: u32, @builtin(instance_index) i: u32) -> Piece {
    if (i >= frame.tiles.w) {
        return nothing();
    }
    let seg = stroke_record(i);
    let o = seg.info.x;
    if (o == NONE) {
        return nothing(); // an empty slot
    }
    let layer = seg.info.y;
    let q = array<vec2<f32>, 4>(seg.a.xy, seg.a.zw, seg.b.xy, seg.b.zw);
    var along = 0.5 * (q[2] + q[3] - q[0] - q[1]);
    if (dot(along, along) < 1e-12) {
        along = q[1] - q[0];
    }
    let axis = select(vec2<f32>(1.0, 0.0), normalize(along), dot(along, along) > 1e-12);
    let across = vec2<f32>(-axis.y, axis.x);
    var lo = vec2<f32>(1e30);
    var hi = vec2<f32>(-1e30);
    for (var k = 0u; k < 4u; k++) {
        let p = vec2<f32>(dot(q[k], axis), dot(q[k], across));
        lo = min(lo, p);
        hi = max(hi, p);
    }
    let at = mix(lo - 1.0, hi + 1.0, corner(v));
    let size = rect_of(o).zw;
    var out: Piece;
    out.position = to_atlas(o, layer, at.x * axis + at.y * across);
    out.a = seg.a;
    out.b = seg.b;
    out.o = vec4<u32>(o, layer, bitcast<u32>(size.x), bitcast<u32>(size.y));
    out.depth = vec2<f32>(bitcast<f32>(seg.info.z), bitcast<f32>(seg.info.w));
    return out;
}

// Whether point p lies in the triangle a b c (either winding).
fn inside(p: vec2<f32>, a: vec2<f32>, b: vec2<f32>, c: vec2<f32>) -> bool {
    let d = vec3<f32>((b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x), (c.x - b.x) * (p.y - b.y) - (c.y - b.y) * (p.x - b.x), (a.x - c.x) * (p.y - c.y) - (a.y - c.y) * (p.x - c.x));
    return all(d >= vec3<f32>(0.0)) || all(d <= vec3<f32>(0.0));
}

@fragment
fn fs_stroke(in: Piece) -> @location(0) vec4<f32> {
    let o = in.o.x;
    let packed = atlas_of(o)[in.o.y];
    let px = floor(in.position.xy) - vec2<f32>(f32(packed & 0xffffu), f32(packed >> 16u));
    let size = vec2<f32>(bitcast<f32>(in.o.z), bitcast<f32>(in.o.w));
    if (px.x < 0.0 || px.y < 0.0 || px.x >= size.x || px.y >= size.y) {
        discard;
    }
    let far = -1e30;
    // the quad as two triangles (0 1 2) and (0 2 3), each counted whole: a quad folded by a sharp
    // miter covers the union of its triangles
    let diagonal = edge_area(in.a.xy, in.b.xy, px, far);
    let a = abs(edge_area(in.a.xy, in.a.zw, px, far) + edge_area(in.a.zw, in.b.xy, px, far) - diagonal)
        + abs(diagonal + edge_area(in.b.xy, in.b.zw, px, far) + edge_area(in.b.zw, in.a.xy, px, far));
    if (in.depth.x <= 0.0 && a > 0.0) {
        // its depth at the pixel's center: z / w is affine along the piece on screen (lines stay lines, and z and w
        // are affine along them)
        let c = px + 0.5;
        let m0 = 0.5 * (in.a.xy + in.a.zw);
        let m1 = 0.5 * (in.b.xy + in.b.zw);
        let along = m1 - m0;
        let t = clamp(dot(c - m0, along) / max(dot(along, along), 1e-12), 0.0, 1.0);
        let z = clamp(mix(in.depth.x, in.depth.y, t), -1.0, 0.0);
        let through = inside(c, in.a.xy, in.a.zw, in.b.xy) || inside(c, in.a.xy, in.b.xy, in.b.zw);
        // the nearer the larger: a depth's magnitude's bits
        keep_stroke_depth(u32(in.position.y) * u32(frame.size.z) + u32(in.position.x), select(0u, 0x80000000u, through) | ((bitcast<u32>(z) & 0x7fffffffu) >> 1u));
    }
    return exact(a);
}

// ── pass 2: composite (compute) ───────────────────────────────────────────────

// A layer's paint at the pixel centred at `up` (view pixels, y up), premultiplied: a solid color,
// or the object's gradient there (`stops`).
fn paint(o: u32, color: vec4<f32>, first: u32, second: u32, count: u32, up: vec2<f32>) -> vec4<f32> {
    if (color.a >= 0.0) {
        return premultiplied(color);
    }
    let g = gradient_of(o);
    var c = stops(first, second, count, bitcast<f32>(brush2_of(o).z), dot(up - g.xy, g.zw));
    let light = place_of(o).w;
    if (light != 0.0) {
        c = vec4<f32>(clamp(c.rgb + light, vec3<f32>(0.0), vec3<f32>(1.0)), c.a);
    }
    return premultiplied(c);
}

// A layer's coverage at a local pixel as its tile's entry has it (`mask`: per layer, the fill where its edges run 1,
// inside them 2, the stroke 4, the background stroke 8): the atlas's where its edges or strokes run, 1 inside the fill
// (no read), else 0.
fn covered(mask: u32, layer: u32, origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>) -> f32 {
    if ((mask & array<u32, 3>(1u, 4u, 8u)[layer]) != 0u) {
        return cover(origin, local, size);
    }
    return select(0.0, 1.0, layer == 0u && (mask & 2u) != 0u);
}

// A layer's coverage at a local pixel (0 outside the object's box).
fn cover(origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>) -> f32 {
    if (local.x < 0 || local.y < 0 || local.x >= size.x || local.y >= size.y) {
        return 0.0;
    }
    return min(abs(textureLoad(atlas, origin + vec2<u32>(local), 0).r), 1.0);
}

// The area of the unit pixel (centred at 0) on the side n of the line p.n = d: its projection on
// n is the sum of two uniform variables, so the area is a piecewise quadratic of d.
fn side_area(n: vec2<f32>, d: f32) -> f32 {
    let a = max(abs(n.x), abs(n.y));
    let b = min(abs(n.x), abs(n.y));
    let t = -d; // the area of {p.n >= d} = P(projection <= -d), by symmetry
    if (t <= -0.5 * (a + b)) {
        return 0.0;
    }
    if (t >= 0.5 * (a + b)) {
        return 1.0;
    }
    if (b < 1e-6) {
        return clamp(t / a + 0.5, 0.0, 1.0);
    }
    if (t <= -0.5 * (a - b)) {
        let s = t + 0.5 * (a + b);
        return s * s / (2.0 * a * b);
    }
    if (t <= 0.5 * (a - b)) {
        return b / (2.0 * a) + (t + 0.5 * (a - b)) / a;
    }
    let s = 0.5 * (a + b) - t;
    return 1.0 - s * s / (2.0 * a * b);
}

// The offset d with side_area(n, d) = c (its inverse).
fn offset_for(n: vec2<f32>, c: f32) -> f32 {
    let a = max(abs(n.x), abs(n.y));
    let b = min(abs(n.x), abs(n.y));
    var t: f32;
    if (b < 1e-6) {
        t = a * (c - 0.5);
    } else if (c <= b / (2.0 * a)) {
        t = -0.5 * (a + b) + sqrt(2.0 * a * b * c);
    } else if (c <= 1.0 - b / (2.0 * a)) {
        t = -0.5 * (a - b) + a * (c - b / (2.0 * a));
    } else {
        t = 0.5 * (a + b) - sqrt(2.0 * a * b * (1.0 - c));
    }
    return -t;
}

// The area of the unit pixel (centred at 0) inside both half-planes p.n1 >= d1 and p.n2 >= d2.
fn both_area(n1: vec2<f32>, d1: f32, n2: vec2<f32>, d2: f32) -> f32 {
    var poly: array<vec2<f32>, 8>;
    var count = 4u;
    poly[0] = vec2<f32>(-0.5, -0.5);
    poly[1] = vec2<f32>(0.5, -0.5);
    poly[2] = vec2<f32>(0.5, 0.5);
    poly[3] = vec2<f32>(-0.5, 0.5);
    for (var h = 0u; h < 2u; h++) {
        let n = select(n2, n1, h == 0u);
        let d = select(d2, d1, h == 0u);
        var next: array<vec2<f32>, 8>;
        var m = 0u;
        for (var i = 0u; i < count; i++) {
            let p = poly[i];
            let q = poly[(i + 1u) % count];
            let sp = dot(p, n) - d;
            let sq = dot(q, n) - d;
            if (sp >= 0.0 && m < 8u) {
                next[m] = p;
                m++;
            }
            if ((sp >= 0.0) != (sq >= 0.0) && m < 8u) {
                next[m] = p + (q - p) * (sp / (sp - sq));
                m++;
            }
        }
        poly = next;
        count = m;
    }
    var area = 0.0;
    for (var i = 0u; i < count; i++) {
        let p = poly[i];
        let q = poly[(i + 1u) % count];
        area += p.x * q.y - q.x * p.y;
    }
    return 0.5 * abs(area);
}

// What covers a pixel, or a part of it, as the composite mixes it: the raster base's two targets in one value
// (`blend.wgsl`'s `Base`): display paint (premultiplied; its alpha how much of it is lit) and the light of what is lit
// (exposed, premultiplied; its alpha how much is covered). Every way the composite mixes is linear in it (a layer over
// another, a split pixel's regions, a pixel's samples), so lit content's light is averaged as a camera averages it,
// and shown once (`seen`).
alias Mix = mat2x4<f32>;

// Display paint c (premultiplied) as a mix: nothing of it lit.
fn painted_mix(c: vec4<f32>) -> Mix {
    return Mix(vec4<f32>(c.rgb, 0.0), vec4<f32>(0.0, 0.0, 0.0, c.a));
}

// The light l of lit content (exposed, premultiplied; its alpha the coverage) as a mix, the light kept within what a
// half float holds (as the raster base keeps it).
fn light_mix(l: vec4<f32>) -> Mix {
    return Mix(vec4<f32>(0.0, 0.0, 0.0, l.a), vec4<f32>(min(l.rgb, vec3<f32>(LIGHT_MOST * l.a)), l.a));
}

// A mix divided by k (each column: as a vector is).
fn divided(m: Mix, k: f32) -> Mix {
    return Mix(m[0] / k, m[1] / k);
}

// p over what lies below it: below covered as much as p covers.
fn over(p: Mix, below: Mix) -> Mix {
    return p + below * (1.0 - p[1].a);
}

// A mix as the view shows it: its paint, and its light tone mapped once, the light of what is lit in it averaged
// first (a view with no lit content has none: `lighting`).
fn seen(m: Mix) -> vec4<f32> {
    if (!lighting || m[0].a <= 0.0) {
        return vec4<f32>(m[0].rgb, m[1].a);
    }
    return vec4<f32>(m[0].rgb + toned(m[1].rgb / m[0].a, u32(frame.lighting.z + 0.5)) * m[0].a, m[1].a);
}

// The pixel as two regions split by the line p.n = d (inside: p.n >= d, of area a).
struct Split {
    n: vec2<f32>,
    d: f32,
    a: f32,
    inside: Mix,
    outside: Mix,
};

// The half-plane (normal, offset) of a partial layer: area c, normal the coverage gradient; z > 1.5
// when it has no direction.
fn half_plane(origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>, c: f32) -> vec3<f32> {
    let g = vec2<f32>(
        cover(origin, local + vec2<i32>(1, 0), size) - cover(origin, local - vec2<i32>(1, 0), size),
        cover(origin, local - vec2<i32>(0, 1), size) - cover(origin, local + vec2<i32>(0, 1), size),
    );
    return line_of(g, c);
}

// The half-plane of a partial layer of area c whose coverage changes by g across the pixel (x right, y up): its normal
// g's direction, its offset its area's (`offset_for`); z > 1.5 where g has no direction.
fn line_of(g: vec2<f32>, c: f32) -> vec3<f32> {
    if (dot(g, g) < 1e-8) {
        return vec3<f32>(0.0, 0.0, 2.0);
    }
    let n = normalize(g);
    return vec3<f32>(n, offset_for(n, c));
}

// A pixel as the composite lays its layers: two regions (`Split`). Mode 0: uniform (inside = outside); 1: one
// partial layer pending, its half-plane found only if another partial layer comes (where its coverage lies: `origin`,
// `local`, `size`); 2: split by a line.
struct Pixel {
    s: Split,
    mode: u32,
    origin: vec2<u32>,
    local: vec2<i32>,
    size: vec2<i32>,
};

// The pixel with paint p (a mix, where the layer covers) of coverage c laid over it: the layer's coverage lies at
// `local` of a box of `size` at `origin` in the atlas (`cover`).
fn lay(px: Pixel, p: Mix, c: f32, origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>) -> Pixel {
    var out = px;
    if (c >= 1.0 - 1e-5) {
        let q = p * c;
        out.s.inside = over(q, px.s.inside);
        out.s.outside = over(q, px.s.outside);
        return out;
    }
    if (px.mode == 0u) {
        // the first partial layer: exact as it is, unless another partial layer comes
        out.mode = 1u;
        out.s.a = c;
        out.s.inside = over(p, px.s.inside);
        out.origin = origin;
        out.local = local;
        out.size = size;
        return out;
    }
    return lay_line(lined(px), p, c, half_plane(origin, local, size, c));
}

// The pixel with its pending partial layer's line found (mode 1 to 2), from its coverage's gradient; one without a
// direction settled as plain coverage.
fn lined(px: Pixel) -> Pixel {
    if (px.mode != 1u) {
        return px;
    }
    var out = px;
    let h = half_plane(px.origin, px.local, px.size, px.s.a);
    if (h.z > 1.5) {
        // the pending layer has no direction: settle it as plain coverage
        let settled = px.s.a * px.s.inside + (1.0 - px.s.a) * px.s.outside;
        out.s.inside = settled;
        out.s.outside = settled;
        out.s.a = 0.0;
        out.s.n = vec2<f32>(1.0, 0.0);
        out.s.d = 1.0;
    } else {
        out.s.n = h.xy;
        out.s.d = h.z;
    }
    out.mode = 2u;
    return out;
}

// The pixel with paint p (a mix, where the layer covers) of coverage c laid over it in the half-plane `line` (p.n >= d),
// a line known as it is laid (z > 1.5: none, the paint laid as plain coverage).
fn lay_line(px: Pixel, p: Mix, c: f32, line: vec3<f32>) -> Pixel {
    var out = px;
    if (line.z > 1.5) {
        let q = p * c;
        out.s.inside = over(q, px.s.inside);
        out.s.outside = over(q, px.s.outside);
        return out;
    }
    if (px.mode == 0u) {
        out.mode = 2u;
        out.s.n = line.xy;
        out.s.d = line.z;
        out.s.a = c;
        out.s.inside = over(p, px.s.inside);
        return out;
    }
    return split_by(lined(px), p, line, c);
}

// The pixel (split by a line: mode 2) with paint p laid over it in the half-plane h (p.n >= d), of area c: the new
// line splits the pixel again, its inside the layer over what each old region leaves in it.
fn split_by(px: Pixel, p: Mix, hl: vec3<f32>, c: f32) -> Pixel {
    var out = px;
    let s = out.s;
    let overlap = both_area(s.n, s.d, hl.xy, hl.z);
    let in_l = divided(overlap * s.inside + (c - overlap) * s.outside, c);
    let out_l = divided((s.a - overlap) * s.inside + (1.0 - s.a - c + overlap) * s.outside, max(1.0 - c, 1e-6));
    out.s.n = hl.xy;
    out.s.d = hl.z;
    out.s.a = c;
    out.s.inside = over(p, in_l);
    out.s.outside = out_l;
    return out;
}

// Where layer l is nearer than `last`, the layer laid just before it, both planar: the half-plane of the unit pixel
// (centred at 0, y up, as `half_plane`'s) where their planes put l in front, if they cross inside the pixel (Duff's
// test: their depths' difference changes sign over it); else none (z > 1.5): l is in front all over it.
fn nearer_part(l: Layer, last: Layer) -> vec3<f32> {
    let none = vec3<f32>(0.0, 0.0, 2.0);
    if (l.key == 0u || l.key == NONE || last.key == 0u || last.key == NONE) {
        return none;
    }
    let ol = (l.key >> 2u) - 1u;
    let om = (last.key >> 2u) - 1u;
    if ((flags_of(ol).x != 0u && (l.key & 3u) != 1u) || (flags_of(om).x != 0u && (last.key & 3u) != 1u)) {
        return none; // (a stroke's own depths, a pixel's)
    }
    // their depths' difference: at the centre, and its gradient over view pixels (y down); a difference that stays
    // within the depths' own precision over the pixel (`frame.depth.x` of them: 8 f32 steps) is no crossing, a tie
    let g = place_of(ol).xy - place_of(om).xy;
    let dc = l.z - last.z;
    let reach = 0.5 * (abs(g.x) + abs(g.y));
    if (abs(dc) >= reach || reach <= frame.depth.x * max(abs(l.z), abs(last.z))) {
        return none;
    }
    // l nearer: dc + g.p < 0 (p from the centre, y down); y up, q = (p.x, -p.y): q.(-g.x, g.y) > dc
    let length = sqrt(dot(g, g));
    return vec3<f32>(-g.x, g.y, dc) / length;
}

// The pixel with layer l laid over it only where it is nearer than the whole layer laid just before it (half-plane h,
// `nearer_part`): exact for a whole layer; a partial one keeps its coverage's share there (`both_area`), along the
// line that cuts it more.
fn lay_nearer(px: Pixel, l: Layer, h: vec3<f32>, gid: vec2<u32>, up: vec2<f32>) -> Pixel {
    let o = (l.key >> 2u) - 1u;
    let local = vec2<i32>(vec2<f32>(gid) - rect_of(o).xy);
    let size = vec2<i32>(rect_of(o).zw);
    let layer = array<u32, 3>(2u, 0u, 1u)[l.key & 3u];
    let packed = atlas_of(o)[layer];
    let p = paint_of(o, layer, up);
    var line = h;
    var area = side_area(h.xy, h.z);
    if (l.c < 1.0 - 1e-5) {
        let hc = half_plane(vec2<u32>(packed & 0xffffu, packed >> 16u), local, size, l.c);
        if (hc.z <= 1.5) {
            area = both_area(h.xy, h.z, hc.xy, hc.z);
            let n = select(h.xy, hc.xy, l.c < side_area(h.xy, h.z));
            line = vec3<f32>(n, offset_for(n, area));
        } else {
            area *= l.c;
            line = vec3<f32>(h.xy, offset_for(h.xy, area));
        }
    }
    if (area <= 1e-6) {
        return px;
    }
    return lay_line(px, p, area, line);
}

// A layer's place in a pixel's order: key = (object + 1) << 2 | step (an object's layers in their order: background
// stroke, fill, stroke; a raster's: 1), 0 the raster base; its depth there; its coverage.
struct Layer {
    key: u32,
    z: f32,
    c: f32,
};

// Whether layer a is laid before b: farther, or as far and earlier in the order (a 2D view's order alone).
fn before(a: Layer, b: Layer) -> bool {
    return a.z > b.z || (a.z == b.z && a.key < b.key);
}

// A layer's paint at the pixel centred at `up` (view pixels, y up; for gradients): object o's background stroke,
// fill or stroke (`layer`, as its atlas origins are numbered), as its colors give it.
fn painted(o: u32, layer: u32, up: vec2<f32>) -> vec4<f32> {
    if (layer == 2u) {
        return paint(o, background_of(o), 0u, 0u, 0u, up);
    }
    if (layer == 0u) {
        return paint(o, fill_of(o), brush_of(o).x, brush2_of(o).x, brush_of(o).y, up);
    }
    return paint(o, stroke_of(o), brush_of(o).z, brush2_of(o).y, brush_of(o).w, up);
}

// Whether the view has lit content (paths or meshes with a material): a view with none composites by a pipeline
// without the light's code and a mix's light (whose registers it would pay for unused).
override lighting: bool = false;

// Whether the view lays rasters (a 2D view's points and meshes, a 3D view's raster base), see-through fragments'
// lists and see-through points' slabs: a view without them composites by a pipeline without their code, whose
// registers (as many as the pixel's longest path through the composite needs) every pixel of the view would pay for
// unused.
override rasters: bool = true;
override lists: bool = true;
override points: bool = false;

// A layer's paint as a mix: a fill with a material lit.
fn paint_of(o: u32, layer: u32, up: vec2<f32>) -> Mix {
    let p = painted(o, layer, up);
    if (lighting && layer == 0u && material_of(o).w > 0.5) {
        return lit(o, p, up);
    }
    return painted_mix(p);
}

// A fill with a material at the pixel centred at `up`: its paint (premultiplied) the base color of a surface lit by
// the view's lights where its plane passes through the pixel, its light exposed (`light.wgsl`). Where it is opaque,
// the light from all around reaches it as the view's ambient occlusion says (what is seen through is not in the depth
// that is found from).
fn lit(o: u32, p: vec4<f32>, up: vec2<f32>) -> Mix {
    if (p.a <= 0.0) {
        return light_mix(p);
    }
    let pixel = vec2<f32>(up.x, frame.size.y - up.y);
    let z = -plane_depth(o, pixel); // (z / w: its depth from the far plane, negated: reversed Z)
    let h = frame.inverse * vec4<f32>(pixel.x / frame.size.x * 2.0 - 1.0, 1.0 - pixel.y / frame.size.y * 2.0, z, 1.0);
    let world = h.xyz / h.w;
    let v = select(frame.toward.xyz, normalize(frame.eye.xyz - world), frame.eye.w > 0.5);
    let m = material_of(o);
    var ao = 1.0;
    if (frame.occlusion.x > 0.0 && p.a >= 1.0 - 1e-5) {
        ao = textureLoad(occlusion, vec2<i32>(pixel), 0).x;
    }
    let radiance = reflected(linear(p.rgb / p.a), m.x, m.y, m.z, normal_of(o).xyz, world, v, ao);
    return light_mix(vec4<f32>(radiance * frame.lighting.y * p.a, p.a));
}

// Object o's plane's depth at `at` (view pixels): from its reference point (its flat's, shared to the bit), where its
// plane keeps its depth's digits.
fn plane_depth(o: u32, at: vec2<f32>) -> f32 {
    return dot(place_of(o).xy, at - vec2<f32>(flags_of(o).zw)) + place_of(o).z;
}

// Object o's depth at the pixel `centre`: its plane's; its strokes', where it is not planar, as they cover the pixel
// (`origin`: the layer's atlas; `local`: the pixel in its box).
fn depth_at(o: u32, step: u32, origin: vec2<u32>, local: vec2<i32>, centre: vec2<f32>) -> f32 {
    let z = plane_depth(o, centre);
    if (flags_of(o).x == 0u || step == 1u) {
        return z;
    }
    let at = origin + vec2<u32>(local);
    let v = stroke_depth(at.y * u32(frame.size.z) + at.x);
    return select(z, -bitcast<f32>(v << 1u), v != 0u);
}

// Object o's layer `step` at the pixel `centre` (view pixels), `local` in its box: its place in the order and its
// coverage (0: none; `mask`: its tile entry's, see `covered`).
fn layer_at(o: u32, mask: u32, step: u32, local: vec2<i32>, centre: vec2<f32>) -> Layer {
    let key = ((o + 1u) << 2u) | step;
    if (atlas_of(o).w != NONE) {
        return Layer(key, plane_depth(o, centre), select(0.0, 1.0, step == 1u));
    }
    let packed = atlas_of(o)[array<u32, 3>(2u, 0u, 1u)[step]];
    if (packed == NONE) {
        return Layer(key, 0.0, 0.0);
    }
    let origin = vec2<u32>(packed & 0xffffu, packed >> 16u);
    return Layer(key, depth_at(o, step, origin, local, centre), covered(mask, array<u32, 3>(2u, 0u, 1u)[step], origin, local, vec2<i32>(rect_of(o).zw)));
}

// What lies under the group (`frame.counts.y`), or a 3D view's raster base, at pixel `gid`, as a mix: display paint,
// or (where it carries light: `frame.counts.w` bit 1) its paint and its light, as the raster base's two targets or the
// group before left them.
fn base_at(gid: vec2<u32>) -> Mix {
    let p = textureLoad(base, gid, 0);
    if ((frame.counts.w & 1u) == 0u) {
        return painted_mix(p);
    }
    return Mix(p, textureLoad(base_light, gid, 0));
}

// The pixel `gid` (centred at `up`) with layer l laid over it.
fn settle(px: Pixel, l: Layer, gid: vec2<u32>, up: vec2<f32>) -> Pixel {
    if (l.key == 0u) {
        return lay_raster(px, base_at(gid), true, vec2<u32>(0u), vec2<i32>(gid), vec2<i32>(frame.size.xy));
    }
    let o = (l.key >> 2u) - 1u;
    let local = vec2<i32>(vec2<f32>(gid) - rect_of(o).xy);
    let size = vec2<i32>(rect_of(o).zw);
    let raster = atlas_of(o).w;
    if (raster != NONE) {
        let origin = vec2<u32>(raster & 0xffffu, raster >> 16u);
        return lay_raster(px, painted_mix(textureLoad(layers, origin + vec2<u32>(local), 0)), false, origin, local, size);
    }
    let layer = array<u32, 3>(2u, 0u, 1u)[l.key & 3u];
    let packed = atlas_of(o)[layer];
    return lay(px, paint_of(o, layer, up), l.c, vec2<u32>(packed & 0xffffu, packed >> 16u), local, size);
}

// A raster's coverage (its alpha) at a pixel, 0 outside its box: the raster base's (`base_layer`; `local` the view
// pixel, `size` the view's) or a raster layer's (`local` in its box of `size` at `origin` in the raster atlas).
fn raster_cover(base_layer: bool, origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>) -> f32 {
    if (local.x < 0 || local.y < 0 || local.x >= size.x || local.y >= size.y) {
        return 0.0;
    }
    let at = origin + vec2<u32>(local);
    if (base_layer) {
        return base_at(at)[1].a;
    }
    return textureLoad(layers, at, 0).a;
}

// The pixel with a raster's pixel r (a mix, premultiplied: its coverage its alpha, its samples') laid over it as a
// path's layer is, where it covers: a partial one in the half-plane its alpha's gradient gives, found as it is laid (a
// raster's coverage lies in no atlas), so that where its edge and a path's share the pixel, each covers its own part.
fn lay_raster(px: Pixel, r: Mix, base_layer: bool, origin: vec2<u32>, local: vec2<i32>, size: vec2<i32>) -> Pixel {
    let c = r[1].a;
    if (!rasters || c <= 0.0) {
        return px;
    }
    var line = vec3<f32>(0.0, 0.0, 2.0);
    if (c < 1.0 - 1e-5) {
        let g = vec2<f32>(
            raster_cover(base_layer, origin, local + vec2<i32>(1, 0), size) - raster_cover(base_layer, origin, local - vec2<i32>(1, 0), size),
            raster_cover(base_layer, origin, local - vec2<i32>(0, 1), size) - raster_cover(base_layer, origin, local + vec2<i32>(0, 1), size),
        );
        line = line_of(g, c);
    }
    return lay_line(px, divided(r, c), c, line);
}

// A see-through fragment found in a pixel's list: its node, and its index + 1 (0: none found).
struct Found {
    node: Node,
    at: u32,
};

// Whether fragment a comes before b in their order: farther first, then by key and color, then by index (what a
// pixel shows does not depend on the order the GPU appended its fragments in: only identical ones swap).
fn node_before(a: Found, b: Found) -> bool {
    let x = a.node;
    let y = b.node;
    return x.depth > y.depth || (x.depth == y.depth && (x.key < y.key || (x.key == y.key && (x.color < y.color || (x.color == y.color && a.at < b.at)))));
}

// The first of a pixel's fragments (its list from `head`) after `after` (at 0: the first of all).
fn next_node(head: u32, after: Found) -> Found {
    var best = Found(Node(0.0, 0u, 0u, 0u), 0u);
    var at = head;
    loop {
        if (at == 0u) {
            break;
        }
        let here = Found(list_node(at - 1u), at);
        if ((after.at == 0u || node_before(after, here)) && (best.at == 0u || node_before(here, best))) {
            best = here;
        }
        at = here.node.next;
    }
    return best;
}

// A fragment's place among the layers: at its depth pushed back as the base's is (a path drawn on it shows), after
// the base among equals.
fn node_layer(f: Found) -> Layer {
    return Layer(1u, f.node.depth * (1.0 - frame.depth.x), 1.0);
}

const SAME_LAYER: f32 = 1e-5; // a stroke's own fragments this close are one layer (its joints)
const FEW: u32 = 8u;          // layers a pixel where depths cross sorts at once
const SLABS: u32 = 4u;        // a pixel's nearest layers its see-through points are laid among (`bound`)
const NO_LAYER: f32 = -3.0e38; // nearer than every layer: where a pixel has fewer than SLABS (`bound`)

// A pixel's see-through points that come before a layer at depth z, from slab `first` on, composited in their order,
// and the first slab still to come. Slab j holds its points between the j-th and the (j+1)-th of its nearest layers
// (`bound`), blended in their order (`blend_lists.wgsl`): it comes before the (j+1)-th, wherever the composite meets
// that depth (a layer it hides, it never meets: the slab comes before the next it lays); the last, after everything.
struct Points {
    mix: Mix,
    next: u32,
};

fn points_before(first: u32, z: f32, gid: vec2<u32>) -> Points {
    var out = Points(Mix(), first);
    if (!points || first > SLABS) {
        return out;
    }
    let bounds = textureLoad(slab_bounds, gid, 0);
    for (var j = first; j <= SLABS; j++) {
        if (j < SLABS && z > bounds[j]) {
            break; // farther than the layer after slab j
        }
        if (bounds[j - 1u] > NO_LAYER) {
            out.mix = over(painted_mix(textureLoad(slabs, gid, i32(j - 1u), 0)), out.mix);
        }
        out.next = j + 1u;
    }
    return out;
}

// The pixel with what comes before `until` of its fragments from `u.next` on, of its base's `u.samples` (a bit each:
// not laid yet) and of its points laid over it as one layer: composited sample by sample (a base sample under its
// fragments, nearest last; a stroke's overlapping pieces once; points over every sample), then the samples' mean, so
// no seam shows where a mesh's triangles meet inside the pixel, nor where the base and the fragments share it.
fn slab(u: Under, head: u32, until: Layer, gid: vec2<u32>) -> Under {
    if (!lists || ((u.next.at == 0u || !before(node_layer(u.next), until)) && u.samples == 0u)) {
        return u;
    }
    var out = u;
    var acc: array<Mix, 8>;
    var kept: array<vec2<u32>, 8>; // per sample, the last fragment laid: its layer (record and kind), its depth
    var laid = false;
    for (var s = 0u; s < 8u; s++) {
        acc[s] = Mix();
        kept[s] = vec2<u32>(NONE, 0u);
        if ((u.samples & (1u << s)) != 0u && before(Layer(0u, base_sample_depth(gid, s) * (1.0 - frame.depth.x), 1.0), until)) {
            acc[s] = base_sample(gid, s);
            out.samples &= ~(1u << s);
            laid = true;
        }
    }
    var f = u.next;
    loop {
        if (f.at == 0u || !before(node_layer(f), until)) {
            break;
        }
        let farther = points_before(out.slab, node_layer(f).z, gid);
        out.slab = farther.next;
        if (farther.mix[1].a > 0.0) {
            for (var s = 0u; s < frame.lists.w; s++) {
                acc[s] = over(farther.mix, acc[s]);
            }
            out.shown += 1u;
        }
        let c = rgba8(f.node.color);
        let p = painted_mix(vec4<f32>(c.rgb * c.a, c.a));
        let mask = (f.node.key >> 3u) & 0xffu;
        let layer = f.node.key & 0xfffff803u;
        for (var s = 0u; s < 8u; s++) {
            let again = (f.node.key & 3u) == 3u && kept[s].x == layer && bitcast<f32>(kept[s].y) - f.node.depth <= SAME_LAYER;
            if ((mask & (1u << s)) != 0u && !again) {
                acc[s] = over(p, acc[s]);
                kept[s] = vec2<u32>(layer, bitcast<u32>(f.node.depth));
            }
        }
        laid = true;
        f = next_node(head, f);
    }
    out.next = f;
    if (laid) {
        var sum = Mix();
        for (var s = 0u; s < 8u; s++) {
            sum += acc[s];
        }
        out.px = lay(out.px, divided(sum, f32(frame.lists.w)), 1.0, vec2<u32>(0u), vec2<i32>(0), vec2<i32>(0));
    }
    return out;
}

// What lies under the layers from `until` on: the base, the see-through fragments and points.
struct Under {
    px: Pixel,
    next: Found,     // the first fragment not laid
    base_left: bool, // the base (as one layer) not laid
    samples: u32,    // where the pixel has fragments, the base's samples not laid (instead)
    slab: u32,       // the first of its points' slabs not laid (`points_before`)
    shown: u32,      // how many times points were laid
};

// The pixel with the base, the see-through fragments (its list from `head`) and points that come before `until` laid
// over it, in their order: the points once the base is (they lie in front of its opaque samples).
fn under(u: Under, head: u32, base: Layer, until: Layer, gid: vec2<u32>, up: vec2<f32>) -> Under {
    var out = u;
    if (u.base_left && before(base, until)) {
        out.px = settle(out.px, base, gid, up);
        out.base_left = false;
    }
    out = slab(out, head, until, gid);
    if (!out.base_left) {
        let farther = points_before(out.slab, until.z, gid);
        out.slab = farther.next;
        if (farther.mix[1].a > 0.0) {
            out.px = lay(out.px, farther.mix, 1.0, vec2<u32>(0u), vec2<i32>(0), vec2<i32>(0));
            out.shown += 1u;
        }
    }
    return out;
}

// Each pixel of the view: the layers of its tile's objects laid in depth order, farthest first (the draw order among
// equal depths: a 2D view's draw order), with a 3D view's raster base and see-through fragments in their places. Its
// tile's list comes in the order its objects' depths suggest (a 2D view's: the draw order), so a pixel lays the
// layers as they come and checks only that each comes after the last (`laid`); where one does not (where depths
// cross), the pixel takes them again in their order (`crossed`): in the compute form, a second pass over the pixels
// the first lists, so that the few where depths cross keep the rest from waiting.

// What a pixel's composite starts from: what lies under its layers (the background, or what the groups before laid),
// a 3D view's raster base as a layer and the depth past which it hides everything, its see-through fragments' list,
// its tile's list, and where it is.
struct Begun {
    fresh: Under,
    base_layer: Layer,
    hidden: f32,
    head: u32,
    first: u32,
    end: u32,
    entries: u32,
    pixel: vec2<f32>,
    centre: vec2<f32>,
    up: vec2<f32>,
};

// Pixel gid's see-through fragments' list (only in the listed rows are the heads this frame's): its head (0: none).
fn head_at(gid: vec2<u32>) -> u32 {
    if (lists && frame.lists.x == 1u && gid.y >= frame.lists.y && gid.y < frame.lists.z) {
        return list_head(gid.y * u32(frame.size.x) + gid.x);
    }
    return 0u;
}

fn begin(gid: vec2<u32>) -> Begun {
    let tile = (gid.y / TILE) * frame.tiles.x + gid.x / TILE;
    let pixel = vec2<f32>(gid);
    let centre = pixel + 0.5;
    let up = vec2<f32>(pixel.x + 0.5, frame.size.y - pixel.y - 0.5);
    var start: Pixel;
    start.mode = 0u;
    start.s.n = vec2<f32>(1.0, 0.0);
    start.s.d = 1.0;
    start.s.a = 0.0;
    start.s.inside = painted_mix(frame.background);
    if (frame.counts.y == 1u) {
        start.s.inside = base_at(gid);
    }
    start.s.outside = start.s.inside;
    // a 3D view's raster base: a layer at its depth (a path drawn on it, a little nearer than it, shows), or (laid
    // already) hiding what lies behind it; nothing shows behind it where it is opaque
    let base_layer = Layer(0u, textureLoad(base_depth, min(gid, textureDimensions(base_depth) - 1u), 0).r * (1.0 - frame.depth.x), 1.0);
    var hidden = 3.0;
    if ((frame.counts.z == 1u && base_at(gid)[1].a >= 1.0) || frame.counts.z == 2u) {
        hidden = base_layer.z;
    }
    // its see-through fragments: where it has some, its base sample by sample among them; elsewhere one layer
    let head = head_at(gid);
    let none = Found(Node(0.0, 0u, 0u, 0u), 0u);
    let all = (1u << frame.lists.w) - 1u;
    let fresh = Under(start, next_node(head, none), frame.counts.z == 1u && head == 0u, select(0u, all, frame.counts.z == 1u && head != 0u), 1u, 0u);
    let first = tile_entry(tile);
    let end = tile_entry(tile + 1u);
    let entries = frame.tiles.x * frame.tiles.y + 1u; // where the tiles' entries begin
    return Begun(fresh, base_layer, hidden, head, first, end, entries, pixel, centre, up);
}

// The pixel's mix once what lies under nothing more (the base, the fragments and points left) is laid.
fn finish(u0: Under, b: Begun, gid: vec2<u32>) -> Mix {
    let u = under(u0, b.head, b.base_layer, Layer(NONE, NO_LAYER, 0.0), gid, b.up);
    return u.px.s.a * u.px.s.inside + (1.0 - u.px.s.a) * u.px.s.outside;
}

// The pixel's layers laid as they come: its mix, where each comes after the last (else, ordered false).
struct Laid {
    ordered: bool,
    mix: Mix,
};

fn laid(gid: vec2<u32>, b: Begun) -> Laid {
    let base_layer = b.base_layer;
    let hidden = b.hidden;
    let head = b.head;
    let first = b.first;
    let end = b.end;
    let entries = b.entries;
    let pixel = b.pixel;
    let centre = b.centre;
    let up = b.up;
    var u = b.fresh;
    var last = Layer(0u, 3.0e38, 0.0); // nothing laid yet: before everything
    var ordered = true;
    for (var k = first; k < end && ordered; k++) {
        let e = tile_entry(entries + k);
        let o = e & 0xffffffu;
        let mask = e >> 24u;
            let local = vec2<i32>(pixel - rect_of(o).xy);
        let bsize = vec2<i32>(rect_of(o).zw);
        if (local.x < 0 || local.y < 0 || local.x >= bsize.x || local.y >= bsize.y) {
            continue;
        }
        let z = plane_depth(o, centre);
        let key = (o + 1u) << 2u;
        let raster = atlas_of(o).w;
        for (var step = 0u; step < 3u; step++) {
            var l = Layer(key | step, z, 1.0);
            var p: Mix;
            var origin = vec2<u32>(0u);
            if (raster != NONE) {
                if (!rasters || step != 1u) {
                    continue;
                }
                origin = vec2<u32>(raster & 0xffffu, raster >> 16u);
                p = painted_mix(textureLoad(layers, origin + vec2<u32>(local), 0));
            } else {
                let layer = array<u32, 3>(2u, 0u, 1u)[step];
                let packed = atlas_of(o)[layer];
                if (packed == NONE) {
                    continue;
                }
                origin = vec2<u32>(packed & 0xffffu, packed >> 16u);
                l.c = covered(mask, layer, origin, local, bsize);
                if (l.c <= 1e-5) {
                    continue;
                }
                if (flags_of(o).x != 0u && step != 1u) {
                    l.z = depth_at(o, step, origin, local, centre);
                }
                p = paint_of(o, layer, up);
            }
            if (l.z > hidden) {
                continue;
            }
            if (before(l, last) || (frame.depth.x > 0.0 && nearer_part(l, last).z <= 1.5)) {
                ordered = false;
                break;
            }
            u = under(u, head, base_layer, l, gid, up);
            if (raster != NONE) {
                u.px = lay_raster(u.px, p, false, origin, local, bsize);
            } else {
                u.px = lay(u.px, p, l.c, origin, local, bsize);
            }
            last = l;
        }
    }
    if (!ordered) {
        return Laid(false, Mix());
    }
    return Laid(true, finish(u, b, gid));
}

// The pixel where depths cross: every layer again, in their order.
fn crossed(gid: vec2<u32>, b: Begun) -> Mix {
    let base_layer = b.base_layer;
    let hidden = b.hidden;
    let head = b.head;
    let first = b.first;
    let end = b.end;
    let entries = b.entries;
    let pixel = b.pixel;
    let centre = b.centre;
    let up = b.up;
    var u = b.fresh;
    // its layers in their order, FEW at a time: one pass over its tile's list keeps the FEW first after the last laid,
    // sorted as they come (a pixel where n layers cross costs n / FEW passes, not n)
    var last = Layer(0u, 3.0e38, 0.0); // nothing laid yet: before everything
    // the last laid, if a whole path layer and nothing since: its paint, and the pixel before it
    var prev = Layer(NONE, 0.0, 0.0);
    var prev_paint = Mix();
    var prev_under = u.px;
    loop {
        var few: array<Layer, FEW>;
        var n = 0u;
        for (var k = first; k < end; k++) {
            let e = tile_entry(entries + k);
            let o = e & 0xffffffu;
            let mask = e >> 24u;
            let local = vec2<i32>(pixel - rect_of(o).xy);
            let bsize = vec2<i32>(rect_of(o).zw);
            if (local.x < 0 || local.y < 0 || local.x >= bsize.x || local.y >= bsize.y) {
                continue;
            }
            for (var step = 0u; step < 3u; step++) {
                let l = layer_at(o, mask, step, local, centre);
                if (l.c <= 1e-5 || l.z > hidden || !before(last, l) || (n == FEW && !before(l, few[FEW - 1u]))) {
                    continue;
                }
                var j = min(n, FEW - 1u);
                for (; j > 0u && before(l, few[j - 1u]); j--) {
                    few[j] = few[j - 1u];
                }
                few[j] = l;
                n = min(n + 1u, FEW);
            }
        }
        for (var i = 0u; i < n; i++) {
            let before_under = u.base_left;
            let next_before = u.next.at;
            let shown_before = u.shown;
            u = under(u, head, base_layer, few[i], gid, up);
            if (u.base_left != before_under || u.next.at != next_before || u.shown != shown_before) {
                prev = Layer(NONE, 0.0, 0.0);
            }
            let path = few[i].key != 0u && atlas_of((few[i].key >> 2u) - 1u).w == NONE;
            var paint = Mix();
            if (path) {
                let o = (few[i].key >> 2u) - 1u;
                paint = paint_of(o, array<u32, 3>(2u, 0u, 1u)[few[i].key & 3u], up);
            }
            let h = nearer_part(few[i], prev);
            let whole = few[i].c >= 1.0 - 1e-5;
            let laid_before = u.px;
            if (h.z <= 1.5 && path && prev_paint[1].a >= 1.0 - 1e-5) {
                // over an opaque layer: only where it is nearer (behind it, it is hidden)
                u.px = lay_nearer(u.px, few[i], h, gid, up);
            } else if (h.z <= 1.5 && path && whole && prev_under.mode == 0u) {
                // over a see-through one, both whole, on what is one colour: each over the other where it is nearer
                u.px.mode = 2u;
                u.px.s.n = h.xy;
                u.px.s.d = h.z;
                u.px.s.a = side_area(h.xy, h.z);
                u.px.s.inside = over(paint, laid_before.s.inside);
                u.px.s.outside = over(prev_paint, over(paint, prev_under.s.inside));
            } else {
                u.px = settle(u.px, few[i], gid, up);
            }
            prev = Layer(NONE, 0.0, 0.0);
            if (path && whole) {
                prev = few[i];
                prev_paint = paint;
                prev_under = laid_before;
            }
        }
        if (n < FEW) {
            break;
        }
        last = few[FEW - 1u];
    }
    return finish(u, b, gid);
}

// A pixel's nearest layers' depths met so far, far to near (NO_LAYER past the last), with a layer at depth z among them:
// where all SLABS are met, only if it is nearer than the farthest, which makes room.
fn nearer(k: vec4<f32>, z: f32) -> vec4<f32> {
    // A boundary is a depth, not a fragment: triangles and per-sample invocations can
    // contribute several nodes at one depth without creating another slab for points.
    if (any(k == vec4<f32>(z))) {
        return k;
    }
    var out = k;
    if (out.w > NO_LAYER) {
        if (z >= out.x) {
            return out;
        }
        out = vec4<f32>(out.yzw, NO_LAYER);
    }
    var j = SLABS - 1u;
    for (; j > 0u && out[j - 1u] < z; j--) {
        out[j] = out[j - 1u];
    }
    out[j] = z;
    return out;
}

// A 3D view's slab bounds: the depths of pixel gid's SLABS nearest layers, far to near (NO_LAYER where it has fewer),
// its paths' and its see-through fragments', as the composite takes them (`layer_at`, `node_layer`), but what is fixed
// in the frame (in front of everything, it parts no points). A see-through point counts those farther than it
// (`blend_lists.wgsl`'s `slab_of`): with none, it is blended into the base; else into the slab between two of them,
// which the composite lays between them (`points_before`). A point behind SLABS layers is behind them all: the base.
fn bound(gid: vec2<u32>) -> vec4<f32> {
    let tile = (gid.y / TILE) * frame.tiles.x + gid.x / TILE;
    let entries = frame.tiles.x * frame.tiles.y + 1u;
    let pixel = vec2<f32>(gid);
    var k = vec4<f32>(NO_LAYER);
    for (var i = tile_entry(tile); i < tile_entry(tile + 1u); i++) {
        let e = tile_entry(entries + i);
        let o = e & 0xffffffu;
        let local = vec2<i32>(pixel - rect_of(o).xy);
        let size = vec2<i32>(rect_of(o).zw);
        if (local.x < 0 || local.y < 0 || local.x >= size.x || local.y >= size.y) {
            continue;
        }
        for (var step = 0u; step < 3u; step++) {
            let l = layer_at(o, e >> 24u, step, local, pixel + 0.5);
            if (l.c > 1e-5 && l.z > -1.0) {
                k = nearer(k, l.z);
            }
        }
    }
    var at = head_at(gid);
    loop {
        if (at == 0u) {
            break;
        }
        let f = Found(list_node(at - 1u), at);
        k = nearer(k, node_layer(f).z);
        at = f.node.next;
    }
    return k;
}

const TILE: u32 = 16u;

// A depth no layer has (a 3D view's depths run from the near plane, -1, to the far plane, 0: z / w - 1).
const NO_DEPTH: f32 = 2.0;

// ── the composite's depth entry: a light's shadow map ─────────────────────────

// A triangle over the whole target: a fragment per pixel.
@vertex
fn vs_cover(@builtin(vertex_index) v: u32) -> @builtin(position) vec4<f32> {
    let p = vec2<f32>(f32((v << 1u) & 2u), f32(v & 2u));
    return vec4<f32>(p * 2.0 - 1.0, 0.0, 1.0);
}

// Whose depth a pass of nearest layers draws: a light's map (standard Z; what is half opaque or more casts a shadow),
// or (`view_depth`) a view's opaque depth, for its ambient occlusion (reversed Z; what is opaque, as its raster base's
// opaque meshes are).
override view_depth: bool = false;

// What casts a shadow at texel `gid` of a light's map (the view, seen from the light), or shuts out light at a pixel
// of a view: the nearest of its tile's objects' layers that cover half the texel or more where their paint is at least
// `opacity`; its depth (3: none).
fn nearest(gid: vec2<u32>, opacity: f32) -> f32 {
    let tile = (gid.y / TILE) * frame.tiles.x + gid.x / TILE;
    let pixel = vec2<f32>(gid);
    let centre = pixel + 0.5;
    let up = vec2<f32>(pixel.x + 0.5, frame.size.y - pixel.y - 0.5);
    let entries = frame.tiles.x * frame.tiles.y + 1u;
    var z = 3.0;
    for (var k = tile_entry(tile); k < tile_entry(tile + 1u); k++) {
        let e = tile_entry(entries + k);
        let o = e & 0xffffffu;
        let mask = e >> 24u;
        let local = vec2<i32>(pixel - rect_of(o).xy);
        if (any(local < vec2<i32>(0)) || any(local >= vec2<i32>(rect_of(o).zw))) {
            continue;
        }
        for (var step = 0u; step < 3u; step++) {
            let l = layer_at(o, mask, step, local, centre);
            if (l.c >= 0.5 && l.z < z && painted(o, array<u32, 3>(2u, 0u, 1u)[step], up).a >= opacity) {
                z = l.z;
            }
        }
    }
    return z;
}

// A light's map, or a view's opaque depth: its paths' nearest depth where it is nearer than its meshes' (the depth
// test's).
@fragment
fn fs_nearest(@builtin(position) at: vec4<f32>) -> @builtin(frag_depth) f32 {
    let z = nearest(vec2<u32>(at.xy), select(0.5, 1.0 - 1e-5, view_depth));
    if (z > 0.5) {
        discard;
    }
    return select(z + 1.0, -z, view_depth); // (z / w, as its meshes write it: a light's from the near plane, a view's reversed)
}
