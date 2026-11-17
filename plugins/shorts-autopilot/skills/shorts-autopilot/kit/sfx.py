"""Sound effects synthesized by code (no third-party licenses: they are yours).

Each effect is a 48 kHz stereo WAV (float) with its peak at -1 dBFS, plus kit.json with duration, peak, loudness and
what it is for. The mixer levels them with the gain each plan asks for. Synthesized because they can be adjusted to
the millisecond, carry no copyright-claim risk on YouTube, and Claude cannot listen: they are checked by measurement.

Usage:  python kit/sfx.py <output-folder>
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, istft, sosfilt, stft

SR = 48000
PEAK_DBFS = -1.0
SEED = 20261106

rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------- building blocks
def span(dur: float) -> np.ndarray:
    return np.arange(int(round(dur * SR))) / SR


def noise(dur: float) -> np.ndarray:
    return rng.standard_normal(int(round(dur * SR)))


def filt(x: np.ndarray, tipo: str, hz, orden: int = 4) -> np.ndarray:
    return sosfilt(butter(orden, hz, btype=tipo, fs=SR, output="sos"), x)


def sweep(f0: float, f1: float, dur: float, curva: float = 1.0) -> np.ndarray:
    """Sine whose frequency goes from f0 to f1 (exponential; `curva` > 1 drops sooner)."""
    t = span(dur)
    u = (t / dur) ** (1 / curva)
    f = f0 * (f1 / f0) ** u
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def env_exp(dur: float, ataque: float, tau: float) -> np.ndarray:
    t = span(dur)
    sube = np.clip(t / max(ataque, 1e-4), 0, 1)
    return sube * np.exp(-np.maximum(t - ataque, 0) / tau)


def moving_band(x: np.ndarray, centro: Callable[[np.ndarray], np.ndarray], ancho_oct: float,
                 nperseg: int = 1024) -> np.ndarray:
    """Band-pass that moves over time (an octave-scale bell applied in the spectrum)."""
    solape = nperseg * 3 // 4
    f, t, z = stft(x, fs=SR, nperseg=nperseg, noverlap=solape, boundary="even", padded=True)
    u = np.clip(t / (len(x) / SR), 0, 1)
    fc = centro(u)
    campana = np.exp(-0.5 * ((np.log2(np.maximum(f, 20.0))[:, None] - np.log2(fc)[None, :]) / ancho_oct) ** 2)
    _, y = istft(z * campana, fs=SR, nperseg=nperseg, noverlap=solape, boundary=True)
    y = y[: len(x)]
    return np.pad(y, (0, len(x) - len(y)))


def pan(mono: np.ndarray, p0: float, p1: float | None = None) -> np.ndarray:
    """Constant-power pan, fixed (p0) or moving from p0 to p1 (-1 left, +1 right)."""
    p = np.full(len(mono), p0) if p1 is None else np.linspace(p0, p1, len(mono))
    ang = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(ang), mono * np.sin(ang)], 1)


def reverb(x: np.ndarray, rt60: float, mezcla: float, brillo_hz: float = 6000) -> np.ndarray:
    """Reverb with a decaying noise response (different left and right: widens the stereo)."""
    if x.ndim == 1:
        x = pan(x, 0.0)
    n_ir = int(rt60 * SR)
    t = np.arange(n_ir) / SR
    caida = np.exp(-6.91 * t / rt60)
    x = np.pad(x, ((0, n_ir), (0, 0)))
    salida = np.empty_like(x)
    for c in range(2):
        ir = filt(rng.standard_normal(n_ir) * caida, "low", brillo_hz, 2)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-12
        mojado = fftconvolve(x[:, c], ir)[: len(x)]
        salida[:, c] = (1 - mezcla) * x[:, c] + mezcla * mojado
    return trim_tail(salida)


def trim_tail(x: np.ndarray, umbral_db: float = -70) -> np.ndarray:
    nivel = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    vivos = np.nonzero(nivel > 10 ** (umbral_db / 20) * nivel.max())[0]
    return x[: (vivos[-1] + 1 if len(vivos) else len(x))]


def saturate(x: np.ndarray, empuje: float) -> np.ndarray:
    return np.tanh(x * empuje) / np.tanh(empuje)


def layer(*capas: tuple[np.ndarray, float]) -> np.ndarray:
    largo = max(len(c) for c, _ in capas)
    out = np.zeros(largo)
    for c, g in capas:
        out[: len(c)] += c * g
    return out


def finish(x: np.ndarray, fundido_s: float = 0.006) -> np.ndarray:
    """Stereo, no DC, short fades at both ends and the peak at PEAK_DBFS."""
    if x.ndim == 1:
        x = pan(x, 0.0)
    x = x - x.mean(0, keepdims=True)
    n = max(1, int(fundido_s * SR))
    rampa = np.linspace(0, 1, n)[:, None]
    x[:n] *= rampa
    x[-n:] *= rampa[::-1]
    return x / (np.abs(x).max() + 1e-12) * 10 ** (PEAK_DBFS / 20)


# ---------------------------------------------------------------- the effects
def whoosh(dur: float, f_ini: float, f_pico: float, f_fin: float, pico_en: float = 0.6,
           p0: float = -0.7, p1: float = 0.7, rt60: float = 0.5) -> np.ndarray:
    """Passing air: filtered noise whose center rises to the peak and falls, panned side to side."""
    def centro(u: np.ndarray) -> np.ndarray:
        sube = f_ini * (f_pico / f_ini) ** np.clip(u / pico_en, 0, 1)
        baja = f_pico * (f_fin / f_pico) ** np.clip((u - pico_en) / (1 - pico_en), 0, 1)
        return np.where(u < pico_en, sube, baja)
    x = moving_band(noise(dur), centro, 0.55)
    t = span(dur) / dur
    env = np.where(t < pico_en, (t / pico_en) ** 2.2, np.exp(-(t - pico_en) / (1 - pico_en) * 4.0))
    return reverb(pan(x * env, p0, p1), rt60, 0.18)


def impact() -> np.ndarray:
    """Hit with body: falling sub, mid thump, click and a short tail."""
    sub = sweep(78, 36, 1.0, 1.6) * env_exp(1.0, 0.003, 0.32)
    cuerpo = filt(noise(0.4), "low", 650) * env_exp(0.4, 0.001, 0.055)
    chasquido = filt(noise(0.05), "high", 2200) * env_exp(0.05, 0.0005, 0.005)
    x = saturate(layer((sub, 1.0), (cuerpo, 0.55), (chasquido, 0.35)), 1.6)
    return reverb(x, 1.6, 0.16, 3500)


def boom() -> np.ndarray:
    """Trailer boom: very long sub with rumble."""
    sub = sweep(56, 29, 2.6, 1.3) * env_exp(2.6, 0.006, 0.85)
    retumbo = filt(noise(2.6), "low", 140) * env_exp(2.6, 0.01, 0.7)
    golpe = filt(noise(0.5), "bandpass", [180, 480]) * env_exp(0.5, 0.002, 0.12)
    x = saturate(layer((sub, 1.0), (retumbo, 0.6), (golpe, 0.45)), 1.3)
    return reverb(x, 3.0, 0.28, 2500)


def riser(dur: float = 2.0) -> np.ndarray:
    """Tension riser: noise opening to the highs + three tones rising an octave. Cuts dry."""
    x = moving_band(noise(dur), lambda u: 380 * (7200 / 380) ** (u ** 1.4), 0.45 + 0.0)
    t = span(dur)
    tonos = sum(sweep(f, f * 2, dur, 0.8) for f in (220, 277.2, 329.6)) / 3
    env = (t / dur) ** 2.4
    mono = (x * 0.8 + tonos * 0.18) * env
    ancho = np.linspace(0.0, 0.9, len(mono))
    estereo = np.stack([mono * (1 - ancho * 0.5), mono * (1 - ancho * 0.5)], 1)
    estereo[:, 0] += filt(noise(dur), "high", 3000) * env * ancho * 0.12
    estereo[:, 1] += filt(noise(dur), "high", 3000) * env * ancho * 0.12
    return estereo


def reverse_cymbal(dur: float = 1.1) -> np.ndarray:
    """Reverse cymbal: grows and cuts right on the hit."""
    plat = filt(noise(dur), "high", 4200) * env_exp(dur, 0.001, 0.38)
    for retardo_ms in (0.71, 1.13, 1.7):  # metallic resonances
        d = int(retardo_ms * SR / 1000)
        plat[d:] += plat[:-d] * 0.35
    return reverb(plat[::-1], 0.6, 0.2)


def pop(f0: float = 1050, f1: float = 260) -> np.ndarray:
    tono = sweep(f0, f1, 0.09, 2.2) * env_exp(0.09, 0.0008, 0.028)
    click_part = filt(noise(0.01), "high", 3000) * env_exp(0.01, 0.0002, 0.0015)
    return layer((tono, 1.0), (click_part, 0.25))


def click() -> np.ndarray:
    tono = np.sin(2 * np.pi * 4100 * span(0.03)) * env_exp(0.03, 0.0003, 0.004)
    ruido_c = filt(noise(0.03), "bandpass", [2500, 7000]) * env_exp(0.03, 0.0002, 0.002)
    return layer((tono, 0.6), (ruido_c, 1.0))


def tick(f: float = 2300) -> np.ndarray:
    madera = filt(noise(0.06), "bandpass", [f * 0.85, f * 1.15], 2) * env_exp(0.06, 0.0003, 0.011)
    arm = np.sin(2 * np.pi * f * 1.93 * span(0.06)) * env_exp(0.06, 0.0003, 0.006)
    return layer((madera, 1.0), (arm, 0.25))


def typing(dur: float = 1.6) -> np.ndarray:
    """Keyboard: key hits with random gaps and tones (the space bar lower)."""
    out = np.zeros(int(dur * SR) + SR // 10)
    t = 0.02
    while t < dur:
        n0 = int(t * SR)
        fc = rng.uniform(1600, 4200)
        golpe = filt(noise(0.05), "bandpass", [fc * 0.7, fc * 1.3], 2) * env_exp(0.05, 0.0003, rng.uniform(0.008, 0.02))
        if rng.random() < 0.12:
            golpe = golpe + filt(noise(0.05), "low", 260) * env_exp(0.05, 0.001, 0.02) * 1.4
        out[n0:n0 + len(golpe)] += golpe * rng.uniform(0.55, 1.0)
        t += rng.uniform(0.065, 0.15)
    return reverb(pan(out, 0.1), 0.25, 0.08)


def notification() -> np.ndarray:
    """Generic two-note message alert (not any app's sound)."""
    def nota(f: float, dur: float) -> np.ndarray:
        t = span(dur)
        return (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t)) * env_exp(dur, 0.004, 0.16)
    a, b = nota(1318.5, 0.45), nota(1975.5, 0.55)
    out = np.zeros(int(0.65 * SR))
    out[: len(a)] += a
    d = int(0.085 * SR)
    out[d:d + len(b)] += b * 0.85
    return reverb(out, 0.7, 0.18)


