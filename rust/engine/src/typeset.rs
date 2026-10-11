//! Typst as a library: a document in, its layout out, read straight off Typst's frames. Every
//! glyph comes with its outline's key, its placement, its paint and the source bytes it draws
//! (its cluster, through its span); every shape as cubic curves; each item with the source node
//! it came from; every labelled group as the items inside it.
//!
//! Coordinates: a glyph's placement maps its outline (font units, y up) to the page in points
//! with y up (Typst's page is y down; the flip is folded in here). Shapes come in page points,
//! y up. Python scales points to scene units.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex, OnceLock};

use typst::diag::{FileError, FileResult, Severity, SourceDiagnostic};
use typst::foundations::{Bytes, Datetime, Duration};
use typst::introspection::{Location, Tag};
use typst::layout::{Abs, Frame, FrameItem, Point, Transform};
use typst::syntax::{FileId, RootedPath, Source, Span, SyntaxKind, VirtualPath, VirtualRoot};
use typst::text::{Font, FontBook, FontInstance};
use typst::utils::LazyHash;
use typst::visualize::{Curve, CurveItem, FixedStroke, Geometry, Paint};
use typst::{Library, LibraryExt, World, WorldExt};
use typst::text::{Coverage, FontAxis, FontFlags, FontInfo, FontVariant};
use typst_kit::fonts::{FontPath, FontSource, FontStore, embedded, scan, system};
use typst_layout::PagedDocument;
use unicode_segmentation::UnicodeSegmentation;

/// One item's row: kind, key, placement (6), fill (4), stroke (4), stroke width, advance, and
/// where the item came from (see `Walk::origin`): its node in the source (start, end), the bytes
/// of the node's text a glyph's cluster draws (start, end) and the node's kind (`NODE_*`).
const ROW: usize = 23;
/// An item's node: none (nothing in the main source made it), markup text (its text is its
/// source), a string literal (its text is the string's value), or another node (an escape, a
/// shorthand, an element around the item…).
const NODE_NONE: f64 = 0.0;
const NODE_TEXT: f64 = 1.0;
const NODE_STR: f64 = 2.0;
const NODE_OTHER: f64 = 3.0;
const GLYPH: f64 = 0.0;
const SHAPE: f64 = 1.0;

/// Fonts and packages for one dependency revision: loading fonts costs milliseconds,
/// compiling with the same revision again is incremental.
struct Setup {
    revision: u64, // the caller's font/package dependency identity, shared with its layout cache
    library: LazyHash<Library>,
    fonts: FontStore,
    packages: Option<PathBuf>,
    // a package's files, read and parsed once: a source kept is one Typst's memos recognize
    files: Mutex<HashMap<FileId, FileResult<Bytes>>>,
    sources: Mutex<HashMap<FileId, FileResult<Source>>>,
}

/// A setup's fonts: the directories scanned (the caller's and ManimGX's own), the packages, and
/// the system families the document names (lowercase; none: no system font at all).
type SetupKey = (Vec<String>, Option<String>, Vec<String>);

fn setups() -> &'static Mutex<HashMap<SetupKey, Arc<Setup>>> {
    static SETUPS: OnceLock<Mutex<HashMap<SetupKey, Arc<Setup>>>> = OnceLock::new();
    SETUPS.get_or_init(Default::default)
}

/// The fonts in `font_paths` (the caller's, then the ones ManimGX ships) and Typst's own, and of
/// the system's only the families in `named`: a document sets its text in ManimGX's fonts on every
/// machine, falls back only among them, and reaches a system font only by naming it.
fn setup(font_paths: &[String], packages: Option<&str>, named: &[String], revision: u64) -> Arc<Setup> {
    let key = (font_paths.to_vec(), packages.map(str::to_owned), named.to_vec());
    let mut all = setups().lock().unwrap();
    if let Some(held) = all.get(&key)
        && held.revision == revision
    {
        return held.clone();
    }
    let mut fonts = FontStore::new();
    let dirs: Vec<PathBuf> = font_paths.iter().map(PathBuf::from).collect();
    fonts.extend(cached_scan(&dirs, || dirs.iter().flat_map(|dir| scan(dir)).collect()));
    fonts.extend(embedded());
    if !named.is_empty() {
        fonts.extend(
            cached_scan(&font_directories(), || system().collect())
                .into_iter()
                .filter(|(_, info)| named.contains(&info.family.to_lowercase())),
        );
    }
    let made = Arc::new(Setup {
        revision,
        library: LazyHash::new(Library::default()),
        fonts,
        packages: packages.map(PathBuf::from),
        files: Mutex::default(),
        sources: Mutex::default(),
    });
    // Existing documents retain their own Arc; only reuse under this setup is replaced.
    all.insert(key, made.clone());
    made
}

