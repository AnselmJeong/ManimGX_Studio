// The raster pipeline: point clouds and meshes (paths are drawn exactly: see `vector.wgsl`), a 3D
// view's into its z-buffered base, a 2D view's each alone into its rectangle of a raster atlas.
// Every object is drawn from resident shapes: clip = C1·S1 + C2·S2 (term 2 only while morphing),
// where Ck = camera · Mk is composed on the CPU once per object: the camera is one more affine map
// in the blend, so a vertex costs one 4×4 per term and no branches. Fixed-in-frame objects are just
// another matrix; depth is real depth.
//
// Kinds differ only in how a shape's vertices become triangles:
//   points  a camera-facing disk per point, sized in scene units; one with no opacity makes no
//           fragments.
//   meshes  their triangles, optionally textured; a surface's faces' edges as screen-space ribbons
//           with miter joins.
// Colors are per object (flat); only gradients are evaluated per fragment, in their own shaders.
// A tween's paint is two paints and how far the second is mixed in: colors are mixed once per
// object on the CPU, rows (gradient stops, per-vertex colors) here — so a tween uploads nothing.

struct View {
    pixels: vec4<f32>,   // width, height (pixels), samples per pixel, unused
    light: vec4<f32>,    // CE's light position
    toward: vec4<f32>,   // unit vector toward the viewer (two-sided lighting); w: stroke depth bias
    eye: vec4<f32>,      // where it sees from (w = 1: a 3D view's perspective)
    lighting: vec4<f32>, // its lights (`light.wgsl`), how many; the exposure; the tone mapping (1: AgX); its bloom
    lights: array<Light, 8>,
    harmonics: array<vec4<f32>, 9>, // its environment's diffuse light (`environment.rs`)
    occlusion: vec4<f32>,           // its ambient occlusion: how much (0: none), how far (`occlusion.rs`)
};

struct Instance {
    c1_0: vec4<f32>, c1_1: vec4<f32>, c1_2: vec4<f32>, c1_3: vec4<f32>, // clip matrix of term 1
    c2_0: vec4<f32>, c2_1: vec4<f32>, c2_2: vec4<f32>, c2_3: vec4<f32>, // clip matrix of term 2
    m1_0: vec4<f32>, m1_1: vec4<f32>, m1_2: vec4<f32>,                  // world matrices (lit meshes)
    m2_0: vec4<f32>, m2_1: vec4<f32>, m2_2: vec4<f32>,
    params: vec4<f32>,   // window lo, window hi, stroke width px, background width px
    extra: vec4<f32>,    // point radius px at w = 1, light amount (gradients)
    ids: vec4<u32>,      // vertex base of term 1, of term 2 (NONE), flags (from bit 8: the record's place in its view)
    fill: vec4<f32>,     // the paint (`Paint`): solid colors (alpha −1: a gradient)
    stroke: vec4<f32>,
    background: vec4<f32>,
    gradient: vec4<f32>, // gradient axis on screen: origin (px), direction / |direction|² (px)
    brush: vec4<u32>,    // fill rows (offset, count), stroke rows (offset, count)
    brush2: vec4<u32>,   // paint 2's fill rows, stroke rows (offsets, counts as paint 1's); how far it is mixed in (f32 bits, 0: not)
    material: vec4<f32>, // metallic, roughness, reflectance (an instance with MATERIAL: lit by the view's lights)
};

const NONE: u32 = 0xffffffffu;
const OVERLAY: u32 = 1u; // fixed in the frame
const LIT: u32 = 4u;
const TEXTURED: u32 = 8u;
const NEAREST: u32 = 16u;
const CUBIC: u32 = 32u;
const MATERIAL: u32 = 64u;

// The rest it reads (the store's arrays, the objects) comes through its head's loaders (`blend_buffers.wgsl`); a 3D
// view's see-through lists' entries are in `blend_lists.wgsl`.
@group(0) @binding(0) var<uniform> view: View;
// the view's lights' shadow maps (`shadow.rs`), a layer each, and how they are compared (bilinearly): a group of
// their own, which the passes that draw them do not bind
@group(3) @binding(0) var shadow_maps: texture_depth_2d_array;
@group(3) @binding(1) var shadow_compare: sampler_comparison;
@group(3) @binding(2) var dfg_table: texture_2d<f32>;
@group(3) @binding(3) var dfg_linear: sampler;
@group(3) @binding(4) var environment: texture_cube<f32>;
@group(3) @binding(5) var occlusion: texture_2d<f32>; // its ambient occlusion (`occlusion.rs`; 1x1 where it has none)
@group(1) @binding(0) var image: texture_2d<f32>;
@group(1) @binding(1) var image_sampler: sampler;

