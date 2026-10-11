//! The Python extension's build. Pyodide's (the browser's wheel) carries the player for a page —
//! this crate for wasm32-unknown-unknown with its `web` feature, the same player as a window's,
//! drawing with WebGPU — built beside it (`_engine.web()`), which ManimGX's element in the browser
//! plays films with. x264 is built by its own crate (`../x264`).

#[cfg(feature = "python")]
use std::path::{Path, PathBuf};

fn main() {
    #[cfg(feature = "render")]
    dxc::prepare();
    println!("cargo::rustc-check-cfg=cfg(web_player)");
    #[cfg(feature = "python")]
    web_player();
}

/// The player for a page, as the browser loads it: `engine.js` and `engine_bg.wasm`
/// (wasm-bindgen's JS and module), built for Pyodide's extension by a cargo of its own (a target
/// directory of its own, in the workspace's) whenever this crate's sources change, into OUT_DIR,
/// where the extension takes them in (`cfg(web_player)`). Without the wasm32-unknown-unknown
/// target, a warning: the extension builds without it, and the page says what it misses. A native
/// extension carries none: its films are played in a window (`window`).
#[cfg(feature = "python")]
fn web_player() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("emscripten") {
        return;
    }
    let crate_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    println!("cargo:rerun-if-changed={}", crate_dir.join("src").display());
    // the workspace's target directory: its root is this crate's parent (rust/), in a clone and in
    // the source distribution alike
    let target = std::env::var_os("CARGO_TARGET_DIR")
        .map_or_else(|| crate_dir.join("../target"), PathBuf::from)
        .join("web-player");
    let built = std::process::Command::new(std::env::var("CARGO").unwrap())
        .args(["build", "--locked", "--lib", "--release", "--target", "wasm32-unknown-unknown", "--no-default-features", "--features", "web"])
        .arg("--target-dir")
        .arg(&target)
        .current_dir(&crate_dir)
        // this build's own flags are for the extension's target (Pyodide's link arguments)
        .env_remove("RUSTFLAGS")
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("CARGO_BUILD_TARGET")
        .status();
    let module = target.join("wasm32-unknown-unknown/release/_engine.wasm");
    if !built.is_ok_and(|s| s.success()) || !module.exists() {
        println!("cargo:warning=the player for a page (ManimGX in the browser) was not built: `rustup target add wasm32-unknown-unknown`");
        return;
    }
    match bindgen(&module, Path::new(&std::env::var("OUT_DIR").unwrap())) {
        Ok(()) => println!("cargo:rustc-cfg=web_player"),
        Err(error) => println!("cargo:warning=the player's JS was not made: {error}"),
    }
}

#[cfg(feature = "python")]
fn bindgen(module: &Path, out: &Path) -> Result<(), String> {
    wasm_bindgen_cli_support::Bindgen::new()
        .input_path(module)
        .out_name("engine")
        .web(true)
        .map_err(|e| e.to_string())?
        .typescript(false)
        .omit_default_module_path(true)
        .remove_name_section(true)
        .remove_producers_section(true)
        .generate(out)
        .map_err(|e| e.to_string())
}
