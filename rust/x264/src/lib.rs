//! x264, the H.264 encoder, built from its source (fetched, see build.rs) and used through a C
//! shim (src/shim.c): NV12 pictures in; out, samples for an MP4, each a picture's NAL units
//! prefixed by their sizes, with the parameter sets apart.

use std::ffi::{CString, c_char, c_int, c_void};

unsafe extern "C" {
    fn manimgx_x264_open(
        out: *mut *mut c_void, width: c_int, height: c_int, fps: c_int, preset: *const c_char, crf: f32, count: c_int,
        names: *const *const c_char, values: *const *const c_char, sps: *mut *const u8, sps_size: *mut c_int,
        pps: *mut *const u8, pps_size: *mut c_int,
    ) -> c_int;
    fn manimgx_x264_encode(
        encoder: *mut c_void, nv12: *const u8, pts: i64, constant: *const u8, force_key: c_int, sample: *mut *const u8, size: *mut c_int,
        sample_pts: *mut i64, key: *mut c_int,
    ) -> c_int;
    fn manimgx_x264_delayed(encoder: *mut c_void) -> c_int;
    fn manimgx_x264_close(encoder: *mut c_void);
}

/// A picture as x264 wrote it: its NAL units, together one MP4 sample.
pub struct Sample<'a> {
    pub data: &'a [u8],
    pub pts: i64,
    pub key: bool,
}

/// An encoder of NV12 pictures, used by one thread at a time (x264 has no thread affinity).
pub struct Encoder {
    raw: *mut c_void,
    picture: usize,
    macroblocks: usize,
    /// The sequence parameter set, without its size prefix.
    pub sps: Vec<u8>,
    /// The picture parameter set, without its size prefix.
    pub pps: Vec<u8>,
}

unsafe impl Send for Encoder {}

impl Encoder {
    /// Pictures of `width` × `height` at `fps`, their times in frames, in BT.601 limited range
    /// over sRGB bytes: x264's `preset` and constant rate factor `crf`, then its own `options`
    /// (name, value), as `-x264-params` gives them.
    pub fn new(width: u32, height: u32, fps: u32, preset: &str, crf: f32, options: &[(String, String)]) -> Result<Self, String> {
        let text = |s: &str| CString::new(s).map_err(|e| e.to_string());
        let preset_c = text(preset)?;
        let names = options.iter().map(|(name, _)| text(name)).collect::<Result<Vec<_>, _>>()?;
        let values = options.iter().map(|(_, value)| text(value)).collect::<Result<Vec<_>, _>>()?;
        let (names_p, values_p): (Vec<_>, Vec<_>) = names.iter().zip(&values).map(|(n, v)| (n.as_ptr(), v.as_ptr())).unzip();
        let (mut raw, mut sps, mut pps, mut sps_size, mut pps_size) = (std::ptr::null_mut(), std::ptr::null(), std::ptr::null(), 0, 0);
        let status = unsafe {
            manimgx_x264_open(
                &mut raw, width as c_int, height as c_int, fps as c_int, preset_c.as_ptr(), crf, options.len() as c_int, names_p.as_ptr(),
                values_p.as_ptr(), &mut sps, &mut sps_size, &mut pps, &mut pps_size,
            )
        };
        match status {
            0 => {}
            1 => return Err(format!("unknown x264 preset {preset}")),
            k if k >= 2 => return Err(format!("x264 option {}={}", options[k as usize - 2].0, options[k as usize - 2].1)),
            _ => return Err("x264 could not open an encoder".into()),
        }
        let (sps, pps) = unsafe { (std::slice::from_raw_parts(sps, sps_size as usize).to_vec(), std::slice::from_raw_parts(pps, pps_size as usize).to_vec()) };
        let (width, height) = (width as usize, height as usize);
        Ok(Self { raw, picture: width * height * 3 / 2, macroblocks: width.div_ceil(16) * height.div_ceil(16), sps, pps })
    }

    /// Encode an NV12 picture shown from `pts` — or, with none, one that x264 held back (while
    /// [`delayed`](Self::delayed)). `constant`, a byte per macroblock, marks those unchanged since
    /// the previous picture: x264 skips them. `force_key` makes the picture a keyframe (an IDR
    /// picture, where a player can start). Returns the sample written, if any.
    pub fn encode(&mut self, nv12: Option<&[u8]>, pts: i64, constant: Option<&[u8]>, force_key: bool) -> Result<Option<Sample<'_>>, String> {
        assert!(nv12.is_none_or(|p| p.len() >= self.picture) && constant.is_none_or(|c| c.len() >= self.macroblocks));
        let (mut sample, mut size, mut sample_pts, mut key) = (std::ptr::null(), 0, 0, 0);
        let status = unsafe {
            manimgx_x264_encode(
                self.raw, nv12.map_or(std::ptr::null(), <[u8]>::as_ptr), pts, constant.map_or(std::ptr::null(), <[u8]>::as_ptr), force_key as c_int, &mut sample,
                &mut size, &mut sample_pts, &mut key,
            )
        };
        if status < 0 {
            return Err("x264 failed to encode a picture".into());
        }
        Ok((size > 0).then(|| Sample { data: unsafe { std::slice::from_raw_parts(sample, size as usize) }, pts: sample_pts, key: key != 0 }))
    }

    /// Whether x264 still holds pictures back.
    pub fn delayed(&self) -> bool {
        unsafe { manimgx_x264_delayed(self.raw) > 0 }
    }
}

impl Drop for Encoder {
    fn drop(&mut self) {
        unsafe { manimgx_x264_close(self.raw) }
    }
}
