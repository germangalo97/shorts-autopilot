/** Background photo with a slow move (Ken Burns), cropped to the screen. Hidden in control mode. */
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { SMOOTH } from "./anim";
import { TextOnly } from "./control";

function Moved({ zoom, panY, dur, children }: { zoom: [number, number]; panY: [number, number]; dur: number; children: React.ReactNode }): React.ReactElement {
  const frame = useCurrentFrame();
  const k = interpolate(frame, [0, Math.max(1, dur)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SMOOTH });
  const z = zoom[0] + (zoom[1] - zoom[0]) * k;
  const y = panY[0] + (panY[1] - panY[0]) * k;
  return <AbsoluteFill style={{ transform: `translate(0px, ${y}px) scale(${z})` }}>{children}</AbsoluteFill>;
}

export function Photo({ src, from, to, zoom, panY, dim, position }: {
  src: string;
  from: number;
  to: number;
  zoom: [number, number];
  panY: [number, number];
  dim: number;
  position: string;
}): React.ReactElement | null {
  const textOnly = React.useContext(TextOnly);
  if (textOnly) return null;
  const dur = to - from;
  return (
    <Sequence from={from} durationInFrames={dur} layout="none">
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <Moved zoom={zoom} panY={panY} dur={dur}>
          <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: position, filter: `brightness(${dim}) contrast(1.08)` }} />
        </Moved>
      </AbsoluteFill>
    </Sequence>
  );
}
