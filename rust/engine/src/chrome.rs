//! The player's face, drawn by the engine itself: its controls as shapes and its text in ManimGX's
//! fonts (see `text`), records of a 2D view in points (y up, from the bottom left) over a clear
//! background, laid over the film. So they are drawn as a film is, exactly, and need no toolkit: a
//! `Face` (what the player shows) in, a picture out, and where its controls are.

use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use crate::render::{Frame, Gpu, Mat34, Player, Record, VIEW_LENGTH};
use crate::text::{Family, Fonts, Line};

/// The shapes every control is made of, uploaded once: a unit square, a unit disk, a triangle.
const SQUARE: u64 = 1;
const DISK: u64 = 2;
const TRIANGLE: u64 = 3;
/// A glyph's upload key: its font, weight and id, apart from the shapes'.
const GLYPH: u64 = 1 << 62;

const BLUE: [f32; 4] = [0.345, 0.769, 0.867, 1.0]; // manim's BLUE_C
const WHITE: [f32; 4] = [1.0; 4];
const DIM: [f32; 4] = [1.0, 1.0, 1.0, 0.55];

/// What the player shows: the face's state, as the player has it.
pub(crate) struct Face {
    pub(crate) size: (f32, f32), // points
    pub(crate) time: f64,
    pub(crate) duration: f64, // made so far, until the take ends
    pub(crate) made: f64,     // the last frame made (where playing waits)
    pub(crate) playing: bool,
    pub(crate) controls: bool, // the controls show
    pub(crate) chapters: Vec<(f64, f64, String)>,
    pub(crate) hover: Option<f64>, // the pointer over the timeline, at this time
    pub(crate) rate: f64,
    pub(crate) captions: Option<bool>, // the take has captions: shown or not
    pub(crate) said: Vec<String>,      // what is said now, if shown
    pub(crate) sound: Option<bool>,    // the take has sound: muted or not
    pub(crate) scenes: bool,           // the file has other scenes
    pub(crate) fullscreen: bool,
    pub(crate) flash: Option<String>,  // what was just done
    pub(crate) status: Option<String>, // no picture yet: what the player waits for
    pub(crate) error: Option<String>,
    pub(crate) help: bool,
    pub(crate) mac: bool, // a Mac's keys (Option, not Ctrl)
}

/// A control of the face: what is there to point at.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum Control {
    Timeline,
    Toggle,
    Next,
    Mute,
    Captions,
    Fullscreen,
}

/// The keys, as the help lists them (the chapters' key, `{}`: Option on a Mac, Ctrl elsewhere).
const KEYS: [(&str, &str); 14] = [
    ("Space   k", "play, pause"),
    ("←   →", "5 seconds back, on"),
    ("j   l", "10 seconds back, on"),
    (",   .", "a frame back, on (paused)"),
    ("{}  ←   →", "the play before, after"),
    ("0  …  9", "a tenth of the way in"),
    ("Home   End", "the start, the end"),
    ("<   >", "slower, faster"),
    ("↑   ↓", "louder, quieter"),
    ("m", "mute"),
    ("c", "captions"),
    ("f", "full screen"),
    ("N   P", "the file's next, previous scene"),
    ("?", "these keys"),
];

/// A text set: its glyphs (upload key, curves, placement from font units to points, y up, from
/// its first baseline's start), and its extent from there: left, right, top, bottom.
pub(crate) struct Label {
    glyphs: Vec<(u64, u32, [f32; 6])>,
    pub(crate) bounds: [f32; 4],
}

impl Label {
    pub(crate) fn width(&self) -> f32 {
        self.bounds[1] - self.bounds[0]
    }
}

pub(crate) struct Chrome {
    pub(crate) player: Player,
    fonts: Rc<Fonts>,
    labels: HashMap<String, Rc<Label>>, // those the last layouts drew
    breaks: HashMap<String, Rc<Vec<String>>>, // the lines of the captions they drew
    used: HashSet<String>,              // those this layout draws
    curves: HashMap<u64, u32>,          // the paths uploaded: their curves
    records: Vec<Record>,
    zones: Vec<([f32; 4], Control)>, // where the controls laid out are (points: x0, y0, x1, y1)
    pub(crate) scale: f32,           // pixels per point
}

