// An environment's prefilter (`environment.rs`): its picture (RGBE, equirectangular, its up the scene's +z) into a
// cube (`to_cube`), the cube's mips (`halve`), and the cube it lights with, a roughness a level (`prefilter`).

const PI: f32 = 3.14159265358979;

@group(0) @binding(0) var picture: texture_2d<u32>;
@group(0) @binding(1) var level_out: texture_storage_2d_array<rgba16float, write>;
@group(0) @binding(2) var linear: sampler;
// the level's GGX lobe (alpha: perceptual roughness squared), its samples, the source's texels a face, the coarsest
// mip a sample reads; what the picture's light is stored times (`to_cube`: one over the environment's unit, so the
// brightest stays within a half float's range)
struct Params {
    alpha: f32,
    samples: f32,
    texels: f32,
    coarsest: f32,
    scale: f32,
    unused_0: f32,
    unused_1: f32,
    unused_2: f32,
};
@group(0) @binding(3) var<uniform> params: Params;
@group(0) @binding(4) var level_in: texture_2d_array<f32>;
@group(0) @binding(5) var source: texture_cube<f32>;

// A cube face's direction at (u, v) in [-1, 1], v down (wgpu's faces: +x, -x, +y, -y, +z, -z).
fn cube_direction(face: u32, uv: vec2<f32>) -> vec3<f32> {
    let u = uv.x;
    let v = uv.y;
    switch face {
        case 0u: {
            return normalize(vec3<f32>(1.0, -v, -u));
        }
        case 1u: {
            return normalize(vec3<f32>(-1.0, -v, u));
        }
        case 2u: {
            return normalize(vec3<f32>(u, 1.0, v));
        }
        case 3u: {
            return normalize(vec3<f32>(u, -1.0, -v));
        }
        case 4u: {
            return normalize(vec3<f32>(u, -v, 1.0));
        }
        default: {
            return normalize(vec3<f32>(-u, -v, -1.0));
        }
    }
}

// An RGBE pixel's light: its mantissas times 2^(exponent - 136).
fn rgbe(p: vec4<u32>) -> vec3<f32> {
    if (p.w == 0u) {
        return vec3<f32>(0.0);
    }
    return vec3<f32>(p.xyz) * exp2(f32(p.w) - 136.0);
}

// The picture's light in direction d: its pixel there (`environment.rs`'s `direction`, inverted).
fn picture_at(d: vec3<f32>) -> vec3<f32> {
    let size = textureDimensions(picture);
    let u = 0.5 - atan2(d.y, d.x) / (2.0 * PI);
    let v = acos(clamp(d.z, -1.0, 1.0)) / PI;
    let x = min(u32(u * f32(size.x)), size.x - 1u);
    let y = min(u32(v * f32(size.y)), size.y - 1u);
    return rgbe(textureLoad(picture, vec2<u32>(x, y), 0));
}

// The cube's level 0: each texel the picture's light averaged over ACROSS x ACROSS points across it (a texel spans a
// fifth of a degree, a 4096-wide picture's pixel a tenth; fewer points miss or double a small bright light's pixels),
// in the environment's unit.
const ACROSS: u32 = 8u;

@compute @workgroup_size(8, 8, 1)
fn to_cube(@builtin(global_invocation_id) id: vec3<u32>) {
    let side = textureDimensions(level_out).x;
    if (id.x >= side || id.y >= side) {
        return;
    }
    var sum = vec3<f32>(0.0);
    for (var j = 0u; j < ACROSS; j++) {
        for (var i = 0u; i < ACROSS; i++) {
            let at = (vec2<f32>(id.xy) + (vec2<f32>(f32(i), f32(j)) + 0.5) / f32(ACROSS)) / f32(side) * 2.0 - 1.0;
            sum += picture_at(cube_direction(id.z, at));
        }
    }
    textureStore(level_out, id.xy, id.z, vec4<f32>(sum * (params.scale / f32(ACROSS * ACROSS)), 1.0));
}

// A mip: each texel the average of the four under it.
@compute @workgroup_size(8, 8, 1)
fn halve(@builtin(global_invocation_id) id: vec3<u32>) {
    let side = textureDimensions(level_out).x;
    if (id.x >= side || id.y >= side) {
        return;
    }
    let p = id.xy * 2u;
    let sum = textureLoad(level_in, p, id.z, 0) + textureLoad(level_in, p + vec2<u32>(1u, 0u), id.z, 0) + textureLoad(level_in, p + vec2<u32>(0u, 1u), id.z, 0) + textureLoad(level_in, p + vec2<u32>(1u, 1u), id.z, 0);
    textureStore(level_out, id.xy, id.z, sum * 0.25);
}

fn hammersley(i: u32, n: u32) -> vec2<f32> {
    var bits = i;
    bits = (bits << 16u) | (bits >> 16u);
    bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
    bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
    bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
    bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
    return vec2<f32>(f32(i) / f32(n), f32(bits) * 2.3283064365386963e-10);
}

// A level of the cube it lights with: in each direction n (the view along it, n = v = r: the split sum's), the source's
// light averaged over the GGX lobe, cosine weighted: GGX samples of the half vector, each read from the source's mip
// whose texels match the sample's solid angle (+1: Krivanek and Colbert's filtered importance sampling), none coarser
// than `params.coarsest` (a coarser one mixes light from beyond the lobe's reach into the sample).
@compute @workgroup_size(8, 8, 1)
fn prefilter(@builtin(global_invocation_id) id: vec3<u32>) {
    let side = textureDimensions(level_out).x;
    if (id.x >= side || id.y >= side) {
        return;
    }
    let n = cube_direction(id.z, (vec2<f32>(id.xy) + 0.5) / f32(side) * 2.0 - 1.0);
    let samples = u32(params.samples);
    if (samples <= 1u) {
        textureStore(level_out, id.xy, id.z, vec4<f32>(textureSampleLevel(source, linear, n, 0.0).rgb, 1.0));
        return;
    }
    let up = select(vec3<f32>(0.0, 0.0, 1.0), vec3<f32>(1.0, 0.0, 0.0), abs(n.z) > 0.999);
    let t = normalize(cross(up, n));
    let b = cross(n, t);
    let a2 = params.alpha * params.alpha;
    let texel = 4.0 * PI / (6.0 * params.texels);
    var sum = vec3<f32>(0.0);
    var weight = 0.0;
    for (var i = 0u; i < samples; i++) {
        let xi = hammersley(i, samples);
        let phi = 2.0 * PI * xi.x;
        let cos_t = sqrt((1.0 - xi.y) / (1.0 + (a2 - 1.0) * xi.y));
        let sin_t = sqrt(max(1.0 - cos_t * cos_t, 0.0));
        let h = t * (sin_t * cos(phi)) + b * (sin_t * sin(phi)) + n * cos_t;
        let l = 2.0 * dot(n, h) * h - n;
        let nol = dot(n, l);
        if (nol > 0.0) {
            // the sample's density over directions (n = v: D / 4) and its solid angle
            let k = cos_t * cos_t * (a2 - 1.0) + 1.0;
            let d = a2 / (PI * k * k);
            let omega = 4.0 / (f32(samples) * d);
            let lod = clamp(0.5 * log2(omega / texel) + 1.0, 0.0, params.coarsest);
            sum += textureSampleLevel(source, linear, l, lod).rgb * nol;
            weight += nol;
        }
    }
    textureStore(level_out, id.xy, id.z, vec4<f32>(sum / max(weight, 1e-6), 1.0));
}
