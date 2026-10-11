//! H.264 through x264 (the `x264` crate: x264 built from its source), told which macroblocks did
//! not change since the previous frame, into an MP4.
//!
//! The film knows what changed; x264 honors `X264_MBINFO_CONSTANT` per macroblock (with
//! `analyse.b_mb_info`) and skips its analysis there. A held picture is one sample that lasts
//! longer: nothing is encoded for it, its duration is the gap to the next pts. x264 writes each
//! picture as NAL units prefixed by their sizes — an MP4 sample as it is.

use crate::mp4::{Audio, Mp4};

/// A frame as the encoder receives it: what changed since the previous one — the converted
/// macroblocks (`listed`, and their NV12 `packets`, 384 bytes each: luma 16×16, then chroma 8
/// rows of 16) — and for how many frames it shows. The encoder keeps the picture.
pub struct Change {
    pub listed: Vec<u32>,
    pub packets: Vec<u8>,
    pub first: bool,
    pub repeat: u32,
    /// A keyframe: a player can start here (a section's first frame).
    pub key: bool,
}

/// One changed macroblock into the picture: the part of it inside the picture (a picture whose
/// sides are not multiples of 16 ends in partial macroblocks, right and bottom).
fn scatter(packet: &[u8], mb: usize, columns: usize, width: usize, height: usize, nv12: &mut [u8]) {
    let (x, y) = ((mb % columns) * 16, (mb / columns) * 16);
    let inside = 16.min(width - x); // bytes of a row: luma, or chroma's interleaved pairs
    for row in 0..16.min(height.saturating_sub(y)) {
        let at = (y + row) * width + x;
        nv12[at..at + inside].copy_from_slice(&packet[row * 16..row * 16 + inside]);
    }
    let luma = width * height;
    for row in 0..8.min((height / 2).saturating_sub(y / 2)) {
        let at = luma + (y / 2 + row) * width + x;
        nv12[at..at + inside].copy_from_slice(&packet[256 + row * 16..256 + row * 16 + inside]);
    }
}

/// An encoder on its own thread, keeping the picture: changes go in through a channel, so
/// drawing, converting and encoding overlap, and a frame costs the thread that draws it only
/// what changed. `join` writes the file and returns (bytes written, seconds spent in x264);
/// `abort` leaves no file.
pub struct Worker {
    frames: std::sync::mpsc::SyncSender<Change>,
    sound: std::sync::mpsc::Sender<Option<Audio>>,
    thread: std::thread::JoinHandle<Result<(u64, f64), String>>,
    aborted: std::sync::Arc<std::sync::atomic::AtomicBool>,
}

impl Worker {
    pub fn new(mut encoder: Encoder, width: usize, height: usize) -> Self {
        let (frames, inbox) = std::sync::mpsc::sync_channel::<Change>(8);
        let (sound, heard) = std::sync::mpsc::channel::<Option<Audio>>();
        let aborted = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
        let stop = aborted.clone();
        let thread = std::thread::spawn(move || {
            let mut busy = 0.0;
            let mut nv12 = vec![0u8; width * height * 3 / 2];
            let (columns, rows) = (width.div_ceil(16), height.div_ceil(16));
            for change in inbox {
                if stop.load(std::sync::atomic::Ordering::Acquire) {
                    break;
                }
                let t0 = std::time::Instant::now();
                let mut constant = vec![1u8; columns * rows];
                for (k, &mb) in change.listed.iter().enumerate() {
                    scatter(&change.packets[k * 384..k * 384 + 384], mb as usize, columns, width, height, &mut nv12);
                    constant[mb as usize] = 0;
                }
                encoder.encode(&nv12, (!change.first).then_some(&constant[..]), change.repeat, change.key)?;
                busy += t0.elapsed().as_secs_f64();
            }
            if stop.load(std::sync::atomic::Ordering::Acquire) {
                return Err("the video was abandoned".into());
            }
            let audio = heard.recv().ok().flatten();
            let t0 = std::time::Instant::now();
            let bytes = encoder.finish(audio.as_ref())?;
            Ok((bytes, busy + t0.elapsed().as_secs_f64()))
        });
        Self { frames, sound, thread, aborted }
    }

    /// Stop without writing the file: its partial samples are deleted by the time this returns
    /// (the thread ends at its next frame and drops the encoder, and the encoder its MP4).
    pub fn abort(self) {
        self.aborted.store(true, std::sync::atomic::Ordering::Release);
        let _ = self.join(None);
    }

    pub fn send(&self, change: Change) -> Result<(), String> {
        self.frames.send(change).map_err(|_| "the encoder stopped".to_string())
    }

    /// Write the file, with `audio` beside the video, if any.
    pub fn join(self, audio: Option<Audio>) -> Result<(u64, f64), String> {
        let _ = self.sound.send(audio);
        drop(self.frames);
        self.thread.join().map_err(|_| "the encoder panicked".to_string())?
    }
}

pub struct Encoder {
    x264: x264::Encoder,
    mp4: Mp4,
    pts: i64,
}

impl Encoder {
    /// `options`: x264's own (name, value) settings, applied over the preset (as `-x264-params`).
    #[allow(clippy::too_many_arguments)]
    pub fn new(width: u32, height: u32, fps: u32, preset: &str, crf: f32, options: &[(String, String)], path: &str) -> Result<Self, String> {
        let x264 = x264::Encoder::new(width, height, fps, preset, crf, options)?;
        let mp4 = Mp4::new(path, width, height, fps, x264.sps.clone(), x264.pps.clone()).map_err(|e| e.to_string())?;
        Ok(Self { x264, mp4, pts: 0 })
    }

    /// Encode one NV12 frame shown for `duration` frames; `constant` (one byte per macroblock,
    /// nonzero = unchanged since the previous frame) lets x264 skip those macroblocks; `key`
    /// makes it a keyframe.
    pub fn encode(&mut self, nv12: &[u8], constant: Option<&[u8]>, duration: u32, key: bool) -> Result<(), String> {
        let pts = self.pts;
        self.pts += duration as i64;
        if let Some(sample) = self.x264.encode(Some(nv12), pts, constant, key)? {
            self.mp4.sample(sample.data, sample.pts, sample.key).map_err(|e| e.to_string())?;
        }
        Ok(())
    }

    /// Drain the frames x264 still holds and write the file, with `audio` if any; returns its
    /// size.
    pub fn finish(self, audio: Option<&Audio>) -> Result<u64, String> {
        let Self { mut x264, mut mp4, pts } = self;
        while x264.delayed() {
            if let Some(sample) = x264.encode(None, 0, None, false)? {
                mp4.sample(sample.data, sample.pts, sample.key).map_err(|e| e.to_string())?;
            }
        }
        mp4.finish(pts, audio).map_err(|e| e.to_string())
    }
}
