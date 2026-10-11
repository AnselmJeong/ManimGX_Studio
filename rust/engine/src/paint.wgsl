// Paint, as both pipelines evaluate it (each shader is this file and `tone.wgsl`, then its own; `row_at` is
// theirs): colors mix as every color in ManimGX mixes — OKLab, weighted by opacity (Python's `mix_rgba`,
// the player's) — and a gradient is evenly spaced stops, a tween's rows mixed toward paint 2's.

fn linear(c: vec3<f32>) -> vec3<f32> {
    return select(pow((c + 0.055) / 1.055, vec3<f32>(2.4)), c / 12.92, c <= vec3<f32>(0.04045));
}

fn oklab(c: vec3<f32>) -> vec3<f32> {
    let l = linear(c);
    let lms = vec3<f32>(
        dot(vec3<f32>(0.4122214708, 0.5363325363, 0.0514459929), l),
        dot(vec3<f32>(0.2119034982, 0.6806995451, 0.1073969566), l),
        dot(vec3<f32>(0.0883024619, 0.2817188376, 0.6299787005), l),
    );
    let r = sign(lms) * pow(abs(lms), vec3<f32>(1.0 / 3.0));
    return vec3<f32>(
        dot(vec3<f32>(0.2104542553, 0.7936177850, -0.0040720468), r),
        dot(vec3<f32>(1.9779984951, -2.4285922050, 0.4505937099), r),
        dot(vec3<f32>(0.0259040371, 0.7827717662, -0.8086757660), r),
    );
}

fn srgb(lab: vec3<f32>) -> vec3<f32> {
    let r = vec3<f32>(
        lab.x + 0.3963377774 * lab.y + 0.2158037573 * lab.z,
        lab.x - 0.1055613458 * lab.y - 0.0638541728 * lab.z,
        lab.x - 0.0894841775 * lab.y - 1.2914855480 * lab.z,
    );
    let lms = r * r * r;
    return gamma(vec3<f32>(
        4.0767416621 * lms.x - 3.3077115913 * lms.y + 0.2309699292 * lms.z,
        -1.2684380046 * lms.x + 2.6097574011 * lms.y - 0.3413193965 * lms.z,
        -0.0041960863 * lms.x - 0.7034186147 * lms.y + 1.7076147010 * lms.z,
    ));
}

// Color a -> b at t.
fn mix_rgba(a: vec4<f32>, b: vec4<f32>, t: f32) -> vec4<f32> {
    let wa = a.a * (1.0 - t);
    let wb = b.a * t;
    let opacity = wa + wb;
    let la = oklab(a.rgb);
    let lb = oklab(b.rgb);
    let lab = select(mix(la, lb, t), (la * wa + lb * wb) / max(opacity, 1e-9), opacity > 1e-9);
    return vec4<f32>(srgb(lab), opacity);
}

fn premultiplied(c: vec4<f32>) -> vec4<f32> {
    return vec4<f32>(c.rgb * c.a, c.a);
}

// Row k of a brush: paint 1's, or mixed `m` of the way toward paint 2's row k (a tween's paint).
fn row(first: u32, second: u32, k: u32, m: f32) -> vec4<f32> {
    if (m <= 0.0) {
        return row_at(first + k);
    }
    return mix_rgba(row_at(first + k), row_at(second + k), m);
}

// A gradient of `count` rows at t along its axis (clamped to [0, 1]): its stops evenly spaced.
fn stops(first: u32, second: u32, count: u32, m: f32, t: f32) -> vec4<f32> {
    let x = clamp(t, 0.0, 1.0) * f32(count - 1u);
    let k = min(u32(floor(x)), count - 2u);
    return mix_rgba(row(first, second, k, m), row(first, second, k + 1u, m), x - f32(k));
}
