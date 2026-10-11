// The frame's changed macroblocks as NV12, packed: only what changed is converted and read back.
// Per macroblock 96 words: luma 16 rows × 16 bytes, then chroma 8 rows × (8 U,V pairs).
// BT.601 over limited range, applied to the sRGB bytes (what the encoder is told).

struct Grid {
    size: vec4<u32>, // macroblocks per row, macroblocks listed, unused, unused
};

@group(0) @binding(0) var frame: texture_2d<f32>;
@group(0) @binding(1) var<storage, read> listed: array<u32>;
@group(0) @binding(2) var<storage, read_write> packed: array<u32>;
@group(0) @binding(3) var<uniform> grid: Grid;

fn luma(c: vec3<f32>) -> u32 {
    return u32(clamp(round(16.0 + dot(c, vec3<f32>(65.481, 128.553, 24.966))), 0.0, 255.0));
}

fn chroma(c: vec3<f32>) -> u32 {
    let u = u32(clamp(round(128.0 + dot(c, vec3<f32>(-37.797, -74.203, 112.0))), 0.0, 255.0));
    let v = u32(clamp(round(128.0 + dot(c, vec3<f32>(112.0, -93.786, -18.214))), 0.0, 255.0));
    return u | (v << 8u);
}

// One invocation: a 4×2 block of pixels (two luma words, one chroma word of two U,V pairs).
@compute @workgroup_size(4, 8)
fn cs_macroblocks(@builtin(workgroup_id) group: vec3<u32>, @builtin(local_invocation_id) local: vec3<u32>) {
    let slot = group.x;
    if (slot >= grid.size.y) {
        return;
    }
    let mb = listed[slot];
    let origin = vec2<i32>(i32((mb % grid.size.x) * 16u + local.x * 4u), i32((mb / grid.size.x) * 16u + local.y * 2u));
    var top = 0u;
    var bottom = 0u;
    var pairs = 0u;
    for (var k = 0; k < 2; k++) {
        var sum = vec3<f32>(0.0);
        for (var dx = 0; dx < 2; dx++) {
            let x = k * 2 + dx;
            let a = textureLoad(frame, origin + vec2<i32>(x, 0), 0).rgb;
            let b = textureLoad(frame, origin + vec2<i32>(x, 1), 0).rgb;
            top |= luma(a) << (8u * u32(x));
            bottom |= luma(b) << (8u * u32(x));
            sum += a + b;
        }
        pairs |= chroma(sum * 0.25) << (16u * u32(k));
    }
    let base = slot * 96u;
    packed[base + local.y * 8u + local.x] = top;
    packed[base + local.y * 8u + 4u + local.x] = bottom;
    packed[base + 64u + local.y * 4u + local.x] = pairs;
}
