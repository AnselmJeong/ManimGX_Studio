//! ManimGX's player: draws blends of shapes — every kind, 2D and 3D — and encodes them to MP4.
//!
//! Python uploads each shape once (a path's curves as their control points, a point cloud, a
//! mesh), each brush of several rows once (gradient stops, per-point or per-vertex colors) and each
//! image once; then per frame it sends one record per object: shape keys, two 3×4 matrices, a
//! reveal window, colors, widths, flags. Every animation is new numbers.
//!
//! Every view's paths are drawn exactly (see `vector`): their curves flattened on the GPU, every
//! frame, to the size they are drawn at through the view's camera, each pixel covered by the area
//! inside it, and composited per pixel in depth order (a 2D view's: its draw order). Point clouds
//! and meshes are drawn by the raster pipeline (`blend.wgsl`): a 2D view's into layers laid in their
//! place in the order, a 3D view's into its z-buffered base, which the composite lays at its depth
//! (its see-through meshes' fragments too, through per-pixel lists, and its see-through points,
//! through slabs between its layers). Per object the camera is folded into
//! the blend (C = camera · M, once per object on the CPU): a vertex costs one 4×4 per term.
//!
//! The same drawing runs natively (read back, or encoded to MP4: see `export`) and in the
//! browser, onto a canvas with WebGPU (see `web`).

use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::ops::Range;

use bytemuck::{Pod, Zeroable};
use wgpu::util::DeviceExt;

use crate::{CameraView, check_key, environment, mesh::Mesh, read};

#[cfg(windows)]
#[path = "dxc.rs"]
mod dxc;
#[path = "bloom.rs"]
mod bloom;
#[cfg(not(target_arch = "wasm32"))]
#[path = "lavapipe.rs"]
mod lavapipe;
#[path = "occlusion.rs"]
mod occlusion;
#[path = "shadow.rs"]
mod shadow;
#[path = "vector.rs"]
mod vector;

pub(crate) const COLOR: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8Unorm;
/// What a 3D view with lit meshes keeps their light in, beside its display paint (`blend.wgsl`'s `Base`).
pub(crate) const RADIANCE: wgpu::TextureFormat = wgpu::TextureFormat::Rgba16Float;
// Reversed Z keeps distant depth differences in a float's significant digits. Depth24Plus
// may use fixed-point depth, where those differences vanish.
const DEPTH: wgpu::TextureFormat = wgpu::TextureFormat::Depth32FloatStencil8;
const NONE: u32 = u32::MAX;
const OVERLAY: u64 = 1;
const LIT: u64 = 4;
const TEXTURED: u64 = 8;
const NEAREST: u64 = 16; // an image's reconstruction from its pixels (neither: linear)
const CUBIC: u64 = 32;
const MATERIAL: u64 = 64; // an instance lit by its material and the view's lights (a record's: material[3] = 1)
const STYLE: u64 = 6; // a record's flags from this bit: its stroke's cap | joint << 2 (see `vector.wgsl`)
const ROUND: u32 = 1; // a cap's or joint's style
const SQUARE: u32 = 2; // a cap's
const PLACE: u32 = 8; // an instance's flags from this bit: its record's place in its view
pub(crate) const VIEW_FLOATS: usize = 44; // projection, overlay (column-major), pixels, light, toward; then background
/// A view's lighting, after its background: where it sees from (3D: w = 1); how many lights, the exposure, the tone
/// mapping (1: AgX), its bloom (`bloom`); then `LIGHTS` lights of 16 floats (see `blend.wgsl`'s `Light`).
const VIEW_LIGHTING: usize = VIEW_FLOATS + 4;
const LIGHTS: usize = 8;
const VIEW_OCCLUSION: usize = VIEW_LIGHTING + 8 + 16 * LIGHTS; // its ambient occlusion: how much (0: none), how far
pub(crate) const VIEW_LENGTH: usize = VIEW_OCCLUSION + 4;

type Mat4 = [[f32; 4]; 4]; // rows
pub(crate) type Mat34 = [[f32; 4]; 3];
type Box3 = [[f32; 3]; 2]; // a box in the world: low, high corners

/// Content keys are already uniform hashes: hashing them again only costs time.
#[derive(Default)]
struct Identity(u64);

impl Hasher for Identity {
    fn finish(&self) -> u64 {
        self.0
    }
    fn write(&mut self, bytes: &[u8]) {
        self.0 = bytes.iter().fold(self.0, |h, &b| h.rotate_left(8) ^ b as u64);
    }
    fn write_u64(&mut self, n: u64) {
        self.0 = n;
    }
}

type Keyed<V> = HashMap<u64, V, BuildHasherDefault<Identity>>;

/// One object as the shader reads it (368 bytes).
#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct Instance {
    c1: Mat4,
    c2: Mat4,
    m1: Mat34,
    m2: Mat34,
    params: [f32; 4],
    extra: [f32; 4],
    ids: [u32; 4],
    paint: Paint,
    material: [f32; 4], // metallic, roughness, reflectance (an instance with MATERIAL)
}

/// An object's paint as both pipelines read it: its colors, paint 2 mixed in (once per object;
/// rows are mixed in the shaders, row by row), alpha −1 marking a gradient; the gradient's axis on
/// screen (origin, direction / |direction|², pixels); its rows (fill offset, count, stroke offset,
/// count); paint 2's rows (fill, stroke offsets), how far it is mixed in (f32 bits; 0: not), and
/// the stroke's style (cap | joint << 2).
#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct Paint {
    fill: [f32; 4],
    stroke: [f32; 4],
    background: [f32; 4],
    gradient: [f32; 4],
    brush: [u32; 4],
    brush2: [u32; 4],
}

/// One object as Python sends it: content keys instead of GPU offsets (336 bytes: a take carries records whole, so
/// `take::RECORD` must be its size). Like its
/// geometry (term 2 while morphing), its paint may be two: paint 2's colors and brushes, mixed in
/// by `dash[3]` (a tween's paint — mixed here, as the shapes are, never in Python).
#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
pub(crate) struct Record {
    key1: u64,
    key2: u64,
    fill_rows: u64,
    stroke_rows: u64,
    fill_rows2: u64,
    stroke_rows2: u64,
    texture: u64,
    flags: u64,
    m1: Mat34,
    m2: Mat34,
    fill: [f32; 4],
    stroke: [f32; 4],
    background: [f32; 4],
    fill2: [f32; 4],
    stroke2: [f32; 4],
    background2: [f32; 4],
    params: [f32; 4],
    gradient_a: [f32; 4],
    gradient_b: [f32; 4],
    dash: [f32; 4], // period, duty, phase (u; no dashes when the period is 0); how far paint 2 is in
    material: [f32; 4], // metallic, roughness, reflectance; 1 where it has one (see `blend.wgsl`'s light)
}
const _: () = assert!(size_of::<Record>() == crate::take::RECORD);

