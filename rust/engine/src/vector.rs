//! A view's paths, drawn with analytic segment coverage (see `vector.wgsl`): flattened per
//! frame on the GPU to the size they are drawn at through the view's camera (projectively in 3D),
//! their segment areas accumulated into a float atlas and composited per 16×16 tile in depth order
//! (the draw order among equal depths: a 2D view's whole order), each pixel kept as two regions. A
//! 2D view's point clouds and meshes are drawn by the raster pipeline (`blend.wgsl`), each alone in
//! its rectangle of a raster atlas, which the composite lays in its place in the order; a 3D view's
//! are its raster base, z-buffered, which the composite lays at its depth per pixel.
//!
//! A view's objects are composited in groups that fit the atlases, in draw order, each group over
//! what the ones before it made; a pixel two groups share is settled at the seam between them (its
//! two regions merged). Only a view whose objects overflow the atlases has more than one group.

use bytemuck::{Pod, Zeroable};

use super::{Camera, Kind, Mat34, NONE, Paint, ROUND, Record, SQUARE, Shape, Store, compose};

const TILE: u32 = 16;
const ATLAS_WIDTH: u32 = 4096;

/// One object as the shader reads it (432 bytes; see `vector.wgsl`).
#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct Object {
    t1x: [f32; 4],
    t1y: [f32; 4],
    t2x: [f32; 4],
    t2y: [f32; 4],
    t1w: [f32; 4], // rows w of the projective map: pixel = (x, y) / w (a 2D view's: (0, 0, 0, 1) and 0)
    t2w: [f32; 4],
    rect: [f32; 4], // its box: corner (view pixels, y down), size
    atlas: [u32; 4],
    ids: [u32; 4],
    params: [f32; 4],
    dash: [f32; 4],
    scale: [f32; 4],
    /// where it lies in depth, z = a (x - x0) + b (y - y0) + c over view pixels from its reference point (`flags`, zw:
    /// its flat's first path's box's corner, else its own), so c, the depth there, keeps its digits (from the view's
    /// corner a steep plane's terms outweigh its depth by orders, and their f32 sum lost them) (a 2D view's: 0, its
    /// order alone decides), and CE's light added to its gradients
    place: [f32; 4],
    // its strokes' depth per pixel (x: a 3D view's path that is not planar); clipped by the near plane (y); its depth
    // plane's reference point (zw: whole view pixels)
    flags: [u32; 4],
    /// its first fill slot, first stroke slot (of its group's); segments a curve is cut into at most, dash windows a
    /// segment meets at most (1: not dashed)
    slots: [u32; 4],
    pieces: [u32; 4], // records a joint takes, a cap; dash windows a subpath meets at most (1: not dashed)
    paint: Paint,
    material: [f32; 4], // metallic, roughness, reflectance; 1 where its fill is lit by the view's lights
    normal: [f32; 4],   // which way its plane faces in the world (a lit fill's)
    t1z: [f32; 4],      // rows of its depth from the far plane (z - w, clip's): a non-planar path's strokes' is z / w
    t2z: [f32; 4],
    near: [f32; 4],     // a clipped object's shadows on the near plane (`flags`, y): see `plan`
}

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct FrameUniform {
    size: [f32; 4],
    tiles: [u32; 4],
    counts: [u32; 4],
    background: [f32; 4],
    depth: [f32; 4],
    lists: [u32; 4],
    inverse: [[f32; 4]; 4], // clip -> world (columns): a 3D view's
    light: [f32; LIGHT],    // toward the viewer, the eye, lighting, the lights (see `Plan::light`)
}

/// A 3D view's light as its composite reads it (`vector.wgsl`'s `Frame`, from `toward`): the unit vector toward the
/// viewer, where it sees from, how many lights with the exposure and the tone mapping, 8 lights of 32 floats
/// (`light.wgsl`'s `Light`), and its environment's diffuse light (9 vectors).
pub(crate) const LIGHT: usize = 12 + 32 * 8 + 36 + 4;

/// A 3D view's see-through points lie among its pixels' this many nearest layers, a slab between each two (as
/// `vector.wgsl`'s `SLABS`; `blend_lists.wgsl` writes them as targets, all in one pass).
pub(crate) const SLABS: usize = 4;

/// A 3D view's see-through fragments for its composite: its lists (heads, nodes: see `blend.wgsl`), the rows whose
/// heads are this frame's, its samples per pixel, and its raster base's samples (color, depth; with lit meshes, their
/// light: `Out::Color`'s `light`) to lay among them.
pub(crate) struct Listed<'a> {
    pub(crate) heads: &'a wgpu::Buffer,
    pub(crate) nodes: &'a wgpu::Buffer,
    pub(crate) rows: [u32; 2],
    pub(crate) samples: u32,
    pub(crate) colors: &'a wgpu::TextureView,
    pub(crate) depths: &'a wgpu::TextureView,
    pub(crate) lights: Option<&'a wgpu::TextureView>,
}

/// Rectangles packed row by row (a row as tall as its tallest), `width` wide.
#[derive(Clone, Copy)]
struct Shelves {
    width: u32,
    x: u32,
    y: u32,
    row: u32,
}

impl Shelves {
    fn new(width: u32) -> Self {
        Self { width, x: 0, y: 0, row: 0 }
    }

    fn rows(&self) -> u32 {
        self.y + self.row
    }

    /// Where a `w`×`h` rectangle goes (x | y << 16), if the rows stay within `limit`.
    fn place(&mut self, w: u32, h: u32, limit: u32) -> Option<u32> {
        let (mut x, mut y, mut row) = (self.x, self.y, self.row);
        if x + w > self.width {
            (x, y, row) = (0, y + row, 0);
        }
        if y + h > limit || w > self.width {
            return None;
        }
        (self.x, self.y, self.row) = (x + w, y, row.max(h));
        Some(x | (y << 16))
    }
}

/// A point cloud or mesh of a 2D view: record `record`, drawn by the raster pipeline into `rect`
/// of the raster atlas (x, y, width, height), which shows the view from `corner` (pixels, y down).
pub(crate) struct Raster {
    pub(crate) record: usize,
    pub(crate) rect: [u32; 4],
    corner: [f32; 2],
}

/// Consecutive objects of a view whose layers fit the atlases: the tiles each reaches, and the
/// slots of the records their flattening can write (fill, stroke).
pub(crate) struct Group {
    objects: Vec<Object>,
    spans: Vec<[u32; 4]>, // first tile x, y, last tile x, y
    masks: Vec<Option<Vec<u8>>>, // which of those tiles each layer can cover (`tile_masks`; none: all, every layer)
    coverage: Shelves,
    raster: Shelves,
    pub(crate) rasters: Vec<Raster>,
    fills: u32,
    strokes: u32,
}

/// A 2D view, planned: its groups, in draw order.
pub(crate) struct Plan {
    pub(crate) groups: Vec<Group>,
    pub(crate) raster_size: [u32; 2], // the part of the raster atlas its groups draw into
    size: [u32; 2],
    background: [f32; 4],
    bias: f32,              // depth units within which paths lie on one another and on the raster base (a 2D view's: 0)
    inverse: [[f32; 4]; 4], // clip -> world (columns)
    pub(crate) lit: bool,   // whether a path of it is lit (its composite's pipeline: with the light)
    crossings: bool,        // whether its depths can cross (a 3D view's: its composite's second pass)
    pub(crate) light: [f32; LIGHT], // what lights its paths with a material (all 0: none; see `FrameUniform`)
}

impl Plan {
    /// Where a raster is drawn: the view's clip space mapped into its rectangle of the raster
    /// atlas (x ↦ scale·x + bias·w, y alike), and the view's pixels (y up) moved by `shift`.
    pub(crate) fn place(&self, raster: &Raster) -> Place {
        let ([w, h], [aw, ah]) = (self.size.map(|v| v as f32), self.raster_size.map(|v| v as f32));
        let offset = [raster.rect[0] as f32 - raster.corner[0], raster.rect[1] as f32 - raster.corner[1]];
        Place { scale: [w / aw, h / ah], bias: [(w + 2.0 * offset[0]) / aw - 1.0, 1.0 - (h + 2.0 * offset[1]) / ah], shift: [offset[0], ah - h - offset[1]] }
    }
}

/// A raster's map from its view into the raster atlas (see `Plan::place`).
#[derive(Clone, Copy)]
pub(crate) struct Place {
    pub(crate) scale: [f32; 2],
    pub(crate) bias: [f32; 2],
    pub(crate) shift: [f32; 2],
}

/// Pixels per unit of one term (rows x, y, w) of a projective map, in its worst direction, where the whole map
/// (every term's rows added) gives pixel (px, py) and w: the largest singular value of its Jacobian there (the quotient
/// rule; an affine map's: `stretch`).
fn stretch_at(x: &[f32; 4], y: &[f32; 4], w: &[f32; 4], [px, py]: [f32; 2], ww: f32) -> f32 {
    let jx = [0, 1, 2].map(|i| (x[i] - px * w[i]) / ww);
    let jy = [0, 1, 2].map(|i| (y[i] - py * w[i]) / ww);
    stretch(&[jx[0], jx[1], jx[2], 0.0], &[jy[0], jy[1], jy[2], 0.0])
}

/// The inverse of a projection (rows), as the shader takes a matrix (columns); a view that has none (singular), 0.
fn inverse(rows: &super::Mat4) -> [[f32; 4]; 4] {
    let mut a: [[f64; 8]; 4] = std::array::from_fn(|i| std::array::from_fn(|j| if j < 4 { rows[i][j] as f64 } else if j - 4 == i { 1.0 } else { 0.0 }));
    for c in 0..4 {
        let p = (c..4).max_by(|&x, &y| a[x][c].abs().total_cmp(&a[y][c].abs())).expect("a row");
        if a[p][c].abs() < 1e-12 {
            return [[0.0; 4]; 4];
        }
        a.swap(c, p);
        let d = a[c][c];
        a[c] = a[c].map(|x| x / d);
        for r in 0..4 {
            if r != c {
                let f = a[r][c];
                a[r] = std::array::from_fn(|j| a[r][j] - f * a[c][j]);
            }
        }
    }
    std::array::from_fn(|col| std::array::from_fn(|row| a[row][4 + col] as f32))
}

/// The plane z = a x + b y + c nearest to points (x, y, z) (least squares). Points on a line on screen (a straight
/// path, a plane seen edge on) fix only the depth along it: the plane that varies along the line alone (the least-norm
/// one); a single point, a flat plane at its depth.
fn fit_plane(points: &[[f64; 3]]) -> [f64; 3] {
    if points.is_empty() {
        return [0.0; 3];
    }
    let n = points.len() as f64;
    let mean = [0, 1, 2].map(|i| points.iter().map(|p| p[i]).sum::<f64>() / n);
    let (mut sxx, mut sxy, mut syy, mut sxz, mut syz) = (0.0, 0.0, 0.0, 0.0, 0.0);
    for p in points {
        let (x, y, z) = (p[0] - mean[0], p[1] - mean[1], p[2] - mean[2]);
        (sxx, sxy, syy, sxz, syz) = (sxx + x * x, sxy + x * y, syy + y * y, sxz + x * z, syz + y * z);
    }
    let det = sxx * syy - sxy * sxy;
    let (a, b) = if det.abs() > 1e-9 * (sxx * syy).max(1e-30) {
        ((sxz * syy - syz * sxy) / det, (syz * sxx - sxz * sxy) / det)
    } else if sxx + syy > 1e-12 {
        // along the line's direction u (the spread's principal axis, eigenvalue l): z = mean + s (u . (p - mean))
        let l = 0.5 * (sxx + syy) + (0.25 * (sxx - syy) * (sxx - syy) + sxy * sxy).sqrt();
        let (ux, uy) = if sxy.abs() > 1e-12 { (sxy, l - sxx) } else if sxx >= syy { (1.0, 0.0) } else { (0.0, 1.0) };
        let m = (ux * ux + uy * uy).sqrt();
        let (ux, uy) = (ux / m, uy / m);
        let s = (ux * sxz + uy * syz) / (ux * ux * sxx + 2.0 * ux * uy * sxy + uy * uy * syy);
        (s * ux, s * uy)
    } else {
        (0.0, 0.0)
    };
    [a, b, mean[2] - a * mean[0] - b * mean[1]]
}

