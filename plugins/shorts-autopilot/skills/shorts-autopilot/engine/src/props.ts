/**
 * What the engine receives. The Python kit (kit/build.py) writes this file: it resolves every word reference to a
 * frame, every color token to a hex value, and lays out every text line (position and size) before rendering, so the
 * engine only draws. Nothing here is typed by hand.
 */
export interface Word {
  w: string;
  clean: string;
  /** Second the word starts. */
  a: number;
  /** Second the word ends. */
  end: number;
  endsSentence: boolean;
}

export type FontName = "anton" | "inter" | "grotesk" | "serif" | "mono";

export interface Style {
  accent: string;
  accent2: string;
  danger: string;
  ok: string;
  text: string;
  muted: string;
  bg: string;
  panel: string;
  font: FontName;
  subtitleFont: FontName;
}

export interface Line {
  text: string;
  from: number;
  to: number;
  x: number;
  y: number;
  size: number;
  color: string;
}

export interface Beat {
  from: number;
  to: number;
  lines: Line[];
}

export interface Background {
  image?: string;
  color: string;
  zoom: [number, number];
  panY: [number, number];
  dim: number;
  position: string;
  aiGenerated: boolean;
}

export interface Pill {
  text: string;
  from: number;
  to: number;
  background: string;
  color: string;
}

export type Element =
  | { type: "checklist"; from: number; to: number; items: { text: string; ok: boolean; from: number }[]; x: number; y: number; size: number; gap: number }
  | { type: "screen"; from: number; to: number; text: string; x: number; y: number; width: number; height: number }
  | { type: "timer"; from: number; to: number; fillBy: number; text: string; x: number; y: number; radius: number }
  | { type: "search"; from: number; to: number; title: string; query: string; typeFrom: number; result: string; resultFrom: number; x: number; y: number; width: number; height: number }
  | { type: "calendar"; from: number; to: number; month: string; day: string; x: number; y: number }
  | { type: "arrow"; from: number; to: number; x: number; y: number }
  | { type: "static"; from: number; to: number; opacity: number }
  | { type: "blackout"; from: number; to: number; duration: number }
  | { type: "source"; from: number; to: number; text: string; y: number };

export interface Scene {
  from: number;
  to: number;
  background: Background;
  kicker?: Pill;
  beats: Beat[];
  elements: Element[];
}

export interface ShortProps {
  [key: string]: unknown;
  fps: number;
  frames: number;
  words: Word[];
  style: Style;
  badge: { text: string; x: number; y: number } | null;
  aiImageLabel: string;
  aiImageLabelY: number;
  hits: number[];
  subtitles: { enabled: boolean; hide: [number, number][]; keywords: Record<string, string>; y: number; x: number; size: number; maxWidth: number };
  scenes: Scene[];
  grain: number;
  shake: { strength: number; frames: number };
  drift: { px: number; frames: number };
}