/// `a` then `b` (affine maps as six numbers: x' = a·x + c·y + e, y' = b·x + d·y + f).
fn then(a: [f32; 6], b: [f32; 6]) -> [f32; 6] {
    [
        b[0] * a[0] + b[2] * a[1],
        b[1] * a[0] + b[3] * a[1],
        b[0] * a[2] + b[2] * a[3],
        b[1] * a[2] + b[3] * a[3],
        b[0] * a[4] + b[2] * a[5] + b[4],
        b[1] * a[4] + b[3] * a[5] + b[5],
    ]
}

fn matrix([a, b, c, d, e, f]: [f32; 6]) -> Mat34 {
    [[a, c, 0.0, e], [b, d, 0.0, f], [0.0, 0.0, 1.0, 0.0]]
}

/// A path as the player takes it, from cubic points (x, y, z; four per curve): its subpaths
/// broken where a curve does not start where the last ended, closed where one ends where it
/// began; and the centroid and Newell area vector of its control points.
fn path(points: &[[f64; 3]]) -> (Vec<u8>, Vec<u8>, [f32; 6]) {
    let curves = points.len() / 4;
    let near = |p: [f64; 3], q: [f64; 3]| (p[0] - q[0]).abs() < 1e-6 && (p[1] - q[1]).abs() < 1e-6;
    let mut subpaths: Vec<[u32; 4]> = Vec::new();
    let mut start = 0;
    for i in 1..=curves {
        if i == curves || !near(points[4 * i], points[4 * i - 1]) {
            let closed = near(points[4 * start], points[4 * i - 1]);
            subpaths.push([start as u32, i as u32, closed as u32, 0]);
            start = i;
        }
    }
    let n = points.len().max(1) as f64;
    let centroid = [0, 1, 2].map(|k| points.iter().map(|p| p[k]).sum::<f64>() / n);
    let mut area = [0.0f64; 3];
    for (p, q) in points.iter().zip(points.iter().cycle().skip(1)) {
        area[0] += (p[1] - q[1]) * (p[2] + q[2]);
        area[1] += (p[2] - q[2]) * (p[0] + q[0]);
        area[2] += (p[0] - q[0]) * (p[1] + q[1]);
    }
    let summary = [centroid[0], centroid[1], centroid[2], area[0], area[1], area[2]].map(|x| x as f32);
    (bytemuck::cast_slice(points).to_vec(), bytemuck::cast_slice(&subpaths).to_vec(), summary)
}

/// Cubic points of a polygon's edges (straight curves), closed.
fn polygon(corners: &[[f64; 2]]) -> Vec<[f64; 3]> {
    let mut points = Vec::with_capacity(4 * corners.len());
    for (i, &a) in corners.iter().enumerate() {
        let b = corners[(i + 1) % corners.len()];
        for t in [0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0] {
            points.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), 0.0]);
        }
    }
    points
}

/// Cubic points of the unit circle: four quarter arcs.
fn circle() -> Vec<[f64; 3]> {
    let k = 0.552_284_749_830_793_6; // 4/3 · (√2 − 1)
    let mut points = Vec::new();
    for (c, s) in [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)] {
        // from (c, s) a quarter turn on, to (−s, c): its tangents' handles k long
        points.extend([[c, s, 0.0], [c - k * s, s + k * c, 0.0], [-s + k * c, c + k * s, 0.0], [-s, c, 0.0]]);
    }
    points
}

/// "m:ss.t": a time in minutes, seconds and tenths.
pub(crate) fn stamp(t: f64) -> String {
    let tenths = (t.max(0.0) * 10.0 + 1e-6).floor() as u64;
    format!("{}:{:02}.{}", tenths / 600, tenths / 10 % 60, tenths % 10)
}

impl Chrome {
    pub(crate) fn new(fonts: Rc<Fonts>) -> Self {
        let mut player = Player::new(1, 1, 4);
        let shapes = [(SQUARE, polygon(&[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])), (DISK, circle()), (TRIANGLE, polygon(&[[0.0, 0.0], [1.0, 0.5], [0.0, 1.0]]))];
        let mut curves = HashMap::new();
        for (key, points) in shapes {
            let (data, subpaths, summary) = path(&points);
            player.add_path(key, &data, &subpaths, summary).expect("a control's shape");
            curves.insert(key, (points.len() / 4) as u32);
        }
        Self { player, fonts, labels: HashMap::new(), breaks: HashMap::new(), used: HashSet::new(), curves, records: Vec::new(), zones: Vec::new(), scale: 1.0 }
    }

