/**
 * Visual pieces a scene can use (see references/scenes.md): checklist, typewriter screen, one-minute timer, search box,
 * calendar page, bouncing arrow, TV static, blackout sweep and source label. Each one gets its entry/exit frames and a
 * position already computed by kit/build.py. In control mode (TextOnly) only their text is drawn.
 */
import React from "react";
import { AbsoluteFill, random, useCurrentFrame } from "remotion";
import { appear, clamp, mix, prog } from "../lib/anim";
import { TextOnly } from "../lib/control";
import { FONTS } from "../lib/fonts";
import { PillLabel } from "../lib/ui";
import type { Element, Style } from "../props";

/** Check (ok) or cross drawn with bars, so it never depends on the font having the glyph. */
function Mark({ ok, size, style }: { ok: boolean; size: number; style: Style }): React.ReactElement {
  const bar = size * 0.14;
  return (
    <div style={{ width: size * 1.25, height: size * 1.25, borderRadius: size, background: ok ? style.ok : style.danger, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, position: "relative" }}>
      {ok ? (
        <div style={{ width: size * 0.55, height: size * 0.28, borderLeft: `${bar}px solid ${style.bg}`, borderBottom: `${bar}px solid ${style.bg}`, transform: "rotate(-45deg) translate(2px, -4px)" }} />
      ) : (
        [45, -45].map((g) => <div key={g} style={{ position: "absolute", width: size * 0.7, height: bar, borderRadius: bar, background: style.bg, transform: `rotate(${g}deg)` }} />)
      )}
    </div>
  );
}

function Checklist({ el, style }: { el: Extract<Element, { type: "checklist" }>; style: Style }): React.ReactElement {
  const frame = useCurrentFrame();
  return (
    <>
      {el.items.map((it, i) => {
        const k = appear(frame, it.from, el.to);
        if (k <= 0) return null;
        return (
          <div key={i} style={{ position: "absolute", left: el.x, top: el.y + i * el.gap, display: "flex", alignItems: "center", gap: 30, transform: `translate(${(1 - k) * -120}px, -50%)`, opacity: clamp(k * 1.6, 0, 1) }}>
            <Mark ok={it.ok} size={el.size} style={style} />
            <div style={{ fontFamily: FONTS[style.font], fontSize: el.size * 1.25, lineHeight: 1, color: it.ok ? style.text : style.danger, whiteSpace: "pre", textShadow: "0 10px 40px rgba(0,0,0,0.75)" }}>{it.text}</div>
          </div>
        );
      })}
    </>
  );
}

function Screen({ el }: { el: Extract<Element, { type: "screen" }> }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  const k = appear(frame, el.from, el.to);
  if (k <= 0) return null;
  const n = Math.floor(clamp(((frame - el.from - 6) / 30) * 22, 0, el.text.length));
  return (
    <div
      style={{
        position: "absolute", left: el.x, top: el.y, width: el.width, height: el.height, borderRadius: 40, overflow: "hidden",
        background: textOnly ? "transparent" : "#151515", border: textOnly ? "none" : "14px solid #2b2b2b",
        boxShadow: textOnly ? "none" : "0 40px 100px rgba(0,0,0,0.7)", transform: `scale(${0.85 + 0.15 * k})`, opacity: clamp(k * 1.5, 0, 1),
      }}
    >
      {!textOnly && <div style={{ position: "absolute", inset: 0, background: "radial-gradient(circle at 50% 45%, #0f2e1d 0%, #040a06 78%)" }} />}
      {!textOnly && <div style={{ position: "absolute", inset: 0, backgroundImage: "repeating-linear-gradient(0deg, rgba(0,0,0,0.35) 0px, rgba(0,0,0,0.35) 2px, transparent 2px, transparent 5px)" }} />}
      <div style={{ position: "absolute", left: 44, right: 44, top: 46, fontFamily: FONTS.mono, fontSize: 54, lineHeight: 1.28, color: "#7CFFB2", whiteSpace: "pre-wrap", textShadow: "0 0 18px rgba(124,255,178,0.55)" }}>
        {el.text.slice(0, n)}
        <span style={{ opacity: frame % 16 < 8 ? 1 : 0 }}>{"\u258C"}</span>
      </div>
    </div>
  );
}

