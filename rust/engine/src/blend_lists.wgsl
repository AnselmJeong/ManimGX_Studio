// `blend.wgsl`'s see-through lists (where there are storage buffers to append them to): a 3D view's
// see-through fragments, appended per pixel in its raster passes, read by the composite.

@group(0) @binding(7) var<storage, read> sprites: array<vec2<u32>>; // a 3D view's see-through points, far to near: (object, vertex)

// A 3D view's see-through points, six vertices each, in the order `sprites` lists them.
@vertex
fn vs_sprites(@builtin(vertex_index) v: u32) -> Dotted {
    let s = sprites[v / 6u];
    return disk(s.x, s.y, v % 6u);
}

// ── 3D compositing: see-through fragments in depth order, per pixel ────────────────────
//
// A 3D view with see-through layers draws its opaque layers first (depth tested and written).
// Each see-through layer then appends its fragments to a list per pixel: a node per fragment,
// its depth and color at the pixel's center and the samples it covers in front of the opaque
// depth (each tested at its own depth on the fragment's plane). The appends run per sample
// (Metal runs a fragment shader with side effects per sample anyway) and the invocation at a
// fragment's lowest covered sample appends it; a backend that gives each sample only its own
// bit gets a node per sample, the same composite. The view's composite (`vector.wgsl`) lays each
// list's nodes in depth order among its paths and its opaque base: the nodes between two of its
// layers composited sample by sample (a node over the samples it covers), their samples' mean one
// layer. So a pixel shows the depth-ordered composite of every surface on its rays, in any draw
// order: surfaces through surfaces, lines inside a translucent sphere, a cube through a
// translucent floor; exact but where see-through surfaces cross one another inside a pixel
// (ordered there by its center), or where one's edge crosses an opaque edge inside a pixel. One
// object's layer counts once per sample: a stroke's overlapping ribbons as one.
//
// See-through points need no lists to be in depth order: disks facing the camera, sorted far to
// near (`sprites`: among equal depths, the view's order), they composite exactly by blending in
// that order, however many a pixel stacks. Among the view's other see-through layers (its paths',
// its listed fragments') they keep that order by slabs: a pass of the composite's (`vector.wgsl`'s
// `bound`) leaves the depths of each pixel's nearest layers, and a point's fragment counts those
// farther than it. With none, it blends into the base over the opaque samples, as everywhere
// where nothing else is see-through; else into its slab, the pixel's points between two of those
// layers, which the composite lays between them. So a point is never listed, and a pixel's points
// cost the composite a few slabs, however many there are.

struct Node {
    depth: f32,
    color: u32, // straight RGBA8
    key: u32,   // record << 11 | samples covered << 3 | winding sign << 2 | kind (0 mesh, 3 a mesh's edges)
    next: u32,  // the next node + 1 (0: none)
};

@group(2) @binding(0) var<storage, read_write> heads: array<atomic<u32>>;
@group(2) @binding(1) var<storage, read_write> nodes: array<Node>;
@group(2) @binding(2) var<storage, read_write> appended: atomic<u32>;
@group(2) @binding(3) var opaque_depth: SampleDepth;

// Where sample s of n lies from its pixel's center (the standard patterns; others: the center).
fn sample_offset(n: u32, s: u32) -> vec2<f32> {
    if (n == 4u) {
        var four = array<vec2<f32>, 4>(vec2(-2.0, -6.0), vec2(6.0, -2.0), vec2(-6.0, 2.0), vec2(2.0, 6.0));
        return four[s] / 16.0;
    }
    if (n == 8u) {
        var eight = array<vec2<f32>, 8>(vec2(1.0, -3.0), vec2(-1.0, 3.0), vec2(5.0, 1.0), vec2(-3.0, -5.0), vec2(-5.0, 5.0), vec2(-7.0, -1.0), vec2(3.0, 7.0), vec2(7.0, -7.0));
        return eight[s] / 16.0;
    }
    return vec2<f32>(0.0);
}

// A fragment's depth across its pixel (its plane's slopes), taken in uniform control flow.
fn slopes(pos: vec4<f32>) -> vec2<f32> {
    return vec2<f32>(dpdx(pos.z), dpdy(pos.z));
}

