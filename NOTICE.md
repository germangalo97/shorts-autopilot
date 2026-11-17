# Third-party software and services

This repository's own code is MIT-licensed (see LICENSE). It relies on software and services with their own terms,
which you accept when you install or use them:

- **Remotion** (video engine, installed by `npm install`): free for individuals, non-profits and companies with up to
  3 employees; larger companies need a Remotion Company License. Read https://www.remotion.dev/docs/license
  (checked 17/11/2026). This repository does not include Remotion's code.
- **Google Fonts** used by the engine (Anton, Inter Tight, Space Grotesk, Instrument Serif, JetBrains Mono): SIL Open
  Font License.
- **Gemini API** (voice): Google's terms and quotas apply to your own key.
- **Codex CLI / ChatGPT** (optional images): OpenAI's terms and your plan's limits apply.
- **Mixkit** (optional music): the Mixkit license shown on each track page applies; read it before publishing.
- **faster-whisper** (word timings, MIT) and its models.
- The **sound effects** are synthesized by `kit/sfx.py` and are covered by this repository's MIT license.

Publishing through a website with a browser tool can break a platform's terms; see
`plugins/shorts-autopilot/skills/shorts-autopilot/references/web-publishing.md`.
