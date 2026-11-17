"""Sound design from the scenes: every visual event gets its matching effect, so sound and image stay tied to the same
spoken word. Effects are the kit synthesized by kit/sfx.py (no third-party licenses). Extra effects and music cuts can
be added in scenes.json («sound.extra», «music.cuts», «music.stop», «music.resume»), already resolved to seconds."""
from __future__ import annotations

from common import FPS

MIN_GAP_S = 0.06
END_POP_S = 0.72

ELEMENT_SOUNDS = {
    "screen": [("from", "typing", -18)],
    "timer": [("from", "tick", -14), ("from+15", "tock", -14)],
    "search": [("typeFrom", "typing", -20), ("resultFrom", "beep_low", -12)],
    "calendar": [("from", "text_hit", -11)],
    "arrow": [("from", "pop_high", -12)],
    "static": [("from", "crt_hum", -15)],
    "blackout": [("from", "boom", -9)],
    "source": [("from", "swish", -16)],
}


def _fx(t: float, effect: str, db: float, align: str | None = None) -> dict:
    e = {"t": round(max(0.0, t), 3), "effect": effect, "db": db}
    if align:
        e["align"] = align
    return e


def _element_effects(el: dict) -> list[dict]:
    out = []
    if el["type"] == "checklist":
        out += [_fx(i["from"] / FPS, "click", -13) for i in el["items"]]
    for key, effect, db in ELEMENT_SOUNDS.get(el["type"], []):
        base, _, plus = key.partition("+")
        out.append(_fx((el[base] + (int(plus) if plus else 0)) / FPS, effect, db))
    return out


def _dedupe(effects: list[dict]) -> list[dict]:
    kept: list[dict] = []
    last: dict[str, float] = {}
    for e in sorted(effects, key=lambda x: x["t"]):
        if e["effect"] in last and e["t"] - last[e["effect"]] < MIN_GAP_S:
            continue
        last[e["effect"]] = e["t"]
        kept.append(e)
    return kept


def make_plan(props: dict, spec: dict, music: dict) -> dict:
    duration = props["frames"] / FPS
    fx = [_fx(0, "impact", -9), _fx(0, "text_hit", -12)]
    for k, scene in enumerate(props["scenes"]):
        if k > 0:
            fx.append(_fx(scene["from"] / FPS, "whoosh_short", -16, "peak"))
        for beat in scene["beats"]:
            if beat["from"] > 0:
                fx.append(_fx(beat["from"] / FPS, "text_hit", -11))
            fx += [_fx(line["from"] / FPS, "pop", -14) for line in beat["lines"] if line["from"] > beat["from"]]
        for el in scene["elements"]:
            fx += _element_effects(el)
    fx += [_fx(h / FPS, "impact", -9) for h in props["hits"]]
    fx.append(_fx(duration - END_POP_S, "pop_high", -16))
    for e in (spec.get("sound") or {}).get("extra", []):
        fx.append(_fx(float(e["t"]), e["effect"], float(e.get("db", -14)), e.get("align")))
    fx = [e for e in fx if e["t"] <= duration]
    m = spec.get("music") or {}
    automation = []
    for a, b in m.get("cuts", []):
        automation += [{"t": round(a - 0.05, 3), "db": 0}, {"t": a, "db": -40}, {"t": round(b - 0.1, 3), "db": -40}, {"t": round(b + 0.15, 3), "db": 0}]
    plan_music = {"file": music["file"], "from": float(music.get("from", 0)), "db": float(music.get("db", -13)),
                  "duckDb": float(music.get("duckDb", -4)), "automation": automation, "fadeOut": 0.7}
    if m.get("stop") is not None:
        plan_music["stop"] = {"t": float(m["stop"]), "dur": 0.5}
    if m.get("resume") is not None:
        plan_music["resume"] = float(m["resume"])
    return {"music": plan_music, "effects": _dedupe(fx), "effectsLu": -6.0}
