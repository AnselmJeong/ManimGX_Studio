//! Versioned arrays: how a take codes what it uploads (see `take`).
//!
//! A take's uploads are arrays — a mesh's points, uvs, normals and triangles; a path's control
//! points and subpaths; a cloud's points; a brush's rows; an image's pixels; a frame's records —
//! each under a key of its kind and content, sent once. An array that replaces another (the same
//! object's, in the same role, the frame before: its base) is coded against it: a film's shapes
//! change a little from frame to frame, so what is sent is their change. Of these codings, the
//! smallest is kept:
//!
//! - `ALONE`: the array itself;
//! - `FIRST`: its difference from the base;
//! - `SECOND`: its difference from the linear prediction `2 base − base's base` (floats: what
//!   moves smoothly moves on);
//! - `TAIL`: the base is its start, and the rest is new.
//!
//! Floats are differenced as the integers that order as they do, so a small change is a small
//! integer. The integers are laid out lane by lane (x's, then y's, then z's) and byte by byte,
//! then compressed with zstd. Floats go at the precision the GPU draws them: a mesh's float64
//! points are rounded to float32 on the way in (measured on the example films: about one pixel
//! in 200,000 changes, by one level). A chain of versions is cut every `DEPTH` (a keyframe), so
//! any version decodes from a keyframe and a few differences.

use bytemuck::Pod;

pub(crate) const ALONE: u8 = 0;
pub(crate) const FIRST: u8 = 1;
pub(crate) const SECOND: u8 = 2;
pub(crate) const TAIL: u8 = 3;

/// Versions in a chain before a keyframe.
#[cfg(any(feature = "python", feature = "player", test))]
pub(crate) const DEPTH: u8 = 32;

/// What an array holds: its elements' type and how many lanes make one (coded lane by lane).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u8)]
pub(crate) enum Kind {
    MeshPoints,    // float32 x, y, z (float64 in, rounded)
    MeshUvs,       // float32 u, v (float64 in, rounded)
    MeshNormals,   // float32 x, y, z (float64 in, rounded)
    MeshTriangles, // u32
    PathPoints,    // float64 x, y, z: control points, four per curve
    PathSubpaths,  // u32 × 4
    Points,        // float32 × 4
    Rows,          // float32 × 4
    Texture,       // u8 × 4
    Records,       // u32 × 84: a frame's records (`take::RECORD` bytes each)
}

impl Kind {
    #[cfg(any(feature = "player", test))]
    pub(crate) fn from_u8(k: u8) -> Result<Kind, String> {
        use Kind::*;
        [MeshPoints, MeshUvs, MeshNormals, MeshTriangles, PathPoints, PathSubpaths, Points, Rows, Texture, Records].get(k as usize).copied().ok_or_else(|| format!("unknown array kind {k}"))
    }

    /// Bytes an element takes, as the take carries it.
    pub(crate) fn width(self) -> usize {
        match self {
            Kind::PathPoints => 8,
            Kind::Texture => 1,
            _ => 4,
        }
    }

    fn lanes(self) -> usize {
        match self {
            Kind::MeshPoints | Kind::MeshNormals | Kind::PathPoints => 3,
            Kind::MeshUvs => 2,
            Kind::PathSubpaths | Kind::Points | Kind::Rows | Kind::Texture => 4,
            Kind::MeshTriangles => 1,
            Kind::Records => crate::take::RECORD / 4,
        }
    }

    fn float(self) -> bool {
        !matches!(self, Kind::MeshTriangles | Kind::PathSubpaths | Kind::Texture | Kind::Records)
    }

    /// Whether it arrives as float64 and goes as float32.
    #[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
    pub(crate) fn rounded(self) -> bool {
        matches!(self, Kind::MeshPoints | Kind::MeshUvs | Kind::MeshNormals)
    }
}

/// The array as a take carries it: a mesh's float64s as float32s, anything else as it is.
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
pub(crate) fn canonical(kind: Kind, data: &[u8]) -> Vec<u8> {
    if kind.rounded() {
        let f: Vec<f64> = bytemuck::pod_collect_to_vec(data);
        return bytemuck::cast_slice(&f.iter().map(|&x| x as f32).collect::<Vec<f32>>()).to_vec();
    }
    data.to_vec()
}

