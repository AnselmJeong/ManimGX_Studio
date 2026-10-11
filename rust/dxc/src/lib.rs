//! Windows' shader compiler is part of the engine's distribution, not a capability inferred
//! from PATH. DXC is Microsoft's maintained compiler; FXC cannot compile our valid WGSL loops.
//! The official release archive is pinned by bytes, and its corresponding source by its files.

use std::{fs, path::Path};

const BINARY_URL: &str = "https://github.com/microsoft/DirectXShaderCompiler/releases/download/v1.9.2609/dxc_2026_09_29.zip";
const BINARY_HASH: &str = "ad31b1fc8443175d204f77a611fdb3ef2ec42759bdc2f1167368de24a4a7e7f1";
const SOURCE_URL: &str = "https://github.com/microsoft/DirectXShaderCompiler/archive/01b62ad47db7dee3dd33f90e7339cf9e860b3f93.tar.gz";
const SOURCE_HASH: &str = "2d6e2bfe4265ba123b4a3d4d0a4c245e32971e66ba06c2d3ccc30337199ef5ff";
// GitHub's source archive omits these three gitlinks. DXC's SPIR-V backend uses them;
// collect their exact revisions too, so its compiler can be rebuilt from the source bundle.
const SUBMODULES: &[(&str, &str)] = &[
    ("https://github.com/microsoft/DirectX-Headers/archive/980971e835876dc0cde415e8f9bc646e64667bf7.tar.gz", "44fda0c5e670cea86f6b890d7c4252c0c7b0b04cc5c8e292bb39b0d6ea00512d"),
    ("https://github.com/KhronosGroup/SPIRV-Headers/archive/496543121ce6419f23d6fa5d7194ba66c36212d2.tar.gz", "5db9005d02b280ffb4c4605feb1e4e122dbdfeac673544d1bc26516f1f073c20"),
    ("https://github.com/KhronosGroup/SPIRV-Tools/archive/ef96ed763b43b59b33b31b362f09a02b729fa1c9.tar.gz", "a2e2378712cd1a21fdbfc24c7fc8533df44b33ca0a051e258e2f3ddf3a7b2ee5"),
];

/// Stage DXC in the engine's OUT_DIR for maturin. A complete-source build on any platform
/// collects both the distributable and its matching source; ordinary non-Windows builds do no
/// DXC work. Only dxcompiler.dll is needed: since DXC 1.8.2502, dxil.dll is optional.
pub fn prepare() {
    println!("cargo:rerun-if-env-changed=MANIMGX_SOURCES");
    let windows = std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows");
    let collecting = std::env::var_os("MANIMGX_SOURCES").is_some();
    if !windows && !collecting { return; }
    let archive = fetch::file(BINARY_URL, BINARY_HASH);
    if collecting {
        fetch::tree(SOURCE_URL, SOURCE_HASH);
        for (url, hash) in SUBMODULES { fetch::tree(url, hash); }
    }
    if windows {
        let out = std::env::var_os("OUT_DIR").expect("a build script's OUT_DIR");
        let arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
        extract(&archive, Path::new(&out), &arch).unwrap_or_else(|error| panic!("the bundled DXC: {error}"));
    }
}

fn extract(archive: &Path, out: &Path, arch: &str) -> Result<(), Box<dyn std::error::Error>> {
    let folder = match arch {
        "x86_64" => "x64",
        "aarch64" => "arm64",
        _ => return Err(format!("DXC has no bundled compiler for {arch}").into()),
    };
    let mut zip = zip::ZipArchive::new(fs::File::open(archive)?)?;
    let mut dll = zip.by_name(&format!("bin\\{folder}\\dxcompiler.dll"))?;
    std::io::copy(&mut dll, &mut fs::File::create(out.join("dxcompiler.dll"))?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn only_the_target_compiler_is_staged() {
        let work = tempfile::tempdir().unwrap();
        let archive = work.path().join("compiler.zip");
        let mut zip = zip::ZipWriter::new(fs::File::create(&archive).unwrap());
        for (name, bytes) in [("bin\\x64\\dxcompiler.dll", "x64"), ("bin\\arm64\\dxcompiler.dll", "arm64"), ("bin\\x64\\dxil.dll", "optional validator")] {
            zip.start_file(name, zip::write::SimpleFileOptions::default()).unwrap();
            zip.write_all(bytes.as_bytes()).unwrap();
        }
        zip.finish().unwrap();
        for (arch, bytes) in [("x86_64", "x64"), ("aarch64", "arm64")] {
            let out = work.path().join(arch);
            fs::create_dir(&out).unwrap();
            extract(&archive, &out, arch).unwrap();
            assert_eq!(fs::read_to_string(out.join("dxcompiler.dll")).unwrap(), bytes);
            assert_eq!(fs::read_dir(out).unwrap().count(), 1);
        }
        assert!(extract(&archive, work.path(), "unknown").unwrap_err().to_string().contains("unknown"));
    }
}
