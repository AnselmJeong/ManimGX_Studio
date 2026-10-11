// <manimgx-player>: ManimGX's player in the page. The engine's own player, the one `manimgx
// preview`'s window is, compiled to WebAssembly: it draws the film and its face (the controls, the
// time, the plays, captions, the scene's error, the keys) onto a canvas with WebGPU, and keeps the
// clock and the sound. The element only hands it what its viewer does, in the web's own words,
// draws it when it is due, and does what it asks (another scene, full screen). Its scene is
// Python, run in the browser by Pyodide (see director.ts).
//
//   <manimgx-player><script type="text/python"> …a scene… </script></manimgx-player>
//   player.source = code                                    (the film made again, time kept)

import type { Engine, Player } from "./engine.js";
import { message } from "./protocol.js";
import type { FromDirector, ToDirector } from "./protocol.js";

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const MAC = /Mac|iPhone|iPad/.test(navigator.platform);

/** Where Pyodide and ManimGX come from (set before the first film starts). */
export const settings = {
  /** Pyodide's files (its `indexURL`). */
  pyodide: PYODIDE,
  /** What micropip installs: `manimgx==<this version>` from PyPI, or a wheel's URL. */
  manimgx: "manimgx",
};

/** The entry point supplies the bundled director's script. */
export const runtime = {
  worker: (): string | URL => new URL("./director.js", import.meta.url),
};

interface PagePlayer {
  wait(): void;
  feed(bytes: ArrayBuffer): void;
  fail(error: string): void;
}

interface Page {
  director: Worker;
  players: Map<number, PagePlayer>;
  engine: Promise<Engine | null>;
  status: string;
  failure: string | null;
}

let page: Page | undefined; // the page's director, its engine (once it is up), and its players

function send(director: Worker, data: ToDirector): void {
  director.postMessage(data);
}

/** The page's director (Pyodide, in a worker) and engine, begun once. */
function begin(): Page {
  if (page) return page;
  const director = new Worker(runtime.worker(), { type: "module" });
  const players = new Map<number, PagePlayer>();
  let up: (engine: Engine | null) => void = () => {};
  const current: Page = {
    director,
    players,
    engine: new Promise((resolve) => (up = resolve)),
    status: "Loading Python…",
    failure: null,
  };
  page = current;
  const fail = (error: string): void => {
    if (current.failure !== null) return;
    current.failure = current.status = error;
    up(null);
    director.terminate();
    for (const player of players.values()) player.fail(error);
  };
  director.onerror = (event) => fail(`ManimGX could not start: ${event.message}`);
  director.onmessageerror = () => fail("ManimGX could not read its worker's reply");
  director.onmessage = async ({ data }: MessageEvent<FromDirector>) => {
    if (current.failure !== null) return;
    if ("failure" in data) return fail(data.failure);
    if ("status" in data) {
      current.status = data.status;
      for (const player of players.values()) player.wait();
    }
    if ("engine" in data) {
      // the player, from the ManimGX the director installed: its JS, its WebAssembly, the fonts
      // its face is set in
      const { js, wasm, fonts } = data.engine;
      const url = URL.createObjectURL(new Blob([js], { type: "text/javascript" }));
      try {
        const engine = (await import(url)) as Engine;
        await engine.default({ module_or_path: wasm });
        await engine.init(fonts);
        up(engine);
      } catch (error) {
        fail(`ManimGX can't draw here: ${message(error)}`);
      } finally {
        URL.revokeObjectURL(url);
      }
    }
    if ("film" in data) players.get(data.film)?.feed(data.feed);
  };
  send(director, { boot: { pyodide: settings.pyodide, manimgx: settings.manimgx } });
  return page;
}

let films = 0;

/** A scene written in Python, made in the page and played on a canvas by ManimGX's engine,
 *  with the engine's own controls. */
export class ManimgxPlayer extends HTMLElement {
  static observedAttributes = ["scene"];