    /// Shape `key` placed by `m` (points), in `rgba`.
    fn shape(&mut self, key: u64, m: [f32; 6], rgba: [f32; 4]) {
        let s = self.scale;
        self.records.push(Record::filled(key, self.curves[&key], matrix(then(m, [s, 0.0, 0.0, s, 0.0, 0.0])), rgba));
    }

    fn rect(&mut self, x: f32, y: f32, w: f32, h: f32, rgba: [f32; 4]) {
        self.shape(SQUARE, [w, 0.0, 0.0, h, x, y], rgba);
    }

    fn disk(&mut self, x: f32, y: f32, r: f32, rgba: [f32; 4]) {
        self.shape(DISK, [r, 0.0, 0.0, r, x, y], rgba);
    }

    /// A triangle in the box (x, y, w, h) pointing right (w < 0: left).
    fn triangle(&mut self, x: f32, y: f32, w: f32, h: f32, rgba: [f32; 4]) {
        self.shape(TRIANGLE, [w, 0.0, 0.0, h, x, y], rgba);
    }

    /// The control at (x, y) points, as the last layout placed them.
    pub(crate) fn control(&self, x: f32, y: f32) -> Option<Control> {
        self.zones.iter().rev().find(|(r, _)| (r[0]..r[2]).contains(&x) && (r[1]..r[3]).contains(&y)).map(|(_, c)| *c)
    }

    /// The label of `lines` (each placed at its offset, points), set once and kept while the
    /// layouts draw it, under `name`.
    fn label(&mut self, name: String, lines: impl FnOnce(&Fonts) -> Vec<(Line, f32, f32, f32)>) -> Result<Rc<Label>, String> {
        self.used.insert(name.clone());
        if let Some(label) = self.labels.get(&name) {
            return Ok(label.clone());
        }
        let mut glyphs = Vec::new();
        let mut bounds = [f32::MAX, f32::MIN, f32::MIN, f32::MAX];
        for (line, x, y, size) in lines(&self.fonts) {
            bounds = [bounds[0].min(x), bounds[1].max(x + line.width), bounds[2].max(y + 0.75 * size), bounds[3].min(y - 0.25 * size)];
            for g in &line.glyphs {
                let key = GLYPH | u64::from(g.font) << 17 | u64::from(g.bold) << 16 | u64::from(g.id);
                if !self.curves.contains_key(&key) {
                    let points = self.fonts.outline(g.font, g.bold, g.id);
                    self.curves.insert(key, (points.len() / 4) as u32);
                    if !points.is_empty() {
                        let (data, subpaths, summary) = path(&points);
                        self.player.add_path(key, &data, &subpaths, summary)?;
                    }
                }
                // a space has no outline
                if self.curves[&key] > 0 {
                    glyphs.push((key, self.curves[&key], [g.scale, 0.0, 0.0, g.scale, x + g.x, y + g.y]));
                }
            }
        }
        if bounds[0] > bounds[1] {
            bounds = [0.0; 4];
        }
        let label = Rc::new(Label { glyphs, bounds });
        self.labels.insert(name, label.clone());
        Ok(label)
    }

    /// `text`, a line in Noto Sans at `size` points (its digits all one width).
    fn sans(&mut self, size: f32, text: &str) -> Result<Rc<Label>, String> {
        self.label(format!("sans {size} {text}"), |fonts| vec![(fonts.line(text, Family::Sans, size, false, true), 0.0, 0.0, size)])
    }

    /// `text` as it is, its lines and spaces, in DejaVu Sans Mono at `size` points.
    fn mono(&mut self, size: f32, text: &str) -> Result<Rc<Label>, String> {
        self.label(format!("mono {size} {text}"), |fonts| {
            let lead = 1.45 * size;
            text.lines().enumerate().map(|(i, line)| (fonts.line(&line.replace('\t', "    "), Family::Mono, size, false, false), 0.0, -lead * i as f32, size)).collect()
        })
    }

