//! Sound out: a film's soundtrack encoded as AAC-LC (rusty_aac, pure Rust), for the MP4's sound
//! track. The encoder delays the sound by one frame of 1024 samples (its priming), which the MP4's
//! edit list skips.

use rusty_aac::encode::{AacEncoder, AacEncoderConfig, audio_specific_config_bytes};

use crate::mp4::Audio;

/// The samples an AAC-LC encoder puts before the sound: one frame.
const PRIMING: u32 = 1024;

/// Interleaved float samples of `channels` channels at `rate`, encoded at about `bitrate` bits a
/// second.
pub fn encode(pcm: &[f32], channels: usize, rate: u32, bitrate: u32) -> Result<Audio, String> {
    let mut encoder = AacEncoder::new(AacEncoderConfig { bitrate_bps: bitrate, ..Default::default() });
    encoder.push_pcm(pcm, channels as u16, rate).map_err(|e| e.to_string())?;
    encoder.finish();
    let mut units = Vec::new();
    while let Ok(packet) = encoder.next_packet() {
        units.push(packet.data);
    }
    let config = audio_specific_config_bytes(rate, channels as u16);
    Ok(Audio { rate, channels: channels as u16, config, priming: PRIMING, length: (pcm.len() / channels) as u64, units })
}
