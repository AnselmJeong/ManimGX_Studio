//! The projector: takes, as their director sends them (`feed`: arrays, uploads, frames, notes),
//! the frame at any moment of them drawn on demand (`show`, then `encode`). A take is kept whole,
//! as sent — its arrays coded (see `pack`): the film, small — while its player holds only what the
//! frames drawn lately draw: a frame's shapes are made from their arrays when it is drawn, and
//! those drawn longest ago go past a budget. So a film of any length is watched in any order in
//! bounded memory. A newer take (the scene run again) replaces the one shown once it reaches the
//! moment shown, or ends: an edit never blanks the picture, nor loses the place. A take whose
//! scene failed replaces it only if it got there.
//!
//! It is the player's (see `player`): in a window and on a page's canvas alike.

use std::collections::HashMap;
use std::sync::Arc;

use crate::pack::{self, Kind};
use crate::render::{Frame, Gpu, Player};
use crate::take::{self, Fields};

/// Bytes of shapes, brushes and textures a take's player holds: past it, what was drawn longest
/// ago goes, down to half (so the store packs what is left), made again from the take if drawn
/// again. A frame draws 1-20 MB (the example films).
const DRAWN: usize = 64 << 20;
/// Bytes of decoded arrays kept at hand: the bases the next versions are decoded against.
const DECODED: usize = 32 << 20;

/// A coded array as the projector keeps it: in the browser, in a buffer of the page's own,
/// outside the WebAssembly memory (so a take's length is bounded by the page's memory, not
/// WebAssembly's 4 GB); natively, in memory.
#[cfg(target_arch = "wasm32")]
type Blob = js_sys::Uint8Array;
#[cfg(not(target_arch = "wasm32"))]
type Blob = Box<[u8]>;

#[cfg(target_arch = "wasm32")]
fn blob(bytes: &[u8]) -> Blob {
    js_sys::Uint8Array::from(bytes)
}
#[cfg(not(target_arch = "wasm32"))]
fn blob(bytes: &[u8]) -> Blob {
    bytes.into()
}

#[cfg(target_arch = "wasm32")]
fn bytes(blob: &Blob) -> std::borrow::Cow<'_, [u8]> {
    blob.to_vec().into()
}
#[cfg(not(target_arch = "wasm32"))]
fn bytes(blob: &Blob) -> std::borrow::Cow<'_, [u8]> {
    (&blob[..]).into()
}

/// A distinct frame of a take: shown from frame `first` until the next one's; its view and
/// records array, and its cameras' (key, width, height, view, records array).
struct Shot {
    first: u32,
    view: Vec<u8>,
    records: u64,
    cameras: Vec<(u64, u32, u32, Vec<u8>, u64)>,
}

/// A take's arrays as sent: coded, all kept (they are the take), each decoded when a frame needs
/// it, its chain's bases first, the latest kept at hand.
#[derive(Default)]
struct Pack {
    arrays: HashMap<u64, Coded>,
    decoded: HashMap<u64, (Arc<Vec<u8>>, u64)>, // immutable bytes and when last used
    held: usize,
    clock: u64,
}

struct Coded {
    kind: Kind,
    mode: u8,
    base: u64,
    depth: u8,
    blob: Blob,
}

impl Pack {
    fn add(&mut self, f: &mut Fields) -> Result<(), String> {
        let (key, base, kind, mode, data) = (f.u64()?, f.u64()?, Kind::from_u8(f.u8()?)?, f.u8()?, f.string()?);
        crate::check_key(key)?;
        if self.arrays.contains_key(&key) { return Err("an array key is immutable within a take".into()); }
        // The writer sends every base first, once, and cuts each dependency chain at DEPTH.
        // Enforcing that DAG on receipt keeps lazy decoding bounded and rules out cycles.
        let depth = match mode {
            pack::ALONE if base == 0 => 0,
            pack::ALONE => return Err("an independent array cannot have a base".into()),
            pack::FIRST | pack::SECOND | pack::TAIL => {
                let parent = self.arrays.get(&base).ok_or("an array's base must precede it")?;
                if parent.kind != kind { return Err("an array and its base have different kinds".into()); }
                if mode == pack::SECOND && parent.base == 0 { return Err("an array's second base is missing".into()); }
                if parent.depth >= pack::DEPTH { return Err("an array's dependency chain is too deep".into()); }
                parent.depth + 1
            }
            _ => return Err(format!("unknown array coding {mode}")),
        };
        self.arrays.insert(key, Coded { kind, mode, base, depth, blob: blob(data) });
        Ok(())
    }

