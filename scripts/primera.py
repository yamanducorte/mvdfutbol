# -*- coding: utf-8 -*-
"""Tablas de Primera Division desde Wikipedia (CC BY-SA 4.0).

Uso:  python scripts/primera.py

Por que Wikipedia: la AUF no publica la tabla de Primera en formato legible, los
proveedores de datos cobran por la temporada en curso, y la tabla de Google es
de un proveedor licenciado (scrapearla viola sus terminos). Wikipedia publica
con licencia libre; la unica obligacion es citar y enlazar, y eso lo hace el
sitio en cada pagina.

Contras honestos: la actualiza gente, asi que puede demorar horas despues de
cada fecha y puede tener errores. Para resultados en vivo hace falta un
proveedor pago.
"""
import html as H
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "primera.json"
ARTICULO = "Campeonato Uruguayo de Primera División 2026"
PAGINA = "https://es.wikipedia.org/wiki/" + urllib.parse.quote(ARTICULO.replace(" ", "_"))
API = "https://es.wikipedia.org/w/api.php"
# Wikipedia pide identificarse con un contacto en el User-Agent.
AGENTE = "MVDFutbol/1.0 (https://mvdfutbol.netlify.app; yamanducorte@gmail.com)"
CREDITO = "Tabla: Wikipedia, «" + ARTICULO + "» (CC BY-SA 4.0)"
# Que secciones publicamos y con que nombre. El resto del articulo se ignora.
SECCIONES = [
    ("tabla anual", "Primera División · Tabla anual"),
    ("torneo clausura", "Primera División · Torneo Clausura"),
    ("torneo apertura", "Primera División · Torneo Apertura"),
]


def limpiar(celda):
    texto = H.unescape(re.sub(r"<[^>]+>", " ", celda))
    return re.sub(r"\s+", " ", texto).strip()


def nombre_equipo(texto):
    """Saca marcas de campeon/descenso y notas al pie: 'Racing (C)' -> 'Racing'."""
    texto = re.sub(r"\s*\((?:C|D|A|P|E|CL|S)\)\s*", " ", texto)
    texto = re.sub(r"\s*\[\s*\d+\s*\]\s*", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def entero(texto):
    hallado = re.search(r"-?\d+", texto.replace("−", "-").replace("+", ""))
    return int(hallado.group()) if hallado else 0


def tabla_de(html_tabla):
    filas = re.findall(r"<tr.*?</tr>", html_tabla, re.S)
    if len(filas) < 3:
        return []
    encabezado = [limpiar(c).lower().rstrip(".") for c in re.findall(r"<t[hd].*?</t[hd]>", filas[0], re.S)]
    columnas = {}
    for indice, nombre in enumerate(encabezado):
        for clave, etiquetas in (("pts", ("pts", "puntos")), ("pj", ("pj", "pg")), ("g", ("g",)),
                                 ("e", ("e",)), ("p", ("p",)), ("gf", ("gf",)), ("gc", ("gc",)),
                                 ("dg", ("dif", "dg"))):
            if nombre in etiquetas and clave not in columnas:
                columnas[clave] = indice
    if "pts" not in columnas or "pj" not in columnas:
        return []
    salida = []
    for fila in filas[1:]:
        celdas = [limpiar(c) for c in re.findall(r"<t[hd].*?</t[hd]>", fila, re.S)]
        if len(celdas) < max(columnas.values()) + 1:
            continue
        equipo = nombre_equipo(celdas[1])
        if not equipo or equipo.lower().startswith("equipo"):
            continue
        salida.append({
            "equipo": equipo,
            "pj": entero(celdas[columnas["pj"]]),
            "g": entero(celdas[columnas["g"]]) if "g" in columnas else 0,
            "e": entero(celdas[columnas["e"]]) if "e" in columnas else 0,
            "p": entero(celdas[columnas["p"]]) if "p" in columnas else 0,
            "gf": entero(celdas[columnas["gf"]]) if "gf" in columnas else 0,
            "gc": entero(celdas[columnas["gc"]]) if "gc" in columnas else 0,
            "dg": entero(celdas[columnas["dg"]]) if "dg" in columnas else 0,
            "pts": entero(celdas[columnas["pts"]]),
        })
    return salida


def main():
    url = (API + "?action=parse&page=" + urllib.parse.quote(ARTICULO) +
           "&prop=text&format=json&formatversion=2")
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        html = json.loads(respuesta.read().decode("utf-8"))["parse"]["text"]

    encontradas = {}
    titulo_actual = ""
    for pieza in re.findall(r"(<h[23][^>]*>.*?</h[23]>|<table.*?</table>)", html, re.S):
        if pieza.startswith("<h"):
            titulo_actual = limpiar(pieza).replace("[ editar ]", "").strip().lower()
        elif "Pts" in pieza and "Equipo" in pieza:
            for marca, nombre in SECCIONES:
                if marca in titulo_actual and nombre not in encontradas:
                    tabla = tabla_de(pieza)
                    if tabla:
                        encontradas[nombre] = tabla

    ligas = []
    for _, nombre in SECCIONES:
        if nombre in encontradas:
            ligas.append({
                "id": "wiki-" + nombre.split("·")[-1].strip().lower().replace(" ", "-"),
                "grupo": "primera",
                "nombre": nombre,
                "tabla": encontradas[nombre],
                "ultimos_resultados": [],
                "proximos_partidos": [],
                "credito": CREDITO,
                "credito_url": PAGINA,
            })

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": PAGINA,
        "credito": CREDITO,
        "ligas": ligas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(str(len(ligas)) + " tabla(s) de Primera -> " + str(SALIDA.relative_to(RAIZ)))
    for liga in ligas:
        puntero = liga["tabla"][0]
        print("  " + liga["nombre"][:40].ljust(42) + str(len(liga["tabla"])) + " equipos | lidera " +
              puntero["equipo"] + " (" + str(puntero["pts"]) + " pts, " + str(puntero["pj"]) + " PJ)")


if __name__ == "__main__":
    main()
