// SPDX-FileCopyrightText: 2026 Academa, Inc.
// SPDX-FileCopyrightText: The Android Open Source Project
// SPDX-License-Identifier: Apache-2.0
// Modified by Academa, Inc.

// A 3D view's bloom (`bloom.rs`): the glow a lens and a sensor spread around the light they take in, which keeps the
// light: a share of each pixel's light (the view's strength) is spread over the view, the rest stays where it is. The
// share is taken from the light the view shows (its composite's: what lies nearer has hidden the light behind it), at
// half the view's size (`spread`), then halved level by level (`down`), and the levels are added back up from the
// coarsest (`up`), each as much of the glow as any other, so that it falls off about as the square of the distance,
// out to the coarsest level's reach, as a lens's glare does. Each pixel is then shown with the glow over it (`show`).

// The view's glow: the share of its light spread, the share each level spreads (strength / levels), its tone mapping
// (`tone.wgsl`'s `toned`).
struct Glow {
    strength: f32,
    share: f32,
    tone: u32,
    unused: u32,
};

@group(0) @binding(0) var<uniform> params: Glow;
// what a level is made from: the level before (the first's: the view's light), or the coarser levels added up
@group(0) @binding(1) var source: texture_2d<f32>;
@group(0) @binding(2) var bilinear: sampler;      // clamped to the edges
@group(0) @binding(3) var level: texture_storage_2d<rgba16float, write>;
@group(0) @binding(4) var own: texture_2d<f32>;   // a level's own share (`down`'s), which the coarser levels are added to
@group(0) @binding(5) var paint: texture_2d<f32>; // the view's display paint, premultiplied, its alpha how much is lit
@group(0) @binding(6) var light: texture_2d<f32>; // its light (exposed, premultiplied), its alpha how much is covered
@group(0) @binding(7) var glow: texture_2d<f32>;  // the glow, at half the view's size: its levels added up
@group(0) @binding(8) var shown: texture_storage_2d<rgba8unorm, write>;

// `source`'s light a step (x, y) of `t` from uv, bilinearly.
fn tap(uv: vec2<f32>, t: vec2<f32>, x: f32, y: f32) -> vec3<f32> {
    return textureSampleLevel(source, bilinear, uv + t * vec2<f32>(x, y), 0.0).rgb;
}

// Texel `id` of `level` from the level before it (`source`, twice its size): the mean of the 6 x 6 texels around it,
// weighted toward its middle, by 13 bilinear taps (Jimenez's: the four around its centre, half the weight, and four
// overlapping squares of four around them, an eighth each), which keeps the light (each texel of the level before
// counts a quarter in all, as in a 2 x 2 box) and lets little alias where a small light moves across the texels.
fn halved(id: vec2<u32>) -> vec3<f32> {
    let uv = (vec2<f32>(id) + 0.5) / vec2<f32>(textureDimensions(level));
    let t = 1.0 / vec2<f32>(textureDimensions(source));
    let inner = tap(uv, t, -1.0, -1.0) + tap(uv, t, 1.0, -1.0) + tap(uv, t, -1.0, 1.0) + tap(uv, t, 1.0, 1.0);
    let sides = tap(uv, t, 0.0, -2.0) + tap(uv, t, -2.0, 0.0) + tap(uv, t, 2.0, 0.0) + tap(uv, t, 0.0, 2.0);
    let corners = tap(uv, t, -2.0, -2.0) + tap(uv, t, 2.0, -2.0) + tap(uv, t, -2.0, 2.0) + tap(uv, t, 2.0, 2.0);
    return 0.125 * (inner + tap(uv, t, 0.0, 0.0)) + 0.0625 * sides + 0.03125 * corners;
}

// The first level: the share of the view's light each level spreads, at half its size.
@compute @workgroup_size(8, 8)
fn spread(@builtin(global_invocation_id) id: vec3<u32>) {
    if (any(id.xy >= textureDimensions(level))) {
        return;
    }
    textureStore(level, id.xy, vec4<f32>(halved(id.xy) * params.share, 1.0));
}

// Each level after it: the level before, at half its size.
@compute @workgroup_size(8, 8)
fn down(@builtin(global_invocation_id) id: vec3<u32>) {
    if (any(id.xy >= textureDimensions(level))) {
        return;
    }
    textureStore(level, id.xy, vec4<f32>(halved(id.xy), 1.0));
}

// Each level added up, from the coarsest: its own share and the coarser levels' (`source`, half its size), read through
// a tent over the 3 x 3 of its texels around each, which keeps the light.
@compute @workgroup_size(8, 8)
fn up(@builtin(global_invocation_id) id: vec3<u32>) {
    if (any(id.xy >= textureDimensions(level))) {
        return;
    }
    let uv = (vec2<f32>(id.xy) + 0.5) / vec2<f32>(textureDimensions(level));
    let t = 1.0 / vec2<f32>(textureDimensions(level));
    let sides = tap(uv, t, -1.0, 0.0) + tap(uv, t, 1.0, 0.0) + tap(uv, t, 0.0, -1.0) + tap(uv, t, 0.0, 1.0);
    let corners = tap(uv, t, -1.0, -1.0) + tap(uv, t, 1.0, -1.0) + tap(uv, t, -1.0, 1.0) + tap(uv, t, 1.0, 1.0);
    let coarser = (4.0 * tap(uv, t, 0.0, 0.0) + 2.0 * sides + corners) / 16.0;
    textureStore(level, id.xy, vec4<f32>(textureLoad(own, id.xy, 0).rgb + coarser, 1.0));
}

// Each pixel as the view shows it with the glow over it (the composite's `seen`, the glow added): the glow is light,
// over the whole pixel. Where the pixel is lit, it adds to what the glow leaves of the lit surfaces' light, and the two
// are tone mapped once; where it shows display paint (the background, what has no material, what is fixed in the
// frame), the glow is shown by the tone mapping on its own and added to the paint, as a display adds light (white stays
// white); where it shows nothing, the glow is all it shows, as opaque as it is bright.
@compute @workgroup_size(16, 16)
fn show(@builtin(global_invocation_id) id: vec3<u32>) {
    let size = textureDimensions(shown);
    if (any(id.xy >= size)) {
        return;
    }
    let p = textureLoad(paint, id.xy, 0);
    let l = textureLoad(light, id.xy, 0);
    let g = textureSampleLevel(glow, bilinear, (vec2<f32>(id.xy) + 0.5) / vec2<f32>(size), 0.0).rgb;
    let over = toned(g, params.tone);
    let covered = max(l.a, p.a);
    let painted = covered - p.a;
    var c = max(p.rgb, min(p.rgb + over * painted, vec3<f32>(painted))) + over * (1.0 - covered);
    if (p.a > 0.0) {
        c += toned(((1.0 - params.strength) * l.rgb + g * p.a) / p.a, params.tone) * p.a;
    }
    textureStore(shown, id.xy, vec4<f32>(c, covered + max(over.r, max(over.g, over.b)) * (1.0 - covered)));
}
