"""Turns scenes.json (what Claude writes: scenes anchored to spoken words) into build/props.json (what the engine draws).

Every word reference is checked against the real voice timings, every on-screen fact comes from texts.json (with its
source), every image must exist, and every text line gets a position and size that fit the screen safe zone. If any
of that fails, it stops with a message that says exactly what to fix: nothing is drawn by guesswork.
"""
from __future__ import annotations

import math
import re

from common import FPS, KitError, clean_word, to_frame

REF = re.compile(r"^(\d+)(?::([^+\-]+))?([+-]\d+(?:\.\d+)?)?$")
COLOR_TOKENS = ("accent", "accent2", "danger", "ok", "text", "muted", "bg", "panel")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Layout of the big lines (px on the 1080×1920 screen). Safe zone measured against third-party guides, not official.
TOP_Y = 400
GAP = 24
HALF_LINE = 0.46
WIDE_WIDTH = 960
NARROW_WIDTH = 760
NARROW_BELOW_Y = 700
LINES_BOTTOM = 1170
DEFAULT_SIZE = 160
MIN_SIZE = 56
SHRINK = 0.92
CHAR_WIDTH = {"anton": 0.5, "inter": 0.62, "grotesk": 0.6, "serif": 0.48, "mono": 0.62}
DEFAULT_LINE_COLORS = ("text", "accent", "text", "accent2")
COVER_LEAD = -12  # frames: the hook is already fully visible on frame 0 (apps may use it as the cover)

ELEMENT_DEFAULTS = {
    "checklist": {"x": 110, "y": 820, "size": 84, "gap": 150},
    "screen": {"x": 90, "y": 760, "width": 740, "height": 420},
    "timer": {"x": 495, "y": 1000, "radius": 190},
    "search": {"x": 90, "y": 700, "width": 740, "height": 520},
    "calendar": {"x": 495, "y": 1000},
    "arrow": {"x": 495, "y": 1120},
    "static": {"opacity": 0.45},
    "blackout": {"duration": 26},
    "source": {"y": 1160},
}


def resolve_ref(ref, words: list[dict], duration: float) -> float:
    """«12:word» (word 12 of the voice, checked), «12», «12:word+0.3», «start» or «end» → seconds."""
    if isinstance(ref, bool):
        raise KitError(f"«{ref}» is not a word reference")
    if isinstance(ref, (int, float)) and not isinstance(ref, bool):
        ref = str(int(ref))
    if ref == "start":
        return 0.0
    if ref == "end":
        return duration
    m = REF.match(str(ref).strip())
    if not m:
        raise KitError(f"«{ref}» is not a word reference (use «12:word», «start» or «end»)")
    i = int(m.group(1))
    if i >= len(words):
        raise KitError(f"«{ref}»: word {i} is out of range (the voice has {len(words)} words)")
    expected = m.group(2)
    if expected and clean_word(expected) != clean_word(words[i]["clean"]):
        raise KitError(f"«{ref}»: word {i} is «{words[i]['w']}», not «{expected}» (did the script or the take change?)")
    offset = float(m.group(3)) if m.group(3) else 0.0
    return max(0.0, min(duration, words[i]["a"] + offset))


def char_width(font: str) -> float:
    return CHAR_WIDTH.get(font, 0.62)


def color(token: str | None, style: dict, default: str) -> str:
    value = token or default
    if HEX.match(value):
        return value
    if value in COLOR_TOKENS:
        return style[value]
    raise KitError(f"color «{value}»: use #RRGGBB or one of {', '.join(COLOR_TOKENS)}")


def text_of(value, texts: dict) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KitError(f"empty or invalid text: {value!r}")
    if value.startswith("$t:"):
        key = value[3:]
        if key not in texts:
            raise KitError(f"«{value}»: there is no «{key}» in texts.json (every on-screen fact needs a source there)")
        return texts[key]
    return value


def _stack(sizes: list[float], top: float = TOP_Y) -> list[float]:
    ys, y_prev, s_prev = [], None, None
    for s in sizes:
        y = top + s * HALF_LINE if y_prev is None else y_prev + s_prev * HALF_LINE + GAP + s * HALF_LINE
        ys.append(y)
        y_prev, s_prev = y, s
    return ys


