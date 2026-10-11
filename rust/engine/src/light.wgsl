// SPDX-FileCopyrightText: 2026 Academa, Inc.
// SPDX-FileCopyrightText: The Android Open Source Project
// SPDX-License-Identifier: Apache-2.0
// Modified by Academa, Inc.

// Light on a surface with a material (GGX distribution, height-correlated Smith visibility, Schlick Fresnel, Lambert
// diffuse), from a view's lights: the radiance the surface sends toward the eye, which the view's tone mapping shows
// (`tone.wgsl`). A light's intensity is what a white matte surface shows: 1 makes one facing it white (its
// illuminance is π times the intensity; an ambient light's radiance is the intensity, from every direction).

// A light (see `feed.lighting`): where (an ambient light: nowhere; a sun: the unit direction toward it; a point or
// spot: its position; an environment: its picture's +x) and its kind (0 ambient, 1 sun, 2 point, 3 spot, 4
// environment); its color in linear light times its intensity, and how far a point or spot reaches (an environment:
// its cube's roughest level); a spot's axis (where it points; an environment: its picture's up, +z, and the light a 1
// in its cube stands for) and its cone's falloff, scale and offset; then its shadow map's layer (-1: none), a texel's world size (a spot's: at
// unit distance along its axis), whether the map is a perspective one (`shadow.rs`), and where the map sees from
// (clip = shadow · world).
struct Light {
    place: vec4<f32>,
    color: vec4<f32>,
    axis: vec4<f32>,
    cone: vec4<f32>,
    shadow: mat4x4<f32>,
};

const LIGHT_PI: f32 = 3.14159265358979;
const MIN_PERCEPTUAL_ROUGHNESS: f32 = 0.045; // below it, highlights alias and f16 overflows

fn d_ggx(roughness: f32, NoH: f32) -> f32 {
    let one_minus = 1.0 - NoH * NoH;
    let a = NoH * roughness;
    let k = min(roughness / (one_minus + a * a), 453.5);
    return k * k * (1.0 / LIGHT_PI);
}

fn v_smith_ggx_correlated(roughness: f32, NoV: f32, NoL: f32) -> f32 {
    let a2 = roughness * roughness;
    let lambda_v = NoL * sqrt((NoV - a2 * NoV) * NoV + a2);
    let lambda_l = NoV * sqrt((NoL - a2 * NoL) * NoL + a2);
    return 0.5 / max(lambda_v + lambda_l, 0.0000077);
}

fn f_schlick(f0: vec3<f32>, LoH: f32) -> vec3<f32> {
    let f90 = clamp(dot(f0, vec3<f32>(50.0 * 0.33)), 0.0, 1.0); // a surface darker than any real one: no glare
    let x = 1.0 - LoH;
    let x2 = x * x;
    return f0 + (f90 - f0) * (x2 * x2 * x);
}

// The radiance a surface at p, facing n (either side: the one toward v), sends toward v (a unit vector toward the
// eye), lit by the view's lights (`light_count`, `light_at`, `shadowed`, `dfg_at`, `environment_at`, `harmonic`: its
// host's): its base color in linear light, how metallic, how rough (perceptual), how much a dielectric reflects head
// on. The specular lobe keeps the light single scattering loses on a rough surface (energy compensation, from the
// DFG table's albedo of a white conductor, y): a white rough metal under a uniform light shows that light, at any
// roughness. Light from all around (an ambient light, an environment) lights by the split sum: the specular lobe's
// albedo, mix(dfg.x, dfg.y, f0), times the light the lobe gathers (an environment's cube at the roughness's level,
// toward the lobe's dominant direction), and the diffuse part the light the specular lobe does not reflect (1 - its
// albedo). Of that light, `ao` reaches p (its view's ambient occlusion; 1: all of it): the diffuse part takes it as it
// is, the specular lobe as much of it as a lobe that narrow sees (Lagarde and de Rousiers' approximation), each with
// the light that bounces between the surfaces that shut it out (`bounced`).
fn reflected(base: vec3<f32>, metallic: f32, perceptual_roughness: f32, reflectance: f32, normal: vec3<f32>, p: vec3<f32>, v: vec3<f32>, ao: f32) -> vec3<f32> {
    let n = select(normal, -normal, dot(normal, v) < 0.0);
    let perceptual = clamp(perceptual_roughness, MIN_PERCEPTUAL_ROUGHNESS, 1.0);
    let roughness = perceptual * perceptual;
    let diffuse = base * (1.0 - metallic);
    let f0 = base * metallic + vec3<f32>(0.16 * reflectance * reflectance * (1.0 - metallic));
    let NoV = max(dot(n, v), 1e-4);
    let dfg = dfg_at(NoV, perceptual);
    let energy = 1.0 + f0 * (1.0 / max(dfg.y, 1e-4) - 1.0);
    let albedo = mix(vec3<f32>(dfg.x), vec3<f32>(dfg.y), f0);
    var diffuse_ao = vec3<f32>(1.0);
    var specular_ao = vec3<f32>(1.0);
    if (ao < 1.0) {
        diffuse_ao = bounced(ao, diffuse);
        specular_ao = bounced(clamp(pow(NoV + ao, exp2(-16.0 * roughness - 1.0)) - 1.0 + ao, 0.0, 1.0), f0);
    }
    var color = vec3<f32>(0.0);
    for (var i = 0u; i < light_count(); i++) {
        let light = light_at(i);
        let kind = u32(light.place.w + 0.5);
        if (kind == 0u) {
            color += (diffuse * (1.0 - albedo) * diffuse_ao + albedo * energy * specular_ao) * light.color.rgb;
            continue;
        }
        if (kind == 4u) {
            // directions in the environment's axes (x, z: the light's place and axis)
            let axes = mat3x3<f32>(light.place.xyz, cross(light.axis.xyz, light.place.xyz), light.axis.xyz);
            let dominant = mix(reflect(-v, n), n, roughness * roughness);
            let level = light.color.w * perceptual * (2.0 - perceptual);
            let specular = environment_at(dominant * axes, level) * (light.axis.w * albedo * energy);
            color += (diffuse * (1.0 - albedo) * irradiance(n * axes) * diffuse_ao + specular * specular_ao) * light.color.rgb;
            continue;
        }
        var l = light.place.xyz;
        var attenuation = 1.0;
        if (kind >= 2u) {
            let to_light = light.place.xyz - p;
            let d2 = dot(to_light, to_light);
            let f = d2 / max(light.color.w * light.color.w, 1e-8);
            let window = clamp(1.0 - f * f, 0.0, 1.0);
            attenuation = window * window / max(d2, 1e-4);
            l = to_light * inverseSqrt(max(d2, 1e-12));
            if (kind == 3u) {
                let t = clamp(dot(-light.axis.xyz, l) * light.axis.w + light.cone.x, 0.0, 1.0);
                attenuation *= t * t;
            }
        }
        let NoL = dot(n, l);
        if (attenuation <= 0.0 || NoL <= 0.0) {
            continue;
        }
        let h = normalize(v + l);
        let NoH = clamp(dot(n, h), 0.0, 1.0);
        let LoH = clamp(dot(l, h), 0.0, 1.0);
        let specular = d_ggx(roughness, NoH) * v_smith_ggx_correlated(roughness, NoV, NoL) * f_schlick(f0, LoH) * energy;
        let seen = shadowed(light, p, n);
        color += (diffuse * (1.0 / LIGHT_PI) + specular) * (NoL * LIGHT_PI * attenuation * seen) * light.color.rgb;
    }
    return color;
}

