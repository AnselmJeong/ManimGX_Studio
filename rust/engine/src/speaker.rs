//! The player's sound: the shown take's soundtrack (a WAV, see `take`), played on its screen's
//! speakers and following the player's clock (see `player`): on and on while the clock runs, and
//! again from where it is after the clock jumps (a seek, a new rate) or once the two drift `SLACK`
//! apart. In a window, on this machine's audio output (on Linux, where that would link ALSA, the
//! window is silent); in a page, through Web Audio, which sounds once the page has been clicked or
//! typed in (`resume`).

use crate::player::Clock;

/// Seconds the sound may drift from the clock before it starts again where the clock is (the
/// audio device's crystal and the system's clock part by tens of millionths: minutes apart).
#[cfg(any(target_arch = "wasm32", all(feature = "window", not(target_os = "linux"))))]
const SLACK: f64 = 0.03;

/// The player's sound: its volume, and the speaker playing the shown take's soundtrack, opened
/// once a take has one.
pub(crate) struct Sound {
    pub(crate) volume: f32,
    pub(crate) muted: bool,
    jumped: bool,      // the clock jumped since the speaker last followed it
    take: Option<u32>, // the take whose sound the speaker has
    speaker: Option<Speaker>,
}

impl Sound {
    pub(crate) fn new() -> Self {
        Self { volume: 1.0, muted: false, jumped: true, take: None, speaker: None }
    }

    /// The clock jumped: the sound starts again where it is.
    pub(crate) fn jumped(&mut self) {
        self.jumped = true;
    }

    /// The viewer did something (a key, a click, a tap): a page may sound from now on.
    pub(crate) fn resume(&self) {
        #[cfg(target_arch = "wasm32")]
        web::resume();
    }

    /// Play take `take`'s soundtrack (none: silence) by `clock`, silent while the film `waits`
    /// for frames.
    pub(crate) fn follow(&mut self, take: Option<u32>, sound: Option<&[u8]>, clock: Clock, waits: bool) {
        let take = take.filter(|_| sound.is_some());
        if self.take != take {
            if self.speaker.is_none() && sound.is_some() {
                self.speaker = Speaker::new();
            }
            if let Some(speaker) = &mut self.speaker {
                speaker.load(sound);
            }
            self.jumped = true;
        }
        if let Some(speaker) = &mut self.speaker {
            let volume = if self.muted || waits { 0.0 } else { self.volume };
            speaker.follow(clock, volume, self.jumped);
        }
        (self.take, self.jumped) = (take, false);
    }
}

/// A WAV file's sound, as a take carries it (16-bit PCM): its samples (interleaved, as floats),
/// its rate and its channels. (A page has the browser read it.)
#[cfg(not(target_arch = "wasm32"))]
#[cfg_attr(not(all(feature = "window", not(target_os = "linux"))), allow(dead_code))]
fn wav(file: &[u8]) -> Option<(Vec<f32>, u32, usize)> {
    let u16_at = |b: &[u8], at: usize| Some(u16::from_le_bytes(b.get(at..at.checked_add(2)?)?.try_into().ok()?));
    let u32_at = |b: &[u8], at: usize| Some(u32::from_le_bytes(b.get(at..at.checked_add(4)?)?.try_into().ok()?));
    if file.get(..4)? != b"RIFF" || file.get(8..12)? != b"WAVE" {
        return None;
    }
    let (mut at, mut format) = (12usize, None);
    while at.checked_add(8).is_some_and(|end| end <= file.len()) {
        let size = u32_at(file, at + 4)? as usize;
        let body = &file[at + 8..(at + 8).saturating_add(size).min(file.len())];
        match &file[at..at + 4] {
            b"fmt " => format = Some((u16_at(body, 0)?, usize::from(u16_at(body, 2)?), u32_at(body, 4)?, u16_at(body, 14)?)),
            b"data" => {
                let (kind, channels, rate, bits) = format?;
                if kind != 1 || bits != 16 || channels == 0 {
                    return None;
                }
                let samples = body.chunks_exact(2).map(|s| f32::from(i16::from_le_bytes([s[0], s[1]])) / 32768.0).collect();
                return Some((samples, rate, channels));
            }
            _ => {}
        }
        // the next chunk (a chunk's size is even, a pad byte after an odd one)
        at = at.checked_add(8)?.checked_add(size)?.checked_add(size & 1)?;
    }
    None
}

