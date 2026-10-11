//! MP4 (ISO/IEC 14496-12/14/15) holding an H.264 track and, if the film has sound, an AAC-LC track;
//! faststart.
//!
//! A video sample is a picture as x264 writes it (NAL units, each prefixed by its 4-byte size) and a
//! held picture is one sample that lasts longer — times are in frames (timescale = fps). With
//! B-frames (the slower presets), a picture can be decoded before the one it follows: the samples
//! are in decode order, each retaining its duration; signed composition offsets give its
//! presentation time. An audio
//! sample is an AAC access unit of 1024 samples; the encoder's priming before the sound's first
//! sample is skipped by an edit list, so the sound starts with the film, to the sample. Video
//! samples stream to a temporary file; `finish` writes the header (`moov`), then the samples,
//! a second of video and a second of sound at a time, so a player can start before the file has
//! arrived.

use std::fs::File;
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::ops::Range;

pub struct Mp4 {
    path: String,
    part: String,
    data: Option<BufWriter<File>>,
    width: u32,
    height: u32,
    fps: u32,
    sps: Vec<u8>,
    pps: Vec<u8>,
    samples: Vec<Sample>,
    bytes: u64,
}

struct Sample {
    size: u32,
    pts: i64,
    duration: u32,
    key: bool,
}

/// A film's sound, encoded: AAC-LC access units of 1024 samples each, in order.
pub struct Audio {
    pub rate: u32,
    pub channels: u16,
    /// The AudioSpecificConfig (the decoder's configuration).
    pub config: Vec<u8>,
    /// Samples the encoder put before the sound's first (hidden by the edit list).
    pub priming: u32,
    /// The sound's own samples, after the priming: what plays.
    pub length: u64,
    pub units: Vec<Vec<u8>>,
}

/// Where each track's chunks go in `mdat`, in file order: (audio?, the samples it holds).
type Layout = Vec<(bool, Range<usize>)>;

