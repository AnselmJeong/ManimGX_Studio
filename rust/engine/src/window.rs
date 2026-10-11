//! The window: ManimGX's player (see `player`) on this machine's screen. Its takes come from its
//! director on standard input; it asks for another scene by writing a line of JSON to standard
//! output (`{"scene": "Name"}`). It closes when it is closed, or its director goes.
//!
//! What a window adds to the player is the window: winit's events in the player's words (the web's,
//! which winit's own follow), its size, title, cursor and full screen.

use std::io::{Read, Write};
use std::rc::Rc;
use std::sync::Arc;
use std::time::Duration;

use winit::application::ApplicationHandler;
use winit::dpi::LogicalSize;
use winit::event::{ElementState, MouseButton, MouseScrollDelta, TouchPhase, WindowEvent};
use winit::event_loop::{ActiveEventLoop, ControlFlow, EventLoop, EventLoopProxy};
use winit::keyboard::{Key, ModifiersState, NamedKey};
use winit::window::{CursorIcon, Fullscreen, Window, WindowId};

use crate::player::{self, Ask, Cursor, Modifiers, Player, Screen, Wake};
use crate::render::with_gpu;
use crate::text::Fonts;

/// What the window is opened with.
pub(crate) struct Options {
    pub(crate) title: String,
    pub(crate) time: f64,          // where the playhead starts, seconds
    pub(crate) fonts: Vec<String>, // the font directories its face is set in
}

/// What wakes the event loop: the director's bytes, or its end.
enum Event {
    Take(Vec<u8>),
    Gone,
}

/// Open the window and play what comes on standard input, until either ends.
pub(crate) fn run(options: Options) -> Result<(), String> {
    let event_loop = EventLoop::<Event>::with_user_event().build().map_err(|e| e.to_string())?;
    let proxy = event_loop.create_proxy();
    std::thread::spawn(move || listen(proxy));
    let fonts = Rc::new(Fonts::new(crate::typeset::face_fonts(&options.fonts)));
    let mut app = App { options, fonts, window: None, player: None, modifiers: ModifiersState::empty(), pointer: (0.0, 0.0), finger: None, cursor: Cursor::Arrow, sized: false, failed: None };
    event_loop.run_app(&mut app).map_err(|e| e.to_string())?;
    app.failed.map_or(Ok(()), Err)
}

/// The director's bytes, as they come, to the event loop; then its end.
fn listen(proxy: EventLoopProxy<Event>) {
    let mut input = std::io::stdin().lock();
    let mut buffer = vec![0u8; 1 << 20];
    while let Ok(n) = input.read(&mut buffer) {
        if n == 0 || proxy.send_event(Event::Take(buffer[..n].to_vec())).is_err() {
            break;
        }
    }
    let _ = proxy.send_event(Event::Gone);
}

struct App {
    options: Options,
    fonts: Rc<Fonts>,
    window: Option<Arc<Window>>,
    player: Option<Player>,
    modifiers: ModifiersState,
    pointer: (f64, f64), // where the pointer is (pixels)
    finger: Option<u64>, // the touch the player follows
    cursor: Cursor,
    sized: bool, // the window has its film's proportions, or its viewer's
    failed: Option<String>,
}

/// A key as the web names it (and winit's names follow): a character, or `"ArrowLeft"`, `" "`…
fn named(key: &Key) -> Option<String> {
    match key {
        Key::Character(c) => Some(c.to_string()),
        Key::Named(NamedKey::Space) => Some(" ".into()),
        Key::Named(named) => Some(format!("{named:?}")),
        _ => None,
    }
}

impl App {
    fn fail(&mut self, event_loop: &ActiveEventLoop, error: String) {
        self.failed = Some(error);
        event_loop.exit();
    }

