# shorts-autopilot

**Faceless vertical shorts, made end to end by Claude Code.** You say "find a trending topic, make the video and
publish it"; Claude researches it, verifies every fact in primary sources, writes the script, generates the voice,
lays out animated captions anchored to each spoken word, mixes music and sound effects, checks the result with
numbers, and publishes (or leaves everything ready for you to publish).

[Leer en español](README.es.md)

## What you get

- A 60-110 s vertical video (1080×1920, 30 fps, -14 LUFS) for YouTube Shorts, TikTok, Instagram Reels and X.
- Every on-screen fact comes from `texts.json` with its source and the date it was read. No source, no fact.
- AI disclosure is built in: a "made with AI" badge, a label on every AI image, the AI switch on every network.
- Automatic checks: words the voice skipped, text where the apps cover the screen, loudness, black or frozen frames,
  and a contact sheet Claude looks at before publishing.
- A first-time setup interview: Claude checks your machine, installs what is missing (asking first), and asks about
  your account, language, look and how you want to publish.

## Requirements and costs

| Piece | Cost | Notes |
|---|---|---|
| Claude Code | paid Claude plan | the agent that runs everything |
| Python 3.10+, Node.js 18+, ffmpeg | free | Claude installs them with your OK |
| Voice: Gemini text-to-speech | free tier | your own Google AI Studio key; measured quota 10 requests/day |
| Images: Codex CLI | inside a ChatGPT plan | or use your own images, or none (typography-only style) |
| Music: Mixkit | free | license recorded per track |
| Video engine: Remotion | free for individuals and companies up to 3 people | company license above that |
| Publishing | free | YouTube via browser, Metricool free plan (20 posts/month), or manual |

Tested on Windows 11 with Python 3.11 and Node 24 (16-17/11/2026). macOS and Linux commands are documented but were
not tested yet.

## Install

Inside Claude Code:

```
/plugin marketplace add germangalo97/shorts-autopilot
/plugin install shorts-autopilot@shorts-autopilot
```

Or copy `plugins/shorts-autopilot/skills/shorts-autopilot` into `~/.claude/skills/`.

Then just say: **"set up shorts-autopilot"** (or "make me a faceless short"). Claude runs the setup interview the
first time.

## How it works

```
topic + facts → script.json → voice (Gemini) → word timings (Whisper) → images → scenes.json
  → build (checks every anchor, fact and image) → mix (-14 LUFS) → covered-zone check → render
  → quality check + contact sheet → publish.html / upload → links recorded
```

Claude writes `scenes.json` (scenes anchored to spoken words, e.g. `"12:word"`); the kit lays out every line inside
the safe zone, generates the sound design from the scenes, and the Remotion engine draws the frames. Details:
[SKILL.md](plugins/shorts-autopilot/skills/shorts-autopilot/SKILL.md) and the `references/` folder.

## Publishing and platform rules

YouTube Studio through a browser profile you log into yourself, Metricool's free plan, or manual upload with a page
of ready-to-copy texts. Instagram and TikTok through their websites is **off by default**: their terms forbid
automated interaction, so it is only enabled if you accept that risk explicitly.

## Honest limits

- Claude cannot listen: audio is checked by measurement (loudness, words heard), not by ear.
- Facts are only as good as the sources: the skill forces sources, it cannot make a bad source good.
- Platform interfaces change; the browser steps may need updating. Report it in an issue.

## Tests

```
cd plugins/shorts-autopilot/skills/shorts-autopilot/kit
python -m pytest tests -q
```

## License

MIT for this repository's code. Third-party software and services keep their own terms: see [NOTICE.md](NOTICE.md).
