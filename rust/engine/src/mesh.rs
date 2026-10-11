//! A mesh prepared for drawing or recording. Geometry is evaluated in its input precision;
//! each sink rounds the finished vertices and normals to the GPU's precision.

use std::borrow::Cow;

pub(crate) struct Mesh<'a> {
    pub(crate) points: Cow<'a, [[f64; 3]]>,
    pub(crate) uvs: Cow<'a, [[f64; 2]]>,
    pub(crate) normals: Cow<'a, [[f64; 3]]>,
    pub(crate) triangles: Cow<'a, [u32]>,
    pub(crate) outline: u32,
    pub(crate) block: u32,
}

impl<'a> Mesh<'a> {
    pub(crate) fn new(points: &'a [u8], uvs: &'a [u8], normals: &'a [u8], triangles: &'a [u8], outline: u32, block: u32) -> Result<Self, String> {
        let p = read::<[f64; 3]>(points, "points")?;
        let uv = read::<[f64; 2]>(uvs, "uvs")?;
        let t = read::<u32>(triangles, "triangles")?;
        if uv.len() != p.len() || !t.len().is_multiple_of(3) || t.iter().any(|&i| i as usize >= p.len()) {
            return Err("a mesh needs a (u, v) per point, and whole triangles of its points".into());
        }
        let n = if normals.is_empty() { smooth_normals(&p, &t).into() } else { read::<[f64; 3]>(normals, "normals")? };
        if n.len() != p.len() {
            return Err("a mesh needs a normal per point".into());
        }
        let block = if block == 0 { outline } else { block };
        if outline > 2 && (block < outline || !p.len().is_multiple_of(block as usize)) {
            return Err("an outlined mesh is whole faces of vertices, each beginning with its loop".into());
        }
        // A reveal shows a surface face by face: each face's triangles are its own.
        let faces = (p.len() / block.max(1) as usize).max(1);
        let own = |(k, face): (usize, &[u32])| face.iter().all(|&i| i as usize / block as usize == k);
        if outline > 2 && (!t.len().is_multiple_of(3 * faces) || (!t.is_empty() && !t.chunks(t.len() / faces).enumerate().all(own))) {
            return Err("an outlined mesh's triangles are its faces' own, face after face, as many each".into());
        }
        Ok(Self {
            points: p,
            uvs: uv,
            normals: n,
            triangles: t,
            outline,
            block,
        })
    }
}

/// Borrow aligned input; a byte buffer with another alignment is read into aligned storage.
fn read<'a, T: bytemuck::Pod>(bytes: &'a [u8], what: &str) -> Result<Cow<'a, [T]>, String> {
    match bytemuck::try_cast_slice(bytes) {
        Ok(values) => Ok(Cow::Borrowed(values)),
        Err(_) => crate::read(bytes, what).map(Cow::Owned),
    }
}

/// Area-weighted vertex normals: each corner receives its faces in one fixed order.
fn smooth_normals(p: &[[f64; 3]], triangles: &[u32]) -> Vec<[f64; 3]> {
    let faces: Vec<[f64; 3]> = triangles
        .chunks_exact(3)
        .map(|t| {
            let (a, b, c) = (p[t[0] as usize], p[t[1] as usize], p[t[2] as usize]);
            let (u, w) = ([b[0] - a[0], b[1] - a[1], b[2] - a[2]], [c[0] - a[0], c[1] - a[1], c[2] - a[2]]);
            [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        })
        .collect();
    let mut out = vec![[0.0f64; 3]; p.len()];
    for k in 0..3 {
        for (t, f) in triangles.chunks_exact(3).zip(&faces) {
            let o = &mut out[t[k] as usize];
            o[0] += f[0];
            o[1] += f[1];
            o[2] += f[2];
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_unaligned_byte_buffer_prepares_the_same_mesh() {
        let points = [[1.0f64, 2.0, 3.0], [4.0, 5.0, 6.0], [2.0, 2.0, 0.0]];
        let uvs = [[0.0f64; 2]; 3];
        let triangles = [0u32, 1, 2];
        let aligned = Mesh::new(bytemuck::cast_slice(&points), bytemuck::cast_slice(&uvs), &[], bytemuck::cast_slice(&triangles), 0, 0).unwrap();
        let mut bytes = vec![0];
        bytes.extend_from_slice(bytemuck::cast_slice(&points));
        let end_points = bytes.len();
        bytes.extend_from_slice(bytemuck::cast_slice(&uvs));
        let end_uvs = bytes.len();
        bytes.extend_from_slice(bytemuck::cast_slice(&triangles));
        let shifted = Mesh::new(&bytes[1..end_points], &bytes[end_points..end_uvs], &[], &bytes[end_uvs..], 0, 0).unwrap();
        assert_eq!(shifted.points, aligned.points);
        assert_eq!(shifted.uvs, aligned.uvs);
        assert_eq!(shifted.normals, aligned.normals);
        assert_eq!(shifted.triangles, aligned.triangles);
    }
}