/// A 3D view's paths' flats: the planes (and lines) they lie in, decided in the world, once a frame, as exactly as
/// their points are known: each path's own plane (its shape's three plane points through its placement, a morph's
/// two terms' summed) joins the first flat that holds all three points within 32 ulps of their magnitude, or starts
/// one. A straight path (its points on a line) joins a plane that holds it; else its stroke lies in the plane of the
/// nearest flat it runs along (parallel to it: a grid line over a floor, its whole width over the floor); else it
/// faces the camera, as a line of its own. The paths of a flat share its depth over the view, the same numbers (so
/// where they meet their draw order decides, as in a 2D view), whatever the camera; other paths compare depths alone.
#[derive(Default)]
struct Flats {
    of: std::collections::HashMap<usize, usize>, // record -> its flat
    points: Vec<[[f64; 3]; 3]>,                  // each flat's: three points of its plane in the world (a line's: on it)
}

/// Place plane witnesses without rounding their basis into a different plane. In-plane
/// principal axes may rotate freely when their spreads coincide; only the plane matters.
fn world_plane(a: &Shape, b: Option<&Shape>, record: &Record) -> [[f64; 3]; 3] {
    let at = |m: &Mat34, p: [f64; 3], translate: bool| [0, 1, 2].map(|k| m[k][0] as f64 * p[0] + m[k][1] as f64 * p[1] + m[k][2] as f64 * p[2] + if translate { m[k][3] as f64 } else { 0.0 });
    std::array::from_fn(|i| {
        let first = at(&record.m1, a.plane[i], true);
        let second = b.map_or([0.0; 3], |b| at(&record.m2, b.plane[i], false));
        [0, 1, 2].map(|k| first[k] + second[k])
    })
}

#[cfg(test)]
mod plane_precision {
    use super::*;

    #[test]
    fn a_planes_projection_does_not_depend_on_its_principal_axes() {
        // Equal in-plane spreads have no preferred eigenbasis. Tiny changes can rotate
        // the witnesses by a large angle, but must not rotate or translate their plane.
        for perturbation in [-f64::EPSILON, 0.0, f64::EPSILON] {
            let mut points = [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]];
            points[0][0] += perturbation;
            let mut store = Store::default();
            store.add_path(1, &points, &[[0, 1, 1, 0]], [0.0; 3], [0.0, 0.0, 1.0]);
            let shape = store.shapes.get(&1).unwrap();
            for offset in [0.0f32, 100.0, 100_000.0] {
                let m = [[0.81, 0.24, 0.55, offset], [0.44, 0.93, -0.14, -offset], [0.37, -0.62, 0.89, offset]];
                let record = Record::filled(1, 1, m, [1.0; 4]);
                let placed = world_plane(shape, None, &record);
                let actual = fit_plane(&placed);
                let m = m.map(|row| row.map(f64::from));
                let determinant = m[0][0] * m[1][1] - m[0][1] * m[1][0];
                let a = (m[2][0] * m[1][1] - m[2][1] * m[1][0]) / determinant;
                let b = (m[0][0] * m[2][1] - m[0][1] * m[2][0]) / determinant;
                // Evaluate the fitted plane where the shape actually lies. Intercepts
                // alone are ill-conditioned for a plane translated far from the origin.
                for x in [-1.0, 0.0, 1.0] {
                    for y in [-1.0, 0.0, 1.0] {
                        let wanted = m[2][3] + a * x + b * y;
                        let found = actual[0] * (m[0][3] + x) + actual[1] * (m[1][3] + y) + actual[2];
                        assert!((wanted - found).abs() <= 8.0 * f64::EPSILON * (1.0 + offset as f64), "{perturbation} {offset}: {wanted} != {found}");
                    }
                }
            }
        }
    }
}

fn flats(store: &Store, records: &[Record], order: &[usize]) -> Flats {
    type P = [f64; 3];
    let sub = |a: P, b: P| -> P { [a[0] - b[0], a[1] - b[1], a[2] - b[2]] };
    let add = |a: P, b: P| -> P { [a[0] + b[0], a[1] + b[1], a[2] + b[2]] };
    let dot = |a: P, b: P| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    let cross = |a: P, b: P| -> P { [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]] };
    let unit = |a: P| -> P {
        let l = dot(a, a).sqrt();
        if l > 0.0 { a.map(|x| x / l) } else { [1.0, 0.0, 0.0] }
    };
    // a flat: a point of it, a unit vector (a plane's normal, a line's direction), whether it is a line
    let mut known: Vec<(P, P, bool)> = Vec::new();
    let mut lines: Vec<(usize, [P; 3], f64)> = Vec::new();
    let mut out = Flats::default();
    let near = |points: &[P; 3], scale: f64, (o, u, line): (P, P, bool)| {
        let tol = 32.0 * f32::EPSILON as f64 * scale;
        points.iter().all(|&p| {
            let d = sub(p, o);
            if line {
                let c = cross(d, u);
                dot(c, c) <= tol * tol
            } else {
                dot(d, u).abs() <= tol
            }
        })
    };
    for &k in order {
        let r = &records[k];
        let Some(a) = store.shapes.get(&r.key1).filter(|s| s.kind == Kind::Path) else { continue };
        if r.flags & super::OVERLAY != 0 {
            continue; // in the frame, not the scene
        }
        let b = if r.key2 == 0 { None } else { store.shapes.get(&r.key2) };
        let points = world_plane(a, b, r);
        let scale = points.iter().flat_map(|p| p.iter()).fold(1.0f64, |m, x| m.max(x.abs()));
        let (u, v) = (sub(points[1], points[0]), sub(points[2], points[0]));
        let n = cross(u, v);
        let span = dot(u, u).max(dot(v, v));
        if dot(n, n) <= (64.0 * f32::EPSILON as f64).powi(2) * span * span {
            lines.push((k, points, scale)); // a line: placed once every plane is known
            continue;
        }
        let f = known.iter().position(|&flat| !flat.2 && near(&points, scale, flat)).unwrap_or_else(|| {
            known.push((points[0], unit(n), false));
            out.points.push(points);
            known.len() - 1
        });
        out.of.insert(k, f);
    }
    let planes = known.len();
    for (k, points, scale) in lines {
        let along = {
            let (u, v) = (sub(points[1], points[0]), sub(points[2], points[0]));
            unit(if dot(u, u) >= dot(v, v) { u } else { v })
        };
        let f = known.iter().position(|&flat| near(&points, scale, flat)).unwrap_or_else(|| {
            // the nearest plane it runs along gives its stroke's plane: through it, parallel to that plane
            let parallel = known[..planes].iter().filter(|(_, n, _)| dot(along, *n).abs() <= 1e-5).min_by(|(o, n, _), (p, m, _)| dot(sub(points[0], *o), *n).abs().total_cmp(&dot(sub(points[0], *p), *m).abs()));
            match parallel {
                Some(&(_, n, _)) => {
                    known.push((points[0], unit(n), false));
                    out.points.push([points[0], add(points[0], along), add(points[0], cross(n, along))]);
                }
                None => {
                    known.push((points[0], along, true));
                    out.points.push([points[0], add(points[0], along), add(points[0], along.map(|x| 2.0 * x))]);
                }
            }
            known.len() - 1
        });
        out.of.insert(k, f);
    }
    out
}

/// The largest singular value of a 2×3 map's linear part: pixels per unit in its worst direction.
fn stretch(x: &[f32; 4], y: &[f32; 4]) -> f32 {
    let (a, b, c) = (x[0] * x[0] + x[1] * x[1] + x[2] * x[2], x[0] * y[0] + x[1] * y[1] + x[2] * y[2], y[0] * y[0] + y[1] * y[1] + y[2] * y[2]);
    let m = 0.5 * (a + c);
    (m + (0.25 * (a - c) * (a - c) + b * b).sqrt()).sqrt()
}

/// The triangles of a round piece's fan over half a turn at radius `half` (pixels): its chords
/// within 1/32 px of the arc, as the shader's `fan` (one more for its rounding).
fn fan(half: f32) -> u32 {
    let step = 2.0 * (1.0 - 0.03125 / half).max(-1.0).acos();
    (std::f32::consts::PI / step).ceil().clamp(1.0, 128.0) as u32 + 1
}

/// The tiles (first x, y, last x, y) a box of view pixels reaches.
fn span([x0, y0, x1, y1]: [f32; 4], [tx, ty]: [u32; 2]) -> [u32; 4] {
    let last = |v: f32, tiles: u32| (((v as u32).max(1) - 1) / TILE).min(tiles - 1);
    [x0 as u32 / TILE, y0 as u32 / TILE, last(x1, tx), last(y1, ty)]
}

/// Each tile's list of a group's objects (a counting sort), farthest first by their depth at the tile's center, in
/// draw order among equals (a 2D view's: its draw order), the order the composite expects (and checks): each tile's
/// first entry (and one past the end), then the entries: an object's index, and in its top byte which of its layers
/// can cover the tile (`tile_masks`; a tile none can is not listed).
fn tile_lists(spans: &[[u32; 4]], masks: &[Option<Vec<u8>>], objects: &[Object], tiles_x: u32, tiles: usize) -> Vec<u32> {
    // an object's mask at tile (tx, ty) of its span: its own, or (unclassified) every layer it shows
    let mask = |index: usize, tx: u32, ty: u32| -> u8 {
        let [x0, y0, x1, _] = spans[index];
        match &masks[index] {
            Some(m) => m[((ty - y0) * (x1 - x0 + 1) + (tx - x0)) as usize],
            None => {
                let atlas = objects[index].atlas;
                if atlas[3] != NONE { 1 } else { [1u8, 4, 8].iter().zip(atlas).filter(|(_, at)| *at != NONE).fold(0, |m, (bit, _)| m | bit) }
            }
        }
    };
    let mut starts = vec![0u32; tiles + 1];
    for (index, &[x0, y0, x1, y1]) in spans.iter().enumerate() {
        for ty in y0..=y1 {
            for tx in x0..=x1 {
                if mask(index, tx, ty) != 0 {
                    starts[(ty * tiles_x + tx) as usize + 1] += 1;
                }
            }
        }
    }
    for i in 0..tiles {
        starts[i + 1] += starts[i];
    }
    let mut at = starts.clone();
    let mut entries = vec![0u32; starts[tiles] as usize];
    for (index, &[x0, y0, x1, y1]) in spans.iter().enumerate() {
        for ty in y0..=y1 {
            for tx in x0..=x1 {
                let m = mask(index, tx, ty);
                if m != 0 {
                    let slot = &mut at[(ty * tiles_x + tx) as usize];
                    entries[*slot as usize] = index as u32 | (m as u32) << 24;
                    *slot += 1;
                }
            }
        }
    }
    for t in 0..tiles {
        let list = &mut entries[starts[t] as usize..starts[t + 1] as usize];
        if list.len() > 1 {
            let [cx, cy] = [(t as u32 % tiles_x) as f32 + 0.5, (t as u32 / tiles_x) as f32 + 0.5].map(|c| c * TILE as f32);
            let depth = |e: &u32| {
                let o = &objects[(*e & 0xff_ffff) as usize];
                o.place[0] * (cx - o.flags[2] as f32) + o.place[1] * (cy - o.flags[3] as f32) + o.place[2]
            };
            list.sort_by(|i, j| depth(j).total_cmp(&depth(i)));
        }
    }
    starts.extend(entries);
    starts
}

/// The boxes classified tile by tile: more tiles than this (else every tile, as a small box mostly is).
const BOXED: u32 = 16;

