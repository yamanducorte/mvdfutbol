# -*- coding: utf-8 -*-
"""Genera el sitio estatico de MVD Futbol en publico/.

Uso:  python scripts/sitio.py

Arma la portada, las notas y una pagina por campeonato juvenil (tabla, ultimos
resultados y fixture) a partir de contenido/notas/*.json y datos/juveniles.json.
Los anuncios salen de anuncios.json.
"""
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "contenido" / "notas"
JUVENILES = RAIZ / "datos" / "juveniles.json"
ANUNCIOS = RAIZ / "anuncios.json"
PUBLICO = RAIZ / "publico"

SITIO = "MVD Fútbol"
DOMINIO = "https://mvdfutbol.netlify.app"
LEMA = "Juveniles, primera y lo que se dice en la radio"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre"]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'"
           "%3E%3Crect width='32' height='32' rx='6' fill='%230f1419'/%3E%3Cpath d='M6 24V8h4l4 7"
           " 4-7h4v16h-4v-9l-4 7-4-7v9z' fill='%235ec3f0'/%3E%3Crect x='6' y='26' width='20'"
           " height='2' fill='%23f2a93b'/%3E%3C/svg%3E")

CSS = """
:root{
  --papel:#f6f5f1; --papel-2:#ecebe4; --tinta:#15181d; --tinta-2:#555d69;
  --linea:#d9d7cd; --celeste:#1b7fb8; --celeste-osc:#0f1419; --ambar:#c87a12;
  --borde-radio:3px;
  --titulo:'Archivo',system-ui,sans-serif;
  --lectura:'Source Serif 4',Georgia,serif;
  --dato:'IBM Plex Mono',ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--papel);color:var(--tinta);font-family:var(--lectura);line-height:1.6}
a{color:inherit}
.faja{background:var(--celeste-osc);color:#f6f7f8}
.ancho{max-width:1120px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header .ancho{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-block:14px;flex-wrap:wrap}
.marca{display:flex;align-items:center;gap:10px;text-decoration:none}
.marca .iso{width:30px;height:30px;border-radius:5px;background:#5ec3f0;color:#0f1419;font-family:var(--titulo);font-weight:800;font-size:.95rem;display:grid;place-items:center;letter-spacing:-.04em}
.marca b{font-family:var(--titulo);font-weight:800;font-size:1.22rem;letter-spacing:-.02em;line-height:1}
.marca span{display:block;font-family:var(--dato);font-size:.6rem;letter-spacing:.22em;text-transform:uppercase;color:#8fa0ae;margin-top:3px}
nav{display:flex;gap:18px;font-family:var(--titulo);font-size:.84rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
nav a{color:#c9d4dc;text-decoration:none;padding-bottom:2px;border-bottom:2px solid transparent}
nav a:hover,nav a[aria-current]{color:#fff;border-color:#f2a93b}
.fecha-faja{border-top:1px solid #222a33;font-family:var(--dato);font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:#7f8d99}
.fecha-faja .ancho{padding-block:7px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
main{padding-block:28px 48px}
.columnas{display:grid;grid-template-columns:minmax(0,2.1fr) minmax(0,1fr);gap:40px;align-items:start}
h1{font-family:var(--titulo);font-weight:800;letter-spacing:-.025em;line-height:1.08;font-size:clamp(1.7rem,4vw,2.5rem);text-wrap:balance}
h2{font-family:var(--titulo);font-weight:700;letter-spacing:-.015em;font-size:1.18rem;text-wrap:balance}
h3{font-family:var(--titulo);font-weight:700;font-size:1rem}
.rotulo{font-family:var(--dato);font-size:.67rem;font-weight:500;letter-spacing:.2em;text-transform:uppercase;color:var(--tinta-2);display:flex;align-items:center;gap:10px;margin-bottom:14px}
.rotulo::after{content:"";flex:1;height:1px;background:var(--linea)}
.notas{display:flex;flex-direction:column;gap:22px}
.nota-item{display:grid;gap:7px;padding-bottom:20px;border-bottom:1px solid var(--linea)}
.nota-item:last-child{border-bottom:0}
.nota-item a{text-decoration:none}
.nota-item h2 a:hover{color:var(--celeste)}
.nota-item p{color:var(--tinta-2);font-size:.97rem}
.meta{font-family:var(--dato);font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--tinta-2);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.pastilla{background:var(--papel-2);border:1px solid var(--linea);border-radius:999px;padding:2px 9px;font-family:var(--dato);font-size:.64rem;letter-spacing:.12em;text-transform:uppercase}
.vacio{border:1px dashed var(--linea);border-radius:var(--borde-radio);padding:22px;color:var(--tinta-2);font-size:.95rem}
aside{display:flex;flex-direction:column;gap:26px;min-width:0}
.bloque{border:1px solid var(--linea);background:#fff;border-radius:var(--borde-radio)}
.bloque>h3{padding:11px 14px;border-bottom:1px solid var(--linea);font-size:.82rem;text-transform:uppercase;letter-spacing:.09em}
.bloque .cuerpo{padding:12px 14px}
table{width:100%;border-collapse:collapse;font-family:var(--dato);font-size:.8rem;font-variant-numeric:tabular-nums}
th{text-align:right;font-weight:500;font-size:.63rem;letter-spacing:.1em;text-transform:uppercase;color:var(--tinta-2);padding:8px 5px;border-bottom:1px solid var(--linea)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td{padding:7px 5px;border-bottom:1px solid var(--papel-2)}
tbody tr:last-child td{border-bottom:0}
td.pos{color:var(--tinta-2);width:1.6rem}
td.eq{font-family:var(--lectura);font-size:.94rem}
td.pts{font-weight:600}
tr.lider td.pos{color:var(--celeste);font-weight:600}
.scroll-x{overflow-x:auto}
.partido{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--papel-2);font-size:.92rem}
.partido:last-child{border-bottom:0}
.partido .v{text-align:right}
.partido .marcador{font-family:var(--dato);font-weight:600;font-size:.88rem;background:var(--papel-2);border-radius:var(--borde-radio);padding:2px 8px;white-space:nowrap}
.partido .hora{font-family:var(--dato);font-size:.78rem;color:var(--tinta-2);white-space:nowrap}
.aviso{border:1px solid var(--linea);border-left:3px solid var(--ambar);background:#fff;border-radius:var(--borde-radio);padding:14px}
.aviso .et{font-family:var(--dato);font-size:.62rem;letter-spacing:.16em;text-transform:uppercase;color:var(--ambar)}
.aviso h3{margin:6px 0 5px;font-size:1rem}
.aviso p{font-size:.9rem;color:var(--tinta-2);margin-bottom:10px}
.aviso a{display:inline-block;font-family:var(--titulo);font-weight:700;font-size:.82rem;text-decoration:none;background:var(--celeste-osc);color:#fff;padding:8px 14px;border-radius:var(--borde-radio)}
.aviso a:hover{background:var(--celeste)}
.grilla-ligas{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.ficha{border:1px solid var(--linea);background:#fff;border-radius:var(--borde-radio);padding:13px 14px;text-decoration:none;display:grid;gap:5px}
.ficha:hover{border-color:var(--celeste)}
.ficha b{font-family:var(--titulo);font-size:.95rem}
.ficha small{font-family:var(--dato);font-size:.7rem;color:var(--tinta-2)}
article.cuerpo-nota{max-width:38rem}
article.cuerpo-nota .bajada{font-size:1.1rem;color:var(--tinta-2);margin:12px 0 20px}
article.cuerpo-nota p{margin-bottom:1.05em;font-size:1.05rem}
.fuente{border-top:1px solid var(--linea);margin-top:26px;padding-top:14px;font-size:.9rem;color:var(--tinta-2)}
.fuente a{color:var(--celeste)}
footer{border-top:1px solid var(--linea);margin-top:40px;background:var(--papel-2)}
footer .ancho{padding-block:24px;display:flex;gap:18px;justify-content:space-between;flex-wrap:wrap;font-size:.84rem;color:var(--tinta-2)}
footer a{color:var(--celeste)}
@media (max-width:820px){ .columnas{grid-template-columns:1fr;gap:34px} }
@media (prefers-color-scheme:dark){
  :root{--papel:#121519;--papel-2:#1b2027;--tinta:#e9ecef;--tinta-2:#9aa5b1;--linea:#2a313a;--celeste:#5ec3f0;--ambar:#f2a93b}
  .bloque,.aviso,.ficha{background:#171c22}
  .marca .iso{background:#5ec3f0}
}
"""