    /// `text` in lines no wider than `width` points (broken between words), in Noto Sans: its
    /// breaks found once, and kept while the layouts draw them.
    fn wrapped(&mut self, size: f32, text: &str, width: f32) -> Result<Vec<Rc<Label>>, String> {
        let name = format!("wrap {size} {width} {text}");
        self.used.insert(name.clone());
        let fonts = &self.fonts;
        let lines = self
            .breaks
            .entry(name)
            .or_insert_with(|| {
                let mut lines = Vec::new();
                for paragraph in text.lines() {
                    let mut line = String::new();
                    for word in paragraph.split(' ') {
                        let longer = if line.is_empty() { word.to_owned() } else { format!("{line} {word}") };
                        if !line.is_empty() && fonts.line(&longer, Family::Sans, size, false, true).width > width {
                            lines.push(std::mem::replace(&mut line, word.to_owned()));
                        } else {
                            line = longer;
                        }
                    }
                    lines.push(line);
                }
                Rc::new(lines)
            })
            .clone();
        lines.iter().map(|line| self.sans(size, line)).collect()
    }

    /// The keys, as a table: each key bold and to the right, what it does to the left.
    fn keys(&mut self, mac: bool) -> Result<Rc<Label>, String> {
        let chapter = if mac { "Option" } else { "Ctrl" };
        self.label(format!("keys {mac}"), |fonts| {
            let (size, row, gap) = (13.0, 21.0, 16.0);
            let keys: Vec<Line> = KEYS.iter().map(|(k, _)| fonts.line(&k.replace("{}", chapter), Family::Sans, size, true, false)).collect();
            let column = keys.iter().map(|l| l.width).fold(0.0, f32::max);
            let mut lines = Vec::new();
            for (i, (key, (_, what))) in keys.into_iter().zip(KEYS).enumerate() {
                let y = -row * i as f32;
                lines.push((fonts.line(what, Family::Sans, size, false, false), column + gap, y, size));
                let x = column - key.width;
                lines.push((key, x, y, size));
            }
            lines
        })
    }

    /// Draw `label` with its first baseline starting at (x, y) (points), in `rgba`.
    fn text(&mut self, label: &Label, x: f32, y: f32, rgba: [f32; 4]) {
        let s = self.scale;
        let to_pixels = [s, 0.0, 0.0, s, x * s, y * s];
        for &(key, curves, placement) in &label.glyphs {
            self.records.push(Record::filled(key, curves, matrix(then(placement, to_pixels)), rgba));
        }
    }

    /// Lay out `face`: the records to draw, and where its controls are. Whether there is anything
    /// over the film.
    pub(crate) fn lay_out(&mut self, face: &Face) -> Result<bool, String> {
        self.records.clear();
        self.zones.clear();
        self.used.clear();
        self.draw(face)?;
        // the texts it no longer draws go (a time shown once is not kept)
        let used = &self.used;
        self.labels.retain(|name, _| used.contains(name));
        self.breaks.retain(|name, _| used.contains(name));
        Ok(!self.records.is_empty())
    }

    fn draw(&mut self, face: &Face) -> Result<(), String> {
        let (w, h) = face.size;
        if let Some(status) = &face.status {
            let label = self.sans(15.0, status)?;
            self.text(&label, (w - label.width()) / 2.0, h / 2.0, [1.0, 1.0, 1.0, 0.7]);
        }
        if face.controls {
            self.controls(face)?;
        }
        // what is said now, over the picture, above the controls when they show
        let mut y = if face.controls { 76.0 } else { 24.0 };
        for said in face.said.iter().rev() {
            for label in self.wrapped(20.0, said, w - 64.0)?.iter().rev() {
                let x = (w - label.width()) / 2.0;
                self.rect(x - 8.0, y - 8.0, label.width() + 16.0, 32.0, [0.03, 0.03, 0.03, 0.75]);
                self.text(label, x, y, WHITE);
                y += 36.0;
            }
        }
        if let Some(flash) = &face.flash {
            let label = self.sans(18.0, flash)?;
            let x = (w - label.width()) / 2.0;
            self.rect(x - 14.0, h * 0.86 - 12.0, label.width() + 28.0, 40.0, [0.0, 0.0, 0.0, 0.55]);
            self.text(&label, x, h * 0.86, WHITE);
        }
        if let Some(error) = &face.error {
            // the scene's error, over its last good picture
            self.rect(0.0, 0.0, w, h, [0.08, 0.0, 0.0, 0.82]);
            let label = self.mono(12.0, error)?;
            self.text(&label, 20.0, h - 28.0, [1.0, 0.706, 0.706, 1.0]);
        }
        if face.help {
            let label = self.keys(face.mac)?;
            let (bw, bh) = (label.width() + 48.0, label.bounds[2] - label.bounds[3] + 36.0);
            let (x, y) = ((w - bw) / 2.0, (h - bh) / 2.0);
            self.rect(x, y, bw, bh, [0.13, 0.13, 0.13, 0.95]);
            self.text(&label, x + 24.0 - label.bounds[0], y + bh - 18.0 - label.bounds[2], WHITE);
        }
        Ok(())
    }

