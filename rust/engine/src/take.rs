//! A take: a scene's run as the engine's calls — shapes, brushes and images uploaded under their
//! keys, then frames (a view and its records, shown for some frames) — written as one stream of
//! messages. Python records it wherever it runs (natively or in Pyodide: `Recorder`); a projector
//! reads it back and draws any of its frames on demand (`web`).
//!
//! A message is its length (u32), its op (u8), then its fields, little-endian; a byte string is
//! its length (u32), then its bytes. A take begins with START: its format version (u32), width
//! and height (u32 each), and frame rate (f64). It ends with END (whether its
//! scene failed: a take cut short has none); NOTE carries the director's notes (JSON: the plays,
//! the sections, the captions) to whoever shows the take, and SOUND the film's sound, an audio
//! file its player plays beside the frames.
//!
//! ENVIRONMENT carries an environment's picture (the light around a 3D view: `environment`), sent
//! when it is added, before any frame that shows it.
//!
//! What an upload holds goes as ARRAY messages (see `pack`): each array under its own key, sent
//! once, coded against the array it replaces. The upload itself names its arrays by key, and a
//! FRAME names its records array. An array's base is the array of the same role in the upload
//! the same record slot drew the frame before: the writer learns what replaces what from the
//! frames' records, so a film changing a little from frame to frame is sent as its changes.

#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
use std::collections::HashMap;
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
use std::sync::Arc;

#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
use crate::pack::{self, Kind};

/// The wire contract, including the layouts of views, records, uploads and coded arrays.
/// Bump when a writer's output can no longer be read with the same meaning by an older reader.
pub(crate) const VERSION: u32 = 1;
// Opcode 0 was the unversioned START. A different opcode makes old readers reject this one.
pub(crate) const START: u8 = 14;
pub(crate) const PATH: u8 = 1;
pub(crate) const POINTS: u8 = 2;
pub(crate) const MESH: u8 = 3;
pub(crate) const ROWS: u8 = 4;
pub(crate) const TEXTURE: u8 = 5;
pub(crate) const GROW: u8 = 6;
pub(crate) const FRAME: u8 = 8;
pub(crate) const NOTE: u8 = 9;
pub(crate) const SOUND: u8 = 10;
pub(crate) const ARRAY: u8 = 11;
pub(crate) const END: u8 = 12;
pub(crate) const ENVIRONMENT: u8 = 13;

/// The keys a record draws: shapes, brushes (fill and stroke, of both paints), texture.
pub(crate) const KEYS: usize = 7;
pub(crate) const RECORD: usize = 336; // (`render::Record`'s size: checked where it is defined)

/// The keys of each record in `records`.
pub(crate) fn slots(records: &[u8]) -> impl Iterator<Item = [u64; KEYS]> + '_ {
    records.chunks_exact(RECORD).map(|r| std::array::from_fn(|k| u64::from_le_bytes(r[8 * k..8 * k + 8].try_into().unwrap())))
}

/// An upload the writer holds until a frame shows it (so it knows what it replaces).
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
struct Upload {
    op: u8,
    key: u64,
    head: Vec<u8>, // its fields other than its arrays
    arrays: Vec<(Kind, Vec<u8>)>,
    waited: bool, // a frame has passed without showing it
}

/// Writes a take's messages into a buffer, taken out as it fills (`drain`).
#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
#[derive(Default)]
pub(crate) struct Writer {
    buffer: Vec<u8>,
    sent: HashMap<u64, u8>,          // every array sent: its depth in its chain
    arrays: HashMap<u64, Arc<[u8]>>, // arrays that may be bases: those the last frames drew
    parents: HashMap<u64, u64>,      // their bases
    uploads: HashMap<u64, (u8, Vec<u64>)>, // an upload's op and arrays (uploads the last frames drew)
    pending: Vec<Upload>,
    slots: Vec<[u64; KEYS]>,  // the last frame's records' keys (the frame's, then its cameras')
    records: HashMap<u64, u64>, // a view's last records array (0: the frame's; else a camera's)
}