/// A font on disk, mapped into memory when first used (not read whole: a CJK font is 60 MB and a
/// text touches a few of its pages).
struct Mapped {
    path: PathBuf,
    index: u32,
}

impl FontSource for Mapped {
    fn load(&self) -> Option<Font> {
        let file = std::fs::File::open(&self.path).ok()?;
        // SAFETY: a font file is not written while mapped (as fontdb and typst-kit assume)
        let map = unsafe { memmap2::Mmap::map(&file) }.ok()?;
        Font::new(Bytes::new(map), self.index)
    }
}

/// A scanned font as the cache keeps it: where it is, and its info's fields.
type Cached = (PathBuf, u32, String, FontVariant, FontFlags, Vec<FontAxis>, Coverage);
/// What made a cached scan, in its file's name: bump it with Typst, or when `Cached` changes.
const SCAN: &str = "typst-0.15.1";

/// MANIMGX_CACHE_DIR when set, otherwise the current user's native cache or the browser
/// runtime's private filesystem. A missing native root disables disk reuse, with no shared-temp fallback.
pub fn cache_directory() -> Option<PathBuf> {
    if let Some(root) = std::env::var_os("MANIMGX_CACHE_DIR").filter(|root| !root.is_empty()) {
        return Some(root.into());
    }
    #[cfg(target_os = "emscripten")]
    return Some(std::env::temp_dir().join("manimgx"));
    #[cfg(not(target_os = "emscripten"))]
    dirs::cache_dir().map(|root| root.join("manimgx"))
}

/// The fonts under `dirs`, as Typst finds them (`find`: typst-kit's scan of them), read from a
/// cache on disk while no file under them has changed: scanning parses every font (~50 ms for the
/// system's, ~15 ms for a CJK collection); checking the files' sizes and times costs a few
/// milliseconds. A font installed or removed changes the fingerprint, so every font stays usable.
fn cached_scan(
    dirs: &[PathBuf],
    find: impl FnOnce() -> Vec<(FontPath, FontInfo)>,
) -> Vec<(Mapped, FontInfo)> {
    if dirs.is_empty() {
        return Vec::new();
    }
    let key = fingerprint(dirs);
    let cache = cache_directory().map(|root| root.join("fonts").join(format!("{SCAN}-{key:016x}.bin")));
    read_scan(cache.as_deref(), find)
}

fn read_scan(cache: Option<&Path>, find: impl FnOnce() -> Vec<(FontPath, FontInfo)>) -> Vec<(Mapped, FontInfo)> {
    let entries: Vec<Cached> = match cache.and_then(|path| std::fs::read(path).ok()).and_then(|b| bincode::deserialize(&b).ok()) {
        Some(entries) => entries,
        None => {
            let entries: Vec<Cached> = find()
                .into_iter()
                .map(|(path, info)| {
                    let FontInfo { family, variant, flags, axes, coverage } = info;
                    (path.path, path.index, family, variant, flags, axes, coverage)
                })
                .collect();
            if let Some(cache) = cache
                && let Ok(bytes) = bincode::serialize(&entries)
            {
                // written whole, then renamed: a reader never sees half a file
                let partial = cache.with_extension(format!("{}.tmp", std::process::id()));
                let _ = std::fs::create_dir_all(cache.parent().expect("cache directory"))
                    .and_then(|()| std::fs::write(&partial, bytes))
                    .and_then(|()| std::fs::rename(&partial, cache));
            }
            entries
        }
    };
    entries
        .into_iter()
        .map(|(path, index, family, variant, flags, axes, coverage)| {
            (Mapped { path, index }, FontInfo { family, variant, flags, axes, coverage })
        })
        .collect()
}