    /// The controls: a shade; the timeline in chapters (made, played); play or pause, the next
    /// scene, the sound, the time, the chapter; the rate, the captions, full screen; over the
    /// timeline, the time there.
    fn controls(&mut self, face: &Face) -> Result<(), String> {
        let (w, _) = face.size;
        for k in 0..16 {
            let a = 0.6 * (1.0 - k as f32 / 16.0).powi(2);
            self.rect(0.0, 5.0 * k as f32, w, 5.0, [0.0, 0.0, 0.0, a]);
        }
        let (left, right, height) = timeline(face.size);
        self.zones.push(([left - 6.0, height - 10.0, right + 6.0, height + 10.0], Control::Timeline));
        let x = |s: f64| left + (right - left) * if face.duration > 0.0 { (s / face.duration) as f32 } else { 0.0 };
        let thick = if face.hover.is_some() { 5.0 } else { 3.0 };
        let spans: Vec<(f64, f64)> = if face.chapters.len() > 1 { face.chapters.iter().map(|c| (c.0, c.1)).collect() } else { vec![(0.0, face.duration)] };
        for (a, b) in spans {
            let (x0, x1) = (x(a) + if a > 0.0 { 1.0 } else { 0.0 }, x(b) - if b < face.duration { 1.0 } else { 0.0 });
            if x1 <= x0 {
                continue;
            }
            let y = height - thick / 2.0;
            self.rect(x0, y, x1 - x0, thick, [1.0, 1.0, 1.0, 0.3]);
            let made = x(face.made.clamp(a, b)).min(x1);
            if made > x0 {
                self.rect(x0, y, made - x0, thick, [1.0, 1.0, 1.0, 0.25]);
            }
            let played = x(face.time.clamp(a, b)).min(x1);
            if played > x0 {
                self.rect(x0, y, played - x0, thick, BLUE);
            }
        }
        if face.hover.is_some() {
            self.disk(x(face.time), height, 6.5, BLUE);
        }
        // the row, a button's place 32 points square each, from the left
        let mut at = 6.0;
        let mut button = |chrome: &mut Chrome, control: Control| {
            chrome.zones.push(([at, 5.0, at + 32.0, 37.0], control));
            at += 32.0;
            at - 32.0
        };
        let b = button(self, Control::Toggle);
        if face.playing {
            self.rect(b + 10.0, 14.0, 4.0, 14.0, WHITE);
            self.rect(b + 18.0, 14.0, 4.0, 14.0, WHITE);
        } else {
            self.triangle(b + 10.0, 14.0, 13.0, 14.0, WHITE);
        }
        if face.scenes {
            let b = button(self, Control::Next);
            self.triangle(b + 9.0, 15.0, 10.0, 12.0, WHITE);
            self.rect(b + 20.0, 15.0, 2.5, 12.0, WHITE);
        }
        if let Some(muted) = face.sound {
            let b = button(self, Control::Mute);
            self.rect(b + 8.0, 17.5, 4.0, 7.0, WHITE);
            self.triangle(b + 18.0, 13.0, -9.0, 16.0, WHITE);
            if muted {
                let (c, s) = (std::f32::consts::FRAC_1_SQRT_2, std::f32::consts::FRAC_1_SQRT_2);
                // a stroke across it, 2 by 18 points, turned an eighth
                self.shape(SQUARE, [2.0 * c, 2.0 * s, -18.0 * s, 18.0 * c, b + 22.0, 14.0], WHITE);
            } else {
                self.rect(b + 20.5, 18.0, 2.0, 6.0, DIM);
                self.rect(b + 24.0, 16.0, 2.0, 10.0, DIM);
            }
        }
        let label = self.sans(13.0, &format!("{} / {}", stamp(face.time), stamp(face.duration)))?;
        let after = at + 8.0;
        self.text(&label, after, 16.0, WHITE);
        let chapter = face.chapters.iter().rev().find(|c| c.0 <= face.time + 1e-6);
        if let Some((_, _, title)) = chapter {
            let title = self.sans(13.0, &format!("• {title}"))?;
            self.text(&title, after + label.width() + 14.0, 16.0, [1.0, 1.0, 1.0, 0.85]);
        }
        // from the right
        let mut edge = w - 6.0;
        let mut button = |chrome: &mut Chrome, control: Control| {
            edge -= 32.0;
            chrome.zones.push(([edge, 5.0, edge + 32.0, 37.0], control));
            edge
        };
        let b = button(self, Control::Fullscreen);
        // four corners of a 14-point square, each two arms 5 long and 2 thick: their angle at the
        // square's corner (at a point inside it, its arms out to the edges, when full screen)
        let (arm, thick) = (5.0, 2.0);
        let bar = |chrome: &mut Chrome, (x0, y0): (f32, f32), (x1, y1): (f32, f32)| chrome.rect(x0.min(x1), y0.min(y1), (x1 - x0).abs(), (y1 - y0).abs(), WHITE);
        for (cx, cy, sx, sy) in [(b + 9.0, 14.0, 1.0, 1.0), (b + 23.0, 14.0, -1.0, 1.0), (b + 9.0, 28.0, 1.0, -1.0), (b + 23.0, 28.0, -1.0, -1.0)] {
            let (vx, vy, out) = if face.fullscreen { (cx + sx * arm, cy + sy * arm, -1.0) } else { (cx, cy, 1.0) };
            bar(self, (vx, vy), (vx + out * sx * arm, vy + out * sy * thick));
            bar(self, (vx, vy), (vx + out * sx * thick, vy + out * sy * arm));
        }
        if let Some(on) = face.captions {
            let b = button(self, Control::Captions);
            let label = self.label("cc".into(), |fonts| vec![(fonts.line("CC", Family::Sans, 12.0, true, false), 0.0, 0.0, 12.0)])?;
            self.text(&label, b + (32.0 - label.width()) / 2.0, 16.5, if on { BLUE } else { DIM });
        }
        if (face.rate - 1.0).abs() > 1e-9 {
            let label = self.sans(13.0, &format!("{}×", face.rate))?;
            self.text(&label, edge - 6.0 - label.width(), 16.0, WHITE);
        }
        if let Some(at) = face.hover {
            let title = face.chapters.iter().rev().find(|c| c.0 <= at + 1e-6).filter(|_| face.chapters.len() > 1);
            let words = title.map_or_else(|| stamp(at), |c| format!("{} · {}", c.2, stamp(at)));
            let label = self.sans(12.0, &words)?;
            let lx = (x(at) - label.width() / 2.0).min(w - label.width() - 10.0).max(10.0);
            self.rect(lx - 6.0, height + 12.0, label.width() + 12.0, 22.0, [0.0, 0.0, 0.0, 0.7]);
            self.text(&label, lx, height + 18.0, WHITE);
        }
        Ok(())
    }

