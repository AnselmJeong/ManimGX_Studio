//! The player: ManimGX's, on any screen. A projector of takes (see `project`) on a clock of its
//! own: it plays the takes its director sends, keeps its place when a newer take replaces the one
//! shown, sounds them (`speaker`) and draws its face (`chrome`) over the film; its viewer moves
//! through the film with keys, a pointer, a wheel or a finger.
//!
//! It is the same on every screen. A screen — a window (`window`), a page's canvas (`web`) — gives
//! it a surface, hands on its viewer's input in the web's words (a key's value, a pointer's place
//! in pixels, a wheel's deltas in points), draws when it is due (`wake`), and does what it asks
//! (`asks`: another scene, full screen). Each input says whether the player used it, so that a
//! page lets the rest go by (a scroll, its own keys).
//!
//! Its director's notes (JSON, see `Film`) give it the plays (its chapters), the sections, the
//! captions; between takes, the file's scenes and the scene's error.

use std::collections::HashMap;
use std::rc::Rc;

use serde::Deserialize;
use web_time::{Duration, Instant};

use crate::chrome::{Chrome, Control, Face, timeline};
use crate::project::{self, Note, Projector, Settled};
use crate::render::{Gpu, with_gpu};
use crate::speaker::Sound;
use crate::text::Fonts;

const IDLE: Duration = Duration::from_secs(2); // the controls hide after this, while playing
const FLASH: Duration = Duration::from_millis(700); // what was done shows this long
const COUNTING: Duration = Duration::from_millis(2); // how often a frame's count is looked for
const RATES: [f64; 8] = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0];

/// The film's clock: seconds, held, or running from an instant at a rate.
#[derive(Clone, Copy, PartialEq)]
pub(crate) struct Clock {
    pub(crate) time: f64,
    pub(crate) since: Option<Instant>, // running: the instant `time` was the time
    pub(crate) rate: f64,
}

impl Clock {
    /// The time at `at`.
    pub(crate) fn at(&self, at: Instant) -> f64 {
        self.since.map_or(self.time, |since| self.time + at.saturating_duration_since(since).as_secs_f64() * self.rate)
    }

    fn now(&self) -> f64 {
        self.at(Instant::now())
    }

    fn playing(&self) -> bool {
        self.since.is_some()
    }

    /// Hold the time at `t`, running on from there if playing.
    fn set(&mut self, t: f64) {
        self.time = t;
        self.since = self.since.map(|_| Instant::now());
    }

    fn play(&mut self) {
        self.since.get_or_insert_with(Instant::now);
    }

    fn pause(&mut self) {
        self.time = self.now();
        self.since = None;
    }

    /// Keep it within the film: at its end, it stops there; past its last frame made (or a time
    /// beyond it the clock was set to) while it is being made, it waits there, and runs on once
    /// more is made.
    fn bound(&mut self, made: f64, ended: bool) {
        if !self.playing() || self.now() < made {
            return;
        }
        if ended {
            self.set(made);
            self.pause();
        } else {
            self.time = self.time.max(made);
            self.since = Some(Instant::now());
        }
    }
}

/// A note of the director's, as JSON has it: one of these at a time (see `Film`).
#[derive(Deserialize, Default)]
#[serde(default)]
struct Said {
    scenes: Option<Vec<String>>,
    scene: Option<String>,
    error: Option<Fault>,
    play: Option<Play>,
    section: Option<Section>,
    captions: Option<Vec<Caption>>,
}

#[derive(Deserialize)]
struct Fault {
    message: String,
    trace: Option<String>,
}

#[derive(Deserialize)]
struct Play {
    index: u32,
    start: f64,
    end: f64,
    #[serde(rename = "where")]
    place: Option<(String, u32)>,
}

#[derive(Deserialize)]
struct Section {
    name: String,
    start: f64,
}

#[derive(Deserialize)]
struct Caption {
    start: f64,
    end: f64,
    text: String,
}

/// What the director has said of a take: its plays, sections and captions, its sound.
#[derive(Default)]
struct Notes {
    plays: Vec<Play>,
    sections: Vec<Section>,
    captions: Vec<Caption>,
    sound: Option<Vec<u8>>,
}

impl Notes {
    /// Its chapters, (start, end, title): its sections, if it has several, or else its plays,
    /// each by the line that played it (and its file, when the plays come from several).
    fn chapters(&self, duration: f64) -> Vec<(f64, f64, String)> {
        if self.sections.len() > 1 {
            let ends = self.sections.iter().skip(1).map(|s| s.start).chain([duration]);
            return self.sections.iter().zip(ends).map(|(s, end)| (s.start, end, s.name.clone())).collect();
        }
        let files: std::collections::HashSet<&str> = self.plays.iter().filter_map(|p| p.place.as_ref().map(|w| w.0.as_str())).collect();
        let title = |p: &Play| match &p.place {
            None => format!("Play {}", p.index + 1),
            Some((file, line)) if files.len() > 1 => format!("{}:{line}", file.rsplit(['/', '\\']).next().unwrap_or(file)),
            Some((_, line)) => format!("Line {line}"),
        };
        self.plays.iter().map(|p| (p.start, p.end, title(p))).collect()
    }

