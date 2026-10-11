// A 3D view's base depth for the composite: the raster pass's depth, its samples' nearest, as one float a pixel.

@group(0) @binding(0) var depth_in: texture_depth_multisampled_2d;
@group(0) @binding(1) var depth_one: texture_depth_2d;
@group(0) @binding(2) var depth_out: texture_storage_2d<r32float, write>;

// What parts a face's samples from its plane: a share of its depth (rounding, 8 f32 steps; its edges' pull, 16:
// `blend.wgsl`'s PULL; 8 to spare) and its depth slope times a share of a pixel (the rasterizer's snapping of corners
// to half a 1/256 step, one triangle's and its neighbour's; the edges' pull, 4 of them; 2 to spare).
const STROKES: vec2<f32> = vec2<f32>(32.0 * 1.2e-7, 8.0 / 512.0);

// A sample's place in its pixel (the standard patterns: their offsets sum to zero).
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

// The pixel's depth: where its samples lie on one plane (one face covers it, its edges' strokes on it), the plane's at
// the pixel's centre (their mean: the pattern's offsets sum to zero), pushed back by all that parts a face's samples
// from its plane (`STROKES`), so a path on that face meets it however steep the face and wherever its edges are; else
// its nearest sample's (reversed Z: the greatest).
@compute @workgroup_size(16, 16)
fn nearest_of_samples(@builtin(global_invocation_id) gid: vec3<u32>) {
    let size = textureDimensions(depth_in);
    if (gid.x >= size.x || gid.y >= size.y) {
        return;
    }
    let n = textureNumSamples(depth_in);
    var z = array<f32, 8>();
    var nearest = 0.0;
    var mean = 0.0;
    var gradient = vec2<f32>(0.0); // (least squares: the offsets' moments, then their products with the depths)
    var moments = vec3<f32>(0.0);
    for (var s = 0u; s < min(n, 8u); s++) {
        z[s] = textureLoad(depth_in, vec2<i32>(gid.xy), i32(s));
        nearest = max(nearest, z[s]);
        mean += z[s] / f32(n);
        let o = sample_offset(n, s);
        moments += vec3<f32>(o.x * o.x, o.y * o.y, o.x * o.y);
    }
    var flat = n > 1u && n <= 8u;
    if (flat) {
        var b = vec2<f32>(0.0);
        for (var s = 0u; s < n; s++) {
            b += sample_offset(n, s) * (z[s] - mean);
        }
        let det = moments.x * moments.y - moments.z * moments.z;
        gradient = vec2<f32>(b.x * moments.y - b.y * moments.z, b.y * moments.x - b.x * moments.z) / det;
        let tolerance = STROKES.x * nearest + STROKES.y * (abs(gradient.x) + abs(gradient.y));
        for (var s = 0u; s < n; s++) {
            flat = flat && abs(z[s] - mean - dot(gradient, sample_offset(n, s))) <= tolerance;
        }
    }
    let centre = mean - STROKES.x * mean - STROKES.y * (abs(gradient.x) + abs(gradient.y));
    textureStore(depth_out, gid.xy, vec4<f32>(-select(nearest, centre, flat), 0.0, 0.0, 0.0)); // from the far plane, as paths'
}

@compute @workgroup_size(16, 16)
fn single_sample(@builtin(global_invocation_id) gid: vec3<u32>) {
    let size = textureDimensions(depth_one);
    if (gid.x >= size.x || gid.y >= size.y) {
        return;
    }
    textureStore(depth_out, gid.xy, vec4<f32>(-textureLoad(depth_one, vec2<i32>(gid.xy), 0), 0.0, 0.0, 0.0));
}
