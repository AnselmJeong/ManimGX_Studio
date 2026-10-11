//! FFmpeg 9.0.2's audio decoders, and libopus 1.6.1 for Opus, from their sources (fetched), with
//! nothing installed: no configure, no make. What FFmpeg's configure resolves for the components
//! ManimGX decodes with is the lock below (`ON`, the names it turns on; `SOURCES`, the files it
//! compiles), made once by
//!
//! ```text
//! configure --arch=c --target-os=none --enable-cross-compile --disable-asm --disable-inline-asm
//!   --disable-pthreads --disable-network --disable-autodetect --disable-everything
//!   --disable-programs --disable-doc --disable-avdevice --disable-avfilter --disable-swscale
//!   --disable-faan --enable-swresample --enable-libopus --enable-decoder=aac,mp3float,mp2float,
//!   mp1float,libopus,vorbis,flac,alac,pcm_u8,pcm_s8,pcm_s16le,pcm_s16be,pcm_s24le,pcm_s24be,
//!   pcm_s32le,pcm_s32be,pcm_f32le,pcm_f32be,pcm_f64le,pcm_f64be,pcm_alaw,pcm_mulaw,
//!   adpcm_ima_wav,adpcm_ms --enable-demuxer=mov,mp3,ogg,matroska,wav,w64,aiff,caf,flac,aac
//!   --enable-parser=aac,mpegaudio,vorbis,opus,flac
//! ```
//!
//! (its config.h's and config_components.h's names set to 1, but the documentation's and tests';
//! `make -n`'s objects). In portable C, it is the same on every target, the browser's included.
//! The configuration is written from the lock: 1 for its names and for what every C99 library
//! has, 0 for every other name FFmpeg's sources test, and each component FFmpeg declares on or
//! off. libopus's files are read from its own lists. The build has no threads: the crate calls
//! FFmpeg one call at a time.

use std::collections::BTreeSet;
use std::path::Path;

/// The names configure turns on.
const ON: &str = "libopus safe_bitstream_reader avformat avcodec swresample avutil iamf decoders parsers demuxers
    adts_header dirac_parse golomb iamfdec iso_media mpegaudio mpegaudiodsp mpegaudioheader mpeg4audio riffdec
    sinewin aac_decoder alac_decoder flac_decoder mp1float_decoder mp2float_decoder mp3float_decoder vorbis_decoder
    pcm_alaw_decoder pcm_f32be_decoder pcm_f32le_decoder pcm_f64be_decoder pcm_f64le_decoder pcm_mulaw_decoder
    pcm_s8_decoder pcm_s16be_decoder pcm_s16le_decoder pcm_s24be_decoder pcm_s24le_decoder pcm_s32be_decoder
    pcm_s32le_decoder pcm_u8_decoder adpcm_ima_wav_decoder adpcm_ms_decoder libopus_decoder aac_parser flac_parser
    mpegaudio_parser opus_parser vorbis_parser aac_demuxer aiff_demuxer caf_demuxer flac_demuxer matroska_demuxer
    mov_demuxer mp3_demuxer ogg_demuxer w64_demuxer wav_demuxer";