fn light_count() -> u32 {
    return u32(view.lighting.x);
}

fn light_at(i: u32) -> Light {
    return view.lights[i];
}

// The shadow maps, as `light.wgsl`'s `shadowed` reads them: a layer's comparison at uv (bilinear), a texel's size.
fn shadow_compare_at(uv: vec2<f32>, layer: i32, depth: f32) -> f32 {
    return textureSampleCompareLevel(shadow_maps, shadow_compare, uv, layer, depth);
}

fn shadow_texel() -> vec2<f32> {
    return 1.0 / vec2<f32>(textureDimensions(shadow_maps));
}

// The DFG table at (NoV, perceptual roughness), as `light.wgsl`'s `reflected` reads it.
fn dfg_at(NoV: f32, perceptual: f32) -> vec2<f32> {
    return textureSampleLevel(dfg_table, dfg_linear, vec2<f32>(NoV, perceptual), 0.0).xy;
}

// The environment, as `light.wgsl`'s `reflected` reads it: its cube's light toward d at a level, and its diffuse
// light's harmonics.
fn environment_at(d: vec3<f32>, level: f32) -> vec3<f32> {
    return textureSampleLevel(environment, dfg_linear, d, level).rgb;
}

fn harmonic(i: u32) -> vec3<f32> {
    return view.harmonics[i].xyz;
}

// The clip position of vertex `index` of object `i`.
fn clip(i: u32, index: u32) -> vec4<f32> {
    let h = vec4<f32>(vertex(index).xyz, 1.0);
    var c = vec4<f32>(dot(c1_0_of(i), h), dot(c1_1_of(i), h), dot(c1_2_of(i), h), dot(c1_3_of(i), h));
    let base2 = ids_of(i).y;
    if (base2 != NONE) {
        let g = vec4<f32>(vertex(base2 + (index - ids_of(i).x)).xyz, 1.0);
        c += vec4<f32>(dot(c2_0_of(i), g), dot(c2_1_of(i), g), dot(c2_2_of(i), g), dot(c2_3_of(i), g));
    }
    return c;
}

// Where a direction `d` from vertex `index` (and its morph's `d2` from term 2's) moves its clip position: so `clip`
// plus this is the clip position of the point that far along.
fn clip_along(i: u32, d: vec3<f32>, d2: vec3<f32>) -> vec4<f32> {
    let h = vec4<f32>(d, 0.0);
    var c = vec4<f32>(dot(c1_0_of(i), h), dot(c1_1_of(i), h), dot(c1_2_of(i), h), dot(c1_3_of(i), h));
    if (ids_of(i).y != NONE) {
        let g = vec4<f32>(d2, 0.0);
        c += vec4<f32>(dot(c2_0_of(i), g), dot(c2_1_of(i), g), dot(c2_2_of(i), g), dot(c2_3_of(i), g));
    }
    return c;
}

// A direction's projective differential at c, in pixel x, pixel y, depth. The common 1/c.w² cancels from a plane's
// gradient. Scaling each direction before the cross product makes its magnitude irrelevant, including tiny normals.
fn projected_direction(c: vec4<f32>, d: vec4<f32>) -> vec3<f32> {
    let v = (c.w * d.xyz - d.w * c.xyz) * vec3<f32>(0.5 * view.pixels.xy, 1.0);
    let scale = max(max(abs(v.x), abs(v.y)), abs(v.z));
    if (scale == 0.0) {
        return vec3<f32>(0.0);
    }
    return v / scale;
}