    /// An array's bytes (as the take carries it).
    fn get(&mut self, key: u64) -> Result<Arc<Vec<u8>>, String> {
        self.clock += 1;
        if let Some((data, used)) = self.decoded.get_mut(&key) {
            *used = self.clock;
            return Ok(data.clone());
        }
        let c = self.arrays.get(&key).ok_or("the take names an array it never sent")?;
        let (kind, mode, base_key, coded) = (c.kind, c.mode, c.base, bytes(&c.blob).into_owned());
        let base = if base_key != 0 { Some(self.get(base_key)?) } else { None };
        let older = match mode {
            pack::SECOND => Some(self.get(self.arrays.get(&base_key).map_or(0, |b| b.base))?),
            _ => None,
        };
        let data = Arc::new(pack::decode(kind, mode, &coded, base.as_deref().map(|b| &b[..]), older.as_deref().map(|o| &o[..]))?);
        self.held += data.len();
        self.decoded.insert(key, (data.clone(), self.clock));
        if self.held > DECODED {
            // the least recently used, down to half
            let mut by_use: Vec<(u64, u64)> = self.decoded.iter().map(|(&k, (_, used))| (*used, k)).collect();
            by_use.sort_unstable();
            for (_, k) in by_use {
                if self.held <= DECODED / 2 {
                    break;
                }
                if let Some((d, _)) = self.decoded.remove(&k) {
                    self.held -= d.len();
                }
            }
        }
        Ok(data)
    }
}

/// How an upload is made from its arrays.
enum Recipe {
    Path { centroid_area: [f32; 6], points: u64, subpaths: u64, grown: Vec<(u32, u64, bool)>, applied: usize },
    Points(u64),
    Mesh { outline: u32, block: u32, arrays: [u64; 4] },
    Rows(u64),
    Texture { width: u32, height: u32, rgba: u64 },
}

impl Recipe {
    /// Put the shape (brush, texture) `key` into the player.
    fn make(&mut self, key: u64, frame: u32, pack: &mut Pack, player: &mut Player) -> Result<(), String> {
        if !matches!(self, Recipe::Path { .. }) && player.has(key) {
            return Ok(());
        }
        match self {
            Recipe::Path { centroid_area, points, subpaths, grown, applied } => {
                // A shot sees only growth that had arrived when it was recorded. The
                // path's bounds, joints and closure belong to that version too: cropping
                // a fully grown path's curve window cannot recover its earlier picture.
                let wanted = grown.partition_point(|&(first, _, _)| first <= frame);
                if !player.has(key) || *applied > wanted {
                    player.evict(&[key]);
                    player.add_path(key, &pack.get(*points)?, &pack.get(*subpaths)?, *centroid_area)?;
                    *applied = 0;
                }
                for &(_, tail, closed) in &grown[*applied..wanted] {
                    player.grow_path(key, &pack.get(tail)?, closed)?;
                    *applied += 1;
                }
            }
            Recipe::Points(data) => player.add_points(key, &pack.get(*data)?)?,
            Recipe::Mesh { outline, block, arrays: [points, uvs, normals, triangles] } => {
                // the take's float32s, as the player takes them (which rounds them back: exactly)
                let mut wide = |key: u64| -> Result<Vec<u8>, String> {
                    let f: Vec<f32> = bytemuck::pod_collect_to_vec(&pack.get(key)?);
                    Ok(bytemuck::cast_slice(&f.iter().map(|&x| x as f64).collect::<Vec<f64>>()).to_vec())
                };
                let (p, uv, n) = (wide(*points)?, wide(*uvs)?, wide(*normals)?);
                player.add_mesh(key, &p, &uv, &n, &pack.get(*triangles)?, *outline, *block)?;
            }
            Recipe::Rows(data) => player.add_rows(key, &pack.get(*data)?)?,
            Recipe::Texture { width, height, rgba } => player.add_texture(key, *width, *height, &pack.get(*rgba)?)?,
        }
        Ok(())
    }
}

/// A take as the projector holds it: its arrays, how its uploads are made of them, its distinct
/// frames, its player (what the frames drawn lately draw, on the GPU), and whether its director
/// has finished it (or its scene failed).
pub(crate) struct Take {
    pub(crate) number: u32,
    pub(crate) size: (u32, u32), // its frames' own size (from START)
    pub(crate) player: Player,
    pack: Pack,
    recipes: HashMap<u64, Recipe>,
    shots: Vec<Shot>,
    used: HashMap<u64, u64>, // a key the player holds → the draw that last drew it
    draws: u64,
    pub(crate) frames: u32,
    pub(crate) fps: f64,
    pub(crate) ended: bool,
    failed: bool,
}

