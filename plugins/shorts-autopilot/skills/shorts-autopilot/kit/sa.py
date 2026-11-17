"""shorts-autopilot command line. Run it with the Python of the studio (see references/setup.md):

  python <kit>/sa.py doctor [studio]          what is installed and what is missing (never prints keys)
  python <kit>/sa.py init <studio-folder>     creates the studio: config, engine (npm install), sound effects
  python <kit>/sa.py new <slug>               creates videos/<date>-<slug>/ with the template files (run inside the studio)
  python <kit>/sa.py voice <video>            one voice take (Gemini TTS) + shorter pauses
  python <kit>/sa.py align <video>            word timings with Whisper; reports words not heard
  python <kit>/sa.py words <video>            index:word@second list, to anchor scenes
  python <kit>/sa.py image <video> <piece> [attempt]   one image with Codex
  python <kit>/sa.py build <video>            scenes.json → build/props.json + build/sound-plan.json (checks everything)
  python <kit>/sa.py mix <video>              sound mix at -14 LUFS
  python <kit>/sa.py zones <video> [every]    text-only frames; no text where the apps cover the screen
  python <kit>/sa.py render <video>           final MP4 + quality check + contact sheet + cover
  python <kit>/sa.py page <video>             out/publish.html (texts to copy, AI-label help, links)
  python <kit>/sa.py youtube <video>          scripts for the YouTube Studio upload (Playwright)
  python <kit>/sa.py split <file>             8 MB parts + SHA-256 (for browser tools with an upload size limit)
  python <kit>/sa.py music search|download|measure ...   free Mixkit music into <studio>/music
  python <kit>/sa.py finish <video>           build + mix + zones + render + page, stopping at the first failure
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (CONFIG_NAME, ENGINE_TEMPLATE, FPS, KIT_DIR, TEMPLATES, KitError, Video, find_studio,  # noqa: E402
                    load_config, read_json, run, video_at, write_json)

PY_MODULES = ("numpy", "scipy", "soundfile", "PIL", "faster_whisper")
PART_BYTES = 8_000_000
TAIL_S = 0.6
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,50}$")


def _version(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "installed (version unreadable)"


def doctor(args: list[str]) -> None:
    report = {"python": sys.version.split()[0], "pythonOk": sys.version_info >= (3, 10),
              "pythonModules": {m: importlib.util.find_spec(m) is not None for m in PY_MODULES},
              "node": _version(["node", "--version"]), "npm": _version(["npm", "--version"]),
              "ffmpeg": _version(["ffmpeg", "-version"]), "ffprobe": _version(["ffprobe", "-version"]),
              "codex (optional, images)": _version(["codex", "--version"]), "git (optional)": _version(["git", "--version"])}
    try:
        studio = find_studio(Path(args[0]) if args else Path.cwd())
        cfg = load_config(studio)
        env_file = studio / ".env"
        has_key = bool(os.environ.get("GEMINI_API_KEY")) or (env_file.is_file() and re.search(r"^GEMINI_API_KEY=\S+", env_file.read_text(encoding="utf-8"), re.M) is not None)
        report["studio"] = {"folder": str(studio), "engineInstalled": (studio / "engine" / "node_modules" / "remotion").is_dir(),
                            "soundEffects": len(list((studio / "assets" / "sfx").glob("*.wav"))),
                            "musicFiles": len(list((studio / "music").glob("*.mp3"))), "geminiKeySet": has_key,
                            "imagesProvider": cfg["images"]["provider"], "browserTool": cfg["publishing"]["browserTool"],
                            "accountName": cfg["account"]["name"] or "(empty: run the setup interview)"}
    except KitError as e:
        report["studio"] = f"not created yet ({e})"
    print(json.dumps(report, ensure_ascii=False, indent=1))


def _copy_engine(dest: Path) -> None:
    if dest.exists():
        print(f"engine already at {dest} (not overwritten)")
        return
    shutil.copytree(ENGINE_TEMPLATE, dest, ignore=shutil.ignore_patterns("node_modules", "*.log"))


def init(args: list[str]) -> None:
    if len(args) != 1:
        raise KitError("usage: sa.py init <studio-folder>")
    studio = Path(args[0]).expanduser().resolve()
    studio.mkdir(parents=True, exist_ok=True)
    for sub in ("videos", "music", "assets/sfx", "upload"):
        (studio / sub).mkdir(parents=True, exist_ok=True)
    cfg = studio / CONFIG_NAME
    if not cfg.exists():
        shutil.copyfile(TEMPLATES / "config.example.json", cfg)
    env = studio / ".env"
    if not env.exists():
        env.write_text("# Paste your keys here yourself. Claude never types or prints them.\nGEMINI_API_KEY=\n", encoding="utf-8")
    gi = studio / ".gitignore"
    if not gi.exists():
        gi.write_text(".env\nengine/node_modules/\nupload/\nbrowser-profile/\nvideos/*/build/\nvideos/*/out/*.mp4\n", encoding="utf-8")
    _copy_engine(studio / "engine")
    print("installing the video engine (npm install, 1-3 minutes)...", flush=True)
    run(["npm", "install", "--no-audit", "--no-fund"], cwd=studio / "engine", timeout=1800)
    print("synthesizing the sound effects...", flush=True)
    run([sys.executable, str(KIT_DIR / "sfx.py"), str(studio / "assets" / "sfx")], timeout=900)
    print(f"studio ready: {studio}\nnext: fill {cfg} (setup interview) and put the Gemini key in {env}")


def new(args: list[str]) -> None:
    if not args or not SLUG.match(args[0]):
        raise KitError("usage: sa.py new <slug>  (lowercase letters, digits and dashes)")
    studio = find_studio(Path.cwd())
    folder = studio / "videos" / f"{dt.date.today().isoformat()}-{args[0]}"
    if folder.exists():
        raise KitError(f"{folder} already exists")
    shutil.copytree(TEMPLATES / "video", folder)
    spec = read_json(folder / "video.json")
    spec["date"] = dt.date.today().isoformat()
    write_json(folder / "video.json", spec, indent=2)
    for sub in ("voice", "public/img", "build", "out"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    print(folder)


def voice(args: list[str]) -> None:
    import voice as v  # noqa: PLC0415
    video = video_at(args[0])
    raw = v.generate(video)
    v.tighten(raw, video.voice("-tight"), float(load_config(video.studio)["voice"]["pauseFactor"]))


def align(args: list[str]) -> None:
    from align import MAX_MISSING, run_align  # noqa: PLC0415
    video = video_at(args[0])
    cfg = load_config(video.studio)
    data = run_align(video.voice("-tight"), video.folder / "script.json", video.words_file, cfg["whisper"]["model"],
                     cfg["videoLanguage"], cfg["whisper"]["device"])
    c = data["control"]
    print(f"script {c['scriptWords']} words · heard {c['heardWords']} · {data['duration']:.2f} s")
    print(f"not heard ({len(c['missing'])}): {c['missing']}\nheard differently or extra ({len(c['extra'])}): {c['extra']}")
    if len(c["missing"]) > MAX_MISSING:
        raise KitError("the take skipped script words: listen-check failed, make a new take (new «take» in video.json)")


def words(args: list[str]) -> None:
    video = video_at(args[0])
    ws = read_json(video.words_file)["words"]
    print(" ".join(f"{i}:{w['clean']}@{w['a']:.2f}" for i, w in enumerate(ws)))


def image(args: list[str]) -> None:
    import images  # noqa: PLC0415
    if len(args) < 2:
        raise KitError("usage: sa.py image <video> <piece> [attempt]")
    images.codex_image(video_at(args[0]), args[1], int(args[2]) if len(args) > 2 else 1)


def _texts(video: Video) -> dict:
    raw = read_json(video.folder / "texts.json", required=False)
    out = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, dict) or "text" not in value or not value.get("source"):
            raise KitError(f"texts.json: «{key}» needs «text» and «source» (no on-screen fact without a source)")
        out[key] = value["text"]
    return out


def _resolve_sound(spec: dict, ws: list[dict], duration: float) -> dict:
    from build import resolve_ref  # noqa: PLC0415
    r = lambda ref: round(resolve_ref(ref, ws, duration), 3)  # noqa: E731
    sound = spec.get("sound") or {}
    music = spec.get("music") or {}
    out = {"sound": {"extra": [{**e, "t": r(e["at"])} for e in sound.get("extra", [])]},
           "music": {"cuts": [[r(a), r(b)] for a, b in music.get("cuts", [])]}}
    for key in ("stop", "resume"):
        if music.get(key) is not None:
            out["music"][key] = r(music[key])
    return out


def build(args: list[str]) -> None:
    from build import build_props  # noqa: PLC0415
    from sound_plan import make_plan  # noqa: PLC0415
    video = video_at(args[0])
    cfg = load_config(video.studio)
    data = read_json(video.words_file)
    duration = math.ceil((data["duration"] + TAIL_S) * FPS) / FPS
    images = {p.name for p in (video.public / "img").glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")}
    spec = read_json(video.folder / "scenes.json")
    props = build_props(spec, data["words"], _texts(video), cfg, duration, images)
    write_json(video.build / "props.json", props, indent=None)
    sfx_src, sfx_dst = video.studio / "assets" / "sfx", video.public / "sfx"
    if not any(sfx_src.glob("*.wav")):
        raise KitError(f"no sound effects in {sfx_src}: run «python kit/sfx.py {sfx_src}»")
    shutil.copytree(sfx_src, sfx_dst, dirs_exist_ok=True)
    music = video.spec.get("music") or {}
    if not music.get("file"):
        raise KitError("video.json has no «music.file»: pick one with «sa.py music ...» (it goes in <studio>/music)")
    src = video.studio / "music" / music["file"]
    if not src.is_file():
        raise KitError(f"missing music file {src}")
    (video.public / "music").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, video.public / "music" / music["file"])
    plan = make_plan(props, _resolve_sound(spec, data["words"], duration), music)
    write_json(video.build / "sound-plan.json", plan)
    print(f"props: {props['frames']} frames ({props['frames'] / FPS:.2f} s), {len(props['scenes'])} scenes, "
          f"{sum(len(s['beats']) for s in props['scenes'])} beats · sound plan: {len(plan['effects'])} effects")


def mix(args: list[str]) -> None:
    from mix import mix as do_mix  # noqa: PLC0415
    video = video_at(args[0])
    report = do_mix(read_json(video.build / "sound-plan.json"), video.voice("-tight"), video.public, video.build / "mix.wav")
    print(json.dumps(report))


def _engine(video: Video) -> Path:
    engine = video.studio / "engine"
    if not (engine / "node_modules" / "remotion").is_dir():
        raise KitError(f"the engine is not installed in {engine}: run «npm install» there (or sa.py init again)")
    return engine


def zones(args: list[str]) -> None:
    from zones import check_folder  # noqa: PLC0415
    video = video_at(args[0])
    every = int(args[1]) if len(args) > 1 else 5
    props = read_json(video.build / "props.json")
    out = video.build / "control"
    if out.exists():
        shutil.rmtree(out)
    frames = [str(f) for f in range(0, props["frames"], every)]
    run(["node", "scripts/stills.mjs", "ShortControl", str(video.build / "props.json"), str(video.public), str(out), *frames],
        cwd=_engine(video), timeout=3600)
    report = check_folder(out)
    write_json(video.build / "zones.json", report)
    print(f"{report['framesChecked']} frames checked (every {every}) · lasting covered text: {report['lastingCovered']} "
          f"{report['lastingFrames'][:30]} · single-frame entries: {report['singleFrameEntries']}")
    if report["lastingCovered"]:
        raise KitError("text sits where the apps cover the screen: move or shorten it (see build/zones.json)")


def _rendered(path: Path) -> None:
    """Windows can keep the file busy: Remotion then leaves <name>.remotion-in-progress (measured). Rename it."""
    pending = path.with_name(path.name + ".remotion-in-progress")
    if not path.exists() and pending.exists():
        pending.rename(path)
    if not path.exists():
        raise KitError(f"the render did not produce {path}")


def render(args: list[str]) -> None:
    from quality import check  # noqa: PLC0415
    video = video_at(args[0])
    engine = _engine(video)
    silent = video.build / "silent.mp4"
    run(["npx", "remotion", "render", "src/index.ts", "Short", str(silent), f"--props={video.build / 'props.json'}",
         f"--public-dir={video.public}", "--muted", "--crf=16"], cwd=engine, timeout=7200)
    _rendered(silent)
    mixed = video.build / "mix.wav"
    if not mixed.is_file():
        raise KitError("no build/mix.wav: run «sa.py mix» first")
    final = video.out / f"{video.slug}.mp4"
    final.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent), "-i", str(mixed), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-af", "apad", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(final)])
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "0.5", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(video.out / "cover.jpg")])
    report = check(final, video.out / "sheet.jpg")
    print(json.dumps({k: report[k] for k in ("frames", "seconds", "lufs", "peakDbtp", "black", "frozen", "problems", "approved")}))
    print(f"final: {final}\ncontact sheet (look at it): {video.out / 'sheet.jpg'}")
    if not report["approved"]:
        raise KitError("the quality check failed: see the problems above")


def page(args: list[str]) -> None:
    from publish import build_page  # noqa: PLC0415
    video = video_at(args[0])
    print(build_page(video, video.out / f"{video.slug}.mp4"))


def youtube(args: list[str]) -> None:
    from youtube import prepare  # noqa: PLC0415
    video = video_at(args[0])
    folder = prepare(video, video.out / f"{video.slug}.mp4")
    print(f"ready: {folder} (yt_step1.js, yt_step2.js, yt_step3.js, video.mp4). Delete video.mp4 after the upload.")


def split(args: list[str]) -> None:
    if not args:
        raise KitError("usage: sa.py split <file> [part-bytes]")
    src = Path(args[0]).resolve()
    size = int(args[1]) if len(args) > 1 else PART_BYTES
    data = src.read_bytes()
    folder = src.parent / f"{src.stem}-parts"
    folder.mkdir(exist_ok=True)
    parts = []
    for k in range(0, len(data), size):
        p = folder / f"part{k // size}"
        p.write_bytes(data[k:k + size])
        parts.append(str(p))
    print(json.dumps({"file": str(src), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "parts": parts}, indent=1))


def music(args: list[str]) -> None:
    studio = find_studio(Path.cwd())
    env = {**os.environ, "SA_MUSIC_DIR": str(studio / "music")}
    proc = subprocess.run([sys.executable, str(KIT_DIR / "music.py"), *args], env=env)
    if proc.returncode:
        raise KitError("music command failed (see above)")


def finish(args: list[str]) -> None:
    for step in (build, mix, zones, render, page):
        print(f"--- {step.__name__}", flush=True)
        step(args[:1])


COMMANDS = {"doctor": doctor, "init": init, "new": new, "voice": voice, "align": align, "words": words, "image": image,
            "build": build, "mix": mix, "zones": zones, "render": render, "page": page, "youtube": youtube, "split": split,
            "music": music, "finish": finish}


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(__doc__)
    name, args = sys.argv[1], sys.argv[2:]
    if name not in ("doctor", "init", "new", "split", "music") and not args:
        raise SystemExit(f"usage: sa.py {name} <video-folder>")
    try:
        COMMANDS[name](args)
    except KitError as e:
        print(f"STOP: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