function Timer({ el, style }: { el: Extract<Element, { type: "timer" }>; style: Style }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  const k = appear(frame, el.from, el.to);
  if (k <= 0) return null;
  const r = el.radius;
  const full = clamp((frame - el.from) / Math.max(1, el.fillBy - el.from), 0, 1);
  const turn = 2 * Math.PI * r;
  const cut = el.text.lastIndexOf(" ");
  const [top, bottom] = cut > 0 ? [el.text.slice(0, cut), el.text.slice(cut + 1)] : [el.text, ""];
  const box = r * 2 + 60;
  return (
    <div style={{ position: "absolute", left: el.x - r - 30, top: el.y - r - 30, width: box, height: box, transform: `scale(${0.7 + 0.3 * k})`, opacity: clamp(k * 1.5, 0, 1) }}>
      {!textOnly && (
        <svg width={box} height={box} style={{ position: "absolute", left: 0, top: 0, transform: "rotate(-90deg)" }}>
          <circle cx={r + 30} cy={r + 30} r={r} fill="none" stroke="#2A2E36" strokeWidth={34} />
          <circle cx={r + 30} cy={r + 30} r={r} fill="none" stroke={style.accent} strokeWidth={34} strokeLinecap="round" strokeDasharray={`${turn * full} ${turn}`} />
        </svg>
      )}
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: FONTS[style.font], color: style.text, lineHeight: 0.95 }}>
        <div style={{ fontSize: r * 0.75 }}>{top}</div>
        <div style={{ fontSize: r * 0.36, color: style.accent }}>{bottom}</div>
      </div>
    </div>
  );
}

function Search({ el, style }: { el: Extract<Element, { type: "search" }>; style: Style }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  const k = appear(frame, el.from, el.to);
  if (k <= 0) return null;
  const letters = Math.floor(clamp(((frame - el.typeFrom) / 30) * 26, 0, el.query.length));
  const kr = frame >= el.resultFrom ? prog(frame, el.resultFrom, 6) : 0;
  // the result is fitted to the box width (a fixed 120 px clipped «0 RESULTADOS» in the test render)
  const resultSize = Math.min(120, (el.width - 100) / Math.max(1, el.result.length * 0.56));
  return (
    <div
      style={{
        position: "absolute", left: el.x, top: el.y, width: el.width, height: el.height, borderRadius: 26, overflow: "hidden",
        background: textOnly ? "transparent" : style.panel, border: textOnly ? "none" : "2px solid #2A2E36",
        transform: `translateY(${(1 - k) * 60}px)`, opacity: clamp(k * 1.6, 0, 1),
      }}
    >
      <div style={{ height: 64, display: "flex", alignItems: "center", padding: "0 26px", fontFamily: FONTS.mono, fontSize: 28, color: style.muted }}>{el.title}</div>
      <div style={{ margin: "6px 26px 0", height: 92, borderRadius: 46, background: textOnly ? "transparent" : "#fff", display: "flex", alignItems: "center", gap: 18, padding: "0 30px" }}>
        {!textOnly && <div style={{ width: 34, height: 34, borderRadius: 17, border: `6px solid ${style.bg}`, flexShrink: 0 }} />}
        <div style={{ fontFamily: FONTS.inter, fontWeight: 800, fontSize: 44, color: textOnly ? "#fff" : style.bg, whiteSpace: "pre" }}>
          {el.query.slice(0, letters)}
          <span style={{ opacity: frame < el.resultFrom && frame % 16 < 8 ? 1 : 0 }}>|</span>
        </div>
      </div>
      {!textOnly && Array.from({ length: 6 }, (_, i) => <div key={i} style={{ margin: "26px 26px 0", height: 18, width: `${68 + 26 * random(`line-${i}`)}%`, borderRadius: 9, background: "#2A2E36" }} />)}
      {kr > 0 && (
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, textAlign: "center", fontFamily: FONTS[style.font], fontSize: resultSize, lineHeight: 1, color: style.danger, transform: `scale(${mix(1.8, 1, kr)})`, opacity: clamp(kr * 2, 0, 1) }}>
          {el.result}
        </div>
      )}
    </div>
  );
}

