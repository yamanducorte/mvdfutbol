# -*- coding: utf-8 -*-
"""Tablas de Primera Division y cruces de la Copa AUF Uruguay, desde Wikipedia.

Uso:  python scripts/primera.py

Por que Wikipedia: la AUF no publica la tabla de Primera en formato legible, los
proveedores de datos cobran por la temporada en curso, y la tabla de Google es
de un proveedor licenciado (scrapearla viola sus terminos). Wikipedia publica
con licencia libre; la unica obligacion es citar y enlazar, y eso lo hace el
sitio en cada pagina.

Por que no la calculamos nosotros, si tenemos los partidos: se probo, y la
tabla anual calculada sumando Apertura + Intermedio + Clausura daba un punto de
diferencia en tres equipos contra la oficial (quitas de puntos, fallos de mesa,
partidos dados por ganados). En Primera hay una tabla oficial publicada y esa es
la que vale. En juveniles no existe ninguna publicada, y ahi si la calculamos
nosotros, avisando que es calculada.

Contras honestos: Wikipedia la actualiza gente, asi que puede demorar horas
despues de cada fecha y puede tener errores. Para resultados en vivo hace falta
un proveedor pago.
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
ARTICULO_COPA = "Copa AUF Uruguay 2026"
API = "https://es.wikipedia.org/w/api.php"
# Wikipedia pide identificarse con un contacto en el User-Agent.
AGENTE = "MVDFutbol/1.0 (https://yamanducorte.github.io/mvdfutbol; yamanducorte@gmail.com)"


def pagina(articulo):
    return "https://es.wikipedia.org/wiki/" + urllib.parse.quote(articulo.replace(" ", "_"))


def credito(articulo):
    return "Tabla: Wikipedia, «" + articulo + "» (CC BY-SA 4.0)"


# Que secciones del articulo publicamos, con que nombre y con que etiquetas.
# (marca en el titulo, titulo del sitio, torneo, serie)
SECCIONES = [
    ("tabla anual", "Primera División · Tabla anual", "anual", None),
    ("torneo clausura", "Primera División · Torneo Clausura", "clausura", None),
    ("serie a", "Primera División · Torneo Intermedio · Serie A", "intermedio", "A"),
    ("serie b", "Primera División · Torneo Intermedio · Serie B", "intermedio", "B"),
    ("torneo apertura", "Primera División · Torneo Apertura", "apertura", None),
]
# Las rondas de la Copa, de la mas avanzada a la primera. El titulo tiene que ser
# igual, no contener: "final" esta dentro de "octavos de final".
RONDAS_COPA = [
    ("final", "Final"),
    ("semifinales", "Semifinales"),
    ("semifinal", "Semifinales"),
    ("cuartos de final", "Cuartos de final"),
    ("octavos de final", "Octavos de final"),
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


def traer(articulo):
    url = (API + "?action=parse&page=" + urllib.parse.quote(articulo) +
           "&prop=text&format=json&formatversion=2")
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))["parse"]["text"]


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


def llaves_de(html_tabla):
    """Los cruces de una ronda: la tabla 'Equipo 1 | Resultado | Equipo 2'.

    Un cruce sin resultado todavia no se jugo, y asi se muestra.
    """
    filas = re.findall(r"<tr.*?</tr>", html_tabla, re.S)
    cruces = []
    for fila in filas:
        celdas = [limpiar(c) for c in re.findall(r"<t[hd].*?</t[hd]>", fila, re.S)]
        if len(celdas) < 3:
            continue
        uno, resultado, dos = celdas[0], celdas[1], celdas[2]
        if uno.lower().startswith("equipo") or not uno or not dos:
            continue
        # El resultado viene como "0:4" o "2:1 (3:4 p)"; si no hay numeros, no se jugo.
        jugado = bool(re.search(r"\d+\s*[:–-]\s*\d+", resultado))
        cruces.append({
            "uno": nombre_equipo(uno),
            "dos": nombre_equipo(dos),
            "resultado": resultado if jugado else "",
            "jugado": jugado,
        })
    return cruces


def tablas_de_primera():
    html = traer(ARTICULO)
    encontradas = {}
    titulo_actual = ""
    for pieza in re.findall(r"(<h[234][^>]*>.*?</h[234]>|<table.*?</table>)", html, re.S):
        if pieza.startswith("<h"):
            titulo_actual = limpiar(pieza).replace("[ editar ]", "").strip().lower()
        elif "Pts" in pieza and "Equipo" in pieza:
            for marca, nombre, _, _ in SECCIONES:
                if marca in titulo_actual and nombre not in encontradas:
                    tabla = tabla_de(pieza)
                    if tabla:
                        encontradas[nombre] = tabla
    ligas = []
    for _, nombre, torneo, serie in SECCIONES:
        if nombre not in encontradas:
            continue
        ligas.append({
            "id": "wiki-" + torneo + ("-" + serie.lower() if serie else ""),
            "grupo": "primera",
            "categoria": "primera",
            "division": None,
            "torneo": torneo,
            "serie": serie,
            "nombre": nombre,
            "titulo": nombre,
            "oficial": True,
            "tabla": encontradas[nombre],
            "ultimos_resultados": [],
            "proximos_partidos": [],
            "credito": credito(ARTICULO),
            "credito_url": pagina(ARTICULO),
        })
    return ligas


def cruces_de_la_copa():
    """Las llaves de la fase final de la Copa AUF Uruguay, de la ronda mas
    avanzada hacia atras. Si el articulo todavia no tiene una ronda, no sale."""
    try:
        html = traer(ARTICULO_COPA)
    except Exception as error:
        print("  !! no se pudo leer la Copa: " + str(error))
        return []
    por_titulo = {}
    titulo_actual = ""
    for pieza in re.findall(r"(<h[234][^>]*>.*?</h[234]>|<table.*?</table>)", html, re.S):
        if pieza.startswith("<h"):
            titulo_actual = limpiar(pieza).replace("[ editar ]", "").strip().lower()
        elif "Equipo 1" in pieza or "Equipo&#160;1" in pieza:
            por_titulo.setdefault(titulo_actual, []).extend(llaves_de(pieza))
    rondas, ya = [], set()
    for marca, nombre in RONDAS_COPA:
        if nombre in ya:
            continue
        cruces = por_titulo.get(marca)
        if cruces:
            rondas.append({"ronda": nombre, "cruces": cruces})
            ya.add(nombre)
    return rondas


def main():
    ligas = tablas_de_primera()
    rondas = cruces_de_la_copa()

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fuente": pagina(ARTICULO),
        "credito": credito(ARTICULO),
        "ligas": ligas,
        "copa": {
            "nombre": "Copa AUF Uruguay",
            "fuente": pagina(ARTICULO_COPA),
            "credito": credito(ARTICULO_COPA),
            "rondas": rondas,
        },
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(str(len(ligas)) + " tabla(s) de Primera -> " + str(SALIDA.relative_to(RAIZ)))
    for liga in ligas:
        puntero = liga["tabla"][0]
        print("  " + liga["nombre"][:44].ljust(46) + str(len(liga["tabla"])) + " equipos | " +
              puntero["equipo"] + " (" + str(puntero["pts"]) + " pts, " + str(puntero["pj"]) + " PJ)")
    for ronda in rondas:
        jugados = sum(1 for c in ronda["cruces"] if c["jugado"])
        print("  Copa · " + ronda["ronda"].ljust(38) + str(len(ronda["cruces"])) +
              " cruces (" + str(jugados) + " jugados)")


if __name__ == "__main__":
    main()