/// Where fontdb looks for the system's fonts (its `load_system_fonts`), and where typst-kit
/// looks for Adobe's.
fn font_directories() -> Vec<PathBuf> {
    let home = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" }).map(PathBuf::from);
    let mut dirs: Vec<PathBuf> = Vec::new();
    if cfg!(target_os = "macos") {
        dirs.extend(["/Library/Fonts", "/System/Library/Fonts", "/Network/Library/Fonts"].map(PathBuf::from));
        if let Ok(assets) = std::fs::read_dir("/System/Library/AssetsV2") {
            dirs.extend(assets.flatten().map(|e| e.path()).filter(|p| {
                p.file_name().is_some_and(|n| n.to_string_lossy().starts_with("com_apple_MobileAsset_Font"))
            }));
        }
        dirs.extend(home.iter().flat_map(|h| {
            let adobe = h.join("Library/Application Support/Adobe");
            [h.join("Library/Fonts"), adobe.join("CoreSync/plugins/livetype/.r"), adobe.join(".User Owned Fonts")]
        }));
    } else if cfg!(windows) {
        let root = std::env::var_os("SYSTEMROOT").map_or_else(|| PathBuf::from("C:\\Windows"), PathBuf::from);
        dirs.push(root.join("Fonts"));
        dirs.extend(home.iter().flat_map(|h| {
            let adobe = h.join("AppData\\Roaming\\Adobe");
            [
                h.join("AppData\\Local\\Microsoft\\Windows\\Fonts"),
                h.join("AppData\\Roaming\\Microsoft\\Windows\\Fonts"),
                adobe.join("CoreSync\\plugins\\livetype\\r"),
                adobe.join("User Owned Fonts"),
            ]
        }));
    } else {
        dirs.extend(["/usr/share/fonts", "/usr/local/share/fonts"].map(PathBuf::from));
        dirs.extend(home.iter().flat_map(|h| [h.join(".local/share/fonts"), h.join(".fonts")]));
    }
    dirs
}

/// Every file under `dirs`: its path, size and modification time, hashed.
fn fingerprint(dirs: &[PathBuf]) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::hash::DefaultHasher::new();
    let mut stack: Vec<PathBuf> = dirs.to_vec();
    while let Some(dir) = stack.pop() {
        dir.hash(&mut hasher);
        let Ok(entries) = std::fs::read_dir(&dir) else { continue };
        let mut entries: Vec<_> = entries.flatten().collect();
        entries.sort_by_key(|e| e.file_name());
        for entry in entries {
            let Ok(meta) = std::fs::metadata(entry.path()) else { continue };
            if meta.is_dir() {
                stack.push(entry.path());
            } else {
                entry.file_name().hash(&mut hasher);
                meta.len().hash(&mut hasher);
                meta.modified().ok().hash(&mut hasher);
            }
        }
    }
    hasher.finish()
}

/// A document: its setup and its main source.
struct Document<'a> {
    setup: &'a Setup,
    main: Source,
}

impl Document<'_> {
    /// A package's file: mitex's from the engine (`@preview/mitex`, the package the converted
    /// LaTeX calls, built in), any other from the packages' directory, if there is one.
    fn read(&self, id: FileId) -> FileResult<Bytes> {
        let path = id.get();
        let within = path.vpath().get_without_slash();
        if let VirtualRoot::Package(spec) = path.root()
            && (spec.namespace.as_str(), spec.name.as_str()) == ("preview", "mitex")
            && spec.version.to_string() == mitex_spec_gen::VERSION
            && let Some((_, bytes)) = mitex_spec_gen::PACKAGE.iter().find(|(p, _)| *p == within)
        {
            return Ok(Bytes::new(*bytes));
        }
        let (VirtualRoot::Package(spec), Some(root)) = (path.root(), &self.setup.packages) else {
            return Err(FileError::NotFound(within.into()));
        };
        let file = root
            .join(spec.namespace.as_str())
            .join(spec.name.as_str())
            .join(spec.version.to_string())
            .join(within);
        std::fs::read(&file)
            .map(Bytes::new)
            .map_err(|error| FileError::from_io(error, &file))
    }
}

