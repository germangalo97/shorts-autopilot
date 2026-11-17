"""Checks that no text sits where the apps cover a vertical video (header on top; name, caption and music at the
bottom; the button column on the right). Reads frames of the CONTROL composition (only text, no photos) and counts lit
pixels per zone. The zones are the most prudent values from third-party guides read on 07/11/2026 (AdMake,
AdaptlyPost, Wild & Free Tools, bundle.social); there is no official document from the apps."""
from __future__ import annotations

from pathlib import Path

import numpy as np

ZONES = {"top": (0, 230, 0, 1080), "bottom": (1440, 1920, 0, 1080), "buttons": (700, 1750, 920, 1080)}
LIGHT = 70  # the control background is #0E0E0E (14): a pixel with a channel above 70 is drawing
MIN_PIXELS = 150  # fewer than this are loose edges, not a letter


def count_lit(frame: np.ndarray) -> dict[str, int]:
    lit = frame[..., :3].max(axis=2) > LIGHT
    return {name: int(lit[y0:y1, x0:x1].sum()) for name, (y0, y1, x0, x1) in ZONES.items()}


def covered(counts: dict[str, int]) -> list[str]:
    return [z for z, n in counts.items() if n >= MIN_PIXELS]


def split_flags(flags: dict[int, list[str]], step: int) -> tuple[list[int], list[int]]:
    """LASTING problems (the same zone is also flagged on the previous or next checked frame) vs ENTRIES (a single
    frame: a word that enters scaled-up and blurred)."""
    lasting, entries = [], []
    for frame, zones in sorted(flags.items()):
        near = set(flags.get(frame - step, [])) | set(flags.get(frame + step, []))
        (lasting if near & set(zones) else entries).append(frame)
    return lasting, entries


def check_folder(folder: Path) -> dict:
    from PIL import Image  # noqa: PLC0415

    files = sorted(folder.glob("*.png"))
    if not files:
        raise SystemExit(f"no frames in {folder}")
    flags, detail = {}, []
    for f in files:
        with Image.open(f) as im:
            frame = np.asarray(im.convert("RGB"))
        if frame.shape[:2] != (1920, 1080):
            raise SystemExit(f"{f.name}: {frame.shape[1]}×{frame.shape[0]}, expected 1080×1920")
        counts = count_lit(frame)
        zones = covered(counts)
        if zones:
            n = int(f.stem.rsplit("_", 1)[-1])
            flags[n] = zones
            detail.append({"frame": n, "zones": zones, "pixels": counts})
    numbers = sorted(int(f.stem.rsplit("_", 1)[-1]) for f in files)
    step = min((b - a for a, b in zip(numbers, numbers[1:])), default=1)
    lasting, entries = split_flags(flags, step)
    return {"framesChecked": len(files), "every": step, "lastingCovered": len(lasting), "lastingFrames": lasting,
            "singleFrameEntries": entries, "detail": detail, "zones": ZONES}