#[cfg(any(feature = "python", all(test, not(target_arch = "wasm32"))))]
impl Writer {
    fn begin(&mut self, op: u8) -> usize {
        let at = self.buffer.len();
        self.buffer.extend_from_slice(&[0; 4]);
        self.buffer.push(op);
        at
    }
    fn end(&mut self, at: usize) {
        let n = (self.buffer.len() - at - 4) as u32;
        self.buffer[at..at + 4].copy_from_slice(&n.to_le_bytes());
    }
    fn put(&mut self, bytes: &[u8]) {
        self.buffer.extend_from_slice(bytes);
    }
    fn string(&mut self, bytes: &[u8]) {
        self.put(&(bytes.len() as u32).to_le_bytes());
        self.put(bytes);
    }
    fn hold(&mut self, op: u8, key: u64, head: &[u8], arrays: Vec<(Kind, &[u8])>) {
        let arrays = arrays.into_iter().map(|(kind, data)| (kind, pack::canonical(kind, data))).collect();
        self.pending.push(Upload { op, key, head: head.to_vec(), arrays, waited: false });
    }

    pub(crate) fn start(&mut self, width: u32, height: u32, fps: f64) {
        let at = self.begin(START);
        self.put(&VERSION.to_le_bytes());
        self.put(&width.to_le_bytes());
        self.put(&height.to_le_bytes());
        self.put(&fps.to_le_bytes());
        self.end(at);
    }
    pub(crate) fn path(&mut self, key: u64, points: &[u8], subpaths: &[u8], centroid_area: [f32; 6]) {
        self.hold(PATH, key, bytemuck::cast_slice(&centroid_area), vec![(Kind::PathPoints, points), (Kind::PathSubpaths, subpaths)]);
    }
    pub(crate) fn points(&mut self, key: u64, vertices: &[u8]) {
        self.hold(POINTS, key, &[], vec![(Kind::Points, vertices)]);
    }
    pub(crate) fn mesh(&mut self, key: u64, mesh: &crate::mesh::Mesh<'_>) {
        let head: Vec<u8> = [mesh.outline.to_le_bytes(), mesh.block.to_le_bytes()].concat();
        self.hold(MESH, key, &head, vec![
            (Kind::MeshPoints, bytemuck::cast_slice(&mesh.points)),
            (Kind::MeshUvs, bytemuck::cast_slice(&mesh.uvs)),
            (Kind::MeshNormals, bytemuck::cast_slice(&mesh.normals)),
            (Kind::MeshTriangles, bytemuck::cast_slice(&mesh.triangles)),
        ]);
    }
    pub(crate) fn rows(&mut self, key: u64, rows: &[u8]) {
        self.hold(ROWS, key, &[], vec![(Kind::Rows, rows)]);
    }
    pub(crate) fn texture(&mut self, key: u64, width: u32, height: u32, rgba: &[u8]) {
        let head: Vec<u8> = [width.to_le_bytes(), height.to_le_bytes()].concat();
        self.hold(TEXTURE, key, &head, vec![(Kind::Texture, rgba)]);
    }
    /// An environment, written at once (frames show it by its id, in their views: none waits to show it).
    pub(crate) fn environment(&mut self, id: u32, width: u32, height: u32, rgbe: &[u8]) {
        let key = self.array(Kind::Texture, rgbe.to_vec(), None);
        let at = self.begin(ENVIRONMENT);
        self.put(&id.to_le_bytes());
        self.put(&width.to_le_bytes());
        self.put(&height.to_le_bytes());
        self.put(&key.to_le_bytes());
        self.end(at);
    }
    pub(crate) fn grow(&mut self, key: u64, points: &[u8], closed: bool) {
        self.hold(GROW, key, &[closed as u8], vec![(Kind::PathPoints, points)]);
    }

    /// Send an array (or, sent before, nothing): its key. Coded against `base`, if that is at
    /// hand and its chain is short enough.
    fn array(&mut self, kind: Kind, data: Vec<u8>, base: Option<u64>) -> u64 {
        let key = pack::key(kind, &data);
        if self.sent.contains_key(&key) {
            self.arrays.entry(key).or_insert_with(|| data.into());
            return key;
        }
        let base = base.filter(|b| self.sent.get(b).is_some_and(|&d| d < pack::DEPTH) && self.arrays.contains_key(b));
        let older = base.and_then(|b| self.parents.get(&b)).and_then(|o| self.arrays.get(o)).cloned();
        let (mode, blob) = pack::encode(kind, &data, base.map(|b| &self.arrays[&b][..]), older.as_deref());
        let base = base.filter(|_| mode != pack::ALONE);
        let at = self.begin(ARRAY);
        self.put(&key.to_le_bytes());
        self.put(&base.unwrap_or(0).to_le_bytes());
        self.put(&[kind as u8, mode]);
        self.string(&blob);
        self.end(at);
        self.sent.insert(key, base.map_or(0, |b| self.sent[&b] + 1));
        if let Some(b) = base {
            self.parents.insert(key, b);
        }
        self.arrays.insert(key, data.into());
        key
    }