    fn take(&mut self, said: Said) {
        if let Some(play) = said.play {
            self.plays.push(play);
        } else if let Some(section) = said.section {
            // the film begins with one; a section with no frame yet gives way to the next
            if self.sections.is_empty() {
                self.sections.push(Section { name: "unnamed".into(), start: 0.0 });
            }
            if self.sections.last().is_some_and(|s| s.start >= section.start) {
                self.sections.pop();
            }
            self.sections.push(section);
        } else if let Some(captions) = said.captions {
            self.captions = captions;
        }
    }
}

/// A screen's surface, and the pass that puts the film and the face on it.
pub(crate) struct Screen {
    surface: wgpu::Surface<'static>,
    config: wgpu::SurfaceConfiguration,
    pipeline: wgpu::RenderPipeline,
    layout: wgpu::BindGroupLayout,
    place: wgpu::Buffer,
    blank: wgpu::TextureView, // no film yet, no face: a texture bound, never read
}

/// What putting a picture on the screen came to.
#[derive(PartialEq, Eq)]
enum Presented {
    Shown,
    Hidden, // the screen is covered: it takes no picture until it shows
    Again,  // its surface was out of date (now made again): draw again
}

const COMPOSITE: &str = r"
@group(0) @binding(0) var film: texture_2d<f32>;
@group(0) @binding(1) var face: texture_2d<f32>;
// the film's rectangle (pixels: x0, y0, x1, y1), and whether there is a face
@group(0) @binding(2) var<uniform> place: array<vec4<f32>, 2>;

@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4<f32> {
    let uv = vec2<f32>(f32((i << 1u) & 2u), f32(i & 2u));
    return vec4<f32>(uv * 2.0 - 1.0, 0.0, 1.0);
}

// the film where it is placed, pixel for pixel (black around it), the face over it: both
// premultiplied
@fragment fn fs(@builtin(position) p: vec4<f32>) -> @location(0) vec4<f32> {
    let xy = vec2<i32>(floor(p.xy));
    let film_at = place[0];
    var color = vec3<f32>(0.0);
    if (p.x >= film_at.x && p.x < film_at.z && p.y >= film_at.y && p.y < film_at.w) {
        color = textureLoad(film, xy - vec2<i32>(film_at.xy), 0).rgb;
    }
    if (place[1].x > 0.5) {
        let over = textureLoad(face, xy, 0);
        color = over.rgb + (1.0 - over.a) * color;
    }
    return vec4<f32>(color, 1.0);
}
";

impl Screen {
    /// A screen of `surface` (a window's, a canvas's) at `size` pixels.
    pub(crate) fn new(gpu: &Gpu, surface: wgpu::Surface<'static>, size: (u32, u32)) -> Result<Self, String> {
        let caps = surface.get_capabilities(&gpu.adapter);
        // the film's bytes as they are (sRGB-encoded): a format that stores them unchanged
        let format = [wgpu::TextureFormat::Bgra8Unorm, wgpu::TextureFormat::Rgba8Unorm].into_iter().find(|f| caps.formats.contains(f)).ok_or("the screen's surface takes no 8-bit format")?;
        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format,
            width: size.0.max(1),
            height: size.1.max(1),
            present_mode: wgpu::PresentMode::Fifo,
            desired_maximum_frame_latency: 2,
            alpha_mode: caps.alpha_modes.first().copied().unwrap_or(wgpu::CompositeAlphaMode::Opaque),
            view_formats: vec![],
            color_space: wgpu::SurfaceColorSpace::Auto,
        };
        surface.configure(&gpu.device, &config);
        let device = &gpu.device;
        let texture = |binding| wgpu::BindGroupLayoutEntry { binding, visibility: wgpu::ShaderStages::FRAGMENT, ty: wgpu::BindingType::Texture { sample_type: wgpu::TextureSampleType::Float { filterable: false }, view_dimension: wgpu::TextureViewDimension::D2, multisampled: false }, count: None };
        let uniform = wgpu::BindGroupLayoutEntry { binding: 2, visibility: wgpu::ShaderStages::FRAGMENT, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None }, count: None };
        let layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor { label: Some("composite"), entries: &[texture(0), texture(1), uniform] });
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: Some("composite"), source: wgpu::ShaderSource::Wgsl(COMPOSITE.into()) });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[Some(&layout)], immediate_size: 0 });
        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("composite"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState { module: &shader, entry_point: Some("vs"), compilation_options: Default::default(), buffers: &[] },
            fragment: Some(wgpu::FragmentState { module: &shader, entry_point: Some("fs"), compilation_options: Default::default(), targets: &[Some(wgpu::ColorTargetState { format, blend: None, write_mask: wgpu::ColorWrites::ALL })] }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview_mask: None,
            cache: None,
        });
        let place = device.create_buffer(&wgpu::BufferDescriptor { label: Some("place"), size: 32, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let blank = device
            .create_texture(&wgpu::TextureDescriptor { label: Some("blank"), size: wgpu::Extent3d { width: 1, height: 1, depth_or_array_layers: 1 }, mip_level_count: 1, sample_count: 1, dimension: wgpu::TextureDimension::D2, format: crate::render::COLOR, usage: wgpu::TextureUsages::TEXTURE_BINDING, view_formats: &[] })
            .create_view(&Default::default());
        Ok(Self { surface, config, pipeline, layout, place, blank })
    }

    fn size(&self) -> (u32, u32) {
        (self.config.width, self.config.height)
    }

    fn resize(&mut self, gpu: &Gpu, (width, height): (u32, u32)) {
        (self.config.width, self.config.height) = (width.max(1), height.max(1));
        self.surface.configure(&gpu.device, &self.config);
    }

    /// The commands that put the film (at `place`, pixels) and the face over it into `view`.
    fn composite(&self, gpu: &Gpu, view: &wgpu::TextureView, film: Option<&wgpu::TextureView>, face: Option<&wgpu::TextureView>, place: [f32; 4]) -> wgpu::CommandEncoder {
        let flags = [f32::from(u8::from(face.is_some())), 0.0, 0.0, 0.0];
        gpu.queue.write_buffer(&self.place, 0, bytemuck::cast_slice(&[place, flags]));
        let group = gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("composite"),
            layout: &self.layout,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: wgpu::BindingResource::TextureView(film.unwrap_or(&self.blank)) },
                wgpu::BindGroupEntry { binding: 1, resource: wgpu::BindingResource::TextureView(face.unwrap_or(&self.blank)) },
                wgpu::BindGroupEntry { binding: 2, resource: self.place.as_entire_binding() },
            ],
        });
        let mut encoder = gpu.device.create_command_encoder(&Default::default());
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("composite"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment { view, depth_slice: None, resolve_target: None, ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::BLACK), store: wgpu::StoreOp::Store } })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
                multiview_mask: None,
            });
            pass.set_pipeline(&self.pipeline);
            pass.set_bind_group(0, &group, &[]);
            pass.draw(0..3, 0..1);
        }
        encoder
    }

    /// Put the film (at `place`, pixels) and the face over it on the screen; `presenting` just
    /// before it is presented.
    fn present(&mut self, gpu: &Gpu, film: Option<&wgpu::TextureView>, face: Option<&wgpu::TextureView>, place: [f32; 4], presenting: impl FnOnce()) -> Presented {
        let texture = match self.surface.get_current_texture() {
            wgpu::CurrentSurfaceTexture::Success(t) | wgpu::CurrentSurfaceTexture::Suboptimal(t) => t,
            wgpu::CurrentSurfaceTexture::Occluded => return Presented::Hidden,
            wgpu::CurrentSurfaceTexture::Outdated | wgpu::CurrentSurfaceTexture::Lost => {
                self.surface.configure(&gpu.device, &self.config);
                return Presented::Again;
            }
            _ => return Presented::Again,
        };
        let encoder = self.composite(gpu, &texture.texture.create_view(&Default::default()), film, face, place);
        gpu.queue.submit(Some(encoder.finish()));
        presenting();
        gpu.queue.present(texture);
        Presented::Shown
    }
}

