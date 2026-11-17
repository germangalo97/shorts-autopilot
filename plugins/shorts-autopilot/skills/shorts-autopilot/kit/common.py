"""Shared helpers: errors, word cleaning, JSON, the studio folder and its config, running external commands."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

FPS = 30
CONFIG_NAME = "config.json"
STUDIO_MARK = "shortsAutopilot"
KIT_DIR = Path(__file__).resolve().parent
SKILL_DIR = KIT_DIR.parent
ENGINE_TEMPLATE = SKILL_DIR / "engine"
TEMPLATES = SKILL_DIR / "templates"


class KitError(Exception):
    """A problem the person (or Claude) has to fix. The message says what and where."""


def clean_word(text: str) -> str:
    """Lowercase, no accents, no signs (keeps ñ): «¿Está?» → «esta»."""
    t = text.lower().replace("ñ", "\x00")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\x00]", "", t)
    return t.replace("\x00", "ñ")


def read_json(path: Path, required: bool = True) -> dict:
    if not path.is_file():
        if required:
            raise KitError(f"missing file: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise KitError(f"{path} is not valid JSON: {e}") from e


def write_json(path: Path, data: dict, indent: int | None = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def to_frame(seconds: float) -> int:
    return int(round(seconds * FPS))


def find_studio(start: Path) -> Path:
    """The studio is the folder with config.json (marked «shortsAutopilot»). Searched from `start` upwards."""
    for folder in [start.resolve(), *start.resolve().parents]:
        cfg = folder / CONFIG_NAME
        if cfg.is_file():
            try:
                if STUDIO_MARK in json.loads(cfg.read_text(encoding="utf-8")):
                    return folder
            except json.JSONDecodeError:
                continue
    raise KitError(f"no studio found from {start}: run «python kit/sa.py init <folder>» first (see references/setup.md)")


def load_config(studio: Path) -> dict:
    defaults = read_json(TEMPLATES / "config.example.json")
    user = read_json(studio / CONFIG_NAME)
    return deep_merge(defaults, user)


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def secret(studio: Path, name: str) -> str:
    """Reads a key from the environment or from <studio>/.env. Never print the value."""
    if os.environ.get(name):
        return os.environ[name]
    env = studio / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name and value.strip():
                return value.strip().strip('"').strip("'")
    raise KitError(f"{name} is not set: the person adds it to {env} (Claude never types or prints it)")


@dataclass(frozen=True)
class Video:
    """One video = one folder inside <studio>/videos/."""
    folder: Path
    studio: Path

    @property
    def spec(self) -> dict:
        return read_json(self.folder / "video.json")

    @property
    def take(self) -> str:
        return self.spec.get("take", "take-1")

    def voice(self, suffix: str = "") -> Path:
        return self.folder / "voice" / f"{self.take}{suffix}.wav"

    @property
    def words_file(self) -> Path:
        return self.folder / "voice" / f"{self.take}.words.json"

    @property
    def public(self) -> Path:
        return self.folder / "public"

    @property
    def build(self) -> Path:
        return self.folder / "build"

    @property
    def out(self) -> Path:
        return self.folder / "out"

    @property
    def slug(self) -> str:
        return self.folder.name


def video_at(path: str | Path) -> Video:
    folder = Path(path).resolve()
    if not (folder / "video.json").is_file():
        raise KitError(f"{folder} is not a video folder (no video.json). Create one with «python kit/sa.py new <slug>»")
    return Video(folder=folder, studio=find_studio(folder))


def need(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        raise KitError(f"«{tool}» is not installed or not in PATH (see references/setup.md)")
    return found


def run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> str:
    """Runs a command; on failure raises KitError with the end of its output (never swallowed)."""
    exe = need(cmd[0])
    proc = subprocess.run([exe, *cmd[1:]], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr)[-2500:]
        raise KitError(f"{' '.join(cmd[:3])}… failed (exit {proc.returncode}):\n{tail}")
    return proc.stdout + proc.stderr
