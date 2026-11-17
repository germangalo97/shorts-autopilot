"""Images for the backgrounds.

Providers (config «images.provider»):
- «codex»: Codex CLI with the image tool of a ChatGPT plan (no extra cost inside the plan's limits). One image per
  request; Codex runs in an empty folder, read-only, without reading project documents, so it cannot read or send
  your files. The request, the result and the usage reported by Codex are logged per attempt.
- «folder»: the person drops their own images (or ones made in any app) into <video>/public/img/.
- «none»: no photos; scenes use solid colors and the pieces (typography-only style).
Every image made by an AI is labeled on screen and declared on every network.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path

from common import KitError, Video, read_json, write_json

VALID = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
FIELDS = ("piece", "purpose", "image", "constraints")
TIMEOUT_S = 900
EFFORT = "low"
PROMPT = """<task>
Create one image with your image generation tool. Call the tool exactly once, with transparent_background false.
Purpose: {purpose}
Image: {image}
Constraints: {constraints}
</task>
<action_safety>
Do not read, list or write any files. Do not run shell commands. Do not browse the web.
</action_safety>
<compact_output_contract>
Reply with one line: "done" or the exact error.
</compact_output_contract>
"""


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def requests(video: Video) -> list[dict]:
    pieces = read_json(video.folder / "images.json").get("pieces") or []
    if not pieces:
        raise KitError("images.json has no pieces")
    for p in pieces:
        missing = [f for f in FIELDS if not p.get(f)]
        if missing:
            raise KitError(f"image piece {p.get('piece')!r} lacks: {', '.join(missing)}")
        if not VALID.match(p["piece"]):
            raise KitError(f"invalid piece name {p['piece']!r} (lowercase, digits, dashes)")
    return pieces


def _events(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("{"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise KitError(f"{path} is not a PNG")
    return struct.unpack(">II", head[16:24])


def _limits(session: Path) -> dict | None:
    seen = None
    for e in _events(session):
        p = e.get("payload")
        if isinstance(p, dict) and p.get("type") == "token_count" and isinstance(p.get("rate_limits"), dict):
            r = p["rate_limits"]
            seen = {"window5hUsedPct": (r.get("primary") or {}).get("used_percent"),
                    "weekUsedPct": (r.get("secondary") or {}).get("used_percent"), "plan": r.get("plan_type")}
    return seen


def codex_image(video: Video, piece: str, attempt: int) -> Path:
    exe = shutil.which("codex")
    if not exe:
        raise KitError("Codex CLI is not installed (npm install -g @openai/codex, then «codex login» with a ChatGPT plan)")
    spec = next((p for p in requests(video) if p["piece"] == piece), None)
    if spec is None:
        raise KitError(f"there is no piece «{piece}» in images.json")
    name = f"{piece}-attempt-{attempt}"
    logs = video.folder / "images-log"
    logs.mkdir(parents=True, exist_ok=True)
    record = logs / f"{name}.json"
    if record.exists():
        raise KitError(f"{record} exists: that attempt was already made (use the next attempt number)")
    prompt = PROMPT.format(**{k: spec[k] for k in FIELDS[1:]})
    (logs / f"{name}.txt").write_text(prompt, encoding="utf-8")
    work = video.build / "codex-empty-folder"
    work.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-C", str(work),
           "-c", f"model_reasoning_effort={EFFORT}", "-c", "project_doc_max_bytes=0", "-"]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_S)
    raw = logs / f"{name}.jsonl"
    raw.write_text(proc.stdout, encoding="utf-8")
    thread = next((e.get("thread_id") for e in _events(raw) if e.get("type") == "thread.started"), None)
    if not thread:
        raise KitError(f"Codex did not start a session (exit {proc.returncode}): {proc.stderr[-800:]}")
    sessions = list((codex_home() / "sessions").rglob(f"rollout-*-{thread}.jsonl"))
    if len(sessions) != 1:
        raise KitError(f"expected 1 Codex session log for {thread}, found {len(sessions)}")
    images = []
    for e in _events(sessions[0]):
        item = (e.get("payload") or {}).get("item") if isinstance(e.get("payload"), dict) else None
        if isinstance(item, dict) and item.get("kind") == "image_gen.generation":
            images.append(item)
    if not images:
        raise KitError(f"Codex made no image (exit {proc.returncode}); see {raw}")
    dest = video.public / "img" / f"{piece}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = images[0]
    src = Path(img["savedPath"]) if img.get("savedPath") else None
    if src and src.is_file():
        shutil.copyfile(src, dest)
    elif img.get("result"):
        dest.write_bytes(base64.b64decode(img["result"]))
    else:
        raise KitError(f"Codex reported an image without file or data: {img.get('failure')}")
    w, h = _png_size(dest)
    write_json(record, {"piece": piece, "attempt": attempt, "when": dt.datetime.now().isoformat(timespec="seconds"),
                        "seconds": round(time.monotonic() - t0, 1), "file": str(dest), "width": w, "height": h,
                        "codexLimitsAfter": _limits(sessions[0]), "revisedPrompt": img.get("revisedPrompt")}, indent=2)
    print(f"image: {dest} ({w}×{h}, {time.monotonic() - t0:.0f} s) · Codex limits after: {_limits(sessions[0])}")
    return dest
