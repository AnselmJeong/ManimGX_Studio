//! The player in the browser (WebAssembly, WebGPU): ManimGX's player (see `player`) on a page's
//! canvas, the same as in a window. The page's element (`browser`) hands on what its viewer
//! does, in the web's own words, draws it when it is due (`wake`, `draw`) and does what it asks
//! (`asks`); its director's takes come from Pyodide, in a worker (`feed`).

use std::cell::RefCell;
use std::rc::Rc;

use wasm_bindgen::prelude::*;

use crate::player::{self, Ask, Cursor, Modifiers, Screen, Wake};
use crate::render::{GPU, Gpu, with_gpu};
use crate::text::Fonts;

thread_local! {
    // the fonts every player's face is set in
    static FONTS: RefCell<Option<Rc<Fonts>>> = const { RefCell::new(None) };
}

#[wasm_bindgen(start)]
fn start() {
    console_error_panic_hook::set_once();
}

fn error(e: impl std::fmt::Display) -> JsError {
    JsError::new(&e.to_string())
}

/// Bring the GPU up, and take the fonts the players' faces are set in (each a font file's
/// bytes): once, before a player is made.
#[wasm_bindgen]
pub async fn init(fonts: Vec<js_sys::Uint8Array>) -> Result<(), JsError> {
    if GPU.with_borrow(Option::is_none) {
        let gpu = Gpu::new().await.map_err(error)?;
        GPU.with_borrow_mut(|slot| *slot = Some(gpu));
    }
    if FONTS.with_borrow(Option::is_none) {
        let files = fonts.iter().map(|f| &*Box::leak(f.to_vec().into_boxed_slice()));
        let fonts = Rc::new(Fonts::new(files));
        FONTS.with_borrow_mut(|slot| *slot = Some(fonts));
    }
    Ok(())
}

/// ManimGX's player, on a canvas.
#[wasm_bindgen]
pub struct Player {
    player: player::Player,
}

#[wasm_bindgen]
impl Player {
    /// A player on `canvas` (at its size, pixels), from `time` seconds, playing or paused; `mac`:
    /// its viewer's keys are a Mac's.
    #[wasm_bindgen(constructor)]
    pub fn new(canvas: web_sys::HtmlCanvasElement, time: f64, playing: bool, mac: bool) -> Result<Player, JsError> {
        let fonts = FONTS.with_borrow(Clone::clone).ok_or_else(|| error("init() first"))?;
        let size = (canvas.width(), canvas.height());
        let screen = with_gpu(|gpu| {
            let surface = gpu.instance.create_surface(wgpu::SurfaceTarget::Canvas(canvas)).map_err(|e| e.to_string())?;
            Screen::new(gpu, surface, size)
        })
        .and_then(|s| s)
        .map_err(error)?;
        Ok(Player { player: player::Player::new(screen, fonts, player::Options { time, playing, mac }) })
    }

    /// Take in the next bytes of its director's stream.
    pub fn feed(&mut self, bytes: &[u8]) -> Result<(), JsError> {
        self.player.feed(bytes).map_err(error)
    }

    /// A key pressed, as `KeyboardEvent` has it. Whether the player took it.
    pub fn key(&mut self, key: &str, ctrl: bool, alt: bool, meta: bool) -> bool {
        self.player.key(key, Modifiers { ctrl, alt, meta })
    }

    /// The pointer moved to (x, y), pixels from the canvas's top left.
    pub fn pointer(&mut self, x: f64, y: f64) {
        self.player.pointer(x, y);
    }

    /// The pointer pressed (a finger, if `touch`) at (x, y), pixels from the canvas's top left.
    /// Whether the player took it.
    pub fn press(&mut self, x: f64, y: f64, touch: bool) -> bool {
        self.player.press(x, y, touch)
    }

    /// The pointer let go. Whether the player took it.
    pub fn release(&mut self) -> bool {
        self.player.release()
    }

    /// The pointer left the canvas.
    pub fn leave(&mut self) {
        self.player.leave();
    }

    /// The press was called off (`pointercancel`: a finger's pan scrolled the page).
    pub fn cancel(&mut self) {
        self.player.cancel();
    }

    /// A wheel turned by (dx, dy) points, as `WheelEvent` has it. Whether the player took it.
    pub fn wheel(&mut self, dx: f64, dy: f64) -> bool {
        self.player.wheel(dx, dy)
    }

    /// The canvas's size on the page, pixels (the screen's own), and its pixels per point.
    pub fn resize(&mut self, width: u32, height: u32, scale: f32) {
        self.player.resize(width, height, scale);
    }

    /// The canvas scrolled out of sight (or its page hidden), or into it.
    pub fn hide(&mut self, hidden: bool) {
        self.player.hide(hidden);
    }

    /// The player is full screen now, or not.
    pub fn fullscreen(&mut self, on: bool) {
        self.player.fullscreen(on);
    }

    /// When to draw it next: 0, at the next animation frame; milliseconds from now; −1, once
    /// something happens.
    pub fn wake(&mut self) -> Result<f64, JsError> {
        Ok(match self.player.wake().map_err(error)? {
            Wake::Now => 0.0,
            Wake::At(at) => at.saturating_duration_since(web_time::Instant::now()).as_secs_f64() * 1000.0,
            Wake::Idle => -1.0,
        })
    }

    /// Draw it now.
    pub fn draw(&mut self) -> Result<(), JsError> {
        self.player.draw(|| {}).map_err(error)
    }

    /// What it asks of the page since it was last asked, in turn: `["scene", name]` (its director
    /// to run the file's scene of that name), `["fullscreen", on]`.
    pub fn asks(&mut self) -> js_sys::Array {
        self.player
            .asks()
            .into_iter()
            .map(|ask| -> JsValue {
                match ask {
                    Ask::Scene(name) => js_sys::Array::of2(&"scene".into(), &name.into()).into(),
                    Ask::Fullscreen(on) => js_sys::Array::of2(&"fullscreen".into(), &on.into()).into(),
                }
            })
            .collect()
    }

    /// The cursor over it, as CSS names it.
    #[wasm_bindgen(getter)]
    pub fn cursor(&self) -> String {
        match self.player.cursor() {
            Cursor::Arrow => "default",
            Cursor::Hand => "pointer",
            Cursor::Hidden => "none",
        }
        .into()
    }

    /// The time shown, seconds.
    #[wasm_bindgen(getter)]
    pub fn time(&self) -> f64 {
        self.player.time()
    }

    #[wasm_bindgen(setter)]
    pub fn set_time(&mut self, t: f64) {
        self.player.seek(t);
    }

    /// The film's length so far, seconds.
    #[wasm_bindgen(getter)]
    pub fn duration(&self) -> f64 {
        self.player.duration()
    }

    #[wasm_bindgen(getter)]
    pub fn playing(&self) -> bool {
        self.player.playing()
    }

    pub fn play(&mut self) {
        self.player.play();
    }

    pub fn pause(&mut self) {
        self.player.pause();
    }

    /// The scene it plays, as its director named it.
    #[wasm_bindgen(getter)]
    pub fn scene(&self) -> Option<String> {
        self.player.scene().map(str::to_owned)
    }

    /// The film's own size, its frames' (pixels): [width, height]; none before its first take.
    #[wasm_bindgen(getter)]
    pub fn film(&self) -> Option<Vec<u32>> {
        self.player.film().map(|(w, h)| vec![w, h])
    }
}