#[cfg(feature = "player")]
impl Record {
    /// Path `key` of `curves` curves, placed by `m`, filled with `fill` (straight RGBA): a record a
    /// host makes itself (the window's controls), as Python makes a filled mobject's.
    pub(crate) fn filled(key: u64, curves: u32, m: Mat34, fill: [f32; 4]) -> Self {
        let clear = [0.0; 4];
        Record { key1: key, m1: m, fill, fill2: fill, stroke: clear, stroke2: clear, background: clear, background2: clear, params: [0.0, curves as f32, 0.0, 0.0], ..Zeroable::zeroed() }
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Kind {
    Path,
    Points,
    Mesh,
}

/// A shape: a path's curves (drawn exactly), or the vertices and index codes of a point cloud or
/// mesh, which the raster pipeline draws.
struct Shape {
    kind: Kind,
    curves: Curves,
    base: u32,
    count: u32,
    raster: Raster,
    centroid: [f32; 3], // mean of the control points (a mean commutes with every affine map)
    area: [f32; 3],     // Newell area vector (carried by the cofactor of the linear part)
    lo: [f32; 3],       // bounds of what it draws in its own space (a path's control points: its curves lie within)
    hi: [f32; 3],
    middle: [f32; 3],     // the center of its bounds, by which a 3D view orders it
    plane: [[f64; 3]; 3], // a path's fitted plane; keep its precision through placement and projection
    planar: bool,         // a path's control points lie in that plane (a straight path's: on its line)
}

/// A path's curves in the store: four control points each, and its subpaths as curve ranges.
#[derive(Clone, Copy, Default)]
struct Curves {
    first: u32,
    count: u32,
    room: u32, // curves it can grow to where it is (a path that grows is moved to the end, with room)
    first_subpath: u32,
    subpaths: u32,
    flatness: f32, // the largest second difference of a curve's control points (Wang's D)
    miter: f32,    // how far a stroke reaches past the path, in half-widths (its sharpest corner's miter)
}

/// A point cloud's or mesh's index codes, in the order it is drawn: `count` points, triangles or
/// (a surface's) faces, u's steps as a path's curves are, each laid out with all it draws, one
/// after another, in every layer.
#[derive(Clone, Default)]
struct Raster {
    count: u32,
    fill: Range<u32>,   // mesh triangles
    stroke: Range<u32>, // point quads; a mesh's faces' edges
}

impl Raster {
    /// What a window over u shows: every step it reaches into, whole (a point, a triangle, a face
    /// with its edges), of every layer the same.
    fn shown(&self, [lo, hi]: [f32; 2]) -> (Range<u32>, Range<u32>) {
        let n = self.count;
        let a = (lo.max(0.0).floor() as u32).min(n);
        let b = (hi.max(0.0).ceil() as u32).clamp(a, n);
        let cut = |layer: &Range<u32>| {
            let per = layer.len() as u32 / n.max(1);
            layer.start + a * per..layer.start + b * per
        };
        (cut(&self.fill), cut(&self.stroke))
    }
}

struct Brush {
    offset: u32,
    count: u32,
    see_through: bool, // a row's opacity is below 1
}

/// The shapes and brushes the film still shows, packed into shared arrays (indices rebased on
/// the way in). The arrays only grow — the GPU receives what was appended since it last looked —
/// until the film evicts what no frame shows any more; once more of them is dead than alive, the
/// living are packed again (a new `generation`: the GPU takes the arrays afresh).
#[derive(Default)]
pub(crate) struct Store {
    points: Vec<[f64; 3]>, // paths' control points, four per curve (as given: a path grows and moves from them)
    ctrl: Vec<[f32; 4]>,   // the same for the GPU; a curve's first carries its flatness in w
    ranges: Vec<[u32; 4]>, // paths' subpaths: first curve, end curve (the path's own numbers), closed
    vertices: Vec<[f32; 4]>,
    extras: Vec<[f32; 4]>, // one per vertex
    links: Vec<[u32; 2]>,  // one per vertex (along a mesh's faces' edges; unused by points)
    indices: Vec<u32>,
    rows: Vec<[f32; 4]>,
    shapes: Keyed<Shape>,
    brushes: Keyed<Brush>,
    dead: usize, // bytes of evicted shapes still in the arrays
    generation: u64,
    dirty: Vec<(usize, Range<usize>)>, // (array, bytes) written in place since the GPU looked
}

const VERTEX_BYTES: usize = 16 + 16 + 8; // vertex, extra, link
const CURVE_BYTES: usize = 4 * (24 + 16); // four control points, as f64 and as the GPU's f32

fn bounds(vertices: &[[f32; 4]]) -> ([f32; 3], [f32; 3]) {
    vertices.iter().fold(([f32::MAX; 3], [f32::MIN; 3]), |(lo, hi), v| ([0, 1, 2].map(|i| lo[i].min(v[i])), [0, 1, 2].map(|i| hi[i].max(v[i]))))
}

fn middle((lo, hi): ([f32; 3], [f32; 3])) -> [f32; 3] {
    [0, 1, 2].map(|i| (lo[i] + hi[i]) / 2.0)
}

fn sub(a: [f32; 3], b: [f32; 3]) -> [f32; 3] {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}

fn cross(a: [f32; 3], b: [f32; 3]) -> [f32; 3] {
    [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
}

fn dot(a: [f32; 3], b: [f32; 3]) -> f32 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

/// Three points of the plane that points lie nearest (least squares): their mean, and the mean moved by their spread
/// along each of their two widest principal axes. A planar path's plane exactly; a straight path's line (its second
/// spread is none: its third point is its mean). And whether they lie in it (to rounding).
fn plane(points: &[[f64; 3]]) -> ([[f64; 3]; 3], bool) {
    let n = points.len().max(1) as f64;
    let mean = [0, 1, 2].map(|i| points.iter().map(|p| p[i]).sum::<f64>() / n);
    let mut m = [[0.0f64; 3]; 3];
    for p in points {
        let d = [0, 1, 2].map(|i| p[i] - mean[i]);
        for (i, row) in m.iter_mut().enumerate() {
            for (j, v) in row.iter_mut().enumerate() {
                *v += d[i] * d[j] / n;
            }
        }
    }
    // Jacobi's rotations: m = v diag v^T (a few sweeps converge a 3 x 3 to rounding)
    let mut v = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];
    for _ in 0..8 {
        for (p, q) in [(0, 1), (0, 2), (1, 2)] {
            if m[p][q].abs() <= 1e-30 {
                continue;
            }
            let theta = (m[q][q] - m[p][p]) / (2.0 * m[p][q]);
            let t = theta.signum() / (theta.abs() + (theta * theta + 1.0).sqrt());
            let (c, s) = (1.0 / (t * t + 1.0).sqrt(), t / (t * t + 1.0).sqrt());
            for row in m.iter_mut() {
                (row[p], row[q]) = (c * row[p] - s * row[q], s * row[p] + c * row[q]);
            }
            for k in 0..3 {
                (m[p][k], m[q][k]) = (c * m[p][k] - s * m[q][k], s * m[p][k] + c * m[q][k]);
            }
            for row in v.iter_mut() {
                (row[p], row[q]) = (c * row[p] - s * row[q], s * row[p] + c * row[q]);
            }
        }
    }
    let mut axes = [0, 1, 2];
    axes.sort_by(|&a, &b| m[b][b].total_cmp(&m[a][a]));
    let along = |k: usize| [0, 1, 2].map(|i| mean[i] + m[k][k].max(0.0).sqrt() * v[i][k]);
    let planar = m[axes[2]][axes[2]].max(0.0).sqrt() <= 1e-6 * m[axes[0]][axes[0]].max(0.0).sqrt() + 1e-12;
    ([mean, along(axes[0]), along(axes[1])], planar)
}

/// The largest second difference of a curve's control points (Wang's D, in its own units).
fn flatness(p: &[[f64; 3]]) -> f64 {
    let d = |a: [f64; 3], b: [f64; 3], c: [f64; 3]| ((a[0] - 2.0 * b[0] + c[0]).powi(2) + (a[1] - 2.0 * b[1] + c[1]).powi(2) + (a[2] - 2.0 * b[2] + c[2]).powi(2)).sqrt();
    d(p[0], p[1], p[2]).max(d(p[1], p[2], p[3]))
}

/// A curve's control points as the GPU takes them: f32, the first carrying its flatness in w.
fn gpu_curve(p: &[[f64; 3]]) -> [[f32; 4]; 4] {
    let d = flatness(p) as f32;
    std::array::from_fn(|k| [p[k][0] as f32, p[k][1] as f32, p[k][2] as f32, if k == 0 { d } else { 0.0 }])
}

/// How far a stroke reaches past a path, in half-widths: the miter of its sharpest joint (limit
/// 10), from the turns between consecutive curves in the path's own space (affine maps change
/// angles: the box that uses it doubles it). `ranges` are the path's own curve ranges.
fn miter(points: &[[f64; 3]], ranges: &[[u32; 4]]) -> f32 {
    let tangent = |p: &[[f64; 3]], end: bool| {
        let (a, b) = if end { (p[3], if p[2] != p[3] { p[2] } else { p[1] }) } else { (p[0], if p[1] != p[0] { p[1] } else { p[2] }) };
        let d = [a[0] - b[0], a[1] - b[1]];
        let l = (d[0] * d[0] + d[1] * d[1]).sqrt();
        if l > 1e-12 { [d[0] / l, d[1] / l] } else { [0.0, 0.0] }
    };
    let mut worst = 1.0f64;
    for r in ranges {
        for c in r[0]..r[1] {
            let next = if c + 1 < r[1] { c + 1 } else if r[2] != 0 { r[0] } else { continue };
            let (i, j) = (c as usize, next as usize);
            let into = tangent(&points[4 * i..4 * i + 4], true); // both point backwards along the path
            let out = tangent(&points[4 * j..4 * j + 4], false);
            let cos = -(into[0] * out[0] + into[1] * out[1]); // of the angle between the travel directions
            let half_turn = ((1.0 - cos.clamp(-1.0, 1.0)) * 0.5).sqrt(); // sin of half the turn
            worst = worst.max((1.0 / (1.0 - half_turn * half_turn).sqrt().max(0.1)).min(10.0));
        }
    }
    worst as f32
}

impl Store {
    fn push_vertices(&mut self, vertices: &[[f32; 4]], extras: Option<&[[f32; 4]]>) -> u32 {
        let base = self.vertices.len() as u32;
        self.vertices.extend_from_slice(vertices);
        match extras {
            Some(e) => self.extras.extend_from_slice(e),
            None => self.extras.extend(std::iter::repeat_n([0.0; 4], vertices.len())),
        }
        base
    }

    /// Append curves' control points (four each), `room` curves' worth in all: their index.
    fn push_curves(&mut self, points: &[[f64; 3]], room: usize) -> u32 {
        let first = (self.points.len() / 4) as u32;
        self.points.extend_from_slice(points);
        self.ctrl.extend(points.chunks_exact(4).flat_map(gpu_curve));
        self.points.resize(4 * (first as usize + room), [0.0; 3]);
        self.ctrl.resize(self.points.len(), [0.0; 4]);
        first
    }

    fn bytes(&self) -> usize {
        self.vertices.len() * VERTEX_BYTES + self.indices.len() * 4 + self.rows.len() * 16 + self.points.len() / 4 * CURVE_BYTES + self.ranges.len() * 16
    }

    /// The arrays sent to the GPU, in binding order (the indices are only an index buffer).
    fn arrays(&self) -> [&[u8]; 7] {
        [bytemuck::cast_slice(&self.vertices), bytemuck::cast_slice(&self.links), bytemuck::cast_slice(&self.indices), bytemuck::cast_slice(&self.rows), bytemuck::cast_slice(&self.extras), bytemuck::cast_slice(&self.ctrl), bytemuck::cast_slice(&self.ranges)]
    }

    fn fits(&self, limits: &wgpu::Limits) -> bool {
        self.arrays().iter().enumerate().all(|(k, bytes)| bytes.len() as u64 <= store_limit(limits, k))
    }

    fn rooms(&self, limits: &wgpu::Limits) -> Result<[u64; 7], String> {
        let arrays = self.arrays();
        let mut rooms = [0; 7];
        for (k, name) in ["vertices", "vertex links", "indices", "paint rows", "vertex normals and UVs", "curve points", "subpath ranges"].iter().enumerate() {
            rooms[k] = buffer_room(arrays[k].len() as u64, 1, 1024, store_limit(limits, k), name)?;
        }
        Ok(rooms)
    }

    /// The bytes a shape holds in the arrays: a path's curves (with their room), a point cloud's or
    /// mesh's vertices and index codes.
    #[cfg(any(feature = "python", feature = "player"))]
    fn held(s: &Shape) -> usize {
        s.count as usize * VERTEX_BYTES + (s.raster.fill.len() + s.raster.stroke.len()) * 4 + s.curves.room as usize * CURVE_BYTES + s.curves.subpaths as usize * 16
    }

    /// Forget shapes and brushes; their bytes stay until the arrays are packed.
    #[cfg(any(feature = "python", feature = "player"))]
    fn evict(&mut self, keys: &[u64]) {
        for key in keys {
            if let Some(s) = self.shapes.remove(key) {
                self.dead += Self::held(&s);
            }
            if let Some(b) = self.brushes.remove(key) {
                self.dead += b.count as usize * 16;
            }
        }
    }

    /// Pack the living once most of the arrays is dead, or a binding needs the space now.
    fn pack_if_worthwhile(&mut self, pressed: bool) {
        if self.dead == 0 || (!pressed && (self.dead < 16 << 20 || self.dead * 2 < self.bytes())) {
            return;
        }
        *self = self.packed(|_| true);
    }

    /// A stable packing of selected resources; keys remain logical, offsets belong to this store.
    fn packed(&self, keep: impl Fn(u64) -> bool) -> Self {
        let old = self;
        let mut packed = Self { generation: old.generation + 1, ..Default::default() };
        let mut shapes: Vec<(&u64, &Shape)> = old.shapes.iter().filter(|(key, _)| keep(**key)).collect();
        shapes.sort_by_key(|(_, s)| (s.curves.first, s.base)); // keep their order: packing is a stable move
        for (&key, s) in shapes {
            let mut shape = Shape { base: 0, count: 0, raster: Raster::default(), ..*s };
            if s.kind == Kind::Path {
                let c = s.curves;
                let (a, b) = (4 * c.first as usize, 4 * (c.first + c.count) as usize);
                let first = packed.push_curves(&old.points[a..b], c.count as usize);
                let first_subpath = packed.ranges.len() as u32;
                packed.ranges.extend_from_slice(&old.ranges[c.first_subpath as usize..(c.first_subpath + c.subpaths) as usize]);
                shape.curves = Curves { first, room: c.count, first_subpath, ..c };
            } else {
                let (a, b) = (s.base as usize, (s.base + s.count) as usize);
                let base = packed.push_vertices(&old.vertices[a..b], Some(&old.extras[a..b]));
                let moved = |v: u32| v - s.base + base;
                let r = &s.raster;
                let linked = s.kind == Kind::Mesh && !r.stroke.is_empty();
                packed.links.extend(old.links[a..b].iter().map(|l| if linked { [moved(l[0]), moved(l[1])] } else { [0, 0] }));
                let fill_start = packed.indices.len() as u32;
                packed.indices.extend(old.indices[r.fill.start as usize..r.fill.end as usize].iter().map(|&i| moved(i)));
                let stroke_start = packed.indices.len() as u32;
                packed.indices.extend(old.indices[r.stroke.start as usize..r.stroke.end as usize].iter().map(|&code| (moved(code >> 3) << 3) | (code & 7)));
                let end = packed.indices.len() as u32;
                let raster = Raster { count: r.count, fill: fill_start..stroke_start, stroke: stroke_start..end };
                shape = Shape { base, count: s.count, raster, ..shape };
            }
            packed.shapes.insert(key, shape);
        }
        let mut brushes: Vec<(&u64, &Brush)> = old.brushes.iter().filter(|(key, _)| keep(**key)).collect();
        brushes.sort_by_key(|(_, b)| b.offset);
        for (&key, b) in brushes {
            let offset = packed.rows.len() as u32;
            packed.rows.extend_from_slice(&old.rows[b.offset as usize..(b.offset + b.count) as usize]);
            packed.brushes.insert(key, Brush { offset, count: b.count, see_through: b.see_through });
        }
        packed
    }

    /// A path: its control points (four per curve) and subpaths (its own curve ranges: first, end,
    /// closed), and (centroid, Newell area vector) of its control points.
    fn add_path(&mut self, key: u64, points: &[[f64; 3]], ranges: &[[u32; 4]], centroid: [f32; 3], area: [f32; 3]) {
        let count = (points.len() / 4) as u32;
        let first = self.push_curves(points, count as usize);
        let first_subpath = self.ranges.len() as u32;
        self.ranges.extend_from_slice(ranges);
        let flatness = points.chunks_exact(4).map(flatness).fold(0.0, f64::max) as f32;
        let curves = Curves { first, count, room: count, first_subpath, subpaths: ranges.len() as u32, flatness, miter: miter(points, ranges) };
        let (lo, hi) = points.iter().fold(([f32::MAX; 3], [f32::MIN; 3]), |(lo, hi), p| ([0, 1, 2].map(|i| lo[i].min(p[i] as f32)), [0, 1, 2].map(|i| hi[i].max(p[i] as f32))));
        let (plane, planar) = plane(points);
        self.shapes.insert(key, Shape { kind: Kind::Path, curves, base: 0, count: 0, raster: Raster::default(), centroid, area, lo, hi, middle: middle((lo, hi)), plane, planar });
    }

    /// Append curves to a path's last subpath (`closed`: whether it now ends where it begins),
    /// where it is when it has room, else after moving it to the end with room to grow. Older frames
    /// still draw their prefix: nothing written before changes.
    fn grow_path(&mut self, key: u64, tail: &[[f64; 3]], closed: bool) -> Result<(), String> {
        let s = self.shapes.get(&key).ok_or_else(|| format!("unknown shape {key}"))?;
        if s.kind != Kind::Path || s.curves.subpaths == 0 {
            return Err("only a path grows".into());
        }
        let (c, added) = (s.curves, (tail.len() / 4) as u32);
        let mut curves = c;
        if c.count + added > c.room {
            // move it to the end, with room: its old place is dead
            let room = (c.count + added).max(2 * c.count).max(64);
            let old: Vec<[f64; 3]> = self.points[4 * c.first as usize..4 * (c.first + c.count) as usize].to_vec();
            curves.first = self.push_curves(&old, room as usize);
            curves.room = room;
            self.dead += c.room as usize * CURVE_BYTES;
        }
        let at = 4 * (curves.first + curves.count) as usize;
        self.points[at..at + tail.len()].copy_from_slice(tail);
        for (k, p) in tail.chunks_exact(4).enumerate() {
            self.ctrl[at + 4 * k..at + 4 * k + 4].copy_from_slice(&gpu_curve(p));
        }
        self.dirty.push((5, at * 16..(at + tail.len()) * 16));
        let last = (curves.first_subpath + curves.subpaths - 1) as usize;
        self.ranges[last][1] += added;
        self.ranges[last][2] = closed as u32;
        self.dirty.push((6, last * 16..(last + 1) * 16));
        curves.count += added;
        let points = &self.points[4 * curves.first as usize..4 * (curves.first + curves.count) as usize];
        let ranges = &self.ranges[curves.first_subpath as usize..(curves.first_subpath + curves.subpaths) as usize];
        curves.flatness = curves.flatness.max(tail.chunks_exact(4).map(flatness).fold(0.0, f64::max) as f32);
        curves.miter = miter(points, ranges);
        let s = self.shapes.get_mut(&key).expect("present");
        (s.lo, s.hi) = tail.iter().fold((s.lo, s.hi), |(lo, hi), p| ([0, 1, 2].map(|i| lo[i].min(p[i] as f32)), [0, 1, 2].map(|i| hi[i].max(p[i] as f32))));
        s.curves = curves;
        Ok(())
    }

    fn add_points(&mut self, key: u64, vertices: &[[f32; 4]]) {
        let base = self.push_vertices(vertices, None);
        let start = self.indices.len() as u32;
        self.indices.extend((0..vertices.len() as u32).flat_map(|i| (0..6).map(move |corner| ((base + i) << 3) | corner)));
        let count = vertices.len() as u32;
        self.add_raster(key, Kind::Points, vertices, base, Raster { count, fill: start..start, stroke: start..self.indices.len() as u32 });
    }

    /// A mesh, drawn triangle by triangle; with `outline` > 2 face by face: its vertices are
    /// blocks of `block` (a surface's faces), each beginning with a closed loop of `outline` (the
    /// last repeating the first) — the face's edges, stroked like a path's — and its triangles
    /// are the faces' own, face after face.
    #[allow(clippy::too_many_arguments)]
    fn add_mesh(&mut self, key: u64, vertices: &[[f32; 4]], extras: &[[f32; 4]], triangles: &[u32], outline: u32, block: u32) {
        let base = self.push_vertices(vertices, Some(extras));
        let start = self.indices.len() as u32;
        self.indices.extend(triangles.iter().map(|&i| i + base));
        let end = self.indices.len() as u32;
        if outline > 2 {
            for first in (0..vertices.len() as u32).step_by(block as usize).map(|k| base + k) {
                let last = first + outline - 1; // repeats `first`: joints wrap around it
                self.links.extend((first..=last).map(|v| [if v == first { last - 1 } else { v - 1 }, if v == last { first + 1 } else { v + 1 }]));
                self.links.extend((last + 1..first + block).map(|v| [v, v])); // the face's inside
                self.indices.extend((first..last).flat_map(|v| (0..6).map(move |corner| (v << 3) | corner)));
            }
        }
        let count = if outline > 2 { vertices.len() as u32 / block } else { (triangles.len() / 3) as u32 };
        self.add_raster(key, Kind::Mesh, vertices, base, Raster { count, fill: start..end, stroke: end..self.indices.len() as u32 });
    }

    /// A point cloud or mesh, its vertices stored from `base` and its index codes `raster` (a
    /// vertex without neighbours links nowhere).
    fn add_raster(&mut self, key: u64, kind: Kind, vertices: &[[f32; 4]], base: u32, raster: Raster) {
        self.links.resize(self.vertices.len(), [0, 0]);
        let (lo, hi) = bounds(vertices);
        let n = vertices.len().max(1) as f32;
        let centroid = [0, 1, 2].map(|k| vertices.iter().map(|v| v[k]).sum::<f32>() / n);
        self.shapes.insert(key, Shape { kind, curves: Curves::default(), base, count: vertices.len() as u32, raster, centroid, area: [0.0; 3], lo, hi, middle: middle((lo, hi)), plane: [[0.0; 3]; 3], planar: true });
    }

    fn add_rows(&mut self, key: u64, rows: &[[f32; 4]]) {
        let offset = self.rows.len() as u32;
        self.rows.extend_from_slice(rows);
        self.brushes.insert(key, Brush { offset, count: rows.len() as u32, see_through: rows.iter().any(|r| r[3] < 1.0) });
    }
}

fn affine(m: &Mat34, p: [f32; 3]) -> [f32; 3] {
    [0, 1, 2].map(|i| m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3])
}

fn project(p: &Mat4, x: [f32; 3]) -> [f32; 4] {
    [0, 1, 2, 3].map(|i| p[i][0] * x[0] + p[i][1] * x[1] + p[i][2] * x[2] + p[i][3])
}

/// Items in the order of their keys, stably: a counting pass per byte of the key, lowest first.
fn radix_sort<T: Copy>(mut items: Vec<(u32, T)>) -> Vec<(u32, T)> {
    let mut sorted = items.clone();
    for shift in [0, 8, 16, 24] {
        let mut starts = [0usize; 256];
        for (key, _) in &items {
            starts[((key >> shift) & 0xff) as usize] += 1;
        }
        let mut at = 0;
        for start in &mut starts {
            (*start, at) = (at, at + *start);
        }
        for &item in &items {
            let byte = ((item.0 >> shift) & 0xff) as usize;
            sorted[starts[byte]] = item;
            starts[byte] += 1;
        }
        std::mem::swap(&mut items, &mut sorted);
    }
    items
}

/// The clip matrix of a blend term: camera · [M; 0 0 0 1]; only the first term carries the
/// camera's own translation (the terms add up to one point).
fn compose(p: &Mat4, m: &Mat34, first: bool) -> Mat4 {
    [0, 1, 2, 3].map(|r| {
        [0, 1, 2, 3].map(|c| p[r][0] * m[0][c] + p[r][1] * m[1][c] + p[r][2] * m[2][c] + if c == 3 && first { p[r][3] } else { 0.0 })
    })
}

/// The cofactor of a matrix's linear part applied to a normal: how area vectors transform.
fn carry(m: &Mat34, n: [f32; 3]) -> [f32; 3] {
    let r = [0, 1, 2].map(|i| [m[i][0], m[i][1], m[i][2]]);
    [dot(cross(r[1], r[2]), n), dot(cross(r[2], r[0]), n), dot(cross(r[0], r[1]), n)]
}

/// The center of `shape`'s bounds, mapped by `m` (an affine map keeps a box's center its center).
fn world_center(shape: &Shape, m: &Mat34) -> [f32; 3] {
    affine(m, shape.middle)
}

/// CE's light: half the cube of the cosine toward the light, halved again when facing away, on the side seen from
/// `seen` (a direction from the point toward the viewer).
fn shade(normal: [f32; 3], point: [f32; 3], light: [f32; 3], seen: [f32; 3]) -> f32 {
    let length = dot(normal, normal).sqrt();
    let to_light = sub(light, point);
    let distance = dot(to_light, to_light).sqrt();
    if length < 1e-12 || distance < 1e-12 {
        return 0.0;
    }
    let facing = if dot(seen, normal) < 0.0 { -1.0 } else { 1.0 };
    let cosine = facing * dot(normal, to_light) / (length * distance);
    let amount = 0.5 * cosine.powi(3);
    if amount < 0.0 { amount * 0.5 } else { amount }
}

fn lighten(c: [f32; 4], amount: f32) -> [f32; 4] {
    [(c[0] + amount).clamp(0.0, 1.0), (c[1] + amount).clamp(0.0, 1.0), (c[2] + amount).clamp(0.0, 1.0), c[3]]
}

/// sRGB → OKLab, as the shader's `oklab` (the published matrices, as the shader and Python
/// have them: f32 rounds them alike).
#[allow(clippy::excessive_precision)]
fn oklab(c: [f32; 4]) -> [f32; 3] {
    let l = [c[0], c[1], c[2]].map(|x| if x <= 0.04045 { x / 12.92 } else { ((x + 0.055) / 1.055).powf(2.4) });
    let lms = [
        0.4122214708 * l[0] + 0.5363325363 * l[1] + 0.0514459929 * l[2],
        0.2119034982 * l[0] + 0.6806995451 * l[1] + 0.1073969566 * l[2],
        0.0883024619 * l[0] + 0.2817188376 * l[1] + 0.6299787005 * l[2],
    ]
    .map(f32::cbrt);
    [
        0.2104542553 * lms[0] + 0.7936177850 * lms[1] - 0.0040720468 * lms[2],
        1.9779984951 * lms[0] - 2.4285922050 * lms[1] + 0.4505937099 * lms[2],
        0.0259040371 * lms[0] + 0.7827717662 * lms[1] - 0.8086757660 * lms[2],
    ]
}

/// OKLab → sRGB, as the shader's `srgb`.
#[allow(clippy::excessive_precision)]
fn srgb(lab: [f32; 3]) -> [f32; 3] {
    let r = [
        lab[0] + 0.3963377774 * lab[1] + 0.2158037573 * lab[2],
        lab[0] - 0.1055613458 * lab[1] - 0.0638541728 * lab[2],
        lab[0] - 0.0894841775 * lab[1] - 1.2914855480 * lab[2],
    ]
    .map(|x| x * x * x);
    [
        4.0767416621 * r[0] - 3.3077115913 * r[1] + 0.2309699292 * r[2],
        -1.2684380046 * r[0] + 2.6097574011 * r[1] - 0.3413193965 * r[2],
        -0.0041960863 * r[0] - 0.7034186147 * r[1] + 1.7076147010 * r[2],
    ]
    .map(|x| {
        let l = x.clamp(0.0, 1.0);
        if l <= 0.0031308 { 12.92 * l } else { 1.055 * l.powf(1.0 / 2.4) - 0.055 }
    })
}

/// Color a → b at t, as every color in ManimGX mixes (the shader's `mix_rgba`, Python's
/// `mix_rgba`): OKLab weighted by opacity; exactly a at 0, b at 1.
fn mix_rgba(a: [f32; 4], b: [f32; 4], t: f32) -> [f32; 4] {
    if t <= 0.0 || a == b {
        return a;
    }
    if t >= 1.0 {
        return b;
    }
    let (wa, wb) = (a[3] * (1.0 - t), b[3] * t);
    let opacity = wa + wb;
    if a[..3] == b[..3] {
        return [a[0], a[1], a[2], opacity];
    }
    let (la, lb) = (oklab(a), oklab(b));
    let lab = [0, 1, 2].map(|i| if opacity > 1e-9 { (la[i] * wa + lb[i] * wb) / opacity } else { la[i] + (lb[i] - la[i]) * t });
    let [r, g, b] = srgb(lab);
    [r, g, b, opacity]
}

/// The view as Python sends it, read once per frame.
pub(crate) struct Camera {
    projection: Mat4,
    overlay: Mat4,
    pub(crate) size: [f32; 2],
    unit: f32, // pixels per scene unit (stroke widths arrive in scene units: a record is the camera's business only here)
    light: [f32; 3],
    three_d: bool,
    toward: [f32; 3],
    eye: [f32; 4], // where it sees from (w = 1: a 3D view's perspective; else it sees along `toward` from everywhere)
    bias: f32, // the share of a depth within which a path lies on the raster base (a few of the depth's f32 steps)
    far: [f32; 4], // its depth from the far plane as a row of its projection: -z (a view's: reversed Z), z - w (`far_row`)
}

/// A standard-Z projection's depth measured from its far plane, z - w (clip's), as a row (a light's: a view's own is
/// reversed, its depth from the far plane -z): where its row z is a multiple of row w plus a constant (a perspective's,
/// z = a w + b), (a - 1) w + b, which keeps the depth's every digit where z / w is near 1 (one f32 ulp there is half a
/// thousandth of a unit at twenty units away; subtracting near-equal rows would lose them); else row z minus row w.
fn far_row(p: &Mat4) -> [f32; 4] {
    let [z, w] = [p[2], p[3]].map(|r| r.map(|x| x as f64));
    let i = (0..3).max_by(|&i, &j| w[i].abs().total_cmp(&w[j].abs())).expect("a column");
    if w[i].abs() > 1e-12 {
        let a = z[i] / w[i];
        if (0..3).all(|j| (z[j] - a * w[j]).abs() <= 1e-6 * (z[j].abs() + w[j].abs()) + 1e-12) {
            let b = z[3] - a * w[3];
            return [0, 1, 2, 3].map(|j| ((a - 1.0) * w[j] + if j == 3 { b } else { 0.0 }) as f32);
        }
    }
    [0, 1, 2, 3].map(|j| (z[j] - w[j]) as f32)
}

impl Camera {
    pub(crate) fn new(view: &[f32]) -> Self {
        let matrix = |at: usize| -> Mat4 { [0, 1, 2, 3].map(|r| [0, 1, 2, 3].map(|c| view[at + c * 4 + r])) };
        Self {
            far: matrix(0)[2].map(|x| -x), // (reversed Z: z / w is NEAR / distance, 0 at infinity)
            projection: matrix(0),
            overlay: matrix(16),
            size: [view[32], view[33]],
            unit: view[34],
            light: [view[36], view[37], view[38]],
            three_d: view[39] > 0.5,
            toward: [view[40], view[41], view[42]],
            eye: [0, 1, 2, 3].map(|k| view[VIEW_LIGHTING + k]),
            bias: view[43],
        }
    }

    /// A light's shadow map as a camera: what plans the paths' shadows (seen from the light, toward it).
    fn seen_from(s: &shadow::Shadow) -> Self {
        let projection: Mat4 = std::array::from_fn(|i| std::array::from_fn(|j| s.matrix[j][i]));
        Self {
            far: far_row(&projection),
            projection,
            overlay: [[0.0; 4]; 4],
            size: [shadow::SIZE as f32; 2],
            unit: s.unit,
            light: s.toward,
            three_d: true,
            toward: s.toward,
            eye: [0.0; 4], // (what its paths cast is their depth alone: no light)
            bias: 0.0,
        }
    }

    /// From a point in the scene toward the viewer: toward its eye in a 3D view's perspective, else its direction.
    fn toward_viewer(&self, p: [f32; 3]) -> [f32; 3] {
        if self.eye[3] > 0.5 { sub([self.eye[0], self.eye[1], self.eye[2]], p) } else { self.toward }
    }

    fn pixels(&self, c: [f32; 4]) -> [f32; 2] {
        [(c[0] / c[3] * 0.5 + 0.5) * self.size[0], (c[1] / c[3] * 0.5 + 0.5) * self.size[1]]
    }

    /// The camera an object is seen through: the view, or the frame (fixed in frame: in front of
    /// everything, at depth 1, the near plane's).
    fn eye(&self, r: &Record) -> Mat4 {
        if r.flags & OVERLAY == 0 {
            return self.projection;
        }
        let mut eye = self.overlay;
        eye[2] = eye[3];
        eye
    }

