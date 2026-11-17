# shorts-autopilot

**Videos verticales sin cara, hechos de punta a punta por Claude Code.** Le decís "buscá un tema en tendencia,
hacé el video y publicalo"; Claude investiga, verifica cada dato en la fuente original, escribe el guion, genera la
voz, arma subtítulos animados atados a cada palabra dicha, mezcla música y efectos, controla el resultado con números
y lo publica (o te deja todo listo para que lo publiques vos).

[Read in English](README.md)

## Qué obtenés

- Un video vertical de 60 a 110 s (1080×1920, 30 cuadros por segundo, -14 LUFS de volumen) para YouTube Shorts,
  TikTok, Instagram Reels y X.
- Cada dato que aparece en pantalla sale de `texts.json`, con su fuente y la fecha en que se leyó. Sin fuente, no va.
- La declaración de IA viene incluida: rótulo "hecho con IA", etiqueta en cada imagen de IA y el interruptor de IA
  encendido en cada red.
- Controles automáticos: palabras que la voz se salteó, textos donde las apps tapan la pantalla, volumen, cuadros
  negros o congelados, y una hoja con un cuadro cada medio segundo que Claude mira antes de publicar.
- Una configuración inicial guiada: Claude revisa tu computadora, instala lo que falta (preguntando antes) y te
  pregunta por tu cuenta, idioma, estilo y cómo querés publicar.

## Requisitos y costos

| Pieza | Costo | Notas |
|---|---|---|
| Claude Code | plan pago de Claude | el agente que hace todo |
| Python 3.10+, Node.js 18+, ffmpeg | gratis | Claude los instala con tu OK |
| Voz: texto a voz de Gemini | plan gratis | tu propia clave de Google AI Studio; cupo medido: 10 pedidos por día |
| Imágenes: Codex | dentro de un plan de ChatGPT | o tus propias imágenes, o ninguna (estilo solo tipografía) |
| Música: Mixkit | gratis | la licencia queda anotada por tema |
| Motor de video: Remotion | gratis para personas y empresas de hasta 3 personas | licencia para empresas más grandes |
| Publicación | gratis | YouTube por el navegador, Metricool gratis (20 publicaciones por mes) o a mano |

Probado en Windows 11 con Python 3.11 y Node 24 (16 y 17/11/2026). Los comandos de macOS y Linux están documentados
pero todavía no se probaron.

## Instalación

Dentro de Claude Code:

```
/plugin marketplace add germangalo97/shorts-autopilot
/plugin install shorts-autopilot@shorts-autopilot
```

O copiá `plugins/shorts-autopilot/skills/shorts-autopilot` dentro de `~/.claude/skills/`.

Después decí: **"configurá shorts-autopilot"** (o "haceme un video sin cara"). La primera vez, Claude hace la
configuración guiada.

## Cómo funciona

```
tema + datos → script.json → voz (Gemini) → tiempo de cada palabra (Whisper) → imágenes → scenes.json
  → build (revisa cada ancla, dato e imagen) → mezcla (-14 LUFS) → control de zonas tapadas → render
  → control de calidad + hoja de cuadros → publish.html / subida → links anotados
```

Claude escribe `scenes.json` (escenas atadas a palabras dichas, por ejemplo `"12:palabra"`); el kit acomoda cada
renglón dentro de la zona segura, arma el diseño de sonido a partir de las escenas y el motor de Remotion dibuja los
cuadros.

## Publicación y reglas de las plataformas

YouTube Studio con un perfil de navegador en el que entrás vos, el plan gratis de Metricool, o subida a mano con una
página de textos listos para copiar. Instagram y TikTok manejando sus páginas web vienen **apagados**: sus reglas
prohíben la interacción automatizada, así que solo se activan si aceptás ese riesgo de forma explícita.

## Límites, con honestidad

- Claude no puede escuchar: el audio se controla midiendo (volumen, palabras oídas), no de oído.
- Los datos valen lo que valen las fuentes: la skill obliga a tener fuente, no puede mejorar una fuente mala.
- Las páginas de las redes cambian; los pasos del navegador pueden necesitar ajustes. Avisalo en un issue.

## Licencia

MIT para el código de este repositorio. El software y los servicios de terceros tienen sus propias condiciones: ver
[NOTICE.md](NOTICE.md).
