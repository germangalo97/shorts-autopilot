// Renders single frames of a composition with one bundle: used by the zone control (kit/zones.py) and for previews.
//   node scripts/stills.mjs <composition> <props.json> <public-dir> <out-dir> <frame...>
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const [, , id, propsPath, publicDir, outDir, ...frames] = process.argv;
if (!id || !propsPath || !publicDir || !outDir || frames.length === 0) {
  throw new Error("usage: node scripts/stills.mjs <composition> <props.json> <public-dir> <out-dir> <frame...>");
}
const inputProps = JSON.parse(fs.readFileSync(propsPath, "utf8"));
fs.mkdirSync(outDir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve(publicDir) });
const composition = await selectComposition({ serveUrl, id, inputProps, chromiumOptions: { gl: "angle" } });
for (const f of frames) {
  const output = path.join(outDir, `${id}_${String(f).padStart(5, "0")}.png`);
  await renderStill({ composition, serveUrl, output, frame: Number(f), inputProps, chromiumOptions: { gl: "angle" }, timeoutInMilliseconds: 120000 });
}
process.stdout.write(`${frames.length} frames -> ${outDir}\n`);
