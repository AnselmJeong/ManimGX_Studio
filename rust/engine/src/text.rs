//! The face's text (see `chrome`): a line in ManimGX's fonts, shaped by rustybuzz, the shaper Typst
//! sets text with, so its glyphs are the ones Typst would place; each character in the first font
//! that has it (the line's family first, then the others in their order), the line's runs in their
//! reading order. And its glyphs' outlines, as the renderer draws a path.
//!
//! Typst itself is not here: it is a typesetter of documents, and what the face sets is lines. In
//! the browser it would be 28 MB of WebAssembly; this is 0.7 MB.

use rustybuzz::{Direction, Face, Feature, UnicodeBuffer, Variation};
use ttf_parser::{GlyphId, Tag};
use unicode_segmentation::UnicodeSegmentation;

/// The families the face sets text in.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub(crate) enum Family {
    Sans,
    Mono,
}

impl Family {
    fn name(self) -> &'static str {
        match self {
            Family::Sans => "Noto Sans",
            Family::Mono => "DejaVu Sans Mono",
        }
    }
}

/// A font: its family, whether it slants, and its faces at the weights the face sets: regular and
/// bold (a variable font's at 700; another's, the same face).
struct Font {
    family: String,
    italic: bool,
    regular: Face<'static>,
    bold: Face<'static>,
}

/// The fonts the face is set in, in the order a character falls back through them.
pub(crate) struct Fonts {
    fonts: Vec<Font>,
    orders: [Vec<u16>; 2], // where a character of each family is looked for (`order`)
}

/// A glyph of a line: its font (an index), weight and id; where its origin is (points, y up, from
/// the line's start on its baseline); its size (points per font unit).
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Glyph {
    pub(crate) font: u16,
    pub(crate) bold: bool,
    pub(crate) id: u16,
    pub(crate) x: f32,
    pub(crate) y: f32,
    pub(crate) scale: f32,
}

/// A line set: its glyphs, and its advance (points).
#[derive(Debug)]
pub(crate) struct Line {
    pub(crate) glyphs: Vec<Glyph>,
    pub(crate) width: f32,
}

/// A font's family, as its name table gives it (the typographic family first).
fn family(face: &Face) -> String {
    let names = face.names();
    [ttf_parser::name_id::TYPOGRAPHIC_FAMILY, ttf_parser::name_id::FAMILY]
        .into_iter()
        .find_map(|id| names.into_iter().filter(|n| n.name_id == id).find_map(|n| n.to_string()))
        .unwrap_or_default()
}

impl Fonts {
    /// The fonts in `files` (each a font file's bytes, kept for as long as the program runs; a
    /// collection gives each of its fonts), falling back in that order.
    pub(crate) fn new(files: impl IntoIterator<Item = &'static [u8]>) -> Self {
        let mut fonts = Vec::new();
        let wght = Tag::from_bytes(b"wght");
        for data in files {
            for index in 0..ttf_parser::fonts_in_collection(data).unwrap_or(1) {
                let (Some(regular), Some(mut bold)) = (Face::from_slice(data, index), Face::from_slice(data, index)) else { continue };
                if bold.variation_axes().into_iter().any(|axis| axis.tag == wght) {
                    bold.set_variations(&[Variation { tag: wght, value: 700.0 }]);
                }
                fonts.push(Font { family: family(&regular), italic: regular.is_italic(), regular, bold });
            }
        }
        let order = |family: Family| {
            let mut order: Vec<u16> = (0..fonts.len() as u16).collect();
            order.sort_by_key(|&i| {
                let font: &Font = &fonts[usize::from(i)];
                (font.family != family.name() || font.italic, font.italic, font.family.contains("Emoji"))
            });
            order
        };
        let orders = [order(Family::Sans), order(Family::Mono)];
        Self { fonts, orders }
    }

