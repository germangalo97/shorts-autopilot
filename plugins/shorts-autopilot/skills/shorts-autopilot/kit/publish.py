"""Builds out/publish.html: one card per network with the video path, the text ready to copy, where the AI label is,
and, once published, the link. Reads publish.json («youtube», «tiktok», «instagram», «x» and «published»)."""
from __future__ import annotations

import html
from pathlib import Path

from common import Video, load_config, read_json

UI = {
    "en": {"published": "PUBLISHED", "file": "File", "title": "Title", "text": "Text", "copy": "Copy", "copied": "Copied",
           "label": "AI label", "sources": "Sources of what the video says", "done": "published on", "missing": "missing",
           "nothing": "nothing", "aiNote": "Images and/or voice are AI-made: the AI label is mandatory on every network.",
           "record": "Below is what was uploaded, kept as a record.", "link": "Copy link"},
    "es": {"published": "YA PUBLICADO", "file": "Archivo", "title": "Título", "text": "Texto", "copy": "Copiar", "copied": "Copiado",
           "label": "Etiqueta de IA", "sources": "Fuentes de lo que dice el video", "done": "publicado en", "missing": "falta",
           "nothing": "nada", "aiNote": "Las imágenes y/o la voz son de IA: la etiqueta de IA es obligatoria en cada red.",
           "record": "Lo de abajo queda como registro de lo que se subió.", "link": "Copiar link"},
}
NETWORKS = (
    ("youtube", "YouTube Shorts", {"en": "YouTube Studio, step «Details» → «Altered or synthetic content» → <b>Yes</b>. Also «Not made for kids».",
                                   "es": "YouTube Studio, paso «Detalles» → «Contenido alterado o sintético» → <b>Sí</b>. Además «No es para niños»."}),
    ("tiktok", "TikTok", {"en": "TikTok Studio (web) → «Show more» → «AI-generated content» → <b>on</b>.",
                          "es": "TikTok Studio (web) → «Mostrar más» → «Contenido generado por IA» → <b>Activar</b>."}),
    ("instagram", "Instagram Reels", {"en": "instagram.com, «New reel» step → «Add AI label» → <b>on</b>. Note: «Share to Facebook» may be on by default.",
                                      "es": "instagram.com, paso «Nuevo reel» → «Añadir etiqueta de IA» → <b>activada</b>. Ojo: «Compartir en Facebook» puede venir encendido."}),
    ("x", "X", {"en": "X has no verified switch for this: the AI disclosure goes inside the text (already there).",
                "es": "X no tiene un interruptor verificado: la declaración de IA va dentro del texto (ya está)."}),
)
STYLE = """:root{--bg:#f7f7f4;--panel:#fff;--ink:#16181d;--muted:#5b6170;--line:#e3e4df;--accent:#d7ff3e;--ok:#1d7a3e;--ok-bg:#e3f6e9}
@media (prefers-color-scheme: dark){:root{--bg:#111317;--panel:#1a1d23;--ink:#eceef2;--muted:#a3a9b6;--line:#2c3038;--ok:#7be0a0;--ok-bg:#12301f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
main{max-width:900px;margin:0 auto;padding:24px 16px 80px}h1{font-size:1.6rem;margin:.2em 0}h2{font-size:1.2rem;margin:1.8em 0 .5em}
.sub{color:var(--muted)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin:12px 0}
.copy{white-space:pre-wrap;background:var(--bg);border:1px dashed var(--line);border-radius:10px;padding:10px;word-break:break-word}
button{font:inherit;font-weight:700;border:0;border-radius:10px;padding:6px 14px;background:var(--accent);color:#111;cursor:pointer;margin:6px 0 10px}
.ok{background:var(--ok-bg);color:var(--ok);border-radius:10px;padding:10px 14px}"""
SCRIPT = """document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){var t=document.getElementById(b.getAttribute('data-copy')).textContent;try{navigator.clipboard.writeText(t).then(function(){b.textContent=b.getAttribute('data-ok');});}catch(e){}});});"""


def _copy(ident: str, text: str, label: str, ok: str) -> str:
    return f'<div class="copy" id="{ident}">{html.escape(text)}</div>\n<button data-copy="{ident}" data-ok="{ok}">{label}</button>'


def build_page(video: Video, video_file: Path) -> Path:
    cfg = load_config(video.studio)
    t = UI.get(cfg.get("uiLanguage", "en"), UI["en"])
    lang = cfg.get("uiLanguage", "en") if cfg.get("uiLanguage") in UI else "en"
    pub = read_json(video.folder / "publish.json")
    texts = read_json(video.folder / "texts.json", required=False)
    done = pub.get("published") or {}
    body = [f"<h1>{html.escape(video.spec.get('title', video.slug))}</h1>",
            f'<p class="sub">{t["done"]}: {", ".join(n for c, n, _ in NETWORKS if c in done) or t["nothing"]} · {t["missing"]}: '
            f'{", ".join(n for c, n, _ in NETWORKS if c not in done and pub.get(c)) or t["nothing"]}</p>', f"<p>{t['aiNote']}</p>"]
    for key, name, help_text in NETWORKS:
        texts_net = pub.get(key)
        if not texts_net:
            continue
        rec = done.get(key) or {}
        body.append(f"<h2>{name}{' · ' + t['published'] if rec else ''}</h2><div class=\"panel\">")
        if rec:
            body.append(f'<div class="ok">{html.escape(rec.get("when", ""))} {html.escape(rec.get("note", ""))}</div>')
            body.append(_copy(f"{key}-link", rec.get("link", ""), t["link"], t["copied"]))
            body.append(f'<p class="sub">{t["record"]}</p>')
        body.append(f"<b>{t['file']}</b>" + _copy(f"{key}-file", str(video_file), t["copy"], t["copied"]))
        if texts_net.get("title"):
            body.append(f"<b>{t['title']}</b>" + _copy(f"{key}-title", texts_net["title"], t["copy"], t["copied"]))
        text = texts_net.get("description") or texts_net.get("text") or ""
        if text:
            body.append(f"<b>{t['text']}</b>" + _copy(f"{key}-text", text, t["copy"], t["copied"]))
        body.append(f"<p><b>{t['label']}:</b> {help_text[lang]}</p></div>")
    sources = sorted({v["source"] for k, v in texts.items() if not k.startswith("_") and isinstance(v, dict) and v.get("source")})
    if sources:
        body.append(f"<h2>{t['sources']}</h2><div class=\"panel\"><ul>" + "".join(f"<li>{html.escape(s)}</li>" for s in sources) + "</ul></div>")
    page = (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{html.escape(video.slug)}</title>\n<style>\n{STYLE}\n</style>\n</head>\n<body>\n<main>\n" + "\n".join(body)
            + f"\n</main>\n<script>\n{SCRIPT}\n</script>\n</body>\n</html>\n")
    out = video.out / "publish.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