impl Mp4 {
    /// `sps`, `pps`: the stream's parameter sets, without size prefixes.
    pub fn new(path: &str, width: u32, height: u32, fps: u32, sps: Vec<u8>, pps: Vec<u8>) -> io::Result<Self> {
        if sps.len() < 4 || pps.is_empty() {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "H.264 parameter sets are missing"));
        }
        let part = format!("{path}.part");
        let data = BufWriter::with_capacity(1 << 20, File::create(&part)?);
        Ok(Self { path: path.to_string(), part, data: Some(data), width, height, fps, sps, pps, samples: Vec::new(), bytes: 0 })
    }

    pub fn sample(&mut self, data: &[u8], pts: i64, key: bool) -> io::Result<()> {
        if data.is_empty() {
            return Ok(());
        }
        self.data.as_mut().ok_or_else(|| io::Error::other("the video is finished"))?.write_all(data)?;
        self.bytes += data.len() as u64;
        self.samples.push(Sample { size: data.len() as u32, pts, duration: 0, key });
        Ok(())
    }

    /// Write the file: the video lasts until `end` (in frames — the last hold included), with
    /// `audio` beside it, if any. A file that could not be written whole is not left behind.
    pub fn finish(mut self, end: i64, audio: Option<&Audio>) -> io::Result<u64> {
        if let Some(mut data) = self.data.take() {
            data.flush()?;
        }
        // Recover each picture's authored duration in presentation order, retaining the
        // encoder's sample order. In particular, the final displayed picture owns the hold,
        // even when B-frames follow it in decode order.
        let mut order: Vec<_> = (0..self.samples.len()).collect();
        order.sort_unstable_by_key(|&i| self.samples[i].pts);
        let mut until = end;
        for i in order.into_iter().rev() {
            self.samples[i].duration = (until - self.samples[i].pts) as u32;
            until = self.samples[i].pts;
        }
        let written = self.write(end, audio);
        if written.is_err() {
            let _ = std::fs::remove_file(&self.path);
        }
        written
    }

    /// The chunks: the whole video in one without sound; with sound, a second of each in turn.
    fn layout(&self, audio: Option<&Audio>) -> Layout {
        let Some(audio) = audio else {
            return vec![(false, 0..self.samples.len())];
        };
        // A picture must arrive before its own presentation and every later picture in
        // decode order: any of them may need it as a reference. Signed composition offsets
        // make the sample-duration clock unsuitable as a progressive-download deadline.
        let mut deadlines: Vec<_> = self.samples.iter().map(|s| s.pts).collect();
        for i in (1..deadlines.len()).rev() {
            deadlines[i - 1] = deadlines[i - 1].min(deadlines[i]);
        }
        let (mut chunks, mut v, mut a, mut second) = (Vec::new(), 0, 0, 1i64);
        while v < self.samples.len() || a < audio.units.len() {
            let v0 = v;
            while v < self.samples.len() && deadlines[v] < second * self.fps as i64 {
                v += 1;
            }
            if v > v0 {
                chunks.push((false, v0..v));
            }
            let a0 = a;
            while a < audio.units.len() && (a as i64 * 1024) < second * audio.rate as i64 {
                a += 1;
            }
            if a > a0 {
                chunks.push((true, a0..a));
            }
            second += 1;
        }
        chunks
    }

    fn write(&self, end: i64, audio: Option<&Audio>) -> io::Result<u64> {
        let sound: u64 = audio.map_or(0, |a| a.units.iter().map(|u| u.len() as u64).sum());
        let body = self.bytes + sound;
        let wide = body + 16 > u32::MAX as u64;
        let header = if wide { 16 } else { 8 };
        let layout = self.layout(audio);
        let ftyp = ftyp();
        let probe = self.moov(end, audio, &layout, 0, wide)?;
        let start = (ftyp.len() + probe.len() + header) as u64;
        let moov = self.moov(end, audio, &layout, start, wide)?;
        let mut out = BufWriter::with_capacity(1 << 20, File::create(&self.path)?);
        out.write_all(&ftyp)?;
        out.write_all(&moov)?;
        if wide {
            out.write_all(&1u32.to_be_bytes())?;
            out.write_all(b"mdat")?;
            out.write_all(&(body + 16).to_be_bytes())?;
        } else {
            out.write_all(&((body + 8) as u32).to_be_bytes())?;
            out.write_all(b"mdat")?;
        }
        let mut video = BufReader::with_capacity(1 << 20, File::open(&self.part)?);
        for (is_audio, range) in &layout {
            if *is_audio {
                for unit in &audio.expect("audio chunks come with audio").units[range.clone()] {
                    out.write_all(unit)?;
                }
            } else {
                let bytes: u64 = self.samples[range.clone()].iter().map(|s| s.size as u64).sum();
                io::copy(&mut (&mut video).take(bytes), &mut out)?;
            }
        }
        out.flush()?;
        Ok((ftyp.len() + moov.len() + header) as u64 + body)
    }

    /// Each track's chunks: (their offsets in the file, the samples each holds).
    fn chunks(&self, audio: Option<&Audio>, layout: &Layout, offset: u64) -> [(Vec<u64>, Vec<u32>); 2] {
        let mut tracks: [(Vec<u64>, Vec<u32>); 2] = Default::default();
        let mut at = offset;
        for (is_audio, range) in layout {
            let size: u64 = if *is_audio {
                audio.map_or(0, |a| a.units[range.clone()].iter().map(|u| u.len() as u64).sum())
            } else {
                self.samples[range.clone()].iter().map(|s| s.size as u64).sum()
            };
            let track = &mut tracks[*is_audio as usize];
            track.0.push(at);
            track.1.push(range.len() as u32);
            at += size;
        }
        tracks
    }

    /// The header, with the samples starting at byte `offset` of the file.
    fn moov(&self, end: i64, audio: Option<&Audio>, layout: &Layout, offset: u64, wide: bool) -> io::Result<Vec<u8>> {
        // ISO/IEC 14496-12: decoding timestamps order samples; composition timestamps say
        // when they appear. Accumulate their own durations in decode order and preserve every
        // authored presentation time with signed ctts offsets. This also gives the last
        // displayed picture its proper duration, without a decode-preroll edit or extra frames.
        let duration = end.max(1) as u32;
        let deltas: Vec<_> = self.samples.iter().map(|s| s.duration).collect();
        let mut decode = 0;
        let offsets: Vec<_> = self.samples.iter().map(|s| {
            let offset = i32::try_from(s.pts - decode)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "MP4 composition offset exceeds 32-bit range"))?;
            decode += s.duration as i64;
            Ok(offset as u32)
        }).collect::<io::Result<_>>()?;
        let [(video_at, video_counts), (audio_at, audio_counts)] = self.chunks(audio, layout, offset);
        // the sound's length in the movie's timescale (frames)
        let heard = audio.map_or(0, |a| (a.length * self.fps as u64).div_ceil(a.rate as u64) as u32);
        let mut w = Boxes::default();
        w.boxed(b"moov", |w| {
            w.full(b"mvhd", 0, 0, |w| {
                w.u32(0);
                w.u32(0);
                w.u32(self.fps);
                w.u32(duration.max(heard));
                w.u32(0x0001_0000);
                w.u16(0x0100);
                w.zeros(10);
                w.matrix();
                w.zeros(24);
                w.u32(if audio.is_some() { 3 } else { 2 });
            });
            w.boxed(b"trak", |w| {
                w.full(b"tkhd", 0, 3, |w| {
                    w.u32(0);
                    w.u32(0);
                    w.u32(1);
                    w.u32(0);
                    w.u32(duration);
                    w.zeros(8);
                    w.u16(0);
                    w.u16(0);
                    w.u16(0);
                    w.u16(0);
                    w.matrix();
                    w.u32(self.width << 16);
                    w.u32(self.height << 16);
                });
                w.boxed(b"mdia", |w| {
                    w.full(b"mdhd", 0, 0, |w| {
                        w.u32(0);
                        w.u32(0);
                        w.u32(self.fps);
                        w.u32(duration);
                        w.u16(0x55c4); // "und"
                        w.u16(0);
                    });
                    w.full(b"hdlr", 0, 0, |w| {
                        w.u32(0);
                        w.bytes(b"vide");
                        w.zeros(12);
                        w.bytes(b"VideoHandler\0");
                    });
                    w.boxed(b"minf", |w| {
                        w.full(b"vmhd", 0, 1, |w| w.zeros(8));
                        w.dinf();
                        w.boxed(b"stbl", |w| {
                            w.full(b"stsd", 0, 0, |w| {
                                w.u32(1);
                                self.avc1(w);
                            });
                            w.full(b"stts", 0, 0, |w| w.runs(&deltas));
                            if offsets.iter().any(|&o| o != 0) {
                                w.full(b"ctts", 1, 0, |w| w.runs(&offsets));
                            }
                            if self.samples.iter().any(|s| !s.key) {
                                let keys: Vec<u32> = (1..).zip(&self.samples).filter(|(_, s)| s.key).map(|(k, _)| k).collect();
                                w.full(b"stss", 0, 0, |w| {
                                    w.u32(keys.len() as u32);
                                    keys.iter().for_each(|&k| w.u32(k));
                                });
                            }
                            w.stsc(&video_counts);
                            w.full(b"stsz", 0, 0, |w| {
                                w.u32(0);
                                w.u32(self.samples.len() as u32);
                                self.samples.iter().for_each(|s| w.u32(s.size));
                            });
                            w.stco(&video_at, wide);
                        });
                    });
                });
            });
            if let Some(audio) = audio {
                self.sound(w, audio, heard, &audio_counts, &audio_at, wide);
            }
        });
        Ok(w.0)
    }

    /// The sound's track: AAC-LC, its priming cut by an edit list, a unit of pre-roll.
    fn sound(&self, w: &mut Boxes, audio: &Audio, heard: u32, counts: &[u32], at: &[u64], wide: bool) {
        let units = audio.units.len() as u32;
        let bitrate = (audio.units.iter().map(|u| u.len() as u64).sum::<u64>() * 8 * audio.rate as u64 / (units.max(1) as u64 * 1024)) as u32;
        w.boxed(b"trak", |w| {
            w.full(b"tkhd", 0, 3, |w| {
                w.u32(0);
                w.u32(0);
                w.u32(2);
                w.u32(0);
                w.u32(heard);
                w.zeros(8);
                w.u16(0);
                w.u16(1); // alternate group: sound
                w.u16(0x0100); // volume
                w.u16(0);
                w.matrix();
                w.u32(0);
                w.u32(0);
            });
            w.boxed(b"edts", |w| {
                w.full(b"elst", 0, 0, |w| {
                    w.u32(1);
                    w.u32(heard); // in the movie's timescale
                    w.u32(audio.priming); // in the track's: where the sound's first sample is
                    w.u16(1);
                    w.u16(0);
                });
            });
            w.boxed(b"mdia", |w| {
                w.full(b"mdhd", 0, 0, |w| {
                    w.u32(0);
                    w.u32(0);
                    w.u32(audio.rate);
                    w.u32(units * 1024);
                    w.u16(0x55c4); // "und"
                    w.u16(0);
                });
                w.full(b"hdlr", 0, 0, |w| {
                    w.u32(0);
                    w.bytes(b"soun");
                    w.zeros(12);
                    w.bytes(b"SoundHandler\0");
                });
                w.boxed(b"minf", |w| {
                    w.full(b"smhd", 0, 0, |w| w.u32(0));
                    w.dinf();
                    w.boxed(b"stbl", |w| {
                        w.full(b"stsd", 0, 0, |w| {
                            w.u32(1);
                            w.boxed(b"mp4a", |w| {
                                w.zeros(6);
                                w.u16(1); // data reference
                                w.zeros(8);
                                w.u16(audio.channels);
                                w.u16(16);
                                w.u32(0);
                                w.u32(audio.rate << 16);
                                w.full(b"esds", 0, 0, |w| {
                                    let config = &audio.config;
                                    // ES_Descriptor ⊃ DecoderConfigDescriptor ⊃ DecoderSpecificInfo;
                                    // SLConfigDescriptor
                                    w.u8(0x03);
                                    w.u8((3 + 2 + 13 + 2 + config.len() + 3) as u8);
                                    w.u16(0);
                                    w.u8(0);
                                    w.u8(0x04);
                                    w.u8((13 + 2 + config.len()) as u8);
                                    w.u8(0x40); // MPEG-4 audio
                                    w.u8(0x15); // audio stream
                                    w.bytes(&[0, 0x18, 0]); // buffer size: 6144 bytes
                                    w.u32(bitrate);
                                    w.u32(bitrate);
                                    w.u8(0x05);
                                    w.u8(config.len() as u8);
                                    w.bytes(config);
                                    w.u8(0x06);
                                    w.u8(1);
                                    w.u8(0x02);
                                });
                            });
                        });
                        w.full(b"stts", 0, 0, |w| {
                            w.u32(1);
                            w.u32(units);
                            w.u32(1024);
                        });
                        w.stsc(counts);
                        w.full(b"stsz", 0, 0, |w| {
                            w.u32(0);
                            w.u32(units);
                            audio.units.iter().for_each(|u| w.u32(u.len() as u32));
                        });
                        w.stco(at, wide);
                        // a decoder needs the unit before any it starts at
                        w.full(b"sgpd", 1, 0, |w| {
                            w.bytes(b"roll");
                            w.u32(2);
                            w.u32(1);
                            w.u16(0xffff); // -1
                        });
                        w.full(b"sbgp", 0, 0, |w| {
                            w.bytes(b"roll");
                            w.u32(1);
                            w.u32(units);
                            w.u32(1);
                        });
                    });
                });
            });
        });
    }

    fn avc1(&self, w: &mut Boxes) {
        w.boxed(b"avc1", |w| {
            w.zeros(6);
            w.u16(1); // data reference
            w.zeros(16);
            w.u16(self.width as u16);
            w.u16(self.height as u16);
            w.u32(0x0048_0000);
            w.u32(0x0048_0000);
            w.u32(0);
            w.u16(1); // frames per sample
            let name = b"manimgx";
            w.u8(name.len() as u8);
            w.bytes(name);
            w.zeros(31 - name.len());
            w.u16(0x0018);
            w.u16(0xffff);
            w.boxed(b"avcC", |w| {
                let (sps, pps) = (&self.sps, &self.pps);
                w.u8(1);
                w.u8(sps[1]); // profile
                w.u8(sps[2]); // constraints
                w.u8(sps[3]); // level
                w.u8(0xff); // 4-byte NAL sizes
                w.u8(0xe1); // one SPS
                w.u16(sps.len() as u16);
                w.bytes(sps);
                w.u8(1); // one PPS
                w.u16(pps.len() as u16);
                w.bytes(pps);
                if matches!(sps[1], 100 | 110 | 122 | 144) {
                    w.u8(0xfd); // 4:2:0
                    w.u8(0xf8); // 8-bit luma
                    w.u8(0xf8); // 8-bit chroma
                    w.u8(0);
                }
            });
        });
    }
}

