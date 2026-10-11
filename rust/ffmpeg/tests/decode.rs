//! Execute the linked native decoder, including libopus. An rlib alone can hide unresolved C
//! symbols until Python imports the engine; these tests require a working executable first.

#[test]
fn pcm_wave_is_decoded_without_external_libraries() {
    let mut wav = Vec::from(&b"RIFF\x2c\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00data\x08\x00\x00\x00"[..]);
    for sample in [0_i16, 16384, -16384, 0] {
        wav.extend(sample.to_le_bytes());
    }
    let (samples, rate, channels) = ffmpeg::decode(&wav).unwrap();
    assert_eq!(rate, 48000);
    assert_eq!(channels, 1);
    assert_eq!(samples, [0.0, 0.5, -0.5, 0.0]);
}

#[test]
fn opus_silence() {
    // A 20 ms mono Opus packet (f8 ff fe), in three Ogg pages: OpusHead (no pre-skip),
    // OpusTags (empty), and the packet (final granule 960). No encoder or external tool needed.
    let (samples, rate, channels) = ffmpeg::decode(include_bytes!("silence.opus")).unwrap();
    assert_eq!((samples.len(), rate, channels), (960, 48_000, 1));
    assert!(
        samples
            .iter()
            .all(|sample| sample.is_finite() && sample.abs() < 1e-6)
    );
}

#[test]
fn rejects_invalid_audio() {
    for bytes in [b"".as_slice(), b"not an audio file"] {
        assert!(ffmpeg::decode(bytes).is_err());
    }
}
