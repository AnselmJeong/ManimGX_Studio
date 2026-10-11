//! x264 r3223 from its source (the GitHub mirror's archive of 0480cb05, fetched), with nothing installed:
//! the configuration its `configure` would write for the target, its C, and its assembly — on
//! x86-64 NASM's (the `nasm` crate: NASM from its source, in this script), on AArch64 the C
//! compiler's. Elsewhere, its C alone.

use std::path::{Path, PathBuf};

fn main() {
    nasm::serve();
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=src/shim.c");
    let source = &fetch::tree(
        "https://github.com/mirror/x264/archive/0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee.tar.gz",
        "f6be0c17bbcea2e79823e0dc953ad86f605deb41602d606108e1182a5118c434",
    );
    let out = PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    let target = |key: &str| std::env::var(format!("CARGO_CFG_TARGET_{key}")).unwrap_or_default();
    let (arch, os, msvc) = (target("ARCH"), target("OS"), target("ENV") == "msvc");
    let (x86, arm) = (arch == "x86_64", arch == "aarch64" && !msvc); // with assembly
    let (linux, windows) = (os == "linux", os == "windows");
    let stack = if x86 && !msvc { 64 } else { 16 };

    // config.h: what configure defines as 1 (x264 tests them with `#if`: the rest are 0)
    let mut defines = vec![
        "HAVE_BITDEPTH8 HAVE_GPL HAVE_INTERLACED HAVE_THREAD HAVE_LOG2F",
        if windows { "HAVE_WIN32THREAD SYS_WINDOWS" } else { "HAVE_POSIXTHREAD HAVE_STRTOK_R HAVE_CLOCK_GETTIME HAVE_SYSCONF HAVE_MMAP" },
    ];
    for (on, names) in [
        (!msvc, "HAVE_VECTOREXT"),
        (os == "macos", "SYS_MACOSX"),
        (linux, "SYS_LINUX HAVE_MALLOC_H HAVE_CPU_COUNT HAVE_GETAUXVAL"),
        (linux && x86, "HAVE_THP"),
        (x86, "ARCH_X86_64 HAVE_MMX"),
        (x86 && !msvc, "HAVE_X86_INLINE_ASM"),
        (x86 && msvc, "__SSE__"),
        (arch == "aarch64", "ARCH_AARCH64"),
        (arm, "HAVE_AARCH64 HAVE_NEON HAVE_DOTPROD HAVE_I8MM HAVE_SVE HAVE_SVE2 HAVE_AS_ARCHEXT_DOTPROD_DIRECTIVE"),
        (arm, "HAVE_AS_ARCHEXT_I8MM_DIRECTIVE HAVE_AS_ARCHEXT_SVE_DIRECTIVE HAVE_AS_ARCHEXT_SVE2_DIRECTIVE"),
    ] {
        if on {
            defines.push(names);
        }
    }
    let mut config: String = defines.iter().flat_map(|names| names.split_whitespace()).map(|name| format!("#define {name} 1\n")).collect();
    config += &format!("#define STACK_ALIGNMENT {stack}\n#define AS_ARCH_LEVEL armv8.2-a\n");
    std::fs::write(out.join("config.h"), config).unwrap();
    let version = "#define X264_VERSION \"\"\n#define X264_POINTVER \"0.165.3223 0480cb0\"\n";
    std::fs::write(out.join("x264_config.h"), format!("#define X264_GPL 1\n#define X264_INTERLACED 1\n#define X264_BIT_DEPTH 8\n#define X264_CHROMA_FORMAT 0\n{version}")).unwrap();

    // configure's compiler flags; the files x264's Makefile compiles once, then those it compiles
    // per bit depth (only 8)
    let build = || {
        let mut build = cc::Build::new();
        build.include(&out).include(source).warnings(false).opt_level(3);
        if msvc {
            build.flag("-fp:fast").flag("-GS-");
        } else {
            build.flag("-w").flag("-ffast-math").flag("-std=gnu99").define("_GNU_SOURCE", None).flag("-fomit-frame-pointer");
            build.flag_if_supported("-fno-tree-vectorize").flag("-fvisibility=hidden");
            if x86 {
                build.flag_if_supported("-mstack-alignment=64").flag_if_supported("-mpreferred-stack-boundary=6");
            }
        }
        build
    };
    let sources = |dir: &str, names: &str, ext: &str| names.split_whitespace().map(|name| source.join(format!("{dir}/{name}.{ext}"))).collect::<Vec<_>>();
    let mut once = build();
    once.files(sources("common", "osdep base cpu tables", "c")).files(sources("encoder", "api", "c")).file("src/shim.c");
    if windows {
        once.file(source.join("common/win32thread.c"));
    }
    let mut objects = once.compile_intermediates();
    let mut depth = build();
    depth.define("HIGH_BIT_DEPTH", "0").define("BIT_DEPTH", "8");
    depth.files(sources("common", "mc predict pixel macroblock frame dct cabac common rectangle set quant deblock vlc mvpred bitstream threadpool", "c"));
    depth.files(sources("encoder", "analyse me ratecontrol set macroblock cabac cavlc encoder lookahead", "c"));
    if x86 {
        depth.files(sources("common/x86", "mc-c predict-c", "c"));
    }
    if arm {
        depth.files(sources("common/aarch64", "asm-offsets mc-c predict-c", "c"));
        depth.files(sources("common/aarch64", "bitstream-a cabac-a dct-a deblock-a mc-a pixel-a predict-a quant-a", "S"));
        depth.files(sources("common/aarch64", "dct-a-sve deblock-a-sve mc-a-sve pixel-a-sve dct-a-sve2", "S"));
        depth.define("PIC", None);
        if os == "macos" {
            depth.define("PREFIX", None);
        }
    }
    objects.extend(depth.compile_intermediates());
    if x86 {
        objects.extend(assemble(source, &out, &os, stack));
    }
    cc::Build::new().objects(objects).compile("x264");
}

