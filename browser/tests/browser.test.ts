import { describe, expect, test } from "bun:test";
import { readFile } from "node:fs/promises";
import { createContext, SourceTextModule, SyntheticModule } from "node:vm";
import type * as BrowserAPI from "../dist/index.js";

const bundle = await readFile(new URL("../dist/manimgx.js", import.meta.url), "utf8");
const packageJSON = (await Bun.file(new URL("../package.json", import.meta.url)).json()) as {
  version: string;
};

// Each page gets its own globals and module, just as separate browser tabs do. Loading the
// emitted file also catches packaging mistakes that importing the TypeScript source misses.
async function page(
  script: string | null = null,
  failAt: "import" | "wasm" | "fonts" | null = null,
) {
  const tasks = new Map<number, () => void>();
  const frames = new Map<number, () => void>();
  let taskId = 0;
  const blobs: Blob[] = [];
  const elements = new Map<string, unknown>();
  const workers: Director[] = [];
  const natives: NativePlayer[] = [];
  const observers: Observer[] = [];
  const document = Object.assign(new EventTarget(), { fullscreenElement: null });
  class Observer {
    targets = new Set<unknown>();
    constructor(_callback: unknown) {
      observers.push(this);
    }
    observe(target: unknown) {
      this.targets.add(target);
    }
    disconnect() {
      this.targets.clear();
    }
  }
  class NativePlayer {
    time = 0;
    playing = false;
    cursor = "default";
    feeds: number[][] = [];
    fullscreenChanges = 0;
    wakeAfter = -1;
    frees = 0;
    constructor(_canvas: unknown, time: number, playing: boolean) {
      this.time = time;
      this.playing = playing;
      natives.push(this);
    }
    free() {
      this.frees++;
    }
    resize() {}
    pause() {
      this.playing = false;
    }
    asks() {
      return [];
    }
    wake() {
      return this.wakeAfter;
    }
    feed(bytes: Uint8Array) {
      if (bytes[0] === 255) throw new Error("decode failed");
      this.feeds.push([...bytes]);
    }
    fullscreen() {
      this.fullscreenChanges++;
    }
  }
  const waiting = { textContent: "", remove() {} };
  const canvas = Object.assign(new EventTarget(), {
    style: { cursor: "" },
    width: 0,
    height: 0,
    getBoundingClientRect: () => ({ width: 320, height: 180 }),
  });

  class Element extends EventTarget {
    isConnected = true;
    tabIndex = -1;
    style = { setProperty() {} };
    attributes = new Map<string, string>();
    shadowRoot = {
      innerHTML: "",
      querySelector: (selector: string) => (selector === "canvas" ? canvas : waiting),
      append() {},
    };
    attachShadow() {
      return this.shadowRoot;
    }
    querySelector() {
      return script === null ? null : { textContent: script };
    }
    hasAttribute(name: string) {
      return this.attributes.has(name);
    }
    getAttribute(name: string) {
      return this.attributes.get(name) ?? null;
    }
    setAttribute(name: string, value: string) {
      this.attributes.set(name, value);
      this.attributeChangedCallback();
    }
    removeAttribute(name: string) {
      this.attributes.delete(name);
      this.attributeChangedCallback();
    }
    attributeChangedCallback() {}
  }

  class Director {
    sent: unknown[] = [];
    onmessage: ((event: { data: unknown }) => Promise<void>) | null = null;
    onerror: ((event: { message: string }) => void) | null = null;
    terminations = 0;
    constructor(
      readonly url: string,
      readonly options: WorkerOptions,
    ) {
      workers.push(this);
    }
    postMessage(data: unknown) {
      this.sent.push(data);
    }
    terminate() {
      this.terminations++;
    }
  }

  const context = createContext({
    HTMLElement: Element,
    AbortController,
    document,
    ResizeObserver: Observer,
    IntersectionObserver: Observer,
    navigator: { platform: "Linux" },
    customElements: {
      get: (name: string) => elements.get(name),
      define: (name: string, value: unknown) => elements.set(name, value),
    },
    Worker: Director,
    Blob,
    URL: class extends URL {
      static override createObjectURL(blob: Blob) {
        blobs.push(blob);
        return `blob:test/${blobs.length}`;
      }
      static override revokeObjectURL() {}
    },
    devicePixelRatio: 2,
    setTimeout: (callback: () => void) => {
      tasks.set(++taskId, callback);
      return taskId;
    },
    clearTimeout: (id: number) => tasks.delete(id),
    requestAnimationFrame: (callback: () => void) => {
      frames.set(++taskId, callback);
      return taskId;
    },
    cancelAnimationFrame: (id: number) => frames.delete(id),
  });
  const engine = new SyntheticModule(
    ["default", "init", "Player"],
    function () {
      this.setExport("default", async () => {
        if (failAt === "wasm") throw new Error("wasm failed");
      });
      this.setExport("init", async () => {
        if (failAt === "fonts") throw new Error("fonts failed");
      });
      this.setExport("Player", NativePlayer);
    },
    { context },
  );
  await engine.link(() => {
    throw new Error("Unexpected engine import");
  });
  await engine.evaluate();
  const module = new SourceTextModule(bundle, {
    context,
    importModuleDynamically: () => {
      if (failAt === "import") throw new Error("import failed");
      return engine;
    },
  });
  await module.link(() => {
    throw new Error("The published player must be one self-contained module");
  });
  await module.evaluate();
  const api = module.namespace as typeof BrowserAPI;
  return {
    api,
    blobs,
    elements,
    workers,
    natives,
    observers,
    document,
    timers: tasks,
    frames,
    waiting,
    canvas,
    flush: () => {
      const batch = [...tasks.values()];
      tasks.clear();
      batch.forEach((task) => task());
    },
  };
}

