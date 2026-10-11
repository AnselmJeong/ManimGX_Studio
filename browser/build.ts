import { rm } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const output = join(root, "dist");
const { version } = (await Bun.file(join(root, "package.json")).json()) as {
  version: string;
};

// Compile the worker before putting its source in the player's single-file bundle.
const director = await Bun.build({
  entrypoints: [join(root, "src/director.ts")],
  target: "browser",
  format: "esm",
  minify: true,
});
if (!director.success) throw new AggregateError(director.logs, "Could not build the director");
const worker = director.outputs[0];
if (!worker) throw new Error("The director build produced no JavaScript");

await rm(output, { recursive: true, force: true });
const player = await Bun.build({
  entrypoints: [join(root, "src/index.ts")],
  target: "browser",
  format: "esm",
  minify: true,
  outdir: output,
  naming: "manimgx.js",
  define: {
    VERSION: JSON.stringify(version),
    DIRECTOR: JSON.stringify(await worker.text()),
  },
});
if (!player.success) throw new AggregateError(player.logs, "Could not build the player");