impl Take {
    /// One complete, successful recording, decoded by the same projector as a window or page.
    #[cfg(any(feature = "python", test))]
    pub(crate) fn read(stream: &[u8]) -> Result<Self, String> {
        let mut projector = Projector::default();
        projector.feed(stream)?;
        if !projector.pending.is_empty() { return Err("a message of the take ends early".into()); }
        if projector.takes != 1 { return Err("a recording must contain exactly one take".into()); }
        let take = projector.shown.unwrap();
        if !take.ended || take.failed { return Err("the take did not end successfully".into()); }
        if take.frames == 0 || take.size.0 == 0 || take.size.1 == 0 || !take.fps.is_finite() || take.fps <= 0.0 {
            return Err("a take needs frames, positive dimensions, and a finite positive frame rate".into());
        }
        Ok(take)
    }

    /// A recording's exact integer frame, including holds; every upload uses the projector's
    /// existing recipes and bounded decoded-array cache.
    #[cfg(any(feature = "python", test))]
    pub(crate) fn frame_views(&mut self, frame: u32) -> Result<Vec<Frame>, String> {
        if frame >= self.frames { return Err(format!("frame {frame} is outside the take's {} frames", self.frames)); }
        self.views(self.shot(frame).ok_or("the take has no recorded frames")?)
    }

    /// Each recorded shot's first frame and repeat count, without expanding its held frames.
    #[cfg(any(feature = "python", test))]
    pub(crate) fn timeline(&self) -> Vec<(u32, u32)> {
        self.shots.iter().enumerate().map(|(i, shot)| (shot.first, self.shots.get(i + 1).map_or(self.frames, |next| next.first) - shot.first)).collect()
    }

    /// Its frame at `time` seconds (the last, past its end).
    pub(crate) fn frame(&self, time: f64) -> u32 {
        ((time * self.fps + 1e-6).floor().max(0.0) as u32).min(self.frames.saturating_sub(1))
    }

    /// Whether it has the frame at `time`.
    fn has(&self, time: f64) -> bool {
        f64::from(self.frames) > (time * self.fps + 1e-6).floor()
    }

    /// Its shot showing `frame` (the last, past its end).
    fn shot(&self, frame: u32) -> Option<usize> {
        let last = self.shots.len().checked_sub(1)?;
        Some(self.shots.partition_point(|s| s.first <= frame).saturating_sub(1).min(last))
    }

    /// Shot `at`'s views (its cameras', then the frame), everything they draw in the player.
    fn views(&mut self, at: usize) -> Result<Vec<Frame>, String> {
        let Take { shots, pack, player, recipes, used, .. } = self;
        let shot = &shots[at];
        let mut cameras = Vec::with_capacity(shot.cameras.len());
        for (key, width, height, view, records) in &shot.cameras {
            cameras.push((*key, *width, *height, view.clone(), pack.get(*records)?.to_vec()));
        }
        let frames = player.views(&shot.view, &pack.get(shot.records)?, cameras)?;
        self.draws += 1;
        for frame in &frames {
            for keys in take::slots(bytemuck::cast_slice(&frame.records)) {
                for key in keys.into_iter().filter(|&k| k != 0) {
                    if let Some(recipe) = recipes.get_mut(&key) {
                        recipe.make(key, shot.first, pack, player)?;
                    }
                    used.insert(key, self.draws);
                }
            }
        }
        if player.held() > DRAWN {
            // what was drawn longest ago goes, down to half: the store then packs itself
            let mut by_use: Vec<(u64, u64)> = used.iter().filter(|&(_, &d)| d != self.draws).map(|(&k, &d)| (d, k)).collect();
            by_use.sort_unstable();
            for chunk in by_use.chunks(64) {
                if player.held() <= DRAWN / 2 {
                    break;
                }
                let keys: Vec<u64> = chunk.iter().map(|&(_, k)| k).collect();
                player.evict(&keys);
                for k in &keys {
                    used.remove(k);
                }
            }
        }
        Ok(frames)
    }
}

/// A note, as the projector hands it on with the number of the take it belongs to (0: none yet):
/// the director's JSON, or a take's sound (an audio file).
pub(crate) enum Note {
    Json(String),
    Sound(Vec<u8>),
}

/// How many see-through fragments a frame drawn through the lists appended, read back after the
/// frame (asynchronously: a frame never waits for it): more than they had room for, and the
/// lists grow, and the frame shown is drawn again (`settle`).
#[derive(Default)]
struct Count {
    buffer: Option<wgpu::Buffer>,
    read: std::sync::Arc<std::sync::atomic::AtomicBool>, // mapped: the count can be read
    of: Option<(u32, u64)>,                              // being read: of this take, its lists' room then
    copied: bool,                                        // the last frame encoded copies it
}

/// What reading back a frame's see-through count says (`Projector::settle`).
#[derive(PartialEq, Eq)]
pub(crate) enum Settled {
    Nothing,
    Waiting, // the count is on its way: settle again
    Redraw,  // the lists grew: draw the frame shown again
}