/// The files configure compiles, by library.
const SOURCES: [(&str, &str); 4] = [
    (
        "libavutil",
        "adler32 aes aes_ctr ambient_viewing_environment audio_fifo avsscanf avstring base64 blowfish bprint buffer
        camellia cast5 channel_layout container_fifo cpu crc csp des detection_bbox dict display dovi_meta
        downmix_info encryption_info error eval executor fifo file file_open film_grain_params fixed_dsp float_dsp
        float_scalarproduct frame hash hdr_dynamic_metadata hdr_dynamic_vivid_metadata hmac hwcontext hwcontext_stub
        iamf imgutils integer intmath lfg lls log log2_tab lzo mastering_display_metadata mathematics md5 mem
        murmur3 opt parseutils pixdesc pixelutils random_seed rational raw_color_params rc4 refstruct reverse
        ripemd samplefmt sha sha512 side_data slicethread spherical stereo3d tdrdi tea threadmessage time timecode
        timecode_internal timestamp tree twofish tx tx_double tx_float tx_int32 utils uuid version
        video_enc_params video_hint xga_font_data xtea",
    ),
    (
        "libavcodec",
        "aac/aacdec aac/aacdec_ac aac/aacdec_float aac/aacdec_lpd aac/aacdec_tab aac/aacdec_usac
        aac/aacdec_usac_mps212 aac_ac3_parser aac_parser aacps_common aacps_float aacpsdsp_float aacsbr aactab
        ac3_channel_layout_tab ac3_parser adpcm adpcm_data adts_header adts_parser alac alac_data alacdsp allcodecs
        avcodec avdct bitstream bitstream_filters bsf cbrt_data cbrt_tablegen_common codec_desc codec_par d3d11va
        dct32_fixed dct32_float decode dirac dv_profile encode exif flac flac_parser flacdata flacdec flacdsp
        get_buffer golomb h2645_parse imgconvert jni kbdwin lcevctab libopus libopusdec mathtables mediacodec
        mpeg12framerate mpeg4audio mpeg4audio_sample_rates mpegaudio mpegaudio_parser mpegaudiodata
        mpegaudiodec_common mpegaudiodec_float mpegaudiodecheader mpegaudiodsp mpegaudiodsp_data mpegaudiodsp_fixed
        mpegaudiodsp_float mpegaudiotabs options opus/frame_duration_tab opus/parse opus/parser packet parser
        parsers pcm profiles qsv_api raw sbrdsp sinewin threadprogress tiff_common to_upper4 utils version vlc
        vorbis vorbis_data vorbis_parser vorbisdec vorbisdsp xiph",
    ),
    (
        "libavformat",
        "aacdec aiff aiffdec allformats apetag av1 avformat avio aviobuf caf cafdec codecstring demux demux_utils
        dovi_isom dump dv dvdclut flac_picture flacdec format iamf iamf_parse iamf_reader id3v1 id3v2 img2 isom
        isom_tags lcevc matroska matroskadec metadata mov mov_chan mov_esds mp3dec mux mux_utils nal oggdec
        oggparsedirac oggparseflac oggparseogm oggparseopus oggparseskeleton oggparsespeex oggparsetheora
        oggparsevorbis oggparsevp8 options os_support packet_list pcm protocols qtpalette rawdec replaygain riff
        riffdec rmsipr sdp seek url urldecode utils version vorbiscomment vpcc w64 wavdec",
    ),
    ("libswresample", "audioconvert dither options rematrix resample resample_dsp swresample swresample_frame version"),
];