// A surface's perceptual roughness widened by how far its normal turns across a pixel (`turn`: the normal's change a
// pixel across and a pixel down, each squared, summed): a highlight narrower than the pixel then shows its light
// averaged over the pixel, not its light at the one point shaded, which a glint misses or hits, by orders of magnitude,
// from frame to frame (normal filtering: Kaplanyan 2016; Tokuyoshi and Kaplanyan 2019; its variance 0.15 and threshold
// 0.2). A flat surface keeps its roughness.
fn over_pixel(perceptual: f32, turn: f32) -> f32 {
    let roughness = perceptual * perceptual;
    let kernel = min(2.0 * 0.15 * turn, 0.2);
    return sqrt(sqrt(clamp(roughness * roughness + kernel, 0.0, 1.0)));
}

// The light from all around that reaches a surface of `albedo` where `visibility` of it is not shut out, with what
// bounces off the surfaces around it (as bright as it: Jimenez et al. 2016's fit), no less than the visibility.
fn bounced(visibility: f32, albedo: vec3<f32>) -> vec3<f32> {
    let a = 2.0404 * albedo - 0.3324;
    let b = -4.7951 * albedo + 0.6417;
    let c = 2.7552 * albedo + 0.6903;
    return max(vec3<f32>(visibility), ((visibility * a + b) * visibility + c) * visibility);
}

// An environment's diffuse light on a surface facing n (in its axes): its nine harmonics' sum (`harmonic`, its host's;
// `environment::harmonics`), no less than none.
fn irradiance(n: vec3<f32>) -> vec3<f32> {
    let first = harmonic(0u) + harmonic(1u) * n.y + harmonic(2u) * n.z + harmonic(3u) * n.x;
    let second = harmonic(4u) * (n.x * n.y) + harmonic(5u) * (n.y * n.z) + harmonic(6u) * (3.0 * n.z * n.z - 1.0) + harmonic(7u) * (n.z * n.x) + harmonic(8u) * (n.x * n.x - n.y * n.y);
    return max(first + second, vec3<f32>(0.0));
}

// How much of a light reaches p, a surface facing n: its shadow map's depth there (its host's `shadow_compare_at`,
// `shadow_texel`) compared with p's, each texel of a 3x3 neighbourhood bilinearly (a soft edge a few texels wide), p
// moved off the surface by a texel and a half along its normal first (no surface shadows itself: acne). Outside the
// map, lit.
fn shadowed(light: Light, p: vec3<f32>, n: vec3<f32>) -> f32 {
    let layer = i32(round(light.cone.y));
    if (layer < 0) {
        return 1.0;
    }
    var texel = light.cone.z;
    if (light.cone.w > 0.5) {
        texel *= max((light.shadow * vec4<f32>(p, 1.0)).w, 0.0);
    }
    let q = light.shadow * vec4<f32>(p + n * (1.5 * texel), 1.0);
    let ndc = q.xyz / q.w;
    let uv = ndc.xy * vec2<f32>(0.5, -0.5) + vec2<f32>(0.5);
    if (q.w <= 0.0 || ndc.z > 1.0 || any(uv < vec2<f32>(0.0)) || any(uv > vec2<f32>(1.0))) {
        return 1.0;
    }
    let step = shadow_texel();
    var seen = 0.0;
    for (var dy = -1; dy <= 1; dy++) {
        for (var dx = -1; dx <= 1; dx++) {
            seen += shadow_compare_at(uv + vec2<f32>(f32(dx), f32(dy)) * step, layer, ndc.z);
        }
    }
    return seen / 9.0;
}

// The most exposed light a view with lit meshes keeps (its raster base's light is half floats: `blend.wgsl`'s `Base`).
const LIGHT_MOST: f32 = 65000.0;
