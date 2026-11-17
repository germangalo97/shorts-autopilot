# First-time setup interview

Goal: a person who may be using Claude Code for the first time ends with a working studio and one test video, without
needing to know what Python, npm or a browser profile are. Talk in their language, one decision at a time, using the
question tool with short options and a recommended default. Explain each technical word where it appears.

## 1. Check the machine

Run `python SKILL/kit/sa.py doctor` (if Python is missing, the command fails: start with the table below).

| Needed | Why (plain words) | Windows | macOS | Linux (Debian/Ubuntu) |
|---|---|---|---|---|
| Python 3.10+ | runs the kit | `winget install Python.Python.3.12` | `brew install python` | `sudo apt install python3 python3-venv` |
| Node.js 18+ | runs the video engine | `winget install OpenJS.NodeJS.LTS` | `brew install node` | `sudo apt install nodejs npm` |
| ffmpeg | cuts, mixes and measures audio/video | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| Codex CLI (optional) | makes the images with a ChatGPT plan | `npm install -g @openai/codex` then `codex login` | same | same |

Before installing anything: say what it is, that it is free, and ask. After installing, a new terminal may be needed
for PATH changes; run `doctor` again.

## 2. Create the studio

Ask where to keep it (default: a folder named `shorts-studio` in their Documents). Then:

```
mkdir <STUDIO>
python -m venv <STUDIO>/.venv
<py> -m pip install -r SKILL/kit/requirements.txt
<py> SKILL/kit/sa.py init <STUDIO>
```
(`<py>` = `<STUDIO>/.venv/Scripts/python.exe` on Windows, `<STUDIO>/.venv/bin/python` elsewhere.)
`init` copies the engine, runs `npm install` (≈250 packages, 1-3 min) and synthesizes the 25 sound effects.
Tell them to start Claude Code from STUDIO from now on (Playwright can only upload files inside that folder).

## 3. Interview → config.json

Ask, in this order, and write the answers into `STUDIO/config.json`:

1. **Languages:** the language they want to talk to you in (`uiLanguage`) and the language of the videos (`videoLanguage`,
   ISO code: `es`, `en`, `pt`...). Latin-alphabet languages are what was tested.
2. **Account:** name, handles per network, the closing line (default: "follow for the next one"). Ask if they want
   selling in videos (default no).
3. **Niche and audience:** what the account is about, who watches. Topics to never touch (`rules.neverMention`).
4. **Who picks topics:** ask every time (default) or automatic (`topics.chooseTopic`).
5. **Look:** keep the default palette (lime / yellow / red on near-black) or their brand colors (`style`). Labels in
   their video language (`labels.badge`, `labels.aiImage`), e.g. "HECHO CON IA" / "IMAGEN GENERADA CON IA".
6. **Voice:** Gemini text-to-speech on the free tier. They create a key at Google AI Studio (aistudio.google.com,
   «Get API key») and paste it into `STUDIO/.env` after `GEMINI_API_KEY=` themselves. Never ask them to paste it in
   the chat. Default voice `Aoede` (female, warm); other voices are listed in Google's docs. `doctor` shows whether
   the key is set without showing it.
7. **Images:** `codex` (needs a ChatGPT plan with Codex; images count against that plan's limits), `folder` (they bring
   images; mark own photos with `"ai": false` in the scene so they are not labeled AI) or `none` (typography only).
   Do not suggest paid image APIs unless they ask; if they do, give the price from the provider's page read today.
8. **Publishing**, per network: `browser` (Claude uploads with their logged-in browser), `metricool` (free plan,
   20 posts/month total), or `manual` (Claude prepares `publish.html` and they upload). See `publishing.md`.
   - Browser tool: **Playwright MCP with a dedicated profile** (recommended, any browser):
     `claude mcp add playwright -- npx @playwright/mcp@latest --browser chrome --user-data-dir <STUDIO>/browser-profile`
     (use `msedge` for Edge). Restart Claude Code; open the profile once with a navigation and let THEM log in to each
     network by hand. **Claude in Chrome extension** works in their everyday Chrome or Edge.
   - Instagram/TikTok through their websites: off by default. Explain the risk with the quotes in
     `web-publishing.md` and only set `webAutomationRiskAccepted: true` if they say yes in their own words.
   - YouTube visibility: PUBLIC, UNLISTED (good for the first test) or PRIVATE.
9. **Costs, said out loud:** Claude Code needs a paid Claude plan; Codex images need a ChatGPT plan; Gemini voice and
   Mixkit music are free (limits apply); Remotion is free for individuals and companies of up to 3 people (company
   license above that, read on remotion.dev on 17/11/2026).

## 4. Test video

Offer a short first video (UNLISTED on YouTube) so they see the whole loop once. Report what each check measured.
