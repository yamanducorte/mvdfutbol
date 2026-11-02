# -*- coding: utf-8 -*-
"""Genera el sitio estatico de MVD Futbol en publico/.

Uso:  python scripts/sitio.py

Diseno: diario deportivo (titular grande, notas secundarias en columnas, franja
de resultados, columna derecha con tabla y anuncios) en celeste uruguayo.
Arma portada, notas, indice de juveniles y una pagina por campeonato a partir de
contenido/notas/*.json, datos/juveniles.json y anuncios.json.
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
# Clave de IndexNow: avisa a Bing, Yandex y DuckDuckGo apenas se publica algo.
# Google no usa IndexNow; para Google valen el sitemap de noticias y el RSS.
INDEXNOW = "7f3c1a9d4b5e4c82a1d6e0f93b2c7a58"
# Archivo de verificacion de Google Search Console. No borrarlo: si desaparece,
# Google quita la verificacion y se pierde el acceso a los datos.
VERIFICACION_GOOGLE = "google7352264a901f3c24.html"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre"]

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'"
           "%3E%3Crect width='32' height='32' fill='%23ffffff'/%3E%3Crect y='23' width='32'"
           " height='9' fill='%231173b8'/%3E%3Cpath d='M4 20V5h4l4 7 4-7h4v15h-4v-8l-4 7-4-7v8z'"
           " fill='%2312161c'/%3E%3C/svg%3E")

CSS = """
:root{
  --celeste:#1173b8;        /* celeste uruguayo, bajado para que lea bien sobre blanco */
  --celeste-vivo:#56b4e9;   /* el de la bandera, para fondos oscuros */
  --tinta:#12161c; --gris:#666e78; --linea:#dcdcd7; --papel:#fff; --crema:#f3f2ec;
  --titular:'Archivo',system-ui,sans-serif;
  --lectura:'Source Serif 4',Georgia,serif;
  --dato:'IBM Plex Mono',ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--papel);color:var(--tinta);font-family:var(--lectura);line-height:1.6}
a{color:inherit}
img{max-width:100%}
.ancho{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}

