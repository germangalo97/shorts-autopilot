# scenes.json reference

`sa.py build` turns this file into the engine's props. Everything is checked: word anchors, images, texts, colors.

## Word references

`"12:word"` = the moment word 12 starts (the word is checked against the voice). Also `"12"`, `"12:word+0.3"`,
`"12:word-0.2"` (seconds), `"start"`, `"end"`. Get the list with `sa.py words <video>` (`index:word@second`).

## Top level

```json
{
  "hits": ["5:apaga", "12:ia"],
  "subtitles": {"hide": [["start", "19:el"]], "keywords": {"ia": "accent"}, "enabled": true},
  "music": {"cuts": [["26:corta", "30:todo"]], "stop": "139:y", "resume": "151:el"},
  "sound": {"extra": [{"at": "12:ia", "effect": "riser_short", "db": -16, "align": "peak"}]},
  "look": {"grain": 0.05, "shake": 16, "drift": 10},
  "scenes": []
}
```

- `hits`: shake + flash + impact sound on these words.
- `subtitles.hide`: stretches without subtitles (when giant lines already say the words). `keywords`: words with color.
- `music.cuts`: the music drops out between two words. `stop`/`resume`: tape-stop and come back.
- Colors: `accent`, `accent2`, `danger`, `ok`, `text`, `muted`, `bg`, `panel` (from config.style) or `#RRGGBB`.

## A scene

```json
{
  "from": "14:fui",
  "background": {"image": "aviso.png", "zoom": [1.1, 1.3], "panY": [0, -70], "dim": 0.7, "position": "50% 65%", "ai": true},
  "kicker": {"text": "PROOF 1 OF 3", "color": "accent", "textColor": "bg"},
  "beats": [
    {"lines": ["I WENT TO FIND", {"text": "THE EVIDENCE", "at": "18:evidence", "color": "accent", "size": 165}]},
    {"at": "21:word", "top": 820, "lines": ["..."]}
  ],
  "elements": []
}
```

- The first scene starts at `"start"`; each scene ends where the next one begins.
- No `background.image` → a plain color with a slow moving glow. `"ai": false` for the person's own photos.
- A beat shows its lines until the next beat. A line without `at` appears with the beat; with `at`, it pops in later.
- Lines stack from y 400 (or the beat's `top`), are shrunk to fit, and narrowed when they reach the app button column.
  Default size 160; giant numbers 300-420.
- Strings starting with `$t:` come from texts.json (facts must).

## Elements (`at` / `until` default to the scene's start / end)

| type | fields | sound |
|---|---|---|
| `checklist` | `items: [{text, ok, at}]`, `x, y, size, gap` | click per row |
| `screen` | `text` (types itself on an old green screen), `x, y, width, height` | typing |
| `timer` | `text` ("≈ 1 MINUTE"), `fillBy`, `x, y, radius` | tick/tock |
| `search` | `title, query, typeAt, result, resultAt, x, y, width, height` | typing + low beep |
| `calendar` | `month, day, x, y` | text hit |
| `arrow` | `x, y` (bounces down, toward the description) | high pop |
| `static` | `opacity` (TV static) | CRT hum |
| `blackout` | `duration` frames (lights go out left to right) | boom |
| `source` | `text, y` (small label, e.g. "SOURCE: agency.gov") | swish |

Effects available for `sound.extra`: whoosh_short, whoosh_long, whoosh_low, swish, impact, boom, riser, riser_short,
reverse, pop, pop_high, click, tick, tock, typing, notification, glitch, glitch_short, shutter, text_hit, sparkle,
crt_hum, beep, beep_low, tape_stop.

## Safe zone (what the apps cover, 1080×1920)

Top 0-230, bottom 1440-1920, right column x > 920 between y 700 and 1750. Values from third-party guides
(07/11/2026); no official document exists. `sa.py zones` checks every 5th frame.