def glitch(dur: float = 0.42) -> np.ndarray:
    """Digital glitch: bits of square wave, crushed noise and gaps, with hard edges."""
    out = np.zeros(int(dur * SR))
    i = 0
    while i < len(out):
        largo = int(rng.uniform(0.012, 0.05) * SR)
        tipo = rng.choice(["cuadrada", "triturado", "hueco", "cuadrada"])
        if tipo == "cuadrada":
            f = rng.uniform(90, 1800)
            pieza = np.sign(np.sin(2 * np.pi * f * np.arange(largo) / SR)) * 0.6
        elif tipo == "triturado":
            pieza = np.repeat(rng.standard_normal(largo // 24 + 1), 24)[:largo] * 0.7
        else:
            pieza = np.zeros(largo)
        out[i:i + largo] = pieza[: len(out) - i]
        i += largo
    return pan(filt(out, "low", 9000, 2), rng.uniform(-0.3, 0.3))


def shutter() -> np.ndarray:
    a = filt(noise(0.03), "bandpass", [1200, 6000], 2) * env_exp(0.03, 0.0002, 0.006)
    b = filt(noise(0.04), "bandpass", [700, 3500], 2) * env_exp(0.04, 0.0002, 0.01)
    out = np.zeros(int(0.16 * SR))
    out[: len(a)] += a
    d = int(0.07 * SR)
    out[d:d + len(b)] += b * 0.8
    return out


def text_hit() -> np.ndarray:
    """Dry hit for a word that lands on screen."""
    sub = sweep(150, 55, 0.25, 1.8) * env_exp(0.25, 0.001, 0.07)
    clic_t = filt(noise(0.02), "high", 1800) * env_exp(0.02, 0.0002, 0.003)
    return saturate(layer((sub, 1.0), (clic_t, 0.4)), 1.8)


def sparkle() -> np.ndarray:
    """Sparkle: high partials entering staggered, with a long reverb."""
    out = np.zeros(int(1.2 * SR))
    for _ in range(9):
        f = rng.uniform(2200, 7800)
        n0 = int(rng.uniform(0, 0.28) * SR)
        p = np.sin(2 * np.pi * f * span(0.8)) * env_exp(0.8, 0.002, rng.uniform(0.18, 0.4))
        out[n0:n0 + len(p)] += p * rng.uniform(0.3, 1.0)
    return reverb(out, 2.2, 0.45, 9000)


def crt_hum(dur: float = 2.0) -> np.ndarray:
    """Old monitor hum (use very low)."""
    t = span(dur)
    hum = 0.5 * np.sin(2 * np.pi * 50 * t) + 0.25 * np.sin(2 * np.pi * 100 * t) + 0.12 * np.sin(2 * np.pi * 150 * t)
    silbido = 0.04 * np.sin(2 * np.pi * 15625 * t)
    estatica = filt(noise(dur), "bandpass", [1500, 6000], 2) * 0.1
    chispas = np.zeros(len(t))
    for _ in range(int(dur * 7)):
        i = rng.integers(0, len(t) - 400)
        chispas[i:i + 400] += filt(noise(400 / SR), "high", 2500) * env_exp(400 / SR, 0.0001, 0.001)
    return layer((hum, 1.0), (silbido, 1.0), (estatica, 1.0), (chispas, 0.5))


def beep(f: float = 880, dur: float = 0.075) -> np.ndarray:
    t = span(dur)
    onda = np.sign(np.sin(2 * np.pi * f * t))
    env = np.clip(t / 0.003, 0, 1) * np.clip((dur - t) / 0.01, 0, 1)
    return filt(onda * env, "low", 7000, 2)



def tape_stop(dur: float = 0.55) -> np.ndarray:
    """Tape stop: a falling tone (goes with the music tape-stop the mixer does)."""
    tono = sweep(420, 40, dur, 0.7) * np.linspace(1, 0.2, int(dur * SR))
    return filt(tono, "low", 2500, 2)


KIT: dict[str, tuple[Callable[[], np.ndarray], str]] = {
    "whoosh_short": (lambda: whoosh(0.38, 500, 2600, 900), "quick cut, push-in, word entering"),
    "whoosh_long": (lambda: whoosh(0.95, 260, 1700, 450, 0.55, -0.9, 0.9, 0.8), "scene transition"),
    "whoosh_low": (lambda: whoosh(0.7, 120, 700, 180, 0.6, 0.6, -0.6, 0.7), "heavy sweep, big scene change"),
    "swish": (lambda: whoosh(0.22, 1800, 6500, 3000, 0.5, -0.3, 0.3, 0.3), "small text appearing"),
    "impact": (impact, "giant word, idea hit"),
    "boom": (boom, "big cinematic moment"),
    "riser": (lambda: riser(2.0), "tension before a key moment (ends on the hit)"),
    "riser_short": (lambda: riser(1.0), "short tension"),
    "reverse": (reverse_cymbal, "lead-in to a reveal (ends on the hit)"),
    "pop": (lambda: pop(1050, 260), "subtitle or icon popping"),
    "pop_high": (lambda: pop(1700, 520), "second, higher pop"),
    "click": (click, "interface, button, cursor"),
    "tick": (lambda: tick(2300), "clock"),
    "tock": (lambda: tick(1700), "clock (second hit)"),
    "typing": (lambda: typing(1.6), "terminal, typing"),
    "notification": (notification, "message received (generic)"),
    "glitch": (lambda: glitch(0.42), "digital glitch, experimental transition"),
    "glitch_short": (lambda: glitch(0.18), "short glitch"),
    "shutter": (shutter, "photo, screenshot"),
    "text_hit": (text_hit, "word landing"),
    "sparkle": (sparkle, "achievement, positive moment"),
    "crt_hum": (lambda: crt_hum(2.0), "old monitor background (very low)"),
    "beep": (lambda: beep(880), "computer"),
    "beep_low": (lambda: beep(440, 0.11), "computer (another note)"),
    "tape_stop": (tape_stop, "tape stop (with the music stop)"),
}


def lufs_of(path: Path) -> float | None:
    """Integrated loudness (LUFS) measured with ffmpeg; None if too short to measure."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("I:") and "LUFS" in line:
            value = float(line.split()[1])
            return None if value < -69 else value
    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    data = {}
    for name, (make, use) in KIT.items():
        x = finish(make())
        path = folder / f"{name}.wav"
        sf.write(str(path), x.astype(np.float32), SR, subtype="FLOAT")
        data[name] = {"file": path.name, "seconds": round(len(x) / SR, 3), "peakDbfs": PEAK_DBFS, "lufs": lufs_of(path), "use": use}
    with open(folder / "kit.json", "w", encoding="utf-8") as f:
        json.dump({"sr": SR, "seed": SEED, "effects": data}, f, ensure_ascii=False, indent=1)
    print(f"sfx: {len(KIT)} effects -> {folder}")


if __name__ == "__main__":
    main()