/// Takes: the one shown, and a newer one coming in beside it.
#[derive(Default)]
pub(crate) struct Projector {
    pub(crate) shown: Option<Take>,
    pub(crate) coming: Option<Take>, // until it reaches the moment shown, or ends
    drawn: Option<(u32, usize, (u32, u32))>, // the take, shot and size last drawn
    takes: u32,                      // takes begun
    pending: Vec<u8>,                // the start of a message still arriving
    count: Count,
}

impl Projector {
    /// Take in the next bytes of the stream: the notes among them, each with its take's number.
    pub(crate) fn feed(&mut self, chunk: &[u8]) -> Result<Vec<(u32, Note)>, String> {
        let mut notes = Vec::new();
        if self.pending.is_empty() {
            // read in place; keep what a message cut off
            let (messages, used) = take::messages(chunk);
            let result = messages.iter().try_for_each(|m| self.message(m, &mut notes));
            self.pending.extend_from_slice(&chunk[used..]);
            return result.map(|()| notes);
        }
        // a message arriving in pieces (an image, the sound) is read once it is whole: each piece
        // is only appended until then
        self.pending.extend_from_slice(chunk);
        let whole = self.pending.get(..4).is_some_and(|n| self.pending.len() >= 4 + u32::from_le_bytes(n.try_into().unwrap()) as usize);
        if !whole {
            return Ok(notes);
        }
        let pending = std::mem::take(&mut self.pending);
        let (messages, used) = take::messages(&pending);
        let result = messages.iter().try_for_each(|m| self.message(m, &mut notes));
        self.pending = pending[used..].to_vec();
        result.map(|()| notes)
    }

    fn message(&mut self, message: &[u8], notes: &mut Vec<(u32, Note)>) -> Result<(), String> {
        let mut f = Fields(message);
        let op = f.u8()?;
        if op == 0 {
            return Err("unversioned takes are unsupported; record the scene again with this version of ManimGX".into());
        }
        if op == take::START {
            let format = f.u32()?;
            if format != take::VERSION { return Err(format!("unsupported take format {format}; this engine reads format {}", take::VERSION)); }
            let (width, height, fps) = (f.u32()?, f.u32()?, f.f64()?);
            if width == 0 || height == 0 || !fps.is_finite() || fps <= 0.0 { return Err("a take needs positive dimensions and a finite positive frame rate".into()); }
            self.takes += 1;
            let fresh = Take { number: self.takes, size: (width, height), player: Player::new(width, height, 4), pack: Pack::default(), recipes: HashMap::new(), shots: Vec::new(), used: HashMap::new(), draws: 0, frames: 0, fps, ended: false, failed: false };
            // the first take is shown at once; a later one comes in beside it
            match self.shown {
                None => self.shown = Some(fresh),
                Some(_) => self.coming = Some(fresh),
            }
            return Ok(());
        }
        let newest = self.coming.as_mut().or(self.shown.as_mut());
        if op == take::NOTE || op == take::SOUND {
            // a note belongs to the newest take (0: none yet)
            let bytes = f.string()?;
            notes.push((newest.map_or(0, |t| t.number), if op == take::NOTE { Note::Json(String::from_utf8_lossy(bytes).into_owned()) } else { Note::Sound(bytes.to_vec()) }));
            return Ok(());
        }
        let Some(t) = newest else { return Err("a take begins with START".into()) };
        if t.ended { return Err("a take cannot change after END".into()); }
        // filed, not made: a frame makes what it draws when it is drawn
        let recipe = match op {
            take::ARRAY => return t.pack.add(&mut f),
            take::END => {
                (t.ended, t.failed) = (true, f.u8()? != 0);
                return Ok(());
            }
            take::PATH => (f.u64()?, Recipe::Path { centroid_area: f.f32s()?, points: f.u64()?, subpaths: f.u64()?, grown: Vec::new(), applied: 0 }),
            take::POINTS => (f.u64()?, Recipe::Points(f.u64()?)),
            take::MESH => (f.u64()?, Recipe::Mesh { outline: f.u32()?, block: f.u32()?, arrays: [f.u64()?, f.u64()?, f.u64()?, f.u64()?] }),
            take::ROWS => (f.u64()?, Recipe::Rows(f.u64()?)),
            take::TEXTURE => (f.u64()?, Recipe::Texture { width: f.u32()?, height: f.u32()?, rgba: f.u64()? }),
            take::ENVIRONMENT => {
                // made at once: the player keeps its environments (the views that show one name it)
                let (id, width, height, rgbe) = (f.u32()?, f.u32()?, f.u32()?, f.u64()?);
                return t.player.add_environment(id, width, height, &t.pack.get(rgbe)?);
            }
            take::GROW => {
                let (key, closed, tail) = (f.u64()?, f.u8()? != 0, f.u64()?);
                if let Some(Recipe::Path { grown, .. }) = t.recipes.get_mut(&key) {
                    grown.push((t.frames, tail, closed));
                }
                return Ok(());
            }
            take::FRAME => {
                let (repeat, view, records) = (f.u32()?, f.string()?.to_vec(), f.u64()?);
                if repeat == 0 { return Err("a recorded frame needs a positive repeat count".into()); }
                let frames = t.frames.checked_add(repeat).ok_or("the take has too many frames")?;
                let mut cameras = Vec::new();
                for _ in 0..f.u32()? {
                    cameras.push((f.u64()?, f.u32()?, f.u32()?, f.string()?.to_vec(), f.u64()?));
                }
                t.shots.push(Shot { first: t.frames, view, records, cameras });
                t.frames = frames;
                return Ok(());
            }
            op => return Err(format!("unknown message {op} in the take")),
        };
        t.recipes.insert(recipe.0, recipe.1);
        Ok(())
    }