    /// Where a point of the world shows on the view: its pixel (x, y from the top left) and its depth (z / w from the
    /// far plane: `far`), to the double's digits.
    fn seen(&self, p: [f64; 3]) -> [f64; 3] {
        let row = |r: [f32; 4]| r[0] as f64 * p[0] + r[1] as f64 * p[1] + r[2] as f64 * p[2] + r[3] as f64;
        let w = row(self.projection[3]);
        let (x, y) = (row(self.projection[0]) / w, row(self.projection[1]) / w);
        [(x * 0.5 + 0.5) * self.size[0] as f64, (0.5 - y * 0.5) * self.size[1] as f64, row(self.far) / w]
    }

    /// The camera an object is seen through, its row z its depth from the far plane (z - w: `far`).
    fn deep_eye(&self, r: &Record) -> Mat4 {
        let mut eye = self.eye(r);
        eye[2] = if r.flags & OVERLAY == 0 { self.far } else { eye[3].map(|x| -x) };
        eye
    }
}

impl Store {
    /// Vertex `vertex` of an instance's shape in clip space, as `clip` in `blend.wgsl` places it.
    fn clip(&self, instance: &Instance, vertex: u32) -> [f32; 4] {
        let at = |k: u32| {
            let v = self.vertices[k as usize];
            [v[0], v[1], v[2]]
        };
        let c = project(&instance.c1, at(vertex));
        if instance.ids[1] == NONE {
            return c;
        }
        let d = project(&instance.c2, at(instance.ids[1] + vertex - instance.ids[0]));
        [0, 1, 2, 3].map(|i| c[i] + d[i])
    }

    /// A record's box in the world (low, high corners): its shape's corners through its placement, a morph's two
    /// terms' boxes added (term 2 carries no translation).
    fn world_box(&self, r: &Record) -> Result<Box3, String> {
        let bound = |key: u64, m: &Mat34, translate: bool| -> Result<Box3, String> {
            let shape = self.shapes.get(&key).ok_or_else(|| format!("unknown shape {key}"))?;
            let mut out = [[f32::MAX; 3], [f32::MIN; 3]];
            for k in 0..8 {
                let p = [0, 1, 2].map(|i| if k >> i & 1 == 0 { shape.lo[i] } else { shape.hi[i] });
                for (i, row) in m.iter().enumerate() {
                    let q = row[0] * p[0] + row[1] * p[1] + row[2] * p[2] + if translate { row[3] } else { 0.0 };
                    (out[0][i], out[1][i]) = (out[0][i].min(q), out[1][i].max(q));
                }
            }
            Ok(out)
        };
        let mut b = bound(r.key1, &r.m1, true)?;
        if r.key2 != 0 {
            let t = bound(r.key2, &r.m2, false)?;
            b = [std::array::from_fn(|i| b[0][i] + t[0][i]), std::array::from_fn(|i| b[1][i] + t[1][i])];
        }
        Ok(b)
    }

    /// Where on a view a record can paint: its shape's bounds seen through its eye, grown by what
    /// reaches past the geometry (miter joins, antialiasing, point disks) — in pixels, rows from
    /// the top. None: it cannot be bounded (behind the camera, a morph in 3D).
    pub(crate) fn footprint(&self, camera: &Camera, r: &Record) -> Option<[f32; 4]> {
        let a = self.shapes.get(&r.key1)?;
        let eye = camera.eye(r);
        let corners = |shape: &Shape| {
            let (lo, hi) = (shape.lo, shape.hi);
            (0..8).map(move |k| [0, 1, 2].map(|i| if k >> i & 1 == 0 { lo[i] } else { hi[i] }))
        };
        let (mut lo, mut hi) = ([f32::MAX; 2], [f32::MIN; 2]);
        let mut nearest = 1.0f32; // the largest 1/w: how much a pixel-sized margin grows with perspective
        if r.key2 == 0 {
            let c = compose(&eye, &r.m1, true);
            for p in corners(a) {
                let q = project(&c, p);
                if q[3] <= 1e-6 {
                    return None;
                }
                nearest = nearest.max(1.0 / q[3]);
                let px = camera.pixels(q);
                lo = [lo[0].min(px[0]), lo[1].min(px[1])];
                hi = [hi[0].max(px[0]), hi[1].max(px[1])];
            }
        } else {
            if camera.three_d {
                return None;
            }
            // in 2D, w is 1 for the whole blend: bound each term in clip x, y and add the bounds
            let b = self.shapes.get(&r.key2)?;
            let bound = |c: &Mat4, shape: &Shape| {
                corners(shape).fold(([f32::MAX; 2], [f32::MIN; 2]), |(l, h), p| {
                    let q = project(c, p);
                    ([l[0].min(q[0]), l[1].min(q[1])], [h[0].max(q[0]), h[1].max(q[1])])
                })
            };
            let ((l1, h1), (l2, h2)) = (bound(&compose(&eye, &r.m1, true), a), bound(&compose(&eye, &r.m2, false), b));
            lo = camera.pixels([l1[0] + l2[0], l1[1] + l2[1], 0.0, 1.0]);
            hi = camera.pixels([h1[0] + h2[0], h1[1] + h2[1], 0.0, 1.0]);
        }
        let scale = (eye[0][0] * eye[0][0] + eye[0][1] * eye[0][1] + eye[0][2] * eye[0][2]).sqrt() * camera.size[0] / 2.0;
        let margin = r.params[2].max(r.params[3]) * camera.unit * 5.0 + r.gradient_a[3] * scale * nearest + 2.0; // miter limit 10; disks; antialiasing
        Some([lo[0] - margin, camera.size[1] - hi[1] - margin, hi[0] + margin, camera.size[1] - lo[1] + margin])
    }

    /// CE's light on a record in a 3D view: a lit path's, once for its whole area at its centroid, on the side the eye
    /// sees there (fixed in the frame: the side toward the view); none for anything else (a mesh is lit per vertex).
    pub(crate) fn light(&self, camera: &Camera, r: &Record) -> Result<f32, String> {
        if !camera.three_d || r.flags & LIT == 0 {
            return Ok(0.0);
        }
        let a = self.shapes.get(&r.key1).ok_or_else(|| format!("unknown shape {}", r.key1))?;
        if a.kind != Kind::Path {
            return Ok(0.0);
        }
        let (mut centroid, mut area) = (affine(&r.m1, a.centroid), carry(&r.m1, a.area));
        if r.key2 != 0 {
            let b = self.shapes.get(&r.key2).ok_or_else(|| format!("unknown shape {}", r.key2))?;
            let (c2, n2) = (affine(&r.m2, b.centroid), carry(&r.m2, b.area));
            centroid = [0, 1, 2].map(|i| centroid[i] + c2[i]);
            area = [0, 1, 2].map(|i| area[i] + n2[i]);
        }
        let seen = if r.flags & OVERLAY != 0 { camera.toward } else { camera.toward_viewer(centroid) };
        Ok(shade(area, centroid, camera.light, seen))
    }

    /// A record's paint, seen through `eye` (see `Paint`); its solid colors unlit.
    fn paint(&self, camera: &Camera, eye: &Mat4, r: &Record) -> Result<Paint, String> {
        let brush = |key: u64| if key == 0 { Ok(None) } else { self.brushes.get(&key).map(Some).ok_or_else(|| format!("unknown brush {key}")) };
        let (fill_rows, stroke_rows) = (brush(r.fill_rows)?, brush(r.stroke_rows)?);
        // paint 2's rows, where they match paint 1's in number (else paint 1's)
        let second = |rows: Option<&Brush>, key: u64| Ok::<_, String>(brush(key)?.filter(|b| rows.is_some_and(|a| a.count == b.count)).or(rows).map_or(0, |b| b.offset));
        let (fill2, stroke2) = (second(fill_rows, r.fill_rows2)?, second(stroke_rows, r.stroke_rows2)?);
        let ((fo, fc), (so, sc)) = (fill_rows.map_or((0, 0), |b| (b.offset, b.count)), stroke_rows.map_or((0, 0), |b| (b.offset, b.count)));
        let mix = r.dash[3];
        let solid = |a: [f32; 4], b: [f32; 4], count: u32| {
            let c = mix_rgba(a, b, mix);
            if count > 1 { [c[0], c[1], c[2], -1.0] } else { c }
        };
        let mut gradient = [0.0; 4];
        if fc > 1 || sc > 1 {
            let from = camera.pixels(project(eye, [r.gradient_a[0], r.gradient_a[1], r.gradient_a[2]]));
            let to = camera.pixels(project(eye, [r.gradient_b[0], r.gradient_b[1], r.gradient_b[2]]));
            let d = [to[0] - from[0], to[1] - from[1]];
            let length2 = (d[0] * d[0] + d[1] * d[1]).max(f32::MIN_POSITIVE);
            gradient = [from[0], from[1], d[0] / length2, d[1] / length2];
        }
        Ok(Paint {
            fill: solid(r.fill, r.fill2, fc),
            stroke: solid(r.stroke, r.stroke2, sc),
            background: mix_rgba(r.background, r.background2, mix),
            gradient,
            brush: [fo, fc, so, sc],
            brush2: [fill2, stroke2, if fill2 == fo && stroke2 == so { 0 } else { mix.to_bits() }, (r.flags >> STYLE) as u32 & 15],
        })
    }
}

/// A point cloud or mesh as the raster pipeline draws it.
struct Draw {
    kind: Kind,
    fill: Range<u32>,
    stroke: Range<u32>,
    texture: u64,
    stroked: bool, // its faces' edges show (a mesh's)
    stroke_gradient: bool,
    overlay: bool,          // fixed in the frame: drawn over the view
    see_through: [bool; 2], // which of its layers show and can be seen through: its points or triangles, its edges
    lit: bool,              // a mesh with a material, in a 3D view: its light kept apart (`blend.wgsl`'s `Base`)
}

impl Draw {
    /// In a 3D view, its see-through layers go to the lists (a point cloud's are sprites).
    fn listed(&self) -> bool {
        !self.overlay && self.kind != Kind::Points && self.see_through.contains(&true)
    }

    /// In a 3D view, its points are sprites: see-through, blended far to near.
    fn sprites(&self) -> bool {
        !self.overlay && self.kind == Kind::Points && self.see_through[0]
    }
}

/// Which of a view's layers a pass over its draws draws.
#[derive(Clone, Copy, PartialEq)]
enum Phase {
    All,        // everything, as given (2D views; 3D views where nothing can be seen through)
    Opaque,     // a 3D view's opaque layers
    SeeThrough, // its listed see-through layers, appended to the lists
    Overlay,    // what is fixed in the frame, over the composited view
}

/// A layer's passes: coverage counted into the stencil, then covered once where counted.
struct Passes {
    count: wgpu::RenderPipeline,
    cover: wgpu::RenderPipeline,
}

/// The raster pipeline: point clouds and meshes (a 3D view's base, a 2D view's layers).
struct Pipelines {
    stroke: [Passes; 2], // a mesh's faces' edges: [solid, gradient]
    points: wgpu::RenderPipeline,
    sprites: wgpu::RenderPipeline, // a 3D view's see-through points, blended in the order listed
    mesh: wgpu::RenderPipeline,
    appends: Appends,
}

/// A 3D view's listed see-through layers, each appending its fragments to the lists once (see
/// `blend.wgsl`; its composite resolves them), and its sprites among its see-through layers (see
/// `blend_lists.wgsl`): blended into the base where none lies behind them, else into their slabs.
struct Appends {
    stroke: [wgpu::RenderPipeline; 2],
    mesh: wgpu::RenderPipeline,
    sprites: wgpu::RenderPipeline,
    slabs: wgpu::RenderPipeline,
}

pub(crate) struct Gpu {
    #[cfg(feature = "player")]
    pub(crate) instance: wgpu::Instance, // a canvas's or a window's surface is made from it
    #[cfg(feature = "player")]
    pub(crate) adapter: wgpu::Adapter, // what a window's or a canvas's surface can be configured with
    pub(crate) device: wgpu::Device,
    pub(crate) queue: wgpu::Queue,
    raster: RasterLayouts,
    image_layout: wgpu::BindGroupLayout,
    sampler: wgpu::Sampler,
    pipelines: HashMap<(u32, bool), Pipelines>, // by sample count and whether lit meshes' light is kept apart, made when first drawn with
    max_samples: u32,
    vector: vector::Vector,
    shadow_compare: wgpu::Sampler, // a shadow map's depth compared with a surface's, bilinearly
    dfg: wgpu::TextureView,        // the DFG table a lit surface's specular albedo is read from (`dfg.bin`)
    linear: wgpu::Sampler,         // its reads (and an environment's cube's): trilinear, clamped
    no_environment: wgpu::TextureView, // a cube where a frame has no environment: 1x1, dark
    prefilter: Option<environment::Prefilter>, // made when a frame first shows an environment
    occlusion: Option<occlusion::Occlusion>, // a 3D view's ambient occlusion's passes, made when a view first has it
    no_occlusion: wgpu::TextureView,         // what a view without it binds in its place: 1x1
    bloom: Option<bloom::Bloom>,             // a 3D view's bloom's passes, made when a view first has it
    blend: [Option<wgpu::ShaderModule>; 2], // single/multisample texture forms (the shadow passes share either)
    shadow_passes: HashMap<usize, wgpu::RenderPipeline>, // by the light's slot in its view, made when first cast
}

#[cfg(not(target_arch = "wasm32"))]
static GPU: std::sync::OnceLock<Result<std::sync::Mutex<Gpu>, String>> = std::sync::OnceLock::new();

/// Run `f` with the GPU, brought up the first time it is needed (blocking on it).
#[cfg(not(target_arch = "wasm32"))]
pub(crate) fn with_gpu<T>(f: impl FnOnce(&mut Gpu) -> T) -> Result<T, String> {
    let gpu = GPU.get_or_init(|| pollster::block_on(Gpu::new()).map(std::sync::Mutex::new)).as_ref()?;
    let mut guard = gpu.lock().map_err(|_| "GPU mutex poisoned".to_string())?;
    Ok(f(&mut guard))
}

// In the browser a GPU comes up asynchronously, once, before anything draws (`web::init`).
#[cfg(target_arch = "wasm32")]
thread_local! {
    pub(crate) static GPU: std::cell::RefCell<Option<Gpu>> = const { std::cell::RefCell::new(None) };
}

/// Run `f` with the GPU (in the browser: brought up by `web::init`).
#[cfg(target_arch = "wasm32")]
pub(crate) fn with_gpu<T>(f: impl FnOnce(&mut Gpu) -> T) -> Result<T, String> {
    GPU.with_borrow_mut(|gpu| gpu.as_mut().map(f).ok_or_else(|| "the GPU is not up: await init() first".to_string()))
}

/// A shader: `source` after the paint both pipelines share and how light shows (`paint.wgsl`, `tone.wgsl`).
fn shader(device: &wgpu::Device, label: &str, source: &str) -> wgpu::ShaderModule {
    let source = [include_str!("paint.wgsl"), include_str!("tone.wgsl"), source].concat();
    device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some(label), source: wgpu::ShaderSource::Wgsl(source.into()) })
}

/// One compositing algorithm; only its texture types differ at one sample. `textureLoad`'s
/// last argument then names mip zero instead of sample zero.
fn sampled_shader(device: &wgpu::Device, label: &str, source: &str, multisampled: bool) -> wgpu::ShaderModule {
    let kind = if multisampled { "multisampled_2d" } else { "2d" };
    shader(device, label, &format!("alias SampleColor = texture_{kind}<f32>;\nalias SampleDepth = texture_depth_{kind};\n{source}"))
}

fn entry(binding: u32, ty: wgpu::BindingType) -> wgpu::BindGroupLayoutEntry {
    wgpu::BindGroupLayoutEntry { binding, visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT, ty, count: None }
}

fn storage(binding: u32) -> wgpu::BindGroupLayoutEntry {
    entry(binding, wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None })
}

/// How a pass uses the stencil: count a stroke's coverage, cover once where visible (zeroing it
/// only when depth passes), or leave it alone.
#[derive(Clone, Copy)]
enum Stencil {
    Coverage,
    Cover,
    Ignore,
}

/// Whether an adapter blends float32 targets (a view adds its coverage in one), as it says of the format itself (the
/// WebGPU feature).
pub(crate) fn blends_float32(adapter: &wgpu::Adapter) -> bool {
    adapter.get_texture_format_features(wgpu::TextureFormat::R32Float).flags.contains(wgpu::TextureFormatFeatureFlags::BLENDABLE)
}

/// An instance's high-performance adapter: float32 coverage blending and floating-point depth
/// with stencil, which its reversed-Z projection and stroke coverage require.
async fn adapter(instance: &wgpu::Instance) -> Result<wgpu::Adapter, String> {
    let adapter = instance
        .request_adapter(&wgpu::RequestAdapterOptions { power_preference: wgpu::PowerPreference::HighPerformance, ..Default::default() })
        .await
        .map_err(|e| {
            let driver = if cfg!(target_os = "linux") { "; with no GPU driver, Mesa's lavapipe draws on the CPU (Debian, Ubuntu: apt install mesa-vulkan-drivers)" } else { "" };
            format!("no GPU adapter: {e}{driver}")
        })?;
    if !blends_float32(&adapter) {
        return Err("the GPU cannot blend float32 targets (a view adds its coverage in one)".into());
    }
    if !adapter.features().contains(wgpu::Features::DEPTH32FLOAT_STENCIL8) {
        return Err("the GPU cannot use float32 depth with stencil (reversed-Z depth needs floating-point precision)".into());
    }
    Ok(adapter)
}

