//! ManimGX's engine: draws blends of shapes on the GPU (`render`) and typesets with Typst
//! (`typeset`).
//!
//! It is Python's extension module (`python`), which also reads sound (`audio`): natively with
//! the GPU, a film's video encoded by x264, its sound as AAC (`export`); in Pyodide without it,
//! a scene's frames recorded as a take (`take`: its arrays coded against the ones they
//! replace, `pack`). A take is played by the player (`player`: a projector of takes, `project`,
//! on a clock, with a face, `chrome`, and a sound, `speaker`), the same on two screens: a window
//! on this machine (`window`) and, the engine compiled to WebAssembly, a page's canvas (`web`).

#[cfg(feature = "export")]
mod aac;
#[cfg(feature = "python")]
mod audio;
#[cfg(feature = "player")]
mod chrome;
#[cfg(feature = "export")]
mod encode;
mod environment;
#[cfg(any(feature = "python", feature = "render", test))]
mod mesh;
#[cfg(feature = "export")]
mod export;
#[cfg(feature = "export")]
mod mp4;
mod pack;
#[cfg(feature = "player")]
mod player;
#[cfg(feature = "player")]
mod project;
#[cfg(feature = "python")]
mod python;
#[cfg(feature = "player")]
mod speaker;
#[cfg(feature = "render")]
mod render;
mod take;
#[cfg(feature = "player")]
mod text;
#[cfg(feature = "typeset")]
mod typeset;
#[cfg(feature = "web")]
mod web;
#[cfg(feature = "window")]
mod window;

/// The content key of some bytes, taken as one stream: xxh3, 64 bits, never 0 (reserved). What
/// names an upload, so that equal content is uploaded once.
pub fn digest<'a>(parts: impl IntoIterator<Item = &'a [u8]>) -> u64 {
    let mut hasher = xxhash_rust::xxh3::Xxh3::new();
    for part in parts {
        hasher.update(part);
    }
    hasher.digest().max(1)
}

/// A camera's view, drawn into a texture that later views sample by its key: (key, width,
/// height, view, records).
pub(crate) type CameraView = (u64, u32, u32, Vec<u8>, Vec<u8>);

pub(crate) fn check_key(key: u64) -> Result<(), String> {
    if key == 0 { Err("key 0 is reserved".into()) } else { Ok(()) }
}

/// Bytes as the items they hold (`what` names them in the error).
pub(crate) fn read<T: bytemuck::Pod>(bytes: &[u8], what: &str) -> Result<Vec<T>, String> {
    if !bytes.len().is_multiple_of(size_of::<T>()) {
        return Err(format!("{what}: {} bytes is not a whole number of items", bytes.len()));
    }
    Ok(bytemuck::pod_collect_to_vec(bytes))
}