/// Keys held with a key: Control, Alt (Option on a Mac) and Meta (Command on a Mac); Shift is in
/// the key's value.
#[derive(Clone, Copy, Default)]
pub(crate) struct Modifiers {
    pub(crate) ctrl: bool,
    pub(crate) alt: bool,
    pub(crate) meta: bool,
}

/// What the viewer can do, by a key or a control of the face.
#[derive(Clone, Copy, PartialEq, Debug)]
enum Act {
    Toggle,
    Jump(f64),  // seconds back (−) or on
    Frame(f64), // a frame back (−1) or on, paused
    Chapter(isize),
    Tenth(u8),
    Start,
    End,
    Rate(isize),
    Volume(f32), // twentieths up, or down
    Mute,
    Captions,
    Fullscreen,
    Help,
    Scene(isize), // the file's next scene, or the one before
    Back,         // the keys' list closes, or full screen ends
}

/// What key `key` does (its value, as the web names it): the film playing or not, something open
/// that Escape closes (the keys' list, full screen) or not, on a Mac or not. None: the key is the
/// page's, or the system's (held with Control, Alt or Meta: but an arrow with Option on a Mac,
/// with Control elsewhere, goes to the next play or the one before; Alt with an arrow is the
/// browser's Back and Forward there).
fn keyed(key: &str, m: Modifiers, playing: bool, open: bool, mac: bool) -> Option<Act> {
    let chapter = if mac { m.alt && !m.ctrl } else { m.ctrl && !m.alt } && !m.meta;
    Some(match key {
        "ArrowLeft" if chapter => Act::Chapter(-1),
        "ArrowRight" if chapter => Act::Chapter(1),
        _ if m.ctrl || m.alt || m.meta => return None,
        " " | "k" | "K" => Act::Toggle,
        "ArrowLeft" => Act::Jump(-5.0),
        "ArrowRight" => Act::Jump(5.0),
        "j" | "J" => Act::Jump(-10.0),
        "l" | "L" => Act::Jump(10.0),
        "," if !playing => Act::Frame(-1.0),
        "." if !playing => Act::Frame(1.0),
        "<" => Act::Rate(-1),
        ">" => Act::Rate(1),
        "ArrowUp" => Act::Volume(1.0),
        "ArrowDown" => Act::Volume(-1.0),
        "Home" => Act::Start,
        "End" => Act::End,
        "m" | "M" => Act::Mute,
        "c" | "C" => Act::Captions,
        "f" | "F" => Act::Fullscreen,
        "?" => Act::Help,
        "n" | "N" => Act::Scene(1),
        "p" | "P" => Act::Scene(-1),
        "Escape" if open => Act::Back,
        digit if digit.len() == 1 && digit.as_bytes()[0].is_ascii_digit() => Act::Tenth(digit.as_bytes()[0] - b'0'),
        _ => return None,
    })
}

