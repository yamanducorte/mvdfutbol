# -*- coding: utf-8 -*-
"""Trae los partidos del fútbol uruguayo y calcula todas las tablas.

Uso:  python scripts/datos.py
      python scripts/datos.py --listar   (muestra que campeonatos detecta y sale)

Lee la API publica de La Movida Online (SportsPress). Los resultados son hechos
(no se copia texto de nadie) y las tablas se calculan aca a partir de los
partidos jugados. El credito a la fuente va en el JSON y tiene que mostrarse
en el sitio.

Que trae, para cada campeonato: la tabla, los ultimos resultados y los proximos
partidos. Y ademas calcula las **tablas anuales**, que no existen en la fuente:
se suman los torneos del anio de esa misma categoria. En Primera eso es Apertura
+ Intermedio + Clausura, que es como la arma la AUF.

Los torneos ya terminados no cambian nunca mas, asi que sus partidos quedan
cacheados y no se vuelven a pedir: sin eso, cada corrida pediria de nuevo los
120 partidos del Apertura al dope.
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fuentes.json"
DATOS = RAIZ / "datos"
SALIDA = DATOS / "juveniles.json"
CACHE_EQUIPOS = DATOS / "equipos.json"
CACHE_PARTIDOS = DATOS / "partidos.json"
CACHE_ANIOS = DATOS / "anios_de_campeonato.json"
# Nos presentamos con nombre y contacto en vez de disfrazarnos de navegador:
# si a La Movida le molesta lo que hacemos, tiene que poder encontrarnos.
AGENTE = "MVDFutbol/1.0 (+https://yamanducorte.github.io/mvdfutbol; yamanducorte@gmail.com)"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# ---------------------------------------------------------------- clasificacion
# El orden importa: gana el primero que machea.
CATEGORIAS = [
    ("primera", "Primera División", 10, re.compile(r"\bliga\s*auf\b", re.I)),
    ("tercera", "Tercera División", 20, re.compile(r"tercera\s*div|\btercera\b", re.I)),
    ("sub19", "Sub 19", 30, re.compile(r"sub\s?-?19|\bs19\b|\bu19\b", re.I)),
    ("sub17", "Sub 17", 40, re.compile(r"sub\s?-?17|\bs17\b|\bu17\b", re.I)),
    ("sub16", "Sub 16", 50, re.compile(r"sub\s?-?16|\bs16\b|\bu16\b", re.I)),
    ("sub15", "Sub 15", 60, re.compile(r"sub\s?-?15|\bs15\b|\bu15\b", re.I)),
    ("sub14", "Sub 14", 70, re.compile(r"sub\s?-?14|\bs14\b|\bu14\b", re.I)),
    ("sub13", "Sub 13", 80, re.compile(r"sub\s?-?13|\bs13\b", re.I)),
    ("sub11", "Sub 11", 90, re.compile(r"sub\s?-?11|\bs11\b", re.I)),
]
TITULO_CATEGORIA = {c: t for c, t, _, _ in CATEGORIAS}
ORDEN_CATEGORIA = {c: o for c, _, o, _ in CATEGORIAS}

TORNEOS = [
    ("apertura", "Torneo Apertura", re.compile(r"apertura", re.I)),
    ("clausura", "Torneo Clausura", re.compile(r"clausura", re.I)),
    ("intermedio", "Torneo Intermedio", re.compile(r"intermedio", re.I)),
    ("competencia", "Torneo Competencia", re.compile(r"competencia", re.I)),
    ("copa_oro", "Copa de Oro", re.compile(r"copa\s*(de\s*)?oro", re.I)),
    ("copa_plata", "Copa de Plata", re.compile(r"copa\s*(de\s*)?plata", re.I)),
    ("copa", "Copa", re.compile(r"\bcopa\b", re.I)),
    ("final", "Torneo Final", re.compile(r"\bfinal\b", re.I)),
    # Las series tienen nombre propio en la fuente y hay que respetarlo: si todas
    # caen en "Fase regular", dos campeonatos distintos quedan con el mismo titulo.
    ("serie_honor", "Serie de Honor", re.compile(r"serie\s*de\s*honor", re.I)),
    ("serie_campeonato", "Serie Campeonato", re.compile(r"serie\s*campeonato", re.I)),
    ("serie_permanencia", "Serie Permanencia", re.compile(r"serie\s*permanencia", re.I)),
    ("regular", "Fase regular", re.compile(r"fase\s*regular", re.I)),
]
TITULO_TORNEO = {t: tit for t, tit, _ in TORNEOS}
TITULO_TORNEO["anual"] = "Tabla anual"
# Los torneos que suman para la tabla anual. Una copa o una liguilla no suma:
# son competencias aparte, no fases del campeonato.
SUMAN_AL_ANUAL = ("apertura", "clausura", "intermedio")

ES_FEMENINO = re.compile(r"\bfem\b|femenin", re.I)
ES_ASCENSO = re.compile(r"2da\s*div|segunda\s*div|divisional\s*[cd]\b|primera\s*divisional", re.I)
# Juveniles B es la divisional inferior. En La Movida aparece como "Juveniles B",
# "B1"/"B2" y con los nombres de las copas de Oro y de Plata.
ES_JUV_B = re.compile(r"juveniles\s*b|\bb1\b|\bb2\b|copa\s*(de\s*)?(oro|plata)", re.I)
ES_JUV_A = re.compile(r"juveniles\s*a|\bjuv\s*a\b", re.I)
# Dentro de Juveniles B hay dos niveles, B1 y B2, y cada uno con sus fases.
# Sin esto, tres campeonatos distintos quedaban con el mismo nombre en el sitio.
SUBDIVISION = re.compile(r"\b(b1|b2)\b", re.I)
FASES = [
    ("Segunda fase", re.compile(r"segunda\s*fase", re.I)),
    ("Liguilla", re.compile(r"liguilla", re.I)),
    ("Primera fase", re.compile(r"primera\s*fase", re.I)),
]
# Una sola letra o numero: "SERIE A" si, "Serie de Honor" no.
SERIE = re.compile(r"serie\s+([a-z0-9])\b", re.I)


def clasificar(nombre):
    """Etiquetas del campeonato, o None si no nos interesa publicarlo."""
    categoria = next((c for c, _, _, p in CATEGORIAS if p.search(nombre)), None)
    if ES_FEMENINO.search(nombre):
        grupo = "femenino"
    elif categoria == "primera":
        grupo = "primera"
    elif ES_ASCENSO.search(nombre):
        grupo = "ascenso"
    elif categoria:
        # Tercera es la Sub 23: va con los juveniles, no con el ascenso.
        grupo = "juveniles"
    else:
        return None
    torneo = next((t for t, _, p in TORNEOS if p.search(nombre)), "otro")
    # Solo se pone A o B cuando el nombre lo dice. Antes se asumia "si no dice B,
    # es A", y eso metia en Juveniles A torneos que no son: la Serie Campeonato y
    # la Serie de Honor juegan con clubes que no estan en el Apertura de A
    # (Durazno FC, Plaza Colonia, San Jacinto, Udelar, Canadian). Si la fuente no
    # lo aclara, queda sin divisional y el sitio lo muestra aparte.
    division = "B" if ES_JUV_B.search(nombre) else ("A" if ES_JUV_A.search(nombre) else None)
    serie = SERIE.search(nombre)
    subdivision = SUBDIVISION.search(nombre)
    fase = next((f for f, p in FASES if p.search(nombre)), None)
    return {"grupo": grupo, "categoria": categoria, "torneo": torneo,
            "division": division, "serie": serie.group(1).upper() if serie else None,
            "subdivision": subdivision.group(1).upper() if subdivision else None,
            "fase": fase}


def titular(etiquetas):
    """El nombre con el que el campeonato se muestra en el sitio."""
    partes = []
    categoria = etiquetas.get("categoria")
    if categoria:
        partes.append(TITULO_CATEGORIA.get(categoria, categoria))
        if etiquetas.get("division") and categoria not in ("primera", "tercera"):
            # B1 y B2 son dos niveles distintos dentro de Juveniles B: si el
            # nombre lo dice, se respeta, porque si no quedan tablas homonimas.
            partes[-1] += " " + (etiquetas.get("subdivision") or etiquetas["division"])
    elif etiquetas["grupo"] == "femenino":
        partes.append("Femenino")
    elif etiquetas["grupo"] == "ascenso":
        partes.append("Ascenso")
    torneo = TITULO_TORNEO.get(etiquetas.get("torneo"), "")
    if etiquetas.get("serie"):
        torneo += " · Serie " + etiquetas["serie"]
    if etiquetas.get("fase"):
        torneo += " · " + etiquetas["fase"]
    return " · ".join([p for p in (" · ".join(partes), torneo) if p])


# ------------------------------------------------------------------------- api
def api(base, ruta, **parametros):
    url = base.rstrip("/") + "/" + ruta
    if parametros:
        url += "?" + urllib.parse.urlencode(parametros, doseq=True)
    pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(pedido, timeout=60) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def texto(valor):
    """SportsPress devuelve titulos como {'rendered': '...'}."""
    if isinstance(valor, dict):
        valor = valor.get("rendered", "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(valor))).strip()


def leer_json(ruta, por_defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def nombres_de_equipos(base, ids, cache):
    """Resuelve id -> nombre, pidiendo solo los que faltan y dejandolos cacheados."""
    faltantes = [str(i) for i in ids if str(i) not in cache]
    for arranque in range(0, len(faltantes), 50):
        tanda = faltantes[arranque:arranque + 50]
        try:
            for equipo in api(base, "teams", include=",".join(tanda), per_page=50):
                cache[str(equipo["id"])] = texto(equipo.get("title"))
        except Exception:
            continue
    if faltantes:
        CACHE_EQUIPOS.parent.mkdir(parents=True, exist_ok=True)
        CACHE_EQUIPOS.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


def anio_de_liga(base, id_liga, cache):
    """De que anio es un campeonato que no lo dice en el nombre.

    Hay campeonatos que se llaman "Sub 17" o "Liga AUF Torneo Intermedio Hector
    Manco Castro SERIE A", sin anio, y la unica forma de saber si son de ahora es
    mirar la fecha de sus partidos. Se pregunta una vez por campeonato y queda
    cacheado: un torneo de 2023 no va a pasar a ser de 2026.
    """
    clave = str(id_liga)
    if clave in cache:
        return cache[clave]
    anio = ""
    try:
        tanda = api(base, "events", leagues=id_liga, per_page=1, orderby="date",
                    order="desc", status="publish")
        if tanda:
            anio = str(tanda[0].get("date", ""))[:4]
    except Exception:
        return ""      # sin cachear: puede ser un error pasajero
    cache[clave] = anio
    return anio


def eventos_de_liga(base, id_liga):
    """Todos los eventos de una liga (el id de liga ya es de una sola temporada)."""
    eventos = []
    for pagina in (1, 2, 3, 4):
        try:
            tanda = api(base, "events", leagues=id_liga, per_page=100, page=pagina,
                        orderby="date", order="asc", status="publish")
        except Exception:
            break
        eventos.extend(tanda)
        if len(tanda) < 100:
            break
    return eventos


# ------------------------------------------------------------------- las tablas
def tabla_de_posiciones(partidos):
    """Calcula la tabla con los partidos ya jugados: PJ G E P GF GC DG Pts."""
    acumulado = {}
    for partido in partidos:
        local, visita = partido["local"], partido["visita"]
        goles_local, goles_visita = partido["goles_local"], partido["goles_visita"]
        if goles_local is None or goles_visita is None:
            continue
        for equipo in (local, visita):
            acumulado.setdefault(equipo, {"equipo": equipo, "pj": 0, "g": 0, "e": 0, "p": 0,
                                          "gf": 0, "gc": 0, "dg": 0, "pts": 0})
        for equipo, favor, contra in ((local, goles_local, goles_visita),
                                      (visita, goles_visita, goles_local)):
            fila = acumulado[equipo]
            fila["pj"] += 1
            fila["gf"] += favor
            fila["gc"] += contra
            fila["dg"] = fila["gf"] - fila["gc"]
            if favor > contra:
                fila["g"] += 1
                fila["pts"] += 3
            elif favor == contra:
                fila["e"] += 1
                fila["pts"] += 1
            else:
                fila["p"] += 1
    return sorted(acumulado.values(), key=lambda f: (-f["pts"], -f["dg"], -f["gf"], f["equipo"]))


def forma_de(partidos, cuantos=5):
    """Los ultimos resultados de cada equipo: V ganó, E empató, D perdió.

    Del mas viejo al mas nuevo, para que se lea como una linea de tiempo. Cada
    uno guarda contra quien y cuanto, asi el sitio lo puede mostrar al pasar el
    mouse en vez de ser cinco cuadraditos de colores sin explicacion.
    """
    historial = {}
    for partido in sorted((p for p in partidos if p["jugado"]), key=lambda p: p["fecha"]):
        lados = ((partido["local"], partido["goles_local"], partido["goles_visita"], partido["visita"]),
                 (partido["visita"], partido["goles_visita"], partido["goles_local"], partido["local"]))
        for equipo, favor, contra, rival in lados:
            signo = "V" if favor > contra else ("E" if favor == contra else "D")
            historial.setdefault(equipo, []).append({
                "r": signo,
                "rival": rival,
                "marcador": str(favor) + "-" + str(contra),
                "fecha": partido["fecha"][:10],
            })
    return {equipo: lista[-cuantos:] for equipo, lista in historial.items()}


def hace_falta_refrescar(guardado, ident, con_movimiento, corte, manana):
    """Si vale la pena volver a pedirle este campeonato a la fuente.

    Se pregunta solo cuando puede haber algo nuevo: un partido que ya se jugo y
    todavia no tiene el resultado cargado, o uno que se juega en las proximas
    horas. Si todo lo jugado ya tiene resultado y lo que viene es para la semana
    que viene, preguntar de nuevo no cambia nada y le cuesta un pedido a un
    servidor que mantienen voluntarios.
    """
    if guardado.get("estado") == "terminado":
        return False
    partidos = guardado.get("partidos") or []
    falta_resultado = any(not p.get("jugado") and p.get("fecha", "") <= corte
                          for p in partidos)
    juega_ya = any(corte <= p.get("fecha", "") <= manana for p in partidos)
    # Si el campeonato tuvo movimiento y no tenemos ni un partido suyo guardado,
    # hay que pedirlo igual: puede ser una fecha nueva que no conociamos.
    sin_futuro = not any(p.get("fecha", "") >= corte for p in partidos)
    return falta_resultado or juega_ya or (sin_futuro and ident in con_movimiento)


def estado_del_torneo(partidos, corte):
    """'terminado', 'en_curso' o 'sin_empezar', mirando los partidos."""
    if not partidos:
        return "sin_empezar"
    jugados = [p for p in partidos if p["jugado"]]
    if not jugados:
        return "sin_empezar"
    pendientes = [p for p in partidos if not p["jugado"] and p["fecha"] >= corte]
    return "en_curso" if pendientes else "terminado"


def partido_desde_evento(evento, cache):
    equipos = evento.get("teams") or []
    if len(equipos) != 2:
        return None
    resultados = evento.get("main_results") or []
    goles = [int(r) if str(r).strip().isdigit() else None for r in resultados[:2]]
    while len(goles) < 2:
        goles.append(None)
    return {
        "fecha": evento.get("date", ""),
        "local": cache.get(str(equipos[0]), "Equipo " + str(equipos[0])),
        "visita": cache.get(str(equipos[1]), "Equipo " + str(equipos[1])),
        "goles_local": goles[0],
        "goles_visita": goles[1],
        "jugado": goles[0] is not None and goles[1] is not None,
        "link_fuente": evento.get("link", ""),
    }


def ficha(etiquetas, nombre, partidos, corte, extra=None):
    """Arma la entrada de un campeonato tal como la consume el sitio."""
    partidos = sorted(partidos, key=lambda p: p["fecha"])
    jugados = [p for p in partidos if p["jugado"]]
    forma = forma_de(jugados)
    entrada = dict(etiquetas)
    entrada.update({
        "nombre": nombre,
        "titulo": titular(etiquetas),
        "titulo_categoria": TITULO_CATEGORIA.get(etiquetas.get("categoria") or ""),
        "estado": estado_del_torneo(partidos, corte),
        "orden_categoria": ORDEN_CATEGORIA.get(etiquetas.get("categoria"), 999),
        "tabla": [dict(f, forma=forma.get(f["equipo"], []))
                  for f in tabla_de_posiciones(jugados)],
        "ultimos_resultados": list(reversed(jugados))[:12],
        # Solo los que todavia no se jugaron: un partido viejo sin resultado cargado
        # no es "proximo", es un resultado que la fuente no publico.
        "proximos_partidos": [p for p in partidos if not p["jugado"] and p["fecha"] >= corte][:12],
        "jugados": len(jugados),
        "programados": len(partidos),
    })
    if extra:
        entrada.update(extra)
    return entrada


def anuales(fichas, corte):
    """Las tablas anuales, que la fuente no tiene: se suman los torneos del anio.

    Dos niveles: la anual de cada categoria (Sub 17 A, Primera, Tercera) y la
    anual general de los juveniles, que suma todas las categorias juntas.
    """
    calculadas = []
    por_clave = {}
    for f in fichas:
        if f["torneo"] not in SUMAN_AL_ANUAL:
            continue
        clave = (f["grupo"], f.get("categoria"), f.get("division"))
        por_clave.setdefault(clave, []).append(f)

    for (grupo, categoria, division), grupo_fichas in por_clave.items():
        if len(grupo_fichas) < 2:
            continue   # con un solo torneo la anual seria igual a ese torneo
        partidos = [p for f in grupo_fichas for p in f["_partidos"]]
        etiquetas = {"grupo": grupo, "categoria": categoria, "division": division,
                     "torneo": "anual", "serie": None}
        nombres = sorted({TITULO_TORNEO.get(f["torneo"], f["torneo"]) for f in grupo_fichas})
        calculadas.append(ficha(etiquetas, titular(etiquetas), partidos, corte, {
            "calculada": True,
            "suma_de": nombres,
            "explicacion": "Suma de " + ", ".join(nombres) + " de " + str(datetime.now().year) + ".",
        }))

    # La general de juveniles: todas las categorias de una misma division.
    for division in ("A", "B"):
        de_esa = [f for f in fichas
                  if f["grupo"] == "juveniles" and f.get("division") == division
                  and f["torneo"] in SUMAN_AL_ANUAL]
        categorias = {f.get("categoria") for f in de_esa}
        if len(categorias) < 2:
            continue
        partidos = [p for f in de_esa for p in f["_partidos"]]
        etiquetas = {"grupo": "juveniles", "categoria": None, "division": division,
                     "torneo": "anual", "serie": None}
        titulo = "Juveniles " + division + " · Tabla anual general"
        calculadas.append(ficha(etiquetas, titulo, partidos, corte, {
            "titulo": titulo,
            "general": True,
            "calculada": True,
            "suma_de": sorted(TITULO_CATEGORIA.get(c, c or "?") for c in categorias),
            "explicacion": ("Suma de todas las categorías de Juveniles " + division +
                            ": cada club acumula los puntos de sus cinco equipos."),
            "orden_categoria": 5,
        }))
    return calculadas


# ------------------------------------------------------------------------ main
def main():
    fuentes = leer_json(FUENTES, {})
    config = fuentes.get("datos", {}).get("juveniles", {})
    if not config.get("activo", False):
        print("la fuente de datos esta desactivada en fuentes.json")
        return
    base = config["api"]
    solo_listar = "--listar" in sys.argv

    ahora = datetime.now(timezone.utc)
    anio = str(ahora.year)
    corte = ahora.strftime("%Y-%m-%dT%H:%M:%S")
    desde = (ahora - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
    hasta = (ahora + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")

    # 1) Todos los campeonatos de la fuente
    ligas = {}
    for pagina in (1, 2, 3, 4):
        try:
            tanda = api(base, "leagues", per_page=100, page=pagina)
        except Exception as error:
            print("  !! no se pudo listar campeonatos: " + str(error))
            break
        for liga in tanda:
            ligas[liga["id"]] = texto(liga.get("name") or liga.get("title"))
        if len(tanda) < 100:
            break

    # 2) Cuales nos importan: los del anio corriente por nombre, mas los que
    #    tuvieron partidos hace poco (hay campeonatos sin anio en el nombre).
    eventos_recientes = []
    for filtro in ({"after": desde, "before": corte, "order": "desc"},
                   {"after": corte, "before": hasta, "order": "asc"}):
        for pagina in (1, 2, 3):
            try:
                tanda = api(base, "events", per_page=100, page=pagina, orderby="date",
                            status="publish", **filtro)
            except Exception:
                break
            eventos_recientes.extend(tanda)
            if len(tanda) < 100:
                break
    con_movimiento = {i for e in eventos_recientes for i in (e.get("leagues") or [])}

    cache_anios = leer_json(CACHE_ANIOS, {})
    vigentes, preguntados = {}, 0
    for ident, nombre in sorted(ligas.items()):
        etiquetas = clasificar(nombre)
        if not etiquetas:
            continue
        if anio in nombre:
            vigentes[ident] = (nombre, etiquetas)
            continue
        if re.search(r"\b20(1\d|2[0-9])\b", nombre):
            continue            # dice otro anio en el nombre: no va
        if ident in con_movimiento:
            vigentes[ident] = (nombre, etiquetas)
            continue
        # No dice anio y no tuvo movimiento: hay que preguntarle a la fuente.
        if str(ident) not in cache_anios:
            preguntados += 1
        if anio_de_liga(base, ident, cache_anios) == anio:
            vigentes[ident] = (nombre, etiquetas)
    CACHE_ANIOS.write_text(json.dumps(cache_anios, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(str(len(ligas)) + " campeonatos en la fuente, " + str(len(vigentes)) + " vigentes" +
          (" (" + str(preguntados) + " con la fecha preguntada)" if preguntados else ""))

    if solo_listar:
        for ident, (nombre, e) in sorted(vigentes.items(), key=lambda x: x[1][0]):
            print("  %6d  %-46s %-9s %-8s %-11s %s" % (
                ident, nombre[:46], e["grupo"], e["categoria"] or "-", e["torneo"],
                e["division"] or "-"))
        return

    # 3) Los partidos.
    #
    # La Movida es un grupo de voluntarios y este programa corre cada 20 minutos:
    # pedirle de nuevo todos los campeonatos en cada corrida eran 3.384 pedidos
    # por dia a su servidor, por nada. Los partidos quedan guardados y solo se
    # vuelve a pedir un campeonato cuando tuvo o va a tener partidos en estos
    # dias. El resto sale del archivo, que es exactamente lo mismo pero gratis.
    cache_equipos = leer_json(CACHE_EQUIPOS, {})
    cache_partidos = leer_json(CACHE_PARTIDOS, {})
    # "Con movimiento" para decidir si refrescar es una ventana corta: lo que
    # jugo o juega en estos dias. Con la ventana larga (60 dias) calificaba casi
    # todo y no se ahorraba nada. No cuesta pedidos: las fechas ya las tenemos.
    cerca_desde = (ahora - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    cerca_hasta = (ahora + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")
    con_movimiento_cerca = {i for e in eventos_recientes
                            if cerca_desde <= str(e.get("date", "")) <= cerca_hasta
                            for i in (e.get("leagues") or [])}
    manana = (ahora + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    crudos, desde_cache, pedidos = {}, 0, 0
    for ident in sorted(vigentes):
        guardado = cache_partidos.get(str(ident))
        if guardado and guardado.get("partidos"):
            if hace_falta_refrescar(guardado, ident, con_movimiento_cerca, corte, manana):
                pass
            else:
                crudos[ident] = guardado["partidos"]
                desde_cache += 1
                continue
        eventos = eventos_de_liga(base, ident)
        ids = {str(i) for e in eventos for i in (e.get("teams") or [])}
        cache_equipos = nombres_de_equipos(base, ids, cache_equipos)
        crudos[ident] = [p for p in (partido_desde_evento(e, cache_equipos) for e in eventos) if p]
        pedidos += 1
    print(str(len(crudos)) + " campeonatos con partidos: " + str(desde_cache) +
          " de archivo, " + str(pedidos) + " pedidos a la fuente")

    # 4) Las fichas, y el cache de los que quedaron terminados
    fichas = []
    for ident, partidos in crudos.items():
        nombre, etiquetas = vigentes[ident]
        f = ficha(etiquetas, nombre, partidos, corte, {"id": ident})
        f["_partidos"] = partidos
        fichas.append(f)
        if f["jugados"] or f["programados"]:
            cache_partidos[str(ident)] = {"estado": f["estado"], "nombre": nombre,
                                          "partidos": partidos}
    CACHE_PARTIDOS.write_text(json.dumps(cache_partidos, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    # 5) Las anuales calculadas
    fichas += anuales(fichas, corte)

    # Los campeonatos sin un solo partido jugado no se publican: una tabla vacia
    # no le sirve a nadie.
    fichas = [f for f in fichas if f["tabla"]]
    for f in fichas:
        f.pop("_partidos", None)

    orden_torneo = {"anual": 0, "clausura": 1, "intermedio": 2, "apertura": 3}
    fichas.sort(key=lambda f: (f["orden_categoria"], orden_torneo.get(f["torneo"], 9),
                               f.get("serie") or "", f["nombre"]))

    salida = {
        "generado": ahora.isoformat(timespec="seconds"),
        "credito": config.get("credito_obligatorio", ""),
        "ligas": fichas,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    print(str(len(fichas)) + " tablas -> " + str(SALIDA.relative_to(RAIZ)))
    for f in fichas:
        puntero = f["tabla"][0] if f["tabla"] else None
        marca = {"terminado": "[terminado]", "en_curso": "[en curso] ", "sin_empezar": "[sin jugar]"}
        print("  " + marca.get(f["estado"], "") + " " + f["titulo"][:46].ljust(48) +
              ("lidera " + puntero["equipo"] + " (" + str(puntero["pts"]) + ")" if puntero else ""))


if __name__ == "__main__":
    main()
