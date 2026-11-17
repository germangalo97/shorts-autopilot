/** SLAM: the line drops in from big (with motion blur) and sticks. (x, y) is the center of the line. */
import React from "react";
import { useCurrentFrame } from "remotion";
import { mix, OUT, prog } from "./anim";

export function Slam({ text, from, to, x, y, size, color, font, startScale = 2.4 }: {
  text: string;
  from: number;
  to: number;
  x: number;
  y: number;
  size: number;
  color: string;
  font: string;
  startScale?: number;
}): React.ReactElement | null {
  const frame = useCurrentFrame();
  if (frame < from || frame >= to) return null;
  const k = prog(frame, from, 5, OUT);
  const blur = (1 - k) * 14;
  return (
    <div
      style={{
        position: "absolute", left: x, top: y, fontFamily: font, fontSize: size, fontWeight: 400, color, lineHeight: 0.92,
        whiteSpace: "pre", textShadow: "0 20px 60px rgba(0,0,0,0.55)",
        transform: `translate(-50%, -50%) scale(${mix(startScale, 1, k)})`, opacity: Math.min(1, k * 3),
        filter: blur > 0.2 ? `blur(${blur}px)` : undefined,
      }}
    >
      {text}
    </div>
  );
}
