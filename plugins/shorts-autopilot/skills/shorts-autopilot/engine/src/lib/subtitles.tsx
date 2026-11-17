/**
 * Word-by-word subtitles: short groups (by word count, letter count and sentence end), the word being said is
 * highlighted. Groups that would not fit `maxWidth` are scaled down as a whole (width is estimated, then measured by
 * the zone control).
 */
import React from "react";
import { useCurrentFrame } from "remotion";
import { clamp, FPS, springAt } from "./anim";
import type { Word } from "../props";

const NEW_GROUP_GAP_S = 0.35;
const TAIL_S = 0.18;
const MAX_WORDS = 3;
const MAX_LETTERS = 13;
const LETTER_WIDTH = 0.7;
const ACTIVE_SCALE = 1.08;
const SPACING = 0.36;

interface Group {
  words: Word[];
  a: number;
  end: number;
}

export function makeGroups(words: Word[]): Group[] {
  const groups: Group[] = [];
  let current: Word[] = [];
  const close = (): void => {
    if (current.length) groups.push({ words: current, a: current[0].a, end: current[current.length - 1].end });
    current = [];
  };
  words.forEach((p, i) => {
    const letters = current.reduce((s, q) => s + q.clean.length + 1, 0);
    const prev = i > 0 ? words[i - 1] : null;
    if (current.length >= MAX_WORDS || letters + p.clean.length > MAX_LETTERS || (prev && prev.endsSentence) || (prev && p.a - prev.end > NEW_GROUP_GAP_S)) {
      close();
    }
    current.push(p);
  });
  close();
  return groups.map((g, i) => ({ ...g, end: Math.min(g.end + TAIL_S, i + 1 < groups.length ? groups[i + 1].a : g.end + TAIL_S) }));
}

const strip = (t: string): string => t.replace(/[.,;:]+$/, "");

function estimatedWidth(g: Group, size: number): number {
  const letters = g.words.reduce((s, p) => s + strip(p.w).length, 0);
  return size * (LETTER_WIDTH * letters + (g.words.length - 1) * SPACING) * ACTIVE_SCALE;
}

export function Subtitles({ words, font, size, x, y, maxWidth, color, activeColor, keywords, hide }: {
  words: Word[];
  font: string;
  size: number;
  x: number;
  y: number;
  maxWidth: number;
  color: string;
  activeColor: string;
  keywords: Record<string, string>;
  hide: [number, number][];
}): React.ReactElement | null {
  const frame = useCurrentFrame();
  const groups = React.useMemo(() => makeGroups(words), [words]);
  if (hide.some(([a, b]) => frame >= a && frame < b)) return null;
  const s = frame / FPS;
  const g = groups.find((q) => s >= q.a && s < q.end);
  if (!g) return null;
  const enter = springAt(frame, Math.round(g.a * FPS), { damping: 13, stiffness: 260, mass: 0.5 });
  const active = [...g.words].reverse().find((p) => p.a <= s + 1e-6) ?? g.words[0];
  const fit = Math.min(1, maxWidth / estimatedWidth(g, size));
  return (
    <div
      style={{
        position: "absolute", left: 0, right: 0, top: y,
        transform: `translateX(${x - 540}px) translateY(-50%) scale(${(0.82 + 0.18 * enter) * fit})`,
        opacity: clamp(enter * 2.5, 0, 1), display: "flex", justifyContent: "center", gap: `${size * SPACING}px`,
        fontFamily: font, fontSize: size, fontWeight: 900, textTransform: "uppercase", lineHeight: 1,
      }}
    >
      {g.words.map((p, i) => {
        const isActive = p === active;
        const keyColor = keywords[p.clean];
        const pop = isActive ? springAt(frame, Math.round(p.a * FPS), { damping: 12, stiffness: 300, mass: 0.4 }) : 1;
        return (
          <span
            key={i}
            style={{
              display: "inline-block", transform: `scale(${isActive ? 1 + (ACTIVE_SCALE - 1) * pop : 1})`,
              color: isActive ? keyColor ?? activeColor : keyColor ?? color,
              WebkitTextStroke: "10px #000", paintOrder: "stroke fill", textShadow: "0 6px 0 rgba(0,0,0,0.4)",
            }}
          >
            {strip(p.w)}
          </span>
        );
      })}
    </div>
  );
}