// A mesh face's tangent plane at its edge: (depth gradient in pixels, depth at `at`). Derivatives of the projective
// map give the gradient directly: subtracting projected nearby points loses the small tangent in f32 rounding.
// No gradient where the face has no normal or is seen edge on.
fn face_plane(i: u32, at: u32, to: u32) -> vec3<f32> {
    let ca = clip(i, at);
    let sa = screen(ca);
    let n = vertex_extra(at).xyz;
    let edge = vertex(to).xyz - vertex(at).xyz;
    var edge2 = vec3<f32>(0.0);
    var across2 = vec3<f32>(0.0);
    if (ids_of(i).y != NONE) {
        let k = ids_of(i).y - ids_of(i).x;
        edge2 = vertex(to + k).xyz - vertex(at + k).xyz;
        across2 = cross(vertex_extra(at + k).xyz, edge2);
    }
    let d1 = projected_direction(ca, clip_along(i, edge, edge2));
    let d2 = projected_direction(ca, clip_along(i, cross(n, edge), across2));
    let det = d1.x * d2.y - d1.y * d2.x;
    if (det * det <= 1e-12 * dot(d1.xy, d1.xy) * dot(d2.xy, d2.xy) || sa.z < 0.0 || screen(clip(i, to)).z < 0.0) {
        return vec3<f32>(0.0, 0.0, sa.z);
    }
    return vec3<f32>(d1.z * d2.y - d2.z * d1.y, d2.z * d1.x - d1.z * d2.x, 0.0) / det + vec3<f32>(0.0, 0.0, sa.z);
}

// How much nearer a face's edge is drawn than its face: a share of its depth (16 of its f32 steps) and its depth slope
// times a share of a pixel (4 times the half step the rasterizer snaps corners to: Direct3D's, Metal's, Vulkan's 1/256).
// `depth.wgsl` takes a face's pixels with its edges on them as the face's (its `STROKES`).
const PULL: vec2<f32> = vec2<f32>(16.0 * 1.2e-7, 4.0 / 512.0);

// Clip → (pixel x, pixel y, depth); points behind the camera get depth -1 (clipped away).
fn screen(c: vec4<f32>) -> vec3<f32> {
    if (c.w <= 1e-6) {
        return vec3<f32>(0.0, 0.0, -1.0);
    }
    return vec3<f32>((c.xy / c.w * 0.5 + 0.5) * view.pixels.xy, c.z / c.w);
}

fn to_clip(s: vec3<f32>) -> vec4<f32> {
    return vec4<f32>(s.xy / view.pixels.xy * 2.0 - 1.0, s.z, 1.0);
}

// The gradient at t along its axis (`stops`), lit like the object.
fn gradient(i: u32, first: u32, second: u32, count: u32, t: f32, light: f32) -> vec4<f32> {
    let c = stops(first, second, count, bitcast<f32>(brush2_of(i).z), t);
    return vec4<f32>(clamp(c.rgb + light, vec3<f32>(0.0), vec3<f32>(1.0)), c.a);
}

// Position along the object's gradient axis (both on screen).
fn along(i: u32, px: vec2<f32>) -> f32 {
    let g = gradient_of(i);
    return dot(px - g.xy, g.zw);
}

// ── edges ─────────────────────────────────────────────────────────────────────

// A count writes depth and stencil: the least fragment work a pass with a color target allows.
@fragment
fn fs_none() -> @location(0) vec4<f32> {
    return vec4<f32>(0.0);
}

// A face's edges show as its face does: the record's draw holds the faces a reveal shows (`Raster::shown`).
struct Stroked {
    @builtin(position) @invariant position: vec4<f32>, // counted and covered alike, to the bit
    @location(0) @interpolate(flat) color: vec4<f32>,
    @location(1) t: f32,
    @location(2) @interpolate(flat) i: u32,
};

// Offset of a joint between a segment with normal n and its neighbour with normal m (miter, limit 10).
fn joint(n: vec2<f32>, m: vec2<f32>, half: f32) -> vec2<f32> {
    let s = n + m;
    let l = length(s);
    if (l < 1e-6) {
        return n * half;
    }
    let dir = s / l;
    return dir * (half / max(dot(dir, n), 0.1));
}

fn normal(a: vec2<f32>, b: vec2<f32>) -> vec2<f32> {
    let d = b - a;
    let l = length(d);
    return select(vec2<f32>(0.0, 0.0), vec2<f32>(-d.y, d.x) / l, l > 1e-6);
}

