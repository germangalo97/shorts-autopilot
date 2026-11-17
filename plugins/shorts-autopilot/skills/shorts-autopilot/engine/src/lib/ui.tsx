/** Label pill (chapter, source, made-with-AI badge). */
import React from "react";
import { useCurrentFrame } from "remotion";
import { clamp, IN, prog, springAt } from "./anim";

export function PillLabel({ text, from, to, x, y, font, background, color, size = 44, anchor = "center" }: {
  text: string;
  from: number;
  to: number;
  x: number;
  y: number;
  font: string;
  background: string;
  color: string;
  size?: number;
  anchor?: "center" | "left";
}): React.ReactElement | null {
  const frame = useCurrentFrame();
  if (frame < from || frame >= to) return null;
  const r = springAt(frame, from, { damping: 12, stiffness: 260, mass: 0.5 });
  const leave = prog(frame, to - 6, 6, IN);
  return (
    <div
      style={{
        position: "absolute", left: x, top: y,
        transform: `translate(${anchor === "center" ? "-50%" : "0"}, -50%) scale(${(0.5 + 0.5 * r) * (1 - 0.2 * leave)})`,
        opacity: clamp(r * 2, 0, 1) * (1 - leave), background, color, fontFamily: font, fontWeight: 800, fontSize: size,
        padding: `${size * 0.28}px ${size * 0.6}px`, borderRadius: size, whiteSpace: "nowrap", boxShadow: "0 14px 40px rgba(0,0,0,0.35)",
      }}
    >
      {text}
    </div>
  );
}