impl World for Document<'_> {
    fn library(&self) -> &LazyHash<Library> {
        &self.setup.library
    }
    fn book(&self) -> &LazyHash<FontBook> {
        self.setup.fonts.book()
    }
    fn main(&self) -> FileId {
        self.main.id()
    }
    fn source(&self, id: FileId) -> FileResult<Source> {
        if id == self.main.id() {
            return Ok(self.main.clone());
        }
        let cached = self.setup.sources.lock().unwrap().get(&id).cloned();
        if let Some(source) = cached {
            return source;
        }
        let source = self.file(id).and_then(|bytes| {
            let text = std::str::from_utf8(&bytes).map_err(|_| FileError::InvalidUtf8)?;
            Ok(Source::new(id, text.into()))
        });
        self.setup.sources.lock().unwrap().insert(id, source.clone());
        source
    }
    fn file(&self, id: FileId) -> FileResult<Bytes> {
        let mut files = self.setup.files.lock().unwrap();
        files.entry(id).or_insert_with(|| self.read(id)).clone()
    }
    fn font(&self, index: usize) -> Option<Font> {
        self.setup.fonts.font(index)
    }
    fn today(&self, _: Option<Duration>) -> Option<Datetime> {
        None
    }
}

/// Fonts by the keys glyph outlines are cached under: a font instance's number, times 65536,
/// plus the glyph's id. Numbers are for the process, so a key names one outline forever.
fn fonts() -> &'static Mutex<(HashMap<FontInstance, u32>, Vec<FontInstance>)> {
    static FONTS: OnceLock<Mutex<(HashMap<FontInstance, u32>, Vec<FontInstance>)>> =
        OnceLock::new();
    FONTS.get_or_init(Default::default)
}

fn font_number(font: &FontInstance) -> u32 {
    let mut fonts = fonts().lock().unwrap();
    if let Some(&n) = fonts.0.get(font) {
        return n;
    }
    let n = fonts.1.len() as u32;
    fonts.0.insert(font.clone(), n);
    fonts.1.push(font.clone());
    n
}

fn rgba(paint: &Paint) -> [f64; 4] {
    // a gradient or a tiling: its first color stands for it (a part has one paint)
    let color = match paint {
        Paint::Solid(color) => color.clone(),
        Paint::Gradient(gradient) => gradient.stops_ref()[0].0.clone(),
        Paint::Tiling(_) => typst::visualize::Color::BLACK,
    };
    let rgb = color.to_rgb();
    // in 8 bits a channel, as ManimGX's colors are
    [rgb.red, rgb.green, rgb.blue, rgb.alpha].map(|c| (f64::from(c) * 255.0).round() / 255.0)
}

/// A stroke's color and width (none: [-1; 4], 0).
fn stroke(stroke: &Option<FixedStroke>) -> ([f64; 4], f64) {
    stroke.as_ref().map_or(([-1.0; 4], 0.0), |s| (rgba(&s.paint), s.thickness.to_pt()))
}

/// Page (points, y down) to points with y up.
fn flip(ts: Transform) -> Transform {
    Transform::scale(typst::layout::Ratio::one(), -typst::layout::Ratio::one()).pre_concat(ts)
}

fn affine(ts: Transform) -> [f64; 6] {
    [ts.sx.get(), ts.ky.get(), ts.kx.get(), ts.sy.get(), ts.tx.to_pt(), ts.ty.to_pt()]
}

struct Walk<'a> {
    doc: &'a Document<'a>,
    rows: Vec<f64>,
    shapes: Vec<Vec<f64>>,
    labels: Vec<(String, Vec<usize>)>,
    open: Vec<usize>, // the labelled groups the walk is inside
    // the elements the walk is inside, by their tags (an equation, a labelled element…), the
    // innermost last
    around: Vec<(Location, Span)>,
}