    fn upload(&mut self, u: Upload, replaces: Option<u64>) {
        // an upload of another kind has other arrays: no bases
        let bases = replaces.and_then(|r| self.uploads.get(&r)).filter(|(op, _)| *op == u.op).map(|(_, keys)| keys.clone()).unwrap_or_default();
        let keys: Vec<u64> = u.arrays.into_iter().enumerate().map(|(i, (kind, data))| self.array(kind, data, bases.get(i).copied())).collect();
        let at = self.begin(u.op);
        self.put(&u.key.to_le_bytes());
        self.put(&u.head);
        for k in &keys {
            self.put(&k.to_le_bytes());
        }
        self.end(at);
        if u.op != GROW {
            self.uploads.insert(u.key, (u.op, keys));
        }
    }

    pub(crate) fn frame(&mut self, view: &[u8], records: &[u8], repeat: u32, cameras: &[crate::CameraView]) {
        // the views' records, and the keys each draws
        let views: Vec<(u64, &[u8])> = std::iter::once((0, records)).chain(cameras.iter().map(|c| (c.0, &c.4[..]))).collect();
        let slots: Vec<[u64; KEYS]> = views.iter().flat_map(|(_, r)| slots(r)).collect();
        // the uploads it shows first: each replaces what its slot drew the frame before
        let mut replaces: HashMap<u64, Option<u64>> = HashMap::new();
        for (i, keys) in slots.iter().enumerate() {
            for (role, &key) in keys.iter().enumerate() {
                if key != 0 && !replaces.contains_key(&key) && self.pending.iter().any(|u| u.key == key) {
                    replaces.insert(key, self.slots.get(i).map(|was| was[role]).filter(|&was| was != 0 && was != key));
                }
            }
        }
        // in the order they came (a path before its growth); one no frame shows goes after a frame
        for mut u in std::mem::take(&mut self.pending) {
            match replaces.get(&u.key) {
                Some(&was) => self.upload(u, was),
                None if u.waited => self.upload(u, None),
                None => {
                    u.waited = true;
                    self.pending.push(u);
                }
            }
        }
        let mut last = HashMap::new();
        let record_keys: Vec<u64> = views
            .iter()
            .map(|&(view, records)| {
                let key = self.array(Kind::Records, records.to_vec(), self.records.get(&view).copied());
                last.insert(view, key);
                key
            })
            .collect();
        let at = self.begin(FRAME);
        self.put(&repeat.to_le_bytes());
        self.string(view);
        self.put(&record_keys[0].to_le_bytes());
        self.put(&(cameras.len() as u32).to_le_bytes());
        for ((key, width, height, v, _), records) in cameras.iter().zip(&record_keys[1..]) {
            self.put(&key.to_le_bytes());
            self.put(&width.to_le_bytes());
            self.put(&height.to_le_bytes());
            self.string(v);
            self.put(&records.to_le_bytes());
        }
        self.end(at);
        // keep what this frame drew (the bases of the next), and the bases of those
        self.uploads.retain(|k, _| slots.iter().any(|s| s.contains(k)));
        let mut keep: std::collections::HashSet<u64> = self.uploads.values().flat_map(|(_, keys)| keys).copied().chain(last.values().copied()).collect();
        keep.extend(keep.iter().filter_map(|k| self.parents.get(k)).copied().collect::<Vec<_>>());
        self.arrays.retain(|k, _| keep.contains(k));
        self.parents.retain(|k, _| keep.contains(k));
        (self.slots, self.records) = (slots, last);
    }
    pub(crate) fn note(&mut self, json: &str) {
        let at = self.begin(NOTE);
        self.string(json.as_bytes());
        self.end(at);
    }
    pub(crate) fn sound(&mut self, file: &[u8]) {
        let at = self.begin(SOUND);
        self.string(file);
        self.end(at);
    }
    /// The take's end: its film ended, or its scene `failed`.
    pub(crate) fn close(&mut self, failed: bool) {
        let at = self.begin(END);
        self.put(&[failed as u8]);
        self.end(at);
    }

