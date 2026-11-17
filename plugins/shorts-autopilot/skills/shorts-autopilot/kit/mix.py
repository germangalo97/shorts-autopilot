"""Mixes the sound of a video from its plan (build/sound-plan.json, made by kit/sound_plan.py).

Voice always in front; music as a bed (level relative to the voice, ducks while the voice speaks, volume changes,
tape-stop and resume); effects tied to the same seconds as the animation. At the end: -14 LUFS integrated (what
YouTube normalizes to) and true peak <= -1.5 dBTP, measured with ffmpeg (ebur128) in a loop.
Prints a report with voice, music and effects levels measured separately (to check without listening).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d

from common import KitError, write_json

SR = 48000
TARGET_LUFS = -14.0
TOLERANCE_LU = 0.3
MAX_PEAK_DBTP = -1.5
LIMIT_LINEAR = 0.80
VOICE_ACTIVE_DB = -45.0
ATTACK_S, RELEASE_S = 0.04, 0.35
LEVEL_TRIES = 4


def read_audio(path: Path, start: float = 0.0, dur: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.4f}", "-i", str(path)]
    if dur is not None:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).reshape(-1, 2).astype(np.float64)


def rms_db(x: np.ndarray) -> float:
    return float(10 * np.log10(np.mean(x ** 2) + 1e-12))


def voice_envelope(voice: np.ndarray) -> np.ndarray:
    """0-1: how much the voice is speaking (fast attack, slow release, like a side-chain compressor)."""
    m = voice.mean(1)
    energy = uniform_filter1d(m * m, size=int(0.03 * SR))
    active = (10 * np.log10(energy + 1e-12) > VOICE_ACTIVE_DB).astype(np.float64)
    env = np.zeros_like(active)
    a, r = 1 - np.exp(-1 / (ATTACK_S * SR)), 1 - np.exp(-1 / (RELEASE_S * SR))
    step = SR // 1000
    level = 0.0
    for i in range(0, len(active), step):
        target = active[i: i + step].max()
        coef = a if target > level else r
        level += (target - level) * (1 - (1 - coef) ** step)
        env[i: i + step] = level
    return env


def tape_stop(x: np.ndarray, t: float, dur: float) -> np.ndarray:
    i0, n = int(t * SR), int(dur * SR)
    out = x.copy()
    if i0 >= len(x):
        return out
    k = np.arange(n) / n
    pos = np.clip(i0 + np.cumsum((1 - k) ** 1.6), 0, len(x) - 1)
    m = max(0, min(n, len(x) - i0))
    for c in range(2):
        out[i0: i0 + n, c] = np.interp(pos, np.arange(len(x)), x[:, c])[:m]
    out[i0: i0 + n] *= (1 - k[:m] ** 3)[:, None]
    out[i0 + n:] = 0
    return out


def automation(n: int, points: list[dict], base_db: float) -> np.ndarray:
    if not points:
        return np.full(n, 10 ** (base_db / 20))
    ts = [0.0] + [p["t"] for p in points]
    dbs = [points[0]["db"] if points[0]["t"] <= 0 else 0.0] + [p["db"] for p in points]
    return 10 ** ((base_db + np.interp(np.arange(n) / SR, ts, dbs)) / 20)


def music_track(plan: dict, public: Path, dur: float, voice: np.ndarray, env: np.ndarray) -> np.ndarray:
    m = plan["music"]
    path = public / "music" / m["file"]
    if not path.is_file():
        raise KitError(f"missing music file {path}")
    track = read_audio(path, m["from"], dur + 1.0)
    track = np.pad(track, ((0, max(0, int(dur * SR) - len(track))), (0, 0)))[: int(dur * SR)]
    if m.get("stop"):
        stopped = tape_stop(track, m["stop"]["t"], m["stop"]["dur"])
        if m.get("resume") is not None:
            i = int(m["resume"] * SR)
            stopped[i:] = track[i:]
            ramp = min(len(stopped) - i, int(0.012 * SR))
            stopped[i: i + ramp] *= np.linspace(0, 1, ramp)[:, None]
        track = stopped
    speaking = env > 0.5
    voice_db = rms_db(voice[speaking]) if np.any(speaking) else rms_db(voice)
    sounding = np.abs(track).max(1) > 1e-4
    track_db = rms_db(track[sounding]) if np.any(sounding) else -120
    gain = automation(len(track), m.get("automation", []), voice_db + m["db"] - track_db)
    duck = 10 ** (m.get("duckDb", -4.0) * env / 20)
    track = track * (gain * duck)[:, None]
    if m.get("fadeOut"):
        n = int(m["fadeOut"] * SR)
        track[-n:] *= np.linspace(1, 0, n)[:, None] ** 1.5
    return track


@lru_cache(maxsize=64)
def _effect(folder: str, name: str) -> np.ndarray:
    path = Path(folder) / f"{name}.wav"
    if not path.exists():
        raise KitError(f"missing effect {path} (run «python kit/sa.py sfx» in the studio)")
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    if sr != SR:
        raise KitError(f"{path}: {sr} Hz (expected {SR})")
    return x if x.shape[1] == 2 else np.repeat(x, 2, 1)


def effects_bus(plan: dict, public: Path, n: int) -> np.ndarray:
    bus = np.zeros((n, 2))
    for e in plan["effects"]:
        x = _effect(str(public / "sfx"), e["effect"]) * 10 ** (e.get("db", -12.0) / 20)
        start = int(round(e["t"] * SR))
        if e.get("align") == "peak":
            start -= int(np.argmax(uniform_filter1d(np.abs(x).max(1), size=int(0.01 * SR))))
        a, b = max(0, start), min(n, start + len(x))
        if b > a:
            bus[a:b] += x[a - start: b - start]
    return bus


def measure(path: Path) -> tuple[float, float]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    summary = out[out.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not i or not p:
        raise KitError(f"could not measure {path}")
    return float(i.group(1)), float(p.group(1)) if p.group(1) != "-inf" else -120.0


def lufs_of(x: np.ndarray) -> float | None:
    if np.max(np.abs(x)) < 1e-6:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "layer.wav"
        sf.write(str(path), x.astype(np.float32), SR, subtype="FLOAT")
        value = measure(path)[0]
    return None if value < -69 else value


def to_level(x: np.ndarray, target: float) -> np.ndarray:
    now = lufs_of(x)
    return x if now is None else x * 10 ** ((target - now) / 20)


def normalize(mixdown: np.ndarray, out: Path) -> tuple[float, float, float]:
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        sf.write(str(raw), mixdown.astype(np.float32), SR, subtype="FLOAT")
        lufs, peak = measure(raw)
        gain = TARGET_LUFS - lufs
        for _ in range(LEVEL_TRIES):
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-af",
                            f"volume={gain:.3f}dB,alimiter=limit={LIMIT_LINEAR}:attack=4:release=60:level=false",
                            "-ar", str(SR), "-c:a", "pcm_f32le", str(out)], check=True)
            lufs, peak = measure(out)
            if abs(lufs - TARGET_LUFS) <= TOLERANCE_LU and peak <= MAX_PEAK_DBTP:
                break
            gain += TARGET_LUFS - lufs
    return lufs, peak, gain


def mix(plan: dict, voice_path: Path, public: Path, out: Path) -> dict:
    voice = read_audio(voice_path)
    dur = len(voice) / SR
    env = voice_envelope(voice)
    music = music_track(plan, public, dur, voice, env)
    sfx = effects_bus(plan, public, len(voice))
    voice_lufs = lufs_of(voice)
    if voice_lufs is None:
        raise KitError("the voice is silent")
    music = to_level(music, voice_lufs + plan["music"]["db"])
    sfx = to_level(sfx, voice_lufs + plan.get("effectsLu", -6.0))
    lufs, peak, gain = normalize(voice + music + sfx, out)
    speaking = env > 0.5
    report = {"lufs": lufs, "peakDbtp": peak, "gainDb": round(gain, 2), "effects": len(plan["effects"]),
              "musicUnderVoiceDb": round(rms_db(music[speaking]) - rms_db(voice[speaking]), 1)}
    write_json(out.with_suffix(".json"), report)
    if abs(lufs - TARGET_LUFS) > TOLERANCE_LU or peak > MAX_PEAK_DBTP:
        raise KitError(f"level not reached: {lufs} LUFS, peak {peak} dBTP")
    return report