/// Which tiles of an object's box (`span`) each of its shown layers can cover, a byte a tile, row by row: its fill
/// where the fill's edges run (1) and inside them (2), its stroke where it runs (4), its background stroke (8). Its
/// curves run within their control points' hulls (seen through its projective map, whose weights are positive in
/// front of the camera), so a tile meets a layer only within the box of a curve's projected control points grown by
/// how far the layer reaches past the path (`reach`, in pixels); elsewhere a fill winds as its control polygon does
/// (the curves and the polygon differ only inside the hulls): a tile's centre wound around is inside. None: every
/// tile (a box of at most `BOXED` tiles).
fn tile_masks(store: &Store, a: &super::Shape, b: Option<&super::Shape>, rows: &[[f32; 4]; 6], span: [u32; 4], layers: [bool; 3], reach: [f32; 3]) -> Option<Vec<u8>> {
    let [tx0, ty0, tx1, ty1] = span;
    let (columns, lines) = (tx1 - tx0 + 1, ty1 - ty0 + 1);
    if columns * lines <= BOXED {
        return None;
    }
    let [t1x, t1y, t1w, t2x, t2y, t2w] = rows;
    let row = |t: &[f32; 4], p: [f32; 4]| t[0] * p[0] + t[1] * p[1] + t[2] * p[2] + t[3];
    // control point k of curve i, on the view: homogeneous (x, y, w), and divided
    let lift = |i: u32, k: u32| -> [f32; 3] {
        let p = store.ctrl[(4 * (a.curves.first + i) + k) as usize];
        let q = b.map_or([0.0; 4], |b| store.ctrl[(4 * (b.curves.first + i) + k) as usize]);
        [row(t1x, p) + row(t2x, q), row(t1y, p) + row(t2y, q), row(t1w, p) + row(t2w, q)]
    };
    let seen = |i: u32, k: u32| -> [f32; 2] {
        let h = lift(i, k);
        [h[0] / h[2], h[1] / h[2]]
    };
    let mut masks = vec![0u8; (columns * lines) as usize];
    let tile = TILE as f32;
    // each subpath's curves, in pieces (`split`), mark the tiles their pieces' boxes meet, grown by each layer's reach;
    // the pieces' ends make the subpath's outline, which keeps to its curves within the marked tiles (a piece lies in
    // its box, with its chord), closed by the subpath's return to its first point: the fill's edge too, marked for the
    // fill (whether or not the subpath closes itself: a fill closes it, a stroke does not)
    let mut edges: Vec<([f32; 2], [f32; 2])> = Vec::new();
    let mut pieces: Vec<[[f32; 3]; 4]> = Vec::new();
    let subpaths = (0..a.curves.subpaths).map(|s| store.ranges[(a.curves.first_subpath + s) as usize]).map(|r| (r[0], r[1]));
    let all = if a.curves.subpaths == 0 { vec![(0, a.curves.count)] } else { subpaths.collect() };
    for (first, end) in all {
        if end <= first {
            continue;
        }
        let start = seen(first, 0);
        let mut at = start;
        let mut walk = |h: [[f32; 3]; 4], shown: [bool; 3], masks: &mut [u8], at: &mut [f32; 2]| {
            pieces.clear();
            split(h, 0, tile, &mut pieces);
            for piece in &pieces {
                let points = piece.map(|p| [p[0] / p[2], p[1] / p[2]]);
                let (lo, hi) = points.iter().fold(([f32::MAX; 2], [f32::MIN; 2]), |(lo, hi), p| ([lo[0].min(p[0]), lo[1].min(p[1])], [hi[0].max(p[0]), hi[1].max(p[1])]));
                mark(masks, span, columns, (lo, hi), [0, 1, 2].map(|l| layers[l] && shown[l]), reach);
                edges.push((*at, points[3]));
                *at = points[3];
            }
        };
        for i in first..end {
            walk([0, 1, 2, 3].map(|k| lift(i, k)), [true; 3], &mut masks, &mut at);
        }
        if layers[0] && at != start {
            let (q, r) = (lift(end - 1, 3), lift(first, 0));
            let third = |t: f32| [0, 1, 2].map(|n| q[n] + (r[n] - q[n]) * t);
            walk([q, third(1.0 / 3.0), third(2.0 / 3.0), r], [true, false, false], &mut masks, &mut at);
        }
    }
    if layers[0] {
        // inside the fill: where its outlines wind around a tile's centre (a tile no piece's box meets lies off every
        // piece, where the curves wind as their outlines do)
        for ty in ty0..=ty1 {
            let cy = (ty as f32 + 0.5) * tile;
            let mut crossings: Vec<(f32, i32)> = edges
                .iter()
                .filter(|(p, q)| (p[1] <= cy) != (q[1] <= cy))
                .map(|(p, q)| (p[0] + (cy - p[1]) / (q[1] - p[1]) * (q[0] - p[0]), if q[1] > p[1] { 1 } else { -1 }))
                .collect();
            crossings.sort_by(|a, b| a.0.total_cmp(&b.0));
            for tx in tx0..=tx1 {
                let m = &mut masks[((ty - ty0) * columns + (tx - tx0)) as usize];
                if *m & 1 != 0 {
                    continue;
                }
                let cx = (tx as f32 + 0.5) * tile;
                let winding: i32 = crossings.iter().filter(|(x, _)| *x > cx).map(|(_, s)| s).sum();
                if winding != 0 {
                    *m |= 2;
                }
            }
        }
    }
    Some(masks)
}

/// A piece of a curve (its homogeneous control points), halved while its box is wide both ways (de Casteljau, exact
/// for the projected curve: its homogeneous control points are a polynomial's), so that a long straight or gently curved
/// run marks a band of tiles, not its whole box: its pieces, in order, into `out`.
fn split(h: [[f32; 3]; 4], depth: u32, tile: f32, out: &mut Vec<[[f32; 3]; 4]>) {
    let points = h.map(|p| [p[0] / p[2], p[1] / p[2]]);
    let (lo, hi) = points.iter().fold(([f32::MAX; 2], [f32::MIN; 2]), |(lo, hi), p| ([lo[0].min(p[0]), lo[1].min(p[1])], [hi[0].max(p[0]), hi[1].max(p[1])]));
    if depth < 10 && hi[0] - lo[0] > 2.0 * tile && hi[1] - lo[1] > 2.0 * tile {
        let mid = |a: [f32; 3], b: [f32; 3]| [0, 1, 2].map(|n| 0.5 * (a[n] + b[n]));
        let (p01, p12, p23) = (mid(h[0], h[1]), mid(h[1], h[2]), mid(h[2], h[3]));
        let (p012, p123) = (mid(p01, p12), mid(p12, p23));
        let centre = mid(p012, p123);
        split([h[0], p01, p012, centre], depth + 1, tile, out);
        split([centre, p123, p23, h[3]], depth + 1, tile, out);
        return;
    }
    out.push(h);
}

/// The tiles of a box of tiles (`span`, `columns` across) that a box in view pixels (`lo`, `hi`) meets, grown by each
/// shown layer's reach, marked as that layer's edges (its bit).
fn mark(masks: &mut [u8], span: [u32; 4], columns: u32, (lo, hi): ([f32; 2], [f32; 2]), shown: [bool; 3], reach: [f32; 3]) {
    let [tx0, ty0, tx1, ty1] = span;
    let tile = TILE as f32;
    for (layer, (&shown, &grow)) in shown.iter().zip(&reach).enumerate() {
        if !shown {
            continue;
        }
        let bit = [1u8, 4, 8][layer];
        let x0 = (((lo[0] - grow) / tile).floor().max(tx0 as f32) as u32).min(tx1 + 1);
        let x1 = (((hi[0] + grow) / tile).floor().min(tx1 as f32).max(-1.0)) as i64;
        let y0 = (((lo[1] - grow) / tile).floor().max(ty0 as f32) as u32).min(ty1 + 1);
        let y1 = (((hi[1] + grow) / tile).floor().min(ty1 as f32).max(-1.0)) as i64;
        for ty in y0 as i64..=y1 {
            for tx in x0 as i64..=x1 {
                masks[((ty as u32 - ty0) * columns + (tx as u32 - tx0)) as usize] |= bit;
            }
        }
    }
}

/// Place something in the last group or, where it does not fit, in a new one.
fn fit<T>(groups: &mut Vec<Group>, fresh: impl Fn() -> Group, mut place: impl FnMut(&mut Group) -> Option<T>) -> Result<T, String> {
    if let Some(at) = place(groups.last_mut().expect("a group")) {
        return Ok(at);
    }
    groups.push(fresh());
    place(groups.last_mut().expect("a group")).ok_or_else(|| "an object does not fit an empty atlas".into())
}