function Calendar({ el, style }: { el: Extract<Element, { type: "calendar" }>; style: Style }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const k = appear(frame, el.from, el.to);
  if (k <= 0) return null;
  const w = 420;
  const h = 470;
  return (
    <div style={{ position: "absolute", left: el.x - w / 2, top: el.y - h / 2, width: w, height: h, borderRadius: 34, overflow: "hidden", background: "#F7F1E3", boxShadow: "0 40px 90px rgba(0,0,0,0.6)", transform: `scale(${0.6 + 0.4 * k}) rotate(${(1 - k) * -12}deg)`, opacity: clamp(k * 1.5, 0, 1) }}>
      <div style={{ height: 130, background: style.danger, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONTS[style.font], fontSize: 92, color: "#fff", letterSpacing: "0.08em" }}>{el.month}</div>
      <div style={{ height: h - 130, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONTS[style.font], fontSize: 280, color: "#0E0E0E", lineHeight: 1 }}>{el.day}</div>
    </div>
  );
}

function Arrow({ el, style }: { el: Extract<Element, { type: "arrow" }>; style: Style }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  const k = appear(frame, el.from, el.to);
  if (k <= 0 || textOnly) return null;
  const bounce = 26 * Math.abs(Math.sin(((frame - el.from) / 30) * Math.PI * 2));
  const size = 120;
  const bar = size * 0.2;
  return (
    <div style={{ position: "absolute", left: el.x, top: el.y + bounce, opacity: k }}>
      {[45, -45].map((g) => (
        <div key={g} style={{ position: "absolute", left: g > 0 ? -size * 0.62 : -size * 0.08, top: 0, width: size * 0.7, height: bar, borderRadius: bar, background: style.accent, transform: `rotate(${g}deg)`, boxShadow: `0 0 30px ${style.accent}88` }} />
      ))}
    </div>
  );
}

function Static({ el }: { el: Extract<Element, { type: "static" }> }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  if (textOnly || frame < el.from || frame >= el.to) return null;
  return (
    <AbsoluteFill style={{ opacity: el.opacity }}>
      {Array.from({ length: 70 }, (_, i) => {
        const gray = Math.round(40 + 160 * random(`gray-${frame}-${i}`));
        return <div key={i} style={{ position: "absolute", left: 0, top: random(`static-${frame}-${i}`) * 1920, width: 1080, height: 2 + 10 * random(`h-${frame}-${i}`), background: `rgb(${gray},${gray},${gray})`, opacity: 0.35 }} />;
      })}
    </AbsoluteFill>
  );
}

function Blackout({ el }: { el: Extract<Element, { type: "blackout" }> }): React.ReactElement | null {
  const frame = useCurrentFrame();
  const textOnly = React.useContext(TextOnly);
  if (textOnly || frame < el.from || frame >= el.to) return null;
  const k = prog(frame, el.from, el.duration);
  const edge = mix(-25, 125, k);
  const flicker = k < 1 ? 0.2 * random(`blackout-${frame}`) : 0;
  return <AbsoluteFill style={{ background: `linear-gradient(90deg, rgba(0,0,0,0.92) ${edge - 25}%, rgba(0,0,0,${0.3 + flicker}) ${edge}%, rgba(0,0,0,0) ${edge + 18}%)` }} />;
}

export function Piece({ el, style }: { el: Element; style: Style }): React.ReactElement | null {
  switch (el.type) {
    case "checklist":
      return <Checklist el={el} style={style} />;
    case "screen":
      return <Screen el={el} />;
    case "timer":
      return <Timer el={el} style={style} />;
    case "search":
      return <Search el={el} style={style} />;
    case "calendar":
      return <Calendar el={el} style={style} />;
    case "arrow":
      return <Arrow el={el} style={style} />;
    case "static":
      return <Static el={el} />;
    case "blackout":
      return <Blackout el={el} />;
    case "source":
      return <PillLabel text={el.text} from={el.from} to={el.to} x={70} y={el.y} font={FONTS.inter} size={30} background="rgba(14,14,14,0.78)" color="#fff" anchor="left" />;
  }
}
