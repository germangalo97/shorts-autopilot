# Instagram and TikTok through their websites (opt-in, at the person's risk)

**Why it is off by default.** TikTok's Terms of Service say you may not "use automated scripts to collect information
from or otherwise interact with the Services" (read 17/11/2026). Instagram's Terms of Use forbid accessing or
collecting information by automated means without explicit permission (read 17/11/2026). Driving the website with a
browser tool can therefore put the account at risk. Tell the person this in plain words; only proceed if they accept
in their own words, and record it in config. Prefer Metricool or manual upload.

Measured recipe (16/11/2026, Spanish interface, Claude in Chrome extension on the person's own browser):

## Uploading a file bigger than the tool's limit

The Claude in Chrome file upload accepted about 10.4 MB per call. For bigger files:
1. `sa.py split <final.mp4>` → 8 MB parts + the SHA-256 of the original.
2. In the page, create hidden `<input type=file>` elements with the page script tool, upload one part per call.
3. Join them: `new File([p0, p1, p2], 'video.mp4', {type: 'video/mp4'})`; compute the SHA-256 in the page
   (`crypto.subtle.digest`) and compare with the original; return only `equal: true/false`.
4. Put it into the real input with `DataTransfer` and dispatch `input` and `change` with `bubbles: true`.
5. Delete the parts folder afterwards.

## Instagram (instagram.com)

1. Create → Post → load the file in the dialog's input.
2. Crop: the bottom-left button → **Original** (otherwise it is cut square).
3. Next (cover = first frame) → Next.
4. Caption: a `paste` event (ClipboardEvent with DataTransfer) into `[role=dialog] div[contenteditable=true]`.
   Close hashtag suggestions by clicking the dialog title, never Escape.
5. Turn on **Add AI label**.
6. **Share to Facebook** may come ON by default: tell the person; it posted to their personal profile in the test.
7. Share → wait for "your reel has been shared". Verify the reel page shows the AI label.

## TikTok (tiktok.com/tiktokstudio/upload)

1. Same file trick into `input[accept="video/*"]`.
2. Description (a Draft.js editor prefilled with the file name): real click inside, real ctrl+a and Backspace, then ONE
   `paste` with the whole text. Never the `type` action (it dropped letters) and never `execCommand('insertText')`
   followed by Enter (it crashed the page; discard with a forced navigation and start over).
3. Check the character counter and the paragraphs.
4. Show more → **AI-generated content** → turn on → confirm.
5. Wait until the checks say no problems were found → Post.
6. It shows "under review / only me" for a few minutes, then "everyone". Verify the public page says the creator
   labeled it as AI-generated.