/// A new texture's view (which keeps it).
fn image(device: &wgpu::Device, label: &str, [width, height]: [u32; 2], format: wgpu::TextureFormat, usage: wgpu::TextureUsages) -> wgpu::TextureView {
    let texture = device.create_texture(&wgpu::TextureDescriptor {
        label: Some(label),
        size: wgpu::Extent3d { width, height, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage,
        view_formats: &[],
    });
    texture.create_view(&Default::default())
}

fn buffer(device: &wgpu::Device, label: &str, size: u64, usage: wgpu::BufferUsages) -> wgpu::Buffer {
    device.create_buffer(&wgpu::BufferDescriptor { label: Some(label), size, usage, mapped_at_creation: false })
}

/// An array the passes read: a storage buffer, and the bytes it has room for.
struct Data(wgpu::Buffer, u64);

impl Data {
    fn new(device: &wgpu::Device, label: &str) -> Self {
        Self(buffer(device, label, 4096, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST), 4096)
    }

    /// `bytes`, written from its start (made anew, with room for them, where it has less).
    fn hold(&mut self, device: &wgpu::Device, queue: &wgpu::Queue, label: &str, bytes: &[u8]) {
        if self.1 < bytes.len() as u64 {
            self.1 = (bytes.len() as u64).next_power_of_two();
            self.0 = buffer(device, label, self.1, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST);
        }
        queue.write_buffer(&self.0, 0, bytes);
    }
}

/// A group's buffers: every group drawn in a frame has its own (all are written before any is
/// drawn).
struct GroupBuffers {
    uniform: wgpu::Buffer,
    objects: Data,
    tiles: Data,
}

/// The GPU's path coverage and view composition: its pipelines, and what they draw with.
pub(crate) struct Vector {
    limit: u32, // the largest texture side
    shader: wgpu::ShaderModule,
    single_shader: Option<wgpu::ShaderModule>, // the same composite with single-sample textures
    write_layout: wgpu::BindGroupLayout,
    flatten: [Option<wgpu::ComputePipeline>; 2], // independent fill and stroke records, made when needed
    composite: [Option<[wgpu::ComputePipeline; 2]>; 32], // by what a view lays (`LIT`, ...): the composite, `keep`; made when first needed
    crossing: [Option<[wgpu::ComputePipeline; 2]>; 32], // where depths cross: the count, the pixels (alike)
    crossings: (wgpu::Buffer, wgpu::Buffer, u64),      // their list, the second pass's workgroups; pixels it holds
    groups_layout: wgpu::BindGroupLayout,              // the workgroups, as the count writes them
    records: Option<(wgpu::Buffer, wgpu::Buffer, [u32; 2])>, // fill, stroke records' slots; how many they hold
    depth_layouts: [wgpu::BindGroupLayout; 2], // a 3D view's base depth from its raster depth: multisampled, single
    depth_resolve: [wgpu::ComputePipeline; 2],
    nothing: wgpu::Buffer,                      // a view's lists when it has none (and strokes' depths)
    stroke_depths: Option<(wgpu::Buffer, u64)>, // a non-planar path's strokes' depths, per pixel of the atlas
    no_samples: [[wgpu::TextureView; 2]; 2],         // its base's samples when it has none (color, depth)
    nearest: Option<(wgpu::BindGroupLayout, [wgpu::RenderPipeline; 2])>, // a light's map, a view's opaque depth, from its paths (made when first needed)
    bounds: Option<([wgpu::BindGroupLayout; 2], wgpu::ComputePipeline)>, // a 3D view's slab bounds: what they read, where they go (made when first needed)
    no_slabs: wgpu::TextureView, // a view's slabs when it has none: 1x1, one layer
    scene_layout: wgpu::BindGroupLayout,
    image_layout: [wgpu::BindGroupLayout; 2],
    read_layout: wgpu::BindGroupLayout,
    fill: wgpu::RenderPipeline,
    stroke: wgpu::RenderPipeline,
    groups: Vec<GroupBuffers>,
    used: usize, // groups drawn this frame
    atlas: Option<(wgpu::TextureView, [u32; 2])>,
    rows: u32, // the atlas rows this frame's plans have needed most
    scratch: Option<(wgpu::TextureView, [u32; 2])>, // where an overflowing view's groups alternate with its canvas
    carried: Option<([wgpu::TextureView; 2], [u32; 2])>, // and, a view with lit content, their light (in turn)
    no_light_out: wgpu::TextureView,                     // where a group that shows its pixels leaves no light: 1x1
    empty: wgpu::TextureView,
    base_depth: Option<(wgpu::TextureView, [u32; 2])>, // one float a pixel: its samples' nearest
    base: Option<(wgpu::TextureView, [u32; 2])>,       // its colour, which the raster passes resolve into
    base_light: Option<(wgpu::TextureView, [u32; 2])>, // with lit meshes: their light, beside it
    far: wgpu::TextureView,                            // a 2D view's base depth: 1x1, far
}

impl Vector {
    fn shader(device: &wgpu::Device, multisampled: bool) -> wgpu::ShaderModule {
        super::sampled_shader(device, "vector", &[include_str!("vector.wgsl"), include_str!("light.wgsl"), include_str!("vector_buffers.wgsl"), include_str!("vector_compute.wgsl")].concat(), multisampled)
    }

    pub(crate) fn new(device: &wgpu::Device, queue: &wgpu::Queue) -> Self {
        let limits = device.limits();
        let shader = Self::shader(device, true);
        let (vertex, fragment, compute) = (wgpu::ShaderStages::VERTEX, wgpu::ShaderStages::FRAGMENT, wgpu::ShaderStages::COMPUTE);
        // where the composite runs, and the accumulate pass
        let (composing, all) = (compute, wgpu::ShaderStages::VERTEX_FRAGMENT | compute);
        let entry = |binding, visibility, ty| wgpu::BindGroupLayoutEntry { binding, visibility, ty: wgpu::BindingType::Buffer { ty, has_dynamic_offset: false, min_binding_size: None }, count: None };
        let (read, rw) = (wgpu::BufferBindingType::Storage { read_only: true }, wgpu::BufferBindingType::Storage { read_only: false });
        let layout = |label, entries: &[wgpu::BindGroupLayoutEntry]| device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries });
        let scene_layout = layout("vector scene", &[entry(0, all, wgpu::BufferBindingType::Uniform), entry(1, all, read), entry(2, all, read), entry(3, all, read), entry(4, all, read), entry(5, all, read)]);
        let texture = |binding| wgpu::BindGroupLayoutEntry { binding, visibility: composing, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }, count: None };
        let sampled = |binding, sample_type, multisampled| wgpu::BindGroupLayoutEntry { binding, visibility: compute, ty: wgpu::BindingType::Texture { sample_type, view_dimension: wgpu::TextureViewDimension::D2, multisampled }, count: None };
        let target = |format| wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format, view_dimension: wgpu::TextureViewDimension::D2 };
        // what its paths with a material are lit with: a 3D view's lights' shadow maps and their comparison, the DFG
        // table and its bilinear reads, its environment's cube, its ambient occlusion
        let maps = wgpu::BindGroupLayoutEntry { binding: 10, visibility: composing, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Depth, view_dimension: wgpu::TextureViewDimension::D2Array, multisampled: false }, count: None };
        let compare = wgpu::BindGroupLayoutEntry { binding: 11, visibility: composing, ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Comparison), count: None };
        let dfg = wgpu::BindGroupLayoutEntry { binding: 12, visibility: composing, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }, count: None };
        let linear = wgpu::BindGroupLayoutEntry { binding: 13, visibility: composing, ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering), count: None };
        let cube = wgpu::BindGroupLayoutEntry { binding: 15, visibility: composing, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::Cube, multisampled: false }, count: None };
        // and a 3D view's see-through points' slabs, as many layers as `SLABS`
        let slabs = wgpu::BindGroupLayoutEntry { binding: 21, visibility: composing, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2Array, multisampled: false }, count: None };
        let image_layout = [false, true].map(|multisampled| layout(
            "vector images",
            &[texture(0), texture(1), texture(2), wgpu::BindGroupLayoutEntry { binding: 3, visibility: compute, ty: target(super::COLOR), count: None }, texture(4), entry(5, compute, read), entry(6, compute, read), sampled(7, wgpu::TextureSampleType::Float { filterable: false }, multisampled), sampled(8, wgpu::TextureSampleType::Depth, multisampled), entry(9, compute, read), maps, compare, dfg, linear, entry(14, compute, rw), cube, texture(16), texture(17), sampled(18, wgpu::TextureSampleType::Float { filterable: false }, multisampled), wgpu::BindGroupLayoutEntry { binding: 19, visibility: compute, ty: target(super::RADIANCE), count: None }, texture(20), slabs],
        ));
        let read_layout = layout("records in", &[entry(0, vertex, read), entry(1, vertex, read), entry(2, fragment, rw)]);
        let pipeline_layout = |groups: &[Option<&wgpu::BindGroupLayout>]| device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: groups, immediate_size: 0 });
        let accumulate = pipeline_layout(&[Some(&scene_layout), None, None, Some(&read_layout)]);
        let add = wgpu::BlendState { color: wgpu::BlendComponent { src_factor: wgpu::BlendFactor::One, dst_factor: wgpu::BlendFactor::One, operation: wgpu::BlendOperation::Add }, alpha: wgpu::BlendComponent::REPLACE };
        let render = |label: &str, layout: &wgpu::PipelineLayout, vs: &str, fs: &str, targets: &[Option<wgpu::ColorTargetState>]| {
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some(label),
                layout: Some(layout),
                vertex: wgpu::VertexState { module: &shader, entry_point: Some(vs), compilation_options: Default::default(), buffers: &[] },
                fragment: Some(wgpu::FragmentState { module: &shader, entry_point: Some(fs), compilation_options: Default::default(), targets }),
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: None,
                multisample: wgpu::MultisampleState::default(),
                multiview_mask: None,
                cache: None,
            })
        };
        let coverage = [Some(wgpu::ColorTargetState { format: wgpu::TextureFormat::R32Float, blend: Some(add), write_mask: wgpu::ColorWrites::ALL })];
        let (fill, stroke) = (render("vs_fill", &accumulate, "vs_fill", "fs_fill", &coverage), render("vs_stroke", &accumulate, "vs_stroke", "fs_stroke", &coverage));
        let write_layout = layout("records out", &[entry(0, compute, rw), entry(1, compute, rw)]);
        // a 3D view's base depth: its samples' nearest
        let depth_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("base depth"), source: wgpu::ShaderSource::Wgsl(include_str!("depth.wgsl").into()) });
        let depth_entry = |binding, multisampled| wgpu::BindGroupLayoutEntry { binding, visibility: compute, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Depth, view_dimension: wgpu::TextureViewDimension::D2, multisampled }, count: None };
        let depth_out = wgpu::BindGroupLayoutEntry { binding: 2, visibility: compute, ty: wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format: wgpu::TextureFormat::R32Float, view_dimension: wgpu::TextureViewDimension::D2 }, count: None };
        let depth_layouts = [layout("base depth (multisampled)", &[depth_entry(0, true), depth_out]), layout("base depth", &[depth_entry(1, false), depth_out])];
        let depth_resolve = [("nearest_of_samples", &depth_layouts[0]), ("single_sample", &depth_layouts[1])].map(|(entry, l)| {
            device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(entry), layout: Some(&pipeline_layout(&[Some(l)])), module: &depth_shader, entry_point: Some(entry), compilation_options: Default::default(), cache: None })
        });
        let no_samples = [1, 4].map(|samples| [(super::COLOR, None), (super::DEPTH, Some(wgpu::TextureAspect::DepthOnly))].map(|(format, aspect)| {
            let texture = device.create_texture(&wgpu::TextureDescriptor {
                label: Some("no samples"),
                size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 },
                mip_level_count: 1,
                sample_count: samples,
                dimension: wgpu::TextureDimension::D2,
                format,
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
                view_formats: &[],
            });
            texture.create_view(&wgpu::TextureViewDescriptor { aspect: aspect.unwrap_or_default(), ..Default::default() })
        }));
        let far = {
            let t = device.create_texture(&wgpu::TextureDescriptor {
                label: Some("far"),
                size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: wgpu::TextureFormat::R32Float,
                usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                view_formats: &[],
            });
            queue.write_texture(t.as_image_copy(), &0.0f32.to_le_bytes(), wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(4), rows_per_image: Some(1) }, wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 });
            t.create_view(&Default::default())
        };
        Self {
            limit: limits.max_texture_dimension_2d,
            shader,
            single_shader: None,
            write_layout,
            flatten: [None, None],
            composite: Default::default(),
            crossing: Default::default(),
            crossings: (buffer(device, "crossings", 16, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST), buffer(device, "crossing groups", 16, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::INDIRECT), 3),
            groups_layout: layout("crossing groups", &[entry(0, compute, rw)]),
            records: None,
            depth_layouts,
            depth_resolve,
            nothing: buffer(device, "nothing", 16, wgpu::BufferUsages::STORAGE),
            stroke_depths: None,
            no_samples,
            nearest: None,
            bounds: None,
            no_slabs: device
                .create_texture(&wgpu::TextureDescriptor { label: Some("no slabs"), size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 }, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: super::COLOR, usage: wgpu::TextureUsages::TEXTURE_BINDING, view_formats: &[] })
                .create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2Array), ..Default::default() }),
            scene_layout,
            image_layout,
            read_layout,
            fill,
            stroke,
            groups: Vec::new(),
            used: 0,
            atlas: None,
            rows: 0,
            scratch: None,
            carried: None,
            no_light_out: image(device, "no light out", [1, 1], super::RADIANCE, wgpu::TextureUsages::STORAGE_BINDING),
            empty: image(device, "empty", [1, 1], super::COLOR, wgpu::TextureUsages::TEXTURE_BINDING),
            base_depth: None,
            base: None,
            base_light: None,
            far,
        }
    }

    /// Plan a 2D view: its records in `order`, a path each an object of the group whose coverage
    /// atlas its layers fit, a point cloud or mesh each a raster.
    pub(crate) fn plan(&self, store: &Store, camera: &Camera, records: &[Record], order: &[usize], background: [f32; 4]) -> Result<Plan, String> {
        let (w, h) = (camera.size[0], camera.size[1]);
        let size = [w as u32, h as u32];
        let tiles = [size[0].div_ceil(TILE), size[1].div_ceil(TILE)];
        let limit = self.limit;
        let fresh = || Group { objects: Vec::new(), spans: Vec::new(), masks: Vec::new(), coverage: Shelves::new(ATLAS_WIDTH.max(size[0])), raster: Shelves::new(size[0]), rasters: Vec::new(), fills: 0, strokes: 0 };
        let mut groups = vec![fresh()];
        // a 3D view's planes: the paths that lie in one share it, its depth over the view the same numbers for each
        let flats = if camera.three_d { flats(store, records, order) } else { Flats::default() };
        // each flat's depth over the view: its plane's three points through the camera, z / w from the far plane
        let depths: Vec<[f64; 3]> = flats.points.iter().map(|points| fit_plane(&points.map(|p| camera.seen(p)))).collect();
        // where each flat's depth is kept to its digits (`plane_depth`): its first path's box's corner, the same point
        // for all its paths, so they meet in it to the bit and their order decides
        let mut references: Vec<Option<[f32; 2]>> = vec![None; depths.len()];
        for &k in order {
            let r = &records[k];
            let a = store.shapes.get(&r.key1).ok_or_else(|| format!("unknown shape {}", r.key1))?;
            if a.kind != Kind::Path {
                let [x0, y0, x1, y1] = store.footprint(camera, r).unwrap_or([0.0, 0.0, w, h]); // (unbounded: the whole view)
                let [x0, y0, x1, y1] = [x0.floor().max(0.0), y0.floor().max(0.0), x1.ceil().min(w), y1.ceil().min(h)];
                if x1 <= x0 || y1 <= y0 {
                    continue;
                }
                let (rw, rh) = ((x1 - x0) as u32, (y1 - y0) as u32);
                let at = fit(&mut groups, fresh, |g| g.raster.place(rw, rh, limit))?;
                let group = groups.last_mut().expect("a group");
                group.rasters.push(Raster { record: k, rect: [at & 0xffff, at >> 16, rw, rh], corner: [x0, y0] });
                group.objects.push(Object { rect: [x0, y0, x1 - x0, y1 - y0], atlas: [NONE, NONE, NONE, at], ids: [NONE; 4], slots: [group.fills, group.strokes, 0, 0], ..Object::zeroed() });
                group.spans.push(span([x0, y0, x1, y1], tiles));
                group.masks.push(None);
                continue;
            }
            let b = if r.key2 == 0 { None } else { Some(store.shapes.get(&r.key2).ok_or_else(|| format!("unknown shape {}", r.key2))?) };
            if let Some(b) = b.filter(|b| b.curves.count != a.curves.count) {
                return Err(format!("morph between unaligned shapes ({} vs {} curves)", a.curves.count, b.curves.count));
            }
            let c = a.curves;
            let (sw, bw) = (r.params[2] * camera.unit, r.params[3] * camera.unit);
            let eye = camera.eye(r);
            let mut paint = store.paint(camera, &eye, r)?;
            let [fill, stroke, background] = [paint.fill, paint.stroke, paint.background].map(|c| c[3]);
            let layers = [fill > 0.0 || paint.brush[1] > 1, sw > 0.0 && (stroke > 0.0 || paint.brush[3] > 1), bw > 0.0 && background > 0.0];
            if c.count == 0 || layers == [false; 3] {
                continue;
            }
            // canonical point -> view pixel (y down), projectively: (x, y) / w through the camera's
            // clip w (a 2D view's is 1: its rows are the affine map's, term by term, arithmetic and all);
            // only term 1 carries the translation
            let pixels = |m: &Mat34, first: bool| {
                let t = compose(&eye, m, first);
                let x = [0, 1, 2, 3].map(|j| 0.5 * w * t[0][j] + 0.5 * w * t[3][j]);
                let y = [0, 1, 2, 3].map(|j| -0.5 * h * t[1][j] + 0.5 * h * t[3][j]);
                (x, y, t[3])
            };
            let (t1x, t1y, t1w) = pixels(&r.m1, true);
            let (t2x, t2y, t2w) = if b.is_some() { pixels(&r.m2, false) } else { ([0.0; 4], [0.0; 4], [0.0; 4]) };
            // rows of its depth from the far plane (z - w, clip's: exact where z / w is near 1): its depth plane's
            // points, a non-planar path's strokes' depth; and the near plane, z = 0, in front of which it shows
            let deep = camera.deep_eye(r);
            let (z1, z2) = if camera.three_d { (compose(&deep, &r.m1, true)[2], if b.is_some() { compose(&deep, &r.m2, false)[2] } else { [0.0; 4] }) } else { ([0.0; 4], [0.0; 4]) };
            // its box and how far its map stretches, over what can be seen of its boxes: the corners in front of the
            // near plane of the pairs of a point of term 1 and one of term 2 (a morph's; their rows add), and where
            // the pairs' box's edges cross the near plane (a box reaching behind it is `clipped`), a projective map of
            // the pair whose extremes over that part of the box are at those points (a 2D view's w is 1: the terms'
            // bounds add)
            let corners = |lo: [f32; 3], hi: [f32; 3]| -> [[f32; 3]; 8] { std::array::from_fn(|corner| [0, 1, 2].map(|i| if corner >> i & 1 == 0 { lo[i] } else { hi[i] })) };
            let (ones, twos) = (corners(a.lo, a.hi), b.map_or([[0.0; 3]; 8], |b| corners(b.lo, b.hi)));
            let projective = [t1w, t2w].iter().any(|w| w[0] != 0.0 || w[1] != 0.0 || w[2] != 0.0);
            let row = |t: &[f32; 4], p: [f32; 3]| t[0] * p[0] + t[1] * p[1] + t[2] * p[2] + t[3];
            let (js, edges) = if b.is_some() { (8, 6) } else { (1, 3) };
            let pair = |i: usize, j: usize| -> [f32; 4] { [(&t1x, &t2x), (&t1y, &t2y), (&z1, &z2), (&t1w, &t2w)].map(|(t1, t2)| row(t1, ones[i]) + row(t2, twos[j])) };
            let (mut seen, mut clipped) = (Vec::with_capacity(8 * js), false);
            for i in 0..8 {
                for j in 0..js {
                    // (its clip z: z - w, plus w)
                    let h = pair(i, j);
                    if h[2] + h[3] >= 0.0 {
                        seen.push(h);
                        continue;
                    }
                    clipped = true;
                    for k in 0..edges {
                        let g = if k < 3 { pair(i ^ 1 << k, j) } else { pair(i, j ^ 1 << (k - 3)) };
                        if g[2] + g[3] >= 0.0 {
                            let f = (h[2] + h[3]) / ((h[2] + h[3]) - (g[2] + g[3]));
                            seen.push(std::array::from_fn(|n| h[n] + f * (g[n] - h[n])));
                        }
                    }
                }
            }
            if seen.is_empty() {
                continue; // all of it behind the near plane
            }
            let (mut lo, mut hi, mut s1, mut s2) = ([f32::MAX; 2], [f32::MIN; 2], 0.0f32, 0.0f32);
            for [x, y, _, ww] in seen {
                let at = [x / ww, y / ww];
                (lo, hi) = ([lo[0].min(at[0]), lo[1].min(at[1])], [hi[0].max(at[0]), hi[1].max(at[1])]);
                if projective {
                    s1 = s1.max(stretch_at(&t1x, &t1y, &t1w, at, ww));
                    s2 = s2.max(stretch_at(&t2x, &t2y, &t2w, at, ww));
                }
            }
            if !projective {
                (s1, s2) = (stretch(&t1x, &t1y), if b.is_some() { stretch(&t2x, &t2y) } else { 0.0 });
            }
            let mut worst = c.flatness * s1;
            let mut reach = c.miter;
            if let Some(b) = b {
                worst += b.curves.flatness * s2;
                reach = reach.max(b.curves.miter);
            }
            // a stroke reaches past the path by its sharpest miter (doubled: affine maps change
            // angles), at most the miter limit
            let margin = if layers[1] || layers[2] { 0.5 * sw.max(bw) * (2.0 * reach).min(10.0) + 2.0 } else { 2.0 };
            let [x0, y0] = [(lo[0] - margin).floor().max(0.0), (lo[1] - margin).floor().max(0.0)];
            let [x1, y1] = [(hi[0] + margin).ceil().min(w), (hi[1] + margin).ceil().min(h)];
            if x1 <= x0 || y1 <= y0 {
                continue;
            }
            let (ow, oh) = ((x1 - x0) as u32, (y1 - y0) as u32);
            let atlas = fit(&mut groups, fresh, |g| {
                let saved = g.coverage;
                let mut atlas = [NONE; 4];
                for (layer, _) in layers.iter().enumerate().filter(|(_, shown)| **shown) {
                    let Some(at) = g.coverage.place(ow, oh, limit) else {
                        g.coverage = saved;
                        return None;
                    };
                    atlas[layer] = at;
                }
                Some(atlas)
            })?;
            // into the object's local pixels: x - x0 w (a 2D view's w is the translation's 1 alone)
            let local = |t: [f32; 4], by: f32, tw: &[f32; 4]| [0, 1, 2, 3].map(|j| t[j] - by * tw[j]);
            // its depth over view pixels: its plane's (a morph's: both terms' plane points, summed), through the
            // camera, exactly that of the paths before it that it lies in (their order decides where they meet, as
            // in a 2D view, whose paths all lie in depth 0)
            // its fill lit by the view's lights: a 3D view's planar path with a material, in the scene (not fixed in
            // the frame); its plane's normal in the world (a morph's: both terms' plane points, summed, as its depth
            // plane takes them)
            let [q0, q1, q2] = world_plane(a, b, r);
            let (u, v) = ([0, 1, 2].map(|k| q1[k] - q0[k]), [0, 1, 2].map(|k| q2[k] - q0[k]));
            let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
            let length = (n[0] * n[0] + n[1] * n[1] + n[2] * n[2]).sqrt();
            let lit = camera.three_d && r.material[3] > 0.0 && r.flags & super::OVERLAY == 0 && a.planar && b.is_none_or(|b| b.planar) && length > 1e-12;
            let normal = if lit { n.map(|x| (x / length) as f32) } else { [0.0; 3] };
            // else lit as a whole, like CE (where it is shaded in 3D): solid colors here, gradients by the composite
            // (`place`)
            let light = if lit { 0.0 } else { store.light(camera, r)? };
            for c in [&mut paint.fill, &mut paint.stroke, &mut paint.background] {
                if c[3] >= 0.0 {
                    *c = super::lighten(*c, light);
                }
            }
            let [pa, pb, pc] = if camera.three_d {
                let row = |t: &[f32; 4], p: [f64; 3]| [0, 1, 2].map(|j| t[j] as f64 * p[j]).iter().sum::<f64>() + t[3] as f64;
                let points: Vec<[f64; 3]> = (0..3)
                    .filter_map(|i| {
                        let (p1, p2) = (a.plane[i], b.map_or([0.0; 3], |b| b.plane[i]));
                        let at = |t1: &[f32; 4], t2: &[f32; 4]| row(t1, p1) + row(t2, p2);
                        let ww = at(&t1w, &t2w);
                        (ww.abs() > 1e-6).then(|| [at(&t1x, &t2x) / ww, at(&t1y, &t2y) / ww, at(&z1, &z2) / ww])
                    })
                    .collect();
                match flats.of.get(&k) {
                    Some(&f) => depths[f],
                    None => fit_plane(&points),
                }
            } else {
                [0.0; 3]
            };
            let reference = match flats.of.get(&k) {
                Some(&f) => *references[f].get_or_insert([x0, y0]),
                None => [x0, y0],
            };
            // the records its flattening can write, a slot each (see `vector.wgsl`): a fill edge per segment of each
            // curve (as many as its curves need most: the shader's own bound, with room for its rounding) and a closing
            // edge per subpath; for each stroke layer, a body piece per segment and dash window it meets, a joint's
            // records at each curve and a cap's at each end of what each subpath shows in each dash window it meets
            let n = (((24.0 * worst).sqrt() * 1.0001).ceil().max(1.0) as u32).min(256);
            let (cap, joint) = (paint.brush2[3] & 3, paint.brush2[3] >> 2 & 3);
            let (windows_per_segment, windows) = if r.dash[0] > 0.0 && r.dash[1] < 1.0 {
                // a segment (a curve's 1 / n) and a subpath (its longest) meet at most this many, and one for rounding
                let longest = store.ranges[c.first_subpath as usize..(c.first_subpath + c.subpaths) as usize].iter().map(|s| s[1] - s[0]).max().unwrap_or(0);
                let meet = |u: f32| ((u / r.dash[0]).ceil() as u32).saturating_add(2).min(1 << 16);
                (meet(1.0 / n as f32), meet(longest as f32))
            } else {
                (1, 1)
            };
            // a round piece's records (two triangles each) over half a turn, at its widest stroke layer
            let round = [(layers[1], sw), (layers[2], bw)].iter().filter(|(shown, _)| *shown).map(|(_, w)| fan(0.5 * w).div_ceil(2)).max().unwrap_or(1);
            let joints = if joint == ROUND { round } else { 1 };
            let caps = match cap {
                ROUND => round,
                SQUARE => 1,
                _ => 0,
            };
            let fills = if layers[0] { c.count.saturating_mul(n).saturating_add(c.subpaths).saturating_mul(1 + clipped as u32) } else { 0 };
            // a clipped object's hidden points' shadows on the near plane, in its shape's own space: clip z's gradient
            // along its plane g (term 1's), and 1 / (z1 . g): a point p moves to p - z(p) g / (z1 . g) (`shadow`)
            let near = if clipped {
                let [p0, p1, p2] = a.plane;
                let (u, v) = ([0, 1, 2].map(|k| p1[k] - p0[k]), [0, 1, 2].map(|k| p2[k] - p0[k]));
                let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
                let dot = |a: [f64; 3], b: [f64; 3]| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
                let z = [0, 1, 2].map(|i| z1[i] as f64 + t1w[i] as f64); // clip z's
                let g = if dot(n, n) > 1e-20 { [0, 1, 2].map(|k| z[k] - n[k] * dot(z, n) / dot(n, n)) } else { z };
                let d = dot(z, g);
                (if d.abs() > 1e-20 { [g[0], g[1], g[2], 1.0 / d] } else { [z[0], z[1], z[2], 1.0 / dot(z, z).max(1e-20)] }).map(|v| v as f32)
            } else {
                [0.0; 4]
            };
            let per_layer = c.count.saturating_mul(n).saturating_mul(windows_per_segment).saturating_add(c.count.saturating_mul(joints)).saturating_add((2 * c.subpaths).saturating_mul(windows).saturating_mul(caps));
            let strokes = (layers[1] as u32 + layers[2] as u32).saturating_mul(per_layer);
            let group = groups.last_mut().expect("a group");
            group.objects.push(Object {
                t1x: local(t1x, x0, &t1w),
                t1y: local(t1y, y0, &t1w),
                t2x: local(t2x, x0, &t2w),
                t2y: local(t2y, y0, &t2w),
                t1w,
                t2w,
                rect: [x0, y0, x1 - x0, y1 - y0],
                atlas,
                ids: [c.first, b.map_or(NONE, |b| b.curves.first), c.first_subpath, c.subpaths],
                params: [r.params[0], r.params[1], 0.5 * sw, 0.5 * bw],
                dash: [r.dash[0], r.dash[1], r.dash[2], 0.5 * (lo[1] + hi[1]) - y0],
                scale: [s1, s2, margin, c.count as f32],
                // (its depth at its reference point, to its digits: `plane_depth`)
                place: [pa as f32, pb as f32, (pc + pa * reference[0] as f64 + pb * reference[1] as f64) as f32, light],
                flags: [(camera.three_d && !(a.planar && b.is_none_or(|b| b.planar))) as u32, clipped as u32, reference[0] as u32, reference[1] as u32],
                slots: [group.fills, group.strokes, n, windows_per_segment],
                pieces: [joints, caps, windows, 0],
                paint,
                material: if lit { r.material } else { [0.0; 4] },
                normal: [normal[0], normal[1], normal[2], 0.0],
                t1z: z1,
                t2z: z2,
                near,
            });
            let spanned = span([x0, y0, x1, y1], tiles);
            let reach = [2.0, 0.5 * sw * (2.0 * reach).min(10.0) + 2.0, 0.5 * bw * (2.0 * reach).min(10.0) + 2.0];
            let whole = r.params[0] <= 0.0 && r.params[1] >= c.count as f32;
            let rows = [t1x, t1y, t1w, t2x, t2y, t2w];
            group.masks.push(if clipped || !whole { None } else { tile_masks(store, a, b, &rows, spanned, layers, reach) });
            group.spans.push(spanned);
            group.fills = group.fills.saturating_add(fills);
            group.strokes = group.strokes.saturating_add(strokes);
        }
        let raster_size = [size[0], groups.iter().map(|g| g.raster.rows()).max().unwrap_or(0)];
        let lit = groups.iter().any(|g| g.objects.iter().any(|o| o.material[3] > 0.0));
        Ok(Plan { groups, raster_size, size, background, bias: camera.bias, inverse: inverse(&camera.projection), lit, crossings: camera.three_d, light: [0.0; LIGHT] })
    }

    /// A 3D view's base depth for its composite: `depth` (the raster pass's, `samples` per pixel) as its samples'
    /// nearest, one float a pixel.
    pub(crate) fn resolve_depth(&mut self, device: &wgpu::Device, encoder: &mut wgpu::CommandEncoder, depth: &wgpu::TextureView, samples: u32, size: [u32; 2]) {
        let (depth_layouts, depth_resolve) = (&self.depth_layouts, &self.depth_resolve);
        if self.base_depth.as_ref().is_none_or(|(_, have)| *have != size) {
            self.base_depth = Some((image(device, "base depth", size, wgpu::TextureFormat::R32Float, wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING), size));
        }
        let (out, _) = self.base_depth.as_ref().expect("base depth");
        let k = if samples > 1 { 0 } else { 1 };
        let group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("base depth"),
            layout: &depth_layouts[k],
            entries: &[wgpu::BindGroupEntry { binding: k as u32, resource: wgpu::BindingResource::TextureView(depth) }, wgpu::BindGroupEntry { binding: 2, resource: wgpu::BindingResource::TextureView(out) }],
        });
        let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("base depth"), timestamp_writes: None });
        pass.set_pipeline(&depth_resolve[k]);
        pass.set_bind_group(0, &group, &[]);
        pass.dispatch_workgroups(size[0].div_ceil(16), size[1].div_ceil(16), 1);
    }

    /// Where a 3D view's raster passes put its base (their colour), for its composite to read as it writes the canvas.
    pub(crate) fn base(&mut self, device: &wgpu::Device, size: [u32; 2]) -> wgpu::TextureView {
        if self.base.as_ref().is_none_or(|(_, have)| *have != size) {
            self.base = Some((image(device, "base", size, super::COLOR, wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING), size));
        }
        self.base.as_ref().expect("base").0.clone()
    }

    /// Where a 3D view with lit meshes puts its base's light (`blend.wgsl`'s `Base`), beside its paint (`base`).
    pub(crate) fn base_light(&mut self, device: &wgpu::Device, size: [u32; 2]) -> wgpu::TextureView {
        if self.base_light.as_ref().is_none_or(|(_, have)| *have != size) {
            self.base_light = Some((image(device, "base light", size, super::RADIANCE, wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING), size));
        }
        self.base_light.as_ref().expect("base light").0.clone()
    }

    /// A new frame: the groups' buffers are taken afresh, and the coverage atlas sized again for what the last frame
    /// needed (it only grows within a frame: views and lights' maps take it in turn).
    pub(crate) fn begin(&mut self) {
        self.used = 0;
        if self.atlas.as_ref().is_some_and(|(_, [_, ah])| *ah > 2 * self.rows + 256) {
            self.atlas = None;
        }
        self.rows = 0;
    }

    /// The composite's pipelines for views that lay what `key` says (`LIT`, `RASTERS`, `LISTS`: the overrides in
    /// `vector.wgsl`), made when first needed. Only a 3D view needs the passes where depths cross.
    fn composite(&mut self, device: &wgpu::Device, key: usize, crossings: bool) {
        if self.composite[key].is_some() && (!crossings || self.crossing[key].is_some()) {
            return;
        }
        let kind = (key & SINGLE == 0) as usize;
        let shader = if kind == 0 { self.single_shader.get_or_insert_with(|| Self::shader(device, false)) } else { &self.shader };
        let constants = [("lighting", (key & LIT) as f64), ("rasters", (key & RASTERS != 0) as u8 as f64), ("lists", (key & LISTS != 0) as u8 as f64), ("points", (key & POINTS != 0) as u8 as f64)];
        let layout = |groups: &[Option<&wgpu::BindGroupLayout>]| device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: groups, immediate_size: 0 });
        let composing = layout(&[Some(&self.scene_layout), Some(&self.image_layout[kind])]);
        // workgroup memory is written before it is read: zeroing it would only cost time
        let make = |entry: &str, layout: &wgpu::PipelineLayout| {
            let options = wgpu::PipelineCompilationOptions { constants: &constants, zero_initialize_workgroup_memory: false };
            device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(entry), layout: Some(layout), module: shader, entry_point: Some(entry), compilation_options: options, cache: None })
        };
        if self.composite[key].is_none() {
            self.composite[key] = Some([make("composite", &composing), make("keep", &composing)]);
        }
        if crossings && self.crossing[key].is_none() {
            let counting = layout(&[Some(&self.scene_layout), Some(&self.image_layout[kind]), Some(&self.groups_layout)]);
            self.crossing[key] = Some([make("count_crossings", &counting), make("settle_crossings", &composing)]);
        }
    }

    /// Fill and stroke records have independent producers. A view pays only for the families it draws.
    fn prepare_flatten(&mut self, device: &wgpu::Device, counts: [u32; 2]) {
        for (i, count) in counts.into_iter().enumerate() {
            if count == 0 || self.flatten[i].is_some() { continue; }
            let entry = ["flatten_fill", "flatten_stroke"][i];
            let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&self.scene_layout), None, Some(&self.write_layout)], immediate_size: 0 });
            let options = wgpu::PipelineCompilationOptions { zero_initialize_workgroup_memory: false, ..Default::default() };
            self.flatten[i] = Some(device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some(entry), layout: Some(&layout), module: &self.shader, entry_point: Some(entry), compilation_options: options, cache: None }));
        }
    }

    /// The pipelines of a light's map and of a view's opaque depth from its paths (`fs_nearest`), made when one is
    /// first needed: the coverage atlas and a non-planar path's strokes' depths are what they read besides the scene.
    fn nearest(&mut self, device: &wgpu::Device) {
        if self.nearest.is_some() {
            return;
        }
        let fragment = wgpu::ShaderStages::FRAGMENT;
        let atlas = wgpu::BindGroupLayoutEntry { binding: 0, visibility: fragment, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }, count: None };
        let depths = wgpu::BindGroupLayoutEntry { binding: 9, visibility: fragment, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None };
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some("nearest"), entries: &[atlas, depths] });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&self.scene_layout), Some(&layout)], immediate_size: 0 });
        // a light's map (standard Z), a view's depth (reversed Z: nearer is greater)
        let pipelines = [(false, wgpu::CompareFunction::Less), (true, wgpu::CompareFunction::Greater)].map(|(view, compare)| {
            let constants = [("view_depth", view as u8 as f64)];
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some("nearest"),
                layout: Some(&pipeline_layout),
                vertex: wgpu::VertexState { module: &self.shader, entry_point: Some("vs_cover"), compilation_options: Default::default(), buffers: &[] },
                fragment: Some(wgpu::FragmentState { module: &self.shader, entry_point: Some("fs_nearest"), compilation_options: wgpu::PipelineCompilationOptions { constants: &constants, ..Default::default() }, targets: &[] }),
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: Some(wgpu::DepthStencilState { format: wgpu::TextureFormat::Depth32Float, depth_write_enabled: Some(true), depth_compare: Some(compare), stencil: Default::default(), bias: Default::default() }),
                multisample: wgpu::MultisampleState::default(),
                multiview_mask: None,
                cache: None,
            })
        });
        self.nearest = Some((layout, pipelines));
    }

    /// The pipeline of a 3D view's slab bounds (`bound_slabs`), made when first needed: what it reads besides the scene
    /// (the coverage atlas, the lists, a non-planar path's strokes' depths), and where it writes them.
    fn bounds(&mut self, device: &wgpu::Device) {
        if self.bounds.is_some() {
            return;
        }
        let compute = wgpu::ShaderStages::COMPUTE;
        let read = |binding| wgpu::BindGroupLayoutEntry { binding, visibility: compute, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None };
        let atlas = wgpu::BindGroupLayoutEntry { binding: 0, visibility: compute, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }, count: None };
        let out = wgpu::BindGroupLayoutEntry { binding: 0, visibility: compute, ty: wgpu::BindingType::StorageTexture { access: wgpu::StorageTextureAccess::WriteOnly, format: wgpu::TextureFormat::Rgba32Float, view_dimension: wgpu::TextureViewDimension::D2 }, count: None };
        let layouts = [("slab bounds in", &[atlas, read(5), read(6), read(9)][..]), ("slab bounds", &[out][..])].map(|(label, entries)| device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries }));
        let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&self.scene_layout), Some(&layouts[0]), Some(&layouts[1])], immediate_size: 0 });
        let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some("bound_slabs"), layout: Some(&layout), module: &self.shader, entry_point: Some("bound_slabs"), compilation_options: Default::default(), cache: None });
        self.bounds = Some((layouts, pipeline));
    }

    /// Encode group `g` of a planned view into `out`: `statics` are the store's control points, subpaths and rows.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn encode(&mut self, device: &wgpu::Device, queue: &wgpu::Queue, encoder: &mut wgpu::CommandEncoder, plan: &Plan, g: usize, statics: &[wgpu::BindingResource<'_>; 3], out: Out<'_>) {
        let group = &plan.groups[g];
        self.prepare_flatten(device, [group.fills, group.strokes]);
        let [w, h] = plan.size;
        let [tiles_x, tiles_y] = [w.div_ceil(TILE), h.div_ceil(TILE)];
        let (base, light, listed, glowing, slabs) = match &out {
            Out::Color { base, light, listed, light_out, slabs, .. } => (*base, *light, *listed, *light_out, slabs.filter(|_| g == 0)),
            Out::Bounds { listed, .. } => (None, None, *listed, None, None),
            Out::Depth(_) | Out::Opaque(_) => (None, None, None, None, None),
        };
        // records and the coverage atlas, shared by every group (drawn one after another)
        let need = plan.groups.iter().fold([1024, 1024], |[f, s], g| [f.max(g.fills), s.max(g.strokes)]);
        if self.records.as_ref().is_none_or(|(_, _, have)| have[0] < need[0] || have[1] < need[1]) {
            let [f, s] = need.map(u32::next_power_of_two);
            self.records = Some((buffer(device, "fill records", f as u64 * 48, wgpu::BufferUsages::STORAGE), buffer(device, "stroke records", s as u64 * 48, wgpu::BufferUsages::STORAGE), [f, s]));
        }
        let rows = plan.groups.iter().map(|g| g.coverage.rows()).max().unwrap_or(0).max(1);
        self.rows = self.rows.max(rows);
        let width = group.coverage.width;
        if self.atlas.as_ref().is_none_or(|(_, [aw, ah])| *aw != width || *ah < rows) {
            let size = [width, rows.div_ceil(64) * 64];
            self.atlas = Some((image(device, "coverage atlas", size, wgpu::TextureFormat::R32Float, wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING), size));
        }
        if matches!(out, Out::Color { .. }) && plan.groups.len() > 1 && self.scratch.as_ref().is_none_or(|(_, size)| *size != plan.size) {
            self.scratch = Some((image(device, "overflow", plan.size, super::COLOR, wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING), plan.size));
        }
        // a view with lit content (paths, or meshes in its base) composites with the light; its groups but the last
        // leave their pixels' light to the next (`vector_compute.wgsl`'s `store`), in turn in two images, and the last
        // leaves it for the view's glow where it has one
        let lit = plan.lit || light.is_some();
        let carries = lit && g + 1 < plan.groups.len();
        let glows = lit && g + 1 == plan.groups.len() && glowing.is_some();
        if carries && self.carried.as_ref().is_none_or(|(_, size)| *size != plan.size) {
            let carried = || image(device, "carried light", plan.size, super::RADIANCE, wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING);
            self.carried = Some(([carried(), carried()], plan.size));
        }
        // its composite's pipeline: with the code of what the group lays alone (`vector.wgsl`'s overrides)
        let rastered = !group.rasters.is_empty() || (g == 0 && base.is_some());
        let kind = (!listed.is_some_and(|l| l.samples == 1)) as usize;
        let key = (kind == 0) as usize * SINGLE | lit as usize * LIT | rastered as usize * RASTERS | (g == 0 && listed.is_some()) as usize * LISTS | slabs.is_some() as usize * POINTS;
        match out {
            Out::Color { .. } => self.composite(device, key, plan.crossings),
            Out::Bounds { .. } => self.bounds(device),
            Out::Depth(_) | Out::Opaque(_) => self.nearest(device),
        }
        if self.used == self.groups.len() {
            self.groups.push(GroupBuffers {
                uniform: buffer(device, "vector frame", size_of::<FrameUniform>() as u64, wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST),
                objects: Data::new(device, "objects"),
                tiles: Data::new(device, "tiles"),
            });
        }
        let b = &mut self.groups[self.used];
        self.used += 1;
        let tiles = tile_lists(&group.spans, &group.masks, &group.objects, tiles_x, (tiles_x * tiles_y) as usize);
        b.objects.hold(device, queue, "objects", bytemuck::cast_slice::<Object, u8>(&group.objects));
        b.tiles.hold(device, queue, "tiles", bytemuck::cast_slice(&tiles));
        let (atlas, [aw, ah]) = self.atlas.as_ref().expect("atlas");
        let [red, green, blue, alpha] = plan.background;
        let uniform = FrameUniform {
            size: [w as f32, h as f32, *aw as f32, *ah as f32],
            tiles: [tiles_x, tiles_y, group.fills, group.strokes],
            counts: [group.objects.len() as u32, (g > 0) as u32, base.map_or(0, |_| if g == 0 { 1 } else { 2 }), (if g == 0 { light.is_some() } else { lit }) as u32 | ((carries || glows) as u32) << 1],
            background: [red * alpha, green * alpha, blue * alpha, alpha],
            depth: [plan.bias, 0.0, 0.0, 0.0],
            lists: listed.filter(|_| g == 0).map_or([0, 0, 0, 1], |l| [1, l.rows[0], l.rows[1], l.samples]),
            inverse: plan.inverse,
            light: plan.light,
        };
        queue.write_buffer(&b.uniform, 0, bytemuck::bytes_of(&uniform));
        let bind = |layout: &wgpu::BindGroupLayout, entries: &[(u32, wgpu::BindingResource)]| {
            let entries: Vec<wgpu::BindGroupEntry> = entries.iter().map(|(binding, resource)| wgpu::BindGroupEntry { binding: *binding, resource: resource.clone() }).collect();
            device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout, entries: &entries })
        };
        let [ctrl, subs, rows] = statics.clone();
        let scene = bind(&self.scene_layout, &[(0, b.uniform.as_entire_binding()), (1, ctrl), (2, subs), (3, b.objects.0.as_entire_binding()), (4, rows), (5, b.tiles.0.as_entire_binding())]);
        let view = wgpu::BindingResource::TextureView;
        let depth = if base.is_some() { &self.base_depth.as_ref().expect("base depth").0 } else { &self.far };
        let n = group.objects.len() as u32;
        let accumulate = |encoder: &mut wgpu::CommandEncoder, read: &wgpu::BindGroup| {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("accumulate"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment { view: atlas, depth_slice: None, resolve_target: None, ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT), store: wgpu::StoreOp::Store } })],
                depth_stencil_attachment: None,
                occlusion_query_set: None,
                timestamp_writes: None,
                multiview_mask: None,
            });
            pass.set_bind_group(0, &scene, &[]);
            pass.set_bind_group(3, read, &[]);
            for (pipeline, count) in [(&self.fill, group.fills), (&self.stroke, group.strokes)] {
                if count > 0 {
                    pass.set_pipeline(pipeline);
                    pass.draw(0..6, 0..count);
                }
            }
        };
        // a light's map, or a view's opaque depth (`view`): its paths' nearest depth over its meshes' (`images`: what
        // `fs_nearest` reads), where the group's objects are
        let nearest = |encoder: &mut wgpu::CommandEncoder, map: &wgpu::TextureView, view: bool, images: &[(u32, wgpu::BindingResource)]| {
            let [x0, y0, x1, y1] = group.objects.iter().fold([w, h, 0, 0], |[x0, y0, x1, y1], o| {
                let r = o.rect.map(|v| v as u32);
                [x0.min(r[0]), y0.min(r[1]), x1.max(r[0] + r[2]).min(w), y1.max(r[1] + r[3]).min(h)]
            });
            if x1 <= x0 || y1 <= y0 {
                return;
            }
            let (layout, pipelines) = self.nearest.as_ref().expect("the nearest pipelines");
            let images = bind(layout, images);
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("nearest"),
                color_attachments: &[],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment { view: map, depth_ops: Some(wgpu::Operations { load: wgpu::LoadOp::Load, store: wgpu::StoreOp::Store }), stencil_ops: None }),
                occlusion_query_set: None,
                timestamp_writes: None,
                multiview_mask: None,
            });
            pass.set_scissor_rect(x0, y0, x1 - x0, y1 - y0);
            pass.set_pipeline(&pipelines[view as usize]);
            pass.set_bind_group(0, &scene, &[]);
            pass.set_bind_group(1, &images, &[]);
            pass.draw(0..3, 0..1);
        };
        let (fill_records, stroke_records, _) = self.records.as_ref().expect("records");
        // a non-planar path's strokes keep their depth per pixel of the atlas: cleared for each group that has one
        let deep = group.objects.iter().any(|o| o.flags[0] != 0);
        let depths = if deep {
            let need = *aw as u64 * *ah as u64 * 4;
            if self.stroke_depths.as_ref().is_none_or(|(_, have)| *have < need) {
                self.stroke_depths = Some((buffer(device, "stroke depths", need, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST), need));
            }
            let (depths, _) = self.stroke_depths.as_ref().expect("stroke depths");
            encoder.clear_buffer(depths, 0, Some(*aw as u64 * group.coverage.rows().max(1) as u64 * 4));
            depths
        } else {
            &self.nothing
        };
        let write = bind(&self.write_layout, &[(0, fill_records.as_entire_binding()), (1, stroke_records.as_entire_binding())]);
        let read = bind(&self.read_layout, &[(0, fill_records.as_entire_binding()), (1, stroke_records.as_entire_binding()), (2, depths.as_entire_binding())]);
        for (pipeline, count) in self.flatten.iter().zip([group.fills, group.strokes]) {
            let slots = count.div_ceil(64); // workgroups: a thread per slot
            if slots == 0 { continue; }
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("flatten"), timestamp_writes: None });
            pass.set_pipeline(pipeline.as_ref().expect("the required record producer"));
            pass.set_bind_group(0, &scene, &[]);
            pass.set_bind_group(2, &write, &[]);
            pass.dispatch_workgroups(slots.min(65535), slots.div_ceil(65535), 1);
        }
        if n > 0 {
            accumulate(encoder, &read);
        }
        match out {
            Out::Color { rasters, target, lighting, .. } => {
                let (under, written) = layered(g, plan.groups.len(), base.unwrap_or(&self.empty), target, self.scratch.as_ref().map(|(s, _)| s));
                // a 3D view's list of the pixels where depths cross: room for every pixel, emptied
                let pixels = w as u64 * h as u64;
                if plan.crossings && self.crossings.2 < pixels {
                    self.crossings = (buffer(device, "crossings", 4 + 4 * pixels, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST), buffer(device, "crossing groups", 16, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::INDIRECT), pixels);
                }
                encoder.clear_buffer(&self.crossings.0, 0, Some(4));
                let (heads, nodes) = listed.map_or((&self.nothing, &self.nothing), |l| (l.heads, l.nodes));
                let [colors, sample_depths] = listed.map_or([&self.no_samples[kind][0], &self.no_samples[kind][1]], |l| [l.colors, l.depths]);
                let lights = listed.and_then(|l| l.lights).unwrap_or(&self.no_samples[kind][0]);
                // the light under the group (the raster base's, or what the group before left), and where it leaves its own
                let carried = self.carried.as_ref().map(|(c, _)| c);
                let light_in = if g == 0 { light.unwrap_or(&self.empty) } else { carried.map_or(&self.empty, |c| &c[(g - 1) % 2]) };
                let light_out = match glowing.filter(|_| glows) {
                    Some(kept) => kept,
                    None if carries => &carried.expect("the carried light")[g % 2],
                    None => &self.no_light_out,
                };
                let images = bind(
                    &self.image_layout[kind],
                    &[(0, view(atlas)), (1, view(rasters.unwrap_or(&self.empty))), (2, view(under)), (3, view(written)), (4, view(depth)), (5, heads.as_entire_binding()), (6, nodes.as_entire_binding()), (7, view(colors)), (8, view(sample_depths)), (9, depths.as_entire_binding()), (10, view(lighting.maps)), (11, wgpu::BindingResource::Sampler(lighting.compare)), (12, view(lighting.dfg)), (13, wgpu::BindingResource::Sampler(lighting.linear)), (14, self.crossings.0.as_entire_binding()), (15, view(lighting.environment)), (16, view(lighting.occlusion)), (17, view(light_in)), (18, view(lights)), (19, view(light_out)), (20, view(slabs.map_or(&self.empty, |s| s[0]))), (21, view(slabs.map_or(&self.no_slabs, |s| s[1])))],
                );
                let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("composite"), timestamp_writes: None });
                // the pixels where the group lays something of its own, then (by a lean pass) the others
                let [composite, keep] = self.composite[key].as_ref().expect("the composite");
                pass.set_pipeline(composite);
                pass.set_bind_group(0, &scene, &[]);
                pass.set_bind_group(1, &images, &[]);
                pass.dispatch_workgroups(tiles_x, tiles_y, 1);
                pass.set_pipeline(keep);
                pass.dispatch_workgroups(tiles_x, tiles_y, 1);
                // then (a 3D view's) the pixels where depths cross, as many workgroups as the count says
                if plan.crossings {
                    let [count, settle] = self.crossing[key].as_ref().expect("the crossing passes");
                    pass.set_pipeline(count);
                    pass.set_bind_group(2, &bind(&self.groups_layout, &[(0, self.crossings.1.as_entire_binding())]), &[]);
                    pass.dispatch_workgroups(1, 1, 1);
                    pass.set_pipeline(settle);
                    pass.dispatch_workgroups_indirect(&self.crossings.1, 0);
                }
            }
            Out::Bounds { out: bounds, .. } => {
                let (layouts, pipeline) = self.bounds.as_ref().expect("the slab bounds' pipeline");
                let (heads, nodes) = listed.map_or((&self.nothing, &self.nothing), |l| (l.heads, l.nodes));
                let read = bind(&layouts[0], &[(0, view(atlas)), (5, heads.as_entire_binding()), (6, nodes.as_entire_binding()), (9, depths.as_entire_binding())]);
                let written = bind(&layouts[1], &[(0, view(bounds))]);
                let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("slab bounds"), timestamp_writes: None });
                pass.set_pipeline(pipeline);
                pass.set_bind_group(0, &scene, &[]);
                pass.set_bind_group(1, &read, &[]);
                pass.set_bind_group(2, &written, &[]);
                pass.dispatch_workgroups(tiles_x, tiles_y, 1);
            }
            Out::Depth(map) => nearest(encoder, map, false, &[(0, view(atlas)), (9, depths.as_entire_binding())]),
            Out::Opaque(map) => nearest(encoder, map, true, &[(0, view(atlas)), (9, depths.as_entire_binding())]),
        }
    }
}

