// ManimGX in the browser: <manimgx-player>, a scene written in Python, run by Pyodide and played by
// ManimGX's own player, drawn with WebGPU. ManimGX itself comes from PyPI, the version of this
// package. This file is all of it: its worker is inside it, so any bundler (or none) can take it.

import { define, runtime, settings } from "./player.js";

declare const VERSION: string;
declare const DIRECTOR: string;

runtime.worker = () => URL.createObjectURL(new Blob([DIRECTOR], { type: "text/javascript" }));
settings.manimgx = `manimgx==${VERSION}`;
define();

export { ManimgxPlayer, settings } from "./player.js";