    /// The take shown at `time` seconds: the coming one replaces it once it has that moment, or
    /// has ended short of it — unless its scene failed, and then it is dropped (the shown one
    /// stays, and so the place). Returns its number (0: none yet).
    pub(crate) fn show(&mut self, time: f64) -> u32 {
        if let Some(coming) = &self.coming {
            if coming.has(time) || (coming.ended && !coming.failed) {
                self.shown = self.coming.take();
            } else if coming.failed {
                self.coming = None;
            }
        }
        self.shown.as_ref().map_or(0, |t| t.number)
    }

    /// Whether the frame at `time`, at `size`, is what was drawn last (nothing to draw again).
    pub(crate) fn drawn(&self, time: f64, size: (u32, u32)) -> bool {
        let Some(t) = self.shown.as_ref() else { return true };
        t.shot(t.frame(time)).is_none_or(|at| self.drawn == Some((t.number, at, size)))
    }

    /// Draw the frame at `time` of the shown take at `size` (its proportions; a view is
    /// resolution-free but for its size in pixels) into its player's frame: the commands (None:
    /// no frame to draw yet). Its see-through count is read back once they are submitted
    /// (`submitted`, then `settle`).
    pub(crate) fn encode(&mut self, gpu: &mut Gpu, time: f64, size: (u32, u32)) -> Result<Option<wgpu::CommandEncoder>, String> {
        let Some(t) = self.shown.as_mut() else { return Ok(None) };
        let Some(at) = t.shot(t.frame(time)) else { return Ok(None) };
        if (t.player.width, t.player.height) != size {
            (t.player.width, t.player.height, t.player.targets) = (size.0, size.1, None);
        }
        let views = t.views(at)?;
        let views = resized(&views, t.size, size);
        let (mut encoder, _, composited) = t.player.encode(gpu, &views)?;
        self.drawn = Some((t.number, at, size));
        // the count is read for one frame at a time: the next is checked once it is in
        let count = &mut self.count;
        count.copied = false;
        if let Some(lists) = t.player.lists.as_ref().filter(|_| composited && count.of.is_none()) {
            let buffer = count.buffer.get_or_insert_with(|| {
                let usage = wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ;
                gpu.device.create_buffer(&wgpu::BufferDescriptor { label: Some("count"), size: crate::render::COUNT_BYTES, usage, mapped_at_creation: false })
            });
            encoder.copy_buffer_to_buffer(&lists.appended, 0, buffer, 0, Some(crate::render::COUNT_BYTES));
            (count.of, count.copied) = (Some((t.number, lists.capacity)), true);
        }
        Ok(Some(encoder))
    }

    /// The commands of the last `encode` were submitted: its count, if it copied one, is read.
    pub(crate) fn submitted(&mut self) {
        let count = &mut self.count;
        if let Some(buffer) = count.buffer.as_ref().filter(|_| std::mem::take(&mut count.copied)) {
            let read = count.read.clone();
            buffer.slice(..).map_async(wgpu::MapMode::Read, move |result| read.store(result.is_ok(), std::sync::atomic::Ordering::Release));
        }
    }