def layout_lines(lines: list[dict], font: str, top: float = TOP_Y) -> list[dict]:
    """Stacks lines from `top` down; shrinks each to fit its width and all of them to end above LINES_BOTTOM."""
    if not TOP_Y - 170 <= top < LINES_BOTTOM - MIN_SIZE:
        raise KitError(f"beat «top» {top}: use a value between {TOP_Y - 170} and {LINES_BOTTOM - MIN_SIZE}")
    if not lines:
        return []
    cw = char_width(font)
    sizes = [float(line.get("size") or DEFAULT_SIZE) for line in lines]
    for _ in range(40):
        ys = _stack(sizes, top)
        changed = False
        for k, line in enumerate(lines):
            limit = NARROW_WIDTH if ys[k] + sizes[k] * HALF_LINE >= NARROW_BELOW_Y else WIDE_WIDTH
            fit = limit / max(1, len(line["text"]) * cw)
            if sizes[k] > fit:
                sizes[k], changed = fit, True
        ys = _stack(sizes, top)
        if ys[-1] + sizes[-1] * HALF_LINE > LINES_BOTTOM:
            sizes, changed = [s * SHRINK for s in sizes], True
        if not changed:
            break
    if min(sizes) < MIN_SIZE:
        raise KitError(f"too much text in one beat ({' / '.join(line['text'] for line in lines)}): split it in two beats")
    ys = _stack(sizes, top)
    return [{**line, "size": int(s), "y": round(y), "x": 495 if y + s * HALF_LINE >= NARROW_BELOW_Y else 540}
            for line, s, y in zip(lines, sizes, ys)]


def _element(el: dict, scene_from: int, scene_to: int, words, duration, texts) -> dict:
    kind = el.get("type")
    if kind not in ELEMENT_DEFAULTS:
        raise KitError(f"unknown element type «{kind}» (use: {', '.join(ELEMENT_DEFAULTS)})")
    f = lambda ref: to_frame(resolve_ref(ref, words, duration))  # noqa: E731
    out = {**ELEMENT_DEFAULTS[kind], **{k: v for k, v in el.items() if k in ("x", "y", "size", "gap", "width", "height", "radius", "opacity", "duration")}}
    out["type"] = kind
    out["from"] = f(el["at"]) if "at" in el else scene_from
    out["to"] = f(el["until"]) if "until" in el else scene_to
    if kind == "checklist":
        items = el.get("items") or []
        if not items:
            raise KitError("checklist without items")
        out["items"] = [{"text": text_of(i["text"], texts), "ok": bool(i.get("ok", True)),
                         "from": f(i["at"]) if "at" in i else out["from"]} for i in items]
    elif kind in ("screen", "timer", "source"):
        out["text"] = text_of(el.get("text"), texts)
        if kind == "timer":
            out["fillBy"] = f(el["fillBy"]) if "fillBy" in el else out["from"] + 2 * FPS
    elif kind == "search":
        for key in ("title", "query", "result"):
            out[key] = text_of(el.get(key), texts)
        out["typeFrom"] = f(el["typeAt"]) if "typeAt" in el else out["from"] + 10
        out["resultFrom"] = f(el["resultAt"]) if "resultAt" in el else out["from"] + 3 * FPS
    elif kind == "calendar":
        out["month"] = text_of(el.get("month"), texts)
        out["day"] = text_of(el.get("day"), texts)
    return out