    fn face(&self, font: u16, bold: bool) -> &Face<'static> {
        let font = &self.fonts[usize::from(font)];
        if bold { &font.bold } else { &font.regular }
    }

    /// The fonts a character of `family` is looked for in: the family's upright ones, then the
    /// others in their order (upright before slanted, emoji last).
    fn order(&self, family: Family) -> &[u16] {
        &self.orders[family as usize]
    }

    /// `text` (a line) in `family` at `size` points, bold or not, its digits of one width or not:
    /// its glyphs, placed.
    pub(crate) fn line(&self, text: &str, family: Family, size: f32, bold: bool, tabular: bool) -> Line {
        let order = self.order(family);
        let features = [Feature::new(Tag::from_bytes(b"tnum"), 1, ..)];
        let features = if tabular { &features[..] } else { &[] };
        let mut glyphs = Vec::new();
        let mut x = 0.0;
        // its runs of one direction, in the order they are read (Unicode's bidirectional
        // algorithm, the line left to right, as Typst sets an English document's); in each, its
        // pieces of one font
        let bidi = unicode_bidi::BidiInfo::new(text, Some(unicode_bidi::Level::ltr()));
        for paragraph in &bidi.paragraphs {
            let (levels, runs) = bidi.visual_runs(paragraph, paragraph.range.clone());
            for run in runs {
                let rtl = levels[run.start].is_rtl();
                let mut pieces = self.pieces(&text[run.clone()], order);
                if rtl {
                    pieces.reverse();
                }
                for (font, range) in pieces {
                    let face = self.face(font, bold);
                    let mut buffer = UnicodeBuffer::new();
                    buffer.push_str(&text[run.start + range.start..run.start + range.end]);
                    buffer.set_direction(if rtl { Direction::RightToLeft } else { Direction::LeftToRight });
                    buffer.guess_segment_properties();
                    let shaped = rustybuzz::shape(face, features, buffer);
                    let scale = size / face.units_per_em() as f32;
                    for (info, at) in shaped.glyph_infos().iter().zip(shaped.glyph_positions()) {
                        glyphs.push(Glyph { font, bold, id: info.glyph_id as u16, x: x + at.x_offset as f32 * scale, y: at.y_offset as f32 * scale, scale });
                        x += at.x_advance as f32 * scale;
                    }
                }
            }
        }
        Line { glyphs, width: x }
    }

    /// `text`'s pieces of one font: each grapheme in the first font of `order` that has all its
    /// characters (else the first's, which draws what it lacks as its .notdef).
    fn pieces(&self, text: &str, order: &[u16]) -> Vec<(u16, std::ops::Range<usize>)> {
        let mut pieces: Vec<(u16, std::ops::Range<usize>)> = Vec::new();
        for (at, grapheme) in text.grapheme_indices(true) {
            let has = |&&font: &&u16| grapheme.chars().all(|c| c.is_control() || self.face(font, false).glyph_index(c).is_some());
            let font = order.iter().find(has).or(order.first()).copied().unwrap_or(0);
            match pieces.last_mut() {
                Some((last, range)) if *last == font => range.end = at + grapheme.len(),
                _ => pieces.push((font, at..at + grapheme.len())),
            }
        }
        pieces
    }

    /// A glyph's outline: cubic points (font units, y up), four per curve, each contour closed.
    pub(crate) fn outline(&self, font: u16, bold: bool, id: u16) -> Vec<[f64; 3]> {
        let mut pen = Pen { points: Vec::new(), at: [0.0; 2], start: [0.0; 2] };
        self.face(font, bold).outline_glyph(GlyphId(id), &mut pen);
        pen.points
    }
}

/// A glyph's outline as cubic points: lines and TrueType's quadratics raised to cubics.
struct Pen {
    points: Vec<[f64; 3]>,
    at: [f64; 2],
    start: [f64; 2],
}

impl Pen {
    fn cubic(&mut self, a: [f64; 2], b: [f64; 2], to: [f64; 2]) {
        let from = self.at;
        self.points.extend([from, a, b, to].map(|p| [p[0], p[1], 0.0]));
        self.at = to;
    }

    fn line(&mut self, to: [f64; 2]) {
        let from = self.at;
        let third = |k: f64| [from[0] + k * (to[0] - from[0]), from[1] + k * (to[1] - from[1])];
        self.cubic(third(1.0 / 3.0), third(2.0 / 3.0), to);
    }
}