// code: segment << 3 | corner (two triangles: a−, a+, b+ / a−, b+, b−).
fn ribbon(code: u32, i: u32, width: f32, color: vec4<f32>) -> Stroked {
    let a = code >> 3u;
    let corner = code & 7u;
    let b = a + 1u;
    let sa = screen(clip(i, a));
    let sb = screen(clip(i, b));
    let n = normal(sa.xy, sb.xy);
    let half = 0.5 * width;
    let prev = link(a).x;
    let next = link(b).y;
    var oa = n * half;
    var ob = n * half;
    if (prev != a && dot(n, n) > 0.5) {
        oa = joint(n, normal(screen(clip(i, prev)).xy, sa.xy), half);
    }
    if (next != b && dot(n, n) > 0.5) {
        ob = joint(n, normal(sb.xy, screen(clip(i, next)).xy), half);
    }
    let at_b = corner == 2u || corner == 4u || corner == 5u;
    let plus = corner == 1u || corner == 2u || corner == 4u;
    let offset = select(oa, ob, at_b);
    let s = select(sa, sb, at_b);
    let px = s.xy + select(-offset, offset, plus);
    var out: Stroked;
    // in 3D a face's edge lies on its face: each corner at the face's depth where it is (the plane tangent to the face
    // at the corner's end), pulled nearer by what rounding and the rasterizer's snapping can part them by (`PULL`), so
    // the face hides none of it, in any pass (its own see-through face sorts behind it); never nearer than depth 1
    var z = s.z;
    if (s.z >= 0.0) {
        let plane = select(face_plane(i, a, b), face_plane(i, b, a), at_b);
        z = plane.z + dot(plane.xy, px - s.xy);
        z = min(z + PULL.x * z + PULL.y * (abs(plane.x) + abs(plane.y)), max(s.z, 1.0));
    }
    out.position = to_clip(vec3<f32>(px, z));
    out.color = color;
    out.t = 0.0;
    if (color.a < 0.0) {
        out.t = along(i, px);
    }
    out.i = i;
    return out;
}

@vertex
fn vs_stroke(@builtin(vertex_index) code: u32, @builtin(instance_index) i: u32) -> Stroked {
    return ribbon(code, i, params_of(i).z, stroke_of(i));
}

fn stroked(in: Stroked) -> vec4<f32> {
    return premultiplied(in.color);
}

fn stroked_gradient(in: Stroked) -> vec4<f32> {
    return premultiplied(gradient(in.i, brush_of(in.i).z, brush2_of(in.i).y, brush_of(in.i).w, in.t, extra_of(in.i).y));
}

@fragment
fn fs_stroke(in: Stroked) -> @location(0) vec4<f32> {
    return stroked(in);
}

@fragment
fn fs_stroke_gradient(in: Stroked) -> @location(0) vec4<f32> {
    return stroked_gradient(in);
}

@fragment
fn fs_stroke_with_light(in: Stroked) -> Base {
    return painted(stroked(in));
}

@fragment
fn fs_stroke_gradient_with_light(in: Stroked) -> Base {
    return painted(stroked_gradient(in));
}

// ── points ────────────────────────────────────────────────────────────────────

struct Dotted {
    @builtin(position) @invariant position: vec4<f32>, // counted and covered alike, to the bit
    @location(0) local: vec2<f32>,
    @location(1) @interpolate(flat) color: vec4<f32>,
    @location(2) @interpolate(flat) radius: f32,
    @location(3) @interpolate(flat) i: u32,
};

// A point's or vertex's color: its own row when the brush has one per vertex.
fn vertex_color(i: u32, index: u32) -> vec4<f32> {
    let brush = brush_of(i);
    if (brush.y <= 1u) {
        return fill_of(i);
    }
    return row(brush.x, brush2_of(i).x, min(index - ids_of(i).x, brush.y - 1u), bitcast<f32>(brush2_of(i).z));
}

// Corner (0–5: two triangles over its square) of the disk of point `index` of object `i`. A
// point with no opacity is put outside the view: it makes no fragments.
fn disk(i: u32, index: u32, corner: u32) -> Dotted {
    let c = clip(i, index);
    let s = screen(c);
    let radius = extra_of(i).x / max(c.w, 1e-6);
    let local = vec2<f32>(
        select(-1.0, 1.0, corner == 1u || corner == 2u || corner == 4u),
        select(-1.0, 1.0, corner == 2u || corner == 4u || corner == 5u),
    );
    var out: Dotted;
    out.color = vertex_color(i, index);
    out.position = to_clip(vec3<f32>(s.xy + local * (radius + 1.0), select(s.z, -1.0, out.color.a <= 0.0)));
    out.local = local * (radius + 1.0) / max(radius, 1e-6);
    out.radius = radius;
    out.i = i;
    return out;
}