  #film = 0;
  #canvas: HTMLCanvasElement;
  #said: HTMLParagraphElement;
  #source: string | null = null;
  #backlog: ArrayBuffer[] = []; // the director's bytes that came before the player
  #wants: { time: number; playing: boolean | null } = { time: 0, playing: null };
  #begun = false;
  #failed = false;
  #player: Player | null = null; // native GPU resources belong to one connected lifetime
  #connection: AbortController | undefined;
  #timer: number | undefined;
  #frame = 0;
  #root: ShadowRoot;

  constructor() {
    super();
    this.#root = this.attachShadow({ mode: "open" });
    this.#root.innerHTML = `<style>
      :host { display: block; position: relative; aspect-ratio: var(--film, 16 / 9); background: #000; outline: none; contain: content; }
      canvas { position: absolute; inset: 0; width: 100%; height: 100%; touch-action: pan-y; }
      p { position: absolute; inset: 0; margin: auto; height: 1.5em; text-align: center; color: #fffb; font: 15px system-ui, sans-serif; }
    </style><canvas></canvas><p></p>`;
    const canvas = this.#root.querySelector("canvas");
    const said = this.#root.querySelector("p");
    if (!canvas || !said) throw new Error("The player's canvas and status are missing");
    this.#canvas = canvas;
    this.#said = said; // what it waits for, until the engine is up
  }

  connectedCallback(): void {
    if (!this.hasAttribute("tabindex")) this.tabIndex = 0; // it takes keys
    if (this.#connection || this.#failed) return;
    this.#film = ++films; // late bytes from an earlier connection belong to its old decoder
    const connection = (this.#connection = new AbortController());
    // Begun a task later: a page can still set `settings` after importing this.
    const task = setTimeout(() => {
      if (!connection.signal.aborted) this.#begin(connection.signal);
    });
    connection.signal.addEventListener(
      "abort",
      () => {
        clearTimeout(task);
        clearTimeout(this.#timer);
        cancelAnimationFrame(this.#frame);
        this.#frame = 0;
      },
      { once: true },
    );
  }

  disconnectedCallback(): void {
    this.#connection?.abort();
    this.#connection = undefined;
    if (page?.players.delete(this.#film) && page.failure === null) {
      send(page.director, { film: this.#film, drop: true });
    }
    this.#backlog = [];
    const player = this.#player;
    if (player) {
      this.#wants = { time: player.time, playing: false };
      player.pause();
      this.#player = null;
      player.free();
    }
  }

  attributeChangedCallback(): void {
    if (this.#begun && this.#source !== null) this.#run();
  }

  /** The scene's Python source: set it, and the film is made again (the time kept). */
  get source(): string | null {
    return this.#source;
  }
  set source(code: string | null) {
    this.#source = code == null ? null : String(code);
    if (this.#begun && this.#source !== null) this.#run();
  }

  /** The scene shown (a file may define several; N and P go through them). Another scene starts
   *  at its beginning. */
  get scene(): string | null {
    return this.#player?.scene ?? this.getAttribute("scene");
  }
  set scene(name: string | null) {
    this.currentTime = 0;
    if (name == null) this.removeAttribute("scene");
    else this.setAttribute("scene", name);
  }

  /** Seconds. */
  get currentTime(): number {
    return this.#player?.time ?? this.#wants.time;
  }
  set currentTime(t: number) {
    if (!Number.isFinite(Number(t))) return;
    if (this.#player) this.#player.time = Number(t);
    else this.#wants.time = Number(t);
    this.#after();
  }
  /** Seconds made so far; NaN before the film's first frame. */
  get duration(): number {
    return this.#player?.film ? this.#player.duration : NaN;
  }
  get paused(): boolean {
    return this.#player
      ? !this.#player.playing
      : !(this.#wants.playing ?? this.hasAttribute("autoplay"));
  }
  play(): void {
    if (this.#player) this.#player.play();
    else this.#wants.playing = true;
    this.#after();
  }
  pause(): void {
    if (this.#player) this.#player.pause();
    else this.#wants.playing = false;
    this.#after();
  }

  // ── the player ─────────────────────────────────────────────────────────────────────────

  async #begin(signal: AbortSignal): Promise<void> {
    if (this.#failed) return;
    if (!this.#begun) {
      this.#begun = true;
      const script = this.querySelector('script[type="text/python"]');
      if (script && this.#source === null) this.#source = dedent(script.textContent);
    }
    const { players, engine, failure } = begin();
    if (failure !== null) return this.#fail(failure);
    players.set(this.#film, {
      wait: () => this.#wait(),
      feed: (bytes) => this.#feed(bytes),
      fail: (error) => this.#fail(error),
    });
    this.#wait();
    if (this.#source !== null) this.#run();
    const canvas = this.#canvas;
    const box = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(box.width * devicePixelRatio));
    const height = Math.max(1, Math.round(box.height * devicePixelRatio));
    if (canvas.width !== width) canvas.width = width;
    if (canvas.height !== height) canvas.height = height;
    // An unattached element must not be retained by the page's pending runtime promise.
    const made = await Promise.race([
      engine,
      new Promise<undefined>((resolve) =>
        signal.addEventListener("abort", () => resolve(undefined), { once: true }),
      ),
    ]);
    if (!made || signal.aborted || this.#failed) return;
    try {
      const { time, playing } = this.#wants;
      this.#player = new made.Player(canvas, time, playing ?? this.hasAttribute("autoplay"), MAC);
      this.#player.resize(canvas.width, canvas.height, devicePixelRatio);
    } catch (error) {
      return this.#fail(error);
    }
    this.#said.remove();
    this.#wire(signal);
    for (const bytes of this.#backlog.splice(0)) this.#feed(bytes);
    this.#after();
  }

  #wait(): void {
    if (!this.#player && !this.#failed) this.#said.textContent = begin().status;
  }

  #fail(error: unknown): void {
    this.#failed = true;
    this.disconnectedCallback();
    this.#said.textContent = message(error);
    this.#root.append(this.#said);
  }

  #run(): void {
    if (this.#source === null || !page?.players.has(this.#film)) return;
    send(begin().director, {
      film: this.#film,
      run: { source: this.#source, scene: this.getAttribute("scene") },
    });
  }

  #feed(bytes: ArrayBuffer): void {
    if (this.#failed) return;
    if (!this.#player) {
      this.#backlog.push(bytes);
      return;
    }
    try {
      this.#player.feed(new Uint8Array(bytes));
    } catch (error) {
      return this.#fail(error);
    }
    // the film's own proportions (unless the page sizes the player itself)
    const film = this.#player.film;
    if (film) this.style.setProperty("--film", `${film[0]} / ${film[1]}`);
    this.#after();
  }

  /** What the viewer does, handed on as the web has it; what the player takes, the page doesn't. */
  #wire(signal: AbortSignal): void {
    const p = this.#player,
      canvas = this.#canvas;
    if (!p) return;
    const at = (e: PointerEvent): [number, number] => {
      const box = canvas.getBoundingClientRect();
      return [
        (e.clientX - box.left) * (canvas.width / box.width),
        (e.clientY - box.top) * (canvas.height / box.height),
      ];
    };
    // an event handed on (while this player is the element's: not after it failed), the default
    // action prevented if the player took it
    const on = <K extends keyof HTMLElementEventMap>(
      target: Pick<HTMLElement, "addEventListener">,
      type: K,
      hand: (event: HTMLElementEventMap[K]) => boolean | void,
      options?: AddEventListenerOptions,
    ): void =>
      target.addEventListener(
        type,
        (e) => {
          if (this.#player !== p) return;
          if (hand(e)) e.preventDefault();
          this.#after();
        },
        { ...options, signal },
      );
    let pressed: number | null = null; // the pointer that pressed: one at a time, its primary button or finger
    on(this, "keydown", (e) => p.key(e.key, e.ctrlKey, e.altKey, e.metaKey));
    on(canvas, "pointermove", (e) => p.pointer(...at(e)));
    on(canvas, "pointerdown", (e) => {
      if (pressed !== null || e.button !== 0 || !e.isPrimary) return false;
      pressed = e.pointerId;
      this.focus({ preventScroll: true });
      canvas.setPointerCapture(e.pointerId);
      return p.press(...at(e), e.pointerType === "touch");
    });
    const end = (e: PointerEvent, ended: () => boolean | void): boolean | void => {
      if (e.pointerId !== pressed) return false;
      pressed = null;
      return ended();
    };
    on(canvas, "pointerup", (e) => end(e, () => p.release()));
    on(canvas, "pointercancel", (e) => end(e, () => p.cancel()));
    on(canvas, "pointerleave", () => p.leave());
    on(
      canvas,
      "wheel",
      (e) => {
        const unit = [1, 20, canvas.clientHeight][e.deltaMode] ?? 1; // pixels, lines (as a window's), pages
        return p.wheel(e.deltaX * unit, e.deltaY * unit);
      },
      { passive: false },
    );
    on(document, "fullscreenchange", () => p.fullscreen(document.fullscreenElement === this));
    // drawn at the size the page shows it, in the screen's own pixels: sharp at any size
    const resize = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const box = entry.devicePixelContentBoxSize?.[0];
      const css = entry.contentBoxSize[0];
      if (!css) return;
      const w = box ? box.inlineSize : Math.round(css.inlineSize * devicePixelRatio);
      const h = box ? box.blockSize : Math.round(css.blockSize * devicePixelRatio);
      if (this.#player !== p) return;
      p.resize(w, h, w / css.inlineSize);
      this.#after();
    });
    resize.observe(canvas);
    // out of sight, it draws nothing (its clock and sound go on)
    const visibility = new IntersectionObserver(([entry]) => {
      if (!entry) return;
      if (this.#player !== p) return;
      p.hide(!entry.isIntersecting);
      this.#after();
    });
    visibility.observe(this);
    signal.addEventListener(
      "abort",
      () => {
        resize.disconnect();
        visibility.disconnect();
      },
      { once: true },
    );
  }

  /** What the player asks (its director to run another scene, full screen), its cursor, and its
   *  next picture, when it is due. */
  #after(): void {
    const p = this.#player;
    if (!p || !this.#connection || this.#connection.signal.aborted) return;
    for (const [ask, value] of p.asks()) {
      if (ask === "scene") {
        this.setAttribute("scene", value);
      } else if (ask === "fullscreen") {
        if (value)
          this.requestFullscreen?.().catch(() => {}); // refused: not full screen
        else if (document.fullscreenElement === this) document.exitFullscreen();
      }
    }
    this.#canvas.style.cursor = p.cursor;
    clearTimeout(this.#timer);
    let wake;
    try {
      wake = p.wake();
    } catch (error) {
      return this.#fail(error);
    }
    if (wake === 0) this.#frame ||= requestAnimationFrame(() => this.#draw());
    else if (wake > 0) this.#timer = setTimeout(() => this.#after(), wake);
  }

  #draw(): void {
    this.#frame = 0;
    try {
      this.#player?.draw();
    } catch (error) {
      return this.#fail(error);
    }
    this.#after();
  }
}

/** Python written indented in HTML, as the file it is. */
function dedent(text: string): string {
  const lines = text.replace(/^\n+|\s+$/g, "").split("\n");
  const indent = Math.min(...lines.filter((l) => l.trim()).map((l) => l.search(/\S/)));
  return lines.map((l) => l.slice(indent)).join("\n") + "\n";
}

/** Define <manimgx-player> (once `settings` are as they should be). */
export function define(): void {
  customElements.get("manimgx-player") ?? customElements.define("manimgx-player", ManimgxPlayer);
}

declare global {
  interface HTMLElementTagNameMap {
    "manimgx-player": ManimgxPlayer;
  }
}