impl Drop for Mp4 {
    /// The samples' file is temporary: finished or not, it goes (closed first, so that it can).
    fn drop(&mut self) {
        self.data = None;
        let _ = std::fs::remove_file(&self.part);
    }
}

fn ftyp() -> Vec<u8> {
    let mut w = Boxes::default();
    w.boxed(b"ftyp", |w| {
        w.bytes(b"iso4"); // signed composition offsets (ctts version 1)
        w.u32(0x200);
        for brand in [b"iso4", b"isom", b"iso2", b"avc1", b"mp41"] {
            w.bytes(brand);
        }
    });
    w.0
}

#[derive(Default)]
struct Boxes(Vec<u8>);

impl Boxes {
    fn u8(&mut self, v: u8) {
        self.0.push(v);
    }
    fn u16(&mut self, v: u16) {
        self.0.extend_from_slice(&v.to_be_bytes());
    }
    fn u32(&mut self, v: u32) {
        self.0.extend_from_slice(&v.to_be_bytes());
    }
    fn u64(&mut self, v: u64) {
        self.0.extend_from_slice(&v.to_be_bytes());
    }
    fn bytes(&mut self, b: &[u8]) {
        self.0.extend_from_slice(b);
    }
    fn zeros(&mut self, n: usize) {
        self.0.resize(self.0.len() + n, 0);
    }
    fn matrix(&mut self) {
        for v in [0x0001_0000, 0, 0, 0, 0x0001_0000, 0, 0, 0, 0x4000_0000u32] {
            self.u32(v);
        }
    }
    fn dinf(&mut self) {
        self.boxed(b"dinf", |w| {
            w.full(b"dref", 0, 0, |w| {
                w.u32(1);
                w.full(b"url ", 0, 1, |_| {});
            })
        });
    }
    /// How many samples a track's chunks hold, run-length: (first chunk, samples each).
    fn stsc(&mut self, counts: &[u32]) {
        self.full(b"stsc", 0, 0, |w| {
            let runs: Vec<(u32, u32)> = (1..).zip(counts).filter(|&(k, &n)| k == 1 || counts[k as usize - 2] != n).map(|(k, &n)| (k, n)).collect();
            w.u32(runs.len() as u32);
            for (first, n) in runs {
                w.u32(first);
                w.u32(n);
                w.u32(1);
            }
        });
    }
    /// Where a track's chunks start in the file.
    fn stco(&mut self, at: &[u64], wide: bool) {
        if wide {
            self.full(b"co64", 0, 0, |w| {
                w.u32(at.len() as u32);
                at.iter().for_each(|&o| w.u64(o));
            });
        } else {
            self.full(b"stco", 0, 0, |w| {
                w.u32(at.len() as u32);
                at.iter().for_each(|&o| w.u32(o as u32));
            });
        }
    }
    /// Run-length (count, value) entries.
    fn runs(&mut self, values: &[u32]) {
        let mut runs: Vec<(u32, u32)> = Vec::new();
        for &v in values {
            match runs.last_mut() {
                Some((n, last)) if *last == v => *n += 1,
                _ => runs.push((1, v)),
            }
        }
        self.u32(runs.len() as u32);
        for (n, v) in runs {
            self.u32(n);
            self.u32(v);
        }
    }
    fn boxed(&mut self, kind: &[u8; 4], body: impl FnOnce(&mut Self)) {
        let at = self.0.len();
        self.u32(0);
        self.bytes(kind);
        body(self);
        let size = (self.0.len() - at) as u32;
        self.0[at..at + 4].copy_from_slice(&size.to_be_bytes());
    }
    fn full(&mut self, kind: &[u8; 4], version: u8, flags: u32, body: impl FnOnce(&mut Self)) {
        self.boxed(kind, |w| {
            w.u32((version as u32) << 24 | flags);
            body(w);
        });
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    fn movie(pictures: &[(i64, u32)]) -> Mp4 {
        Mp4 {
            path: String::new(), part: String::new(), data: None,
            width: 2, height: 2, fps: 1, sps: vec![0; 4], pps: vec![0], bytes: 0,
            samples: pictures.iter().map(|&(pts, duration)| Sample { size: 0, pts, duration, key: true }).collect(),
        }
    }

    #[test]
    fn progressive_chunks_deliver_references_before_their_earliest_picture() {
        // The P-picture shown at 10s is needed to decode the B-picture shown at 1s.
        // Its 20s hold must not put that B-picture behind 21s of audio.
        let movie = movie(&[(0, 1), (10, 20), (1, 9)]);
        let audio = Audio { rate: 1024, channels: 1, config: vec![], priming: 0, length: 30 * 1024, units: vec![vec![]; 30] };
        let chunks = movie.layout(Some(&audio));
        assert_eq!(&chunks[..4], &[(false, 0..1), (true, 0..1), (false, 1..3), (true, 1..2)]);
        assert!(chunks[4..].iter().all(|(sound, _)| *sound));
    }

    #[test]
    fn composition_offsets_cannot_wrap() {
        let movie = movie(&[(0, 1), (i32::MAX as i64 + 2, 1), (1, i32::MAX as u32 + 1)]);
        let error = movie.moov(i32::MAX as i64 + 3, None, &vec![(false, 0..3)], 0, false).unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::InvalidInput);
        assert!(error.to_string().contains("composition offset"));
    }
}