impl Gpu {
    /// The system's GPU, WebGPU's (Metal, Vulkan, DX12, the browser's): its device, and what draws on it.
    pub(crate) async fn new() -> Result<Self, String> {
        // the system's adapter; where none will do, the lavapipe a Linux wheel bundles
        let descriptor = wgpu::InstanceDescriptor { backends: wgpu::Backends::PRIMARY, ..wgpu::InstanceDescriptor::new_without_display_handle() };
        #[cfg(windows)]
        let descriptor = wgpu::InstanceDescriptor {
            backend_options: wgpu::BackendOptions { dx12: wgpu::Dx12BackendOptions { shader_compiler: dxc::compiler()?, ..Default::default() }, ..descriptor.backend_options },
            ..descriptor
        };
        let instance = wgpu::Instance::new(descriptor);
        #[cfg(target_arch = "wasm32")]
        let adapter = adapter(&instance).await?;
        #[cfg(not(target_arch = "wasm32"))]
        let (instance, adapter) = match adapter(&instance).await {
            Ok(adapter) => (instance, adapter),
            Err(error) => match lavapipe::instance() {
                Ok(Some(lavapipe)) => {
                    let adapter = adapter(&lavapipe).await.map_err(|e| format!("{error}; the bundled lavapipe: {e}"))?;
                    (lavapipe, adapter)
                }
                Ok(None) => return Err(error),
                Err(e) => return Err(format!("{error}; the bundled lavapipe: {e}")),
            },
        };
        // kept where surfaces are made (a canvas's, a window's): from the instance of the adapter
        #[cfg(not(feature = "player"))]
        drop(instance);
        let specific = wgpu::Features::TEXTURE_ADAPTER_SPECIFIC_FORMAT_FEATURES;
        let required_features = (adapter.features() & (specific | wgpu::Features::FLOAT32_BLENDABLE)) | wgpu::Features::DEPTH32FLOAT_STENCIL8;
        let (device, queue) = adapter
            .request_device(&wgpu::DeviceDescriptor {
                label: Some("manimgx"),
                required_features,
                required_limits: adapter.limits(),
                experimental_features: wgpu::ExperimentalFeatures::disabled(),
                memory_hints: wgpu::MemoryHints::Performance,
                trace: wgpu::Trace::Off,
            })
            .await
            .map_err(|e| format!("no GPU device: {e}"))?;
        let both = adapter.get_texture_format_features(COLOR).flags & adapter.get_texture_format_features(DEPTH).flags;
        let max_samples = if !required_features.contains(specific) {
            4
        } else {
            [(wgpu::TextureFormatFeatureFlags::MULTISAMPLE_X8, 8), (wgpu::TextureFormatFeatureFlags::MULTISAMPLE_X4, 4)]
                .into_iter()
                .find(|(flag, _)| both.contains(*flag))
                .map_or(1, |(_, n)| n)
        };
        let image_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("image"),
            entries: &[
                entry(0, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }),
                entry(1, wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering)),
            ],
        });
        let vector = vector::Vector::new(&device, &queue);
        let layout = |label, entries: &[wgpu::BindGroupLayoutEntry]| device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some(label), entries });
        // each raster pass's view: one buffer, bound at the pass's offset
        let view = entry(0, wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: true, min_binding_size: wgpu::BufferSize::new(VIEW_BYTES) });
        // the view's lights' shadow maps, and how they are compared
        let maps = entry(0, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Depth, view_dimension: wgpu::TextureViewDimension::D2Array, multisampled: false });
        let compare = entry(1, wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Comparison));
        // and the DFG table, bilinearly
        let dfg = entry(2, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let linear = entry(3, wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering));
        // and the view's environment's cube (`environment.rs`), and its ambient occlusion (`occlusion.rs`)
        let cube = entry(4, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: true }, view_dimension: wgpu::TextureViewDimension::Cube, multisampled: false });
        let occlusion = entry(5, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let shadows = layout("lighting", &[maps, compare, dfg, linear, cube, occlusion]);
        // the scene's arrays; a 3D view's see-through lists, written (with the opaque depth), and its slab bounds
        let written = |binding| wgpu::BindGroupLayoutEntry { binding, visibility: wgpu::ShaderStages::FRAGMENT, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None };
        let depth = [false, true].map(|multisampled| entry(3, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Depth, view_dimension: wgpu::TextureViewDimension::D2, multisampled }));
        let bounds = entry(0, wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false });
        let lists = depth.map(|depth| layout("append", &[written(0), written(1), written(2), depth]));
        let slabs = depth.map(|depth| [layout("slab bounds", &[bounds]), layout("slab bounds and depth", &[bounds, depth])]);
        let raster = RasterLayouts { scene: layout("scene", &[view, storage(1), storage(2), storage(4), storage(5), storage(6), storage(7)]), lists, slabs, shadows };
        let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            label: Some("image"),
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            ..Default::default()
        });
        let shadow_compare = device.create_sampler(&wgpu::SamplerDescriptor {
            label: Some("shadow"),
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            compare: Some(wgpu::CompareFunction::LessEqual),
            ..Default::default()
        });
        // the split sum's DFG terms (with the multiple-scattering term: scripts/engine/dfg_table.py), NoV across,
        // perceptual roughness down: 64 KB, made once
        let size = wgpu::Extent3d { width: 128, height: 128, depth_or_array_layers: 1 };
        let table = device.create_texture(&wgpu::TextureDescriptor { label: Some("dfg"), size, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: wgpu::TextureFormat::Rg16Float, usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST, view_formats: &[] });
        queue.write_texture(table.as_image_copy(), include_bytes!("dfg.bin"), wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(128 * 4), rows_per_image: Some(128) }, size);
        let dfg = table.create_view(&Default::default());
        let linear = device.create_sampler(&wgpu::SamplerDescriptor { label: Some("linear"), mag_filter: wgpu::FilterMode::Linear, min_filter: wgpu::FilterMode::Linear, mipmap_filter: wgpu::MipmapFilterMode::Linear, ..Default::default() });
        let no_environment = device
            .create_texture(&wgpu::TextureDescriptor { label: Some("no environment"), size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 6 }, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: wgpu::TextureFormat::Rgba16Float, usage: wgpu::TextureUsages::TEXTURE_BINDING, view_formats: &[] })
            .create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::Cube), ..Default::default() });
        let no_occlusion = device
            .create_texture(&wgpu::TextureDescriptor { label: Some("no occlusion"), size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 }, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: wgpu::TextureFormat::R32Float, usage: wgpu::TextureUsages::TEXTURE_BINDING, view_formats: &[] })
            .create_view(&Default::default());
        Ok(Self {
            #[cfg(feature = "player")]
            instance,
            #[cfg(feature = "player")]
            adapter,
            device, queue, raster, image_layout, sampler, pipelines: HashMap::new(), max_samples, vector, shadow_compare, dfg, linear, no_environment, prefilter: None, occlusion: None, no_occlusion, bloom: None, blend: [None, None], shadow_passes: HashMap::new() })
    }

    /// The raster pipeline's passes at `samples`, made when a view first draws rasters with them.
    /// Every pass tests depth and lets equal depth pass (a stroke lies on its own fill; within an
    /// object, later parts draw over earlier ones); `write` ones write it.
    fn pipelines(&mut self, samples: u32, light: bool) {
        if self.pipelines.contains_key(&(samples, light)) {
            return;
        }
        use wgpu::{CompareFunction as C, StencilOperation as Op};
        let device = &self.device;
        // the body, and its reads: from storage buffers, with the see-through lists
        let raster = &self.raster;
        let parts = [include_str!("blend.wgsl"), include_str!("light.wgsl"), include_str!("blend_buffers.wgsl"), include_str!("blend_lists.wgsl")].concat();
        let kind = (samples > 1) as usize;
        let shader = self.blend[kind].get_or_insert_with(|| sampled_shader(device, "blend", &parts, samples > 1)).clone();
        let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&raster.scene), Some(&self.image_layout), None, Some(&raster.shadows)], immediate_size: 0 });
        let face = |compare, pass_op, depth_fail_op| wgpu::StencilFaceState { compare, fail_op: Op::Keep, depth_fail_op, pass_op };
        // a view with lit meshes: two targets, its display paint and its light (`blend.wgsl`'s `Base`), each fragment
        // over both; the paint's alpha (the lit coverage) adds the blend constant's share of a fragment's coverage (a
        // lit mesh's draw sets it to 1)
        let paint_over = wgpu::BlendState {
            color: wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING.color,
            alpha: wgpu::BlendComponent { src_factor: wgpu::BlendFactor::Constant, dst_factor: wgpu::BlendFactor::OneMinusSrcAlpha, operation: wgpu::BlendOperation::Add },
        };
        let targets_for = |write_mask: wgpu::ColorWrites| -> Vec<Option<wgpu::ColorTargetState>> {
            if light {
                vec![Some(wgpu::ColorTargetState { format: COLOR, blend: Some(paint_over), write_mask }), Some(wgpu::ColorTargetState { format: RADIANCE, blend: Some(wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING), write_mask })]
            } else {
                vec![Some(wgpu::ColorTargetState { format: COLOR, blend: Some(wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING), write_mask })]
            }
        };
        let entry = |fs: &str| if light && fs != "fs_none" { format!("{fs}_with_light") } else { fs.to_string() };
        let p = |vs: &str, fs: Option<&str>, stencil: Stencil, write: bool, color: bool| {
            let (front, back) = match stencil {
                Stencil::Coverage => (face(C::Always, Op::IncrementClamp, Op::Keep), face(C::Always, Op::IncrementClamp, Op::Keep)),
                Stencil::Cover => (face(C::NotEqual, Op::Zero, Op::Keep), face(C::NotEqual, Op::Zero, Op::Keep)),
                Stencil::Ignore => (face(C::Always, Op::Keep, Op::Keep), face(C::Always, Op::Keep, Op::Keep)),
            };
            let targets = targets_for(if color { wgpu::ColorWrites::ALL } else { wgpu::ColorWrites::empty() });
            let fs = fs.map(entry);
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some(vs),
                layout: Some(&layout),
                vertex: wgpu::VertexState { module: &shader, entry_point: Some(vs), compilation_options: Default::default(), buffers: &[] },
                fragment: fs.as_deref().map(|fs| wgpu::FragmentState { module: &shader, entry_point: Some(fs), compilation_options: Default::default(), targets: &targets }),
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: Some(wgpu::DepthStencilState {
                    format: DEPTH,
                    depth_write_enabled: Some(write),
                    depth_compare: Some(C::GreaterEqual), // (reversed Z: nearer is greater)
                    stencil: wgpu::StencilState { front, back, read_mask: 0xff, write_mask: 0xff },
                    // (a face's edges lie on its plane, a hair nearer: `ribbon`; faces keep their depth, which
                    // the composite compares paths against)
                    bias: Default::default(),
                }),
                multisample: wgpu::MultisampleState { count: samples, ..Default::default() },
                multiview_mask: None,
                cache: None,
            })
        };
        let stroke = |vs, fs| Passes {
            count: p(vs, Some("fs_none"), Stencil::Coverage, true, false),
            cover: p(vs, Some(fs), Stencil::Cover, true, true),
        };
        // the see-through layers' appends test the opaque depth themselves (read-only here) and
        // write no color; the sprites blended into the base where no see-through layer lies behind them
        // are depth tested
        let group_layout = |group| device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&raster.scene), Some(&self.image_layout), Some(group), Some(&raster.shadows)], immediate_size: 0 });
        let blended = targets_for(wgpu::ColorWrites::ALL);
        let compositing = |layout: &wgpu::PipelineLayout, vs: &str, fs: &str, blends: bool, depth_compare: C| {
            let fs = if blends { entry(fs) } else { fs.to_string() };
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some(&fs),
                layout: Some(layout),
                vertex: wgpu::VertexState { module: &shader, entry_point: Some(vs), compilation_options: Default::default(), buffers: &[] },
                fragment: Some(wgpu::FragmentState { module: &shader, entry_point: Some(&fs), compilation_options: Default::default(), targets: if blends { &blended } else { &[] } }),
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: Some(wgpu::DepthStencilState { format: DEPTH, depth_write_enabled: Some(false), depth_compare: Some(depth_compare), stencil: Default::default(), bias: Default::default() }),
                multisample: wgpu::MultisampleState { count: samples, ..Default::default() },
                multiview_mask: None,
                cache: None,
            })
        };
        let appends = {
            let (append, based) = (group_layout(&raster.lists[kind]), group_layout(&raster.slabs[kind][0]));
            let appended = |vs: &str, fs: &str| compositing(&append, vs, fs, false, C::Always);
            // the slabs, a target each, over the share of each pixel's samples in front of the opaque depth (their
            // pass tests it, on a single sample)
            let slab = Some(wgpu::ColorTargetState { format: COLOR, blend: Some(wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING), write_mask: wgpu::ColorWrites::ALL });
            let slabs = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some("fs_sprites_slabs"),
                layout: Some(&device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&raster.scene), None, Some(&raster.slabs[kind][1])], immediate_size: 0 })),
                vertex: wgpu::VertexState { module: &shader, entry_point: Some("vs_sprites"), compilation_options: Default::default(), buffers: &[] },
                fragment: Some(wgpu::FragmentState { module: &shader, entry_point: Some("fs_sprites_slabs"), compilation_options: Default::default(), targets: &vec![slab; vector::SLABS] }),
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: None,
                multisample: wgpu::MultisampleState::default(),
                multiview_mask: None,
                cache: None,
            });
            Appends {
                stroke: [appended("vs_stroke", "fs_stroke_append"), appended("vs_stroke", "fs_stroke_gradient_append")],
                mesh: appended("vs_mesh", "fs_mesh_append"),
                sprites: compositing(&based, "vs_sprites", "fs_sprites_base", true, C::GreaterEqual),
                slabs,
            }
        };
        let pipelines = Pipelines {
            stroke: [stroke("vs_stroke", "fs_stroke"), stroke("vs_stroke", "fs_stroke_gradient")],
            points: p("vs_points", Some("fs_points"), Stencil::Ignore, true, true),
            sprites: p("vs_sprites", Some("fs_points"), Stencil::Ignore, false, true),
            mesh: p("vs_mesh", Some("fs_mesh"), Stencil::Ignore, true, true),
            appends,
        };
        self.pipelines.insert((samples, light), pipelines);
    }

    /// The pass that draws a mesh's depth into the shadow map of the light in `slot` (made when first cast; the
    /// raster pipeline's shader is made by then).
    fn shadow_pass(&mut self, slot: usize) -> &wgpu::RenderPipeline {
        let (device, raster) = (&self.device, &self.raster);
        let shader = self.blend.iter().flatten().next().expect("the raster pipeline's shader");
        self.shadow_passes.entry(slot).or_insert_with(|| {
            let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&raster.scene)], immediate_size: 0 });
            let constants = [("shadow_light", slot as f64)];
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some("shadow"),
                layout: Some(&layout),
                vertex: wgpu::VertexState { module: shader, entry_point: Some("vs_shadow"), compilation_options: wgpu::PipelineCompilationOptions { constants: &constants, ..Default::default() }, buffers: &[] },
                fragment: None,
                // both sides of a surface cast; a slope's worth of bias against acne (the receiver's offset does the rest)
                primitive: wgpu::PrimitiveState::default(),
                depth_stencil: Some(wgpu::DepthStencilState {
                    format: wgpu::TextureFormat::Depth32Float,
                    depth_write_enabled: Some(true),
                    depth_compare: Some(wgpu::CompareFunction::LessEqual),
                    stencil: Default::default(),
                    bias: wgpu::DepthBiasState { constant: 2, slope_scale: 2.0, clamp: 0.0 },
                }),
                multisample: wgpu::MultisampleState::default(),
                multiview_mask: None,
                cache: None,
            })
        })
    }

    fn image_group(&self, width: u32, height: u32, rgba: &[u8]) -> wgpu::BindGroup {
        let premultiplied: Vec<u8> = rgba
            .chunks_exact(4)
            .flat_map(|p| {
                let a = p[3] as u32;
                [(p[0] as u32 * a / 255) as u8, (p[1] as u32 * a / 255) as u8, (p[2] as u32 * a / 255) as u8, p[3]]
            })
            .collect();
        let texture = self.device.create_texture_with_data(
            &self.queue,
            &wgpu::TextureDescriptor {
                label: Some("image"),
                size: wgpu::Extent3d { width, height, depth_or_array_layers: 1 },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: COLOR,
                usage: wgpu::TextureUsages::TEXTURE_BINDING,
                view_formats: &[],
            },
            wgpu::util::TextureDataOrder::LayerMajor,
            &premultiplied,
        );
        let view = texture.create_view(&Default::default());
        self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("image"),
            layout: &self.image_layout,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&view) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(&self.sampler) },
            ],
        })
    }
}

/// Where a view is drawn — the frame, or a texture another view samples (a camera's view) — by
/// a 2D view's composite, or by the raster pipeline (it gets the pipeline's attachments when that
/// first draws into it). Also the raster atlas a 2D view's point clouds and meshes are drawn in.
pub(crate) struct Canvas {
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) color: wgpu::TextureView,
    pub(crate) raster: Option<Attachments>,
    occluded: Option<occlusion::Occluded>, // where a 3D view's ambient occlusion is found, once it has some
    bloomed: Option<bloom::Bloomed>,       // where a 3D view's glow is made, once it has some
}

/// The raster pipeline's multisamples and depth: they stay on tile, and only the resolved image
/// leaves it — but where a 3D view composites see-through layers (see `Lists`).
pub(crate) struct Attachments {
    pub(crate) msaa: Option<wgpu::TextureView>,
    pub(crate) msaa_light: Option<wgpu::TextureView>, // with lit meshes, their light's samples (`blend.wgsl`'s `Base`)
    pub(crate) depth: wgpu::TextureView,
    pub(crate) depth_only: wgpu::TextureView, // its depth, as a see-through layer's appends read it
    pub(crate) append: Option<(u64, wgpu::BindGroup)>, // the appends' bind group, for the lists' generation
    slabs: Option<Slabs>, // a 3D view's sprites' slabs, once they have see-through layers behind them
}

/// A 3D view's sprites among its other see-through layers (see `blend_lists.wgsl`): the depths of each pixel's nearest
/// layers (`vector::Out::Bounds`), and the slabs between them, a target each and all together (as the composite reads
/// them); the bounds as its sprites' passes read them (into the base; into the slabs, with the opaque depth).
struct Slabs {
    bounds: wgpu::TextureView,
    layers: [wgpu::TextureView; vector::SLABS],
    slabs: wgpu::TextureView,
    groups: [wgpu::BindGroup; 2],
}

/// How a raster pass uses depth and stencil: fresh (cleared, then dropped), kept for the passes
/// after it, only read (by the appends), or kept again with the color's samples (for the composite
/// to read).
#[derive(Clone, Copy)]
enum Depth {
    Fresh,
    Kept,
    Read,
    Shared, // the kept depth, kept again with the samples for the composite to read
}

/// The raster pipeline's bind group layouts: the scene's arrays, a 3D view's see-through lists (written, with the
/// opaque depth) and its slab bounds (as its sprites read them: into the base; into the slabs, with the opaque depth).
struct RasterLayouts {
    scene: wgpu::BindGroupLayout,
    lists: [wgpu::BindGroupLayout; 2],
    slabs: [[wgpu::BindGroupLayout; 2]; 2],
    shadows: wgpu::BindGroupLayout, // what the lit passes read: the shadow maps and their comparison, the DFG table
}

/// A pass's color cleared to a premultiplied color.
fn clear([r, g, b, a]: [f64; 4]) -> wgpu::LoadOp<wgpu::Color> {
    wgpu::LoadOp::Clear(wgpu::Color { r, g, b, a })
}

impl Canvas {
    fn new(gpu: &Gpu, width: u32, height: u32) -> Self {
        // written by the raster passes, and by the composite (a compute pass's storage texture)
        let usage = wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_SRC;
        let size = wgpu::Extent3d { width, height, depth_or_array_layers: 1 };
        let color = gpu.device.create_texture(&wgpu::TextureDescriptor { label: None, size, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: COLOR, usage, view_formats: &[] });
        Self { width, height, color: color.create_view(&Default::default()), raster: None, occluded: None, bloomed: None }
    }

    /// Give it the raster pipeline's attachments (once).
    /// Give it the raster pipeline's attachments (once; with `light`, the lit meshes' light's samples too, once).
    fn attach(&mut self, gpu: &Gpu, samples: u32, light: bool) {
        let size = wgpu::Extent3d { width: self.width, height: self.height, depth_or_array_layers: 1 };
        let texture = |format, usage| gpu.device.create_texture(&wgpu::TextureDescriptor { label: None, size, mip_level_count: 1, sample_count: samples, dimension: wgpu::TextureDimension::D2, format, usage, view_formats: &[] });
        // read by shaders where a 3D view's see-through lists are (the appends test its depth, the composite lays its
        // samples)
        let usage = wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING;
        let attached = self.raster.get_or_insert_with(|| {
            let depth = texture(DEPTH, usage);
            Attachments {
                msaa: (samples > 1).then(|| texture(COLOR, usage).create_view(&Default::default())),
                msaa_light: None,
                depth_only: depth.create_view(&wgpu::TextureViewDescriptor { aspect: wgpu::TextureAspect::DepthOnly, ..Default::default() }),
                depth: depth.create_view(&Default::default()),
                append: None,
                slabs: None,
            }
        });
        if light && samples > 1 && attached.msaa_light.is_none() {
            attached.msaa_light = Some(texture(RADIANCE, usage).create_view(&Default::default()));
        }
    }