/// The key an array is sent under: of its kind and content (equal bytes of two kinds differ).
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
pub(crate) fn key(kind: Kind, data: &[u8]) -> u64 {
    crate::digest([&[kind as u8][..], data])
}

/// An element as the unsigned integer the coding differences.
trait Lane: Pod {
    fn ordered(self, float: bool) -> Self;
    #[cfg_attr(not(any(feature = "player", test)), allow(dead_code))]
    fn unordered(self, float: bool) -> Self;
    #[cfg_attr(not(any(feature = "python", all(test, not(target_arch = "wasm32")))), allow(dead_code))]
    fn sub(self, other: Self) -> Self;
    #[cfg_attr(not(any(feature = "player", test)), allow(dead_code))]
    fn add(self, other: Self) -> Self;
    /// `2 b − o`, as floats (None: not finite).
    fn predict(b: Self, o: Self) -> Option<Self>;
}

macro_rules! lane {
    ($u:ty, $f:ty) => {
        impl Lane for $u {
            fn ordered(self, float: bool) -> Self {
                // floats as integers that order as they do: sign-magnitude to offset
                const TOP: $u = 1 << (<$u>::BITS - 1);
                if !float { self } else if self & TOP != 0 { !self } else { self | TOP }
            }
            fn unordered(self, float: bool) -> Self {
                const TOP: $u = 1 << (<$u>::BITS - 1);
                if !float { self } else if self & TOP != 0 { self ^ TOP } else { !self }
            }
            fn sub(self, other: Self) -> Self {
                self.wrapping_sub(other)
            }
            fn add(self, other: Self) -> Self {
                self.wrapping_add(other)
            }
            fn predict(b: Self, o: Self) -> Option<Self> {
                let p = (2.0 * <$f>::from_bits(b) as f64 - <$f>::from_bits(o) as f64) as $f;
                p.is_finite().then(|| p.to_bits())
            }
        }
    };
}
lane!(u32, f32);
lane!(u64, f64);

impl Lane for u8 {
    fn ordered(self, _: bool) -> Self {
        self
    }
    fn unordered(self, _: bool) -> Self {
        self
    }
    fn sub(self, other: Self) -> Self {
        self.wrapping_sub(other)
    }
    fn add(self, other: Self) -> Self {
        self.wrapping_add(other)
    }
    fn predict(_: Self, _: Self) -> Option<Self> {
        None
    }
}

/// Elements lane by lane (all x's, then all y's, …), then byte by byte: what zstd compresses.
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
fn planes<T: Pod>(values: &[T], lanes: usize) -> Vec<u8> {
    let lanes = if lanes > 1 && values.len().is_multiple_of(lanes) { lanes } else { 1 };
    let (n, w) = (values.len(), size_of::<T>());
    let per = n / lanes.max(1);
    let bytes: &[u8] = bytemuck::cast_slice(values);
    let mut out = vec![0u8; bytes.len()];
    for i in 0..n {
        // element i is lane i % lanes of item i / lanes: its place lane-major
        let at = (i % lanes) * per + i / lanes;
        for b in 0..w {
            out[b * n + at] = bytes[i * w + b];
        }
    }
    out
}

#[cfg(any(feature = "player", test))]
fn unplanes<T: Pod>(bytes: &[u8], lanes: usize) -> Vec<T> {
    let w = size_of::<T>();
    let n = bytes.len() / w;
    let lanes = if lanes > 1 && n.is_multiple_of(lanes) { lanes } else { 1 };
    let per = n / lanes.max(1);
    let mut out = vec![0u8; bytes.len()];
    for i in 0..n {
        let at = (i % lanes) * per + i / lanes;
        for b in 0..w {
            out[i * w + b] = bytes[b * n + at];
        }
    }
    bytemuck::pod_collect_to_vec(&out)
}

/// Code `data` (canonical bytes) against its base (and the base's base), if any: the smallest of
/// the codings that apply. Returns (mode, compressed payload).
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
pub(crate) fn encode(kind: Kind, data: &[u8], base: Option<&[u8]>, older: Option<&[u8]>) -> (u8, Vec<u8>) {
    match kind.width() {
        8 => encode_lanes::<u64>(kind, data, base, older),
        1 => encode_lanes::<u8>(kind, data, base, older),
        _ => encode_lanes::<u32>(kind, data, base, older),
    }
}