#[cfg(all(feature = "window", not(any(target_os = "linux", target_arch = "wasm32"))))]
use native::Speaker;
#[cfg(not(any(target_arch = "wasm32", all(feature = "window", not(target_os = "linux")))))]
use silent::Speaker;
#[cfg(target_arch = "wasm32")]
use web::Speaker;

/// No speaker: a window on Linux is silent (the system's audio would be linked: ALSA).
#[cfg(not(any(target_arch = "wasm32", all(feature = "window", not(target_os = "linux")))))]
mod silent {
    use crate::player::Clock;

    pub(super) enum Speaker {}

    impl Speaker {
        pub(super) fn new() -> Option<Self> {
            None
        }
        pub(super) fn load(&mut self, _: Option<&[u8]>) {}
        pub(super) fn follow(&mut self, _: Clock, _: f32, _: bool) {}
    }
}

/// The system's default audio output, playing a soundtrack by the clock: its thread fills the
/// device's buffer with the samples for the instant they will be heard.
#[cfg(all(feature = "window", not(any(target_os = "linux", target_arch = "wasm32"))))]
mod native {
    use std::sync::{Arc, Mutex};
    use std::time::Instant;

    use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};

    use super::SLACK;
    use crate::player::Clock;

    /// What the device's thread plays: the soundtrack (interleaved, at the device's rate and
    /// channels), and where in it, following the clock.
    struct Track {
        samples: Vec<f32>,
        clock: Clock,
        volume: f32,
        position: Option<f64>, // in frames of the soundtrack; None: where the clock is, next
        loads: u64,            // soundtracks asked for: only the newest is played
    }

    pub(super) struct Speaker {
        _stream: cpal::Stream,
        track: Arc<Mutex<Track>>,
        rate: u32,
        channels: usize,
    }

    impl Speaker {
        /// The default output, playing silence until it is given a soundtrack; None if there is
        /// none (or none that takes float samples).
        pub(super) fn new() -> Option<Self> {
            let device = cpal::default_host().default_output_device()?;
            let supported = device.default_output_config().ok()?;
            if supported.sample_format() != cpal::SampleFormat::F32 {
                return None;
            }
            let config: cpal::StreamConfig = supported.into();
            let (rate, channels) = (config.sample_rate, usize::from(config.channels));
            let track = Arc::new(Mutex::new(Track { samples: Vec::new(), clock: Clock { time: 0.0, since: None, rate: 1.0 }, volume: 1.0, position: None, loads: 0 }));
            let playing = track.clone();
            let stream = device
                .build_output_stream::<f32, _, _>(
                    config,
                    move |out, info| {
                        let Ok(mut track) = playing.lock() else { return out.fill(0.0) };
                        // these samples are heard this much later
                        let stamp = info.timestamp();
                        let heard = Instant::now() + stamp.playback.duration_since(stamp.callback);
                        fill(&mut track, out, channels, f64::from(rate), heard);
                    },
                    |_| {},
                    None,
                )
                .ok()?;
            stream.play().ok()?;
            Some(Self { _stream: stream, track, rate, channels })
        }

        /// Play `file` (a WAV), or nothing: silence until it is read and resampled, on a thread
        /// of its own (a long one takes a while; the player draws on).
        pub(super) fn load(&mut self, file: Option<&[u8]>) {
            let Ok(mut track) = self.track.lock() else { return };
            track.loads += 1;
            (track.samples, track.position) = (Vec::new(), None);
            let Some(file) = file.map(<[u8]>::to_vec) else { return };
            let (load, playing, rate, out) = (track.loads, self.track.clone(), self.rate, self.channels);
            std::thread::spawn(move || {
                let Some((samples, from, channels)) = super::wav(&file) else { return };
                let Ok(resampled) = crate::audio::resample(&samples, channels, f64::from(from), f64::from(rate)) else { return };
                // its channels onto the device's: one to all, or each to its own (wrapping)
                let frames = resampled.len() / channels;
                let samples = (0..frames * out).map(|k| resampled[k / out * channels + k % out % channels]).collect();
                if let Ok(mut track) = playing.lock()
                    && track.loads == load
                {
                    (track.samples, track.position) = (samples, None);
                }
            });
        }

        /// Follow `clock` at `volume`; `jumped`: from where the clock is.
        pub(super) fn follow(&mut self, clock: Clock, volume: f32, jumped: bool) {
            if let Ok(mut track) = self.track.lock() {
                if jumped || track.clock.since.is_some() != clock.since.is_some() || track.clock.rate != clock.rate {
                    track.position = None;
                }
                (track.clock, track.volume) = (clock, volume);
            }
        }
    }

    /// The device's next samples: the soundtrack from where it is (linearly between its samples
    /// at a rate other than 1) at its volume, or silence while the clock is held, or past its end.
    fn fill(track: &mut Track, out: &mut [f32], channels: usize, rate: f64, heard: Instant) {
        let clock = track.clock;
        let wanted = clock.at(heard) * rate;
        let start = match track.position {
            Some(at) if (at - wanted).abs() <= SLACK * rate => at,
            _ => wanted,
        };
        let frames = track.samples.len() / channels;
        if clock.since.is_none() || track.volume == 0.0 || frames == 0 {
            out.fill(0.0);
            track.position = Some(wanted);
            return;
        }
        let mut position = start;
        for frame in out.chunks_exact_mut(channels) {
            let (i, f) = (position.floor(), (position - position.floor()) as f32);
            for (c, sample) in frame.iter_mut().enumerate() {
                let get = |k: f64| if k >= 0.0 && (k as usize) < frames { track.samples[k as usize * channels + c] } else { 0.0 };
                *sample = track.volume * (get(i) * (1.0 - f) + get(i + 1.0) * f);
            }
            position += clock.rate;
        }
        track.position = Some(position);
    }
}