/* cabecera */
header{border-bottom:3px solid var(--tinta)}
.cab{display:flex;align-items:baseline;justify-content:space-between;gap:14px;padding-block:13px;flex-wrap:wrap}
.logo{font-family:var(--titular);font-weight:900;font-size:clamp(1.6rem,4.5vw,2.1rem);letter-spacing:-.045em;text-transform:uppercase;text-decoration:none;line-height:1}
.logo i{font-style:normal;color:var(--celeste)}
.cab small{font-family:var(--dato);font-size:.66rem;letter-spacing:.13em;text-transform:uppercase;color:var(--gris)}
.menu{background:var(--tinta)}
.menu .ancho{display:flex;gap:19px;overflow-x:auto;padding-block:10px}
.menu a{color:#cfd6dd;font-family:var(--titular);font-weight:700;font-size:.79rem;text-transform:uppercase;letter-spacing:.05em;text-decoration:none;white-space:nowrap}
.menu a:hover{color:#fff}
.menu a[aria-current]{color:var(--celeste-vivo)}

/* estructura */
.grilla{display:grid;grid-template-columns:minmax(0,2.4fr) minmax(0,1fr);gap:32px;padding-block:24px 40px}
.grilla>div{min-width:0}
aside{display:flex;flex-direction:column;gap:22px;min-width:0}

/* apertura */
.apertura{border-bottom:1px solid var(--linea);padding-bottom:20px;margin-bottom:20px}
.sello{display:inline-block;background:var(--celeste);color:#fff;font-family:var(--dato);font-size:.63rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;padding:3px 9px;margin-bottom:10px}
.sello.dato{background:var(--tinta)}
.apertura h1,h1.titulo{font-family:var(--titular);font-weight:900;font-size:clamp(1.85rem,4.3vw,3rem);line-height:1.03;letter-spacing:-.035em;text-wrap:balance}
.apertura h1 a{text-decoration:none}
.apertura h1 a:hover{color:var(--celeste)}
.apertura p{color:var(--gris);font-size:1.07rem;margin-top:11px;max-width:40rem}

/* notas secundarias */
.secundarias{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));gap:20px}
.secundarias article{border-top:2px solid var(--tinta);padding-top:10px}
.secundarias h3{font-family:var(--titular);font-weight:700;font-size:1.02rem;line-height:1.19;letter-spacing:-.015em}
.secundarias h3 a{text-decoration:none}
.secundarias h3 a:hover{color:var(--celeste)}
.secundarias small,.firma{display:block;font-family:var(--dato);font-size:.63rem;letter-spacing:.1em;text-transform:uppercase;color:var(--celeste);margin-bottom:4px}
.secundarias p{color:var(--gris);font-size:.93rem;margin-top:5px}

/* franja de resultados */
.franja{background:var(--crema);border-top:1px solid var(--linea);border-bottom:1px solid var(--linea);margin-top:26px;padding-block:18px}
h2.rotulo,aside h2{font-family:var(--titular);font-weight:800;font-size:.82rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:13px}
.marcadores{display:grid;grid-template-columns:repeat(auto-fill,minmax(212px,1fr));gap:10px}
.mk{background:#fff;border:1px solid var(--linea);padding:9px 11px;font-size:.9rem;min-width:0}
.mk div{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.mk span:first-child{min-width:0;overflow-wrap:anywhere}
.mk .r{font-family:var(--dato);font-weight:600;color:var(--celeste);white-space:nowrap}
.mk .h{font-family:var(--dato);font-size:.74rem;color:var(--gris);white-space:nowrap}

/* tablas */
.scroll-x{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-family:var(--dato);font-size:.79rem;font-variant-numeric:tabular-nums}
th{font-size:.6rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--gris);text-align:right;padding:7px 4px;border-bottom:2px solid var(--tinta)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td{padding:7px 4px;border-bottom:1px solid var(--linea)}
tbody tr:last-child td{border-bottom:0}
td.pos{color:var(--gris);width:1.5rem}
td.eq{font-family:var(--lectura);font-size:.93rem}
.escudo{vertical-align:-4px;margin-right:7px;flex:0 0 auto}
.partido .v .escudo{margin:0 0 0 7px}
.mk .escudo{margin-right:6px;vertical-align:-3px}
.partido>span{display:flex;align-items:center;gap:0}
.partido .v{justify-content:flex-end}
td.pts{font-weight:600}
tr.lider td.pos,tr.lider td.pts{color:var(--celeste)}

/* listas de partidos */
.partido{display:grid;grid-template-columns:1fr auto 1fr;gap:9px;align-items:center;padding:8px 0;border-bottom:1px solid var(--linea);font-size:.91rem}
.partido:last-child{border-bottom:0}
.partido>span{min-width:0;overflow-wrap:anywhere}
.partido .v{text-align:right}
.partido .marcador{font-family:var(--dato);font-weight:600;color:var(--celeste);white-space:nowrap}
.partido .hora{font-family:var(--dato);font-size:.76rem;color:var(--gris);white-space:nowrap}

/* fichas de campeonato */
.grilla-ligas{display:grid;grid-template-columns:repeat(auto-fill,minmax(236px,1fr));gap:14px}
.ficha{border:1px solid var(--linea);border-top:3px solid var(--celeste);padding:13px 14px;text-decoration:none;display:grid;gap:5px;background:#fff}
.ficha:hover{border-color:var(--celeste)}
.ficha b{font-family:var(--titular);font-size:.97rem;line-height:1.2}
.ficha small{font-family:var(--dato);font-size:.69rem;color:var(--gris)}

/* anuncios */
.aviso{border:1px solid var(--linea);border-top:3px solid var(--celeste);padding:14px}
.aviso .et{font-family:var(--dato);font-size:.61rem;letter-spacing:.15em;text-transform:uppercase;color:var(--celeste)}
.aviso h3{font-family:var(--titular);font-size:1.02rem;margin:6px 0 5px}
.aviso p{font-size:.89rem;color:var(--gris);margin-bottom:11px}
.aviso a{display:inline-block;font-family:var(--titular);font-weight:700;font-size:.81rem;text-decoration:none;background:var(--tinta);color:#fff;padding:8px 14px}
.aviso a:hover{background:var(--celeste)}

/* nota */
article.nota{max-width:38rem}
article.nota .bajada{font-size:1.13rem;color:var(--gris);margin:13px 0 22px}
article.nota p{margin-bottom:1.05em;font-size:1.06rem}
.video{position:relative;aspect-ratio:16/9;margin:4px 0 22px;background:var(--crema);border:1px solid var(--linea)}
.video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.video .pie{position:absolute;bottom:0;left:0;right:0;background:rgba(18,22,28,.85);color:#fff;font-family:var(--dato);font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;padding:5px 9px}
.tapa-foto{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;margin-bottom:13px;background:var(--crema)}
.nota-foto{float:right;width:132px;aspect-ratio:16/9;object-fit:cover;margin:3px 0 8px 14px;background:var(--crema)}
@media (max-width:520px){.nota-foto{width:104px;margin-left:10px}}
.fuente{border-top:1px solid var(--linea);margin-top:26px;padding-top:14px;font-size:.9rem;color:var(--gris)}
.fuente a{color:var(--celeste)}
.vacio{border:1px dashed var(--linea);padding:20px;color:var(--gris);font-size:.95rem}
.intro{color:var(--gris);font-size:1.05rem;margin:11px 0 24px;max-width:40rem}

footer{border-top:3px solid var(--tinta);margin-top:36px;background:var(--crema)}
footer .ancho{padding-block:22px;display:flex;gap:18px;justify-content:space-between;flex-wrap:wrap;font-size:.85rem;color:var(--gris)}
footer a{color:var(--celeste)}
@media (max-width:860px){ .grilla{grid-template-columns:1fr;gap:30px} }
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


def dia_mes(iso):
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
    return url + ("&" if "?" in url else "?") + "utm_source=mvdfutbol&utm_medium=anuncio&utm_campaign=" + origen


ESCUDOS = {}


def cargar_escudos():
    global ESCUDOS
    ESCUDOS = leer_json(RAIZ / "escudos.json", {}).get("colores", {})


def iniciales(nombre):
    palabras = [p for p in re.split(r"[\s.]+", nombre) if p and p[0].isalpha()]
    if len(palabras) == 1:
        return palabras[0][:3].upper()
    return "".join(p[0] for p in palabras[:3]).upper()


def escudo(nombre, tam=18):
    """Monograma propio con los colores del club. No es el escudo oficial."""
    datos = ESCUDOS.get(nombre)
    if datos:
        fondo, detalle = datos[0], datos[1]
        letras = datos[2] if len(datos) > 2 else iniciales(nombre)
    else:
        # sin color cargado: tono estable derivado del nombre, para que no cambie
        tono = sum(ord(c) for c in nombre) % 360
        fondo, detalle, letras = "hsl(" + str(tono) + ",42%,38%)", "#ffffff", iniciales(nombre)
    claro = detalle.lower() in ("#ffffff", "#fff")
    texto = detalle if claro else "#ffffff"
    return ('<svg class="escudo" viewBox="0 0 24 24" width="' + str(tam) + '" height="' + str(tam) +
            '" role="img" aria-label="' + esc(nombre) + '"><path d="M12 1.5 21 4v8.4c0 4.7-3.5 8.3-9 10.1'
            '-5.5-1.8-9-5.4-9-10.1V4z" fill="' + esc(fondo) + '"/><path d="M12 1.5 21 4v3H3V4z" fill="' +
            esc(detalle) + '" opacity=".92"/><text x="12" y="16.5" text-anchor="middle" font-family="Archivo,'
            'sans-serif" font-size="8.5" font-weight="800" fill="' + esc(texto) + '">' +
            esc(letras[:3]) + "</text></svg>")


def id_video(url):
    hallado = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url or "")
    return hallado.group(1) if hallado else ""


def miniatura(url):
    ident = id_video(url)
    return "https://i.ytimg.com/vi/" + ident + "/hqdefault.jpg" if ident else ""


def video_fuente(fuente):
    """Reproductor de YouTube: es el mecanismo oficial para citar el audio."""
    ident = id_video(fuente.get("video", ""))
    if not ident:
        return ""
    return ('<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/' + esc(ident) +
            '" title="' + esc(fuente.get("programa", "")[:90]) + '" loading="lazy" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe><span class="pie">Fuente: ' +
            esc(fuente.get("nombre", "")) + "</span></div>")


def pie_fuente(liga, por_defecto):
    """Cada tabla cita de donde salio: La Movida, Wikipedia, lo que sea."""
    texto = liga.get("credito") or por_defecto
    if not texto:
        return ""
    enlace = liga.get("credito_url")
    if enlace:
        return '<p class="fuente"><a href="' + esc(enlace) + '" rel="noopener">' + esc(texto) + "</a></p>"
    return '<p class="fuente">' + esc(texto) + "</p>"


def ruta_liga(liga):
    """Cada campeonato vive bajo su seccion: /juveniles/, /ascenso/, /femenino/."""
    return "/" + liga.get("grupo", "juveniles") + "/" + slug(liga["nombre"]) + "/"


TITULOS_GRUPO = {"primera": "Primera División", "juveniles": "Juveniles",
                 "ascenso": "Segunda, Tercera y D", "femenino": "Fútbol femenino"}
INTRO_GRUPO = {
    "primera": "Tabla anual, Torneo Clausura y Torneo Apertura del Campeonato Uruguayo.",
    "juveniles": "Tablas, resultados y fixture de cada categoría, de Sub 11 a Sub 19.",
    "ascenso": "Segunda División Profesional, Tercera División y Divisional D: posiciones y resultados fecha a fecha.",
    "femenino": "Primera y Segunda del fútbol femenino uruguayo: tablas, resultados y próxima fecha.",
}


def categorias_menu(ligas):
    """Atajos a las categorias que hoy tienen campeonato en curso."""
    atajos = []
    for clave in ("primera", "juveniles", "ascenso", "femenino"):
        if any(l.get("grupo", "juveniles") == clave for l in ligas):
            atajos.append((TITULOS_GRUPO[clave].split(",")[0], "/" + clave + "/"))
    for numero in ("19", "17", "15"):
        for liga in ligas:
            if re.search(r"sub\s?-?" + numero + r"\b|s" + numero + r"\b", liga["nombre"], re.I):
                atajos.append(("Sub " + numero, ruta_liga(liga)))
                break
    return atajos


def pagina(titulo, descripcion, contenido, ruta, ligas, seccion="", esquema=None, publicado=""):
    ahora = datetime.now(timezone.utc)
    enlaces = [("Portada", "/")] + categorias_menu(ligas)
    menu = "".join('<a href="' + destino + '"' + (' aria-current="page"' if seccion == destino else "") +
                   ">" + texto + "</a>" for texto, destino in enlaces)
    extra = ('<meta property="article:published_time" content="' + esc(publicado) + '">' if publicado else "")
    if esquema:
        extra += '<script type="application/ld+json">' + json.dumps(esquema, ensure_ascii=False) + "</script>"
    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>""" + esc(titulo) + """</title>
<meta name="description" content=\"""" + esc(descripcion) + """\">
<link rel="canonical" href=\"""" + DOMINIO + esc(ruta) + """\">
<meta property="og:title" content=\"""" + esc(titulo) + """\">
<meta property="og:description" content=\"""" + esc(descripcion) + """\">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_UY">
<meta property="og:site_name" content=\"""" + SITIO + """\">
<meta name="theme-color" content="#12161c">
""" + extra + """
<link rel="alternate" type="application/rss+xml" title=\"""" + SITIO + """\" href="/rss.xml">
<link rel="icon" href=\"""" + FAVICON + """\">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800;900&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>""" + CSS + """</style>
</head>
<body>
<header>
  <div class="ancho cab">
    <a class="logo" href="/">MVD<i>Fútbol</i></a>
    <small>Montevideo · """ + fecha_larga(ahora.isoformat()) + " · actualizado " + hora(ahora.isoformat()) + """ UTC</small>
  </div>
</header>
<div class="menu"><div class="ancho">""" + menu + """</div></div>
<div class="ancho">
""" + contenido + """
</div>
<footer>
  <div class="ancho">
    <span>© """ + str(ahora.year) + " " + SITIO + """ · Montevideo, Uruguay</span>
    <span>Posiciones y resultados de juveniles con datos de <a href="https://lamovidaonline.net" rel="noopener">La Movida Online</a></span>
  </div>
</footer>
</body>
</html>
"""


def html_anuncio(anuncio):
    return ('<div class="aviso"><div class="et">' + esc(anuncio["etiqueta"]) + "</div><h3>" +
            esc(anuncio["titulo"]) + "</h3><p>" + esc(anuncio["texto"]) + '</p><a href="' +
            esc(con_utm(anuncio["url"], anuncio["id"])) + '" rel="noopener sponsored">' +
            esc(anuncio["cta"]) + " →</a></div>")


def html_tabla(tabla, limite=None, completa=True):
    filas = tabla[:limite] if limite else tabla
    if not filas:
        return '<div class="vacio">Todavía no se jugaron partidos en este campeonato.</div>'
    cuerpo = []
    for puesto, fila in enumerate(filas, 1):
        clase = ' class="lider"' if puesto == 1 else ""
        celdas = ['<td class="pos">' + str(puesto) + "</td>",
                  '<td class="eq">' + escudo(fila["equipo"]) + "<span>" + esc(fila["equipo"]) + "</span></td>",
                  "<td>" + str(fila["pj"]) + "</td>"]
        if completa:
            celdas += ["<td>" + str(fila["g"]) + "</td>", "<td>" + str(fila["e"]) + "</td>",
                       "<td>" + str(fila["p"]) + "</td>",
                       "<td>" + str(fila["gf"]) + ":" + str(fila["gc"]) + "</td>"]
        celdas += ["<td>" + ("+" if fila["dg"] > 0 else "") + str(fila["dg"]) + "</td>",
                   '<td class="pts">' + str(fila["pts"]) + "</td>"]
        cuerpo.append("<tr" + clase + ">" + "".join(celdas) + "</tr>")
    encabezados = ["", "Equipo", "PJ"] + (["G", "E", "P", "Goles"] if completa else []) + ["DG", "Pts"]
    return ('<div class="scroll-x"><table><thead><tr>' +
            "".join("<th>" + e + "</th>" for e in encabezados) + "</tr></thead><tbody>" +
            "".join(cuerpo) + "</tbody></table></div>")


def html_marcadores(partidos):
    return "".join('<div class="mk"><div><span>' + escudo(p["local"], 16) + esc(p["local"]) +
                   '</span><span class="r">' + str(p["goles_local"]) + "-" + str(p["goles_visita"]) +
                   "</span></div><div><span>" + escudo(p["visita"], 16) + esc(p["visita"]) +
                   '</span><span class="h">' + dia_mes(p["fecha"]) + "</span></div></div>"
                   for p in partidos)


def html_partidos(partidos, jugados):
    if not partidos:
        return '<div class="vacio">Sin partidos para mostrar.</div>'
    filas = []
    for p in partidos:
        centro = ('<span class="marcador">' + str(p["goles_local"]) + " - " + str(p["goles_visita"]) + "</span>"
                  if jugados else '<span class="hora">' + dia_mes(p["fecha"]) + " " + hora(p["fecha"]) + "</span>")
        filas.append('<div class="partido"><span>' + escudo(p["local"], 16) + "<span>" +
                     esc(p["local"]) + "</span></span>" + centro + '<span class="v"><span>' +
                     esc(p["visita"]) + "</span>" + escudo(p["visita"], 16) + "</span></div>")
    return "".join(filas)


def main():
    cargar_escudos()
    notas = sorted((leer_json(p, None) for p in NOTAS.glob("*.json")),
                   key=lambda n: (n or {}).get("publicado_utc", ""), reverse=True)
    notas = [n for n in notas if n and n.get("slug")]
    juveniles = leer_json(JUVENILES, {"ligas": [], "credito": ""})
    primera = leer_json(RAIZ / "datos" / "primera.json", {"ligas": []})
    ligas = [l for l in (primera.get("ligas", []) + juveniles.get("ligas", [])) if l.get("tabla")]
    credito = juveniles.get("credito", "")
    anuncios = [a for a in leer_json(ANUNCIOS, {}).get("anuncios", []) if a.get("activo") and a.get("url")]
    PUBLICO.mkdir(parents=True, exist_ok=True)

    def escribir(ruta_relativa, texto):
        destino = PUBLICO / ruta_relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")

    resultados = sorted((p for l in ligas for p in l.get("ultimos_resultados", [])),
                        key=lambda p: p["fecha"], reverse=True)
    proximos = sorted((p for l in ligas for p in l.get("proximos_partidos", [])), key=lambda p: p["fecha"])
    # Primero los campeonatos del ano en curso: una tabla de 2025 no va en la portada.
    anio = str(datetime.now(timezone.utc).year)
    ligas.sort(key=lambda l: (l.get("grupo") != "primera", anio not in l["nombre"], l["nombre"]))
    vigentes = [l for l in ligas
                if anio in l["nombre"] or l.get("grupo") == "primera"] or ligas
    destacada = max(vigentes, key=lambda l: sum(f["pj"] for f in l["tabla"])) if vigentes else None

    # ---------------- portada ----------------
    if notas:
        principal, resto = notas[0], notas[1:5]
        foto = miniatura(principal.get("fuente", {}).get("video", ""))
        tapa = ('<a href="/nota/' + esc(principal["slug"]) + '/"><img class="tapa-foto" src="' +
                esc(foto) + '" alt="" loading="eager" width="1120" height="630"></a>') if foto else ""
        apertura = ('<div class="apertura">' + tapa + '<span class="sello">Lo último</span><h1><a href="/nota/' +
                    esc(principal["slug"]) + '/">' + esc(principal.get("titulo", "")) + "</a></h1><p>" +
                    esc(principal.get("bajada", "")) + "</p></div>")
    elif destacada:
        puntero = destacada["tabla"][0]
        resto = []
        apertura = ('<div class="apertura"><span class="sello dato">Juveniles</span><h1><a href="' + ruta_liga(destacada) + '">' + esc(puntero["equipo"]) + " lidera el " +
                    esc(destacada["nombre"]) + " con " + str(puntero["pts"]) + " puntos</a></h1><p>" +
                    "Ganó " + str(puntero["g"]) + " de " + str(puntero["pj"]) + " partidos y tiene " +
                    str(puntero["gf"]) + " goles a favor. La tabla completa, los resultados de la fecha y "
                    "el fixture se actualizan solos.</p></div>")
    else:
        resto = []
        apertura = '<div class="vacio">Todavía no hay contenido publicado.</div>'

    columna = apertura
    if resto:
        tarjetas = []
        for posicion, n in enumerate(resto):
            thumb = miniatura(n.get("fuente", {}).get("video", ""))
            imagen = ('<a href="/nota/' + esc(n["slug"]) + '/"><img class="nota-foto" src="' + esc(thumb) +
                      '" alt="" loading="lazy" width="264" height="148"></a>') if thumb and posicion < 2 else ""
            tarjetas.append("<article><small>" + esc(n.get("fuente", {}).get("nombre", "")) + "</small>" +
                            imagen + '<h3><a href="/nota/' + esc(n["slug"]) + '/">' +
                            esc(n.get("titulo", "")) + "</a></h3><p>" +
                            esc(n.get("bajada", ""))[:110] + "</p></article>")
        columna += '<div class="secundarias">' + "".join(tarjetas) + "</div>"
    elif notas:
        pass
    else:
        columna += ('<div class="secundarias">' + "".join(
            '<article><small>Campeonato</small><h3><a href="' + ruta_liga(l) + '">' +
            esc(l["nombre"]) + "</a></h3><p>Lidera " + esc(l["tabla"][0]["equipo"]) + " con " +
            str(l["tabla"][0]["pts"]) + " puntos.</p></article>" for l in ligas[1:5]) + "</div>")

    if resultados:
        columna += ('<div class="franja"><h2 class="rotulo">Juveniles · resultados de la fecha</h2>'
                    '<div class="marcadores">' + html_marcadores(resultados[:9]) + "</div></div>")

    lateral = []
    if destacada:
        lateral.append("<div><h2>" + esc(destacada["nombre"]) + "</h2>" +
                       html_tabla(destacada["tabla"], 10, completa=False) +
                       '<p style="margin-top:9px"><a style="font-family:var(--dato);font-size:.72rem;'
                       'letter-spacing:.1em;text-transform:uppercase;color:var(--celeste)" href="' + ruta_liga(destacada) + '">Tabla completa →</a></p></div>')
    if proximos:
        lateral.append("<div><h2>Próxima fecha</h2>" + html_partidos(proximos[:6], False) + "</div>")
    lateral += [html_anuncio(a) for a in anuncios]

    escribir("index.html", pagina(
        SITIO + " — juveniles, primera y lo que se dice en la radio",
        "Resultados, posiciones y fixture de las juveniles del fútbol uruguayo, y lo que dicen los "
        "protagonistas en los programas deportivos, con la cita y el minuto.",
        '<div class="grilla"><div>' + columna + "</div><aside>" + "".join(lateral) + "</aside></div>",
        "/", ligas, "/"))

    # ---------------- notas ----------------
    for nota in notas:
        fuente = nota.get("fuente", {})
        parrafos = "".join("<p>" + esc(p) + "</p>" for p in nota.get("cuerpo", []))
        hechos = [h for h in nota.get("hechos", []) if h.get("minuto")]
        pie = ('<div class="fuente">Lo dijo en <strong>' + esc(fuente.get("programa", "")) + "</strong>, de " +
               esc(fuente.get("nombre", "")) + '. <a href="' + esc(fuente.get("video", "")) +
               '" rel="noopener">Ver el video</a>' +
               (" (minuto " + esc(hechos[0]["minuto"]) + ")" if hechos else "") + ".</div>")
        cuerpo = ('<div class="grilla"><div><article class="nota"><span class="sello">' +
                  esc(nota.get("categoria", "fútbol")) + '</span><h1 class="titulo">' +
                  esc(nota.get("titulo", "")) + '</h1><p class="bajada">' + esc(nota.get("bajada", "")) +
                  '</p><span class="firma">' + fecha_larga(nota.get("fecha", "")) + " · vía " +
                  esc(fuente.get("nombre", "")) + "</span>" + video_fuente(fuente) + parrafos + pie +
                  "</article></div><aside>" +
                  "".join(html_anuncio(a) for a in anuncios) + "</aside></div>")
        # Schema NewsArticle: le dice a Google que esto es una noticia, de cuando
        # es y en que se basa (el video). Es lo que habilita Noticias y Discover.
        esquema = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": nota.get("titulo", "")[:110],
            "description": nota.get("bajada", ""),
            "datePublished": nota.get("publicado_utc", nota.get("fecha", "")),
            "dateModified": nota.get("publicado_utc", nota.get("fecha", "")),
            "inLanguage": "es-UY",
            "mainEntityOfPage": DOMINIO + "/nota/" + nota["slug"] + "/",
            "author": {"@type": "Organization", "name": SITIO},
            "publisher": {"@type": "Organization", "name": SITIO},
            "keywords": ", ".join(nota.get("etiquetas", [])),
            "citation": fuente.get("video", ""),
            "isBasedOn": fuente.get("video", ""),
        }
        escribir("nota/" + nota["slug"] + "/index.html", pagina(
            nota.get("titulo", SITIO), nota.get("bajada", ""), cuerpo,
            "/nota/" + nota["slug"] + "/", ligas,
            esquema=esquema, publicado=nota.get("publicado_utc", "")))

    # ---------------- una seccion por division ----------------
    for clave, titulo in TITULOS_GRUPO.items():
        del_grupo = [l for l in ligas if l.get("grupo", "juveniles") == clave]
        if not del_grupo:
            continue
        fichas = "".join('<a class="ficha" href="' + ruta_liga(l) + '"><b>' + esc(l["nombre"]) +
                         "</b><small>" + str(len(l["tabla"])) + " equipos · lidera " +
                         esc(l["tabla"][0]["equipo"]) + " (" + str(l["tabla"][0]["pts"]) +
                         " pts)</small></a>" for l in del_grupo)
        indice = ('<div class="grilla" style="grid-template-columns:1fr"><div>'
                  '<span class="sello dato">Posiciones</span><h1 class="titulo">' + esc(titulo) +
                  ' del fútbol uruguayo</h1><p class="intro">' + esc(INTRO_GRUPO[clave]) +
                  ' Las posiciones se calculan partido por partido y se actualizan solas cada '
                  'veinte minutos.</p><div class="grilla-ligas">' + fichas + "</div>" +
                  pie_fuente(del_grupo[0], credito) + "</div></div>")
        escribir(clave + "/index.html", pagina(
            titulo + " del fútbol uruguayo: tablas y resultados · " + SITIO,
            "Posiciones, resultados y fixture de " + titulo.lower() + " del fútbol uruguayo, "
            "campeonato por campeonato.",
            indice, "/" + clave + "/", ligas, "/" + clave + "/"))

    for liga in ligas:
        ruta = ruta_liga(liga)
        puntero = liga["tabla"][0]
        lateral_liga = []
        if liga.get("ultimos_resultados"):
            lateral_liga.append("<div><h2>Últimos resultados</h2>" +
                                html_partidos(liga["ultimos_resultados"][:8], True) + "</div>")
        if liga.get("proximos_partidos"):
            lateral_liga.append("<div><h2>Próxima fecha</h2>" +
                                html_partidos(liga["proximos_partidos"][:8], False) + "</div>")
        lateral_liga += [html_anuncio(a) for a in anuncios]
        cuerpo = ('<div class="grilla"><div><span class="sello dato">' +
                  esc(TITULOS_GRUPO.get(liga.get("grupo", "juveniles"), "").split(",")[0]) + " · " +
                  str(len(liga["tabla"])) + ' equipos</span><h1 class="titulo">' + esc(liga["nombre"]) +
                  '</h1><p class="intro">Lidera ' + esc(puntero["equipo"]) + " con " + str(puntero["pts"]) +
                  " puntos en " + str(puntero["pj"]) + " partidos.</p>" + html_tabla(liga["tabla"]) +
                  pie_fuente(liga, credito) + "</div><aside>" +
                  "".join(lateral_liga) + "</aside></div>")
        escribir(ruta.strip("/") + "/index.html", pagina(
            liga["nombre"] + ": tabla de posiciones y resultados · " + SITIO,
            "Tabla de posiciones, últimos resultados y próxima fecha de " + liga["nombre"] + ".",
            cuerpo, ruta, ligas, "/" + liga.get("grupo", "juveniles") + "/"))

    # ---------------- archivos de servicio ----------------
    secciones = ["/" + c + "/" for c in TITULOS_GRUPO
                 if any(l.get("grupo", "juveniles") == c for l in ligas)]
    urls = ["/"] + secciones + [ruta_liga(l) for l in ligas] + \
           ["/nota/" + n["slug"] + "/" for n in notas]
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    escribir("sitemap.xml",
             '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
             "".join("<url><loc>" + DOMINIO + u + "</loc><lastmod>" + hoy + "</lastmod></url>\n" for u in urls) +
             "</urlset>\n")
    # Sitemap de noticias: el canal oficial para que Google rastree rapido lo nuevo.
    # Solo admite articulos de los ultimos dos dias; mas viejos hay que sacarlos.
    recientes = [n for n in notas
                 if (datetime.now(timezone.utc) - datetime.fromisoformat(
                     (n.get("publicado_utc") or n.get("fecha", "1970-01-01") + "T00:00:00+00:00"))).days < 2]
    escribir("sitemap-noticias.xml",
             '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' +
             "".join("<url><loc>" + DOMINIO + "/nota/" + n["slug"] + "/</loc><news:news>"
                     "<news:publication><news:name>" + SITIO + "</news:name>"
                     "<news:language>es</news:language></news:publication>"
                     "<news:publication_date>" + esc(n.get("publicado_utc", "")) + "</news:publication_date>"
                     "<news:title>" + esc(n.get("titulo", "")) + "</news:title></news:news></url>\n"
                     for n in recientes) + "</urlset>\n")

    # RSS: lo leen agregadores, Google News y varios rastreadores de IA.
    def rfc822(iso):
        try:
            return datetime.fromisoformat(iso).strftime("%a, %d %b %Y %H:%M:%S +0000")
        except (ValueError, TypeError):
            return ""
    escribir("rss.xml",
             '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
             "<title>" + SITIO + "</title><link>" + DOMINIO + "</link>\n"
             "<description>" + LEMA + "</description><language>es-uy</language>\n" +
             "".join("<item><title>" + esc(n.get("titulo", "")) + "</title><link>" + DOMINIO + "/nota/" +
                     n["slug"] + "/</link><guid>" + DOMINIO + "/nota/" + n["slug"] + "/</guid>"
                     "<pubDate>" + rfc822(n.get("publicado_utc", "")) + "</pubDate><description>" +
                     esc(n.get("bajada", "")) + "</description></item>\n" for n in notas[:20]) +
             "</channel></rss>\n")

    escribir(INDEXNOW + ".txt", INDEXNOW + "\n")
    escribir(VERIFICACION_GOOGLE, "google-site-verification: " + VERIFICACION_GOOGLE + "\n")
    escribir("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: " + DOMINIO + "/sitemap.xml\n"
                           "Sitemap: " + DOMINIO + "/sitemap-noticias.xml\n")
    escribir("llms.txt",
             "# " + SITIO + "\n\n" + LEMA + ". Medio digital uruguayo.\n\n"
             "## Qué hay acá\n"
             "- Tablas de posiciones, resultados y fixture de las juveniles del fútbol uruguayo "
             "(Sub 11 a Sub 19), calculadas partido por partido. Datos: La Movida Online.\n"
             "- Notas sobre lo que dicen los protagonistas del fútbol en los programas deportivos de "
             "radio y YouTube, siempre con la fuente, el programa y el minuto del video.\n\n"
             "## Campeonatos con tabla publicada\n" +
             "".join("- " + l["nombre"] + ": " + DOMINIO + "/juveniles/" + slug(l["nombre"]) + "/\n" for l in ligas))
    escribir("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")

    print("sitio generado: " + str(len(notas)) + " nota(s), " + str(len(ligas)) + " campeonato(s), " +
          str(len(anuncios)) + " anuncio(s) activo(s)")


if __name__ == "__main__":
    main()
