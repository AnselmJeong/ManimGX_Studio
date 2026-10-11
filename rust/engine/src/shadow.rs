//! Shadows: each sun and spot of a 3D view that casts them draws what casts them (its meshes' depth, then its paths'
//! nearest: `vector.wgsl`'s `fs_nearest`) from where it shines, into a map of `SIZE`² (a layer of an array), fitted
//! to the sphere around the casters and as deep as what their shadows can fall on; a surface with a material compares
//! its depth with the map (`light.wgsl`'s `shadowed`).

/// A map's side, in texels.
pub(crate) const SIZE: u32 = 2048;
/// The most maps a view draws (its first suns and spots that cast shadows).
pub(crate) const MOST: usize = 4;

/// A light's shadow map: the light (its slot in the view), where the map sees from (clip = matrix · world, its
/// columns), a texel's size in world units (a spot's: at unit distance along its axis), whether it sees in
/// perspective, its texels per world unit at the casters, and the unit vector toward the light (as a camera's
/// toward its viewer: the paths' plan seen from it).
pub(crate) struct Shadow {
    pub(crate) light: usize,
    pub(crate) matrix: [[f32; 4]; 4],
    pub(crate) texel: f32,
    pub(crate) perspective: bool,
    pub(crate) unit: f32,
    pub(crate) toward: [f32; 3],
}

type V = [f32; 3];

fn dot(a: V, b: V) -> f32 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

