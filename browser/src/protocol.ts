/** Messages shared by the page and its Python worker. */
export interface Boot {
  pyodide: string;
  manimgx: string;
}

export interface Run {
  source: string;
  scene: string | null;
}

export type ToDirector = { boot: Boot } | { film: number; run: Run } | { film: number; drop: true };

/** These byte arrays originate in Pyodide and own transferable ArrayBuffers. */
export interface EngineFiles {
  js: string;
  wasm: Uint8Array<ArrayBuffer>;
  fonts: Uint8Array<ArrayBuffer>[];
}

export type FromDirector =
  | { status: string }
  | { failure: string }
  | { engine: EngineFiles }
  | { film: number; feed: ArrayBuffer };

export function message(error: unknown): string {
  return String(
    typeof error === "object" && error !== null && "message" in error
      ? (error.message ?? error)
      : error,
  );
}