    /// What the player asks: another scene of its director, full screen; and its cursor.
    fn answer(&mut self) {
        let (Some(window), Some(player)) = (&self.window, &mut self.player) else { return };
        for ask in player.asks() {
            match ask {
                Ask::Scene(name) => {
                    let mut out = std::io::stdout().lock();
                    let _ = writeln!(out, "{}", serde_json::json!({ "scene": name }));
                    let _ = out.flush();
                }
                Ask::Fullscreen(on) => {
                    window.set_fullscreen(on.then_some(Fullscreen::Borderless(None)));
                    player.fullscreen(on);
                }
            }
        }
        let cursor = player.cursor();
        if cursor != self.cursor {
            window.set_cursor_visible(cursor != Cursor::Hidden);
            window.set_cursor(if cursor == Cursor::Hand { CursorIcon::Pointer } else { CursorIcon::Default });
            self.cursor = cursor;
        }
    }

    /// Give the window its film's proportions, once, unless they are its already (or its
    /// viewer has sized it): the most that fits two thirds of its screen.
    fn proportion(&mut self) {
        let (Some(window), Some((w, h))) = (&self.window, self.player.as_ref().and_then(Player::film)) else { return };
        if std::mem::replace(&mut self.sized, true) {
            return;
        }
        let size = window.inner_size();
        let (w, h) = (f64::from(w), f64::from(h));
        if (w * f64::from(size.height) / (h * f64::from(size.width)) - 1.0).abs() < 0.01 {
            return;
        }
        let Some(monitor) = window.current_monitor() else { return };
        let room = monitor.size().to_logical::<f64>(monitor.scale_factor());
        let k = (room.width * 2.0 / 3.0 / w).min(room.height * 2.0 / 3.0 / h);
        let _ = window.request_inner_size(LogicalSize::new(w * k, h * k));
    }
}