    /// Read the see-through count of the frame last drawn through the lists, once it is back:
    /// if the lists overflowed they grow, and the frame shown is to be drawn again.
    pub(crate) fn settle(&mut self, gpu: &Gpu) -> Result<Settled, String> {
        let Some((take, capacity)) = self.count.of else { return Ok(Settled::Nothing) };
        if !self.count.read.load(std::sync::atomic::Ordering::Acquire) {
            return Ok(Settled::Waiting);
        }
        let buffer = self.count.buffer.as_ref().expect("counted");
        let appended = crate::render::count(&buffer.slice(..).get_mapped_range().map_err(|e| e.to_string())?);
        buffer.unmap();
        self.count.of = None;
        self.count.read.store(false, std::sync::atomic::Ordering::Release);
        let Some(t) = self.shown.as_mut().filter(|t| t.number == take) else { return Ok(Settled::Nothing) };
        if t.player.overflowed(gpu, appended, capacity) {
            self.drawn = None;
            return Ok(Settled::Redraw);
        }
        Ok(Settled::Nothing)
    }
}

/// The largest size of a take's proportions (`own`) that fits `into` (a texture's most, 8192).
pub(crate) fn fit(own: (u32, u32), into: (u32, u32)) -> (u32, u32) {
    let scale = (into.0 as f32 / own.0 as f32).min(into.1 as f32 / own.1 as f32).min(8192.0 / own.0.max(own.1) as f32);
    ((own.0 as f32 * scale).round().max(1.0) as u32, (own.1 as f32 * scale).round().max(1.0) as u32)
}

