"""Gives every word OF THE SCRIPT its time in the voice take, using Whisper (faster-whisper, runs locally, CPU or GPU).

- Whisper listens without seeing the script (so it cannot «invent» script words that were not said); what it hears is
  aligned to the script word by word (difflib). Every script word not heard and every extra heard word is reported.
- Words keep the script spelling, with the timing of what was heard.
- Whisper places word STARTS well and cuts ends early: each end is stretched to the next word, and the last word of a
  sentence to where the voice energy stops (with a maximum).
"""
from __future__ import annotations

import difflib
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

from common import KitError, clean_word, write_json

ENERGY_STEP_S = 0.01
VOICE_DB = -42.0
SENTENCE_END_MAX_S = 0.6
MIN_GAP_S = 0.02
MAX_MISSING = 3


def script_words(path: Path) -> list[dict]:
    if not path.is_file():
        raise KitError(f"missing script: {path}")
    script = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for block in script.get("blocks", []):
        raw = block["text"].split()
        sentence = 0
        for i, w in enumerate(raw):
            ends = bool(re.search(r"[.?!…:]$", w)) or i == len(raw) - 1
            out.append({"w": w, "clean": clean_word(w), "block": block["id"], "local_sentence": sentence, "endsSentence": ends})
            if ends:
                sentence += 1
    if not out:
        raise KitError(f"{path}: the script has no words")
    return out


GPU_ERRORS = ("cublas", "cudnn", "cuda", "libcudart")


def _transcribe_on(voice: Path, model_name: str, language: str, device: str) -> list[dict]:
    from faster_whisper import WhisperModel  # noqa: PLC0415

    model = WhisperModel(model_name, device=device, compute_type="int8")
    segments, _ = model.transcribe(str(voice), language=language, word_timestamps=True, temperature=0.0,
                                   condition_on_previous_text=False)
    heard = []
    for seg in segments:  # the work (and any GPU error) happens while iterating
        for w in seg.words or []:
            c = clean_word(w.word)
            if c:
                heard.append({"w": w.word.strip(), "clean": c, "a": float(w.start), "end": float(w.end)})
    return heard


def transcribe(voice: Path, model_name: str, language: str, device: str) -> list[dict]:
    """«auto» tries the GPU and falls back to the CPU when the NVIDIA libraries are missing (measured on Windows:
    «cublas64_12.dll is not found»). «cuda» never falls back: it fails with the reason."""
    if importlib.util.find_spec("faster_whisper") is None:
        raise KitError("faster-whisper is not installed: pip install -r kit/requirements.txt")
    try:
        return _transcribe_on(voice, model_name, language, device)
    except RuntimeError as e:
        gpu_problem = any(k in str(e).lower() for k in GPU_ERRORS)
        if device == "auto" and gpu_problem:
            print(f"GPU not usable ({str(e)[:120]}): using the CPU (slower, same result)", flush=True)
            return _transcribe_on(voice, model_name, language, "cpu")
        raise KitError(f"Whisper failed on device «{device}»: {e}") from e


def voice_activity(voice: Path) -> np.ndarray:
    x, sr = sf.read(str(voice), dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    step = int(sr * ENERGY_STEP_S)
    n = len(x) // step
    rms = np.sqrt((x[: n * step].reshape(n, step) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms) > VOICE_DB


def align(script: list[dict], heard: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    a_s = [p["clean"] for p in script]
    a_h = [p["clean"] for p in heard]
    sm = difflib.SequenceMatcher(a=a_s, b=a_h, autojunk=False)
    times: list[tuple[float, float] | None] = [None] * len(script)
    missing, extra = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k]["a"], heard[j1 + k]["end"])
                if a_s[i1 + k] != a_h[j1 + k]:
                    extra.append(f"«{script[i1 + k]['w']}» heard as «{heard[j1 + k]['w']}»")
            continue
        if op in ("replace", "delete"):
            if j2 > j1:
                a0, a1 = heard[j1]["a"], heard[j2 - 1]["end"]
                n = i2 - i1
                for k in range(n):
                    times[i1 + k] = (a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n)
            missing += [script[k]["w"] for k in range(i1, i2)]
        if op in ("replace", "insert"):
            extra += [heard[k]["w"] for k in range(j1, j2)]
    for i, t in enumerate(times):
        if t is None:
            prev = next((times[k] for k in range(i - 1, -1, -1) if times[k]), (0.0, 0.0))
            nxt = next((times[k] for k in range(i + 1, len(times)) if times[k]), (prev[1] + 0.3, prev[1] + 0.3))
            times[i] = (prev[1], max(prev[1] + 0.05, nxt[0]))
    return [{**p, "a": round(t[0], 3), "end": round(t[1], 3)} for p, t in zip(script, times)], missing, extra


def stretch_ends(words: list[dict], active: np.ndarray) -> list[dict]:
    out = []
    for i, p in enumerate(words):
        nxt = words[i + 1]["a"] if i + 1 < len(words) else None
        end = p["end"]
        if p["endsSentence"]:
            k = int(end / ENERGY_STEP_S)
            limit = int((end + SENTENCE_END_MAX_S) / ENERGY_STEP_S)
            if nxt is not None:
                limit = min(limit, int((nxt - MIN_GAP_S) / ENERGY_STEP_S))
            while k < min(limit, len(active)) and active[k]:
                k += 1
            end = max(end, k * ENERGY_STEP_S)
        elif nxt is not None:
            end = max(end, nxt - MIN_GAP_S)
        out.append({**p, "end": round(end, 3)})
    return out


def run_align(voice: Path, script_path: Path, out: Path, model: str, language: str, device: str) -> dict:
    if not voice.is_file():
        raise KitError(f"missing voice take: {voice}")
    script = script_words(script_path)
    heard = transcribe(voice, model, language, device)
    words, missing, extra = align(script, heard)
    words = stretch_ends(words, voice_activity(voice))
    sentence, previous = 0, None
    for p in words:
        key = (p["block"], p.pop("local_sentence"))
        if previous is not None and key != previous:
            sentence += 1
        p["sentence"] = sentence
        previous = key
    duration = float(sf.info(str(voice)).duration)
    data = {"take": voice.stem, "duration": round(duration, 3), "voiceEnd": words[-1]["end"], "words": words,
            "control": {"scriptWords": len(script), "heardWords": len(heard), "missing": missing, "extra": extra, "model": model}}
    write_json(out, data)
    return data
