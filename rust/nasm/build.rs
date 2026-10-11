//! NASM 3.02 from its source (nasm.us's release, fetched), as a library whose `main` is
//! `nasm_main`. MSVC reads NASM's own configuration of it (config/msvc.h); other compilers, what
//! NASM's configure finds on every C99 and POSIX system, and the C library's own functions
//! (Apple's, glibc's and musl's).

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    let source = &fetch::tree(
        "https://www.nasm.us/pub/nasm/releasebuilds/3.02/nasm-3.02.tar.gz",
        "f888713323995fa84af4a5276c01fb54f18cc149c08ac938adb48391de6d7ca0",
    );
    let mut build = cc::Build::new();
    for dir in [".", "include", "x86", "asm", "output", "zlib"] {
        build.include(source.join(dir));
    }
    build.files(SOURCES.split_whitespace().map(|f| source.join(format!("{f}.c"))));
    build.define("main", "nasm_main").warnings(false).opt_level(2);
    let target = |key: &str| std::env::var(format!("CARGO_CFG_TARGET_{key}")).unwrap_or_default();
    if build.get_compiler().is_like_msvc() {
        // as Mkfiles/msvc.mak, and the architecture <windows.h> would define before the SDK's
        // headers, which nasmlib/file.c includes alone
        let arch = match target("ARCH").as_str() {
            "aarch64" => "_ARM64_",
            "x86" => "_X86_",
            _ => "_AMD64_",
        };
        build.std("c11").flag("-bigobj").define(arch, None);
    } else {
        let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
        let mut have = vec![HAVE];
        if target("VENDOR") == "apple" {
            have.push("STRLCPY DECL_STRLCPY");
        }
        if target("OS") == "linux" {
            have.push("ENDIAN_H HTOLE16 HTOLE32 HTOLE64 MEMPCPY"); // glibc's and musl's
        }
        // configure's system extensions (AC_USE_SYSTEM_EXTENSIONS), then what it found
        let mut config = String::from("#define _GNU_SOURCE 1\n#define _DARWIN_C_SOURCE 1\n");
        config += &have.iter().flat_map(|names| names.split_whitespace()).map(|name| format!("#define HAVE_{name} 1\n")).collect::<String>();
        config += "#include \"config/unconfig.h\"\n";
        std::fs::create_dir_all(out.join("config")).unwrap();
        std::fs::write(out.join("config/config.h"), config).unwrap();
        build.include(&out).define("HAVE_CONFIG_H", None).define("_FORTIFY_SOURCE", "0").flag("-w");
    }
    build.compile("nasm");
}

/// The assembler's sources (Makefile.in's `nasm`, without the disassembler).
const SOURCES: &str = "asm/nasm asm/error asm/floats asm/directiv asm/pragma asm/assemble asm/labels asm/parser
    asm/preproc asm/quote asm/listing asm/eval asm/exprlib asm/exprdump asm/stdscan asm/getbool asm/strfunc
    asm/segalloc asm/rdstrnum asm/srcfile asm/directbl asm/pptok asm/tokhash asm/uncompress asm/warnings
    macros/macros output/outform output/outlib output/nulldbg output/nullout output/outbin output/outaout
    output/outcoff output/outelf output/outobj output/outas86 output/outdbg output/outieee output/outmacho
    output/codeview stdlib/snprintf stdlib/vsnprintf stdlib/strlcpy stdlib/strnlen nasmlib/ver nasmlib/alloc
    nasmlib/asprintf nasmlib/crc32b nasmlib/crc64 nasmlib/md5c nasmlib/string nasmlib/nctype nasmlib/file
    nasmlib/fileio nasmlib/mmap nasmlib/realpath nasmlib/path nasmlib/ilog2 nasmlib/numstr nasmlib/rlimit
    nasmlib/zerobuf nasmlib/bsi nasmlib/rbtree nasmlib/hashtbl nasmlib/raa nasmlib/saa nasmlib/strlist
    nasmlib/perfhash nasmlib/badenum nasmlib/readnum common/common common/errstubs x86/insnsa x86/insnsb
    x86/insnsn x86/regs x86/regvals x86/regflags x86/iflag zlib/adler32 zlib/crc32 zlib/infback zlib/inffast
    zlib/inflate zlib/inftrees zlib/zutil";

/// What NASM's configure finds on every C99 and POSIX system.
const HAVE: &str = "INTTYPES_H STDINT_H STDBOOL_H STDARG_H STDIO_H STDLIB_H STRING_H STRINGS_H UNISTD_H FCNTL_H
    SYS_TYPES_H SYS_STAT_H SYS_MMAN_H SYS_PARAM_H SNPRINTF VSNPRINTF STRCASECMP STRNCASECMP STRNLEN
    DECL_STRCASECMP DECL_STRNCASECMP DECL_STRNLEN STAT FSTAT S_ISREG STRUCT_STAT ACCESS FILENO FTRUNCATE MMAP
    GETPAGESIZE SYSCONF REALPATH PATHCONF FSEEKO UINTPTR_T UINTMAX_T _BOOL STDC_INLINE VARIADIC_MACROS ISASCII
    ISCNTRL";