// Append a see-through fragment (straight color) over the samples of `mask` it covers in front
// of the opaque depth: once, by the invocation at its lowest covered sample.
fn append(i: u32, pos: vec4<f32>, slope: vec2<f32>, mask: u32, sample: u32, color: vec4<f32>, kind: u32, positive: bool) {
    if (sample != firstTrailingBit(mask) || color.a <= 0.0) {
        return;
    }
    let pixel = vec2<u32>(pos.xy);
    // its depth at the pixel's center (the position may be a sample's)
    let center = pos.z - dot(slope, pos.xy - floor(pos.xy) - vec2<f32>(0.5));
    let n = u32(view.pixels.z);
    var covered = 0u;
    for (var s = 0u; s < n; s += 1u) {
        if ((mask & (1u << s)) != 0u && center + dot(slope, sample_offset(n, s)) > textureLoad(opaque_depth, pixel, s)) {
            covered |= 1u << s;
        }
    }
    if (covered == 0u) {
        return;
    }
    let k = atomicAdd(&appended, 1u);
    if (k >= arrayLength(&nodes)) {
        return; // full: the count tells the player to draw the frame again with more room
    }
    let key = ((ids_of(i).z >> 8u) << 11u) | (covered << 3u) | select(0u, 4u, positive) | kind;
    let next = atomicExchange(&heads[pixel.y * u32(view.pixels.x) + pixel.x], k + 1u);
    nodes[k] = Node(center, pack4x8unorm(color), key, next);
}

fn straight(c: vec4<f32>) -> vec4<f32> {
    return vec4<f32>(c.rgb / max(c.a, 1e-6), c.a);
}

@fragment
fn fs_stroke_append(in: Stroked, @builtin(sample_mask) mask: u32, @builtin(sample_index) sample: u32) {
    append(in.i, in.position, slopes(in.position), mask, sample, in.color, 3u, true);
}

@fragment
fn fs_stroke_gradient_append(in: Stroked, @builtin(sample_mask) mask: u32, @builtin(sample_index) sample: u32) {
    let c = gradient(in.i, brush_of(in.i).z, brush2_of(in.i).y, brush_of(in.i).w, in.t, extra_of(in.i).y);
    append(in.i, in.position, slopes(in.position), mask, sample, c, 3u, true);
}

@fragment
fn fs_mesh_append(in: Shaded, @builtin(sample_mask) mask: u32, @builtin(sample_index) sample: u32) {
    append(in.i, in.position, slopes(in.position), mask, sample, straight(shaded(in)), 0u, true);
}

// ── slabs ─────────────────────────────────────────────────────────────────────

// the depths of each pixel's nearest layers, far to near (`vector.wgsl`'s `bound`)
@group(2) @binding(0) var slab_bounds: texture_2d<f32>;

// The slab a see-through point's fragment blends into: how many of its pixel's nearest layers lie
// farther than it, its depth taken as the composite takes a listed fragment's (`node_layer`:
// pushed back by the bias, so that a layer through it shows).
fn slab_of(in: Dotted) -> u32 {
    let bounds = textureLoad(slab_bounds, vec2<u32>(in.position.xy), 0);
    let z = -in.position.z * (1.0 - view.toward.w);
    return u32(bounds.x > z) + u32(bounds.y > z) + u32(bounds.z > z) + u32(bounds.w > z);
}

// A see-through point with no layer behind it: blended into the base (depth tested), as dotted.
fn in_base(in: Dotted) -> vec4<f32> {
    if (slab_of(in) != 0u) {
        discard;
    }
    return dotted(in);
}

@fragment
fn fs_sprites_base(in: Dotted) -> @location(0) vec4<f32> {
    return in_base(in);
}

@fragment
fn fs_sprites_base_with_light(in: Dotted) -> Base {
    return painted(in_base(in));
}

// The slabs, one target each: slab j's in target j - 1.
struct Slabs {
    @location(0) first: vec4<f32>,
    @location(1) second: vec4<f32>,
    @location(2) third: vec4<f32>,
    @location(3) fourth: vec4<f32>,
};

// A see-through point with layers behind it: blended into its slab, over the share of the pixel's
// samples where it is in front of the opaque depth (as the base's pass tests them, one by one).
@fragment
fn fs_sprites_slabs(in: Dotted) -> Slabs {
    let j = slab_of(in);
    let c = dot_color(in);
    let n = u32(view.pixels.z);
    var front = 0u;
    for (var s = 0u; s < n; s += 1u) {
        front += u32(in.position.z >= textureLoad(opaque_depth, vec2<u32>(in.position.xy), s));
    }
    if (j == 0u || c.a <= 0.0 || front == 0u) {
        discard;
    }
    let p = premultiplied(c) * (f32(front) / f32(n));
    var out = Slabs(vec4<f32>(0.0), vec4<f32>(0.0), vec4<f32>(0.0), vec4<f32>(0.0));
    switch j {
        case 1u: { out.first = p; }
        case 2u: { out.second = p; }
        case 3u: { out.third = p; }
        default: { out.fourth = p; }
    }
    return out;
}
