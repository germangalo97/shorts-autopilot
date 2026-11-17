"""Quality control of a finished video, before anyone publishes it.

Measures (does not assume): size, frame rate and color tags, image and sound duration, integrated loudness and true
peak, black stretches and frozen stretches, and builds a contact sheet (one frame every half second) to look at.
Any mandatory check that fails makes the whole check fail.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from common import FPS, KitError, write_json

SIZE = (1080, 1920)
TARGET_LUFS, TOLERANCE_LU, MAX_PEAK = -14.0, 0.5, -1.0
MAX_AV_DIFF_S = 0.05
BLACK_MIN_S, FROZEN_MIN_S = 0.25, 0.6
SHEET_EVERY_S = 0.5
SHEET_COLUMNS, SHEET_CELL = 10, 216


def _run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def streams(path: Path) -> dict:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,pix_fmt,r_frame_rate,nb_frames,"
                "duration,color_space", "-of", "json", str(path)])
    return {s["codec_type"]: s for s in json.loads(out[out.find("{"):])["streams"]}


def loudness(path: Path) -> tuple[float, float]:
    out = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = out[out.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    if not i or not p:
        raise KitError("could not measure loudness")
    return float(i.group(1)), float(p.group(1))


def stretches(path: Path, vf: str, start_key: str, end_key: str) -> list[list[float]]:
    out = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", vf, "-an", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(rf"{start_key}:\s*(-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(rf"{end_key}:\s*(-?[\d.]+)", out)]
    return [[a, b] for a, b in zip(starts, ends + [None] * (len(starts) - len(ends)))]


def contact_sheet(video: Path, out: Path, duration: float) -> None:
    from PIL import Image, ImageDraw  # noqa: PLC0415

    tmp = out.with_suffix("")
    tmp.mkdir(parents=True, exist_ok=True)
    step = round(SHEET_EVERY_S * FPS)
    n = int(duration / SHEET_EVERY_S)
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vf",
          f"select=not(mod(n\\,{step})),scale=270:-1", "-fps_mode", "vfr", "-frames:v", str(n), str(tmp / "c_%04d.png")])
    files = sorted(tmp.glob("c_*.png"))
    if not files:
        raise KitError("could not extract frames for the contact sheet")
    with Image.open(files[0]) as first:  # closed before deleting: Windows cannot delete an open file
        height = round(SHEET_CELL * first.height / first.width)
    rows = (len(files) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    sheet = Image.new("RGB", (SHEET_COLUMNS * SHEET_CELL, rows * height), (20, 20, 20))
    for i, f in enumerate(files):
        with Image.open(f) as im:
            cell = im.convert("RGB").resize((SHEET_CELL, height), Image.LANCZOS)
        frame = i * step
        d = ImageDraw.Draw(cell)
        d.rectangle((0, 0, 150, 22), fill=(0, 0, 0))
        d.text((5, 5), f"{frame}  ({frame / FPS:.2f} s)", fill=(255, 220, 0))
        sheet.paste(cell, ((i % SHEET_COLUMNS) * SHEET_CELL, (i // SHEET_COLUMNS) * height))
        f.unlink()
    tmp.rmdir()
    sheet.save(out, quality=88)


def check(video: Path, sheet: Path) -> dict:
    s = streams(video)
    v, a = s.get("video", {}), s.get("audio", {})
    problems = []
    if (v.get("width"), v.get("height")) != SIZE:
        problems.append(f"size {v.get('width')}x{v.get('height')} (expected 1080x1920)")
    if v.get("r_frame_rate") != f"{FPS}/1":
        problems.append(f"frame rate {v.get('r_frame_rate')}")
    if v.get("pix_fmt") != "yuv420p":
        problems.append(f"pixel format {v.get('pix_fmt')}")
    if v.get("color_space") not in ("bt709", None):
        problems.append(f"color space {v.get('color_space')}")
    if not a:
        problems.append("no sound")
    dur_v, dur_a = float(v.get("duration", 0)), float(a.get("duration", 0) or 0)
    if a and abs(dur_v - dur_a) > MAX_AV_DIFF_S:
        problems.append(f"image {dur_v:.3f} s vs sound {dur_a:.3f} s")
    lufs, peak = loudness(video) if a else (None, None)
    if lufs is not None and (abs(lufs - TARGET_LUFS) > TOLERANCE_LU or peak > MAX_PEAK):
        problems.append(f"loudness {lufs} LUFS / peak {peak} dBTP")
    blacks = stretches(video, f"blackdetect=d={BLACK_MIN_S}:pix_th=0.06", "black_start", "black_end")
    frozen = stretches(video, f"freezedetect=n=0.002:d={FROZEN_MIN_S}", "freeze_start", "freeze_end")
    if blacks:
        problems.append(f"black stretches: {blacks}")
    if frozen:
        problems.append(f"frozen stretches: {frozen}")
    contact_sheet(video, sheet, dur_v)
    report = {"video": str(video), "frames": v.get("nb_frames"), "seconds": dur_v, "lufs": lufs, "peakDbtp": peak,
              "black": blacks, "frozen": frozen, "problems": problems, "approved": not problems, "sheet": str(sheet)}
    write_json(video.with_name(video.stem + "_control.json"), report)
    return report