/// What every C99 library has (FFmpeg defines replacements for the rest, which clash with these).
const C99: &str = "atanf atan2f cbrt cbrtf copysign cosf erf exp2 exp2f expf hypot isfinite isinf isnan ldexpf
    llrint llrintf log2 log2f log10f lrint lrintf powf rint round roundf sinf trunc truncf";

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=src/shim.c");
    println!("cargo:rerun-if-changed=src/opus/config.h");
    let ffmpeg = &fetch::tree("https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.gz", "c92e6bbcf8183b80ab4771d4fc07dee2d97dd2af0a72f8a6bf13c4242c756ff0");
    let opus = &fetch::tree(
        "https://downloads.xiph.org/releases/opus/opus-1.6.1.tar.gz",
        "8a88c521e03839005b87575f322c7347f82d77f666f025643a30f495906de8ca",
    );
    let out = &std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    let target = |key: &str| std::env::var(format!("CARGO_CFG_TARGET_{key}")).unwrap_or_default();
    let msvc = target("ENV") == "msvc";
    let mut on: BTreeSet<String> = ON.split_whitespace().map(|name| format!("CONFIG_{}", name.to_uppercase())).collect();
    on.extend(C99.split_whitespace().map(|name| format!("HAVE_{}", name.to_uppercase())));
    on.insert("HAVE_AV_CONFIG_H".into()); // also passed to the compiler, before config.h is read
    if target("POINTER_WIDTH") == "64" {
        on.insert("HAVE_FAST_64BIT".into());
    }

    // config.h: the names FFmpeg's sources test, 1 or 0 (but those they define themselves)
    let (mut tested, mut defined) = (BTreeSet::new(), BTreeSet::new());
    for dir in ["libavutil", "libavcodec", "libavformat", "libswresample", "compat"] {
        scan(&ffmpeg.join(dir), &mut tested, &mut defined);
    }
    let mut config = String::from("#ifndef FFMPEG_CONFIG_H\n#define FFMPEG_CONFIG_H\n#define FFMPEG_CONFIGURATION \"manimgx\"\n");
    config += "#define FFMPEG_LICENSE \"LGPL version 2.1 or later\"\n";
    // The file-system wrappers use these even without file protocols. Ask the compiler, as
    // configure does, rather than assuming a target's available C library headers.
    for header in ["direct.h", "io.h", "unistd.h"] {
        let name = format!("HAVE_{}", header.replace('.', "_").to_uppercase());
        config += &format!("#define {name} __has_include(<{header}>)\n");
        defined.insert(name);
    }
    for name in tested.difference(&defined).chain(&on).collect::<BTreeSet<_>>() {
        config += &format!("#define {name} {}\n", on.contains(name) as u8);
    }
    write(&out.join("config.h"), config + "#endif\n");
    write(&out.join("libavutil/avconfig.h"), "#define AV_HAVE_BIGENDIAN 0\n#define AV_HAVE_FAST_UNALIGNED 0\n".into());
    write(&out.join("libavutil/ffversion.h"), "#define FFMPEG_VERSION \"9.0.2\"\n".into());
    // each component FFmpeg declares, on or off (its sources paste some of those names together,
    // which no scan sees), and the lists of those on, in the order they are declared
    let mut components = String::new();
    for (list, kind, array, file) in [
        ("libavcodec/codec_list.c", "FFCodec", "codec_list", "libavcodec/allcodecs.c"),
        ("libavcodec/parser_list.c", "FFCodecParser", "parser_list", "libavcodec/parsers.c"),
        ("libavcodec/bsf_list.c", "FFBitStreamFilter", "bitstream_filters", "libavcodec/bitstream_filters.c"),
        ("libavformat/demuxer_list.c", "FFInputFormat", "demuxer_list", "libavformat/allformats.c"),
        ("libavformat/muxer_list.c", "FFOutputFormat", "muxer_list", "libavformat/allformats.c"),
        ("libavformat/protocol_list.c", "URLProtocol", "url_protocols", "libavformat/protocols.c"),
    ] {
        let text = std::fs::read_to_string(ffmpeg.join(file)).unwrap();
        let names: Vec<&str> = text
            .lines()
            .filter_map(|line| match line.split_whitespace().collect::<Vec<_>>()[..] {
                ["extern", "const", k, name] if k == kind => name.strip_prefix("ff_")?.strip_suffix(';'),
                _ => None,
            })
            .collect();
        let switch = |name: &str| format!("CONFIG_{}", name.to_uppercase());
        components += &names.iter().map(|name| format!("#define {} {}\n", switch(name), on.contains(&switch(name)) as u8)).collect::<String>();
        let entries: String = names.iter().filter(|name| on.contains(&switch(name))).map(|name| format!("    &ff_{name},\n")).collect();
        write(&out.join(list), format!("static const {kind} * const {array}[] = {{\n{entries}    NULL }};\n"));
    }
    write(&out.join("config_components.h"), components);

    let build = || {
        let mut build = cc::Build::new();
        build.extra_warnings(false).opt_level(3).std("c17"); // FFmpeg counts on dead code being removed
        if msvc {
            build.define("_USE_MATH_DEFINES", None).define("_CRT_SECURE_NO_WARNINGS", None).define("_CRT_NONSTDC_NO_WARNINGS", None);
            build.flag("/we4013").flag("/we4133"); // undeclared functions and incompatible pointers
        } else {
            build.flag("-Werror=implicit-function-declaration").flag("-Werror=incompatible-pointer-types").flag("-fno-math-errno").flag("-fno-signed-zeros");
        }
        build
    };
    // libopus, its float build: the files its lists name
    let mut libopus = build();
    libopus.include("src/opus").define("HAVE_CONFIG_H", None).includes(["include", "celt", "silk", "silk/float"].map(|dir| opus.join(dir)));
    for (list, names) in [("celt_sources.mk", "CELT_SOURCES"), ("silk_sources.mk", "SILK_SOURCES SILK_SOURCES_FLOAT"), ("opus_sources.mk", "OPUS_SOURCES OPUS_SOURCES_FLOAT")] {
        // but silk/debug.c, empty without SILK_DEBUG (an object with no symbols, which ranlib warns of)
        libopus.files(make_list(&opus.join(list), names).iter().filter(|file| *file != "silk/debug.c").map(|file| opus.join(file)));
    }
    let mut objects = libopus.compile_intermediates();
    // FFmpeg's files, and the shim
    let mut libav = build();
    libav.include(out).include(ffmpeg).include(ffmpeg.join("compat/stdbit")).include(opus.join("include"));
    libav.define("HAVE_AV_CONFIG_H", None).define("_ISOC11_SOURCE", None).define("_FILE_OFFSET_BITS", "64").define("_LARGEFILE_SOURCE", None);
    // configure exposes POSIX.1-2001 / XSI alongside ISO C, including fdopen in strict C17.
    libav.define("_POSIX_C_SOURCE", "200112").define("_XOPEN_SOURCE", "600");
    if msvc {
        libav.include(ffmpeg.join("compat/atomics/win32")); // FFmpeg's <stdatomic.h> for MSVC
    }
    for (library, names) in SOURCES {
        libav.files(names.split_whitespace().map(|name| ffmpeg.join(format!("{library}/{name}.c"))));
    }
    objects.extend(libav.file("src/shim.c").compile_intermediates());
    cc::Build::new().objects(objects).compile("ffmpeg");
}