    /// Give it a 3D view's slabs (once; it has the raster pipeline's attachments).
    fn attach_slabs(&mut self, gpu: &Gpu, samples: u32) {
        let attached = self.raster.as_mut().expect("the raster pipeline's attachments");
        if attached.slabs.is_some() {
            return;
        }
        let size = wgpu::Extent3d { width: self.width, height: self.height, depth_or_array_layers: 1 };
        let texture = |label, size, format, usage| gpu.device.create_texture(&wgpu::TextureDescriptor { label: Some(label), size, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format, usage, view_formats: &[] });
        let bounds = texture("slab bounds", size, wgpu::TextureFormat::Rgba32Float, wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING).create_view(&Default::default());
        let slabs = texture("slabs", wgpu::Extent3d { depth_or_array_layers: vector::SLABS as u32, ..size }, COLOR, wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING);
        let layers = std::array::from_fn(|k| slabs.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2), base_array_layer: k as u32, array_layer_count: Some(1), ..Default::default() }));
        let read = wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&bounds) };
        let depth = wgpu::BindGroupEntry { binding: 3, resource: wgpu::BindingResource::TextureView(&attached.depth_only) };
        let group = |layout, entries: &[wgpu::BindGroupEntry]| gpu.device.create_bind_group(&wgpu::BindGroupDescriptor { label: Some("slab bounds"), layout, entries });
        let layouts = &gpu.raster.slabs[(samples > 1) as usize];
        let groups = [group(&layouts[0], std::slice::from_ref(&read)), group(&layouts[1], &[read, depth])];
        let slabs = slabs.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2Array), ..Default::default() });
        attached.slabs = Some(Slabs { bounds, layers, slabs, groups });
    }

    /// A raster pass over it: its color loaded as `color` says, and resolved into the image, or `into`
    /// another (a 3D view's base, for its composite) — with multisamples only the resolved image is
    /// kept, the samples stay on tile — or its samples kept; none for the appends, which only read
    /// depth.
    /// (`light`: a view with lit meshes keeps their light apart, in this target and its samples: `blend.wgsl`'s `Base`.)
    fn pass<'e>(&self, encoder: &'e mut wgpu::CommandEncoder, color: Option<(wgpu::LoadOp<wgpu::Color>, bool)>, depth: Depth, into: Option<&wgpu::TextureView>, light: Option<&wgpu::TextureView>) -> wgpu::RenderPass<'e> {
        let attached = self.raster.as_ref().expect("the raster pipeline's attachments");
        let target = into.unwrap_or(&self.color);
        // a target's attachment: its samples, resolved into it, or it alone; resolved, its samples are dropped (but where
        // the composite reads them after: `Depth::Shared`)
        fn attachment<'a>(msaa: Option<&'a wgpu::TextureView>, target: &'a wgpu::TextureView, load: wgpu::LoadOp<wgpu::Color>, resolve: bool, kept: bool) -> wgpu::RenderPassColorAttachment<'a> {
            let store = if resolve && msaa.is_some() && !kept { wgpu::StoreOp::Discard } else { wgpu::StoreOp::Store };
            wgpu::RenderPassColorAttachment { view: msaa.unwrap_or(target), depth_slice: None, resolve_target: msaa.filter(|_| resolve).map(|_| target), ops: wgpu::Operations { load, store } }
        }
        let kept = matches!(depth, Depth::Shared);
        let mut colors: Vec<Option<wgpu::RenderPassColorAttachment>> = Vec::new();
        if let Some((load, resolve)) = color {
            colors.push(Some(attachment(attached.msaa.as_ref(), target, load, resolve, kept)));
            if let Some(light) = light {
                let load = if matches!(load, wgpu::LoadOp::Load) { wgpu::LoadOp::Load } else { wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT) };
                colors.push(Some(attachment(attached.msaa_light.as_ref(), light, load, resolve, kept)));
            }
        }
        let cleared = |store| Some(wgpu::Operations { load: wgpu::LoadOp::Clear(0.0), store }); // (reversed Z: far)
        let stencil = Some(wgpu::Operations { load: wgpu::LoadOp::Clear(0), store: wgpu::StoreOp::Discard });
        let (depth_ops, stencil_ops) = match depth {
            Depth::Fresh => (cleared(wgpu::StoreOp::Discard), stencil),
            Depth::Kept => (cleared(wgpu::StoreOp::Store), stencil),
            Depth::Read => (None, None),
            Depth::Shared => (Some(wgpu::Operations { load: wgpu::LoadOp::Load, store: wgpu::StoreOp::Store }), stencil),
        };
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("raster"),
            color_attachments: &colors,
            depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment { view: &attached.depth, depth_ops, stencil_ops }),
            occlusion_query_set: None,
            timestamp_writes: None,
            multiview_mask: None,
        });
        if light.is_some() {
            // Ordinary paint contributes no lit coverage, even before this pass's first material mesh.
            pass.set_blend_constant(wgpu::Color::TRANSPARENT);
        }
        pass
    }
}

pub(crate) struct Targets {
    pub(crate) frame: Canvas,
    #[cfg(any(feature = "python", feature = "export"))]
    pub(crate) readback: wgpu::Buffer, // the frame's pixels, then the lists' count (see `Lists`)
    #[cfg(any(feature = "python", feature = "export"))]
    pub(crate) padded: u32,
}

/// The see-through fragments of a frame's 3D views (see `blend.wgsl`): a list head per pixel of
/// the largest view that composites, the nodes, and how many the frame appended — its views
/// together: more than `capacity`, and the frame is drawn again with room for them.
pub(crate) struct Lists {
    pub(crate) heads: wgpu::Buffer,
    pub(crate) nodes: wgpu::Buffer,
    pub(crate) appended: wgpu::Buffer,
    pub(crate) pixels: u64,
    pub(crate) capacity: u64,
    pub(crate) generation: u64, // made anew this many times (the canvases' groups follow)
}

const NODE_BYTES: u64 = 16;

struct Buffers {
    views: wgpu::Buffer, // each raster pass's view, VIEW_STRIDE apart
    slots: usize,        // views it has room for
    instances: wgpu::Buffer,
    capacity: usize,
    sprites: wgpu::Buffer, // the frame's sprites, view after view (see `Player::sprites`)
    room: usize,           // sprites it has room for
    group: Option<wgpu::BindGroup>, // the raster pipeline's
    statics: [wgpu::Buffer; 7], // vertices, links, indices, rows, extras; control points, curve ranges
    sizes: [u64; 7],            // their capacities, bytes
    sent: [usize; 7],           // bytes of the store's arrays they hold
    generation: u64,            // the store's packing they hold
    shadow_maps: ShadowMaps,
}

/// The shadow maps a frame's 3D views draw, one after another (each view's before its own passes): an array of
/// `shadow::SIZE`² depth layers, as many as a view of the frame needs most (1×1 until one casts shadows): a view of
/// each layer to draw into, the whole array (as a 3D view's composite reads it), and the bind group the raster passes
/// read it through.
struct ShadowMaps {
    layers: Vec<wgpu::TextureView>,
    array: wgpu::TextureView,
    size: u32,
    group: wgpu::BindGroup, // the array and its comparison, as the lit passes read them (group 3), with the DFG table and
    environment: Option<u32>, // the environment whose cube it binds (none: `no_environment`)
}

impl ShadowMaps {
    fn new(gpu: &Gpu, size: u32, layers: u32, environment: (Option<u32>, &wgpu::TextureView)) -> Self {
        let device = &gpu.device;
        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("shadow maps"),
            size: wgpu::Extent3d { width: size, height: size, depth_or_array_layers: layers },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Depth32Float,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
            view_formats: &[],
        });
        let array = texture.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2Array), ..Default::default() });
        let layers = (0..layers)
            .map(|layer| texture.create_view(&wgpu::TextureViewDescriptor { dimension: Some(wgpu::TextureViewDimension::D2), base_array_layer: layer, array_layer_count: Some(1), ..Default::default() }))
            .collect();
        let group = Self::bind(gpu, &array, environment.1, &gpu.no_occlusion);
        Self { layers, array, size, group, environment: environment.0 }
    }

    /// What the lit passes read (group 3): the maps and their comparison, the DFG table, an environment's cube, a 3D
    /// view's ambient occlusion (`group` binds none: a view with some binds a group of its own).
    fn bind(gpu: &Gpu, array: &wgpu::TextureView, cube: &wgpu::TextureView, occlusion: &wgpu::TextureView) -> wgpu::BindGroup {
        gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("lighting"),
            layout: &gpu.raster.shadows,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(array) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(&gpu.shadow_compare) },
                wgpu::BindGroupEntry { binding: 2, resource: wgpu::BindingResource::TextureView(&gpu.dfg) },
                wgpu::BindGroupEntry { binding: 3, resource: wgpu::BindingResource::Sampler(&gpu.linear) },
                wgpu::BindGroupEntry { binding: 4, resource: wgpu::BindingResource::TextureView(cube) },
                wgpu::BindGroupEntry { binding: 5, resource: wgpu::BindingResource::TextureView(occlusion) },
            ],
        })
    }
}

/// A view's environment: its first light that is one (kind 4), the id it carries where a point light's reach is.
fn environment_of(view: &[f32]) -> Option<u32> {
    (0..LIGHTS).map(|l| &view[VIEW_LIGHTING + 8 + 16 * l..][..16]).find(|slot| slot[3].round() as u32 == 4).map(|slot| slot[7].round() as u32)
}

/// A 3D view's ambient occlusion, where it has some and a light that it shuts out (light from all around: an ambient
/// or an environment light): how much, how far around.
fn occlusion_of(view: &[f32]) -> Option<(f32, f32)> {
    let [amount, radius] = [view[VIEW_OCCLUSION], view[VIEW_OCCLUSION + 1]];
    let lights = (view[VIEW_LIGHTING + 4] as usize).min(LIGHTS);
    let from_all_around = (0..lights).any(|l| matches!(view[VIEW_LIGHTING + 8 + 16 * l + 3].round() as u32, 0 | 4));
    (amount > 0.0 && radius > 0.0 && from_all_around).then_some((amount, radius))
}

/// A 3D view's bloom, where it has some: the share of its light its lens spreads (at most all of it).
fn bloom_of(view: &[f32]) -> Option<f32> {
    let strength = view[VIEW_LIGHTING + 7];
    (strength > 0.0).then_some(strength.min(1.0))
}

/// The box around two boxes, the first maybe none.
fn union(a: Option<Box3>, [lo, hi]: Box3) -> Box3 {
    a.map_or([lo, hi], |[a, b]| [std::array::from_fn(|i| a[i].min(lo[i])), std::array::from_fn(|i| b[i].max(hi[i]))])
}

/// A view's light as its passes read it (`vector::LIGHT` floats: a raster pass's `View` from `toward`, a composite's
/// `Frame`): the unit vector toward the viewer, where it sees from, how many lights with the exposure and the tone
/// mapping, then each light as the view gives it with its shadow map: its layer (-1: none), a texel's size, whether it
/// sees in perspective, and its matrix (an environment: its cube's roughest level and unit); then its environment's
/// diffuse light (`environment::harmonics`; none: 0), and its ambient occlusion (how much, how far: `occlusion`).
fn lighting(v: &[f32], shadows: &[shadow::Shadow], (harmonics, unit): ([[f32; 4]; 9], f32)) -> [f32; vector::LIGHT] {
    let mut out = [0.0f32; vector::LIGHT];
    out[12 + 32 * LIGHTS..][..36].copy_from_slice(bytemuck::cast_slice(&harmonics));
    out[12 + 32 * LIGHTS + 36..][..4].copy_from_slice(&v[VIEW_OCCLUSION..VIEW_OCCLUSION + 4]);
    out[..3].copy_from_slice(&v[40..43]);
    out[4..12].copy_from_slice(&v[VIEW_LIGHTING..VIEW_LIGHTING + 8]);
    for light in 0..LIGHTS {
        let l = &mut out[12 + 32 * light..][..32];
        l[..16].copy_from_slice(&v[VIEW_LIGHTING + 8 + 16 * light..][..16]);
        l[13..16].copy_from_slice(&[-1.0, 0.0, 0.0]);
        if l[3].round() as u32 == 4 {
            // an environment: its cube's roughest level, where its id was, and its unit
            l[7] = (environment::LEVELS - 1) as f32;
            l[11] = unit;
        }
        if let Some((layer, s)) = shadows.iter().enumerate().find(|(_, s)| s.light == light) {
            l[13..16].copy_from_slice(&[layer as f32, s.texel, s.perspective as u8 as f32]);
            l[16..].copy_from_slice(bytemuck::cast_slice(&s.matrix));
        }
    }
    out
}

impl Buffers {
    /// The store's control points, subpaths and rows, as the vector passes read them.
    fn vector_statics(&self) -> [wgpu::BindingResource<'_>; 3] {
        [self.statics[5].as_entire_binding(), self.statics[6].as_entire_binding(), self.statics[3].as_entire_binding()]
    }
}

/// One view to draw: the frame (key 0) or a texture others sample under `key`.
#[derive(Clone)]
pub(crate) struct Frame {
    pub(crate) key: u64,
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) view: Vec<f32>,
    pub(crate) records: Vec<Record>,
}

/// A view, ready to encode: a 3D view's draws (its instances from the offset); a 2D view's plan,
/// and per group its rasters' draws.
enum Drawing {
    Raster {
        offset: u32,
        draws: Vec<Draw>,
        listed: [u32; 4],    // where its listed see-through layers can paint (x, y, width, height)
        sprites: Range<u32>, // its sprites among the frame's, far to near
        lists: bool,         // whether its listed layers are appended to the lists
        slabs: bool,         // whether its sprites are blended between its other see-through layers, in slabs
        light: bool,         // whether it has lit meshes, their light kept apart in its base (`blend.wgsl`'s `Base`)
        glow: Option<f32>,   // its bloom, where it has lit content to spread (`bloom`)
        // its composite's plan: its paths, exact, laid in depth order with its raster base and listed fragments
        // (none: the raster base is the view)
        plan: Option<vector::Plan>,
        shadows: Vec<shadow::Shadow>, // the maps its lights cast
        cast: Vec<vector::Plan>,      // its paths seen from each (none: it has none)
    },
    Vector(vector::Plan, Vec<(u32, Vec<Draw>)>),
}

#[cfg_attr(feature = "python", pyo3::pyclass(module = "manimgx._engine"))]
pub(crate) struct Player {
    pub(crate) width: u32,
    pub(crate) height: u32,
    samples: u32,
    pub(crate) store: Store,
    images: Keyed<(u32, u32, Vec<u8>)>,
    opaque_images: Keyed<()>, // images with no pixel less than opaque
    environments: HashMap<u32, environment::Environment>, // by the id its views' lights give it (`add_environment`)
    image_groups: Keyed<wgpu::BindGroup>,
    canvases: Keyed<Canvas>,
    rasters: Option<Canvas>, // the raster atlas (see `vector`)
    buffers: Option<Buffers>,
    pub(crate) targets: Option<Targets>,
    #[cfg(feature = "export")]
    pub(crate) export: Option<crate::export::Export>, // the video being written, if any
    pub(crate) lists: Option<Lists>,
    list_capacity: u64, // nodes the lists are made with (grown when a frame needs more)
}

// pixels, light, toward, eye, lighting; the lights (`light.wgsl`), each its 16 floats from the view and its shadow map's
const VIEW_BYTES: u64 = 4 * (8 + vector::LIGHT as u64);
const VIEW_STRIDE: usize = 1280; // VIEW_BYTES, at the widest alignment a uniform's offset can need (256)

/// The raster pipeline's scene bind group: the views, the store's arrays, the frame's objects and a 3D view's sprites.
fn scene_group(gpu: &Gpu, b: &Buffers) -> wgpu::BindGroup {
    let view = wgpu::BindingResource::Buffer(wgpu::BufferBinding { buffer: &b.views, offset: 0, size: wgpu::BufferSize::new(VIEW_BYTES) });
    let resources = [(0, view), (1, b.statics[0].as_entire_binding()), (2, b.statics[1].as_entire_binding()), (4, b.instances.as_entire_binding()), (5, b.statics[3].as_entire_binding()), (6, b.statics[4].as_entire_binding()), (7, b.sprites.as_entire_binding())];
    let entries: Vec<wgpu::BindGroupEntry> = resources.into_iter().map(|(binding, resource)| wgpu::BindGroupEntry { binding, resource }).collect();
    gpu.device.create_bind_group(&wgpu::BindGroupDescriptor { label: Some("scene"), layout: &gpu.raster.scene, entries: &entries })
}

/// A whole buffer at a binding.
fn whole(binding: u32, buffer: &wgpu::Buffer) -> wgpu::BindGroupEntry<'_> {
    wgpu::BindGroupEntry { binding, resource: buffer.as_entire_binding() }
}

fn store_limit(limits: &wgpu::Limits, array: usize) -> u64 {
    if array == 2 { limits.max_buffer_size } else { limits.max_storage_buffer_binding_size.min(limits.max_buffer_size) }
}

/// Geometric growth may use spare space, but a binding can never expose more than its limit.
fn buffer_room(needed: u64, stride: u64, minimum: u64, limit: u64, name: &str) -> Result<u64, String> {
    if needed > limit / stride {
        return Err(format!("resident {name} requires {} bytes; the GPU's buffer limit is {limit} bytes", needed.saturating_mul(stride)));
    }
    Ok(needed.max(minimum).next_power_of_two().min(limit / stride))
}

/// Draw object `k`'s `range` with `pipeline` (set only when it changes).
fn run(pass: &mut wgpu::RenderPass, current: &mut *const wgpu::RenderPipeline, pipeline: &wgpu::RenderPipeline, range: &Range<u32>, k: u32) {
    if !std::ptr::eq(*current, pipeline) {
        pass.set_pipeline(pipeline);
        *current = pipeline;
    }
    pass.draw_indexed(range.clone(), 0, k..k + 1);
}