#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
fn encode_lanes<T: Lane>(kind: Kind, data: &[u8], base: Option<&[u8]>, older: Option<&[u8]>) -> (u8, Vec<u8>) {
    let (float, lanes) = (kind.float(), kind.lanes());
    let a: Vec<T> = bytemuck::pod_collect_to_vec(data);
    let ord = |v: &[T]| v.iter().map(|&x| x.ordered(float)).collect::<Vec<T>>();
    let mut choices: Vec<(u8, Vec<T>)> = vec![(ALONE, ord(&a))];
    if let Some(base) = base {
        let b: Vec<T> = bytemuck::pod_collect_to_vec(base);
        if b.len() == a.len() {
            let (oa, ob) = (ord(&a), ord(&b));
            choices.push((FIRST, oa.iter().zip(&ob).map(|(&x, &y)| x.sub(y)).collect()));
            if let Some(older) = older.filter(|o| float && o.len() == base.len()) {
                let o: Vec<T> = bytemuck::pod_collect_to_vec(older);
                let predicted: Option<Vec<T>> = b.iter().zip(&o).map(|(&b, &o)| T::predict(b, o)).collect();
                if let Some(p) = predicted {
                    choices.push((SECOND, oa.iter().zip(ord(&p)).map(|(&x, y)| x.sub(y)).collect()));
                }
            }
        } else if b.len() < a.len() && base == &data[..base.len()] {
            choices.push((TAIL, ord(&a[b.len()..])));
        }
    }
    choices
        .into_iter()
        .map(|(mode, values)| (mode, zstd::bulk::compress(&planes(&values, lanes), 3).expect("zstd compresses")))
        .min_by_key(|(_, blob)| blob.len())
        .expect("a coding")
}

/// The canonical bytes of an array coded as `mode` against its base (and the base's base).
#[cfg(any(feature = "player", test))]
pub(crate) fn decode(kind: Kind, mode: u8, blob: &[u8], base: Option<&[u8]>, older: Option<&[u8]>) -> Result<Vec<u8>, String> {
    use std::io::Read;
    let mut bytes = Vec::new();
    ruzstd::decoding::StreamingDecoder::new(blob).map_err(|e| e.to_string())?.read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    match kind.width() {
        8 => decode_lanes::<u64>(kind, mode, &bytes, base, older),
        1 => decode_lanes::<u8>(kind, mode, &bytes, base, older),
        _ => decode_lanes::<u32>(kind, mode, &bytes, base, older),
    }
}