/// The page's sound: the soundtrack in an AudioBuffer (read by the browser, off the page's
/// thread), played from where the clock is by a source started at a moment of the audio
/// context's own clock, which the browser keeps exactly (a source plays on the audio thread,
/// whatever the page's thread is doing). The context's output timestamp ties its clock to the
/// page's: what it plays at a time is heard at an instant.
#[cfg(target_arch = "wasm32")]
mod web {
    use std::cell::{Cell, RefCell};
    use std::rc::Rc;

    use wasm_bindgen::prelude::*;
    use wasm_bindgen_futures::JsFuture;
    use web_sys::{AudioBuffer, AudioBufferSourceNode, AudioContext, AudioContextState, GainNode};
    use web_time::{Duration, Instant};

    use super::SLACK;
    use crate::player::Clock;

    /// Seconds an output timestamp may be old: older, the context's device stalls (the machine
    /// slept), and nothing is scheduled by it until it plays again.
    const STALE: f64 = 0.2;

    #[wasm_bindgen]
    extern "C" {
        /// An audio context, as its output timestamp (not in web-sys).
        type Stamped;
        #[wasm_bindgen(method, js_name = getOutputTimestamp)]
        fn output_timestamp(this: &Stamped) -> Stamp;
        /// The context's time being heard, and the page's (`performance.now`) when it is.
        type Stamp;
        #[wasm_bindgen(method, getter, js_name = contextTime)]
        fn context_time(this: &Stamp) -> f64;
        #[wasm_bindgen(method, getter, js_name = performanceTime)]
        fn performance_time(this: &Stamp) -> f64;
        #[wasm_bindgen(js_namespace = performance, js_name = now)]
        fn performance_now() -> f64;
    }

    thread_local! {
        // the page's one audio context, every player's sound through it
        static CONTEXT: RefCell<Option<AudioContext>> = const { RefCell::new(None) };
    }

    /// The page's audio context, made when it is first wanted.
    fn context() -> Option<AudioContext> {
        CONTEXT.with_borrow_mut(|context| {
            if context.is_none() {
                *context = AudioContext::new().ok();
            }
            context.clone()
        })
    }

    /// The viewer did something: the page's context is made, if it was not, and plays. A
    /// browser lets a page sound from within such a gesture on.
    pub(super) fn resume() {
        if let Some(context) = context().filter(|c| c.state() != AudioContextState::Running) {
            let _ = context.resume();
        }
    }

    /// A source playing: from `offset` seconds of the soundtrack at the context's time `when`, at
    /// `rate`.
    struct Playing {
        source: AudioBufferSourceNode,
        when: f64,
        offset: f64,
        rate: f64,
    }

    pub(super) struct Speaker {
        context: AudioContext,
        gain: GainNode,
        buffer: Rc<RefCell<Option<AudioBuffer>>>, // the soundtrack, once the browser has read it
        loads: Rc<Cell<u64>>,                     // soundtracks asked for: only the newest is kept
        playing: Option<Playing>,
    }

