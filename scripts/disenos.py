# -*- coding: utf-8 -*-
"""Genera tres propuestas de diseno de portada con los datos reales.

Uso:  python scripts/disenos.py   ->  publico/disenos/{a,b,c}/index.html

A = diario deportivo (prensa: Marca, Ole, AS): densidad alta, titulares grandes.
B = portal de resultados (Flashscore, Promiedos, SofaScore): el dato manda.
C = revista (The Athletic, ESPN FC): pocas notas, bien presentadas, mucho aire.
Las tres usan la misma informacion real para que la comparacion sea honesta.
"""
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "publico" / "disenos"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
TIPOS = ("https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800;900"
         "&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700"
         "&family=IBM+Plex+Mono:wght@400;500;600&family=Playfair+Display:wght@700;800;900&display=swap")


def esc(v):
    return html.escape(str(v), quote=True)


def slug(t):
    limpio = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", limpio.lower())).strip("-")[:70]


def leer(ruta, defecto):
    try:
        return json.loads((RAIZ / ruta).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def hora(iso):
    try:
        return datetime.fromisoformat(iso[:19]).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def dia_mes(iso):
    try:
        f = datetime.fromisoformat(iso[:19])
        return str(f.day).rjust(2, "0") + "/" + str(f.month).rjust(2, "0")
    except (ValueError, TypeError):
        return ""


def titular(texto, largo=72):
    """Los titulos de los programas vienen gritados en mayusculas y entrecomillados."""
    limpio = re.sub(r"\s+", " ", texto.strip().strip('"“”'))
    letras = [c for c in limpio if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.7:
        limpio = limpio.capitalize()
        for sigla in ("auf", "fifa", "conmebol", "var", "ovacion", "tv"):
            limpio = re.sub(r"\b" + sigla + r"\b", sigla.upper(), limpio)
    return limpio[:largo].rstrip(" ,;.") + ("..." if len(limpio) > largo else "")


def cargar():
    juveniles = leer("datos/juveniles.json", {"ligas": []})
    ligas = [l for l in juveniles.get("ligas", []) if l.get("tabla")]
    destacada = next((l for l in ligas if "Sub15" in l["nombre"]), ligas[0] if ligas else None)
    resultados = sorted((p for l in ligas for p in l.get("ultimos_resultados", [])),
                        key=lambda p: p["fecha"], reverse=True)[:8]
    proximos = sorted((p for l in ligas for p in l.get("proximos_partidos", [])),
                      key=lambda p: p["fecha"])[:6]
    programas = [p for p in leer("datos/hallazgos/pendientes.json", []) if p.get("titulo")][:5]
    anuncios = [a for a in leer("anuncios.json", {}).get("anuncios", []) if a.get("activo") and a.get("url")]
    return ligas, destacada, resultados, proximos, programas, anuncios


BASE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{titulo}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{tipos}">
<style>{css}</style></head><body>
<div class="cinta">Propuesta {letra} · {nombre} — datos reales, portada de ejemplo. <a href="/disenos/">ver las tres</a></div>
{cuerpo}
</body></html>
"""

CINTA = """
.cinta{background:#111;color:#fff;font:500 .76rem/1.5 'IBM Plex Mono',monospace;padding:7px 16px;text-align:center}
.cinta a{color:#8fd3f4}
"""

# ---------------------------------------------------------------- A: diario
CSS_A = CINTA + """
:root{--rojo:#c0202a;--tinta:#101114;--gris:#6b7280;--linea:#dcdcd7;--fondo:#fff;--crema:#f4f2ec}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--fondo);color:var(--tinta);font-family:'Source Serif 4',Georgia,serif}
.ancho{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header{border-bottom:3px solid var(--tinta)}
.cab{display:flex;align-items:baseline;justify-content:space-between;gap:16px;padding-block:12px;flex-wrap:wrap}
.logo{font-family:'Archivo',sans-serif;font-weight:900;font-size:2rem;letter-spacing:-.045em;text-transform:uppercase}
.logo i{font-style:normal;color:var(--rojo)}
.cab small{font-family:'IBM Plex Mono',monospace;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gris)}
.menu{background:var(--tinta);color:#fff}
.menu .ancho{display:flex;gap:20px;overflow-x:auto;font-family:'Archivo',sans-serif;font-weight:700;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;padding-block:9px}
.menu span:first-child{color:#ff6b74}
.grilla{display:grid;grid-template-columns:minmax(0,2.4fr) minmax(0,1fr);gap:30px;padding-block:22px}
.apertura{border-bottom:1px solid var(--linea);padding-bottom:18px;margin-bottom:18px}
.vivo{display:inline-block;background:var(--rojo);color:#fff;font-family:'IBM Plex Mono',monospace;font-size:.64rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;padding:3px 8px;margin-bottom:9px}
.apertura h1{font-family:'Archivo',sans-serif;font-weight:900;font-size:clamp(1.9rem,4.4vw,3.1rem);line-height:1.02;letter-spacing:-.035em;text-wrap:balance}
.apertura p{color:var(--gris);font-size:1.08rem;margin-top:10px;max-width:40rem}
.secundarias{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}
.secundarias article{border-top:2px solid var(--tinta);padding-top:9px}
.secundarias h3{font-family:'Archivo',sans-serif;font-weight:700;font-size:1.02rem;line-height:1.18;letter-spacing:-.015em}
.secundarias small{font-family:'IBM Plex Mono',monospace;font-size:.64rem;letter-spacing:.1em;text-transform:uppercase;color:var(--rojo)}
.franja{background:var(--crema);border-top:1px solid var(--linea);border-bottom:1px solid var(--linea);margin-top:22px;padding-block:16px}
.franja h2,aside h2{font-family:'Archivo',sans-serif;font-weight:800;font-size:.84rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px}
.marcadores{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:10px}
.mk{background:#fff;border:1px solid var(--linea);padding:9px 11px;font-size:.9rem}
.mk .r{font-family:'IBM Plex Mono',monospace;font-weight:600;color:var(--rojo)}
.mk div{display:flex;justify-content:space-between;gap:10px}
aside{display:flex;flex-direction:column;gap:22px;min-width:0}
table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:.78rem;font-variant-numeric:tabular-nums}
th{font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;color:var(--gris);text-align:right;padding:6px 4px;border-bottom:2px solid var(--tinta)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td{padding:6px 4px;border-bottom:1px solid var(--linea)}
td.eq{font-family:'Source Serif 4',serif;font-size:.92rem}
.aviso{border:1px solid var(--linea);border-top:3px solid var(--rojo);padding:13px}
.aviso small{font-family:'IBM Plex Mono',monospace;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;color:var(--rojo)}
.aviso h3{font-family:'Archivo',sans-serif;font-size:1rem;margin:5px 0}
.aviso p{font-size:.88rem;color:var(--gris);margin-bottom:9px}
.aviso a{font-family:'Archivo',sans-serif;font-weight:700;font-size:.8rem;background:var(--tinta);color:#fff;padding:7px 13px;text-decoration:none;display:inline-block}
@media(max-width:860px){.grilla{grid-template-columns:1fr}}
"""

# ---------------------------------------------------------------- B: portal de datos
CSS_B = CINTA + """
:root{--fondo:#0e1116;--panel:#161b22;--panel2:#1c232c;--borde:#262d36;--texto:#e6edf3;--suave:#8b97a5;--verde:#3fb950;--lima:#d2f564}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--fondo);color:var(--texto);font-family:'Archivo',system-ui,sans-serif;font-size:14px}
.ancho{max-width:1180px;margin:0 auto;padding-left:max(14px,env(safe-area-inset-left,0px));padding-right:max(14px,env(safe-area-inset-right,0px))}
header{background:var(--panel);border-bottom:1px solid var(--borde);position:sticky;top:0;z-index:5}
.cab{display:flex;align-items:center;gap:18px;padding-block:11px;flex-wrap:wrap}
.logo{font-weight:800;font-size:1.15rem;letter-spacing:-.03em}
.logo i{font-style:normal;color:var(--lima)}
.tabs{display:flex;gap:7px;overflow-x:auto;padding-block:9px}
.tabs b{font-size:.74rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;background:var(--panel2);border:1px solid var(--borde);border-radius:999px;padding:5px 11px;white-space:nowrap;color:var(--suave)}
.tabs b.on{background:var(--lima);color:#101418;border-color:var(--lima)}
.doble{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:18px;padding-block:18px}
.caja{background:var(--panel);border:1px solid var(--borde);border-radius:7px;overflow:hidden}
.caja>h2{font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--suave);padding:10px 13px;border-bottom:1px solid var(--borde);display:flex;justify-content:space-between}
.pt{display:grid;grid-template-columns:48px 1fr auto 1fr;gap:9px;align-items:center;padding:9px 13px;border-bottom:1px solid var(--borde);font-size:.9rem}
.pt:last-child{border-bottom:0}
.pt .h{font-family:'IBM Plex Mono',monospace;font-size:.72rem;color:var(--suave)}
.pt .g{font-family:'IBM Plex Mono',monospace;font-weight:600;background:var(--panel2);border-radius:4px;padding:2px 9px;white-space:nowrap}
.pt .d{text-align:right}
.pt.fin .g{color:var(--lima)}
table{width:100%;border-collapse:collapse;font-size:.82rem;font-variant-numeric:tabular-nums}
th{font-family:'IBM Plex Mono',monospace;font-size:.62rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--suave);text-align:right;padding:8px 5px;border-bottom:1px solid var(--borde)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td{padding:7px 5px;border-bottom:1px solid #1d242d;font-family:'IBM Plex Mono',monospace}
td.eq{font-family:'Archivo',sans-serif;font-weight:500}
tbody tr:nth-child(-n+4) td.p{color:var(--verde);font-weight:600}
.nt{display:flex;gap:11px;padding:11px 13px;border-bottom:1px solid var(--borde)}
.nt:last-child{border-bottom:0}
.nt .n{font-family:'IBM Plex Mono',monospace;font-size:1.05rem;color:#303a46;font-weight:600;line-height:1}
.nt h3{font-size:.92rem;font-weight:600;line-height:1.3}
.nt small{color:var(--suave);font-size:.74rem}
.aviso{background:linear-gradient(160deg,#1b232c,#161b22);border:1px solid var(--borde);border-radius:7px;padding:14px}
.aviso small{font-family:'IBM Plex Mono',monospace;font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;color:var(--lima)}
.aviso h3{font-size:1rem;margin:6px 0}
.aviso p{font-size:.86rem;color:var(--suave);margin-bottom:11px}
.aviso a{display:block;text-align:center;font-weight:700;font-size:.84rem;background:var(--lima);color:#101418;padding:9px;border-radius:5px;text-decoration:none}
aside{display:flex;flex-direction:column;gap:18px;min-width:0}
@media(max-width:860px){.doble{grid-template-columns:1fr}}
"""

# ---------------------------------------------------------------- C: revista
CSS_C = CINTA + """
:root{--papel:#fbfaf7;--tinta:#1a1a1a;--gris:#6d6a63;--linea:#e2ded4;--vino:#8a2e3b;--oro:#b08a3e}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--papel);color:var(--tinta);font-family:'Source Serif 4',Georgia,serif;line-height:1.65}
.ancho{max-width:1060px;margin:0 auto;padding-left:max(20px,env(safe-area-inset-left,0px));padding-right:max(20px,env(safe-area-inset-right,0px))}
header{text-align:center;padding-block:30px 18px;border-bottom:1px solid var(--linea)}
.logo{font-family:'Playfair Display',Georgia,serif;font-weight:900;font-size:clamp(2rem,6vw,3.1rem);letter-spacing:-.02em;line-height:1}
.logo i{font-style:italic;color:var(--vino)}
header p{font-family:'IBM Plex Mono',monospace;font-size:.66rem;letter-spacing:.3em;text-transform:uppercase;color:var(--gris);margin-top:9px}
nav{display:flex;justify-content:center;gap:26px;padding-block:13px;font-family:'IBM Plex Mono',monospace;font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;border-bottom:1px solid var(--linea);overflow-x:auto}
nav span{white-space:nowrap;color:var(--gris)}
nav span:first-child{color:var(--vino)}
.tapa{padding-block:38px 30px;border-bottom:1px solid var(--linea);display:grid;gap:14px;max-width:44rem}
.tapa .et{font-family:'IBM Plex Mono',monospace;font-size:.64rem;letter-spacing:.24em;text-transform:uppercase;color:var(--oro)}
.tapa h1{font-family:'Playfair Display',serif;font-weight:800;font-size:clamp(2rem,5.2vw,3.3rem);line-height:1.08;letter-spacing:-.02em;text-wrap:balance}
.tapa p{font-size:1.16rem;color:var(--gris)}
.tapa .firma{font-family:'IBM Plex Mono',monospace;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--gris)}
.dos{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(0,1fr);gap:46px;padding-block:30px}
.rot{font-family:'IBM Plex Mono',monospace;font-size:.64rem;letter-spacing:.26em;text-transform:uppercase;color:var(--gris);padding-bottom:9px;border-bottom:2px solid var(--tinta);margin-bottom:18px}
.lista article{padding-block:17px;border-bottom:1px solid var(--linea);display:grid;gap:5px}
.lista h3{font-family:'Playfair Display',serif;font-weight:700;font-size:1.3rem;line-height:1.22}
.lista small{font-family:'IBM Plex Mono',monospace;font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;color:var(--vino)}
.lista p{color:var(--gris);font-size:.98rem}
aside{min-width:0;display:flex;flex-direction:column;gap:30px}
table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:.76rem;font-variant-numeric:tabular-nums}
th{font-size:.58rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:var(--gris);text-align:right;padding:5px 3px;border-bottom:1px solid var(--tinta)}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td{padding:6px 3px;border-bottom:1px solid var(--linea)}
td.eq{font-family:'Source Serif 4',serif;font-size:.9rem}
.res{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid var(--linea);font-size:.92rem}
.res b{font-family:'IBM Plex Mono',monospace;font-weight:600}
.aviso{border:1px solid var(--linea);background:#fff;padding:18px}
.aviso small{font-family:'IBM Plex Mono',monospace;font-size:.6rem;letter-spacing:.2em;text-transform:uppercase;color:var(--oro)}
.aviso h3{font-family:'Playfair Display',serif;font-size:1.15rem;margin:7px 0}
.aviso p{font-size:.92rem;color:var(--gris);margin-bottom:12px}
.aviso a{font-family:'IBM Plex Mono',monospace;font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--vino);text-decoration:none;border-bottom:1px solid var(--vino);padding-bottom:3px}
@media(max-width:860px){.dos{grid-template-columns:1fr;gap:34px}}
"""


def filas_tabla(tabla, limite, clase_pts="p"):
    filas = []
    for puesto, f in enumerate(tabla[:limite], 1):
        filas.append("<tr><td>" + str(puesto) + '</td><td class="eq">' + esc(f["equipo"]) +
                     "</td><td>" + str(f["pj"]) + "</td><td>" + ("+" if f["dg"] > 0 else "") +
                     str(f["dg"]) + '</td><td class="' + clase_pts + '">' + str(f["pts"]) + "</td></tr>")
    return ('<table><thead><tr><th></th><th>Equipo</th><th>PJ</th><th>DG</th><th>Pts</th></tr></thead>'
            "<tbody>" + "".join(filas) + "</tbody></table>")


def diseno_a(datos):
    ligas, destacada, resultados, proximos, programas, anuncios = datos
    apertura = programas[0] if programas else None
    resto = programas[1:5]
    marcadores = "".join('<div class="mk"><div><span>' + esc(p["local"]) + '</span><span class="r">' +
                         str(p["goles_local"]) + "-" + str(p["goles_visita"]) + "</span></div><div><span>" +
                         esc(p["visita"]) + "</span></div></div>" for p in resultados[:6])
    secundarias = "".join("<article><small>" + esc(p["fuente"]) + "</small><h3>" +
                          esc(titular(p["titulo"], 85)) + "</h3></article>" for p in resto)
    avisos = "".join('<div class="aviso"><small>' + esc(a["etiqueta"]) + "</small><h3>" + esc(a["titulo"]) +
                     "</h3><p>" + esc(a["texto"]) + '</p><a href="' + esc(a["url"]) + '">' + esc(a["cta"]) +
                     "</a></div>" for a in anuncios)
    cuerpo = """
<header><div class="ancho cab"><div class="logo">MVD<i>Fútbol</i></div>
<small>Montevideo · {fecha} · edición de la tarde</small></div></header>
<div class="menu"><div class="ancho"><span>Portada</span><span>Juveniles</span><span>Primera</span><span>Selección</span><span>Pases</span><span>Resultados</span></div></div>
<div class="ancho grilla">
  <div>
    <div class="apertura"><span class="vivo">Lo último</span>
      <h1>{apertura}</h1>
      <p>Lo dijo en {programa}. La nota completa sale con la cita textual y el minuto exacto del video.</p>
    </div>
    <div class="secundarias">{secundarias}</div>
    <div class="franja"><div class="ancho"><h2>Juveniles · resultados de la fecha</h2>
      <div class="marcadores">{marcadores}</div></div></div>
  </div>
  <aside>
    <div><h2>{liga}</h2>{tabla}</div>
    {avisos}
  </aside>
</div>
""".format(fecha=fecha_hoy(), apertura=esc(titular(apertura["titulo"], 95)) if apertura else "Sin novedades",
           programa=esc(apertura["fuente"]) if apertura else "", secundarias=secundarias,
           marcadores=marcadores, liga=esc(destacada["nombre"]) if destacada else "",
           tabla=filas_tabla(destacada["tabla"], 8) if destacada else "", avisos=avisos)
    return BASE.format(titulo="MVD Fútbol · propuesta A", tipos=TIPOS, css=CSS_A, letra="A",
                       nombre="Diario deportivo", cuerpo=cuerpo)


def diseno_b(datos):
    ligas, destacada, resultados, proximos, programas, anuncios = datos
    pestanas = "".join("<b" + (' class="on"' if i == 0 else "") + ">" + esc(n) + "</b>"
                       for i, n in enumerate(["Hoy", "Sub 19", "Sub 17", "Sub 16", "Sub 15", "Sub 14",
                                              "Sub 13", "Primera", "Femenino"]))
    jugados = "".join('<div class="pt fin"><span class="h">FIN</span><span>' + esc(p["local"]) +
                      '</span><span class="g">' + str(p["goles_local"]) + " - " + str(p["goles_visita"]) +
                      '</span><span class="d">' + esc(p["visita"]) + "</span></div>" for p in resultados[:7])
    porvenir = "".join('<div class="pt"><span class="h">' + dia_mes(p["fecha"]) + '</span><span>' +
                       esc(p["local"]) + '</span><span class="g">' + hora(p["fecha"]) +
                       '</span><span class="d">' + esc(p["visita"]) + "</span></div>" for p in proximos[:5])
    notas = "".join('<div class="nt"><span class="n">' + str(i).rjust(2, "0") + "</span><div><h3>" +
                    esc(titular(p["titulo"], 78)) + "</h3><small>" + esc(p["fuente"]) +
                    "</small></div></div>" for i, p in enumerate(programas[:4], 1))
    avisos = "".join('<div class="aviso"><small>' + esc(a["etiqueta"]) + "</small><h3>" + esc(a["titulo"]) +
                     "</h3><p>" + esc(a["texto"]) + '</p><a href="' + esc(a["url"]) + '">' + esc(a["cta"]) +
                     "</a></div>" for a in anuncios)
    cuerpo = """
<header><div class="ancho cab"><div class="logo">MVD<i>.</i>futbol</div>
<span style="color:#8b97a5;font-size:.78rem;font-family:'IBM Plex Mono',monospace">{fecha}</span></div>
<div class="ancho tabs">{pestanas}</div></header>
<div class="ancho doble">
  <div style="display:flex;flex-direction:column;gap:18px">
    <div class="caja"><h2><span>Resultados de ayer</span><span>juveniles</span></h2>{jugados}</div>
    <div class="caja"><h2><span>Se juega</span><span>próxima fecha</span></h2>{porvenir}</div>
    <div class="caja"><h2><span>Lo que se dijo en la radio</span></h2>{notas}</div>
  </div>
  <aside>
    <div class="caja"><h2><span>{liga}</span></h2><div style="padding:4px 13px 10px">{tabla}</div></div>
    {avisos}
  </aside>
</div>
""".format(fecha=fecha_hoy(), pestanas=pestanas, jugados=jugados, porvenir=porvenir, notas=notas,
           liga=esc(destacada["nombre"]) if destacada else "",
           tabla=filas_tabla(destacada["tabla"], 10) if destacada else "", avisos=avisos)
    return BASE.format(titulo="MVD Fútbol · propuesta B", tipos=TIPOS, css=CSS_B, letra="B",
                       nombre="Portal de resultados", cuerpo=cuerpo)


def diseno_c(datos):
    ligas, destacada, resultados, proximos, programas, anuncios = datos
    tapa = programas[0] if programas else None
    lista = "".join("<article><small>" + esc(p["fuente"]) + "</small><h3>" + esc(titular(p["titulo"], 90)) +
                    "</h3><p>Con la cita textual y el minuto del programa.</p></article>" for p in programas[1:4])
    res = "".join('<div class="res"><span>' + esc(p["local"]) + " vs " + esc(p["visita"]) + "</span><b>" +
                  str(p["goles_local"]) + "-" + str(p["goles_visita"]) + "</b></div>" for p in resultados[:6])
    avisos = "".join('<div class="aviso"><small>' + esc(a["etiqueta"]) + "</small><h3>" + esc(a["titulo"]) +
                     "</h3><p>" + esc(a["texto"]) + '</p><a href="' + esc(a["url"]) + '">' + esc(a["cta"]) +
                     " →</a></div>" for a in anuncios)
    cuerpo = """
<header><div class="ancho"><div class="logo">MVD <i>Fútbol</i></div><p>Montevideo · {fecha}</p></div></header>
<nav><span>Portada</span><span>Juveniles</span><span>Primera</span><span>Selección</span><span>Análisis</span></nav>
<div class="ancho">
  <div class="tapa"><span class="et">Lo que se dijo</span>
    <h1>{tapa}</h1>
    <p>El audio de los programas deportivos, convertido en texto que se puede buscar, citar y verificar.</p>
    <span class="firma">{programa} · hoy</span>
  </div>
  <div class="dos">
    <div><div class="rot">Más notas</div><div class="lista">{lista}</div></div>
    <aside>
      <div><div class="rot">{liga}</div>{tabla}</div>
      <div><div class="rot">Resultados</div>{res}</div>
      {avisos}
    </aside>
  </div>
</div>
""".format(fecha=fecha_hoy(), tapa=esc(titular(tapa["titulo"], 90)) if tapa else "Sin novedades",
           programa=esc(tapa["fuente"]) if tapa else "", lista=lista,
           liga=esc(destacada["nombre"]) if destacada else "",
           tabla=filas_tabla(destacada["tabla"], 8) if destacada else "", res=res, avisos=avisos)
    return BASE.format(titulo="MVD Fútbol · propuesta C", tipos=TIPOS, css=CSS_C, letra="C",
                       nombre="Revista", cuerpo=cuerpo)


def fecha_hoy():
    f = datetime.now(timezone.utc)
    return str(f.day) + " de " + MESES[f.month - 1] + " de " + str(f.year)


def main():
    datos = cargar()
    propuestas = [("a", "Diario deportivo", diseno_a), ("b", "Portal de resultados", diseno_b),
                  ("c", "Revista", diseno_c)]
    for letra, nombre, funcion in propuestas:
        destino = PUBLICO / letra / "index.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(funcion(datos), encoding="utf-8")
        print("  " + letra.upper() + " · " + nombre + " -> /disenos/" + letra + "/")

    indice = ("<!doctype html><html lang=es><head><meta charset=utf-8>"
              "<meta name=viewport content='width=device-width,initial-scale=1'>"
              "<title>Tres propuestas · MVD Fútbol</title><link rel=stylesheet href='" + TIPOS + "'>"
              "<style>body{font-family:'Source Serif 4',Georgia,serif;background:#f6f5f1;color:#15181d;"
              "margin:0;padding:48px max(16px,env(safe-area-inset-left,0px))}"
              ".c{max-width:820px;margin:0 auto}h1{font-family:Archivo,sans-serif;font-size:2rem;"
              "letter-spacing:-.03em;margin-bottom:8px}p.l{color:#555d69;margin-bottom:30px}"
              "a.o{display:block;border:1px solid #d9d7cd;background:#fff;padding:18px 20px;margin-bottom:14px;"
              "text-decoration:none;color:inherit}a.o:hover{border-color:#1b7fb8}"
              "a.o b{font-family:Archivo,sans-serif;font-size:1.15rem;display:block}"
              "a.o span{color:#555d69;font-size:.95rem}</style></head><body><div class=c>"
              "<h1>Tres propuestas de portada</h1><p class=l>Las tres con los mismos datos reales. "
              "Mirá cuál te resulta más cómoda y decime la letra.</p>"
              "<a class=o href='/disenos/a/'><b>A · Diario deportivo</b><span>Como Marca, Olé o AS: "
              "titular enorme arriba, mucha noticia por pantalla, rojo de prensa deportiva. Pensada para "
              "el que entra a leer qué pasó.</span></a>"
              "<a class=o href='/disenos/b/'><b>B · Portal de resultados</b><span>Como Flashscore o "
              "Promiedos: oscuro, compacto, pestañas por categoría, los marcadores primero y las notas "
              "después. Pensada para el que entra a ver cómo salió.</span></a>"
              "<a class=o href='/disenos/c/'><b>C · Revista</b><span>Como The Athletic: una nota "
              "principal grande, tipografía con carácter, mucho aire. Pensada para leer y para vender "
              "cursos a ese lector.</span></a>"
              "<p class=l style='margin-top:26px'><a href='/'>← volver al sitio actual</a></p>"
              "</div></body></html>")
    (PUBLICO / "index.html").write_text(indice, encoding="utf-8")
    print("  índice -> /disenos/")


if __name__ == "__main__":
    main()