impl Walk<'_> {
    fn item(&mut self, row: [f64; ROW]) {
        let index = self.rows.len() / ROW;
        for &group in &self.open {
            self.labels[group].1.push(index);
        }
        self.rows.extend_from_slice(&row);
    }

    /// Where an item came from: the main source's node that made it, its range and kind. That
    /// is its own (its span's) if the main source has it; else the innermost element around it
    /// that the main source has, so a mark a package drew (mitex's fraction bar or radical) is
    /// the equation's that holds it. For a glyph from its own node, `cluster` (its offset in the
    /// node's text, and its length) gives the bytes it draws; -1, -1 otherwise.
    fn origin(&self, span: Span, cluster: Option<(u16, usize)>) -> [f64; 5] {
        let main = |span: Span| {
            (span.id() == Some(self.doc.main.id())).then(|| self.doc.main.find(span)).flatten()
        };
        let (node, cluster) = match main(span) {
            Some(node) => (node, cluster),
            None => match self.around.iter().rev().find_map(|&(_, span)| main(span)) {
                Some(node) => (node, None),
                None => return [-1.0, -1.0, -1.0, -1.0, NODE_NONE],
            },
        };
        let kind = match node.kind() {
            SyntaxKind::Text => NODE_TEXT,
            SyntaxKind::Str => NODE_STR,
            _ => NODE_OTHER,
        };
        let (from, to) = cluster.map_or((-1.0, -1.0), |(offset, len)| {
            let start = usize::from(offset);
            (start as f64, (start + len) as f64)
        });
        [node.range().start as f64, node.range().end as f64, from, to, kind]
    }

    fn frame(&mut self, frame: &Frame, ts: Transform) {
        for (pos, item) in frame.items() {
            let at = ts.pre_concat(Transform::translate(pos.x, pos.y));
            match item {
                FrameItem::Group(group) => {
                    let labelled = group.label.map(|label| {
                        self.labels.push((label.resolve().to_string(), Vec::new()));
                        self.open.push(self.labels.len() - 1);
                    });
                    self.frame(&group.frame, at.pre_concat(group.transform));
                    if labelled.is_some() {
                        self.open.pop();
                    }
                }
                FrameItem::Text(text) => {
                    let number = f64::from(font_number(&text.font));
                    let scale = text.size.to_pt() / text.font.units_per_em();
                    let fill = rgba(&text.fill);
                    let (stroke, width) = stroke(&text.stroke);
                    // a run advances along x, or along y (a stretched delimiter's parts)
                    let (mut x, mut y) = (Abs::zero(), Abs::zero());
                    for glyph in &text.glyphs {
                        let origin = Point::new(
                            x + glyph.x_offset.at(text.size),
                            -(y + glyph.y_offset.at(text.size)),
                        );
                        // outline (font units, y up) → page (y down) → y up
                        let placement = flip(at)
                            .pre_concat(Transform::translate(origin.x, origin.y))
                            .pre_concat(Transform::scale(
                                typst::layout::Ratio::new(scale),
                                typst::layout::Ratio::new(-scale),
                            ));
                        let [node_start, node_end, from, to, kind] =
                            self.origin(glyph.span.0, Some((glyph.span.1, glyph.range().len())));
                        let [a, b, c, d, e, f] = affine(placement);
                        let advance = glyph.x_advance.get() * text.font.units_per_em();
                        self.item([
                            GLYPH,
                            number * 65536.0 + f64::from(glyph.id),
                            a, b, c, d, e, f,
                            fill[0], fill[1], fill[2], fill[3],
                            stroke[0], stroke[1], stroke[2], stroke[3],
                            width,
                            advance,
                            node_start, node_end, from, to, kind,
                        ]);
                        x += glyph.x_advance.at(text.size);
                        y += glyph.y_advance.at(text.size);
                    }
                }
                FrameItem::Shape(shape, span) => {
                    let curve = match &shape.geometry {
                        Geometry::Line(to) => {
                            let mut c = Curve::new();
                            c.move_(Point::zero());
                            c.line(*to);
                            c
                        }
                        Geometry::Rect(size) => Curve::rect(*size),
                        Geometry::Curve(curve) => curve.clone(),
                    };
                    let points = cubics(&curve, flip(at));
                    if points.is_empty() {
                        continue;
                    }
                    let fill = shape.fill.as_ref().map_or([-1.0; 4], rgba);
                    let (stroke, width) = stroke(&shape.stroke);
                    let [node_start, node_end, from, to, kind] = self.origin(*span, None);
                    let index = self.shapes.len() as f64;
                    self.shapes.push(points);
                    self.item([
                        SHAPE, index, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                        fill[0], fill[1], fill[2], fill[3],
                        stroke[0], stroke[1], stroke[2], stroke[3],
                        width, 0.0, node_start, node_end, from, to, kind,
                    ]);
                }
                FrameItem::Tag(tag @ Tag::Start(elem, _)) => {
                    self.around.push((tag.location(), elem.span()));
                }
                FrameItem::Tag(tag @ Tag::End(..)) => {
                    let location = tag.location();
                    if let Some(i) = self.around.iter().rposition(|&(at, _)| at == location) {
                        self.around.remove(i);
                    }
                }
                FrameItem::Image(..) | FrameItem::Link(..) => {}
            }
        }
    }
}