    impl Speaker {
        pub(super) fn new() -> Option<Self> {
            let context = context()?;
            let gain = context.create_gain().ok()?;
            gain.connect_with_audio_node(&context.destination()).ok()?;
            Some(Self { context, gain, buffer: Rc::default(), loads: Rc::default(), playing: None })
        }

        /// Play `file` (an audio file), or nothing: silence until the browser has read it.
        pub(super) fn load(&mut self, file: Option<&[u8]>) {
            self.stop();
            self.loads.set(self.loads.get() + 1);
            self.buffer.replace(None);
            let Some(file) = file else { return };
            let Ok(read) = self.context.decode_audio_data(&js_sys::Uint8Array::from(file).buffer()) else { return };
            let (load, loads, buffer) = (self.loads.get(), self.loads.clone(), self.buffer.clone());
            wasm_bindgen_futures::spawn_local(async move {
                if let Ok(read) = JsFuture::from(read).await
                    && loads.get() == load
                {
                    buffer.replace(Some(read.unchecked_into()));
                }
            });
        }

        fn stop(&mut self) {
            if let Some(playing) = self.playing.take() {
                let _ = web_sys::AudioScheduledSourceNode::stop(&playing.source);
                let _ = playing.source.disconnect();
            }
        }

        pub(super) fn follow(&mut self, clock: Clock, volume: f32, jumped: bool) {
            self.gain.gain().set_value(volume);
            let Some(buffer) = self.buffer.borrow().clone() else { return };
            // the context's time heard now: none until its output has begun, while it is held
            // (until the page is clicked or typed in), and while its device stalls
            let stamp = self.context.unchecked_ref::<Stamped>().output_timestamp();
            let (heard, at, now) = (stamp.context_time(), stamp.performance_time(), performance_now());
            let running = self.context.state() == AudioContextState::Running && heard > 0.0 && now - at < STALE * 1000.0;
            if clock.since.is_none() || volume == 0.0 || !running {
                return self.stop();
            }
            let heard = heard + (now - at) / 1000.0;
            // what is heard now against what the clock says
            let off = self.playing.as_ref().is_none_or(|p| jumped || p.rate != clock.rate || (p.offset + (heard - p.when) * p.rate - clock.at(Instant::now())).abs() > SLACK);
            if !off {
                return;
            }
            self.stop();
            // from where the clock will be when it is heard: a moment after the context's time
            // now, which is heard later by the context's latency
            let mut when = self.context.current_time() + 0.01;
            let mut offset = clock.at(Instant::now() + Duration::from_secs_f64((when - heard).max(0.0)));
            if offset < 0.0 {
                when -= offset / clock.rate;
                offset = 0.0;
            }
            if offset >= buffer.duration() {
                return;
            }
            let Ok(source) = self.context.create_buffer_source() else { return };
            source.set_buffer(Some(&buffer));
            source.playback_rate().set_value(clock.rate as f32);
            if source.connect_with_audio_node(&self.gain).is_ok() && source.start_with_when_and_grain_offset(when, offset).is_ok() {
                self.playing = Some(Playing { source, when, offset, rate: clock.rate });
            }
        }
    }