async function settle() {
  // Boot, micropip installation and queued runs all yield to promises. The worker's explicit
  // task boundary stays under the test's control, so these checks don't depend on wall time.
  for (let i = 0; i < 30; i++) await Promise.resolve();
}

describe("published browser module", () => {
  test("registers the public element and pins the Python package to its own version", async () => {
    const { api, elements, workers } = await page();
    expect(elements.get("manimgx-player")).toBe(api.ManimgxPlayer);
    expect(api.settings.manimgx).toBe(`manimgx==${packageJSON.version}`);
    expect(workers).toHaveLength(0);
  });

  test("keeps playback requests made before the engine arrives", async () => {
    const { api } = await page();
    const player = new api.ManimgxPlayer();
    expect(player.source).toBeNull();
    expect(player.scene).toBeNull();
    expect(player.duration).toBeNaN();
    expect(player.paused).toBe(true);
    player.setAttribute("autoplay", "");
    expect(player.paused).toBe(false);
    player.pause();
    expect(player.paused).toBe(true);
    player.play();
    expect(player.paused).toBe(false);
    player.currentTime = 2.5;
    player.currentTime = NaN;
    player.currentTime = Infinity;
    expect(player.currentTime).toBe(2.5);
    player.scene = "SecondScene";
    expect(player.scene).toBe("SecondScene");
    expect(player.currentTime).toBe(0);
    player.source = "class SecondScene(Scene): pass";
    expect(player.source).toBe("class SecondScene(Scene): pass");
    player.source = null;
    player.scene = null;
    expect(player.source).toBeNull();
    expect(player.scene).toBeNull();
  });

  test("boots once after settings are set and sends dedented scenes and subsequent edits", async () => {
    const state = await page("\n    class Demo(Scene):\n        pass\n  ");
    const player = new state.api.ManimgxPlayer();
    player.connectedCallback();
    state.api.settings.pyodide = "https://example.test/python/";
    state.api.settings.manimgx = "https://example.test/manimgx.whl";
    expect(state.workers).toHaveLength(0);
    state.flush();
    const director = state.workers[0]!;
    expect(director.options).toEqual({ type: "module" });
    expect(director.sent).toEqual([
      {
        boot: {
          pyodide: "https://example.test/python/",
          manimgx: "https://example.test/manimgx.whl",
        },
      },
      { film: 1, run: { source: "class Demo(Scene):\n    pass\n", scene: null } },
    ]);
    expect(state.canvas).toMatchObject({ width: 640, height: 360 });
    expect(player.tabIndex).toBe(0);
    await director.onmessage!({ data: { status: "Installing ManimGX…" } });
    expect(state.waiting.textContent).toBe("Installing ManimGX…");
    player.source = "class Changed(Scene): pass";
    expect(director.sent.at(-1)).toEqual({ film: 1, run: { source: player.source, scene: null } });
    player.scene = "Changed";
    expect(director.sent.at(-1)).toEqual({
      film: 1,
      run: { source: player.source, scene: "Changed" },
    });
    player.disconnectedCallback();
    player.connectedCallback();
    state.flush();
    expect(state.workers).toHaveLength(1);
    expect(director.sent).toHaveLength(6);
  });

  test("disconnecting frees native resources and subscriptions; reconnecting preserves the time", async () => {
    const state = await page();
    const player = new state.api.ManimgxPlayer();
    player.source = "first";
    player.connectedCallback();
    state.flush();
    const director = state.workers[0]!;
    await director.onmessage!({ data: { engine: { js: "", wasm: new Uint8Array(), fonts: [] } } });
    await settle();
    expect(state.natives).toHaveLength(1);
    expect(state.observers.filter((observer) => observer.targets.size)).toHaveLength(2);
    state.natives[0]!.wakeAfter = 0;
    player.currentTime = 1.25;
    expect(state.frames.size).toBe(1);
    state.natives[0]!.wakeAfter = 20;
    player.currentTime = 1.25;
    expect(state.timers.size).toBe(1);
    state.document.dispatchEvent(new Event("fullscreenchange"));
    expect(state.natives[0]!.fullscreenChanges).toBe(1);

    Object.defineProperty(player, "isConnected", { value: false, writable: true });
    player.disconnectedCallback();
    player.disconnectedCallback(); // teardown is idempotent
    expect(state.natives[0]!.playing).toBe(false);
    expect(state.natives[0]!.frees).toBe(1);
    expect(state.frames.size).toBe(0);
    expect(state.timers.size).toBe(0);
    state.natives[0]!.wakeAfter = -1;
    expect(state.observers.every((observer) => observer.targets.size === 0)).toBe(true);
    state.document.dispatchEvent(new Event("fullscreenchange"));
    expect(state.natives[0]!.fullscreenChanges).toBe(1);
    await director.onmessage!({ data: { film: 1, feed: new Uint8Array([1]).buffer } });
    expect(state.natives[0]!.feeds).toEqual([]);
    const sent = director.sent.length;
    player.source = "edited while detached";
    expect(director.sent).toHaveLength(sent);

    Object.defineProperty(player, "isConnected", { value: true });
    player.connectedCallback();
    state.flush();
    await settle();
    expect(state.natives).toHaveLength(2);
    expect(player.currentTime).toBe(1.25);
    expect(player.paused).toBe(true);
    expect(state.observers.filter((observer) => observer.targets.size)).toHaveLength(2);
    expect(director.sent.at(-1)).toEqual({
      film: 2,
      run: { source: "edited while detached", scene: null },
    });
    state.document.dispatchEvent(new Event("fullscreenchange"));
    expect(state.natives[0]!.fullscreenChanges).toBe(1);
    expect(state.natives[1]!.fullscreenChanges).toBe(1);
    // The previous run may still be sending bytes when this connection's native decoder is
    // empty. A continuation from that old take must never enter the new decoder.
    await director.onmessage!({ data: { film: 1, feed: new Uint8Array([255]).buffer } });
    expect(state.natives[1]!.frees).toBe(0);
    await director.onmessage!({ data: { film: 2, feed: new Uint8Array([2]).buffer } });
    expect(state.natives[0]!.feeds).toEqual([]);
    expect(state.natives[1]!.feeds).toEqual([[2]]);
    await director.onmessage!({ data: { film: 2, feed: new Uint8Array([255]).buffer } });
    expect(state.natives[1]!.frees).toBe(1);
    expect(state.observers.every((observer) => observer.targets.size === 0)).toBe(true);
    expect(state.waiting.textContent).toBe("decode failed");
  });

  test("disconnecting during boot does not create an orphan native player", async () => {
    const state = await page();
    const player = new state.api.ManimgxPlayer();
    player.source = "first";
    player.connectedCallback();
    state.flush();
    Object.defineProperty(player, "isConnected", { value: false, writable: true });
    player.disconnectedCallback();
    await state.workers[0]!.onmessage!({
      data: { engine: { js: "", wasm: new Uint8Array(), fonts: [] } },
    });
    await settle();
    expect(state.natives).toHaveLength(0);
    Object.defineProperty(player, "isConnected", { value: true });
    player.connectedCallback();
    state.flush();
    await settle();
    expect(state.natives).toHaveLength(1);
  });

  test("an old connection cannot create a second player when boot finishes after reconnect", async () => {
    const state = await page();
    const player = new state.api.ManimgxPlayer();
    player.connectedCallback();
    state.flush();
    player.disconnectedCallback();
    player.connectedCallback();
    state.flush();
    await state.workers[0]!.onmessage!({
      data: { engine: { js: "", wasm: new Uint8Array(), fonts: [] } },
    });
    await settle();
    expect(state.natives).toHaveLength(1);
    expect(state.observers.filter((observer) => observer.targets.size)).toHaveLength(2);
  });

  test.each(["import", "wasm", "fonts", "worker", "boot"] as const)(
    "%s initialization failure is terminal for existing and future players",
    async (failure) => {
      const state = await page(
        null,
        ["worker", "boot"].includes(failure) ? null : (failure as "import" | "wasm" | "fonts"),
      );
      const player = new state.api.ManimgxPlayer();
      player.source = "first";
      player.connectedCallback();
      state.flush();
      const director = state.workers[0]!;
      await director.onmessage!({ data: { film: 1, feed: new Uint8Array([1]).buffer } });
      if (failure === "worker") director.onerror!({ message: "worker failed" });
      else if (failure === "boot") await director.onmessage!({ data: { failure: "boot failed" } });
      else
        await director.onmessage!({
          data: { engine: { js: "", wasm: new Uint8Array(), fonts: [] } },
        });
      await settle();
      expect(state.waiting.textContent).toContain(`${failure} failed`);
      expect(director.terminations).toBe(1);
      const sent = director.sent.length;
      player.source = "cannot run";
      const later = new state.api.ManimgxPlayer();
      later.source = "cannot run either";
      later.connectedCallback();
      state.flush();
      await settle();
      expect(director.sent).toHaveLength(sent);
      expect(state.natives).toHaveLength(0);
      expect(state.waiting.textContent).toContain(`${failure} failed`);
      // Even a late successful boot message cannot resurrect this failed runtime or replay
      // bytes that arrived before initialization failed.
      await director.onmessage!({
        data: { engine: { js: "", wasm: new Uint8Array(), fonts: [] } },
      });
      await settle();
      expect(state.natives).toHaveLength(0);
    },
  );

  test("the embedded worker coalesces edits and isolates film failures", async () => {
    const state = await page();
    new state.api.ManimgxPlayer().connectedCallback();
    state.flush();
    const source = await state.blobs[0]!.text();
    const messages: { data: unknown; transfer: unknown[] }[] = [];
    const imports: string[] = [];
    const installs: string[] = [];
    const runs: { film: number; source: string; scene: string | null; tried: string[] }[] = [];
    const drops: number[] = [];
    const tasks: (() => void)[] = [];
    let destroyed = false;
    let allowBoot!: () => void;
    let allowImports: (() => void) | undefined;
    const bootGate = new Promise<void>((resolve) => {
      allowBoot = resolve;
    });
    const wasm = new Uint8Array([0, 97, 115, 109]);
    const fonts = [new Uint8Array([1, 2])];
    const runner = (
      film: number,
      source: string,
      scene: string | null,
      send: (bytes: Uint8Array) => void,
      tried: string[],
    ) => {
      if (source === "broken runner") throw new Error("Python worker failure");
      runs.push({ film, source, scene, tried: [...tried] });
      if (source === "latest" && !tried.includes("networkx")) return "networkx";
      send(new Uint8Array([film]));
      return null;
    };
    const pyodide = {
      loadPackage: async (name: string) => {
        expect(name).toBe("micropip");
      },
      pyimport: (name: string) => {
        expect(name).toBe("micropip");
        return {
          install: async (requirement: string) => {
            installs.push(requirement);
          },
        };
      },
      runPython: (source: string) =>
        source.includes("def run(")
          ? runner
          : source === "drop"
            ? (film: number) => drops.push(film)
            : source.startsWith("lambda text:")
              ? (text: string) => new TextEncoder().encode(text)
              : {
                  toJs: () => ["engine source", wasm, fonts],
                  destroy: () => {
                    destroyed = true;
                  },
                },
      loadPackagesFromImports: async (source: string) => {
        if (source === "broken imports") throw new Error("Package download failed");
        if (source === "pending imports")
          await new Promise<void>((resolve) => {
            allowImports = resolve;
          });
        imports.push(source);
      },
    };
    const global = {
      onmessage: null as ((event: { data: unknown }) => void) | null,
      postMessage: (data: unknown, transfer: unknown[] = []) => {
        messages.push({ data, transfer });
      },
      setTimeout: (callback: () => void) => tasks.push(callback),
    };
    const context = createContext(global);
    const pythonModule = new SyntheticModule(
      ["loadPyodide"],
      function () {
        this.setExport("loadPyodide", async (options: { indexURL: string }) => {
          expect(options.indexURL).toBe("https://example.test/python/");
          await bootGate;
          return pyodide;
        });
      },
      { context },
    );
    await pythonModule.link(() => {
      throw new Error("Unexpected dependency");
    });
    await pythonModule.evaluate();
    const worker = new SourceTextModule(source, {
      context,
      importModuleDynamically: (specifier) => {
        expect(specifier).toBe("https://example.test/python/pyodide.mjs");
        return pythonModule;
      },
    });
    await worker.link(() => {
      throw new Error("The embedded director must be self-contained");
    });
    await worker.evaluate();
    const send = (data: unknown) => global.onmessage!({ data });
    send({ boot: { pyodide: "https://example.test/python/", manimgx: "manimgx==test" } });
    send({ film: 1, run: { source: "stale", scene: null } });
    send({ film: 1, run: { source: "latest", scene: "Demo" } });
    send({ film: 2, run: { source: "other", scene: null } });
    send({ film: 9, run: { source: "detached before boot", scene: null } });
    send({ film: 9, drop: true });
    allowBoot();
    await settle();
    expect(installs).toEqual(["manimgx==test", "networkx"]);
    expect(destroyed).toBe(true);
    expect(messages.slice(0, 3)).toEqual([
      { data: { status: "Loading Python…" }, transfer: [] },
      { data: { status: "Installing ManimGX…" }, transfer: [] },
      {
        data: { engine: { js: "engine source", wasm, fonts } },
        transfer: [wasm.buffer, fonts[0]!.buffer],
      },
    ]);
    expect(runs).toEqual([
      { film: 1, source: "latest", scene: "Demo", tried: [] },
      { film: 1, source: "latest", scene: "Demo", tried: ["networkx"] },
    ]);
    tasks.splice(0).forEach((task) => task());
    await settle();
    expect(imports).toEqual(["latest", "other"]);
    expect(runs.at(-1)).toEqual({ film: 2, source: "other", scene: null, tried: [] });
    const feeds = messages.slice(3) as {
      data: { film: number; feed: ArrayBuffer };
      transfer: unknown[];
    }[];
    expect(feeds.map(({ data }) => [data.film, ...new Uint8Array(data.feed)])).toEqual([
      [1, 1],
      [2, 2],
    ]);
    for (const { data, transfer } of feeds) expect(transfer).toEqual([data.feed]);
    tasks.splice(0).forEach((task) => task());
    await settle();
    expect(drops).toEqual([9]);
    // Teardown of one lifetime cannot erase the newly connected film's source directory.
    send({ film: 2, drop: true });
    send({ film: 5, run: { source: "reconnected", scene: null } });
    await settle();
    expect(drops).toEqual([9, 2]);
    expect(runs.at(-1)).toMatchObject({ film: 5, source: "reconnected" });

    // A failed dependency load or Python call belongs to one film. It must not lock the
    // shared queue, and editing that same film must remain possible afterward.
    for (const [source, error] of [
      ["broken imports", "Package download failed"],
      ["broken runner", "Python worker failure"],
    ]) {
      tasks.splice(0).forEach((task) => task());
      await settle();
      send({ film: 3, run: { source, scene: null } });
      send({ film: 4, run: { source: "next film", scene: null } });
      await settle();
      const failed = messages.at(-1)!.data as { film: number; feed: ArrayBuffer };
      expect(failed.film).toBe(3);
      expect(JSON.parse(new TextDecoder().decode(failed.feed))).toEqual({
        error: { message: error, type: "Error" },
      });
      tasks.splice(0).forEach((task) => task());
      await settle();
      expect(runs.at(-1)).toMatchObject({ film: 4, source: "next film" });
      send({ film: 3, run: { source: "corrected", scene: null } });
      tasks.splice(0).forEach((task) => task());
      await settle();
      expect(runs.at(-1)).toMatchObject({ film: 3, source: "corrected" });
    }
    tasks.splice(0).forEach((task) => task());
    await settle();
    send({ film: 6, run: { source: "pending imports", scene: null } });
    await settle();
    send({ film: 6, drop: true });
    send({ film: 7, run: { source: "new connection", scene: null } });
    await settle();
    expect(drops).not.toContain(6);
    allowImports!();
    await settle();
    expect(runs.at(-1)).toMatchObject({ film: 6, source: "pending imports" });
    expect(drops).not.toContain(6);
    tasks.splice(0).forEach((task) => task());
    await settle();
    expect(drops.at(-1)).toBe(6);
    expect(runs.at(-1)).toMatchObject({ film: 7, source: "new connection" });
  });

  test("the embedded worker reports a terminal boot failure and rejects later runs", async () => {
    const state = await page();
    new state.api.ManimgxPlayer().connectedCallback();
    state.flush();
    const messages: unknown[] = [];
    const global = {
      onmessage: null as ((event: { data: unknown }) => void) | null,
      postMessage: (data: unknown) => messages.push(data),
    };
    const worker = new SourceTextModule(await state.blobs[0]!.text(), {
      context: createContext(global),
      importModuleDynamically: () => {
        throw new Error("Python download failed");
      },
    });
    await worker.link(() => {
      throw new Error("Unexpected dependency");
    });
    await worker.evaluate();
    global.onmessage!({ data: { boot: { pyodide: "https://example.test/", manimgx: "test" } } });
    global.onmessage!({ data: { film: 1, run: { source: "queued", scene: null } } });
    await settle();
    expect(messages).toEqual([
      { status: "Loading Python…" },
      { failure: "ManimGX could not start: Python download failed" },
    ]);
    global.onmessage!({
      data: {
        film: 2,
        get run() {
          throw new Error("A failed worker must not accept more source");
        },
      },
    });
    await settle();
    expect(messages).toHaveLength(2);
  });
});