def _scene(spec: dict, start: int, end: int, ctx: dict) -> dict:
    words, duration, texts, style, images = ctx["words"], ctx["duration"], ctx["texts"], ctx["style"], ctx["images"]
    f = lambda ref: to_frame(resolve_ref(ref, words, duration))  # noqa: E731
    bg_spec = spec.get("background") or {}
    image = bg_spec.get("image")
    if image and image not in images:
        raise KitError(f"background image «{image}» is not in public/img/ (generate it or copy it there first)")
    background = {
        "image": f"img/{image}" if image else None,
        "color": color(bg_spec.get("color"), style, "bg"),
        "zoom": bg_spec.get("zoom", [1.15, 1.05]),
        "panY": bg_spec.get("panY", [0, 0]),
        "dim": float(bg_spec.get("dim", 0.75)),
        "position": bg_spec.get("position", "50% 50%"),
        "aiGenerated": bool(bg_spec.get("ai", True)) if image else False,
    }
    if not image:
        background.pop("image")
    beats_spec = spec.get("beats") or []
    starts = []
    for k, b in enumerate(beats_spec):
        if "at" not in b and k > 0:
            raise KitError(f"scene at frame {start}: beat {k + 1} needs «at» (only the first beat can omit it)")
        starts.append(f(b["at"]) if "at" in b else start)
    if starts != sorted(starts) or (starts and starts[0] < start):
        raise KitError(f"scene at frame {start}: beats must be in order and start inside the scene")
    beats = []
    for k, b in enumerate(beats_spec):
        b_from, b_to = starts[k], starts[k + 1] if k + 1 < len(starts) else end
        raw = [{"text": text_of(x, texts)} if isinstance(x, str) else {**x, "text": text_of(x.get("text"), texts)} for x in b.get("lines", [])]
        laid = layout_lines(raw, style["font"], float(b.get("top", TOP_Y)))
        lines = []
        for j, (src, line) in enumerate(zip(raw, laid)):
            l_from = f(src["at"]) if "at" in src else b_from
            lines.append({"text": line["text"], "from": COVER_LEAD if l_from == 0 else l_from, "to": b_to, "x": line["x"],
                          "y": line["y"], "size": line["size"],
                          "color": color(src.get("color"), style, DEFAULT_LINE_COLORS[j % len(DEFAULT_LINE_COLORS)])})
        beats.append({"from": b_from, "to": b_to, "lines": lines})
    scene = {"from": start, "to": end, "background": background, "beats": beats,
             "elements": [_element(e, start, end, words, duration, texts) for e in spec.get("elements", [])]}
    if spec.get("kicker"):
        k = spec["kicker"]
        scene["kicker"] = {"text": text_of(k.get("text"), texts), "from": f(k["at"]) if "at" in k else start,
                           "to": f(k["until"]) if "until" in k else end,
                           "background": color(k.get("color"), style, "accent"), "color": color(k.get("textColor"), style, "bg")}
    return scene


def build_props(spec: dict, words: list[dict], texts: dict, config: dict, duration: float, images: set[str]) -> dict:
    style = config["style"]
    frames = math.ceil(duration * FPS - 1e-9)
    scenes_spec = spec.get("scenes") or []
    if not scenes_spec:
        raise KitError("scenes.json has no scenes")
    ctx = {"words": words, "duration": duration, "texts": texts, "style": style, "images": images}
    starts = [to_frame(resolve_ref(s.get("from", "start"), words, duration)) for s in scenes_spec]
    if starts[0] != 0:
        raise KitError("the first scene must start at «start» (frame 0)")
    if any(b <= a for a, b in zip(starts, starts[1:])):
        raise KitError(f"scenes must be in order, each one later than the previous (frames: {starts})")
    scenes = [_scene(s, starts[k], starts[k + 1] if k + 1 < len(starts) else frames, ctx) for k, s in enumerate(scenes_spec)]
    hits = sorted({to_frame(resolve_ref(h, words, duration)) for h in spec.get("hits", [])} - {0})
    subs = spec.get("subtitles") or {}
    labels = config.get("labels") or {}
    look = spec.get("look") or {}
    return {
        "fps": FPS,
        "frames": frames,
        "words": [{"w": w["w"], "clean": w["clean"], "a": w["a"], "end": w["end"], "endsSentence": bool(w.get("endsSentence"))} for w in words],
        "style": {k: style[k] for k in (*COLOR_TOKENS, "font", "subtitleFont")},
        "badge": {"text": labels["badge"], "x": 70, "y": 270} if labels.get("badge") else None,
        "aiImageLabel": labels.get("aiImage", ""),
        "aiImageLabelY": 1225,
        "hits": hits,
        "subtitles": {
            "enabled": subs.get("enabled", True),
            "hide": [[to_frame(resolve_ref(a, words, duration)), to_frame(resolve_ref(b, words, duration))] for a, b in subs.get("hide", [])],
            "keywords": {clean_word(k): color(v, style, "accent") for k, v in (subs.get("keywords") or {}).items()},
            "y": 1360, "x": 495, "size": 80, "maxWidth": 780,
        },
        "scenes": scenes,
        "grain": float(look.get("grain", 0.05)),
        "shake": {"strength": float(look.get("shake", 16)), "frames": 9},
        "drift": {"px": float(look.get("drift", 10)), "frames": 150},
    }
