import React from "react";
import { Composition } from "remotion";
import type { ShortProps } from "./props";
import { Short, ShortControl } from "./Short";

const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

/** Placeholder props so the studio opens; real renders always pass --props=<video>/build/props.json. */
const EMPTY: ShortProps = {
  fps: FPS,
  frames: 90,
  words: [],
  style: { accent: "#D7FF3E", accent2: "#FFD23F", danger: "#FF3B3B", ok: "#2BD46B", text: "#FFFFFF", muted: "#8A8F98", bg: "#0E0E0E", panel: "#16181D", font: "anton", subtitleFont: "inter" },
  badge: null,
  aiImageLabel: "",
  aiImageLabelY: 1225,
  hits: [],
  subtitles: { enabled: false, hide: [], keywords: {}, y: 1360, x: 495, size: 80, maxWidth: 780 },
  scenes: [],
  grain: 0.05,
  shake: { strength: 16, frames: 9 },
  drift: { px: 10, frames: 150 },
};

const metadata = ({ props }: { props: ShortProps }) => ({ durationInFrames: Math.max(1, Math.round(props.frames)) });

export function Root(): React.ReactElement {
  return (
    <>
      <Composition id="Short" component={Short} durationInFrames={EMPTY.frames} fps={FPS} width={WIDTH} height={HEIGHT} defaultProps={EMPTY} calculateMetadata={metadata} />
      <Composition id="ShortControl" component={ShortControl} durationInFrames={EMPTY.frames} fps={FPS} width={WIDTH} height={HEIGHT} defaultProps={EMPTY} calculateMetadata={metadata} />
    </>
  );
}