/// x264's x86-64 assembly, by NASM, in parallel: in a folder of their copies, so that NASM, which
/// reads its arguments in Windows' ANSI code page, is given ASCII only; with no timestamp in a
/// COFF object, so that a build is the same bytes whenever it is made.
fn assemble(source: &Path, out: &Path, os: &str, stack: u32) -> Vec<PathBuf> {
    let dir = out.join("x86");
    std::fs::create_dir_all(&dir).unwrap();
    for entry in std::fs::read_dir(source.join("common/x86")).unwrap() {
        let path = entry.unwrap().path();
        if path.extension().is_some_and(|ext| ext == "asm") {
            std::fs::copy(&path, dir.join(path.file_name().unwrap())).unwrap();
        }
    }
    let format = match os {
        "macos" => "-fmacho64",
        "windows" => "-fwin64",
        _ => "-felf64",
    };
    // cpu-a is compiled once, the rest per bit depth
    let files = "cpu-a bitstream-a const-a cabac-a dct-a deblock-a mc-a mc-a2 pixel-a predict-a quant-a dct-64 trellis-64 sad-a";
    std::thread::scope(|scope| {
        let jobs: Vec<_> = files
            .split_whitespace()
            .map(|name| {
                let dir = &dir;
                scope.spawn(move || {
                    let mut nasm = nasm::command();
                    nasm.current_dir(dir).args(["--reproducible", "-I./", format, "-DARCH_X86_64=1", &format!("-DSTACK_ALIGNMENT={stack}")]);
                    if os == "macos" {
                        nasm.arg("-DPREFIX");
                    }
                    if os != "windows" {
                        nasm.arg("-DPIC");
                    }
                    if name != "cpu-a" {
                        nasm.args(["-DBIT_DEPTH=8", "-Dprivate_prefix=x264_8"]);
                    }
                    let status = nasm.args(["-o", &format!("{name}.o"), &format!("{name}.asm")]).status().expect("NASM");
                    assert!(status.success(), "NASM failed on {name}.asm");
                    dir.join(format!("{name}.o"))
                })
            })
            .collect();
        jobs.into_iter().map(|job| job.join().unwrap()).collect()
    })
}