/// What the player asks of its screen.
#[derive(Debug, PartialEq)]
pub(crate) enum Ask {
    Scene(String),    // its director runs the file's scene of this name
    Fullscreen(bool), // full screen, or not
}

/// When the player is to be drawn again.
#[derive(Debug, PartialEq)]
pub(crate) enum Wake {
    Now, // at the screen's next refresh
    At(Instant),
    Idle, // when something happens
}

/// The cursor over the player.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Cursor {
    Arrow,
    Hand,   // over a control
    Hidden, // while the film plays undisturbed
}

/// The pointer: away, over the face (and a control on it), pressed (not on the timeline), or
/// dragging the playhead.
#[derive(Clone, Copy, PartialEq)]
enum Pointer {
    Away,
    Over(Option<Control>),
    Down { on: Option<Control>, touch: bool, shown: bool }, // shown: the controls showed then
    Dragging { was_playing: bool, touch: bool },
}

/// How a player starts.
pub(crate) struct Options {
    pub(crate) time: f64,     // seconds
    pub(crate) playing: bool, // or paused
    pub(crate) mac: bool,     // its viewer's keys are a Mac's (the help names Option, not Ctrl)
}

pub(crate) struct Player {
    screen: Screen,
    takes: Projector,
    clock: Clock,
    sound: Sound,
    notes: HashMap<u32, Notes>, // by take
    scenes: Vec<String>,
    scene: Option<String>,
    error: Option<String>,
    chrome: Chrome,
    cursor: (f64, f64), // pixels, from the top left
    pointer: Pointer,
    active: Option<Instant>,          // when the viewer last did something (none: the controls hidden by a tap)
    flash: Option<(String, Instant)>, // what was done
    help: bool,
    captions: bool,
    fullscreen: bool,
    mac: bool,
    hidden: bool,            // it takes no picture: drawn again once it shows
    counting: bool,          // the frame drawn last has its see-through count coming back
    due: bool,               // to be drawn
    change: Option<Instant>, // when the face drawn last changes by itself
    asks: Vec<Ask>,
    wheeled: f64, // a wheel's turn over the sound's control (points) not yet a twentieth
    pub(crate) ahead: Duration, // a refresh of its screen: when a frame drawn now is seen
}

impl Player {
    pub(crate) fn new(screen: Screen, fonts: Rc<Fonts>, options: Options) -> Self {
        let since = options.playing.then(Instant::now);
        Self {
            screen,
            takes: Projector::default(),
            clock: Clock { time: options.time, since, rate: 1.0 },
            sound: Sound::new(),
            notes: HashMap::new(),
            scenes: Vec::new(),
            scene: None,
            error: None,
            chrome: Chrome::new(fonts),
            cursor: (0.0, 0.0),
            pointer: Pointer::Away,
            active: Some(Instant::now()),
            flash: None,
            help: false,
            captions: false,
            fullscreen: false,
            mac: options.mac,
            hidden: false,
            counting: false,
            due: true,
            change: None,
            asks: Vec::new(),
            wheeled: 0.0,
            ahead: Duration::from_micros(16_667),
        }
    }

    // ── the take ───────────────────────────────────────────────────────────────────────────

    /// Take in the next bytes of the director's stream.
    pub(crate) fn feed(&mut self, bytes: &[u8]) -> Result<(), String> {
        for (number, note) in self.takes.feed(bytes)? {
            self.note(number, note);
        }
        self.due = true;
        Ok(())
    }

    /// A note of the director's, for take `number`: the file's scenes and an error (between
    /// takes); a take's plays, sections, captions and sound.
    fn note(&mut self, number: u32, note: Note) {
        let json = match note {
            Note::Sound(file) => {
                self.notes.entry(number).or_default().sound = Some(file);
                return;
            }
            Note::Json(json) => json,
        };
        let Ok(said) = serde_json::from_str::<Said>(&json) else { return };
        if let Some(scenes) = said.scenes {
            self.scenes = scenes;
            self.scene = said.scene;
            self.error = None;
        } else if let Some(fault) = said.error {
            self.error = Some(fault.trace.unwrap_or(fault.message).trim_end().to_owned());
        } else {
            self.notes.entry(number).or_default().take(said);
        }
    }

    /// The scene being played (its name, as its director said).
    pub(crate) fn scene(&self) -> Option<&str> {
        self.scene.as_deref()
    }

    /// The shown take's frames' own size, pixels.
    pub(crate) fn film(&self) -> Option<(u32, u32)> {
        self.takes.shown.as_ref().map(|t| t.size)
    }

    /// The take shown: frames so far, frames a second, whether it has ended.
    fn take(&self) -> Option<(u32, f64, bool)> {
        self.takes.shown.as_ref().map(|t| (t.frames, t.fps, t.ended))
    }

    /// The film's length so far, seconds.
    pub(crate) fn duration(&self) -> f64 {
        self.take().map_or(0.0, |(frames, fps, _)| f64::from(frames) / fps)
    }

    /// How far the film can be played now: to its end, or to its last frame made.
    fn made(&self) -> f64 {
        self.take().map_or(0.0, |(frames, fps, ended)| f64::from(frames.saturating_sub(u32::from(!ended))) / fps)
    }