def esc(valor):
    return html.escape(str(valor), quote=True)


def slug(texto):
    limpio = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", limpio.lower())).strip("-")[:70]


def leer_json(ruta, por_defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def fecha_larga(iso):
    try:
        f = datetime.fromisoformat(iso[:19])
    except (ValueError, TypeError):
        return ""
    return str(f.day) + " de " + MESES[f.month - 1] + " de " + str(f.year)


def fecha_corta(iso):
    try:
        f = datetime.fromisoformat(iso[:19])
    except (ValueError, TypeError):
        return ""
    return str(f.day).rjust(2, "0") + "/" + str(f.month).rjust(2, "0")


def hora(iso):
    try:
        return datetime.fromisoformat(iso[:19]).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def con_utm(url, origen):
    if not url:
        return ""
    union = "&" if "?" in url else "?"
    return url + union + "utm_source=mvdfutbol&utm_medium=anuncio&utm_campaign=" + origen


def pagina(titulo, descripcion, contenido, ruta_canonica, seccion=""):
    hoy = datetime.now(timezone.utc)
    nav = []
    for texto_nav, destino in (("Últimas", "/"), ("Juveniles", "/juveniles/")):
        actual = ' aria-current="page"' if seccion == destino else ""
        nav.append('<a href="' + destino + '"' + actual + ">" + texto_nav + "</a>")
    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>""" + esc(titulo) + """</title>
<meta name="description" content=\"""" + esc(descripcion) + """\">
<link rel="canonical" href=\"""" + DOMINIO + esc(ruta_canonica) + """\">
<meta property="og:title" content=\"""" + esc(titulo) + """\">
<meta property="og:description" content=\"""" + esc(descripcion) + """\">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_UY">
<link rel="icon" href=\"""" + FAVICON + """\">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>""" + CSS + """</style>
</head>
<body>
<header class="faja">
  <div class="ancho">
    <a class="marca" href="/">
      <span class="iso" aria-hidden="true">M</span>
      <span><b>MVD Fútbol</b><span>""" + esc(LEMA) + """</span></span>
    </a>
    <nav>""" + "".join(nav) + """</nav>
  </div>
  <div class="fecha-faja"><div class="ancho"><span>Montevideo · """ + fecha_larga(hoy.isoformat()) + """</span><span>Actualizado """ + hora(hoy.isoformat()) + """ UTC</span></div></div>
</header>
<main class="ancho">
""" + contenido + """
</main>
<footer>
  <div class="ancho">
    <span>© """ + str(hoy.year) + """ MVD Fútbol · Montevideo, Uruguay</span>
    <span>Resultados y posiciones de juveniles con datos de <a href="https://lamovidaonline.net" rel="noopener">La Movida Online</a></span>
  </div>
</footer>
</body>
</html>
"""


def html_anuncio(anuncio):
    url = con_utm(anuncio["url"], anuncio["id"])
    return ('<div class="aviso"><div class="et">' + esc(anuncio["etiqueta"]) + "</div><h3>" +
            esc(anuncio["titulo"]) + "</h3><p>" + esc(anuncio["texto"]) + '</p><a href="' +
            esc(url) + '" rel="noopener sponsored">' + esc(anuncio["cta"]) + " →</a></div>")


def html_tabla(tabla, limite=None):
    filas = tabla[:limite] if limite else tabla
    if not filas:
        return '<div class="vacio">Todavía no se jugaron partidos en este campeonato.</div>'
    cuerpo = []
    for puesto, fila in enumerate(filas, 1):
        clase = ' class="lider"' if puesto == 1 else ""
        cuerpo.append("<tr" + clase + '><td class="pos">' + str(puesto) + '</td><td class="eq">' +
                      esc(fila["equipo"]) + "</td><td>" + str(fila["pj"]) + "</td><td>" +
                      str(fila["g"]) + "</td><td>" + str(fila["e"]) + "</td><td>" + str(fila["p"]) +
                      "</td><td>" + str(fila["gf"]) + ":" + str(fila["gc"]) + "</td><td>" +
                      ("+" if fila["dg"] > 0 else "") + str(fila["dg"]) + '</td><td class="pts">' +
                      str(fila["pts"]) + "</td></tr>")
    return ('<div class="scroll-x"><table><thead><tr><th></th><th>Equipo</th><th>PJ</th><th>G</th>'
            "<th>E</th><th>P</th><th>Goles</th><th>DG</th><th>Pts</th></tr></thead><tbody>" +
            "".join(cuerpo) + "</tbody></table></div>")


def html_partidos(partidos, jugados):
    if not partidos:
        return '<div class="vacio">Sin partidos para mostrar.</div>'
    filas = []
    for partido in partidos:
        if jugados:
            centro = ('<span class="marcador">' + str(partido["goles_local"]) + " - " +
                      str(partido["goles_visita"]) + "</span>")
        else:
            centro = '<span class="hora">' + fecha_corta(partido["fecha"]) + " " + hora(partido["fecha"]) + "</span>"
        filas.append('<div class="partido"><span>' + esc(partido["local"]) + "</span>" + centro +
                     '<span class="v">' + esc(partido["visita"]) + "</span></div>")
    return "".join(filas)


def html_nota_item(nota):
    fuente = nota.get("fuente", {})
    return ('<article class="nota-item"><div class="meta"><span class="pastilla">' +
            esc(nota.get("categoria", "futbol")) + "</span><span>" + fecha_larga(nota.get("fecha", "")) +
            "</span><span>vía " + esc(fuente.get("nombre", "")) + "</span></div><h2><a href=\"/nota/" +
            esc(nota["slug"]) + '/">' + esc(nota.get("titulo", "")) + "</a></h2><p>" +
            esc(nota.get("bajada", "")) + "</p></article>")


def main():
    notas = sorted((leer_json(p, None) for p in NOTAS.glob("*.json")),
                   key=lambda n: (n or {}).get("publicado_utc", ""), reverse=True)
    notas = [n for n in notas if n and n.get("slug")]
    juveniles = leer_json(JUVENILES, {"ligas": [], "credito": ""})
    anuncios = [a for a in leer_json(ANUNCIOS, {}).get("anuncios", []) if a.get("activo") and a.get("url")]
    ligas = [l for l in juveniles.get("ligas", []) if l.get("tabla")]
    PUBLICO.mkdir(parents=True, exist_ok=True)

    def escribir(ruta_relativa, texto):
        destino = PUBLICO / ruta_relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")

    # ---------- portada ----------
    if notas:
        columna = '<div class="rotulo">Lo último</div><div class="notas">' + \
                  "".join(html_nota_item(n) for n in notas[:12]) + "</div>"
    else:
        columna = ('<div class="rotulo">Lo último</div><div class="vacio">Todavía no hay notas '
                   "publicadas. El vigilante ya está escuchando los programas; la primera nota "
                   "aparece acá en cuanto alguien diga algo que valga.</div>")

    destacadas = []
    for liga in ligas[:4 if notas else 10]:
        puntero = liga["tabla"][0]
        destacadas.append('<a class="ficha" href="/juveniles/' + slug(liga["nombre"]) + '/"><b>' +
                          esc(liga["nombre"]) + "</b><small>Lidera " + esc(puntero["equipo"]) +
                          " · " + str(puntero["pts"]) + " pts · " + str(puntero["pj"]) +
                          " jugados</small></a>")
    columna += ('<div style="margin-top:34px"><div class="rotulo">Juveniles · posiciones</div>'
                '<div class="grilla-ligas">' + "".join(destacadas) + "</div></div>" if destacadas else "")

    lateral = []
    proximos = [p for liga in ligas for p in liga.get("proximos_partidos", [])]
    proximos.sort(key=lambda p: p["fecha"])
    if proximos:
        lateral.append('<div class="bloque"><h3>Próximos partidos</h3><div class="cuerpo">' +
                       html_partidos(proximos[:7], False) + "</div></div>")
    recientes = [p for liga in ligas for p in liga.get("ultimos_resultados", [])]
    recientes.sort(key=lambda p: p["fecha"], reverse=True)
    if recientes:
        lateral.append('<div class="bloque"><h3>Últimos resultados</h3><div class="cuerpo">' +
                       html_partidos(recientes[:7], True) + "</div></div>")
    for anuncio in anuncios:
        lateral.append(html_anuncio(anuncio))

    escribir("index.html", pagina(
        SITIO + " — juveniles, primera y lo que se dice en la radio",
        "Resultados, posiciones y fixture de las juveniles del fútbol uruguayo, y lo que dicen los "
        "protagonistas en los programas deportivos, con la cita y el minuto.",
        '<div class="columnas"><div>' + columna + "</div><aside>" + "".join(lateral) + "</aside></div>",
        "/", "/"))

    # ---------- notas ----------
    for nota in notas:
        fuente = nota.get("fuente", {})
        parrafos = "".join("<p>" + esc(p) + "</p>" for p in nota.get("cuerpo", []))
        pie = ('<div class="fuente">Lo dijo en <strong>' + esc(fuente.get("programa", "")) +
               "</strong>, de " + esc(fuente.get("nombre", "")) + '. <a href="' +
               esc(fuente.get("video", "")) + '" rel="noopener">Ver el video</a>')
        hechos = [h for h in nota.get("hechos", []) if h.get("minuto")]
        if hechos:
            pie += " (minuto " + esc(hechos[0]["minuto"]) + ")"
        pie += ".</div>"
        cuerpo = ('<div class="columnas"><article class="cuerpo-nota"><div class="meta">'
                  '<span class="pastilla">' + esc(nota.get("categoria", "futbol")) + "</span><span>" +
                  fecha_larga(nota.get("fecha", "")) + "</span></div><h1>" + esc(nota.get("titulo", "")) +
                  '</h1><p class="bajada">' + esc(nota.get("bajada", "")) + "</p>" + parrafos + pie +
                  "</article><aside>" + "".join(html_anuncio(a) for a in anuncios) + "</aside></div>")
        escribir("nota/" + nota["slug"] + "/index.html", pagina(
            nota.get("titulo", SITIO), nota.get("bajada", ""), cuerpo,
            "/nota/" + nota["slug"] + "/"))

    # ---------- juveniles ----------
    fichas = []
    for liga in ligas:
        puntero = liga["tabla"][0]
        fichas.append('<a class="ficha" href="/juveniles/' + slug(liga["nombre"]) + '/"><b>' +
                      esc(liga["nombre"]) + "</b><small>" + str(len(liga["tabla"])) + " equipos · lidera " +
                      esc(puntero["equipo"]) + "</small></a>")
    indice = ('<h1>Juveniles del fútbol uruguayo</h1><p class="bajada" style="color:var(--tinta-2);'
              'margin:10px 0 24px;max-width:38rem">Tablas de posiciones, resultados y fixture de '
              'cada categoría, de Sub 11 a Sub 19. Las posiciones se calculan partido por partido '
              'y se actualizan solas.</p><div class="grilla-ligas">' + "".join(fichas) + "</div>")
    if juveniles.get("credito"):
        indice += '<p class="fuente">' + esc(juveniles["credito"]) + "</p>"
    escribir("juveniles/index.html", pagina(
        "Juveniles del fútbol uruguayo: tablas y resultados · " + SITIO,
        "Posiciones, resultados y fixture de las juveniles del fútbol uruguayo por categoría: "
        "Sub 11, Sub 13, Sub 14, Sub 15, Sub 16, Sub 17 y Sub 19.",
        indice, "/juveniles/", "/juveniles/"))

    for liga in ligas:
        ruta = "/juveniles/" + slug(liga["nombre"]) + "/"
        lateral_liga = ['<div class="bloque"><h3>Últimos resultados</h3><div class="cuerpo">' +
                        html_partidos(liga.get("ultimos_resultados", [])[:8], True) + "</div></div>"]
        if liga.get("proximos_partidos"):
            lateral_liga.append('<div class="bloque"><h3>Próxima fecha</h3><div class="cuerpo">' +
                                html_partidos(liga["proximos_partidos"][:8], False) + "</div></div>")
        lateral_liga += [html_anuncio(a) for a in anuncios]
        puntero = liga["tabla"][0]
        cuerpo = ('<div class="columnas"><div><div class="meta" style="margin-bottom:10px">'
                  '<span class="pastilla">Juveniles</span><span>' + str(len(liga["tabla"])) +
                  " equipos</span></div><h1>" + esc(liga["nombre"]) + "</h1>"
                  '<p class="bajada" style="color:var(--tinta-2);margin:10px 0 22px">Lidera ' +
                  esc(puntero["equipo"]) + " con " + str(puntero["pts"]) + " puntos en " +
                  str(puntero["pj"]) + " partidos.</p>" + html_tabla(liga["tabla"]) +
                  '<p class="fuente">' + esc(juveniles.get("credito", "")) + "</p></div><aside>" +
                  "".join(lateral_liga) + "</aside></div>")
        escribir(ruta.strip("/") + "/index.html", pagina(
            liga["nombre"] + ": tabla de posiciones y resultados · " + SITIO,
            "Tabla de posiciones, últimos resultados y próxima fecha de " + liga["nombre"] + ".",
            cuerpo, ruta, "/juveniles/"))

    # ---------- archivos de servicio ----------
    urls = ["/", "/juveniles/"] + ["/juveniles/" + slug(l["nombre"]) + "/" for l in ligas] + \
           ["/nota/" + n["slug"] + "/" for n in notas]
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    escribir("sitemap.xml",
             '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
             "".join("<url><loc>" + DOMINIO + u + "</loc><lastmod>" + hoy + "</lastmod></url>\n" for u in urls) +
             "</urlset>\n")
    escribir("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: " + DOMINIO + "/sitemap.xml\n")
    escribir("llms.txt",
             "# " + SITIO + "\n\n" + LEMA + ". Medio digital uruguayo.\n\n"
             "## Qué hay acá\n"
             "- Tablas de posiciones, resultados y fixture de las juveniles del fútbol uruguayo "
             "(Sub 11 a Sub 19), calculadas partido por partido. Datos: La Movida Online.\n"
             "- Notas sobre lo que dicen los protagonistas del fútbol en los programas deportivos "
             "de radio y YouTube, siempre con la fuente, el programa y el minuto del video.\n\n"
             "## Campeonatos con tabla publicada\n" +
             "".join("- " + l["nombre"] + ": " + DOMINIO + "/juveniles/" + slug(l["nombre"]) + "/\n" for l in ligas))
    escribir("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")

    print("sitio generado en " + str(PUBLICO.relative_to(RAIZ)) + ": " + str(len(notas)) +
          " nota(s), " + str(len(ligas)) + " campeonato(s), " + str(len(anuncios)) + " anuncio(s) activo(s)")
    if not anuncios:
        print("  (ojo: no hay ningun anuncio activo con link en anuncios.json)")


if __name__ == "__main__":
    main()