/// A curve as ManimGX's cubic points (4 per curve, x y z), lines raised to cubics.
fn cubics(curve: &Curve, ts: Transform) -> Vec<f64> {
    let mut out = Vec::new();
    let p = |q: Point| {
        let q = q.transform(ts);
        [q.x.to_pt(), q.y.to_pt()]
    };
    let mut push = |a: [f64; 2], b: [f64; 2], c: [f64; 2], d: [f64; 2]| {
        for q in [a, b, c, d] {
            out.extend_from_slice(&[q[0], q[1], 0.0]);
        }
    };
    let (mut pen, mut start) = ([0.0; 2], [0.0; 2]);
    for item in curve.0.iter() {
        match *item {
            CurveItem::Move(to) => {
                pen = p(to);
                start = pen;
            }
            CurveItem::Line(to) => {
                let end = p(to);
                push(pen, lerp(pen, end, 1.0 / 3.0), lerp(pen, end, 2.0 / 3.0), end);
                pen = end;
            }
            CurveItem::Cubic(c1, c2, to) => {
                let end = p(to);
                push(pen, p(c1), p(c2), end);
                pen = end;
            }
            CurveItem::Close => {
                if pen != start {
                    push(pen, lerp(pen, start, 1.0 / 3.0), lerp(pen, start, 2.0 / 3.0), start);
                }
                pen = start;
            }
        }
    }
    out
}

fn lerp(a: [f64; 2], b: [f64; 2], t: f64) -> [f64; 2] {
    [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
}

fn message(diagnostics: &[SourceDiagnostic], doc: &Document) -> String {
    diagnostics
        .iter()
        .filter(|d| d.severity == Severity::Error)
        .map(|d| {
            let at = doc
                .range(d.span)
                .map(|r| format!(" (source bytes {}..{})", r.start, r.end))
                .unwrap_or_default();
            format!("{}{at}", d.message)
        })
        .collect::<Vec<_>>()
        .join("; ")
}

pub type Layout = (Vec<f64>, Vec<Vec<f64>>, Vec<(String, Vec<usize>)>, bool);

/// Typeset `source` with the fonts in `font_paths` and Typst's own (a system font only by its
/// family's name), and the packages under `packages` besides mitex's (the engine's own): its
/// items (one row of `ROW` floats each, in document order), its shapes' cubic points and its
/// labelled groups (a label and the items inside, nested ones too).
pub fn typeset(source: String, font_paths: &[String], packages: Option<&str>, revision: u64) -> Result<Layout, String> {
    {
        static COMPILES: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        let file = RootedPath::new(VirtualRoot::Project, VirtualPath::new("main.typ").unwrap())
            .intern();
        let main = Source::new(file, source);
        // ManimGX's fonts (the caller's, the bundled ones, Typst's own); a system font only
        // when the document names a family they don't include, and then that family alone
        let lean = setup(font_paths, packages, &[], revision);
        let doc = Document { setup: &lean, main: main.clone() };
        let warned = typst::compile::<PagedDocument>(&doc);
        let mut named: Vec<String> = warned
            .warnings
            .iter()
            .filter_map(|w| w.message.strip_prefix("unknown font family: "))
            .map(str::to_owned)
            .collect();
        named.sort();
        named.dedup();
        let full;
        let system = !named.is_empty();
        let (doc, compiled) = if system {
            full = setup(font_paths, packages, &named, revision);
            let doc = Document { setup: &full, main };
            let compiled = typst::compile::<PagedDocument>(&doc).output;
            (doc, compiled)
        } else {
            (doc, warned.output)
        };
        // Typst memoizes across documents; forget what the last few hundred didn't use
        if COMPILES.fetch_add(1, std::sync::atomic::Ordering::Relaxed) % 256 == 255 {
            typst::comemo::evict(8);
        }
        let document = compiled.map_err(|errors| message(&errors, &doc))?;
        let page = document.pages().first().ok_or("Typst produced no page")?;
        let mut walk = Walk {
            doc: &doc,
            rows: Vec::new(),
            shapes: Vec::new(),
            labels: Vec::new(),
            open: Vec::new(),
            around: Vec::new(),
        };
        walk.frame(&page.frame, Transform::identity());
        Ok((walk.rows, walk.shapes, walk.labels, system))
    }
}

/// The system's fonts' fingerprint (every file under their directories: path, size, time), once
/// per process: a layout set with system fonts is good while it is unchanged.
pub fn system_fonts_fingerprint() -> u64 {
    static FINGERPRINT: OnceLock<u64> = OnceLock::new();
    *FINGERPRINT.get_or_init(|| fingerprint(&font_directories()))
}

/// The fonts a player's face is set in (see `text`): the font files in `dirs` (ManimGX's), and
/// Typst's monospace one, DejaVu Sans Mono; each file's bytes, kept (mapped, where files are) for
/// as long as the program runs.
pub fn face_fonts(dirs: &[String]) -> Vec<&'static [u8]> {
    let mut files: Vec<&'static [u8]> = Vec::new();
    for dir in dirs {
        let Ok(entries) = std::fs::read_dir(dir) else { continue };
        let font = |p: &PathBuf| p.extension().and_then(|e| e.to_str()).is_some_and(|e| ["ttf", "otf", "ttc", "otc"].contains(&e.to_ascii_lowercase().as_str()));
        let mut paths: Vec<PathBuf> = entries.flatten().map(|e| e.path()).filter(font).collect();
        paths.sort();
        for path in paths {
            let Ok(file) = std::fs::File::open(&path) else { continue };
            // SAFETY: a font file is not written while mapped (as fontdb and typst-kit assume)
            if let Ok(map) = unsafe { memmap2::Mmap::map(&file) } {
                files.push(&Box::leak(Box::new(map))[..]);
            }
        }
    }
    let mono = embedded().find(|(_, info)| info.family == "DejaVu Sans Mono" && info.variant == FontVariant::default());
    files.extend(mono.map(|(font, _)| &*Box::leak(font.data().to_vec().into_boxed_slice())));
    files
}