    /// The time shown: the clock's when a frame drawn now is seen, within what is made.
    pub(crate) fn time(&self) -> f64 {
        self.clock.at(Instant::now() + self.ahead).clamp(0.0, self.made())
    }

    /// Whether the clock runs on past what is made: the film waits for its frames.
    fn waits(&self) -> bool {
        self.clock.playing() && self.clock.now() >= self.made() && !self.take().is_some_and(|t| t.2)
    }

    #[cfg(feature = "web")]
    pub(crate) fn playing(&self) -> bool {
        self.clock.playing()
    }

    fn shown_notes(&self) -> Option<&Notes> {
        self.notes.get(&self.takes.shown.as_ref()?.number)
    }

    fn chapters(&self) -> Vec<(f64, f64, String)> {
        self.shown_notes().map_or(Vec::new(), |n| n.chapters(self.duration()))
    }

    // ── what it does ───────────────────────────────────────────────────────────────────────

    pub(crate) fn seek(&mut self, t: f64) {
        if !t.is_finite() {
            return; // no time at all
        }
        self.clock.set(t.clamp(0.0, self.made()));
        self.sound.jumped();
        self.due = true;
    }

    pub(crate) fn play(&mut self) {
        if self.take().is_some_and(|t| t.2) && self.time() >= self.made() - 1e-6 {
            self.seek(0.0); // from the start again
        }
        self.clock.play();
        self.due = true;
    }

    pub(crate) fn pause(&mut self) {
        // held at the time shown (the clock is a refresh ahead of it): the picture stays
        let shown = self.time();
        self.clock.pause();
        self.clock.time = shown;
        self.due = true;
    }

    fn say(&mut self, what: impl Into<String>) {
        self.flash = Some((what.into(), Instant::now()));
    }

    fn act(&mut self, act: Act) {
        self.active = Some(Instant::now());
        self.due = true;
        match act {
            Act::Toggle => {
                if self.clock.playing() { self.pause() } else { self.play() }
                self.say(if self.clock.playing() { "Play" } else { "Pause" });
            }
            Act::Jump(by) => {
                self.seek(self.time() + by);
                self.say(if by < 0.0 { format!("« {} s", -by) } else { format!("{by} s »") });
            }
            Act::Frame(by) => {
                let fps = self.take().map_or(60.0, |t| t.1);
                self.seek(((self.time() * fps + 1e-6).floor() + by) / fps);
            }
            Act::Chapter(step) => {
                let chapters = self.chapters();
                let Some(last) = chapters.len().checked_sub(1) else { return };
                let t = self.time();
                let now = chapters.iter().rposition(|c| c.0 <= t + 1e-6).unwrap_or(0) as isize;
                let (start, _, title) = chapters[(now + step).clamp(0, last as isize) as usize].clone();
                self.seek(start);
                self.say(title);
            }
            Act::Tenth(tenths) => self.seek(f64::from(tenths) / 10.0 * self.duration()),
            Act::Start => self.seek(0.0),
            Act::End => self.seek(self.made()),
            Act::Rate(step) => {
                let at = RATES.iter().position(|&r| r >= self.clock.rate - 1e-9).unwrap_or(3) as isize + step;
                let to = RATES[at.clamp(0, RATES.len() as isize - 1) as usize];
                let t = self.clock.now();
                self.clock.rate = to;
                self.clock.set(t);
                self.say(format!("{to}×"));
            }
            Act::Volume(by) => {
                self.sound.volume = ((self.sound.volume * 20.0).round() + by).clamp(0.0, 20.0) / 20.0;
                self.sound.muted = false;
                self.say(format!("Sound {:.0}%", self.sound.volume * 100.0));
            }
            Act::Mute => {
                self.sound.muted = !self.sound.muted;
                let said = if self.sound.muted { "Muted".to_owned() } else { format!("Sound {:.0}%", self.sound.volume * 100.0) };
                self.say(said);
            }
            Act::Captions => {
                self.captions = !self.captions;
                self.say(if self.captions { "Captions on" } else { "Captions off" });
            }
            Act::Fullscreen => self.asks.push(Ask::Fullscreen(!self.fullscreen)),
            Act::Help => self.help = !self.help,
            Act::Scene(step) => {
                if self.scenes.len() < 2 {
                    return;
                }
                let now = self.scene.as_ref().and_then(|s| self.scenes.iter().position(|n| n == s)).unwrap_or(0) as isize;
                let next = self.scenes[(now + step).rem_euclid(self.scenes.len() as isize) as usize].clone();
                self.asks.push(Ask::Scene(next.clone()));
                self.seek(0.0);
                self.say(next);
            }
            Act::Back => {
                if self.help {
                    self.help = false;
                } else if self.fullscreen {
                    self.asks.push(Ask::Fullscreen(false));
                }
            }
        }
    }

    // ── its viewer ─────────────────────────────────────────────────────────────────────────

    /// A key pressed: `key` is its value as the web names it (`" "`, `"k"`, `"ArrowLeft"`,
    /// `"Escape"`…). Whether the player took it.
    pub(crate) fn key(&mut self, key: &str, m: Modifiers) -> bool {
        self.sound.resume(); // a key pressed: the page may sound now
        let Some(act) = keyed(key, m, self.clock.playing(), self.help || self.fullscreen, self.mac) else { return false };
        self.act(act);
        true
    }

    /// The face's size, points.
    fn points(&self) -> (f32, f32) {
        let (w, h) = self.screen.size();
        (w as f32 / self.chrome.scale, h as f32 / self.chrome.scale)
    }