/// A composite pipeline's key: what the view lays, beyond paths (`vector.wgsl`'s overrides `lighting`, `rasters`,
/// `lists`, `points`): lit content, rasters (a 2D view's points and meshes, a 3D view's raster base), see-through lists,
/// see-through points' slabs.
const LIT: usize = 1;
const RASTERS: usize = 2;
const LISTS: usize = 4;
const POINTS: usize = 8;
const SINGLE: usize = 16; // single-sample texture bindings, with the same compositing code

#[cfg(test)]
mod pipeline_demand {
    use super::*;

    #[test]
    fn record_families_compile_only_when_first_needed() {
        super::super::with_gpu(|gpu| {
            for first in 0..2 {
                let mut vector = Vector::new(&gpu.device, &gpu.queue);
                vector.prepare_flatten(&gpu.device, [0, 0]);
                assert!(vector.flatten.iter().all(Option::is_none));
                let mut counts = [0, 0];
                counts[first] = 1;
                vector.prepare_flatten(&gpu.device, counts);
                assert!(vector.flatten[1 - first].is_none());
                let pipeline = vector.flatten[first].clone().unwrap();
                for counts in [[0, 0], counts, [1, 1]] {
                    vector.prepare_flatten(&gpu.device, counts);
                    assert_eq!(vector.flatten[first].as_ref(), Some(&pipeline));
                }
                assert!(vector.flatten.iter().all(Option::is_some));
            }
        }).unwrap();
    }

