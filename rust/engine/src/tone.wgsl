// SPDX-FileCopyrightText: 2026 Academa, Inc.
// SPDX-FileCopyrightText: 2021 The Android Open Source Project
// SPDX-License-Identifier: Apache-2.0
// Modified by Academa, Inc.

// How light shows on a display: the radiance a view's lit content sends toward the eye, scaled by the exposure,
// clipped or rolled off by AgX, encoded as sRGB (as every color is: `paint.wgsl`'s are).

// Linear light (0-1) encoded as sRGB.
fn gamma(c: vec3<f32>) -> vec3<f32> {
    let l = clamp(c, vec3<f32>(0.0), vec3<f32>(1.0));
    return select(1.055 * pow(l, vec3<f32>(1.0 / 2.4)) - 0.055, 12.92 * l, l <= vec3<f32>(0.0031308));
}

// AgX (Sobotka's; its matrices Blender's, its curve the iolite engine's minimal AgX): the sRGB scene value into its
// working space (Rec.2020, inset), its log2 over 16.5 stops through a sigmoid, back out (outset), to linear sRGB.
const AGX_IN: mat3x3<f32> = mat3x3<f32>(
    vec3<f32>(0.544904663, 0.140439629, 0.088826896),
    vec3<f32>(0.373779945, 0.754110565, 0.178877349),
    vec3<f32>(0.081385728, 0.105433482, 0.732250240),
);
const AGX_OUT: mat3x3<f32> = mat3x3<f32>(
    vec3<f32>(1.127100582, -0.141329763, -0.141329763),
    vec3<f32>(-0.110606643, 1.157823702, -0.110606643),
    vec3<f32>(-0.016493939, -0.016493939, 1.251936407),
);
const REC2020_TO_SRGB: mat3x3<f32> = mat3x3<f32>(
    vec3<f32>(1.660217713, -0.124553686, -0.018154913),
    vec3<f32>(-0.587557716, 1.132944579, -0.100604647),
    vec3<f32>(-0.072829428, -0.008347784, 1.118831740),
);

fn agx(c: vec3<f32>) -> vec3<f32> {
    var v = max(AGX_IN * max(c, vec3<f32>(0.0)), vec3<f32>(1e-10));
    v = clamp((log2(v) + 12.47393) / (4.026069 + 12.47393), vec3<f32>(0.0), vec3<f32>(1.0));
    let x2 = v * v;
    let x4 = x2 * x2;
    let x6 = x4 * x2;
    v = -17.86 * x6 * v + 78.01 * x6 - 126.7 * x4 * v + 92.06 * x4 - 28.72 * x2 * v + 4.361 * x2 - 0.1718 * v + 0.002857;
    return REC2020_TO_SRGB * pow(max(AGX_OUT * v, vec3<f32>(0.0)), vec3<f32>(2.2));
}

// What exposed light shows as (sRGB-encoded): clipped (tone 0) or rolled off by AgX (1).
fn toned(c: vec3<f32>, tone: u32) -> vec3<f32> {
    return gamma(select(clamp(c, vec3<f32>(0.0), vec3<f32>(1.0)), clamp(agx(c), vec3<f32>(0.0), vec3<f32>(1.0)), tone == 1u));
}
