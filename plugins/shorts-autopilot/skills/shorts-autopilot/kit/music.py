"""Free music from Mixkit: search by genre or mood, download with its license, and MEASURE each track.

Claude cannot listen: a track is chosen by its tags and by what is measured (beats per minute, major or minor key,
loudness, how much the energy varies). What was chosen and why is written in the studio's music/ folder.

Usage (from the studio):
  python kit/music.py search <genre-or-mood-page> [...]     e.g. «genre/pop» or «mood/happy» → music/search.json
  python kit/music.py download <id> [<id> ...]              → music/mixkit_<id>.mp3 + music/licenses.json
  python kit/music.py measure [<id> ...]                    → music/measures.json

License: «Mixkit Stock Music Free License». «download» checks that the track page shows that license before
downloading. Read the license yourself on mixkit.co before publishing; this tool does not give legal advice.
"""
from __future__ import annotations

import html as html_lib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

CARPETA = Path(os.environ.get("SA_MUSIC_DIR", "music"))
BASE = "https://mixkit.co/free-stock-music/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PAUSA_S = 1.4
TIMEOUT_S = 40
RE_PREVIEW = re.compile(r'data-audio-player-preview-url-value="https://assets\.mixkit\.co/music/(\d+)/\d+\.mp3"')
RE_TITULO = re.compile(r"<h2[^>]*>\s*([^<]+?)\s*</h2>")
RE_ETIQUETA = re.compile(r'href="/free-stock-music/(?:tag|mood)/([a-z0-9-]+)/"')
RE_DURACION = re.compile(r">\s*(\d{1,2}:\d{2})\s*<")
SR_MEDIR = 22050


ESPERA_429_S = 30  # the site answers 429 when asked too often: wait longer each time


