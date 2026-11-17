/** Image effects: film grain and flashes. */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { OUT, prog } from "./anim";

export function Grain({ opacity = 0.05 }: { opacity?: number }): React.ReactElement {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const seed = (frame * 7) % 211;
  const id = `grain-${seed}`;
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity, pointerEvents: "none" }}>
      <svg width={width} height={height}>
        <filter id={id}>
          <feTurbulence type="fractalNoise" baseFrequency={0.9} numOctaves={2} seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#${id})`} />
      </svg>
    </AbsoluteFill>
  );
}

/** Flash: a frame of color that fades out over `dur` frames. */
export function Flash({ at, dur = 6, color = "#ffffff", max = 1 }: { at: number; dur?: number; color?: string; max?: number }): React.ReactElement | null {
  const frame = useCurrentFrame();
  if (frame < at || frame > at + dur) return null;
  const o = max * (1 - prog(frame, at, dur, OUT));
  return <AbsoluteFill style={{ background: color, opacity: o, pointerEvents: "none" }} />;
}