impl ApplicationHandler<Event> for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.window.is_some() {
            return;
        }
        // a film's usual proportions (16:9) at two thirds of the screen: a take of others
        // reshapes it (`proportion`)
        let room = event_loop.primary_monitor().map_or(LogicalSize::new(1440.0, 900.0), |m| m.size().to_logical::<f64>(m.scale_factor()));
        let k = (room.width * 2.0 / 3.0 / 16.0).min(room.height * 2.0 / 3.0 / 9.0);
        let attributes = Window::default_attributes().with_title(&self.options.title).with_inner_size(LogicalSize::new(16.0 * k, 9.0 * k)).with_min_inner_size(LogicalSize::new(320.0, 180.0));
        let made = event_loop.create_window(attributes).map_err(|e| e.to_string()).and_then(|window| {
            let window = Arc::new(window);
            let size = window.inner_size();
            let screen = with_gpu(|gpu| {
                let surface = gpu.instance.create_surface(window.clone()).map_err(|e| e.to_string())?;
                Screen::new(gpu, surface, (size.width, size.height))
            })??;
            let options = player::Options { time: self.options.time, playing: true, mac: cfg!(target_os = "macos") };
            let mut player = Player::new(screen, self.fonts.clone(), options);
            player.resize(size.width, size.height, window.scale_factor() as f32);
            if let Some(millihertz) = window.current_monitor().and_then(|m| m.refresh_rate_millihertz()) {
                player.ahead = Duration::from_secs_f64(1000.0 / f64::from(millihertz.max(1)));
            }
            Ok((window, player))
        });
        match made {
            Ok((window, player)) => {
                window.focus_window();
                window.request_redraw();
                (self.window, self.player) = (Some(window), Some(player));
            }
            Err(error) => self.fail(event_loop, error),
        }
    }

    fn user_event(&mut self, event_loop: &ActiveEventLoop, event: Event) {
        let (Some(window), Some(player)) = (&self.window, &mut self.player) else { return };
        match event {
            Event::Take(bytes) => {
                let before = player.scene().map(str::to_owned);
                if let Err(error) = player.feed(&bytes) {
                    return self.fail(event_loop, format!("the take could not be read: {error}"));
                }
                if let Some(scene) = player.scene().filter(|&s| before.as_deref() != Some(s)) {
                    window.set_title(&format!("{} — {scene}", self.options.title));
                }
                self.proportion();
            }
            Event::Gone => event_loop.exit(),
        }
    }

    fn window_event(&mut self, event_loop: &ActiveEventLoop, _: WindowId, event: WindowEvent) {
        let (Some(window), Some(player)) = (self.window.clone(), self.player.as_mut()) else { return };
        let scale = window.scale_factor();
        match event {
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::Resized(size) => {
                player.resize(size.width, size.height, scale as f32);
                player.fullscreen(window.fullscreen().is_some());
            }
            WindowEvent::ScaleFactorChanged { scale_factor, .. } => {
                let size = window.inner_size();
                player.resize(size.width, size.height, scale_factor as f32);
            }
            WindowEvent::Occluded(hidden) => player.hide(hidden),
            WindowEvent::ModifiersChanged(modifiers) => self.modifiers = modifiers.state(),
            WindowEvent::KeyboardInput { event, .. } if event.state == ElementState::Pressed => {
                let m = self.modifiers;
                let Some(key) = named(&event.logical_key) else { return };
                // the system's shortcuts: Command-W and Command-Q close the window
                if m.super_key() && matches!(key.as_str(), "w" | "q") {
                    return event_loop.exit();
                }
                player.key(&key, Modifiers { ctrl: m.control_key(), alt: m.alt_key(), meta: m.super_key() });
            }
            WindowEvent::CursorMoved { position, .. } => {
                self.pointer = (position.x, position.y);
                player.pointer(position.x, position.y);
            }
            WindowEvent::CursorLeft { .. } => player.leave(),
            WindowEvent::MouseInput { state, button: MouseButton::Left, .. } => {
                if state == ElementState::Pressed {
                    player.press(self.pointer.0, self.pointer.1, false);
                } else {
                    player.release();
                }
            }
            WindowEvent::MouseWheel { delta, .. } => {
                // winit's deltas move the content (right, down: positive); the web's, the view
                let (dx, dy) = match delta {
                    MouseScrollDelta::PixelDelta(p) => (p.x / scale, p.y / scale),
                    MouseScrollDelta::LineDelta(x, y) => (f64::from(x) * 20.0, f64::from(y) * 20.0),
                };
                player.wheel(-dx, -dy);
            }
            WindowEvent::Touch(touch) => {
                if self.finger.is_some_and(|id| id != touch.id) {
                    return;
                }
                let (x, y) = (touch.location.x, touch.location.y);
                match touch.phase {
                    TouchPhase::Started => {
                        self.finger = Some(touch.id);
                        player.press(x, y, true);
                    }
                    TouchPhase::Moved => player.pointer(x, y),
                    TouchPhase::Ended => {
                        self.finger = None;
                        player.release();
                    }
                    TouchPhase::Cancelled => {
                        self.finger = None;
                        player.cancel();
                    }
                }
            }
            WindowEvent::RedrawRequested => {
                if let Err(error) = player.draw(|| window.pre_present_notify()) {
                    return self.fail(event_loop, error);
                }
            }
            _ => {}
        }
        self.answer();
    }

    fn about_to_wait(&mut self, event_loop: &ActiveEventLoop) {
        let (Some(window), Some(player)) = (&self.window, &mut self.player) else { return };
        let wake = match player.wake() {
            Ok(wake) => wake,
            Err(error) => return self.fail(event_loop, error),
        };
        // drawn at the screen's next refresh, or at a time (a frame's count back, the face
        // changing by itself), or when something happens
        event_loop.set_control_flow(match wake {
            Wake::Now => {
                window.request_redraw();
                ControlFlow::Wait
            }
            Wake::At(at) => ControlFlow::WaitUntil(at),
            Wake::Idle => ControlFlow::Wait,
        });
    }
}