impl Player {
    /// Copy the drawn frame's full-quality RGBA rows, independently of video conversion.
    #[cfg(any(feature = "python", feature = "export"))]
    pub(crate) fn copy_pixels(&self, encoder: &mut wgpu::CommandEncoder) {
        let t = self.targets.as_ref().expect("targets");
        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo { texture: t.frame.color.texture(), mip_level: 0, origin: wgpu::Origin3d::ZERO, aspect: wgpu::TextureAspect::All },
            wgpu::TexelCopyBufferInfo { buffer: &t.readback, layout: wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(t.padded), rows_per_image: Some(self.height) } },
            wgpu::Extent3d { width: self.width, height: self.height, depth_or_array_layers: 1 },
        );
    }

    #[cfg(any(feature = "python", feature = "export"))]
    pub(crate) fn map_pixels(&self, gpu: &Gpu) -> Result<(), String> {
        self.targets.as_ref().expect("targets").readback.slice(..).map_async(wgpu::MapMode::Read, |_| {});
        gpu.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e| e.to_string())?;
        Ok(())
    }

    /// Bring the GPU up to date: images made textures, the store's arrays sent — only what was
    /// appended since last time; everything when they were packed or outgrew their buffers — and
    /// room for `count` instances, `views` views and `sprites` sprites.
    fn prepare(&mut self, gpu: &Gpu, count: usize, views: usize, sprites: usize) -> Result<(), String> {
        let device = &gpu.device;
        let limits = device.limits();
        for (key, (w, h, rgba)) in self.images.drain() {
            self.image_groups.insert(key, gpu.image_group(w, h, &rgba));
        }
        self.image_groups.entry(0).or_insert_with(|| gpu.image_group(1, 1, &[255, 255, 255, 255]));
        let rooms = self.store.rooms(&limits)?;
        let capacity = buffer_room(count as u64, size_of::<Instance>() as u64, 1024, store_limit(&limits, 0), "instances")? as usize;
        let room = buffer_room(sprites as u64, size_of::<[u32; 2]>() as u64, 1024, store_limit(&limits, 0), "sprites")? as usize;
        let slots = buffer_room(views as u64, VIEW_STRIDE as u64, 4, limits.max_buffer_size, "views")? as usize;
        // A rejected frame must leave pending in-place writes available for the next one.
        let dirty = std::mem::take(&mut self.store.dirty);
        let s = &self.store;
        let arrays = s.arrays();
        // (the passes read them as storage buffers; the indices are an index buffer too)
        let storage = wgpu::BufferUsages::STORAGE;
        let buffer = |size: u64| device.create_buffer(&wgpu::BufferDescriptor { label: Some("store"), size, usage: storage | wgpu::BufferUsages::INDEX | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let instances = |capacity: usize| device.create_buffer(&wgpu::BufferDescriptor { label: Some("instances"), size: (capacity * size_of::<Instance>()) as u64, usage: storage | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let view_buffer = |slots: usize| device.create_buffer(&wgpu::BufferDescriptor { label: Some("views"), size: (slots * VIEW_STRIDE) as u64, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let sprite_buffer = |room: usize| device.create_buffer(&wgpu::BufferDescriptor { label: Some("sprites"), size: (room * size_of::<[u32; 2]>()) as u64, usage: storage | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let mut rebind = false;
        let buffers = self.buffers.get_or_insert_with(|| {
            let (views, instances, sprites, statics) = (view_buffer(slots), instances(capacity), sprite_buffer(room), [(); 7].map(|_| buffer(1024)));
            rebind = true;
            let shadow_maps = ShadowMaps::new(gpu, 1, 1, (None, &gpu.no_environment));
            Buffers { views, slots, instances, capacity, sprites, room, group: None, statics, sizes: [1024; 7], sent: [0; 7], generation: s.generation, shadow_maps }
        });
        if buffers.generation != s.generation {
            buffers.sent = [0; 7];
            buffers.generation = s.generation;
        }
        for (k, range) in &dirty {
            if range.end <= buffers.sent[*k] && !range.is_empty() {
                gpu.queue.write_buffer(&buffers.statics[*k], range.start as u64, &arrays[*k][range.clone()]);
            }
        }
        for (k, bytes) in arrays.iter().enumerate() {
            if bytes.len() as u64 > buffers.sizes[k] {
                buffers.sizes[k] = rooms[k];
                buffers.statics[k] = buffer(buffers.sizes[k]);
                buffers.sent[k] = 0;
                rebind = true;
            }
            if buffers.sent[k] < bytes.len() {
                gpu.queue.write_buffer(&buffers.statics[k], buffers.sent[k] as u64, &bytes[buffers.sent[k]..]);
                buffers.sent[k] = bytes.len();
            }
        }
        if buffers.capacity < count {
            buffers.capacity = capacity;
            buffers.instances = instances(buffers.capacity);
            rebind = true;
        }
        if buffers.slots < views {
            buffers.slots = slots;
            buffers.views = view_buffer(buffers.slots);
            rebind = true;
        }
        if buffers.room < sprites {
            buffers.room = room;
            buffers.sprites = sprite_buffer(buffers.room);
            rebind = true;
        }
        if rebind {
            buffers.group = Some(scene_group(gpu, buffers));
        }
        Ok(())
    }

    pub(crate) fn targets(&mut self, gpu: &Gpu) -> &Targets {
        let (width, height) = (self.width, self.height);
        self.targets.get_or_insert_with(|| {
            #[cfg(any(feature = "python", feature = "export"))]
            let padded = (width * 4).div_ceil(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT) * wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
            Targets {
                frame: Canvas::new(gpu, width, height),
                // read back natively (`render`); in the browser a frame goes to its canvas
                #[cfg(any(feature = "python", feature = "export"))]
                readback: gpu.device.create_buffer(&wgpu::BufferDescriptor {
                    label: Some("readback"),
                    size: (padded * height) as u64 + COUNT_BYTES,
                    usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
                    mapped_at_creation: false,
                }),
                #[cfg(any(feature = "python", feature = "export"))]
                padded,
            }
        })
    }

    /// A camera's view as a texture: its canvas, (re)made at the size asked for, sampled under `key`.
    fn canvas(&mut self, gpu: &Gpu, key: u64, width: u32, height: u32) {
        if self.canvases.get(&key).is_some_and(|c| c.width == width && c.height == height) {
            return;
        }
        let canvas = Canvas::new(gpu, width.max(1), height.max(1));
        let group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("camera view"),
            layout: &gpu.image_layout,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(&canvas.color) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::Sampler(&gpu.sampler) },
            ],
        });
        self.image_groups.insert(key, group);
        self.canvases.insert(key, canvas);
    }

    /// A view's records in draw order: with a 3D camera, lit objects far to near first (CE's
    /// order), then the rest as given; fixed-in-frame objects last.
    fn order(&self, camera: &Camera, records: &[Record]) -> Result<Vec<usize>, String> {
        let mut order: Vec<(usize, u8, f32)> = Vec::with_capacity(records.len());
        for (k, r) in records.iter().enumerate() {
            let lit = camera.three_d && r.flags & LIT != 0;
            let nearness = if lit {
                let a = self.store.shapes.get(&r.key1).ok_or_else(|| format!("unknown shape {}", r.key1))?;
                dot(camera.toward, world_center(a, &r.m1))
            } else {
                f32::INFINITY
            };
            order.push((k, (r.flags & OVERLAY != 0) as u8, nearness));
        }
        if camera.three_d || records.iter().any(|r| r.flags & OVERLAY != 0) {
            order.sort_by(|x, y| (x.1, x.2).partial_cmp(&(y.1, y.2)).unwrap_or(std::cmp::Ordering::Equal));
        }
        Ok(order.into_iter().map(|(k, ..)| k).collect())
    }

    /// A record as the raster pipeline draws it: its instance, and the passes that change pixels.
    /// `place` puts a 2D view's point cloud or mesh into its rectangle of the raster atlas;
    /// `index` is the record's place in its view (coincident see-through layers keep that order).
    fn instance(&self, camera: &Camera, r: &Record, place: Option<vector::Place>, index: u32) -> Result<(Instance, Draw), String> {
        let a = self.store.shapes.get(&r.key1).ok_or_else(|| format!("unknown shape {}", r.key1))?;
        let b = if r.key2 == 0 {
            None
        } else {
            let b = self.store.shapes.get(&r.key2).ok_or_else(|| format!("unknown shape {}", r.key2))?;
            if b.count != a.count {
                return Err(format!("morph between unaligned shapes ({} vs {} vertices)", a.count, b.count));
            }
            Some(b)
        };
        let eye = camera.eye(r);
        let mut paint = self.store.paint(camera, &eye, r)?;
        let (many_fill, many_stroke) = (paint.brush[1] > 1, paint.brush[3] > 1);
        let mut c1 = compose(&eye, &r.m1, true);
        let mut c2 = if b.is_some() { compose(&eye, &r.m2, false) } else { [[0.0; 4]; 4] };
        // light, once per object (a path is lit as a whole, like CE)
        let lit = camera.three_d && r.flags & LIT != 0;
        let light = self.store.light(camera, r)?;
        // solid colors lit (a gradient, alpha −1, is lit per fragment)
        for c in [&mut paint.fill, &mut paint.stroke, &mut paint.background] {
            if c[3] >= 0.0 {
                *c = lighten(*c, light);
            }
        }
        if let Some(place) = place {
            for c in [&mut c1, &mut c2] {
                for axis in 0..2 {
                    c[axis] = [0, 1, 2, 3].map(|j| place.scale[axis] * c[axis][j] + place.bias[axis] * c[3][j]);
                }
            }
            paint.gradient[0] += place.shift[0];
            paint.gradient[1] += place.shift[1];
        }
        // pixels per scene unit at w = 1, for points sized in scene units
        let scale = (eye[0][0] * eye[0][0] + eye[0][1] * eye[0][1] + eye[0][2] * eye[0][2]).sqrt() * camera.size[0] / 2.0;
        // lit by its material where it has one (a 3D view's mesh, in the scene: not fixed in the frame), else by CE's
        // light (on the side the eye sees; fixed in the frame, the side toward the view)
        let material = camera.three_d && a.kind == Kind::Mesh && r.material[3] > 0.0 && r.flags & OVERLAY == 0;
        let flags = if material { MATERIAL } else if lit && a.kind == Kind::Mesh { LIT } else { 0 } | if r.texture != 0 { TEXTURED | (r.flags & (NEAREST | CUBIC)) } else { 0 } | (r.flags & OVERLAY);
        let instance = Instance {
            c1,
            c2,
            m1: r.m1,
            m2: r.m2,
            params: [r.params[0], r.params[1], r.params[2] * camera.unit, r.params[3] * camera.unit],
            extra: [0.5 * r.gradient_a[3] * scale, light, 0.0, 0.0],
            ids: [a.base, b.map_or(NONE, |b| b.base), flags as u32 | index << PLACE, 0],
            paint,
            material: if material { r.material } else { [0.0; 4] },
        };
        // which passes change pixels
        let (fill, stroke) = a.raster.shown([r.params[0], r.params[1]]); // (a path has no raster form: nothing)
        // a mesh's edges first find their nearest covered depth, then blend once per sample:
        // a hidden ribbon cannot consume another ribbon's visible coverage
        let stroked = a.kind == Kind::Mesh && !stroke.is_empty() && r.params[2] > 0.0 && (paint.stroke[3] > 0.0 || many_stroke);
        // a layer can be seen through where its color is, or a row of its brushes (a tween's
        // either paint); a textured mesh also where its picture can be
        let see_through = |alpha: f32, many: bool, rows: u64, rows2: u64| {
            let rows_see_through = |key: u64| self.store.brushes.get(&key).is_some_and(|b| b.see_through);
            if many { rows_see_through(rows) || (r.dash[3] > 0.0 && rows_see_through(rows2)) } else { alpha < 1.0 }
        };
        let filled = if a.kind == Kind::Points { !stroke.is_empty() } else { !fill.is_empty() };
        let picture = r.texture != 0 && !self.opaque_images.contains_key(&r.texture);
        let draw = Draw {
            kind: a.kind,
            stroked,
            fill,
            stroke,
            texture: r.texture,
            stroke_gradient: many_stroke,
            overlay: r.flags & OVERLAY != 0,
            see_through: [filled && (see_through(paint.fill[3], many_fill, r.fill_rows, r.fill_rows2) || picture), stroked && see_through(paint.stroke[3], many_stroke, r.stroke_rows, r.stroke_rows2)],
            lit: material,
        };
        Ok((instance, draw))
    }

    /// A 3D view's sprites, appended to `sprites`: every see-through point of `draws` (their
    /// instances from `offset`) that can be seen, as (instance, vertex), far to near — the order
    /// they blend in; among equal depths, the view's order. Their range.
    fn sprites(&self, instances: &[Instance], draws: &[Draw], offset: u32, sprites: &mut Vec<[u32; 2]>) -> Range<u32> {
        // the clouds in the view's order: their records' places
        let mut clouds: Vec<(u32, usize)> = (0..draws.len()).filter(|&j| draws[j].sprites()).map(|j| (instances[j].ids[2] >> PLACE, j)).collect();
        clouds.sort_unstable();
        let mut far_first = Vec::new();
        for (_, j) in clouds {
            let quads = &self.store.indices[draws[j].stroke.start as usize..draws[j].stroke.end as usize];
            for code in quads.iter().step_by(6) {
                let vertex = code >> 3;
                let c = self.store.clip(&instances[j], vertex);
                let depth = c[2] / c[3];
                if c[3] <= 1e-6 || !(0.0..=1.0).contains(&depth) {
                    continue; // behind the camera, or nearer than the near plane or farther than the far one
                }
                // keyed far first (reversed Z: far is small): a depth's bits order it once −0 is +0
                far_first.push((depth.abs().to_bits(), [offset + j as u32, vertex]));
            }
        }
        let first = sprites.len() as u32;
        sprites.extend(radix_sort(far_first).into_iter().map(|(_, sprite)| sprite));
        first..sprites.len() as u32
    }

    /// Encode views in order — camera views first, the frame (key 0) last; each view is
    /// projection, overlay, pixels, light, toward, background. Also: whether the frame was
    /// composited in more than one group (its objects overflowed the atlases), and whether a 3D
    /// view composited see-through layers through the lists (whose count tells if they held).
    pub(crate) fn encode(&mut self, gpu: &mut Gpu, frames: &[Frame]) -> Result<(wgpu::CommandEncoder, bool, bool), String> {
        self.with_working_set(&gpu.device.limits(), frames, |player| player.encode_frame(gpu, frames))
    }

    /// CPU residency includes nearby frames. Only the complete current frame must fit on the GPU.
    /// A temporary packing never evicts logical keys, consumes their pending writes, or leaks its
    /// offsets into the resident store; even a failed encoding restores that store unchanged.
    fn with_working_set<T>(&mut self, limits: &wgpu::Limits, frames: &[Frame], draw: impl FnOnce(&mut Self) -> Result<T, String>) -> Result<T, String> {
        self.store.pack_if_worthwhile(!self.store.fits(limits));
        if self.store.fits(limits) {
            return draw(self);
        }
        let used: Keyed<()> = frames.iter().flat_map(|f| crate::take::slots(bytemuck::cast_slice(&f.records))).flatten().map(|key| (key, ())).collect();
        let working = self.store.packed(|key| used.contains_key(&key));
        working.rooms(limits)?;
        let resident = std::mem::replace(&mut self.store, working);
        let result = draw(self);
        let generation = self.store.generation + 1;
        self.store = resident;
        self.store.generation = generation; // the next GPU upload cannot reuse temporary offsets
        result
    }

    fn encode_frame(&mut self, gpu: &mut Gpu, frames: &[Frame]) -> Result<(wgpu::CommandEncoder, bool, bool), String> {
        let samples = self.samples.clamp(1, gpu.max_samples);
        let mut instances: Vec<Instance> = Vec::new();
        let mut sprites: Vec<[u32; 2]> = Vec::new();
        let mut drawings: Vec<Drawing> = Vec::with_capacity(frames.len());
        for (i, f) in frames.iter().enumerate() {
            if f.view.len() < VIEW_LENGTH {
                return Err(format!("view needs {} floats, got {}", VIEW_LENGTH, f.view.len()));
            }
            if (f.key == 0) != (i + 1 == frames.len()) {
                return Err("the frame (key 0) is the last view, and only it".into());
            }
            let earlier = |key: u64| frames[..i].iter().any(|g| g.key == key);
            if let Some(r) = f.records.iter().find(|r| r.texture != 0 && !earlier(r.texture) && !self.image_groups.contains_key(&r.texture) && !self.images.contains_key(&r.texture)) {
                return Err(format!("unknown texture {}", r.texture));
            }
            let camera = Camera::new(&f.view);
            let drawing = if camera.three_d {
                // its paths are analytic vector layers over the raster base (its meshes and points), depth tested
                // against it; everything else is the base
                let order = self.order(&camera, &f.records)?;
                let path = |k: &usize| self.store.shapes.get(&f.records[*k].key1).is_some_and(|s| s.kind == Kind::Path);
                let paths: Vec<usize> = order.iter().copied().filter(path).collect();
                let base: Vec<usize> = order.iter().copied().filter(|k| !path(k)).collect();
                let offset = instances.len() as u32;
                let mut draws = Vec::with_capacity(f.records.len());
                let background = [0, 1, 2, 3].map(|k| f.view[VIEW_FLOATS + k]);
                let mut plan = if paths.is_empty() { None } else { Some(gpu.vector.plan(&self.store, &camera, &f.records, &paths, background)?) };
                // where its listed see-through layers can paint: their footprints together (the whole view where one
                // cannot be bounded)
                let mut listed: Option<[f32; 4]> = None;
                let join = |a: Option<[f32; 4]>, b: [f32; 4]| Some(a.map_or(b, |a| [a[0].min(b[0]), a[1].min(b[1]), a[2].max(b[2]), a[3].max(b[3])]));
                // what casts shadows (its meshes and paths, but those fixed in the frame) and what they fall on (those
                // with a material): their boxes in the world
                let (mut casters, mut receivers): (Option<Box3>, Option<Box3>) = (None, None);
                let mut cast_by = |r: &Record| -> Result<(), String> {
                    let b = self.store.world_box(r)?;
                    casters = Some(union(casters, b));
                    if r.material[3] > 0.0 {
                        receivers = Some(union(receivers, b));
                    }
                    Ok(())
                };
                for k in base {
                    let (instance, draw) = self.instance(&camera, &f.records[k], None, k as u32)?;
                    if !draw.overlay && draw.listed() {
                        listed = join(listed, self.store.footprint(&camera, &f.records[k]).unwrap_or([f32::MIN, f32::MIN, f32::MAX, f32::MAX]));
                    }
                    if !draw.overlay && draw.kind == Kind::Mesh {
                        cast_by(&f.records[k])?;
                    }
                    instances.push(instance);
                    draws.push(draw);
                }
                let casting: Vec<usize> = paths.iter().copied().filter(|&k| f.records[k].flags & OVERLAY == 0).collect();
                for &k in &casting {
                    cast_by(&f.records[k])?;
                }
                // its lights' shadow maps, where something casts a shadow and something has a material: each sees the
                // casters and reaches the receivers; its paths planned as each light sees them
                let lights = &f.view[VIEW_LIGHTING + 8..VIEW_OCCLUSION];
                let shadows = match (casters, receivers) {
                    (Some(casters), Some(receivers)) => shadow::fit(lights, f.view[VIEW_LIGHTING + 4] as usize, casters, receivers),
                    _ => Vec::new(),
                };
                let cast = if casting.is_empty() { Vec::new() } else { shadows.iter().map(|s| gpu.vector.plan(&self.store, &Camera::seen_from(s), &f.records, &casting, [0.0; 4])).collect::<Result<_, _>>()? };
                // in whole pixels, on the view: (x, y, width, height)
                let pixels = |area: Option<[f32; 4]>| {
                    let [x0, y0, x1, y1] = area.map_or([0.0; 4], |[x0, y0, x1, y1]| [x0.max(0.0), y0.max(0.0), x1.min(camera.size[0]), y1.min(camera.size[1])]);
                    let (x0, y0) = (x0.floor() as u32, y0.floor() as u32);
                    let (x1, y1) = ((x1.ceil() as u32).max(x0), (y1.ceil() as u32).max(y0));
                    [x0, y0, x1 - x0, y1 - y0]
                };
                let listed = pixels(listed);
                // Transparency has the same depth ordering at every sample count. Point sprites
                // blend between the other layers through slabs; mesh fragments use lists.
                let sprites_here = self.sprites(&instances[offset as usize..], &draws, offset, &mut sprites);
                let lists = draws.iter().any(Draw::listed);
                let slabs = !sprites_here.is_empty() && (lists || !casting.is_empty());
                // its lit meshes' light, kept apart from its paint in its base and shown once by its composite (a
                // camera's integration of what is lit)
                let light = draws.iter().any(|d| d.lit && !d.overlay);
                if (lists || light) && plan.is_none() {
                    plan = Some(gpu.vector.plan(&self.store, &camera, &f.records, &[], background)?);
                }
                if let Some(plan) = plan.as_mut() {
                    plan.light = lighting(&f.view, &shadows, self.environment_light(&f.view));
                }
                // its glow, spread from its lit content's light (without any, there is none to spread)
                let glow = bloom_of(&f.view).filter(|_| light || plan.as_ref().is_some_and(|p| p.lit));
                Drawing::Raster { offset, draws, listed, sprites: sprites_here, lists, slabs, light, glow, plan, shadows, cast }
            } else {
                let background = [0, 1, 2, 3].map(|k| f.view[VIEW_FLOATS + k]);
                let plan = gpu.vector.plan(&self.store, &camera, &f.records, &self.order(&camera, &f.records)?, background)?;
                let mut groups = Vec::with_capacity(plan.groups.len());
                for group in &plan.groups {
                    let offset = instances.len() as u32;
                    let mut draws = Vec::with_capacity(group.rasters.len());
                    for raster in &group.rasters {
                        let (instance, draw) = self.instance(&camera, &f.records[raster.record], Some(plan.place(raster)), raster.record as u32)?;
                        instances.push(instance);
                        draws.push(draw);
                    }
                    groups.push((offset, draws));
                }
                Drawing::Vector(plan, groups)
            };
            drawings.push(drawing);
        }
        let rasters = |d: &Drawing| match d {
            Drawing::Raster { .. } => true,
            Drawing::Vector(_, groups) => groups.iter().any(|(_, draws)| !draws.is_empty()),
        };
        if drawings.iter().any(rasters) {
            for d in &drawings {
                match d {
                    Drawing::Raster { light, .. } => gpu.pipelines(samples, *light),
                    Drawing::Vector(..) if rasters(d) => gpu.pipelines(samples, false),
                    Drawing::Vector(..) => {}
                }
            }
            // the passes its lights' shadow maps are drawn with
            for d in &drawings {
                if let Drawing::Raster { shadows, .. } = d {
                    for s in shadows {
                        gpu.shadow_pass(s.light);
                    }
                }
            }
        }
        self.prepare(gpu, instances.len(), frames.len(), sprites.len())?;
        self.targets(gpu);
        for f in &frames[..frames.len() - 1] {
            self.canvas(gpu, f.key, f.width, f.height);
        }
        // the raster pipeline's attachments: a 3D view's canvas's; the raster atlas's, as large
        // as the 2D views need it
        let mut need = [0u32; 2];
        for (f, d) in frames.iter().zip(&drawings) {
            match d {
                Drawing::Raster { light, glow, slabs, .. } => {
                    let canvas = if f.key == 0 { &mut self.targets.as_mut().expect("targets").frame } else { self.canvases.get_mut(&f.key).expect("canvas") };
                    canvas.attach(gpu, samples, *light);
                    if *slabs {
                        canvas.attach_slabs(gpu, samples);
                    }
                    // and where its ambient occlusion is found, if it has some
                    if occlusion_of(&f.view).is_some() && canvas.occluded.is_none() {
                        let occlusion = gpu.occlusion.get_or_insert_with(|| occlusion::Occlusion::new(&gpu.device, gpu.blend[(samples > 1) as usize].as_ref().expect("the raster pipeline's shader"), &gpu.raster.scene));
                        canvas.occluded = Some(occlusion.occluded(&gpu.device, [canvas.width, canvas.height]));
                    }
                    // and where its glow is made, if it has some
                    if glow.is_some() && canvas.bloomed.is_none() {
                        let bloom = gpu.bloom.get_or_insert_with(|| bloom::Bloom::new(&gpu.device));
                        canvas.bloomed = Some(bloom.bloomed(&gpu.device, &gpu.linear, &canvas.color, [canvas.width, canvas.height]));
                    }
                }
                Drawing::Vector(plan, _) if rasters(d) => need = [need[0].max(plan.raster_size[0]), need[1].max(plan.raster_size[1])],
                Drawing::Vector(..) => {}
            }
        }
        if need[1] > 0 {
            if self.rasters.as_ref().is_none_or(|c| c.width < need[0] || c.height < need[1] || c.height > 2 * need[1] + 256) {
                self.rasters = Some(Canvas::new(gpu, need[0], need[1].div_ceil(64) * 64));
            }
            self.rasters.as_mut().expect("raster atlas").attach(gpu, samples, false);
        }
        let composite: Vec<bool> = drawings.iter().map(|d| matches!(d, Drawing::Raster { lists: true, .. })).collect();
        let composited = composite.contains(&true);
        if composited {
            let pixels = frames.iter().zip(&composite).filter(|(_, c)| **c).map(|(f, _)| if f.key == 0 { self.width as u64 * self.height as u64 } else { self.canvases[&f.key].width as u64 * self.canvases[&f.key].height as u64 }).max().unwrap_or(0);
            self.prepare_lists(gpu, pixels);
            let lists = self.lists.as_ref().expect("lists");
            for (f, _) in frames.iter().zip(&composite).filter(|(_, c)| **c) {
                let canvas = if f.key == 0 { &mut self.targets.as_mut().expect("targets").frame } else { self.canvases.get_mut(&f.key).expect("canvas") };
                let attached = canvas.raster.as_mut().expect("attachments");
                if attached.append.as_ref().is_none_or(|(generation, _)| *generation != lists.generation) {
                    let group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
                        label: Some("append"),
                        layout: &gpu.raster.lists[(samples > 1) as usize],
                        entries: &[whole(0, &lists.heads), whole(1, &lists.nodes), whole(2, &lists.appended), wgpu::BindGroupEntry { binding: 3, resource: wgpu::BindingResource::TextureView(&attached.depth_only) }],
                    });
                    attached.append = Some((lists.generation, group));
                }
            }
        }
        let layers = drawings.iter().map(|d| if let Drawing::Raster { shadows, .. } = d { shadows.len() } else { 0 }).max().unwrap_or(0);
        // the frame's environment (its first view's that has one: they share its cube), prefiltered when first shown
        let shown = frames.iter().find_map(|f| environment_of(&f.view));
        if let Some(id) = shown {
            let env = self.environments.get_mut(&id).ok_or_else(|| format!("unknown environment {id}"))?;
            if env.cube.is_none() {
                let prefilter = gpu.prefilter.get_or_insert_with(|| environment::Prefilter::new(&gpu.device));
                let mut encoder = gpu.device.create_command_encoder(&Default::default());
                env.cube = Some(prefilter.run(&gpu.device, &gpu.queue, &mut encoder, env));
                gpu.queue.submit(Some(encoder.finish()));
                env.rgbe = Vec::new(); // (its cube is what the frames read)
            }
        }
        let cube = shown.and_then(|id| self.environments[&id].cube.clone()).unwrap_or_else(|| gpu.no_environment.clone());
        let buffers = self.buffers.as_mut().expect("buffers");
        if layers > 0 && (buffers.shadow_maps.size < shadow::SIZE || layers > buffers.shadow_maps.layers.len()) {
            buffers.shadow_maps = ShadowMaps::new(gpu, shadow::SIZE, layers as u32, (shown, &cube));
        } else if buffers.shadow_maps.environment != shown {
            buffers.shadow_maps.group = ShadowMaps::bind(gpu, &buffers.shadow_maps.array, &cube, &gpu.no_occlusion);
            buffers.shadow_maps.environment = shown;
        }
        let buffers = self.buffers.as_ref().expect("buffers");
        let targets = self.targets.as_ref().expect("targets");
        gpu.queue.write_buffer(&buffers.instances, 0, bytemuck::cast_slice(&instances));
        gpu.queue.write_buffer(&buffers.sprites, 0, bytemuck::cast_slice(&sprites));
        // view i's raster passes draw with slot i: its pixels (a 2D view's: the raster atlas's),
        // light, toward
        let mut views = vec![0u8; frames.len() * VIEW_STRIDE];
        for (i, (f, d)) in frames.iter().zip(&drawings).enumerate() {
            let v = &f.view;
            let [w, h] = match d {
                Drawing::Raster { .. } => [v[32], v[33]],
                Drawing::Vector(plan, _) => plan.raster_size.map(|p| p as f32),
            };
            let head: [f32; 8] = [w, h, samples as f32, 0.0, v[36], v[37], v[38], v[39]];
            let shadows = match d {
                Drawing::Raster { shadows, .. } => &shadows[..],
                Drawing::Vector(..) => &[],
            };
            let mut light = lighting(v, shadows, self.environment_light(v));
            light[3] = v[43]; // (the raster passes': the stroke depth bias)
            let slot = &mut views[i * VIEW_STRIDE..][..VIEW_BYTES as usize];
            slot[..32].copy_from_slice(bytemuck::cast_slice(&head));
            slot[32..].copy_from_slice(bytemuck::cast_slice(&light));
        }
        gpu.queue.write_buffer(&buffers.views, 0, &views);
        let mut encoder = gpu.device.create_command_encoder(&Default::default());
        gpu.vector.begin();
        let mut grouped = false;
        let lists = self.lists.as_ref().filter(|_| composited);
        if let Some(lists) = lists {
            encoder.clear_buffer(&lists.appended, 0, None);
        }
        let indices = &buffers.statics[2];
        for (i, (f, d)) in frames.iter().zip(&drawings).enumerate() {
            let canvas = if f.key == 0 { &targets.frame } else { &self.canvases[&f.key] };
            let slot = [(i * VIEW_STRIDE) as u32];
            match d {
                Drawing::Raster { offset, draws, listed, sprites, lists: listing, slabs, light, glow, plan, shadows, cast } => {
                    // its lights' shadow maps first: its meshes' depth seen from each, then its paths' where nearer
                    for (layer, s) in shadows.iter().enumerate() {
                        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                            label: Some("shadow"),
                            color_attachments: &[],
                            depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment { view: &buffers.shadow_maps.layers[layer], depth_ops: Some(wgpu::Operations { load: wgpu::LoadOp::Clear(1.0), store: wgpu::StoreOp::Store }), stencil_ops: None }),
                            occlusion_query_set: None,
                            timestamp_writes: None,
                            multiview_mask: None,
                        });
                        pass.set_pipeline(&gpu.shadow_passes[&s.light]);
                        pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                        pass.set_index_buffer(indices.slice(..), wgpu::IndexFormat::Uint32);
                        for (k, draw) in draws.iter().enumerate() {
                            if draw.kind == Kind::Mesh && !draw.overlay && !draw.fill.is_empty() {
                                let k = *offset + k as u32;
                                pass.draw_indexed(draw.fill.clone(), 0, k..k + 1);
                            }
                        }
                        drop(pass);
                        if let Some(plan) = cast.get(layer) {
                            let statics = buffers.vector_statics();
                            for g in 0..plan.groups.len() {
                                gpu.vector.encode(&gpu.device, &gpu.queue, &mut encoder, plan, g, &statics, vector::Out::Depth(&buffers.shadow_maps.layers[layer]));
                            }
                        }
                    }
                    // its ambient occlusion: its opaque depth (its opaque meshes', then its opaque paths' where nearer),
                    // then how much of the light from all around reaches each pixel's surface; its lit passes read it
                    let occluded = canvas.occluded.as_ref().zip(occlusion_of(&f.view));
                    let own_lighting = occluded.map(|(o, (amount, radius))| {
                        let occlusion = gpu.occlusion.as_ref().expect("the occlusion's passes");
                        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                            label: Some("occlusion depth"),
                            color_attachments: &[],
                            depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment { view: &o.depth, depth_ops: Some(wgpu::Operations { load: wgpu::LoadOp::Clear(0.0), store: wgpu::StoreOp::Store }), stencil_ops: None }),
                            occlusion_query_set: None,
                            timestamp_writes: None,
                            multiview_mask: None,
                        });
                        pass.set_pipeline(&occlusion.depth);
                        pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                        pass.set_index_buffer(indices.slice(..), wgpu::IndexFormat::Uint32);
                        for (k, draw) in draws.iter().enumerate() {
                            if draw.kind == Kind::Mesh && !draw.overlay && !draw.see_through[0] && !draw.fill.is_empty() {
                                let k = *offset + k as u32;
                                pass.draw_indexed(draw.fill.clone(), 0, k..k + 1);
                            }
                        }
                        drop(pass);
                        if let Some(plan) = plan {
                            let statics = buffers.vector_statics();
                            for g in 0..plan.groups.len() {
                                gpu.vector.encode(&gpu.device, &gpu.queue, &mut encoder, plan, g, &statics, vector::Out::Opaque(&o.depth));
                            }
                        }
                        occlusion.encode(&gpu.queue, &mut encoder, o, &Camera::new(&f.view).projection, amount, radius);
                        ShadowMaps::bind(gpu, &buffers.shadow_maps.array, &cube, &o.out)
                    });
                    let lighting_group = own_lighting.as_ref().unwrap_or(&buffers.shadow_maps.group);
                    let occlusion = occluded.map_or(&gpu.no_occlusion, |(o, _)| &o.out);
                    // the base: the view over the background, or (where its paths lie over and under it) a layer of
                    // its own, in a texture of its own; none where it has nothing to rasterize (its paths are the view)
                    let rasterized = !draws.is_empty();
                    let base = plan.as_ref().filter(|_| rasterized).map(|_| gpu.vector.base(&gpu.device, [canvas.width, canvas.height]));
                    let base_light = light.then(|| gpu.vector.base_light(&gpu.device, [canvas.width, canvas.height]));
                    let background = if plan.is_some() { [0.0; 4] } else { [0, 1, 2, 3].map(|k| f.view[VIEW_FLOATS + k] as f64) };
                    let cleared = clear([background[0] * background[3], background[1] * background[3], background[2] * background[3], background[3]]);
                    let pipelines = &gpu.pipelines[&(samples, *light)];
                    // sprites, six vertices each, drawn with `pipeline`
                    let draw_sprites = |pass: &mut wgpu::RenderPass, pipeline: &wgpu::RenderPipeline, range: &Range<u32>| {
                        if !range.is_empty() {
                            pass.set_pipeline(pipeline);
                            pass.draw(6 * range.start..6 * range.end, 0..1);
                        }
                    };
                    // its composite: its paths in depth order with the base (its depth one float a pixel) and its
                    // listed fragments; then, where it glows, its glow spread from the light it leaves, and its pixels
                    // shown with it
                    let bloomed = canvas.bloomed.as_ref().zip(*glow);
                    let layered = |encoder: &mut wgpu::CommandEncoder, vector: &mut vector::Vector, listed: Option<&vector::Listed>, slabs: Option<&Slabs>| {
                        let Some(plan) = plan else { return };
                        let statics = buffers.vector_statics();
                        let (target, light_out) = bloomed.map_or((&canvas.color, None), |(b, _)| (&b.paint, Some(&b.light)));
                        for g in 0..plan.groups.len() {
                            let lighting = vector::Lighting { maps: &buffers.shadow_maps.array, compare: &gpu.shadow_compare, dfg: &gpu.dfg, linear: &gpu.linear, environment: &cube, occlusion };
                            let slabs = slabs.map(|s| [&s.bounds, &s.slabs]);
                            let out = vector::Out::Color { rasters: None, target, base: base.as_ref(), light: base_light.as_ref(), listed, slabs, lighting, light_out };
                            vector.encode(&gpu.device, &gpu.queue, encoder, plan, g, &statics, out);
                        }
                        if let Some((b, strength)) = bloomed {
                            let tone = f.view[VIEW_LIGHTING + 6].round() as u32;
                            gpu.bloom.as_ref().expect("the bloom's passes").encode(&gpu.queue, encoder, b, strength, tone);
                        }
                    };
                    if !(*listing || *slabs) {
                        if rasterized || plan.is_none() {
                            let mut pass = canvas.pass(&mut encoder, Some((cleared, true)), if plan.is_some() { Depth::Kept } else { Depth::Fresh }, base.as_ref(), base_light.as_ref());
                            pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                            pass.set_bind_group(3, lighting_group, &[]);
                            if sprites.is_empty() {
                                self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::All);
                            } else {
                                // the sprites over everything else but what is fixed in the frame
                                self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::Opaque);
                                draw_sprites(&mut pass, &pipelines.sprites, sprites);
                                self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::Overlay);
                            }
                        }
                        if base.is_some() {
                            let attached = canvas.raster.as_ref().expect("the raster pipeline's attachments");
                            gpu.vector.resolve_depth(&gpu.device, &mut encoder, &attached.depth_only, samples, [canvas.width, canvas.height]);
                        }
                        layered(&mut encoder, &mut gpu.vector, None, None);
                        continue;
                    }
                    let appends = &pipelines.appends;
                    // the opaque layers, their samples and depth kept
                    {
                        let mut pass = canvas.pass(&mut encoder, Some((cleared, false)), Depth::Kept, base.as_ref(), base_light.as_ref());
                        pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                        pass.set_bind_group(3, lighting_group, &[]);
                        self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::Opaque);
                    }
                    let attached = canvas.raster.as_ref().expect("the raster pipeline's attachments");
                    let colors = attached.msaa.as_ref().or(base.as_ref()).expect("base samples");
                    let [_, y, _, h] = *listed;
                    let listed = lists.filter(|_| *listing).map(|l| vector::Listed { heads: &l.heads, nodes: &l.nodes, rows: [y, y + h], samples, colors, depths: &attached.depth_only, lights: attached.msaa_light.as_ref().or(base_light.as_ref()) });
                    // the listed see-through layers appended to the lists (only in their rows are heads cleared and read)
                    if let Some(l) = &listed {
                        let row = canvas.width as u64 * 4;
                        if h > 0 {
                            encoder.clear_buffer(l.heads, y as u64 * row, Some(h as u64 * row));
                        }
                        let append = &attached.append.as_ref().expect("the appends' group").1;
                        let mut pass = canvas.pass(&mut encoder, None, Depth::Read, None, None);
                        pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                        pass.set_bind_group(3, lighting_group, &[]);
                        pass.set_bind_group(2, append, &[]);
                        self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::SeeThrough);
                    }
                    // the sprites among its other see-through layers: the depths of each pixel's nearest found (its
                    // paths' and its listed fragments'), then each sprite blended into the slab between them it lies in
                    let slabs = attached.slabs.as_ref().filter(|_| *slabs);
                    if let Some(s) = slabs {
                        let plan = plan.as_ref().expect("a plan: its paths', or its lists'");
                        let statics = buffers.vector_statics();
                        gpu.vector.encode(&gpu.device, &gpu.queue, &mut encoder, plan, 0, &statics, vector::Out::Bounds { out: &s.bounds, listed: listed.as_ref() });
                        let targets: Vec<_> = s.layers.iter().map(|view| Some(wgpu::RenderPassColorAttachment { view, depth_slice: None, resolve_target: None, ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT), store: wgpu::StoreOp::Store } })).collect();
                        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor { label: Some("slabs"), color_attachments: &targets, depth_stencil_attachment: None, occlusion_query_set: None, timestamp_writes: None, multiview_mask: None });
                        pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                        pass.set_bind_group(2, &s.groups[1], &[]);
                        draw_sprites(&mut pass, &appends.slabs, sprites);
                    }
                    // the sprites behind no other see-through layer blended into the base, depth tested against the
                    // opaque depth kept for them (and kept again, with the samples, for the composite), and what is
                    // fixed in the frame drawn over them; then the composite
                    let mut pass = canvas.pass(&mut encoder, Some((wgpu::LoadOp::Load, true)), Depth::Shared, base.as_ref(), base_light.as_ref());
                    pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                    pass.set_bind_group(3, lighting_group, &[]);
                    pass.set_bind_group(1, &self.image_groups[&0], &[]);
                    match slabs {
                        Some(s) => {
                            pass.set_bind_group(2, &s.groups[0], &[]);
                            draw_sprites(&mut pass, &appends.sprites, sprites);
                        }
                        None => draw_sprites(&mut pass, &pipelines.sprites, sprites),
                    }
                    self.draw(&mut pass, pipelines, indices, draws, *offset, Phase::Overlay);
                    drop(pass);
                    gpu.vector.resolve_depth(&gpu.device, &mut encoder, &attached.depth_only, samples, [canvas.width, canvas.height]);
                    layered(&mut encoder, &mut gpu.vector, listed.as_ref(), slabs);
                }
                Drawing::Vector(plan, groups) => {
                    grouped |= f.key == 0 && plan.groups.len() > 1;
                    for (g, (offset, draws)) in groups.iter().enumerate() {
                        let atlas = self.rasters.as_ref().filter(|_| !draws.is_empty());
                        if let Some(atlas) = atlas {
                            let mut pass = atlas.pass(&mut encoder, Some((clear([0.0; 4]), true)), Depth::Fresh, None, None);
                            pass.set_viewport(0.0, 0.0, plan.raster_size[0] as f32, plan.raster_size[1] as f32, 0.0, 1.0);
                            pass.set_bind_group(0, buffers.group.as_ref(), &slot);
                            pass.set_bind_group(3, &buffers.shadow_maps.group, &[]);
                            for (j, raster) in plan.groups[g].rasters.iter().enumerate() {
                                let [x, y, w, h] = raster.rect;
                                pass.set_scissor_rect(x, y, w, h);
                                self.draw(&mut pass, &gpu.pipelines[&(samples, false)], indices, &draws[j..j + 1], offset + j as u32, Phase::All);
                            }
                        }
                        let statics = buffers.vector_statics();
                        let lighting = vector::Lighting { maps: &buffers.shadow_maps.array, compare: &gpu.shadow_compare, dfg: &gpu.dfg, linear: &gpu.linear, environment: &cube, occlusion: &gpu.no_occlusion };
                        let out = vector::Out::Color { rasters: atlas.map(|a| &a.color), target: &canvas.color, base: None, light: None, listed: None, slabs: None, lighting, light_out: None };
                        gpu.vector.encode(&gpu.device, &gpu.queue, &mut encoder, plan, g, &statics, out);
                    }
                }
            }
        }
        Ok((encoder, grouped, composited))
    }

    /// The lists, with a head for each of `pixels` and room for `list_capacity` nodes (a node
    /// per pixel to begin with; more once a frame needs it).
    pub(crate) fn prepare_lists(&mut self, gpu: &Gpu, pixels: u64) {
        let most = gpu.device.limits().max_storage_buffer_binding_size / NODE_BYTES;
        self.list_capacity = self.list_capacity.max(pixels).min(most);
        let pixels = pixels.max(self.lists.as_ref().map_or(0, |l| l.pixels));
        if self.lists.as_ref().is_some_and(|l| l.pixels >= pixels && l.capacity >= self.list_capacity) {
            return;
        }
        let buffer = |label, size: u64, usage| gpu.device.create_buffer(&wgpu::BufferDescriptor { label: Some(label), size, usage: wgpu::BufferUsages::STORAGE | usage, mapped_at_creation: false });
        let heads = buffer("heads", pixels * 4, wgpu::BufferUsages::COPY_DST);
        let nodes = buffer("nodes", self.list_capacity * NODE_BYTES, wgpu::BufferUsages::empty());
        let appended = buffer("appended", 16, wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC);
        let generation = self.lists.as_ref().map_or(0, |l| l.generation + 1);
        self.lists = Some(Lists { heads, nodes, appended, pixels, capacity: self.list_capacity, generation });
    }

    /// A frame's lists held `appended` nodes: whether they overflowed (then they are given room
    /// for them, and the frame must be drawn again) — never past the most a buffer can bind.
    pub(crate) fn overflowed(&mut self, gpu: &Gpu, appended: u64, capacity: u64) -> bool {
        let most = gpu.device.limits().max_storage_buffer_binding_size / NODE_BYTES;
        if appended <= capacity || capacity >= most {
            return false;
        }
        self.list_capacity = self.list_capacity.max(appended.next_power_of_two()).min(most);
        true
    }

    fn draw(&self, pass: &mut wgpu::RenderPass, pipelines: &Pipelines, indices: &wgpu::Buffer, draws: &[Draw], offset: u32, phase: Phase) {
        let white = &self.image_groups[&0];
        pass.set_bind_group(1, white, &[]);
        pass.set_index_buffer(indices.slice(..), wgpu::IndexFormat::Uint32);
        pass.set_stencil_reference(0);
        let mut current: *const wgpu::RenderPipeline = std::ptr::null();
        let appends = (phase == Phase::SeeThrough).then_some(&pipelines.appends);
        for (k, draw) in draws.iter().enumerate() {
            if phase != Phase::All && draw.overlay != (phase == Phase::Overlay) {
                continue;
            }
            // whether this pass draws its layer: its points or triangles, its edges (a see-through
            // point cloud's are sprites, not appended here)
            let drawn = |layer: usize| match phase {
                Phase::All | Phase::Overlay => true,
                Phase::Opaque => !draw.see_through[layer],
                Phase::SeeThrough => draw.see_through[layer] && draw.kind != Kind::Points,
            };
            let k = offset + k as u32;
            // a layer blended once per sample: counted into the stencil, then covered; or
            // appended fragment by fragment (the resolve counts it once)
            let layer = |pass: &mut wgpu::RenderPass, current: &mut *const wgpu::RenderPipeline, passes: &Passes, append: Option<&wgpu::RenderPipeline>, range: &Range<u32>| match append {
                Some(append) => run(pass, current, append, range, k),
                None => {
                    run(pass, current, &passes.count, range, k);
                    run(pass, current, &passes.cover, range, k);
                }
            };
            let sg = draw.stroke_gradient as usize;
            let (stroke, stroke_append) = (&pipelines.stroke[sg], appends.map(|a| &a.stroke[sg]));
            match draw.kind {
                Kind::Path => {} // (drawn exactly, by the composite)
                Kind::Points => {
                    if drawn(0) {
                        run(pass, &mut current, &pipelines.points, &draw.stroke, k);
                    }
                }
                Kind::Mesh => {
                    if drawn(0) {
                        if draw.texture != 0 { // (the white image is bound for everything else)
                            pass.set_bind_group(1, self.image_groups.get(&draw.texture).unwrap_or(white), &[]);
                        }
                        if draw.lit {
                            pass.set_blend_constant(wgpu::Color { r: 0.0, g: 0.0, b: 0.0, a: 1.0 }); // (its light: `Base`)
                        }
                        run(pass, &mut current, appends.map_or(&pipelines.mesh, |a| &a.mesh), &draw.fill, k);
                        if draw.lit {
                            pass.set_blend_constant(wgpu::Color::TRANSPARENT);
                        }
                        if draw.texture != 0 {
                            pass.set_bind_group(1, white, &[]);
                        }
                    }
                    if draw.stroked && drawn(1) {
                        layer(pass, &mut current, stroke, stroke_append, &draw.stroke); // its faces' edges
                    }
                }
            }
        }
    }
}