/// A shot's views, the frame drawn at `size` rather than its own (`own`): its size in pixels,
/// and its pixels per scene unit, which strokes' widths are in (the cameras' views keep theirs).
fn resized(views: &[Frame], own: (u32, u32), size: (u32, u32)) -> std::borrow::Cow<'_, [Frame]> {
    if own == size {
        return std::borrow::Cow::Borrowed(views);
    }
    let mut views = views.to_vec();
    if let Some(frame) = views.last_mut() {
        let v = &mut frame.view;
        (v[32], v[33], v[34]) = (size.0 as f32, size.1 as f32, v[34] * size.1 as f32 / own.1 as f32);
        (frame.width, frame.height) = size;
    }
    std::borrow::Cow::Owned(views)
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;
    use crate::take::Writer;

    /// A take of `frames` frames at 30 a second, a frame a hold; ended (failed or not), or still
    /// being recorded (None).
    fn take(frames: u32, end: Option<bool>) -> Vec<u8> {
        let mut w = Writer::default();
        w.start(64, 36, 30.0);
        for _ in 0..frames {
            w.frame(&[0; 4 * crate::render::VIEW_FLOATS + 16], &[], 1, &[]);
        }
        if let Some(failed) = end {
            w.close(failed);
        }
        w.drain()
    }

    fn shown(p: &Projector) -> Option<(u32, u32, bool)> {
        p.shown.as_ref().map(|t| (t.number, t.frames, t.ended))
    }

    #[test]
    fn a_recording_is_exactly_one_complete_successful_take() {
        let stream = take(2, Some(false));
        let recording = Take::read(&stream).unwrap();
        assert_eq!((recording.size, recording.frames, recording.fps), ((64, 36), 2, 30.0));
        for end in 0..stream.len() { assert!(Take::read(&stream[..end]).is_err(), "cut at {end}"); }
        for bad in [take(0, Some(false)), take(2, None), take(2, Some(true)), [stream.clone(), stream].concat()] {
            assert!(Take::read(&bad).is_err());
        }
    }

    #[test]
    fn an_unsupported_take_is_rejected_before_its_resources_are_read() {
        let stream = take(2, Some(false));
        for version in [0, take::VERSION + 1, u32::MAX] {
            let mut unsupported = stream.clone();
            unsupported[5..9].copy_from_slice(&version.to_le_bytes());
            // Split even the length and version fields, as native and browser streams can be.
            for chunk in [1, 3, unsupported.len()] {
                let mut projector = Projector::default();
                let result = unsupported.chunks(chunk).try_for_each(|bytes| projector.feed(bytes).map(|_| ()));
                assert_eq!(result.unwrap_err(), format!("unsupported take format {version}; this engine reads format {}", take::VERSION));
                assert!(projector.shown.is_none());
            }
        }
        // The former START had no version, only width, height and fps (17 payload bytes).
        let legacy = [17u32.to_le_bytes().as_slice(), &[0], &64u32.to_le_bytes(), &36u32.to_le_bytes(), &30f64.to_le_bytes()].concat();
        let mut projector = Projector::default();
        assert!(projector.feed(&legacy).err().unwrap().contains("unversioned takes are unsupported"));
        assert!(projector.shown.is_none());
    }

    #[test]
    fn a_recording_seeks_exact_integer_frames_including_holds() {
        let mut w = Writer::default();
        w.start(64, 36, 29.97);
        let mut view = vec![0.0_f32; crate::render::VIEW_LENGTH];
        view[44] = 0.25;
        let cameras = vec![(7, 16, 12, bytemuck::cast_slice(&view).to_vec(), Vec::new())];
        w.frame(bytemuck::cast_slice(&view), &[], 3, &cameras);
        view[44] = 0.75;
        w.frame(bytemuck::cast_slice(&view), &[], 2, &cameras);
        w.close(false);
        let mut recording = Take::read(&w.drain()).unwrap();
        assert_eq!(recording.timeline(), [(0, 3), (3, 2)]);
        for frame in [4, 0, 3, 2, 1, 4] {
            let views = recording.frame_views(frame).unwrap();
            assert_eq!(views.len(), 2);
            assert_eq!((views[0].key, views[0].width, views[0].height), (7, 16, 12));
            assert_eq!(views[0].view[44], 0.25);
            assert_eq!(views[1].view[44], if frame < 3 { 0.25 } else { 0.75 });
        }
        assert!(recording.frame_views(5).is_err());
        assert!(recording.frame_views(u32::MAX).is_err());
    }

    /// The first take is shown at once; a newer one comes in beside it and replaces it once it
    /// has the moment shown — or has ended, shorter.
    #[test]
    fn a_newer_take_replaces_the_shown_one_at_the_moment_shown() {
        let mut p = Projector::default();
        p.feed(&take(10, Some(false))).unwrap();
        assert_eq!(shown(&p), Some((1, 10, true)));
        let coming = take(8, None);
        let (head, tail) = coming.split_at(coming.len() / 2);
        p.feed(head).unwrap();
        assert_eq!(p.show(7.0 / 30.0), 1, "the newer take has no frame 7 yet");
        p.feed(tail).unwrap();
        assert_eq!(p.show(7.0 / 30.0), 2);
        assert_eq!(shown(&p), Some((2, 8, false)));
        p.feed(&take(3, Some(false))).unwrap();
        assert_eq!(p.show(7.0 / 30.0), 3, "a newer take that ended shorter replaces it all the same");
    }

    /// A take whose scene failed replaces the shown one only if it got to the moment shown;
    /// else it is dropped, and the shown one stays.
    #[test]
    fn a_failed_take_replaces_the_shown_one_only_if_it_got_there() {
        let mut p = Projector::default();
        p.feed(&take(10, Some(false))).unwrap();
        p.feed(&take(4, Some(true))).unwrap();
        assert_eq!(p.show(0.5), 1);
        assert!(p.coming.is_none());
        p.feed(&take(20, Some(true))).unwrap();
        assert_eq!(p.show(0.5), 3);
        assert_eq!(shown(&p), Some((3, 20, true)));
    }

    /// The stream is read whole however it is cut: notes come with the number of the take they
    /// belong to, the director's between takes with the newest one's.
    #[test]
    fn notes_come_with_their_take_however_the_stream_is_cut() {
        let mut w = Writer::default();
        w.note(r#"{"scenes": ["A"], "scene": "A"}"#);
        let between = w.drain();
        let mut stream = take(2, None);
        stream.extend(&between);
        stream.extend(take(1, Some(false)));
        stream.extend(&between);
        let read = |cut: usize| {
            let mut p = Projector::default();
            let notes: Vec<u32> = stream.chunks(cut).flat_map(|c| p.feed(c).unwrap()).map(|(n, _)| n).collect();
            (notes, shown(&p), p.coming.as_ref().map(|t| (t.number, t.frames, t.ended)))
        };
        let whole = read(stream.len());
        assert_eq!(whole, (vec![1, 2], Some((1, 2, false)), Some((2, 1, true))));
        for cut in [1, 7, 100] {
            assert_eq!(read(cut), whole);
        }
    }
}

#[cfg(test)]
mod decoder_contract {
    use super::*;

    fn message(op: u8, fields: &[u8]) -> Vec<u8> {
        [(fields.len() as u32 + 1).to_le_bytes().as_slice(), &[op], fields].concat()
    }
    fn start(width: u32, height: u32, fps: f64) -> Vec<u8> {
        message(take::START, &[take::VERSION.to_le_bytes().as_slice(), &width.to_le_bytes(), &height.to_le_bytes(), &fps.to_le_bytes()].concat())
    }
    fn array(key: u64, base: u64, kind: Kind, mode: u8) -> Vec<u8> {
        [key.to_le_bytes().as_slice(), &base.to_le_bytes(), &[kind as u8, mode], &0u32.to_le_bytes()].concat()
    }
    fn frame(repeat: u32) -> Vec<u8> {
        message(take::FRAME, &[repeat.to_le_bytes().as_slice(), &0u32.to_le_bytes(), &1u64.to_le_bytes(), &0u32.to_le_bytes()].concat())
    }

