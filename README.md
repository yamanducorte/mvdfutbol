# mvdfutbol

Medio digital de futbol uruguayo. Se actualiza solo.

## Que hace

- `scripts/monitor.py` — escucha los canales de YouTube de `fuentes.json` y baja el transcripto de cada video nuevo (yt-dlp, sin API key).
- `scripts/redactor.py` — dos etapas: un modelo barato (Haiku 5.5) lee el transcripto entero y decide si hay noticia; un modelo bueno (Opus 5.5) escribe la nota solo con los hechos extraidos, citando programa, fuente y minuto.
- `scripts/datos.py` — trae los partidos de juveniles de la API publica de La Movida Online y **calcula** las tablas de posiciones. No cuesta nada.
- `scripts/sitio.py` — genera el sitio estatico en `publico/`.

## Como corre 24/7

GitHub Actions: `datos.yml` cada 20 minutos (gratis), `noticias.yml` cada hora (usa el secret ANTHROPIC_API_KEY). Netlify publica `publico/` en cada commit.

## Reglas de contenido

1. No se reescriben notas de otros medios. Se informa lo que alguien **dijo** en un programa, con cita corta, link al video y minuto.
2. Rumor y confirmacion se escriben distinto.
3. Los resultados de juveniles llevan credito visible a La Movida Online.