impl ttf_parser::OutlineBuilder for Pen {
    fn move_to(&mut self, x: f32, y: f32) {
        self.at = [f64::from(x), f64::from(y)];
        self.start = self.at;
    }
    fn line_to(&mut self, x: f32, y: f32) {
        self.line([f64::from(x), f64::from(y)]);
    }
    fn quad_to(&mut self, x1: f32, y1: f32, x: f32, y: f32) {
        let (c, to) = ([f64::from(x1), f64::from(y1)], [f64::from(x), f64::from(y)]);
        let from = self.at;
        let third = |p: [f64; 2]| [p[0] + 2.0 / 3.0 * (c[0] - p[0]), p[1] + 2.0 / 3.0 * (c[1] - p[1])];
        self.cubic(third(from), third(to), to);
    }
    fn curve_to(&mut self, x1: f32, y1: f32, x2: f32, y2: f32, x: f32, y: f32) {
        self.cubic([f64::from(x1), f64::from(y1)], [f64::from(x2), f64::from(y2)], [f64::from(x), f64::from(y)]);
    }
    fn close(&mut self) {
        if self.at != self.start {
            self.line(self.start);
        }
    }
}

#[cfg(all(test, feature = "typeset"))]
mod tests {
    use super::*;

    /// ManimGX's fonts, in the repository.
    const FONTS: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../fonts/manimgx-fonts/src/manimgx_fonts");

    /// A line's glyphs, left to right: id, x and y (points, from the first's), points per unit.
    type Glyphs = Vec<(u16, f32, f32, f32)>;

    fn placed(mut glyphs: Glyphs) -> Glyphs {
        glyphs.sort_by(|a, b| a.1.total_cmp(&b.1));
        let (x0, y0) = glyphs.first().map_or((0.0, 0.0), |g| (g.1, g.2));
        glyphs.into_iter().map(|(id, x, y, s)| (id, x - x0, y - y0, s)).collect()
    }

    /// `text` set by Typst, at 13 points.
    fn typst(text: &str, family: Family, bold: bool, tabular: bool) -> Glyphs {
        let style = format!("font: \"{}\", size: 13pt, weight: \"{}\", number-width: {}", family.name(), if bold { "bold" } else { "regular" }, if tabular { "\"tabular\"" } else { "auto" });
        let source = format!("#set page(width: auto, height: auto, margin: 0pt)\n#set text({style})\n#\"{}\"", text.replace('\\', "\\\\").replace('"', "\\\""));
        let (rows, ..) = crate::typeset::typeset(source, &[FONTS.into()], None, 0).expect("Typst sets it");
        placed(rows.chunks_exact(23).filter(|r| r[0] == 0.0).map(|r| ((r[1] as u64 % 65536) as u16, r[6] as f32, r[7] as f32, r[2] as f32)).collect())
    }

    #[test]
    fn a_line_is_set_as_typst_sets_it() {
        let fonts = Fonts::new(crate::typeset::face_fonts(&[FONTS.into()]));
        let lines = [
            ("0:01.2 / 0:04.0", Family::Sans, false, true),
            ("Line 14 · 0:02.4", Family::Sans, false, true),
            ("AVATAR Typography: fi fl ffi", Family::Sans, false, false),
            ("Sound 45% « 10 s » 1.25×", Family::Sans, false, true),
            ("• مرحبا والنهاية", Family::Sans, false, true),
            ("Space   k", Family::Sans, true, false),
            ("  File \"scene.py\", line 3, in construct", Family::Mono, false, false),
        ];
        for (text, family, bold, tabular) in lines {
            let line = fonts.line(text, family, 13.0, bold, tabular);
            let ours = placed(line.glyphs.iter().map(|g| (g.id, g.x, g.y, g.scale)).collect());
            let theirs = typst(text, family, bold, tabular);
            let same = ours.len() == theirs.len() && ours.iter().zip(&theirs).all(|(o, t)| o.0 == t.0 && (o.1 - t.1).abs() < 1e-3 && (o.2 - t.2).abs() < 1e-3 && (o.3 - t.3).abs() < 1e-6);
            assert!(same && !ours.is_empty(), "{text:?}:\n ours  {ours:?}\n Typst {theirs:?}");
        }
    }
}
