# Troubleshooting (all measured)

| Symptom | Cause | Fix |
|---|---|---|
| `cublas64_12.dll is not found` during align | NVIDIA card without CUDA libraries | automatic CPU fallback (`whisper.device: auto`); or set `"cpu"` |
| `word 12 is «x», not «y»` in build | the take or the script changed | run `sa.py words` again and update the anchors |
| `too much text in one beat` | lines would not fit | split the beat in two |
| `lasting covered text` in zones | text under app buttons/caption | shorter line, smaller size, or a lower `top`; see build/zones.json frames |
| frozen stretches in quality | still frame for 0.6 s or more | add a beat, a delayed line or an element in that stretch |
| a text clipped inside a piece | text longer than its box | shorter text; the search result and lines already fit themselves |
| `.remotion-in-progress` file | Windows kept the MP4 busy | handled by the kit (renamed) |
| Google answers HTTP 429 on voice | free quota used (10/day measured for 3.8 Flash TTS) | wait for the next day or ask before paying |
| Playwright says the browser is already in use | the profile is open in another window | close that window, or use the extension |
| Playwright cannot upload the file | file outside the folder Claude Code started in | start Claude Code in the studio |
| PermissionError deleting a file (Windows) | a file still open | the kit closes images before deleting; report if it appears elsewhere |