    #[test]
    fn two_d_views_leave_crossing_passes_for_the_first_three_d_view() {
        super::super::with_gpu(|gpu| {
            let mut vector = Vector::new(&gpu.device, &gpu.queue);
            for key in [0, SINGLE] {
                for _ in 0..2 {
                    vector.composite(&gpu.device, key, false);
                    assert!(vector.composite[key].is_some());
                    assert!(vector.crossing[key].is_none());
                }
                for crossings in [true, false, true] {
                    vector.composite(&gpu.device, key, crossings);
                    assert!(vector.composite[key].is_some());
                    assert!(vector.crossing[key].is_some());
                }
            }
        }).unwrap();
    }
}

/// What group `g` of `groups` lies over and writes: each lies over what the ones before it made (the first over
/// `first`); the last writes the target, the others alternate with the scratch image behind it.
fn layered<'a>(g: usize, groups: usize, first: &'a wgpu::TextureView, target: &'a wgpu::TextureView, scratch: Option<&'a wgpu::TextureView>) -> (&'a wgpu::TextureView, &'a wgpu::TextureView) {
    match (g, (groups - 1 - g).is_multiple_of(2)) {
        (0, true) => (first, target),
        (0, false) => (first, scratch.expect("scratch")),
        (_, true) => (scratch.expect("scratch"), target),
        (_, false) => (target, scratch.expect("scratch")),
    }
}