fn cross(a: V, b: V) -> V {
    [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
}

fn unit(a: V) -> V {
    let l = dot(a, a).sqrt().max(1e-12);
    a.map(|x| x / l)
}

/// A frame for looking along `f` (a unit vector): right and up.
fn basis(f: V) -> (V, V) {
    let up = if f[2].abs() < 0.9 { [0.0, 0.0, 1.0] } else { [0.0, 1.0, 0.0] };
    let x = unit(cross(f, up));
    (x, cross(x, f))
}

/// A matrix's columns from its rows.
fn columns(rows: [[f32; 4]; 4]) -> [[f32; 4]; 4] {
    std::array::from_fn(|j| std::array::from_fn(|i| rows[i][j]))
}

/// The maps of a view's `lights` (16 floats each, as `feed.lighting` packs them) that cast shadows, the first
/// `MOST`: each sees the sphere around `casters` (the meshes' box in the world: low, high corners), and as deep as
/// `receivers` (the box of what shadows can fall on: the meshes and the paths with a material) reach behind it.
pub(crate) fn fit(lights: &[f32], count: usize, casters: [V; 2], receivers: [V; 2]) -> Vec<Shadow> {
    let c: V = std::array::from_fn(|k| 0.5 * (casters[0][k] + casters[1][k]));
    let half: V = std::array::from_fn(|k| 0.5 * (casters[1][k] - casters[0][k]));
    let r = dot(half, half).sqrt().max(1e-3) * 1.02;
    // how far the receivers reach along f from a point
    let reach = |f: V, from: V| {
        (0..8).map(|k| dot(f, std::array::from_fn(|i| receivers[k >> i & 1][i] - from[i]))).fold(f32::MIN, f32::max)
    };
    let mut out = Vec::new();
    for light in 0..count.min(lights.len() / 16) {
        let slot = &lights[16 * light..16 * light + 16];
        if slot[13] < 0.5 || out.len() == MOST {
            continue;
        }
        let place: V = [slot[0], slot[1], slot[2]];
        match slot[3].round() as u32 {
            // a sun: an orthographic map along its light, the sphere in its box, from the sphere's near side to
            // its far side or the receivers', whichever is farther. Held still while the casters move (a still
            // shadow keeps its texels: no shimmer): the sphere's radius rounded up to a step of 2^(1/4), its centre
            // moved to a whole texel across the light
            1 => {
                let f = unit(place.map(|x| -x));
                let (x, y) = basis(f);
                let r = 2f32.powf((r.log2() * 4.0).ceil() / 4.0);
                let texel = 2.0 * r / SIZE as f32;
                let (cx, cy) = (dot(x, c), dot(y, c));
                let (dx, dy) = ((cx / texel).round() * texel - cx, (cy / texel).round() * texel - cy);
                let c: V = std::array::from_fn(|k| c[k] + x[k] * dx + y[k] * dy);
                let deep = r + reach(f, c).max(r);
                let rows = [
                    [x[0] / r, x[1] / r, x[2] / r, -dot(x, c) / r],
                    [y[0] / r, y[1] / r, y[2] / r, -dot(y, c) / r],
                    [f[0] / deep, f[1] / deep, f[2] / deep, (r - dot(f, c)) / deep],
                    [0.0, 0.0, 0.0, 1.0],
                ];
                out.push(Shadow { light, matrix: columns(rows), texel: 2.0 * r / SIZE as f32, perspective: false, unit: SIZE as f32 / (2.0 * r), toward: place });
            }
            // a spot: a perspective map from its point along its axis, a little wider than its cone, from the
            // sphere's near side to its far side or the receivers', whichever is farther
            3 => {
                let f = unit([slot[8], slot[9], slot[10]]);
                let (scale, offset) = (slot[11], slot[12]);
                let outer = (-offset / scale.max(1e-6)).clamp(-1.0, 1.0).acos();
                let t = (outer * 1.15 + 0.02).min(1.4).tan();
                let along = dot(f, std::array::from_fn(|k| c[k] - place[k]));
                let far = (along + r).max(reach(f, place));
                let near = (along - r).max(0.01 * r).max(1e-3);
                if far <= near {
                    continue; // nothing in front of it
                }
                let (x, y) = basis(f);
                let (a, b) = (far / (far - near), far * near / (far - near));
                let rows = [
                    [x[0] / t, x[1] / t, x[2] / t, -dot(x, place) / t],
                    [y[0] / t, y[1] / t, y[2] / t, -dot(y, place) / t],
                    [a * f[0], a * f[1], a * f[2], -a * dot(f, place) - b],
                    [f[0], f[1], f[2], -dot(f, place)],
                ];
                out.push(Shadow { light, matrix: columns(rows), texel: 2.0 * t / SIZE as f32, perspective: true, unit: SIZE as f32 / (2.0 * t * along.max(near)), toward: f.map(|x| -x) });
            }
            _ => {}
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn apply(m: &[[f32; 4]; 4], p: V) -> [f32; 4] {
        std::array::from_fn(|i| m[0][i] * p[0] + m[1][i] * p[1] + m[2][i] * p[2] + m[3][i])
    }

    fn light(kind: f32, place: V, axis: V, angle: f32) -> [f32; 16] {
        let (outer, inner) = (angle.cos(), (angle * 0.8).cos());
        let scale = 1.0 / (inner - outer);
        [place[0], place[1], place[2], kind, 1.0, 1.0, 1.0, 20.0, axis[0], axis[1], axis[2], scale, -outer * scale, 1.0, 0.0, 0.0]
    }

    /// A sun's map holds every point of the sphere around the box: in the map's square, at a depth in [0, 1], the
    /// nearer the sun the smaller.
    #[test]
    fn a_sun_sees_the_whole_box() {
        let shadows = fit(&light(1.0, [1.0, 2.0, 3.0], [0.0; 3], 0.0), 1, [[-2.0, -1.0, -0.5], [2.0, 1.0, 0.5]], [[-2.0, -1.0, -0.5], [2.0, 1.0, 0.5]]);
        let m = &shadows[0].matrix;
        for corner in 0..8 {
            let p = [if corner & 1 == 0 { -2.0 } else { 2.0 }, if corner & 2 == 0 { -1.0 } else { 1.0 }, if corner & 4 == 0 { -0.5 } else { 0.5 }];
            let q = apply(m, p);
            assert!(q[0].abs() <= 1.0 && q[1].abs() <= 1.0 && (0.0..=1.0).contains(&q[2]), "{q:?}");
        }
        let toward = unit([1.0, 2.0, 3.0]);
        assert!(apply(m, toward)[2] < apply(m, toward.map(|x| -x))[2]);
    }

    /// A spot's map sees along its axis: the point it shines at is at the map's center, at a depth in [0, 1].
    #[test]
    fn a_spot_looks_along_its_axis() {
        let shadows = fit(&light(3.0, [0.0, 0.0, 4.0], [0.0, 0.0, -1.0], 0.5), 1, [[-1.0, -1.0, -0.1], [1.0, 1.0, 0.1]], [[-1.0, -1.0, -0.1], [1.0, 1.0, 0.1]]);
        let q = apply(&shadows[0].matrix, [0.0, 0.0, 0.0]);
        let ndc = [q[0] / q[3], q[1] / q[3], q[2] / q[3]];
        assert!(ndc[0].abs() < 1e-5 && ndc[1].abs() < 1e-5 && (0.0..=1.0).contains(&ndc[2]), "{ndc:?}");
    }

    /// A map reaches as deep as what shadows fall on: a wide floor far under a small caster is within its depth.
    #[test]
    fn a_map_reaches_the_receivers() {
        let floor = [[-6.0, -6.0, -3.0], [6.0, 6.0, -3.0]];
        let caster = [[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]];
        let sun = fit(&light(1.0, [1.0, 0.0, 1.0], [0.0; 3], 0.0), 1, caster, floor);
        let spot = fit(&light(3.0, [0.0, 0.0, 4.0], [0.0, 0.0, -1.0], 0.5), 1, caster, floor);
        for (s, p) in [(&sun[0], [3.0, 0.0, -3.0]), (&spot[0], [0.0, 0.0, -3.0])] {
            let q = apply(&s.matrix, p);
            assert!((0.0..=1.0).contains(&(q[2] / q[3])), "{q:?}");
        }
    }
}