    /// The control under the pointer, as the face was last drawn.
    fn control(&self) -> Option<Control> {
        let s = f64::from(self.chrome.scale);
        let h = f64::from(self.points().1);
        self.chrome.control((self.cursor.0 / s) as f32, (h - self.cursor.1 / s) as f32)
    }

    /// The time at `x` pixels along the timeline.
    fn along(&self, x: f64) -> f64 {
        let (left, right, _) = timeline(self.points());
        f64::from(((x as f32 / self.chrome.scale - left) / (right - left)).clamp(0.0, 1.0)) * self.duration()
    }

    /// The pointer moved to (x, y): pixels from the screen's top left.
    pub(crate) fn pointer(&mut self, x: f64, y: f64) {
        self.cursor = (x, y);
        self.active = Some(Instant::now());
        self.due = true;
        match self.pointer {
            Pointer::Dragging { .. } => self.seek(self.along(x)),
            Pointer::Down { .. } => {}
            _ => self.pointer = Pointer::Over(self.control()),
        }
    }

    /// The pointer pressed (a finger, if `touch`) at (x, y), pixels from the screen's top left.
    /// Whether the player took it.
    pub(crate) fn press(&mut self, x: f64, y: f64, touch: bool) -> bool {
        self.sound.resume();
        // what showed before it (a finger comes down where nothing pointed)
        let shown = self.shows_controls();
        self.cursor = (x, y);
        self.active = Some(Instant::now());
        self.due = true;
        self.pointer = match self.control() {
            Some(Control::Timeline) if shown => {
                let was_playing = self.clock.playing();
                self.clock.pause();
                self.seek(self.along(self.cursor.0));
                Pointer::Dragging { was_playing, touch }
            }
            on => Pointer::Down { on: on.filter(|_| shown), touch, shown },
        };
        true
    }

    /// The pointer let go. Whether the player took it.
    pub(crate) fn release(&mut self) -> bool {
        self.sound.resume(); // a finger lifted: what a page counts as a tap
        let touched = match self.pointer {
            Pointer::Dragging { was_playing, touch } => {
                if was_playing {
                    self.clock.play();
                }
                touch
            }
            // on a control: what it does, if let go on it too
            Pointer::Down { on: Some(control), touch, .. } => {
                let act = match control {
                    Control::Toggle => Some(Act::Toggle),
                    Control::Next => Some(Act::Scene(1)),
                    Control::Mute => Some(Act::Mute),
                    Control::Captions => Some(Act::Captions),
                    Control::Fullscreen => Some(Act::Fullscreen),
                    Control::Timeline => None, // pressed, it drags
                };
                if let Some(act) = act.filter(|_| self.control() == Some(control)) {
                    self.act(act);
                }
                touch
            }
            // on the picture: a click plays or pauses (or closes the keys' list); a tap shows the
            // controls, or hides them
            Pointer::Down { on: None, touch: false, .. } => {
                self.act(if self.help { Act::Back } else { Act::Toggle });
                false
            }
            Pointer::Down { on: None, touch: true, shown } => {
                self.active = (!shown).then(Instant::now);
                true
            }
            Pointer::Away | Pointer::Over(_) => return false,
        };
        self.pointer = if touched { Pointer::Away } else { Pointer::Over(self.control()) };
        self.due = true;
        true
    }

    /// The press was called off (the system took the pointer: a finger's pan scrolled the page):
    /// a drag ends where it is, the film playing again if it played, and nothing is done.
    pub(crate) fn cancel(&mut self) {
        if let Pointer::Dragging { was_playing: true, .. } = self.pointer {
            self.clock.play();
        }
        self.pointer = Pointer::Away;
        self.due = true;
    }

    /// The pointer left the screen.
    pub(crate) fn leave(&mut self) {
        if !matches!(self.pointer, Pointer::Dragging { .. }) {
            self.pointer = Pointer::Away;
        }
        self.due = true;
    }

    /// A wheel turned, or a trackpad scrolled, by (dx, dy) points (the web's: right and down are
    /// positive). Over the sound's control it sets the volume, a twentieth per 50 points;
    /// sideways it moves the playhead, a second per 100 points; else the player lets it go by
    /// (the page scrolls). Whether it took it.
    pub(crate) fn wheel(&mut self, dx: f64, dy: f64) -> bool {
        if matches!(self.pointer, Pointer::Over(Some(Control::Mute))) && dy.abs() > dx.abs() {
            self.wheeled -= dy;
            let steps = (self.wheeled / 50.0).trunc();
            if steps != 0.0 {
                self.wheeled -= steps * 50.0;
                self.act(Act::Volume(steps as f32));
            }
            return true;
        }
        if dx.abs() <= dy.abs() {
            return false;
        }
        self.active = Some(Instant::now());
        self.clock.pause();
        self.seek(self.time() + dx / 100.0);
        true
    }

    /// The cursor to show.
    pub(crate) fn cursor(&self) -> Cursor {
        match self.pointer {
            Pointer::Over(Some(_)) | Pointer::Dragging { .. } | Pointer::Down { on: Some(_), .. } => Cursor::Hand,
            Pointer::Over(None) if self.clock.playing() && !self.shows_controls() => Cursor::Hidden,
            _ => Cursor::Arrow,
        }
    }