/// What a view's paths with a material are lit with: its lights' shadow maps (`maps`) and their comparison, the DFG
/// table (`dfg`), its environment's cube, and their trilinear reads; its ambient occlusion (`occlusion.rs`).
pub(crate) struct Lighting<'a> {
    pub(crate) maps: &'a wgpu::TextureView,
    pub(crate) compare: &'a wgpu::Sampler,
    pub(crate) dfg: &'a wgpu::TextureView,
    pub(crate) linear: &'a wgpu::Sampler,
    pub(crate) environment: &'a wgpu::TextureView,
    pub(crate) occlusion: &'a wgpu::TextureView,
}

/// What a group's composite makes.
pub(crate) enum Out<'a> {
    /// A canvas's color, `target` (the last group covers it entirely): `rasters` the raster atlas, with the group's
    /// rasters drawn in it; `base` a 3D view's raster base (`base`; its depth `resolve_depth`'s), laid among the first
    /// group's layers at its depth, as are its see-through fragments (`listed`) and its see-through points' slabs
    /// (`slabs`: the bounds `Bounds` left, the slabs); `light` the base's light where the view has lit meshes (`base` its
    /// display paint then: `vector.wgsl`'s `base_at`); `lighting` what its paths with a material are lit with.
    /// `light_out`: where a view with lit content leaves its pixels' light, `target` their paint, for its glow to be
    /// spread from and shown with (`bloom.rs`), as its groups but the last leave theirs to the next (none: the last group
    /// shows its pixels).
    Color { rasters: Option<&'a wgpu::TextureView>, target: &'a wgpu::TextureView, base: Option<&'a wgpu::TextureView>, light: Option<&'a wgpu::TextureView>, listed: Option<&'a Listed<'a>>, slabs: Option<[&'a wgpu::TextureView; 2]>, lighting: Lighting<'a>, light_out: Option<&'a wgpu::TextureView> },
    /// A 3D view's slab bounds (`vector.wgsl`'s `bound`), into `out`: at each pixel the depths of its first group's
    /// nearest layers, its paths' and its see-through fragments' (`listed`), for its see-through points to find their
    /// slab by before they are drawn.
    Bounds { out: &'a wgpu::TextureView, listed: Option<&'a Listed<'a>> },
    /// A light's shadow map (its layer, its meshes' depth drawn in it): at each texel, where nearer, the depth of the
    /// nearest layer of the plan (seen from the light) that covers it, half opaque or more (`fs_nearest`).
    Depth(&'a wgpu::TextureView),
    /// A view's opaque depth, for its ambient occlusion (`occlusion.rs`; its opaque meshes' drawn in it, reversed Z):
    /// at each pixel, where nearer, the depth of the nearest opaque layer of the plan that covers it.
    Opaque(&'a wgpu::TextureView),
}
#[cfg(test)]
mod area_contract {
    use super::*;

    fn expected(first: [f32; 4], second: [f32; 4]) -> f64 {
        let mut points = vec![[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]];
        for [x, y, d, _] in [first, second] {
            let signed = |p: [f64; 2]| p[0] * x as f64 + p[1] * y as f64 - d as f64;
            let mut clipped = Vec::new();
            for i in 0..points.len() {
                let (p, q) = (points[i], points[(i + 1) % points.len()]);
                let (a, b) = (signed(p), signed(q));
                if a >= 0.0 { clipped.push(p); }
                if (a >= 0.0) != (b >= 0.0) {
                    clipped.push([0, 1].map(|j| p[j] + (q[j] - p[j]) * a / (a - b)));
                }
            }
            points = clipped;
        }
        (0..points.len()).map(|i| {
            let (p, q) = (points[i], points[(i + 1) % points.len()]);
            p[0] * q[1] - p[1] * q[0]
        }).sum::<f64>().abs() * 0.5
    }

    #[test]
    fn half_plane_intersection_matches_independent_polygon_clipping() {
        let mut normals = vec![[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0], [0.6, 0.8], [-0.6, 0.8], [0.6, -0.8], [-0.6, -0.8]];
        for angle in [1e-7f32, 0.01, 0.099, std::f32::consts::PI - 0.099] { normals.push([angle.cos(), angle.sin()]); }
        let offsets = [-1.0, -0.5, -0.49999997, -0.25, 0.0, 0.25, 0.49999997, 0.5, 1.0];
        // x >= 0 intersected with ±16x + y >= 0 removes or retains a triangle
        // of area (1/2) * (1/2) * (1/32) = 1/128. These closed-form witnesses
        // independently catch treating nearly parallel lines as parallel.
        let x = 16.0f32 / 257.0f32.sqrt();
        let axis = [1.0, 0.0, 0.0, 0.0];
        let mut inputs = vec![axis, [x, x / 16.0, 0.0, 0.0], axis, [-x, x / 16.0, 0.0, 0.0]];
        let mut areas = vec![63.0 / 128.0, 1.0 / 128.0];
        for &n in &normals { for &m in &normals { for a in offsets { for b in offsets {
            let first = [n[0], n[1], a, 0.0];
            let second = [m[0], m[1], b, 0.0];
            inputs.extend([first, second]);
            areas.push(expected(first, second));
        }}}}
        super::super::with_gpu(|gpu| {
            let text = include_str!("vector.wgsl");
            let begin = text.find("fn side_area(").unwrap();
            let end = text.find("// What covers a pixel").unwrap();
            let source = format!("{}\n{}", &text[begin..end], r#"
                @group(0) @binding(0) var<storage, read> cases: array<vec4<f32>>;
                @group(0) @binding(1) var<storage, read_write> areas: array<f32>;
                @compute @workgroup_size(64)
                fn area_test(@builtin(global_invocation_id) gid: vec3<u32>) {
                    if (gid.x >= arrayLength(&areas)) { return; }
                    let a = cases[2u * gid.x];
                    let b = cases[2u * gid.x + 1u];
                    areas[gid.x] = both_area(a.xy, a.z, b.xy, b.z);
                }
            "#);
            let device = &gpu.device;
            let module = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("area law"), source: wgpu::ShaderSource::Wgsl(source.into()) });
            let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor { label: Some("area law"), layout: None, module: &module, entry_point: Some("area_test"), compilation_options: Default::default(), cache: None });
            let input = buffer(device, "area inputs", (inputs.len() * 16) as u64, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST);
            gpu.queue.write_buffer(&input, 0, bytemuck::cast_slice(&inputs));
            let size = (areas.len() * 4) as u64;
            let output = buffer(device, "areas", size, wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC);
            let read = buffer(device, "area read", size, wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ);
            let bindings = device.create_bind_group(&wgpu::BindGroupDescriptor { label: None, layout: &pipeline.get_bind_group_layout(0), entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: input.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: output.as_entire_binding() },
            ] });
            let mut encoder = device.create_command_encoder(&Default::default());
            {
                let mut pass = encoder.begin_compute_pass(&Default::default());
                pass.set_pipeline(&pipeline);
                pass.set_bind_group(0, &bindings, &[]);
                pass.dispatch_workgroups((areas.len() as u32).div_ceil(64), 1, 1);
            }
            encoder.copy_buffer_to_buffer(&output, 0, &read, 0, size);
            gpu.queue.submit([encoder.finish()]);
            read.slice(..).map_async(wgpu::MapMode::Read, |result| result.unwrap());
            device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
            let data = read.slice(..).get_mapped_range().unwrap();
            for (i, (actual, expected)) in bytemuck::cast_slice::<_, f32>(&data).iter().zip(areas).enumerate() {
                assert!(actual.is_finite() && (*actual as f64 - expected).abs() < 2e-6, "case {:?}: {actual} != {expected}", &inputs[2*i..2*i+2]);
            }
        }).unwrap();
    }
}
