---
name: shorts-autopilot
description: "Use when the person wants a faceless vertical short video (YouTube Shorts, TikTok, Instagram Reels, X) made end to end by Claude: research a trending topic, verify every fact in primary sources, write the script, AI voice, AI or own images, animated captions, sound design, quality checks, and publishing. Triggers: «make a faceless short», «make a video about <topic> and publish it», «find a trending topic and make the video», «haz un video sin cara», «hagamos un short y lo publicamos», «otro video como el anterior», or when they ask to set up / configure this video pipeline. Also use for the first-time setup interview. Not for videos where the person films themselves."
license: MIT
metadata:
  version: "1.0.0"
---

# shorts-autopilot: from a trending topic to a published short

A 60-110 s vertical video where code does everything: script (Claude), voice (Gemini text-to-speech, free tier),
background images (Codex with a ChatGPT plan, the person's own images, or none), free music (Mixkit), synthesized sound
effects, and every frame drawn by a Remotion engine from a scene list Claude writes. The method behind it went from
first search to published Short in 48 minutes on 16/11/2026, with no cost beyond plans the person already had.

**Principle:** everything the video states comes from a source read today, and every step has a check with a number
(words heard, text in covered zones, loudness, black/frozen frames, platform checks). A failed check gets fixed and
repeated. Never report success on a check that did not run.

`SKILL` below = this skill's base directory (shown when the skill loads). `STUDIO` = the person's studio folder.
Commands run from STUDIO with the studio's Python: `<py> "SKILL/kit/sa.py" <command> ...`
(`<py>` = `STUDIO/.venv/Scripts/python.exe` on Windows, `STUDIO/.venv/bin/python` on macOS/Linux).

## Non-negotiable rules

- **Facts:** research with today's date, primary sources (official pages, the original document), and a second pass for
  anything newer before writing. Every on-screen fact goes in `texts.json` with `source` and `read` date; scenes use it
  as `$t:key`. If a fact cannot be verified, it does not go in the video. Never invent data, results or quotes.
- **AI disclosure, always:** the "made with AI" badge stays on the whole video, every AI image carries its label, every
  network gets its AI label switched on, and every caption says the images/voice are AI. The person cannot turn this off.
- **People and brands:** no real people's faces or voices, no logos, no copyrighted characters or footage, no clients or
  private individuals named. Image prompts always say "no text, no logos, no real people".
- **Money:** free first. Before anything that costs money, say what, how much and when, and wait for a yes.
- **Secrets:** API keys and passwords are pasted by the person into `STUDIO/.env` or the website themselves. Claude
  never types, prints, logs or commits them.
- **Browser:** only with the person's OK for that specific task (a request to publish counts for that publication).
  Do only what was asked; never accept terms, change account settings, or create accounts. At the end, list every
  click/page and close the tabs you opened.
- **Plain language:** the person may be on day one with Claude Code. Explain every technical word where it appears,
  in their language (`config.uiLanguage`). Give absolute file paths in plain text at the end.

## Step 0: is there a studio?

Run `<py> SKILL/kit/sa.py doctor` (or `python` if there is no venv yet). If there is no studio, or `account.name` is
empty, do the **setup interview** in `references/setup.md` before anything else. It installs what is missing (each
install explained and approved), creates the studio, and saves the answers in `STUDIO/config.json`.

## Who picks the topic

- `config.topics.chooseTopic = "auto"`, or they said "/goal", "just do it", or they are away: pick with data and
  explain why in the report.
- Otherwise: show a top 3 (one line each: why it is trending, measured numbers, source, risk) and let them choose.
- A topic that expires in 1-3 days and can be checked in an official source wins (one 60-70 s version for all networks).
- Research recipe and script rules: `references/writing.md`.

## The pipeline (each step has a check)

| # | Step | Command / action | Check that must pass |
|---|---|---|---|
| 1 | Topic + facts | `references/writing.md` (search, measure views, open primary sources) | each fact opened in its source today |
| 2 | Folder | `sa.py new <slug>` | `videos/<date>-<slug>/` exists |
| 3 | Script | write `script.json` (5 blocks: hook, context, teaching, bridge, closing; text + voice direction) | ~2.8 words/s: 190 words ≈ 66 s |
| 4 | Facts file | write `texts.json` (every on-screen fact + source + read date) | no fact without source |
| 5 | Voice | `sa.py voice <video>` | one request (free quota measured: 10/day) |
| 6 | Timings | `sa.py align <video>` | "not heard" ≤ 3; read each «heard as» |
| 7 | Images | write `images.json`; `sa.py image <video> <piece>` per piece (codex) or the person's files in `public/img/` | look at every image: no invented letters, no faces, no logos |
| 8 | Music | `sa.py music search mood/<mood>` → `download <id>` → `measure`; set `video.json` `music.file` | license line recorded in `music/licenses.json` |
| 9 | Scenes | `sa.py words <video>`, then write `scenes.json` (`references/scenes.md`) | `sa.py build <video>` passes |
| 10 | Sound | `sa.py mix <video>` | -14 LUFS, peak ≤ -1.5 dBTP |
| 11 | Covered zones | `sa.py zones <video>` | "lasting covered text: 0" |
| 12 | Render + quality | `sa.py render <video>` then LOOK at `out/sheet.jpg` | `approved: true` (0 black, 0 frozen, levels) + eye check |
| 13 | Publish texts | write `publish.json`, `sa.py page <video>` | `out/publish.html` opens; captions say AI |
| 14 | Publish | `references/publishing.md` per `config.publishing` | each network: link + AI label verified from outside |
| 15 | Close | add `published` links to `publish.json`, `sa.py page` again; final report | absolute paths of everything created |

`sa.py finish <video>` runs 9-13 in a row and stops at the first failure. Fix, then run it again.

## Writing scenes (summary; details in references/scenes.md)

- Anchor everything to spoken words: `"12:word"` (index from `sa.py words`; the word is checked).
- Something changes every 0.5-1.5 s: new beat, delayed line, element, or scene. A big number (1, 2, 3) covers the
  empty second at the start of each part.
- The first frame is a possible cover: the hook's first beat starts at `start` and is already readable on frame 0.
- Lines are laid out automatically inside the safe zone; if `build` says "too much text", split the beat.
- Hide subtitles while giant lines say the same words (`subtitles.hide`).

## Measured traps

- Whisper with `device: auto` on a PC with an NVIDIA card but no CUDA libraries fails with "cublas64_12.dll not
  found": the kit falls back to the CPU by itself (same result, measured 17 s for 67 s of voice).
- Windows can keep a rendered MP4 busy: Remotion leaves `<name>.remotion-in-progress`; the kit renames it.
- A line whose bottom edge crosses y 700 must be narrow (the app button column starts there): the layout handles it;
  `zones` proves it.
- Plain-color scenes get a moving glow; without it, still text on a flat color was flagged as frozen (0.6-0.8 s).
- Playwright only uploads files inside the folder Claude Code was started in: start Claude Code in STUDIO.
- Playwright cannot open a browser profile that is already open in another window: use a dedicated profile
  (`references/setup.md`) or the Claude in Chrome extension.
- Free Metricool: 20 published posts per month, one post on 4 networks counts as 4 (help page read 01/11/2026).

## Final report (always)

What was published where (links and times), what each check measured, what was NOT verified, cost (and which plan it
used), every click made in the browser, and the absolute path of every file created or changed. Separate what was
measured from what was estimated.