    // ── its screen ─────────────────────────────────────────────────────────────────────────

    /// The screen's new size (pixels) and its pixels per point.
    pub(crate) fn resize(&mut self, width: u32, height: u32, scale: f32) {
        if (width, height) != self.screen.size() {
            let screen = &mut self.screen;
            let _ = with_gpu(|gpu| screen.resize(gpu, (width, height)));
        }
        self.chrome.scale = scale;
        self.due = true;
    }

    /// The screen is covered (or minimized, or scrolled away), or shows again.
    pub(crate) fn hide(&mut self, hidden: bool) {
        self.hidden = hidden;
        self.due = true;
    }

    /// The screen is full screen now, or not.
    pub(crate) fn fullscreen(&mut self, on: bool) {
        self.fullscreen = on;
        self.due = true;
    }

    /// What it asks of its screen, since it was last asked.
    pub(crate) fn asks(&mut self) -> Vec<Ask> {
        std::mem::take(&mut self.asks)
    }

    /// Whether the controls show: over a picture, while paused or waiting, after the viewer
    /// did something, the pointer on them, or the keys shown.
    fn shows_controls(&self) -> bool {
        let lately = self.active.is_some_and(|at| at.elapsed() < IDLE);
        let on = matches!(self.pointer, Pointer::Over(Some(_)) | Pointer::Dragging { .. } | Pointer::Down { on: Some(_), .. });
        self.takes.shown.is_some() && (!self.clock.playing() || self.waits() || lately || on || self.help)
    }

    /// What the face shows now, at `time`.
    fn face(&self, time: f64) -> Face {
        let notes = self.shown_notes();
        let said = match notes {
            Some(n) if self.captions => n.captions.iter().filter(|c| c.start <= time && time < c.end).map(|c| c.text.clone()).collect(),
            _ => Vec::new(),
        };
        let status = (self.takes.shown.is_none() && self.error.is_none()).then(|| format!("Making {}…", self.scene.as_deref().unwrap_or("the scene")));
        Face {
            size: self.points(),
            time,
            duration: self.duration(),
            made: self.made(),
            playing: self.clock.playing(),
            controls: self.shows_controls(),
            chapters: self.chapters(),
            hover: match self.pointer {
                Pointer::Over(Some(Control::Timeline)) => Some(self.along(self.cursor.0)),
                Pointer::Dragging { .. } => Some(time),
                _ => None,
            },
            rate: self.clock.rate,
            captions: notes.filter(|n| !n.captions.is_empty()).map(|_| self.captions),
            said,
            sound: notes.and_then(|n| n.sound.as_ref()).map(|_| self.sound.muted),
            scenes: self.scenes.len() > 1,
            fullscreen: self.fullscreen,
            flash: self.flash.as_ref().filter(|(_, at)| at.elapsed() < FLASH).map(|(what, _)| what.clone()),
            status,
            error: self.error.clone(),
            help: self.help,
            mac: self.mac,
        }
    }

    /// When the face changes by itself next, as nothing else does: a flash fading, the controls
    /// hiding.
    fn next_change(&self) -> Option<Instant> {
        let flash = self.flash.as_ref().map(|(_, at)| *at + FLASH).filter(|&end| end > Instant::now());
        let idle = self.active.filter(|_| self.shows_controls()).map(|at| at + IDLE).filter(|&end| end > Instant::now());
        flash.into_iter().chain(idle).min()
    }

    /// When it is to be drawn next. It reads a drawn frame's see-through count meanwhile, and
    /// draws that frame again if the lists grew. Hidden, it is drawn only when something changed
    /// (its clock and sound follow; no picture is taken).
    pub(crate) fn wake(&mut self) -> Result<Wake, String> {
        if self.counting {
            let takes = &mut self.takes;
            let settled = with_gpu(|gpu| {
                let _ = gpu.device.poll(wgpu::PollType::Poll);
                takes.settle(gpu)
            })??;
            self.counting = settled == Settled::Waiting;
            self.due |= settled == Settled::Redraw;
        }
        let now = Instant::now();
        self.due |= self.change.is_some_and(|at| at <= now);
        // playing, a picture each refresh (with nothing to play yet, or out of sight, none)
        if self.due || (self.clock.playing() && self.takes.shown.is_some() && !self.hidden) {
            return Ok(Wake::Now);
        }
        let counting = self.counting.then_some(now + COUNTING);
        Ok(counting.into_iter().chain(self.change.filter(|_| !self.hidden)).min().map_or(Wake::Idle, Wake::At))
    }

    /// Draw: the film's frame now (again only if it changed), the face over it; `presenting`
    /// just before the picture goes to the screen. Hidden, only the clock and the sound.
    pub(crate) fn draw(&mut self, presenting: impl FnOnce()) -> Result<(), String> {
        self.due = false;
        let (made, ended, playing) = (self.made(), self.take().is_some_and(|t| t.2), self.clock.playing());
        self.clock.bound(made, ended);
        let time = self.time();
        let shown = self.takes.show(time);
        self.notes.retain(|&take, _| take >= shown); // a take replaced goes, its notes with it
        if self.hidden {
            self.change = None; // the face is laid out again once it shows
        } else {
            self.picture(time, presenting)?;
        }
        let (take, waits) = (self.takes.shown.as_ref().map(|t| t.number), self.waits());
        let sound = take.and_then(|n| self.notes.get(&n)).and_then(|n| n.sound.as_deref());
        self.sound.follow(take, sound, self.clock, waits);
        if playing && !self.clock.playing() {
            self.due = true; // stopped at the end: the face shows it
        }
        Ok(())
    }