    #[cfg_attr(target_arch = "wasm32", wasm_bindgen_test::wasm_bindgen_test)]
    #[cfg_attr(not(target_arch = "wasm32"), test)]
    fn arrays_have_immutable_preceding_bases_of_the_same_kind() {
        let mut p = Projector::default();
        p.feed(&start(64, 36, 30.0)).unwrap();
        p.feed(&message(take::ARRAY, &array(1, 0, Kind::Points, pack::ALONE))).unwrap();
        for bad in [
            array(0, 0, Kind::Points, pack::ALONE),
            array(1, 0, Kind::Points, pack::ALONE),
            array(2, 2, Kind::Points, pack::FIRST), // self-cycle
            array(2, 3, Kind::Points, pack::FIRST), // forward reference
            array(2, 1, Kind::Texture, pack::FIRST),
            array(2, 1, Kind::Points, pack::ALONE),
            array(2, 0, Kind::Points, pack::FIRST),
            array(2, 1, Kind::Points, pack::SECOND), // no grandparent
            array(2, 1, Kind::Points, 255),
        ] {
            assert!(p.feed(&message(take::ARRAY, &bad)).is_err());
            assert_eq!(p.shown.as_ref().unwrap().pack.arrays.len(), 1);
        }
        p.feed(&message(take::ARRAY, &array(2, 1, Kind::Points, pack::FIRST))).unwrap();
        p.feed(&message(take::ARRAY, &array(3, 2, Kind::Points, pack::SECOND))).unwrap();
        p.feed(&message(take::END, &[0])).unwrap();
        p.feed(&message(take::NOTE, &[2u32.to_le_bytes().as_slice(), b"{}"].concat())).unwrap();
        p.feed(&start(64, 36, 30.0)).unwrap();
        p.feed(&message(take::ARRAY, &array(1, 0, Kind::Texture, pack::ALONE))).unwrap();
        assert_eq!(p.shown.as_ref().unwrap().pack.arrays[&1].kind, Kind::Points);
        assert_eq!(p.coming.as_ref().unwrap().pack.arrays[&1].kind, Kind::Texture);
    }

    #[cfg_attr(target_arch = "wasm32", wasm_bindgen_test::wasm_bindgen_test)]
    #[cfg_attr(not(target_arch = "wasm32"), test)]
    fn array_dependencies_stop_at_the_writers_keyframe_bound() {
        let mut pack = Pack::default();
        for depth in 0..=pack::DEPTH {
            let mode = if depth == 0 { pack::ALONE } else { pack::FIRST };
            pack.add(&mut Fields(&array(depth as u64 + 1, depth as u64, Kind::Points, mode))).unwrap();
        }
        let deepest = pack::DEPTH as u64 + 1;
        assert!(pack.add(&mut Fields(&array(deepest + 1, deepest, Kind::Points, pack::FIRST))).is_err());
        assert_eq!(pack.arrays.len(), deepest as usize);
    }

    #[cfg_attr(target_arch = "wasm32", wasm_bindgen_test::wasm_bindgen_test)]
    #[cfg_attr(not(target_arch = "wasm32"), test)]
    fn frame_holds_are_positive_checked_and_end_with_the_take() {
        let mut p = Projector::default();
        p.feed(&start(64, 36, 30.0)).unwrap();
        assert!(p.feed(&frame(0)).is_err());
        assert!(p.shown.as_ref().unwrap().shots.is_empty());
        p.feed(&frame(u32::MAX)).unwrap();
        assert!(p.feed(&frame(1)).is_err());
        let t = p.shown.as_ref().unwrap();
        assert_eq!((t.frames, t.shots.len()), (u32::MAX, 1));
        p.feed(&message(take::END, &[0])).unwrap();
        assert!(p.feed(&frame(1)).is_err());
        assert!(p.feed(&message(take::ARRAY, &array(1, 0, Kind::Points, pack::ALONE))).is_err());
        assert_eq!(p.shown.as_ref().unwrap().frames, u32::MAX);
    }

    #[cfg_attr(target_arch = "wasm32", wasm_bindgen_test::wasm_bindgen_test)]
    #[cfg_attr(not(target_arch = "wasm32"), test)]
    fn invalid_start_does_not_replace_the_live_take() {
        let mut p = Projector::default();
        p.feed(&start(64, 36, 30.0)).unwrap();
        for (width, height, fps) in [(0, 36, 30.0), (64, 0, 30.0), (64, 36, 0.0), (64, 36, -1.0), (64, 36, f64::INFINITY), (64, 36, f64::NAN)] {
            assert!(p.feed(&start(width, height, fps)).is_err());
            assert!(p.coming.is_none());
            assert_eq!((p.takes, p.shown.as_ref().unwrap().size), (1, (64, 36)));
        }
    }
}
