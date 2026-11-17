"""Prepares a YouTube Shorts upload through YouTube Studio with the Playwright browser tool (the person's logged-in
browser profile, with their OK for this upload).

Writes <studio>/upload/yt_step1.js, yt_step2.js, yt_step3.js and copies the final video to <studio>/upload/video.mp4
(Playwright only reads files inside the folder Claude Code was started in: start Claude Code in the studio).
Delete that copy after the upload.

Steps (references/publishing.md):
  1) navigate to https://www.youtube.com/upload (opens the Studio upload dialog) and check the channel name.
  2) browser_run_code_unsafe with yt_step1.js: file, title, description, not for kids, no paid promotion,
     altered or synthetic content YES (AI images/voice).
  3) yt_step2.js: Next until visibility, chooses the visibility in config («publishing.youtubeVisibility»).
     Wait until the dialog says the checks are complete before step 3.
  4) yt_step3.js: presses the final button and returns what the dialog shows (the link).
Selectors use element names and ids, not button texts, so they do not depend on the interface language. Measured on
the Spanish interface on 16/11/2026; other languages not tested.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from common import KitError, Video, load_config, read_json

TITLE_MAX = 100
DESCRIPTION_MAX = 5000
FORBIDDEN = ("<", ">")

STEP1 = r"""async (page) => {
  const P = __P__;
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  const wait = (ms) => page.waitForTimeout(ms);
  const log = [];
  const d = page.locator('ytcp-uploads-dialog');
  const open = await page.evaluate(() => { const x = document.querySelector('ytcp-uploads-dialog'); return !!(x && x.offsetParent); });
  if (!open) {
    await page.locator('#create-icon').first().click();
    await page.locator('#text-item-0').first().click();
    await wait(1500);
  }
  await d.locator('input[type=file]').first().setInputFiles(P.file);
  await d.locator('#textbox').first().waitFor({ state: 'visible', timeout: 90000 });
  await wait(2500);
  log.push('file loaded');
  const put = async (n, text) => {
    await page.evaluate((k) => { const el = document.querySelectorAll('ytcp-uploads-dialog #textbox')[k]; if (!el) throw new Error('no text box ' + k); el.focus(); }, n);
    await wait(300);
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Delete');
    await page.keyboard.insertText(text);
    await wait(700);
    return await page.evaluate((k) => document.querySelectorAll('ytcp-uploads-dialog #textbox')[k].innerText, n);
  };
  const t = await put(0, P.title);
  if (norm(t) !== norm(P.title)) throw new Error('title ended up as: ' + t);
  const desc = await put(1, P.description);
  if (norm(desc) !== norm(P.description)) throw new Error('description ended up different: ' + desc);
  log.push('title and description');
  const mark = async (name) => {
    await page.evaluate((n) => { const r = document.querySelector('ytcp-uploads-dialog tp-yt-paper-radio-button[name="' + n + '"]'); if (!r) throw new Error('no option ' + n); r.click(); }, name);
    await wait(600);
  };
  await mark('VIDEO_MADE_FOR_KIDS_NOT_MFK');
  await mark('VIDEO_PAID_PRODUCT_PLACEMENT_NO');
  await mark(P.altered ? 'VIDEO_HAS_ALTERED_CONTENT_YES' : 'VIDEO_HAS_ALTERED_CONTENT_NO');
  const checked = await page.evaluate(() => [...document.querySelector('ytcp-uploads-dialog').querySelectorAll('tp-yt-paper-radio-button')]
    .filter(r => /MADE_FOR_KIDS|PAID_PRODUCT|ALTERED/.test(r.getAttribute('name')) && r.getAttribute('aria-checked') === 'true')
    .map(r => r.getAttribute('name').replace('VIDEO_', '')));
  const expected = ['MADE_FOR_KIDS_NOT_MFK', 'PAID_PRODUCT_PLACEMENT_NO', P.altered ? 'HAS_ALTERED_CONTENT_YES' : 'HAS_ALTERED_CONTENT_NO'];
  if (expected.some(e => !checked.includes(e))) throw new Error('checked options: ' + checked.join(', '));
  log.push('options: ' + checked.join(', '));
  return JSON.stringify({ log });
}
"""

STEP2 = r"""async (page) => {
  const VIS = __VIS__;
  const wait = (ms) => page.waitForTimeout(ms);
  const visible = () => page.evaluate((v) => { const r = document.querySelector('ytcp-uploads-dialog tp-yt-paper-radio-button[name="' + v + '"]'); return !!(r && r.offsetParent); }, VIS);
  for (let k = 0; k < 8 && !(await visible()); k++) {
    for (let j = 0; j < 60; j++) {
      const ok = await page.evaluate(() => { const b = document.querySelector('ytcp-uploads-dialog #next-button'); if (b && b.getAttribute('aria-disabled') !== 'true' && b.offsetParent) { b.click(); return true; } return false; });
      if (ok) break;
      await wait(500);
    }
    await wait(1500);
  }
  if (!(await visible())) throw new Error('did not reach the visibility step');
  await page.evaluate((v) => document.querySelector('ytcp-uploads-dialog tp-yt-paper-radio-button[name="' + v + '"]').click(), VIS);
  await wait(900);
  return await page.evaluate(() => {
    const dlg = document.querySelector('ytcp-uploads-dialog');
    const checked = [...dlg.querySelectorAll('tp-yt-paper-radio-button')].filter((r) => r.getAttribute('aria-checked') === 'true').map((r) => r.getAttribute('name'));
    return JSON.stringify({ checked, dialog: dlg.innerText.slice(0, 1200).replace(/\n+/g, ' | ') });
  });
}
"""

STEP3 = r"""async (page) => {
  const before = await page.evaluate(() => { const b = document.querySelector('ytcp-uploads-dialog #done-button'); return b ? { text: b.innerText.trim(), disabled: b.getAttribute('aria-disabled') } : null; });
  if (!before || before.disabled === 'true') throw new Error('the final button is not ready: ' + JSON.stringify(before));
  await page.evaluate(() => document.querySelector('ytcp-uploads-dialog #done-button').click());
  await page.waitForTimeout(4000);
  const shown = await page.evaluate(() => [...document.querySelectorAll('ytcp-uploads-dialog, ytcp-dialog, tp-yt-paper-dialog, ytcp-video-share-dialog')]
    .filter((e) => e.offsetParent).map((e) => e.innerText.trim().replace(/\n+/g, ' | ').slice(0, 500)));
  const links = await page.evaluate(() => [...document.querySelectorAll('a')].map((a) => a.href).filter((h) => /youtu\.be\/|youtube\.com\/shorts\//.test(h)));
  return JSON.stringify({ before, shown, links: [...new Set(links)] });
}
"""


def prepare(video: Video, final: Path) -> Path:
    cfg = load_config(video.studio)
    yt = read_json(video.folder / "publish.json").get("youtube") or {}
    title, description = yt.get("title", ""), yt.get("description", "")
    if not title or len(title) > TITLE_MAX:
        raise KitError(f"the YouTube title has {len(title)} characters (1 to {TITLE_MAX})")
    if len(description) > DESCRIPTION_MAX:
        raise KitError(f"the description has {len(description)} characters (max {DESCRIPTION_MAX})")
    bad = [c for c in FORBIDDEN if c in title + description]
    if bad:
        raise KitError(f"YouTube does not accept {bad} in title or description")
    if not final.is_file():
        raise KitError(f"no final video at {final}: render it first")
    upload = video.studio / "upload"
    upload.mkdir(exist_ok=True)
    copy = upload / "video.mp4"
    shutil.copyfile(final, copy)
    visibility = cfg["publishing"].get("youtubeVisibility", "PUBLIC")
    if visibility not in ("PUBLIC", "UNLISTED", "PRIVATE"):
        raise KitError("publishing.youtubeVisibility must be PUBLIC, UNLISTED or PRIVATE")
    data = {"file": copy.as_posix(), "title": title, "description": description,
            "altered": bool(read_json(video.folder / "publish.json").get("aiLabel", True))}
    (upload / "yt_step1.js").write_text(STEP1.replace("__P__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    (upload / "yt_step2.js").write_text(STEP2.replace("__VIS__", json.dumps(visibility)), encoding="utf-8")
    (upload / "yt_step3.js").write_text(STEP3, encoding="utf-8")
    return upload
