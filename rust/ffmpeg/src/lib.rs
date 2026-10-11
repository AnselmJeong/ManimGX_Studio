//! FFmpeg's audio decoders (libopus's for Opus), built from their sources (see build.rs) and used
//! through a C shim (src/shim.c): a file's bytes in, its sound out.

use std::ffi::{CStr, c_char, c_int, c_void};
use std::sync::Mutex;

unsafe extern "C" {
    fn manimgx_decode(
        data: *const u8,
        size: usize,
        samples: *mut *mut f32,
        frames: *mut usize,
        rate: *mut c_int,
        channels: *mut c_int,
        error: *mut c_char,
        error_size: usize,
    ) -> c_int;
    fn manimgx_free(pointer: *mut c_void);
}

/// FFmpeg is built without threads: it decodes one file at a time.
static ONE_AT_A_TIME: Mutex<()> = Mutex::new(());

/// A file's sound (any container and codec FFmpeg is built with here): interleaved float samples,
/// their rate, and how many channels (1 or 2: wider sound is downmixed to stereo). It starts and
/// ends where the file declares (an MP4's edit list, the encoder's delay and padding).
pub fn decode(file: &[u8]) -> Result<(Vec<f32>, u32, usize), String> {
    let _lock = ONE_AT_A_TIME.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
    let (mut samples, mut frames, mut rate, mut channels) = (std::ptr::null_mut(), 0, 0, 0);
    let mut error = [0 as c_char; 256];
    let status = unsafe {
        manimgx_decode(file.as_ptr(), file.len(), &mut samples, &mut frames, &mut rate, &mut channels, error.as_mut_ptr(), error.len())
    };
    if status < 0 {
        return Err(unsafe { CStr::from_ptr(error.as_ptr()) }.to_string_lossy().into_owned());
    }
    // SAFETY: the shim filled `samples` with `frames` frames of `channels`, which it allocated
    let pcm = unsafe { std::slice::from_raw_parts(samples, frames * channels as usize) }.to_vec();
    unsafe { manimgx_free(samples.cast()) };
    Ok((pcm, rate as u32, channels as usize))
}