/// A glyph's outline as a curve (font units): TrueType's quadratics raised to cubics.
struct Pen {
    curve: Curve,
    at: Point,
}

impl Pen {
    fn point(x: f32, y: f32) -> Point {
        Point::new(Abs::pt(f64::from(x)), Abs::pt(f64::from(y)))
    }
}

impl ttf_parser::OutlineBuilder for Pen {
    fn move_to(&mut self, x: f32, y: f32) {
        self.at = Self::point(x, y);
        self.curve.move_(self.at);
    }
    fn line_to(&mut self, x: f32, y: f32) {
        self.at = Self::point(x, y);
        self.curve.line(self.at);
    }
    fn quad_to(&mut self, x1: f32, y1: f32, x: f32, y: f32) {
        let (c, end) = (Self::point(x1, y1), Self::point(x, y));
        let third = |a: Point, b: Point| a + (b - a) * (2.0 / 3.0);
        self.curve.cubic(third(self.at, c), third(end, c), end);
        self.at = end;
    }
    fn curve_to(&mut self, x1: f32, y1: f32, x2: f32, y2: f32, x: f32, y: f32) {
        self.at = Self::point(x, y);
        self.curve.cubic(Self::point(x1, y1), Self::point(x2, y2), self.at);
    }
    fn close(&mut self) {
        self.curve.close();
    }
}

/// Each key's outline as cubic points (font units, y up); empty for a glyph with no outline
/// (a space) or one Typst would draw as an image (a color emoji).
pub fn glyph_outlines(keys: &[u64]) -> Vec<Vec<f64>> {
    let fonts: Vec<(FontInstance, u16)> = {
        let fonts = fonts().lock().unwrap();
        keys.iter().map(|k| (fonts.1[(k / 65536) as usize].clone(), (k % 65536) as u16)).collect()
    };
    fonts
        .iter()
        .map(|(font, id)| {
            let mut pen = Pen { curve: Curve::new(), at: Point::zero() };
            font.ttf().outline_glyph(ttf_parser::GlyphId(*id), &mut pen);
            cubics(&pen.curve, Transform::identity())
        })
        .collect()
}

/// A ligature glyph's caret positions (font units), from the font's GDEF ligature caret list;
/// empty when the font gives none (then a glyph is divided equally among what it draws).
pub fn ligature_carets(key: u64) -> Vec<f64> {
    let font = fonts().lock().unwrap().1[(key / 65536) as usize].clone();
    carets(font.font().data(), font.font().index(), (key % 65536) as u16).unwrap_or_default()
}