/// What every host asks of a player: shapes, brushes and images uploaded once under a key, then
/// frames drawn from views and records (see `python` and `web`).
impl Player {
    pub(crate) fn new(width: u32, height: u32, samples: u32) -> Self {
        Self {
            width,
            height,
            samples,
            store: Store::default(),
            images: Keyed::default(),
            opaque_images: Keyed::default(),
            environments: HashMap::new(),
            image_groups: Keyed::default(),
            canvases: Keyed::default(),
            rasters: None,
            buffers: None,
            targets: None,
            #[cfg(feature = "export")]
            export: None,
            lists: None,
            list_capacity: 0,
        }
    }

    /// A path: its control points (float64 x, y, z; four per curve), its subpaths (u32 first
    /// curve, end curve, closed, 0) and (centroid, Newell area vector) of its control points.
    pub(crate) fn add_path(&mut self, key: u64, points: &[u8], subpaths: &[u8], centroid_area: [f32; 6]) -> Result<(), String> {
        check_key(key)?;
        let points: Vec<[f64; 3]> = read(points, "points")?;
        let ranges: Vec<[u32; 4]> = read(subpaths, "subpaths")?;
        if !points.len().is_multiple_of(4) || ranges.iter().any(|r| r[0] >= r[1] || r[1] as usize > points.len() / 4) {
            return Err("a path is whole curves, its subpaths ranges of them".into());
        }
        let [cx, cy, cz, ax, ay, az] = centroid_area;
        self.store.add_path(key, &points, &ranges, [cx, cy, cz], [ax, ay, az]);
        Ok(())
    }