    /// The messages written since the last drain.
    pub(crate) fn drain(&mut self) -> Vec<u8> {
        std::mem::take(&mut self.buffer)
    }
}

/// Reads a message's fields in order.
#[cfg(any(feature = "player", test))]
pub(crate) struct Fields<'a>(pub(crate) &'a [u8]);

#[cfg(any(feature = "player", test))]
impl<'a> Fields<'a> {
    pub(crate) fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
        if self.0.len() < n {
            return Err("a message of the take ends early".into());
        }
        let (head, rest) = self.0.split_at(n);
        self.0 = rest;
        Ok(head)
    }
    pub(crate) fn u8(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }
    pub(crate) fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    pub(crate) fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }
    pub(crate) fn f64(&mut self) -> Result<f64, String> {
        Ok(f64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }
    pub(crate) fn f32s<const N: usize>(&mut self) -> Result<[f32; N], String> {
        Ok(bytemuck::pod_read_unaligned(self.take(4 * N)?))
    }
    pub(crate) fn string(&mut self) -> Result<&'a [u8], String> {
        let n = self.u32()? as usize;
        self.take(n)
    }
}

/// The whole messages at the start of `stream`, and how many bytes they take (the rest is a
/// message still arriving).
#[cfg(any(feature = "player", test))]
pub(crate) fn messages(stream: &[u8]) -> (Vec<&[u8]>, usize) {
    let (mut out, mut at) = (Vec::new(), 0);
    while let Some(n) = stream.get(at..at + 4).map(|b| u32::from_le_bytes(b.try_into().unwrap()) as usize) {
        let Some(message) = stream.get(at + 4..at + 4 + n) else { break };
        out.push(message);
        at += 4 + n;
    }
    (out, at)
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;

    fn record(shape: u64) -> Vec<u8> {
        let mut r = vec![0u8; RECORD];
        r[..8].copy_from_slice(&shape.to_le_bytes());
        r
    }

    /// What a writer writes, a reader reads back: every message whole, in order, however the
    /// stream is cut into chunks; an upload waits for the frame that shows it, and replaces what
    /// its slot drew before: its arrays are coded against those, decode to them exactly, and an
    /// array sent before is not sent again.
    #[test]
    fn round_trip() {
        let mut w = Writer::default();
        w.start(960, 540, 30.0);
        let points = |t: f64| -> Vec<u8> { bytemuck::cast_slice(&(0..900).map(|i| ((i as f64) * 0.1 + t).sin()).collect::<Vec<f64>>()).to_vec() };
        let triangles: Vec<u8> = bytemuck::cast_slice(&(0..300u32).collect::<Vec<u32>>()).to_vec();
        let uvs = [[0.0f64; 2]; 300];
        let normals = [[0.0f64, 0.0, 1.0]; 300];
        let before = points(0.0);
        let after = points(0.01);
        w.mesh(7, &crate::mesh::Mesh::new(&before, bytemuck::cast_slice(&uvs), bytemuck::cast_slice(&normals), &triangles, 0, 0).unwrap());
        let mut seen_by_camera = record(7);
        seen_by_camera[56] = 1; // other flags: other records
        w.frame(&[3; 192], &record(7), 1, &[(9, 64, 32, vec![5; 192], seen_by_camera)]);
        w.mesh(8, &crate::mesh::Mesh::new(&after, bytemuck::cast_slice(&uvs), bytemuck::cast_slice(&normals), &triangles, 0, 0).unwrap()); // the next frame's: replaces 7
        w.frame(&[3; 192], &record(7), 2, &[]);
        w.frame(&[3; 192], &record(8), 1, &[]);
        w.sound(&[8; 44]);
        w.note("{\"captions\": []}");
        w.close(false);
        let stream = w.drain();
        for cut in [1, 5, 100, stream.len()] {
            let (mut seen, mut pending) = (Vec::new(), Vec::new());
            for chunk in stream.chunks(cut) {
                pending.extend_from_slice(chunk);
                let (messages, used) = messages(&pending);
                seen.extend(messages.iter().map(|m| m[0]));
                pending.drain(..used);
            }
            let (a, m, f) = (ARRAY, MESH, FRAME);
            // mesh 7: its 4 arrays; the frame's records and its camera's; frame; frame 2 (its
            // records as before); mesh 8 (its points only, then 3 known arrays), records, frame 3
            assert_eq!(seen, [START, a, a, a, a, m, a, a, f, f, a, m, a, f, SOUND, NOTE, END]);
            assert!(pending.is_empty());
        }
        let (messages, _) = messages(&stream);
        // decode every array, as a projector would (each in order, its base before it)
        let mut decoded: HashMap<u64, Vec<u8>> = HashMap::new();
        let mut bases: HashMap<u64, u64> = HashMap::new();
        for m in &messages {
            let mut f = Fields(m);
            if f.u8().unwrap() != ARRAY {
                continue;
            }
            let (key, base, kind, mode, blob) = (f.u64().unwrap(), f.u64().unwrap(), f.u8().unwrap(), f.u8().unwrap(), f.string().unwrap());
            let kind = Kind::from_u8(kind).unwrap();
            let older = bases.get(&base).and_then(|o| decoded.get(o)).map(|v| &v[..]);
            let data = pack::decode(kind, mode, blob, decoded.get(&base).map(|v| &v[..]), older).unwrap();
            assert_eq!(pack::key(kind, &data), key);
            if base != 0 {
                assert_eq!(mode, pack::FIRST, "mesh 8's points are coded against mesh 7's");
                bases.insert(key, base);
            }
            decoded.insert(key, data);
        }
        assert!(decoded.values().any(|d| d[..] == pack::canonical(Kind::MeshPoints, &points(0.01))[..]));
        let mut s = Fields(messages[0]);
        assert_eq!((s.u8().unwrap(), s.u32().unwrap(), s.u32().unwrap(), s.u32().unwrap(), s.f64().unwrap()), (START, VERSION, 960, 540, 30.0));
    }

    #[test]
    fn a_recorded_mesh_keeps_normals_derived_before_positions_are_rounded() {
        let points = [[-0.6f64, -0.6, 1e8], [0.6, -0.6, 1e8 + 1.0], [0.0, 0.6, 1e8]];
        let uvs = [[0.25f64, 0.5], [0.5, 0.75], [0.75, 1.0]];
        let mesh = crate::mesh::Mesh::new(bytemuck::cast_slice(&points), bytemuck::cast_slice(&uvs), &[], bytemuck::cast_slice(&[0u32, 1, 2]), 0, 0).unwrap();
        // The GPU positions have lost their small z difference. Deriving normals from those
        // positions would turn this tilted face into a flat one and change its lighting.
        assert!(mesh.points.iter().all(|v| v[2] as f32 == 1e8));
        assert_eq!(mesh.normals[0], [-1.2, 0.6, 1.44]);
        let mut writer = Writer::default();
        writer.start(320, 240, 10.0);
        writer.mesh(1, &mesh);
        writer.frame(&[0; 192], &record(1), 1, &[]);
        writer.close(false);
        let stream = writer.drain();
        let mut arrays = HashMap::new();
        for message in messages(&stream).0 {
            let mut fields = Fields(message);
            if fields.u8().unwrap() != ARRAY { continue; }
            let (_key, base, kind, mode, data) = (fields.u64().unwrap(), fields.u64().unwrap(), fields.u8().unwrap(), fields.u8().unwrap(), fields.string().unwrap());
            assert_eq!(base, 0);
            arrays.insert(kind, pack::decode(Kind::from_u8(kind).unwrap(), mode, data, None, None).unwrap());
        }
        let wide = |kind: Kind| {
            let f: Vec<f32> = bytemuck::pod_collect_to_vec(&arrays[&(kind as u8)]);
            bytemuck::cast_slice(&f.into_iter().map(f64::from).collect::<Vec<_>>()).to_vec()
        };
        let (points, uvs, normals) = (wide(Kind::MeshPoints), wide(Kind::MeshUvs), wide(Kind::MeshNormals));
        let replay = crate::mesh::Mesh::new(&points, &uvs, &normals, &arrays[&(Kind::MeshTriangles as u8)], 0, 0).unwrap();
        for (before, after) in mesh.points.iter().zip(&*replay.points) {
            assert_eq!(before.map(|v| v as f32), after.map(|v| v as f32));
        }
        for (before, after) in mesh.normals.iter().zip(&*replay.normals) {
            assert_eq!(before.map(|v| v as f32), after.map(|v| v as f32));
        }
        assert_eq!(replay.uvs, mesh.uvs);
        assert_eq!(replay.triangles, mesh.triangles);
    }
}