def pedir(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for intento in range(5):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if intento == 4:
                raise RuntimeError(f"could not download {url}: {e}") from e
            espera = ESPERA_429_S * (intento + 1) if e.code == 429 else PAUSA_S * (intento + 2)
            print(f"  {e.code} en {url}: waiting {espera:.0f} s", flush=True)
            time.sleep(espera)
        except OSError as e:
            if intento == 4:
                raise RuntimeError(f"could not download {url}: {e}") from e
            time.sleep(PAUSA_S * (intento + 2))
    raise RuntimeError(url)


def buscar(paginas: list[str]) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / "search.json"
    tracks = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    for pagina in paginas:
        s = pedir(BASE + pagina.strip("/") + "/").decode("utf-8", "replace")
        marcas = list(RE_PREVIEW.finditer(s))
        for i, m in enumerate(marcas):
            fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(s)
            bloque = s[m.start(): fin]
            titulo = RE_TITULO.search(bloque)
            tid = m.group(1)
            t = tracks.setdefault(tid, {"id": tid, "title": None, "tags": [], "duration": None, "pages": []})
            t["title"] = html_lib.unescape(titulo.group(1)) if titulo else t["title"]
            t["tags"] = sorted(set(t["tags"]) | set(RE_ETIQUETA.findall(bloque)))
            dur = RE_DURACION.search(bloque)
            t["duration"] = dur.group(1) if dur else t["duration"]
            if pagina not in t["pages"]:
                t["pages"].append(pagina)
        print(f"{pagina}: {len(marcas)} tracks")
        time.sleep(PAUSA_S)
    ruta.write_text(json.dumps(temas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(temas)} tracks in {ruta}")


PAUSA_ARCHIVO_S = 3.0


def bajar(ids: list[str]) -> None:
    """With «--no-page» the track page is not opened (the site may answer 429 / a Cloudflare challenge): the file
    is downloaded and the record says the page was not re-read."""
    sin_pagina = "--no-page" in ids
    ids = [i for i in ids if not i.startswith("--")]
    busqueda = json.loads((CARPETA / "search.json").read_text(encoding="utf-8"))
    ruta_lic = CARPETA / "licenses.json"
    licencias = json.loads(ruta_lic.read_text(encoding="utf-8")) if ruta_lic.exists() else {}
    fallidos = []
    for tid in ids:
        info = busqueda.get(tid, {"title": None})
        destino = CARPETA / f"mixkit_{tid}.mp3"
        if destino.name in licencias and destino.exists():
            print(f"{tid}: already here · {info.get('titulo')}")
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", (info.get("title") or "").lower()).strip("-")
        pagina = f"{BASE}{slug}-{tid}/"
        try:
            if not sin_pagina:
                s = pedir(pagina).decode("utf-8", "replace")
                if "Mixkit Stock Music Free License" not in s and "musicFree" not in s:
                    print(f"{tid}: the free music license is not shown on {pagina}, NOT downloaded")
                    continue
            destino.write_bytes(pedir(f"https://assets.mixkit.co/music/{tid}/{tid}.mp3"))
        except RuntimeError as e:
            print(f"{tid}: FAILED ({e})")
            fallidos.append(tid)
            continue
        licencias[destino.name] = {"title": info.get("title"), "url": pagina, "tags": info.get("tags"),
                                   "license": "Mixkit Stock Music Free License", "downloaded": date.today().isoformat(),
                                   "pageChecked": not sin_pagina}
        if sin_pagina:
            time.sleep(PAUSA_ARCHIVO_S)
        ruta_lic.write_text(json.dumps(licencias, ensure_ascii=False, indent=1), encoding="utf-8")  # saved track by track
        print(f"{tid}: ok · {info.get('titulo')}")
        time.sleep(PAUSA_S)
    if fallidos:
        print(f"could not download: {' '.join(fallidos)} (run «download» again with those)")


# ---------------------------------------------------------------- medir
def leer_mono(ruta: Path) -> np.ndarray:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(ruta), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR_MEDIR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).astype(np.float64)


def espectro(x: np.ndarray, n: int = 2048, paso: int = 512) -> np.ndarray:
    ventana = np.hanning(n)
    cuadros = 1 + (len(x) - n) // paso
    idx = np.arange(n)[None, :] + paso * np.arange(cuadros)[:, None]
    return np.abs(np.fft.rfft(x[idx] * ventana, axis=1))


def pulsos_por_minuto(mag: np.ndarray, paso_s: float) -> float:
    flujo = np.maximum(np.diff(np.log1p(mag), axis=0), 0).sum(1)
    flujo = flujo - flujo.mean()
    ac = np.correlate(flujo, flujo, mode="full")[len(flujo) - 1:]
    retardos = np.arange(len(ac)) * paso_s
    validos = (retardos > 60 / 185) & (retardos < 60 / 68)
    mejor = np.argmax(np.where(validos, ac, -np.inf))
    return 60 / retardos[mejor]


PERFIL_MAYOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
PERFIL_MENOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def tonalidad(mag: np.ndarray, n: int = 2048) -> tuple[str, float]:
    f = np.fft.rfftfreq(n, 1 / SR_MEDIR)
    ok = (f > 55) & (f < 2000)
    clase = (np.round(12 * np.log2(f[ok] / 261.63)) % 12).astype(int)
    croma = np.zeros(12)
    np.add.at(croma, clase, mag[:, ok].sum(0))
    mejor, nombre = -2.0, ""
    for t in range(12):
        for perfil, modo in ((PERFIL_MAYOR, "major"), (PERFIL_MENOR, "minor")):
            r = np.corrcoef(croma, np.roll(perfil, t))[0, 1]
            if r > mejor:
                mejor, nombre = r, f"{NOTAS[t]} {modo}"
    return nombre, float(mejor)


def lufs(ruta: Path) -> float | None:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    for linea in reversed(out.splitlines()):
        if linea.strip().startswith("I:") and "LUFS" in linea:
            return float(linea.split()[1])
    return None


def medir(ids: list[str]) -> None:
    licencias = json.loads((CARPETA / "licenses.json").read_text(encoding="utf-8"))
    ruta_m = CARPETA / "measures.json"
    medidas = json.loads(ruta_m.read_text(encoding="utf-8")) if ruta_m.exists() else {}
    archivos = [f"mixkit_{i}.mp3" for i in ids] if ids else list(licencias)
    for nombre in archivos:
        ruta = CARPETA / nombre
        x = leer_mono(ruta)
        mag = espectro(x)
        paso_s = 512 / SR_MEDIR
        acum = np.concatenate([[0.0], np.cumsum(x * x)])  # 1 s moving average with cumulative sums (O(N))
        ini = np.arange(0, len(x) - SR_MEDIR, SR_MEDIR // 2)
        rms = np.sqrt((acum[ini + SR_MEDIR] - acum[ini]) / SR_MEDIR)
        energia_db = 20 * np.log10(np.maximum(rms, 1e-6))
        tono, confianza = tonalidad(mag)
        medidas[nombre] = {"title": licencias.get(nombre, {}).get("title"), "seconds": round(len(x) / SR_MEDIR, 1),
                           "bpm": round(pulsos_por_minuto(mag, paso_s), 1), "key": tono,
                           "keyConfidence": round(confianza, 2), "lufs": lufs(ruta),
                           "energyDbP10P90": [round(float(np.percentile(energia_db, 10)), 1),
                                                  round(float(np.percentile(energia_db, 90)), 1)],
                           "tags": licencias.get(nombre, {}).get("tags")}
        m = medidas[nombre]
        print(f"{nombre:18s} {m['titulo']!s:28s} {m['duracion_s']:6.1f}s {m['ppm']:6.1f} ppm  {m['tonalidad']:10s} "
              f"({m['confianza_tonalidad']})  {m['lufs']} LUFS  energy {m['energia_db_p10_p90']}")
    ruta_m.write_text(json.dumps(medidas, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("search", "download", "measure"):
        raise SystemExit(__doc__)
    accion, args = sys.argv[1], sys.argv[2:]
    {"search": buscar, "download": bajar, "measure": medir}[accion](args)


if __name__ == "__main__":
    main()