/// GDEF's LigCaretList: Coverage → LigGlyph → CaretValues (formats 1 and 3: a coordinate;
/// format 2, a contour point, is skipped).
fn carets(data: &[u8], index: u32, glyph: u16) -> Option<Vec<f64>> {
    let face = ttf_parser::RawFace::parse(data, index).ok()?;
    let gdef = face.table(ttf_parser::Tag::from_bytes(b"GDEF"))?;
    let u16_at = |d: &[u8], at: usize| Some(u16::from_be_bytes([*d.get(at)?, *d.get(at + 1)?]));
    let list = usize::from(u16_at(gdef, 8)?);
    if list == 0 {
        return None;
    }
    let lig = gdef.get(list..)?;
    let coverage = lig.get(usize::from(u16_at(lig, 0)?)..)?;
    let at = coverage_index(coverage, glyph)?;
    let glyph_table = lig.get(usize::from(u16_at(lig, 4 + 2 * at)?)..)?;
    let count = usize::from(u16_at(glyph_table, 0)?);
    let mut out = Vec::new();
    for k in 0..count {
        let value = glyph_table.get(usize::from(u16_at(glyph_table, 2 + 2 * k)?)..)?;
        match u16_at(value, 0)? {
            1 | 3 => out.push(f64::from(u16_at(value, 2)? as i16)),
            _ => return None,
        }
    }
    Some(out)
}

fn coverage_index(coverage: &[u8], glyph: u16) -> Option<usize> {
    let u16_at = |at: usize| Some(u16::from_be_bytes([*coverage.get(at)?, *coverage.get(at + 1)?]));
    match u16_at(0)? {
        1 => (0..usize::from(u16_at(2)?)).find(|&i| u16_at(4 + 2 * i) == Some(glyph)),
        2 => {
            for i in 0..usize::from(u16_at(2)?) {
                let (start, end, first) = (u16_at(4 + 6 * i)?, u16_at(6 + 6 * i)?, u16_at(8 + 6 * i)?);
                if (start..=end).contains(&glyph) {
                    return Some(usize::from(first + (glyph - start)));
                }
            }
            None
        }
        _ => None,
    }
}

/// Where `text`'s graphemes (user-perceived characters, UAX #29) start, in characters.
pub fn graphemes(text: &str) -> Vec<usize> {
    let mut chars = 0;
    text.graphemes(true)
        .map(|g| {
            let at = chars;
            chars += g.chars().count();
            at
        })
        .collect()
}

/// LaTeX math as Typst math (mitex's conversion; its default command spec).
pub fn mitex_math(latex: &str) -> Result<String, String> {
    mitex::convert_math(latex, None)
}

/// LaTeX text as Typst markup (mitex's conversion; its default command spec).
pub fn mitex_text(latex: &str) -> Result<String, String> {
    mitex::convert_text(latex, None)
}

#[cfg(test)]
mod tests {
    /// A one-table SFNT containing one ligature's GDEF caret, with no outline required.
    fn caret_font(format: u16, coordinate: i16, length: usize) -> Vec<u8> {
        let table: Vec<u8> = [1u16, 0, 0, 0, 12, 0, 6, 1, 12, 1, 1, 36, 1, 4, format, coordinate as u16, 0]
            .into_iter().flat_map(u16::to_be_bytes).take(length).collect();
        let mut data = vec![0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0];
        data.extend_from_slice(b"GDEF");
        data.extend_from_slice(&0u32.to_be_bytes());
        data.extend_from_slice(&28u32.to_be_bytes());
        data.extend_from_slice(&(table.len() as u32).to_be_bytes());
        data.extend(table);
        data
    }

    #[test]
    fn truncated_optional_caret_has_no_coordinate() {
        for format in [1, 3] {
            for length in 0..32 {
                assert_eq!(super::carets(&caret_font(format, 250, length), 0, 36), None, "format {format}, length {length}");
            }
        }
    }

    #[test]
    fn valid_caret_coordinates_remain_signed() {
        for format in [1, 3] {
            for coordinate in [i16::MIN, -1, 0, 250, i16::MAX] {
                assert_eq!(super::carets(&caret_font(format, coordinate, 34), 0, 36), Some(vec![f64::from(coordinate)]));
            }
        }
    }

    #[test]
    fn unavailable_cache_root_scans_each_time() {
        let calls = std::cell::Cell::new(0);
        for _ in 0..2 {
            assert!(super::read_scan(None, || {
                calls.set(calls.get() + 1);
                Vec::new()
            }).is_empty());
        }
        assert_eq!(calls.get(), 2);
    }
}
