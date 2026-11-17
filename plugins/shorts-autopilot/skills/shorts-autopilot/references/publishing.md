# Publishing

Before any browser work: the person's OK for this publication, the right account (read the account name on the page
and say it), the AI label on, and the caption from publish.json. After: open the public page from outside and confirm
the label, then record link + time in `publish.json` → `published` and run `sa.py page` again.

## YouTube Shorts (browser, Playwright)

1. `sa.py youtube <video>` → writes `STUDIO/upload/yt_step1.js`, `yt_step2.js`, `yt_step3.js` and copies the video.
2. Navigate to `https://www.youtube.com/upload` (opens the YouTube Studio upload dialog). Read the channel name.
3. `browser_run_code_unsafe` with the file `STUDIO/upload/yt_step1.js` → title, description, not for kids, no paid
   promotion, altered or synthetic content YES.
4. `yt_step2.js` → moves to visibility and picks `publishing.youtubeVisibility`. Read the dialog text it returns and
   wait until YouTube says the checks finished (copyright and restrictions) before step 3.
5. `yt_step3.js` → final button; returns the link. Check from outside:
   `https://www.youtube.com/oembed?url=<link>&format=json` answers 200 for public/unlisted videos.
6. Delete `STUDIO/upload/video.mp4`.

The original flow was measured on the Spanish interface on 16/11/2026. This version selects elements by name and id,
not by button text; that change and other interface languages have not been tested yet. If a step fails, take a
snapshot and continue with guided clicks, never by guessing.

## Metricool (free plan; schedules Instagram, TikTok, Facebook, YouTube)

- Read the notice "You have published X of your 20 posts" first: one post on 4 networks counts as 4.
- Create post → pick networks → video → upload → per-network text → Instagram as Reel, YouTube as Short (needs a title)
  → AI-generated content switch ON in each network's settings → date/time → schedule.
- Verify the list shows each network as pending. If there is no quota, say so and fall back to `manual`.

## Manual

`out/publish.html` has the file path, each text with a copy button, and where each network's AI label is. The person
uploads; they send the links back and Claude records them.

## X

The AI disclosure goes inside the post text (no verified switch). Check which account is logged in before posting;
never post to an account the person did not name.

## Instagram and TikTok through their websites

Off by default. Only with `publishing.webAutomationRiskAccepted: true` and the person's request: `web-publishing.md`.
