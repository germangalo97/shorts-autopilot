/**
 * The short: scenes (background + kicker + beats of slamming lines + pieces), word-by-word subtitles, the always-on
 * made-with-AI badge, an AI label over every AI image, shake and flash on hit words, slow vertical drift and grain.
 * Every frame number comes from props (kit/build.py); nothing is timed by hand here.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { shake } from "./lib/anim";
import { TextOnly } from "./lib/control";
import { FONTS } from "./lib/fonts";
import { Flash, Grain } from "./lib/fx";
import { Photo } from "./lib/photo";
import { Subtitles } from "./lib/subtitles";
import { Slam } from "./lib/type";
import { PillLabel } from "./lib/ui";
import { Piece } from "./pieces/pieces";
import type { Scene, ShortProps } from "./props";

const KICKER_Y = 330;
const GLOW_CYCLE_FRAMES = 140;

/**
 * Plain-color scenes get a slow moving glow: a flat color with still text froze the picture for 0.6-0.8 s in the
 * test render (measured with ffmpeg freezedetect), and something on screen has to change all the time.
 */
function MovingGlow({ from, accent, accent2 }: { from: number; accent: string; accent2: string }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  if (textOnly) return null;
  const k = ((frame - from) / GLOW_CYCLE_FRAMES) * Math.PI * 2;
  const x1 = 50 + 30 * Math.sin(k);
  const y1 = 38 + 14 * Math.cos(k * 0.7);
  const x2 = 50 - 34 * Math.cos(k * 0.8);
  const y2 = 72 + 12 * Math.sin(k * 1.1);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${x1}% ${y1}%, ${accent}38 0%, transparent 45%), radial-gradient(circle at ${x2}% ${y2}%, ${accent2}26 0%, transparent 40%)`,
      }}
    />
  );
}
const BADGE_SIZE = 28;

function SceneView({ scene, props }: { scene: Scene; props: ShortProps }): React.ReactElement | null {
  const frame = useCurrentFrame();
  if (frame < scene.from || frame >= scene.to) return null;
  const { style } = props;
  const bg = scene.background;
  return (
    <>
      <AbsoluteFill style={{ background: bg.color }} />
      {!bg.image && <MovingGlow from={scene.from} accent={style.accent} accent2={style.accent2} />}
      {bg.image && <Photo src={bg.image} from={scene.from} to={scene.to} zoom={bg.zoom} panY={bg.panY} dim={bg.dim} position={bg.position} />}
      {scene.elements.map((el, i) => <Piece key={`e${i}`} el={el} style={style} />)}
      {scene.kicker && <PillLabel text={scene.kicker.text} from={scene.kicker.from} to={scene.kicker.to} x={540} y={KICKER_Y} font={FONTS.inter} size={46} background={scene.kicker.background} color={scene.kicker.color} />}
      {scene.beats.map((b) =>
        frame >= b.from && frame < b.to ? (
          <React.Fragment key={`b${b.from}`}>
            {b.lines.map((l, j) => (
              <Slam key={j} text={l.text} from={l.from} to={l.to} x={l.x} y={l.y} size={l.size} color={l.color} font={FONTS[style.font]} startScale={j === 0 ? 2.2 : 2.6} />
            ))}
          </React.Fragment>
        ) : null,
      )}
      {bg.image && bg.aiGenerated && props.aiImageLabel && (
        <PillLabel text={props.aiImageLabel} from={scene.from} to={scene.to} x={70} y={props.aiImageLabelY} font={FONTS.inter} size={30} background="rgba(14,14,14,0.78)" color="#fff" anchor="left" />
      )}
    </>
  );
}

export function Short(props: ShortProps): React.ReactElement {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  const { style, subtitles: subs } = props;
  const s = shake(frame, props.hits, props.shake.strength, props.shake.frames);
  const drift = props.drift.px * Math.sin((frame / props.drift.frames) * Math.PI * 2);
  return (
    <AbsoluteFill style={{ background: style.bg }}>
      <AbsoluteFill style={{ transform: `translate(${s.dx}px, ${s.dy + drift}px) rotate(${s.rot}deg)` }}>
        {props.scenes.map((sc, i) => <SceneView key={i} scene={sc} props={props} />)}
      </AbsoluteFill>
      {subs.enabled && (
        <Subtitles words={props.words} font={FONTS[style.subtitleFont]} size={subs.size} x={subs.x} y={subs.y} maxWidth={subs.maxWidth} color={style.text} activeColor={style.accent2} keywords={subs.keywords} hide={subs.hide} />
      )}
      {props.badge && <PillLabel text={props.badge.text} from={0} to={props.frames} x={props.badge.x} y={props.badge.y} font={FONTS.inter} size={BADGE_SIZE} background="rgba(255,255,255,0.12)" color="#fff" anchor="left" />}
      {!textOnly && props.hits.map((h) => <Flash key={h} at={h} dur={5} max={0.45} />)}
      {!textOnly && props.grain > 0 && <Grain opacity={props.grain} />}
    </AbsoluteFill>
  );
}

/** The same video with ONLY the text: input for the zone control (kit/zones.py). */
export function ShortControl(props: ShortProps): React.ReactElement {
  return (
    <TextOnly.Provider value>
      <Short {...props} />
    </TextOnly.Provider>
  );
}
