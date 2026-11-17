# Topic, research and script

## Find a trending topic (free)

- YouTube search ordered by views, this month, under 4 minutes: add `&sp=CAMSBAgEGAE%3D` to
  `https://www.youtube.com/results?search_query=<terms>`; read titles, channels and view counts with `yt-dlp`
  (`yt-dlp --flat-playlist --dump-json "<url>"`, install with pip). Record the numbers with the date measured.
- A topic that expires in 1-3 days (a rumor about a date, an event) and can be checked in an official source is ideal.
- Skip: health or legal advice, tragedies, minors, accusations against real people, anything you cannot verify.

## Verify (before writing a single line)

- Open the primary source (the official notice, the original paper, the company's page). WebFetch can read pages
  that block curl. Note the exact sentence and the URL.
- Date every fact by when you read it. Separate: what the source says, what a third party measured, what you measured.
- Do a second search for anything newer than what you found. If sources disagree, say so or drop the claim.

## Script rules (script.json)

- 5 blocks: `hook`, `context`, `teaching`, `bridge`, `closing`. Each with `text` and `style` (voice direction);
  `voiceStyle` describes the overall voice.
- Hook = the question people search, with the date or concrete detail. The promise in the second sentence
  ("I went looking for the evidence").
- About 2.8 words per second: 190 words ≈ 66 s. Short sentences.
- Numbers as digits in the script ("17"): Whisper writes them that way. Times in words in the voice, digits on screen
  (from texts.json).
- An honest twist works: "this video was also made by an AI, so check the source in the description".
- Closing: invite to follow (or the person's own closing from config). Never pressure, never sell unless config says so.

## Image requests (images.json)

- English prompts. One piece per background. Always add: "no text, no letters, no numbers, no logos, no real people,
  no recognizable landmarks". Describe where the subject sits (lower half), because big text goes on top.
- Look at every image before using it; regenerate (next attempt number) if it has invented letters or faces.