    impl Drop for Speaker {
        fn drop(&mut self) {
            self.load(None); // stop playback, invalidate pending decodes, release the buffer
            let _ = self.gain.disconnect();
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use wasm_bindgen_test::*;

        wasm_bindgen_test_configure!(run_in_browser);

        // Observe calls on real browser audio nodes; their actual methods still execute.
        #[wasm_bindgen(inline_js = r#"
export function observeAudio(context, gain, source) {
    const counts = [0, 0, 0];
    const stop = source.stop, disconnect = source.disconnect, detach = gain.disconnect;
    const decode = context.decodeAudioData;
    let decoded;
    source.stop = function (...args) { counts[0]++; return stop.apply(this, args); };
    source.disconnect = function (...args) { counts[1]++; return disconnect.apply(this, args); };
    gain.disconnect = function (...args) { counts[2]++; return detach.apply(this, args); };
    context.decodeAudioData = function (bytes) { decoded = decode.call(this, bytes); return decoded; };
    return { counts, decoded: () => decoded, restore: () => { context.decodeAudioData = decode; } };
}
export function audioDecoded(probe) { return probe.decoded(); }
export function finishAudioProbe(probe) { probe.restore(); return probe.counts; }
"#)]
        extern "C" {
            #[wasm_bindgen(js_name = observeAudio)]
            fn observe_audio(context: &AudioContext, gain: &GainNode, source: &AudioBufferSourceNode) -> JsValue;
            #[wasm_bindgen(js_name = audioDecoded)]
            fn audio_decoded(probe: &JsValue) -> js_sys::Promise;
            #[wasm_bindgen(js_name = finishAudioProbe)]
            fn finish_audio_probe(probe: &JsValue) -> js_sys::Array;
        }

        #[wasm_bindgen_test]
        async fn destruction_stops_owned_audio_and_invalidates_pending_decode() {
            let mut speaker = Speaker::new().expect("browser AudioContext");
            let context = speaker.context.clone();
            let source = context.create_buffer_source().unwrap();
            let playing_buffer = context.create_buffer(1, 48000, 48000.0).unwrap();
            source.set_buffer(Some(&playing_buffer));
            speaker.buffer.replace(Some(playing_buffer));
            source.connect_with_audio_node(&speaker.gain).unwrap();
            source.start_with_when(context.current_time() + 60.0).unwrap();
            let probe = observe_audio(&context, &speaker.gain, &source);

            // A valid PCM file, decoded by the real browser. The promise cannot complete
            // before this synchronous owner is destroyed and JavaScript gets control back.
            let mut wav = b"RIFF".to_vec();
            wav.extend(38u32.to_le_bytes());
            wav.extend(b"WAVEfmt ");
            wav.extend(16u32.to_le_bytes());
            wav.extend([1u16, 1].iter().flat_map(|v| v.to_le_bytes()));
            wav.extend([48000u32, 96000].iter().flat_map(|v| v.to_le_bytes()));
            wav.extend([2u16, 16].iter().flat_map(|v| v.to_le_bytes()));
            wav.extend(b"data");
            wav.extend(2u32.to_le_bytes());
            wav.extend([0, 0]);
            let mut decoding = Speaker::new().unwrap();
            decoding.load(Some(&wav));
            speaker.playing = Some(Playing { source, when: 0.0, offset: 0.0, rate: 1.0 });
            let (playing_buffer, pending_buffer) = (speaker.buffer.clone(), decoding.buffer.clone());
            let pending = audio_decoded(&probe);
            drop(speaker);
            drop(decoding);
            JsFuture::from(pending).await.unwrap();
            JsFuture::from(js_sys::Promise::resolve(&JsValue::UNDEFINED)).await.unwrap();
            let counts = finish_audio_probe(&probe);
            assert_eq!(counts.iter().map(|n| n.as_f64().unwrap()).collect::<Vec<_>>(), [1.0, 1.0, 1.0]);
            assert!(playing_buffer.borrow().is_none(), "the finished owner releases its decoded buffer");
            assert!(pending_buffer.borrow().is_none(), "a detached owner's pending decode must not be published");
            assert_ne!(context.state(), AudioContextState::Closed);
            let next = Speaker::new().unwrap();
            assert_eq!(next.context, context, "another player keeps the shared page context");
        }
    }
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    #[test]
    fn a_takes_sound_is_read_as_written() {
        // a WAV as Python's `wave` writes a take's: 16-bit, two channels, 48 kHz
        let samples: [i16; 6] = [0, 32767, -32768, 16384, -1, 1];
        let data: Vec<u8> = samples.iter().flat_map(|s| s.to_le_bytes()).collect();
        let mut file = b"RIFF".to_vec();
        file.extend((36 + data.len() as u32).to_le_bytes());
        file.extend(b"WAVEfmt ");
        file.extend(16u32.to_le_bytes());
        file.extend([1u16, 2].iter().flat_map(|v| v.to_le_bytes()));
        file.extend([48000u32, 48000 * 4].iter().flat_map(|v| v.to_le_bytes()));
        file.extend([4u16, 16].iter().flat_map(|v| v.to_le_bytes()));
        file.extend(b"data");
        file.extend((data.len() as u32).to_le_bytes());
        file.extend(&data);
        let (read, rate, channels) = super::wav(&file).expect("a WAV");
        assert_eq!((rate, channels), (48000, 2));
        assert_eq!(read, samples.map(|s| f32::from(s) / 32768.0));
        // not a WAV of 16-bit PCM: no sound
        assert!(super::wav(b"RIFF\0\0\0\0WAVE").is_none());
        assert!(super::wav(b"OggS").is_none());
        // a chunk as long as can be: past the end, not around
        let mut endless = b"RIFF\0\0\0\0WAVEjunk".to_vec();
        endless.extend(u32::MAX.to_le_bytes());
        assert!(super::wav(&endless).is_none());
    }
}