// code: point << 3 | corner.
@vertex
fn vs_points(@builtin(vertex_index) code: u32, @builtin(instance_index) i: u32) -> Dotted {
    return disk(i, code >> 3u, code & 7u);
}

// A point's disk, its edge antialiased.
fn dot_color(in: Dotted) -> vec4<f32> {
    let coverage = clamp((1.0 - length(in.local)) * in.radius + 0.5, 0.0, 1.0);
    return vec4<f32>(in.color.rgb, in.color.a * coverage);
}

fn dotted(in: Dotted) -> vec4<f32> {
    let c = dot_color(in);
    if (c.a <= 0.0) {
        discard;
    }
    return premultiplied(c);
}

@fragment
fn fs_points(in: Dotted) -> @location(0) vec4<f32> {
    return dotted(in);
}

@fragment
fn fs_points_with_light(in: Dotted) -> Base {
    return painted(dotted(in));
}

// ── meshes ────────────────────────────────────────────────────────────────────

struct Shaded {
    @builtin(position) @invariant position: vec4<f32>, // counted and covered alike, to the bit
    @location(0) color: vec4<f32>,
    @location(1) uv: vec2<f32>,
    @location(2) @interpolate(flat) textured: u32,
    @location(3) light: f32, // a lit texture's light (a colored mesh's is in its color)
    @location(4) @interpolate(flat) i: u32,
    @location(5) world: vec3<f32>,  // a mesh with a material: where it is
    @location(6) normal: vec3<f32>, // and which way it faces (scene coordinates)
};

fn affine(r0: vec4<f32>, r1: vec4<f32>, r2: vec4<f32>, p: vec3<f32>) -> vec3<f32> {
    let h = vec4<f32>(p, 1.0);
    return vec3<f32>(dot(r0, h), dot(r1, h), dot(r2, h));
}

// Rows of the cofactor of a matrix's linear part: how it carries normals.
fn carry(r0: vec4<f32>, r1: vec4<f32>, r2: vec4<f32>, n: vec3<f32>) -> vec3<f32> {
    return vec3<f32>(dot(cross(r1.xyz, r2.xyz), n), dot(cross(r2.xyz, r0.xyz), n), dot(cross(r0.xyz, r1.xyz), n));
}

// CE's light: half the cube of the cosine toward the light, halved again when facing away, on the side the eye sees
// from p (a 3D view's perspective; else, or `fixed` in the frame, the side toward the view).
fn shade(normal: vec3<f32>, p: vec3<f32>, fixed: bool) -> f32 {
    let toward_light = view.light.xyz - p;
    if (dot(normal, normal) == 0.0 || dot(toward_light, toward_light) == 0.0) {
        return 0.0;
    }
    let seen = select(view.toward.xyz, view.eye.xyz - p, view.eye.w > 0.5 && !fixed);
    let n = normalize(select(normal, -normal, dot(seen, normal) < 0.0));
    let cosine = dot(n, normalize(toward_light));
    // WGSL pow excludes negative bases; the signed cube is defined on both sides of a face.
    let amount = 0.5 * cosine * cosine * cosine;
    return select(amount, amount * 0.5, amount < 0.0);
}

// code: the vertex itself.
@vertex
fn vs_mesh(@builtin(vertex_index) index: u32, @builtin(instance_index) i: u32) -> Shaded {
    var color = vertex_color(i, index);
    let extra = vertex_extra(index);
    let flags = ids_of(i).z;
    var light = 0.0;
    var p = vec3<f32>(0.0);
    var n = vec3<f32>(0.0);
    if ((flags & (LIT | MATERIAL)) != 0u) {
        p = affine(m1_0_of(i), m1_1_of(i), m1_2_of(i), vertex(index).xyz);
        n = carry(m1_0_of(i), m1_1_of(i), m1_2_of(i), extra.xyz);
        let base2 = ids_of(i).y;
        if (base2 != NONE) {
            let k = base2 + (index - ids_of(i).x);
            p += affine(m2_0_of(i), m2_1_of(i), m2_2_of(i), vertex(k).xyz);
            n += carry(m2_0_of(i), m2_1_of(i), m2_2_of(i), vertex_extra(k).xyz);
        }
        // CE's light, once a vertex (a material's lights are the fragment's)
        if ((flags & LIT) != 0u && dot(n, n) > 1e-20) {
            light = shade(n, p, (flags & OVERLAY) != 0u);
            color = vec4<f32>(clamp(color.rgb + light, vec3<f32>(0.0), vec3<f32>(1.0)), color.a);
        }
    }
    var out: Shaded;
    out.position = clip(i, index);
    out.color = color;
    out.uv = vec2<f32>(extra.w, vertex(index).w);
    out.textured = select(0u, flags & (TEXTURED | NEAREST | CUBIC), (flags & TEXTURED) != 0u);
    out.light = light;
    out.i = i;
    out.world = p;
    out.normal = n;
    return out;
}

