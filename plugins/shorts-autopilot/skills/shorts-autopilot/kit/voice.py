"""The voice: the WHOLE script in ONE take with Gemini text-to-speech (free tier of Google AI Studio), then long
silences shortened (AI voices leave almost a second between sentences and it feels slow).

Each script block goes as one piece of text with its own voice direction, all in the SAME request: the voice flows,
no stitched clips. The key is read from GEMINI_API_KEY (environment or <studio>/.env) and is never printed.
Free-tier quota measured on 27/10/2026: 10 requests per day for gemini-3.8-flash-tts; this makes ONE request per run.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

from common import KitError, Video, load_config, read_json, secret

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
RATE = 24_000
TIMEOUT_S = 240
MIN_S, MAX_S = 15, 240
SILENCE_DB = -45
STEP_S = 0.01
MIN_PAUSE_S = 0.3
FADE_S = 0.004


def _pieces(script: dict) -> list[dict]:
    if not script.get("voiceStyle"):
        raise KitError("script.json needs «voiceStyle» (how the voice sounds overall)")
    blocks = script.get("blocks") or []
    if not blocks:
        raise KitError("script.json has no blocks")
    out = []
    for b in blocks:
        if not b.get("text") or not b.get("style"):
            raise KitError(f"block «{b.get('id')}» needs «text» and «style»")
        out.append({"type": "text", "text": b["text"], "annotations": [{"type": "speech_metadata", "style": f"{script['voiceStyle']} {b['style']}"}]})
    return out


def _audio(body: str) -> bytes:
    data = json.loads(body)
    outs = [c for s in data.get("steps", []) if s.get("type") == "model_output" for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
    if not outs:
        raise KitError(f"the answer has no audio (steps: {[s.get('type') for s in data.get('steps', [])]})")
    return base64.b64decode(outs[-1]["data"])


def generate(video: Video) -> Path:
    cfg = load_config(video.studio)["voice"]
    dest = video.voice()
    if dest.exists():
        raise KitError(f"{dest} already exists: set a new «take» in video.json (takes are never overwritten)")
    script = read_json(video.folder / "script.json")
    body = {
        "model": cfg["model"],
        "input": [{"type": "user_input", "content": _pieces(script)}],
        "response_format": {"type": "audio", "mime_type": "audio/wav", "sample_rate": RATE},
        "generation_config": {"speech_config": [{"voice": cfg["voice"]}]},
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"x-goog-api-key": secret(video.studio, "GEMINI_API_KEY"), "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            wav = _audio(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise KitError(f"Google answered HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from e
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(wav)
    seconds = sf.info(str(dest)).duration
    if not MIN_S <= seconds <= MAX_S:
        raise KitError(f"the take lasts {seconds:.1f} s: outside {MIN_S}-{MAX_S} s, check the script")
    words = sum(len(b["text"].split()) for b in script["blocks"])
    print(f"voice: {dest} · {seconds:.1f} s · {words / seconds:.2f} words/s · waited {time.time() - t0:.0f} s")
    return dest


def tighten(src: Path, dest: Path, factor: float) -> None:
    """A silence of L seconds becomes MIN_PAUSE + factor × (L − MIN_PAUSE); shorter ones are untouched."""
    if not 0 <= factor <= 1:
        raise KitError("pause factor must be between 0 and 1")
    x, sr = sf.read(str(src), dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    step = int(round(STEP_S * sr))
    n = len(x) // step
    quiet = np.sqrt((x[: n * step].reshape(n, step) ** 2).mean(axis=1)) < 10 ** (SILENCE_DB / 20)
    keep, cursor, k = [], 0, 0
    before = after = 0.0
    while k < n:
        if not quiet[k]:
            k += 1
            continue
        j = k
        while j < n and quiet[j]:
            j += 1
        length = (j - k) * STEP_S
        if length > MIN_PAUSE_S:
            target = MIN_PAUSE_S + factor * (length - MIN_PAUSE_S)
            cut = int((length - target) / STEP_S)
            before += length
            after += length - cut * STEP_S
            if cut > 0:
                start = ((k + j) // 2 - cut // 2) * step
                keep.append((cursor, start))
                cursor = start + cut * step
        k = j
    keep.append((cursor, len(x)))
    fade = int(FADE_S * sr)
    parts = []
    for idx, (a, b) in enumerate(keep):
        seg = x[a:b].copy()
        if idx > 0 and len(seg) > fade:
            seg[:fade] *= np.linspace(0, 1, fade)
        if idx < len(keep) - 1 and len(seg) > fade:
            seg[-fade:] *= np.linspace(1, 0, fade)
        parts.append(seg)
    y = np.concatenate(parts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), y, sr, subtype="PCM_16")
    print(f"pauses: {before:.1f} s of long silences → {after:.1f} s · {len(x) / sr:.1f} s → {len(y) / sr:.1f} s")
