/** The wasm-bindgen interface exported by rust/engine/src/web.rs. */
export interface Engine {
  default(options: { module_or_path: Uint8Array<ArrayBuffer> }): Promise<unknown>;
  init(fonts: Uint8Array<ArrayBuffer>[]): Promise<void>;
  Player: new (canvas: HTMLCanvasElement, time: number, playing: boolean, mac: boolean) => Player;
}

export interface Player {
  free(): void;
  feed(bytes: Uint8Array): void;
  key(key: string, ctrl: boolean, alt: boolean, meta: boolean): boolean;
  pointer(x: number, y: number): void;
  press(x: number, y: number, touch: boolean): boolean;
  release(): boolean;
  leave(): void;
  cancel(): void;
  wheel(dx: number, dy: number): boolean;
  resize(width: number, height: number, scale: number): void;
  hide(hidden: boolean): void;
  fullscreen(on: boolean): void;
  wake(): number;
  draw(): void;
  asks(): (["scene", string] | ["fullscreen", boolean])[];
  readonly cursor: string;
  time: number;
  readonly duration: number;
  readonly playing: boolean;
  play(): void;
  pause(): void;
  readonly scene: string | undefined;
  readonly film: Uint32Array | undefined;
}