    /// Draw what was laid out at `size` (pixels) into the chrome's frame: the commands.
    pub(crate) fn encode(&mut self, gpu: &mut Gpu, size: (u32, u32)) -> Result<wgpu::CommandEncoder, String> {
        if (self.player.width, self.player.height) != size {
            (self.player.width, self.player.height, self.player.targets) = (size.0, size.1, None);
        }
        let (w, h) = (size.0 as f32, size.1 as f32);
        // pixels, y up: x ∈ [0, w] → [−1, 1], y ∈ [0, h] → [−1, 1] (WGSL: column-major); a
        // clear background
        let mut view = vec![0.0f32; VIEW_LENGTH];
        let projection = [[2.0 / w, 0.0, 0.0, -1.0], [0.0, 2.0 / h, 0.0, -1.0], [0.0, 0.0, 0.0, 0.5], [0.0, 0.0, 0.0, 1.0]];
        for (r, row) in projection.iter().enumerate() {
            for (c, value) in row.iter().enumerate() {
                view[c * 4 + r] = *value;
                view[16 + c * 4 + r] = *value;
            }
        }
        view[32..36].copy_from_slice(&[w, h, 1.0, 1.0]);
        view[40..44].copy_from_slice(&[0.0, 0.0, 1.0, 0.0]);
        let frame = Frame { key: 0, width: size.0, height: size.1, view, records: self.records.clone() };
        let (encoder, _, _) = self.player.encode(gpu, &[frame])?;
        Ok(encoder)
    }
}

/// The timeline's place in a face of `size` points: its left and right ends, its height.
pub(crate) fn timeline(size: (f32, f32)) -> (f32, f32, f32) {
    (12.0, size.0 - 12.0, 44.0)
}
