/** Easing curves and animation helpers. */
import { Easing, interpolate, random, spring } from "remotion";

export const FPS = 30;

export const clamp = (x: number, a: number, b: number): number => Math.min(b, Math.max(a, x));
export const mix = (a: number, b: number, t: number): number => a + (b - a) * t;

/** Fast start, long brake: the editor curve for entrances. */
export const OUT = Easing.bezier(0.16, 1, 0.3, 1);
/** Smooth start and stop, for camera moves. */
export const SMOOTH = Easing.bezier(0.65, 0, 0.35, 1);
/** Pure acceleration, for exits. */
export const IN = Easing.bezier(0.7, 0, 0.84, 0);

/** 0 to 1 between frame `from` and `from + dur`, with a curve. */
export const prog = (frame: number, from: number, dur: number, curve = OUT): number =>
  interpolate(frame, [from, from + Math.max(1, dur)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: curve });

/** Spring that starts at frame `from`. */
export const springAt = (frame: number, from: number, config: { damping?: number; mass?: number; stiffness?: number } = {}): number =>
  spring({ frame: frame - from, fps: FPS, config: { damping: 14, mass: 0.6, stiffness: 180, ...config } });

/** Spring entrance (0 to 1) and a quick exit over the last `exit` frames. */
export function appear(frame: number, from: number, to: number, exit = 5): number {
  if (frame < from || frame >= to) return 0;
  const enter = springAt(frame, from, { damping: 15, stiffness: 210, mass: 0.6 });
  const leave = 1 - prog(frame, to - exit, exit);
  return Math.min(enter, leave);
}

/** Deterministic camera shake: hits on some frames that decay over `dur` frames. */
export function shake(frame: number, hits: number[], strength = 16, dur = 9): { dx: number; dy: number; rot: number } {
  let dx = 0;
  let dy = 0;
  let rot = 0;
  for (const h of hits) {
    const k = frame - h;
    if (k < 0 || k > dur) continue;
    const decay = Math.pow(1 - k / dur, 2);
    dx += (random(`sx${h}-${k}`) - 0.5) * 2 * strength * decay;
    dy += (random(`sy${h}-${k}`) - 0.5) * 2 * strength * decay;
    rot += (random(`sr${h}-${k}`) - 0.5) * 2 * (strength / 18) * 1.2 * decay;
  }
  return { dx, dy, rot };
}