#[cfg(any(feature = "player", test))]
fn decode_lanes<T: Lane>(kind: Kind, mode: u8, bytes: &[u8], base: Option<&[u8]>, older: Option<&[u8]>) -> Result<Vec<u8>, String> {
    let (float, lanes) = (kind.float(), kind.lanes());
    if !bytes.len().is_multiple_of(size_of::<T>()) { return Err("an array ends inside an element".into()); }
    let values: Vec<T> = unplanes(bytes, lanes);
    let base = || -> Result<Vec<T>, String> { crate::read(base.ok_or("an array's base is missing")?, "array base") };
    let ord = |v: &[T]| v.iter().map(|&x| x.ordered(float)).collect::<Vec<T>>();
    let out: Vec<T> = match mode {
        ALONE => values.iter().map(|&x| x.unordered(float)).collect(),
        FIRST => {
            let b = base()?;
            if b.len() != values.len() { return Err("an array's difference and base have different lengths".into()); }
            ord(&b).iter().zip(&values).map(|(&y, &r)| y.add(r).unordered(float)).collect()
        }
        SECOND => {
            let (b, o): (Vec<T>, Vec<T>) = (base()?, crate::read(older.ok_or("an array's second base is missing")?, "array second base")?);
            if b.len() != o.len() || b.len() != values.len() { return Err("an array's prediction and difference have different lengths".into()); }
            let p: Vec<T> = b.iter().zip(&o).map(|(&b, &o)| T::predict(b, o)).collect::<Option<_>>().ok_or("a prediction is not finite")?;
            ord(&p).iter().zip(&values).map(|(&y, &r)| y.add(r).unordered(float)).collect()
        }
        TAIL => {
            let mut b = base()?;
            b.extend(values.iter().map(|&x| x.unordered(float)));
            b
        }
        m => return Err(format!("unknown array coding {m}")),
    };
    Ok(bytemuck::cast_slice(&out).to_vec())
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;

    fn floats(n: usize, t: f32) -> Vec<u8> {
        let v: Vec<f32> = (0..n).map(|i| (i as f32 * 0.37 + t).sin() * 3.0 + t * 0.01).collect();
        bytemuck::cast_slice(&v).to_vec()
    }

    /// Every coding decodes to the array it coded, exactly; and a slowly changing array codes
    /// much smaller against its base than alone.
    #[test]
    fn codings_round_trip() {
        let (older, base, now) = (floats(3000, 0.0), floats(3000, 0.01), floats(3000, 0.02));
        let (mode, blob) = encode(Kind::MeshPoints, &now, Some(&base), Some(&older));
        assert!(mode == FIRST || mode == SECOND);
        assert_eq!(decode(Kind::MeshPoints, mode, &blob, Some(&base), Some(&older)).unwrap(), now);
        let (alone, alone_blob) = encode(Kind::MeshPoints, &now, None, None);
        assert_eq!(alone, ALONE);
        assert!(blob.len() * 2 < alone_blob.len(), "{} against {}", blob.len(), alone_blob.len());
        assert_eq!(decode(Kind::MeshPoints, ALONE, &alone_blob, None, None).unwrap(), now);
        // a longer array whose start is its base: the tail
        let grown: Vec<u8> = [&base[..], &floats(300, 5.0)[..]].concat();
        let (mode, blob) = encode(Kind::PathSubpaths, &grown, Some(&base), None);
        assert_eq!(mode, TAIL);
        assert_eq!(decode(Kind::PathSubpaths, mode, &blob, Some(&base), None).unwrap(), grown);
        // float64 control points, integers, bytes: each its own width
        let f64s: Vec<u8> = bytemuck::cast_slice(&(0..999).map(|i| i as f64 * 1.5 - 7.0).collect::<Vec<f64>>()).to_vec();
        for (kind, data) in [(Kind::PathPoints, f64s), (Kind::Texture, (0..4096).map(|i| (i * 7 % 256) as u8).collect()), (Kind::Records, vec![9u8; crate::take::RECORD * 5])] {
            let (mode, blob) = encode(kind, &data, None, None);
            assert_eq!(decode(kind, mode, &blob, None, None).unwrap(), data, "{kind:?}");
        }
    }

    #[test]
    fn floats_round_to_the_gpus_precision() {
        let f64s: Vec<u8> = bytemuck::cast_slice(&[0.1f64, -2.5, 1e-9]).to_vec();
        let c = canonical(Kind::MeshPoints, &f64s);
        assert_eq!(bytemuck::cast_slice::<u8, f32>(&c), &[0.1f32, -2.5, 1e-9]);
        assert_ne!(key(Kind::MeshPoints, &[]), key(Kind::MeshTriangles, &[]));
    }
}

#[cfg(test)]
mod decoder_contract {
    use super::*;

    #[cfg_attr(target_arch = "wasm32", wasm_bindgen_test::wasm_bindgen_test)]
    #[cfg_attr(not(target_arch = "wasm32"), test)]
    fn malformed_arrays_are_not_padded_or_truncated() {
        let base = [0u8; 8];
        assert!(decode_lanes::<u32>(Kind::Points, ALONE, &[0; 3], None, None).is_err());
        assert!(decode_lanes::<u64>(Kind::PathPoints, ALONE, &[0; 7], None, None).is_err());
        assert!(decode_lanes::<u32>(Kind::Points, FIRST, &[], Some(&base), None).is_err());
        assert!(decode_lanes::<u32>(Kind::Points, FIRST, &base, Some(&base[..3]), None).is_err());
        assert!(decode_lanes::<u32>(Kind::Points, SECOND, &base, Some(&base), Some(&base[..4])).is_err());
        assert!(decode_lanes::<u32>(Kind::Points, SECOND, &base[..4], Some(&base), Some(&base)).is_err());
        assert_eq!(decode_lanes::<u32>(Kind::Points, FIRST, &base, Some(&base), None).unwrap(), base);
        assert_eq!(decode_lanes::<u32>(Kind::Points, SECOND, &base, Some(&base), Some(&base)).unwrap(), base);
    }
}