    /// A point cloud: positions (x, y, z, 0).
    pub(crate) fn add_points(&mut self, key: u64, vertices: &[u8]) -> Result<(), String> {
        check_key(key)?;
        self.store.add_points(key, &read(vertices, "vertices")?);
        Ok(())
    }

    /// A mesh as its object defines it: its points and texture coordinates (float64 x, y, z and
    /// u, v), its triangles (three u32 each) and its normals (float64) when its geometry gives
    /// them — a surface's spline, a flat face — or none, for the area-weighted sum of each
    /// vertex's faces. `outline` > 2: the vertices are faces — blocks of `block` (by default
    /// `outline`), each beginning with a closed loop of `outline` — stroked when drawn.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn add_mesh(&mut self, key: u64, points: &[u8], uvs: &[u8], normals: &[u8], triangles: &[u8], outline: u32, block: u32) -> Result<(), String> {
        check_key(key)?;
        let mesh = Mesh::new(points, uvs, normals, triangles, outline, block)?;
        let v: Vec<[f32; 4]> = mesh.points.iter().zip(&*mesh.uvs).map(|(p, uv)| [p[0] as f32, p[1] as f32, p[2] as f32, uv[1] as f32]).collect();
        let e: Vec<[f32; 4]> = mesh.normals.iter().zip(&*mesh.uvs).map(|(n, uv)| [n[0] as f32, n[1] as f32, n[2] as f32, uv[0] as f32]).collect();
        self.store.add_mesh(key, &v, &e, &mesh.triangles, mesh.outline, mesh.block);
        Ok(())
    }

    /// Append curves to a path: its last subpath continues with these control points (float64
    /// x, y, z; four per curve); `closed`: whether that subpath now ends where it begins.
    pub(crate) fn grow_path(&mut self, key: u64, points: &[u8], closed: bool) -> Result<(), String> {
        let tail: Vec<[f64; 3]> = read(points, "points")?;
        if !tail.len().is_multiple_of(4) {
            return Err("a path grows by whole curves".into());
        }
        self.store.grow_path(key, &tail, closed)
    }

    #[cfg(any(feature = "python", feature = "player"))]
    /// Forget shapes, brushes and textures no frame shows any more (unknown keys are ignored);
    /// the shapes' space is reused once most of the store is dead.
    pub(crate) fn evict(&mut self, keys: &[u64]) {
        self.store.evict(keys);
        for key in keys {
            // a texture goes with its key (key 0, the white image, is never a texture's)
            if *key != 0 {
                self.images.remove(key);
                self.opaque_images.remove(key);
                self.image_groups.remove(key);
            }
        }
    }

    #[cfg(feature = "python")]
    /// (bytes in the store's arrays, of which dead).
    pub(crate) fn stored(&self) -> (usize, usize) {
        (self.store.bytes(), self.store.dead)
    }

    #[cfg(feature = "python")]
    /// Whether retaining the current cache exceeds an individual GPU buffer's capacity.
    pub(crate) fn pressured(&self, gpu: &Gpu) -> bool {
        !self.store.fits(&gpu.device.limits())
    }

    #[cfg(feature = "player")]
    /// Whether it holds `key`: a shape, brush or texture.
    pub(crate) fn has(&self, key: u64) -> bool {
        self.store.shapes.contains_key(&key) || self.store.brushes.contains_key(&key) || self.images.contains_key(&key)
    }

    #[cfg(feature = "player")]
    /// The bytes it holds alive: its arrays' (the GPU's copy mirrors them) and its textures'.
    pub(crate) fn held(&self) -> usize {
        self.store.bytes() - self.store.dead + self.images.values().map(|(_, _, rgba)| rgba.len()).sum::<usize>()
    }

    /// A brush of several rows (RGBA): gradient stops, or one color per point or vertex.
    pub(crate) fn add_rows(&mut self, key: u64, rows: &[u8]) -> Result<(), String> {
        check_key(key)?;
        self.store.add_rows(key, &read(rows, "rows")?);
        Ok(())
    }

    /// An image: straight RGBA8 rows, top to bottom (premultiplied on the way in).
    pub(crate) fn add_texture(&mut self, key: u64, width: u32, height: u32, rgba: &[u8]) -> Result<(), String> {
        check_key(key)?;
        if rgba.len() != (width * height * 4) as usize {
            return Err("texture size does not match its bytes".into());
        }
        if rgba.chunks_exact(4).all(|p| p[3] == 255) {
            self.opaque_images.insert(key, ());
        }
        self.images.insert(key, (width, height, rgba.to_vec()));
        Ok(())
    }

    /// An environment (an `EnvironmentLight`'s picture: equirectangular RGBE rows, top to bottom), the id its views'
    /// lights give it.
    pub(crate) fn add_environment(&mut self, id: u32, width: u32, height: u32, rgbe: &[u8]) -> Result<(), String> {
        if rgbe.len() != (width * height * 4) as usize || width == 0 || height == 0 {
            return Err("environment size does not match its bytes".into());
        }
        self.environments.insert(id, environment::Environment::new(width, height, rgbe.to_vec()));
        Ok(())
    }

    /// A view's environment's diffuse light and its cube's unit (none: 0 and 1).
    fn environment_light(&self, view: &[f32]) -> ([[f32; 4]; 9], f32) {
        environment_of(view).and_then(|id| self.environments.get(&id)).map_or(([[0.0; 4]; 9], 1.0), |e| (e.harmonics, e.unit))
    }

    /// Views to draw: the cameras' (each into a texture that later views sample by its key), then
    /// the frame; each with the lights the engine lights by (`with_sun`).
    pub(crate) fn views(&mut self, view: &[u8], records: &[u8], cameras: Vec<CameraView>) -> Result<Vec<Frame>, String> {
        let mut frames = Vec::with_capacity(cameras.len() + 1);
        for (key, width, height, v, r) in cameras {
            check_key(key)?;
            frames.push(Frame { key, width, height, view: self.with_sun(read(&v, "view")?), records: read(&r, "records")? });
        }
        frames.push(Frame { key: 0, width: self.width, height: self.height, view: self.with_sun(read(view, "view")?), records: read(records, "records")? });
        Ok(frames)
    }

    /// A view's lights as the engine lights by them: its own, then its environment's sun (`environment::Sun`, lifted
    /// out of its picture) as a sun of the view's, turned with the environment, tinted as it is, casting shadows if the
    /// environment does. The built-in studio is made when a view first shows it.
    fn with_sun(&mut self, mut view: Vec<f32>) -> Vec<f32> {
        if view.len() < VIEW_LENGTH {
            return view;
        }
        let Some(at) = (0..LIGHTS).map(|l| VIEW_LIGHTING + 8 + 16 * l).find(|&at| view[at + 3].round() as u32 == 4) else { return view };
        let id = view[at + 7].round() as u32;
        if id == environment::STUDIO {
            self.environments.entry(id).or_insert_with(|| {
                let (width, height, pixels) = environment::studio();
                environment::Environment::new(width, height, pixels)
            });
        }
        let count = view[VIEW_LIGHTING + 4] as usize;
        let Some(sun) = self.environments.get(&id).and_then(|e| e.sun).filter(|_| count < LIGHTS) else { return view };
        let slot = &view[at..at + 16];
        let (right, up) = ([slot[0], slot[1], slot[2]], [slot[8], slot[9], slot[10]]);
        let side = [up[1] * right[2] - up[2] * right[1], up[2] * right[0] - up[0] * right[2], up[0] * right[1] - up[1] * right[0]];
        let toward: [f32; 3] = std::array::from_fn(|k| right[k] * sun.toward[0] + side[k] * sun.toward[1] + up[k] * sun.toward[2]);
        let light: [f32; 3] = std::array::from_fn(|k| slot[4 + k] * sun.light[k]);
        let shadows = slot[13];
        let to = VIEW_LIGHTING + 8 + 16 * count;
        view[to..to + 16].copy_from_slice(&[toward[0], toward[1], toward[2], 1.0, light[0], light[1], light[2], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, shadows, 0.0, 0.0]);
        view[VIEW_LIGHTING + 4] = (count + 1) as f32;
        view
    }
}

/// The lists' count, as read back after a frame's pixels.
pub(crate) const COUNT_BYTES: u64 = 4;

pub(crate) fn count(bytes: &[u8]) -> u64 {
    bytemuck::pod_read_unaligned::<u32>(&bytes[..4]) as u64
}

#[cfg(test)]
mod buffer_contract {
    use super::*;

    #[test]
    fn growth_never_exposes_more_than_the_binding_allows() {
        for stride in [1, 8, 16, size_of::<Instance>() as u64, VIEW_STRIDE as u64] {
            for limit in [1024, 1600, 4096, 65536] {
                for needed in [0, 1, limit / stride, limit / stride + 1] {
                    let room = buffer_room(needed, stride, 1024, limit, "test");
                    if needed <= limit / stride {
                        let room = room.unwrap();
                        assert!(room >= needed);
                        assert!(room * stride <= limit);
                    } else {
                        assert!(room.unwrap_err().contains("GPU's buffer limit"));
                    }
                }
            }
        }
    }

    #[test]
    fn binding_pressure_reclaims_a_dead_minority() {
        let mut store = Store::default();
        for key in 1..=3 {
            store.add_rows(key, &[[key as f32, 0.0, 0.0, 1.0]; 40]);
        }
        store.evict(&[2]);
        assert!(store.dead * 2 < store.bytes());
        let limits = wgpu::Limits { max_storage_buffer_binding_size: 1280, ..Default::default() };
        assert!(!store.fits(&limits));
        store.pack_if_worthwhile(true);
        assert!(store.fits(&limits));
        assert_eq!(store.dead, 0);
        for key in [1, 3] {
            let brush = &store.brushes[&key];
            assert_eq!(&store.rows[brush.offset as usize..(brush.offset + brush.count) as usize], &[[key as f32, 0.0, 0.0, 1.0]; 40]);
        }
    }

    fn retained_frames() -> Player {
        let mut player = Player::new(1, 1, 1);
        for key in 1..=3 {
            player.store.add_points(key, &[[key as f32, 0.0, 0.0, 0.0]; 80]);
            player.store.add_rows(key + 10, &[[key as f32, 0.0, 0.0, 1.0]; 80]);
        }
        player.store.dirty.push((0, 16..32));
        player
    }

    fn frame(camera: u64, shape: u64) -> Frame {
        Frame { key: camera, width: 1, height: 1, view: Vec::new(), records: vec![Record { key1: shape, fill_rows: shape + 10, ..Zeroable::zeroed() }] }
    }

    #[test]
    fn a_draw_uses_every_camera_but_does_not_evict_other_frames_even_on_error() {
        let mut player = retained_frames();
        let limits = wgpu::Limits { max_storage_buffer_binding_size: 2560, ..Default::default() };
        let frames = [frame(9, 3), frame(0, 1)];
        for fail in [false, true, false] {
            let generation = player.store.generation;
            let result = player.with_working_set(&limits, &frames, |p| {
                assert!(p.store.fits(&limits));
                assert_eq!(p.store.shapes.len(), 2);
                assert_eq!(p.store.brushes.len(), 2);
                assert!(!p.store.shapes.contains_key(&2));
                let moved = &p.store.shapes[&3];
                assert_eq!(moved.base, 80);
                assert_eq!(p.store.indices[moved.raster.stroke.start as usize] >> 3, 80);
                assert_eq!(p.store.vertices[moved.base as usize][0], 3.0);
                let rows = &p.store.brushes[&13];
                assert_eq!(p.store.rows[rows.offset as usize][0], 3.0);
                assert!(p.store.dirty.is_empty());
                // As preparation does: temporary writes are consumed independently.
                p.store.dirty.clear();
                if fail { Err("rejected frame".into()) } else { Ok(()) }
            });
            assert_eq!(result.is_err(), fail);
            assert_eq!(player.store.shapes.len(), 3);
            assert_eq!(player.store.brushes.len(), 3);
            assert_eq!(player.store.shapes[&3].base, 160);
            assert_eq!(player.store.dirty, [(0, 16..32)]);
            assert!(player.store.generation > generation);
        }
    }

    #[test]
    fn a_frame_that_itself_exceeds_capacity_is_rejected_without_losing_residency() {
        let mut player = retained_frames();
        let limits = wgpu::Limits { max_storage_buffer_binding_size: 2560, ..Default::default() };
        let frames = [frame(8, 1), frame(9, 2), frame(0, 3)];
        let result = player.with_working_set(&limits, &frames, |_| -> Result<(), String> { panic!("oversized frame reached the GPU") });
        assert!(result.unwrap_err().contains("resident vertices requires 3840 bytes"));
        assert_eq!(player.store.shapes.len(), 3);
        assert_eq!(player.store.dirty, [(0, 16..32)]);
    }

    /// Alternating working sets must upload their own offsets, including after ordinary
    /// residency fits again. Compare actual pixels with the same draws without projection.
    #[test]
    fn projected_residency_preserves_pixels_across_draws() {
        fn player() -> Player {
            let mut p = Player::new(64, 64, 4);
            for key in 1..=3 {
                p.store.add_points(key, &[[key as f32 * 0.4 - 0.8, 0.0, 0.5, 0.0]; 80]);
                let mut color = [0.0, 0.0, 0.0, 1.0];
                color[key as usize - 1] = 1.0;
                p.store.add_rows(key + 10, &[color; 80]);
            }
            p
        }
        fn image(p: &mut Player, gpu: &mut Gpu, limits: &wgpu::Limits, key: u64) -> Vec<u8> {
            let mut f = frame(0, key);
            (f.width, f.height) = (64, 64);
            f.view = vec![0.0; VIEW_LENGTH];
            for at in [0, 16] {
                for i in 0..4 {
                    f.view[at + i * 5] = 1.0;
                }
            }
            f.view[32..36].copy_from_slice(&[64.0, 64.0, 32.0, 1.0]);
            f.view[39] = 1.0;
            f.view[42] = 1.0;
            f.view[47] = 1.0;
            let r = &mut f.records[0];
            r.m1 = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]];
            r.fill = [1.0; 4];
            r.params[1] = 80.0;
            r.gradient_a[3] = 0.25;
            let frames = [f];
            let (mut encoder, _, listed) = p.with_working_set(limits, &frames, |p| p.encode_frame(gpu, &frames)).unwrap();
            assert!(!listed);
            let buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor { label: None, size: 64 * 64 * 4, usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ, mapped_at_creation: false });
            encoder.copy_texture_to_buffer(
                wgpu::TexelCopyTextureInfo { texture: p.targets.as_ref().unwrap().frame.color.texture(), mip_level: 0, origin: wgpu::Origin3d::ZERO, aspect: wgpu::TextureAspect::All },
                wgpu::TexelCopyBufferInfo { buffer: &buffer, layout: wgpu::TexelCopyBufferLayout { offset: 0, bytes_per_row: Some(256), rows_per_image: Some(64) } },
                wgpu::Extent3d { width: 64, height: 64, depth_or_array_layers: 1 },
            );
            gpu.queue.submit(Some(encoder.finish()));
            buffer.slice(..).map_async(wgpu::MapMode::Read, |r| r.unwrap());
            gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
            buffer.slice(..).get_mapped_range().unwrap().to_vec()
        }
        with_gpu(|gpu| {
            let limits = wgpu::Limits { max_storage_buffer_binding_size: 2560, ..gpu.device.limits() };
            let (mut projected, mut reference) = (player(), player());
            let mut images = Vec::new();
            for key in [1, 3, 2, 1] {
                let expected = image(&mut reference, gpu, &gpu.device.limits(), key);
                assert!(expected.chunks_exact(4).any(|pixel| pixel[..3] != [0, 0, 0]));
                assert_eq!(image(&mut projected, gpu, &limits, key), expected);
                images.push(expected);
            }
            assert_ne!(images[0], images[1]);
            for p in [&mut projected, &mut reference] {
                p.store.evict(&[2, 3, 12, 13]);
            }
            assert_eq!(image(&mut projected, gpu, &limits, 1), image(&mut reference, gpu, &gpu.device.limits(), 1));
        }).unwrap();
    }
}