// A mesh's depth from a light (`shadow_light`: its slot in the view), into the light's shadow map.
override shadow_light: u32 = 0u;

@vertex
fn vs_shadow(@builtin(vertex_index) index: u32, @builtin(instance_index) i: u32) -> @builtin(position) vec4<f32> {
    var p = affine(m1_0_of(i), m1_1_of(i), m1_2_of(i), vertex(index).xyz);
    let base2 = ids_of(i).y;
    if (base2 != NONE) {
        p += affine(m2_0_of(i), m2_1_of(i), m2_2_of(i), vertex(base2 + (index - ids_of(i).x)).xyz);
    }
    return view.lights[shadow_light].shadow * vec4<f32>(p, 1.0);
}

// A mesh's depth as its view sees it, into the view's opaque depth (its ambient occlusion's: `occlusion.rs`).
@vertex
fn vs_depth(@builtin(vertex_index) index: u32, @builtin(instance_index) i: u32) -> @builtin(position) @invariant vec4<f32> {
    return clip(i, index);
}

// A picture's pixel (i, j), its edge held beyond its border.
fn pixel(p: vec2<i32>, size: vec2<i32>) -> vec4<f32> {
    return textureLoad(image, clamp(p, vec2<i32>(0), size - vec2<i32>(1)), 0);
}

// Keys' cubic convolution (a = -1/2): the weights of the pixels at -1, 0, 1, 2 from t.
fn keys(t: f32) -> vec4<f32> {
    let t2 = t * t;
    let t3 = t2 * t;
    return vec4<f32>(
        -0.5 * t3 + t2 - 0.5 * t,
        1.5 * t3 - 2.5 * t2 + 1.0,
        -1.5 * t3 + 2.0 * t2 + 0.5 * t,
        0.5 * t3 - 0.5 * t2,
    );
}

// The picture at uv reconstructed from its pixels (centred at (i + 1/2) / size): the nearest
// pixel, or cubic, clamped to what a premultiplied color can be (the kernel overshoots).
fn reconstructed(uv: vec2<f32>, kernel: u32) -> vec4<f32> {
    let size = vec2<i32>(textureDimensions(image));
    let x = uv * vec2<f32>(size) - vec2<f32>(0.5);
    if ((kernel & NEAREST) != 0u) {
        return pixel(vec2<i32>(floor(x + vec2<f32>(0.5))), size);
    }
    let base = floor(x);
    let wx = keys(x.x - base.x);
    let wy = keys(x.y - base.y);
    let b = vec2<i32>(base);
    var sum = vec4<f32>(0.0);
    for (var j = 0; j < 4; j++) {
        var row = vec4<f32>(0.0);
        for (var i = 0; i < 4; i++) {
            row += wx[i] * pixel(b + vec2<i32>(i - 1, j - 1), size);
        }
        sum += wy[j] * row;
    }
    let a = clamp(sum.a, 0.0, 1.0);
    return vec4<f32>(clamp(sum.rgb, vec3<f32>(0.0), vec3<f32>(a)), a);
}

// A texel lit like a color (premultiplied: its light scaled by its coverage), at the mesh's
// opacity.
fn lit_texel(texel: vec4<f32>, light: f32, opacity: f32) -> vec4<f32> {
    return vec4<f32>(clamp(texel.rgb + light * texel.a, vec3<f32>(0.0), vec3<f32>(texel.a)), texel.a) * opacity;
}

// A mesh's picture at the fragment: textures are premultiplied; an image is reconstructed by its resampling algorithm:
// linear (and a camera's view, a colormap) by the sampler, nearest and cubic here.
fn texel_of(in: Shaded) -> vec4<f32> {
    if ((in.textured & (NEAREST | CUBIC)) != 0u) {
        return reconstructed(in.uv, in.textured);
    }
    return textureSampleLevel(image, image_sampler, in.uv, 0.0); // (one level)
}