/// The names in C sources that FFmpeg's configuration sets (HAVE_, CONFIG_, ARCH_): those they
/// test, and those they #define themselves.
fn scan(dir: &Path, tested: &mut BTreeSet<String>, defined: &mut BTreeSet<String>) {
    for entry in std::fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            scan(&path, tested, defined);
        } else if path.extension().is_some_and(|ext| ext == "c" || ext == "h") {
            let text = String::from_utf8_lossy(&std::fs::read(&path).unwrap()).into_owned();
            let mut previous = "";
            for word in text.split(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '#')).filter(|w| !w.is_empty()) {
                let configured = ["HAVE_", "CONFIG_", "ARCH_"].iter().any(|p| word.len() > p.len() && word.starts_with(p))
                    && word.bytes().all(|b| b.is_ascii_uppercase() || b.is_ascii_digit() || b == b'_');
                if configured {
                    if previous == "#define" || previous == "define" { defined.insert(word.to_owned()) } else { tested.insert(word.to_owned()) };
                }
                previous = word;
            }
        }
    }
}

/// The files a makefile's variables list (`NAME = a.c b.c \` and the lines it continues on).
fn make_list(file: &Path, names: &str) -> Vec<String> {
    let text = std::fs::read_to_string(file).unwrap().replace("\\\n", " ");
    text.lines()
        .filter_map(|line| line.split_once('='))
        .filter(|(name, _)| names.split_whitespace().any(|n| n == name.trim()))
        .flat_map(|(_, files)| files.split_whitespace().map(str::to_owned).collect::<Vec<_>>())
        .collect()
}

fn write(path: &Path, text: String) {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}
