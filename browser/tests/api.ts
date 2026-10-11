// Compile this like a consumer of the published declarations, without the package's source.
import { ManimgxPlayer, settings } from "manimgx";

const player: ManimgxPlayer = document.createElement("manimgx-player");
player.source = "class Demo(Scene): pass";
player.source = null;
player.scene = "Demo";
player.scene = null;
player.currentTime = 1.5;
player.play();
player.pause();
const duration: number = player.duration;
const paused: boolean = player.paused;
const source: string | null = player.source;
const scene: string | null = player.scene;
settings.pyodide = "https://example.test/pyodide/";
settings.manimgx = "https://example.test/manimgx.whl";

// @ts-expect-error Python source must be text.
player.source = 1;
// @ts-expect-error Playback positions use seconds as numbers.
player.currentTime = "1.5";
// @ts-expect-error Duration is reported by the engine and is read-only.
player.duration = 10;
// @ts-expect-error Call play() or pause() to change playback.
player.paused = true;
// @ts-expect-error Package requirements and wheel URLs are strings.
settings.manimgx = 1;

void [duration, paused, source, scene];