    /// The picture at `time`: the film's frame (drawn again only if it changed), the face over it.
    fn picture(&mut self, time: f64, presenting: impl FnOnce()) -> Result<(), String> {
        let size = self.screen.size();
        let film = self.takes.shown.as_ref().map(|t| project::fit(t.size, size));
        if let Some(film) = film
            && !self.takes.drawn(time, film)
        {
            let takes = &mut self.takes;
            with_gpu(|gpu| -> Result<(), String> {
                if let Some(encoder) = takes.encode(gpu, time, film)? {
                    gpu.queue.submit(Some(encoder.finish()));
                    takes.submitted();
                }
                Ok(())
            })??;
            self.counting = true;
        }
        let over = self.chrome.lay_out(&self.face(time))?;
        if over {
            let chrome = &mut self.chrome;
            with_gpu(|gpu| -> Result<(), String> {
                let encoder = chrome.encode(gpu, size)?;
                gpu.queue.submit(Some(encoder.finish()));
                Ok(())
            })??;
        }
        self.change = self.next_change();
        let place = film.map_or([0.0; 4], |(w, h)| {
            let (x, y) = ((size.0 - w) / 2, (size.1 - h) / 2);
            [x as f32, y as f32, (x + w) as f32, (y + h) as f32]
        });
        let film = self.takes.shown.as_ref().and_then(|t| t.player.targets.as_ref()).map(|t| &t.frame.color);
        let face = over.then(|| self.chrome.player.targets.as_ref().map(|t| &t.frame.color)).flatten();
        let screen = &mut self.screen;
        match with_gpu(|gpu| screen.present(gpu, film, face, place, presenting))? {
            Presented::Shown => {}
            Presented::Hidden => self.hidden = true,
            Presented::Again => self.due = true,
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keys_are_named_as_the_web_names_them() {
        let none = Modifiers::default();
        let (alt, ctrl, meta) = (Modifiers { alt: true, ..none }, Modifiers { ctrl: true, ..none }, Modifiers { meta: true, ..none });
        let key = |k, m| keyed(k, m, true, false, false);
        assert_eq!(key(" ", none), Some(Act::Toggle));
        assert_eq!(key("k", none), Some(Act::Toggle));
        assert_eq!(key("ArrowLeft", none), Some(Act::Jump(-5.0)));
        assert_eq!(key("L", none), Some(Act::Jump(10.0)));
        // an arrow with Option on a Mac, with Control elsewhere: the play before, after; Alt with
        // an arrow is the browser's Back and Forward there
        assert_eq!(keyed("ArrowLeft", alt, true, false, true), Some(Act::Chapter(-1)));
        assert_eq!(keyed("ArrowRight", ctrl, true, false, false), Some(Act::Chapter(1)));
        assert_eq!(keyed("ArrowLeft", alt, true, false, false), None);
        assert_eq!(keyed("ArrowLeft", ctrl, true, false, true), None);
        // a frame at a time, paused only
        assert_eq!(key(",", none), None);
        assert_eq!(keyed(".", none, false, false, false), Some(Act::Frame(1.0)));
        assert_eq!(key("7", none), Some(Act::Tenth(7)));
        assert_eq!(key("?", none), Some(Act::Help));
        // Escape closes what is open; else it is the page's
        assert_eq!(keyed("Escape", none, true, true, false), Some(Act::Back));
        assert_eq!(key("Escape", none), None);
        // the system's and the page's: Command-R, Control-C, a key the player has no use for
        assert_eq!(key("r", meta), None);
        assert_eq!(key("c", ctrl), None);
        assert_eq!(key("ArrowLeft", meta), None);
        assert_eq!(key("x", none), None);
        assert_eq!(key("Tab", none), None);
    }

    #[test]
    fn chapters_are_the_sections_or_else_the_plays() {
        let play = |index, start, end, place: Option<(&str, u32)>| Play { index, start, end, place: place.map(|(f, l)| (f.to_owned(), l)) };
        let mut notes = Notes { plays: vec![play(0, 0.0, 1.0, Some(("/a/scene.py", 12))), play(1, 1.0, 2.0, Some(("/a/scene.py", 14))), play(2, 2.0, 3.0, None)], ..Notes::default() };
        let titles = |notes: &Notes| notes.chapters(3.0).into_iter().map(|c| c.2).collect::<Vec<_>>();
        assert_eq!(titles(&notes), ["Line 12", "Line 14", "Play 3"]);
        // plays from several files: each by its file's name
        notes.plays[1].place = Some(("/b/helpers.py".into(), 3));
        assert_eq!(titles(&notes), ["scene.py:12", "helpers.py:3", "Play 3"]);
        // sections, if more than one: a section with no frame yet gives way to the next
        for (name, start) in [("Intro", 0.0), ("Middle", 1.0), ("Gone", 2.0), ("End", 2.0)] {
            notes.take(Said { section: Some(Section { name: name.into(), start }), ..Said::default() });
        }
        assert_eq!(notes.chapters(3.0), [(0.0, 1.0, "Intro".into()), (1.0, 2.0, "Middle".into()), (2.0, 3.0, "End".into())]);
    }
}