// A mesh without a material: its colour; a textured one keeps its pixels (lit, if it is: a surface's colormap) and
// takes only its opacity.
fn unlit(in: Shaded, texel: vec4<f32>) -> vec4<f32> {
    return select(premultiplied(in.color), lit_texel(texel, in.light, in.color.a), in.textured != 0u);
}

fn shaded(in: Shaded) -> vec4<f32> {
    let texel = texel_of(in);
    if ((ids_of(in.i).z & MATERIAL) != 0u) {
        return lit(in, texel);
    }
    return unlit(in, texel);
}

// A mesh with a material: its color (its picture's, where it has one) the base color of a surface lit by the view's
// lights: the light it sends toward the eye, exposed (`light.wgsl`), and its opacity; its roughness widened by how far
// its normal turns across the pixel (`over_pixel`: a highlight's light averaged over the pixel). Where it is opaque, the
// light from all around reaches it as the view's ambient occlusion says (what is seen through is not in the depth that
// is found from). (Its normal's derivatives are taken where it has a material: an instance's, the same for every
// fragment of a triangle, so a pixel quad's fragments, all of one triangle, take them together.)
@diagnostic(off, derivative_uniformity)
fn lit_light(in: Shaded, texel: vec4<f32>) -> vec4<f32> {
    var base = in.color;
    if (in.textured != 0u) {
        base = vec4<f32>(texel.rgb / max(texel.a, 1e-6), texel.a * in.color.a);
    }
    let v = select(view.toward.xyz, normalize(view.eye.xyz - in.world), view.eye.w > 0.5);
    let m = material_of(in.i);
    var ao = 1.0;
    if (view.occlusion.x > 0.0 && base.a >= 1.0 - 1e-5) {
        ao = textureLoad(occlusion, vec2<i32>(in.position.xy), 0).x;
    }
    let n = normalize(in.normal);
    let across = dpdx(n);
    let down = dpdy(n);
    let roughness = over_pixel(m.y, dot(across, across) + dot(down, down));
    let radiance = reflected(linear(base.rgb), m.x, roughness, m.z, n, in.world, v, ao);
    return vec4<f32>(radiance * view.lighting.y, base.a);
}

// A mesh with a material, shown on its own as the view's tone mapping shows light, at the mesh's opacity.
fn lit(in: Shaded, texel: vec4<f32>) -> vec4<f32> {
    let l = lit_light(in, texel);
    return premultiplied(vec4<f32>(toned(l.rgb, u32(view.lighting.z + 0.5)), l.a));
}

@fragment
fn fs_mesh(in: Shaded) -> @location(0) vec4<f32> {
    return shaded(in);
}

// ── a view with lit meshes: its raster base in two targets ────────────────────────────────────

// A fragment as the raster base of a view with lit meshes keeps it: display paint in target 0 (premultiplied, its
// alpha the lit layers' coverage), exposed light in target 1 (premultiplied, its alpha every layer's coverage), each
// fragment its own in its target and nothing in the other, its coverage the alpha of both. The `with_light` pipelines'
// blend states lay it over both (target 0's alpha adds the blend constant's share of it: 1 a lit mesh's, else 0), so a
// pixel's samples average display paint and light apart, and the composite mixes them on (`vector.wgsl`'s `Mix`) and
// shows them as the paint plus the light tone mapped once (`seen`): a camera's integration of what is lit.
struct Base {
    @location(0) paint: vec4<f32>,
    @location(1) light: vec4<f32>,
};

// Display paint (premultiplied).
fn painted(c: vec4<f32>) -> Base {
    return Base(c, vec4<f32>(0.0, 0.0, 0.0, c.a));
}

@fragment
fn fs_mesh_with_light(in: Shaded) -> Base {
    let texel = texel_of(in);
    if ((ids_of(in.i).z & MATERIAL) != 0u) {
        let l = lit_light(in, texel);
        return Base(vec4<f32>(0.0, 0.0, 0.0, l.a), vec4<f32>(min(l.rgb, vec3<f32>(LIGHT_MOST)) * l.a, l.a));
    }
    return painted(unlit(in, texel));
}
