# -*- coding: utf-8 -*-
"""Trae partidos de juveniles y calcula las tablas de posiciones.

Uso:  python scripts/datos.py

Lee la API publica de La Movida Online (SportsPress). Los resultados son hechos
(no se copia texto de nadie) y las tablas se calculan aca a partir de los
partidos jugados. El credito a la fuente va en el JSON y tiene que mostrarse
en el sitio.
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fuentes.json"
DATOS = RAIZ / "datos"
SALIDA = DATOS / "juveniles.json"
CACHE_EQUIPOS = DATOS / "equipos.json"
AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
# Clasificacion de campeonatos por nombre. El orden importa: gana el primero que
# machea, por eso femenino va antes que juveniles (hay juveniles femeninas).
GRUPOS = [
    ("femenino", "Fútbol femenino", re.compile(r"\bfem\b|femenino", re.I)),
    ("juveniles", "Juveniles", re.compile(r"\b(juv|sub\s?-?\d{2}|s1[1-9])\b", re.I)),
    ("ascenso", "Segunda, Tercera y D", re.compile(r"2da|segunda|3ra|tercera|divisional\s*d|intermedio", re.I)),
]


def clasificar(nombre):
    for clave, _, patron in GRUPOS:
        if patron.search(nombre):
            return clave
    return None


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


def partidos_de_liga(base, id_liga):
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


def main():
    fuentes = json.loads(FUENTES.read_text(encoding="utf-8"))
    config = fuentes.get("datos", {}).get("juveniles", {})
    if not config.get("activo", False):
        print("juveniles desactivado en fuentes.json")
        return
    base = config["api"]

    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    hasta = (ahora + timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%S")
    corte = ahora.strftime("%Y-%m-%dT%H:%M:%S")

    ligas = {}
    for pagina in (1, 2):
        try:
            for liga in api(base, "leagues", per_page=100, page=pagina):
                ligas[liga["id"]] = texto(liga.get("name") or liga.get("title"))
        except Exception:
            break
    clasificadas = {ident: (clasificar(nombre), nombre) for ident, nombre in ligas.items()}
    clasificadas = {i: v for i, v in clasificadas.items() if v[0]}
    print(str(len(ligas)) + " ligas, " + str(len(clasificadas)) + " clasificadas")

    eventos = []
    for filtro in ({"before": corte, "after": desde, "order": "desc"},
                   {"after": corte, "before": hasta, "order": "asc"}):
        for pagina in (1, 2):
            try:
                tanda = api(base, "events", per_page=100, page=pagina, orderby="date",
                            status="publish", **filtro)
            except Exception as error:
                print("  !! no se pudieron traer eventos: " + str(error))
                break
            eventos.extend(tanda)
            if len(tanda) < 100:
                break

    # Las ligas con partidos en la ventana son las que estan en curso; de esas se
    # trae el torneo completo, porque la tabla necesita todas las fechas jugadas.
    en_curso = {id_liga for evento in eventos for id_liga in (evento.get("leagues") or [])
                if id_liga in clasificadas}
    print(str(len(en_curso)) + " campeonatos con movimiento; trayendo torneos completos")
    completos = []
    for id_liga in sorted(en_curso):
        completos.extend(partidos_de_liga(base, id_liga))
    eventos = completos or eventos

    try:
        cache = json.loads(CACHE_EQUIPOS.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    ids_equipos = {str(i) for e in eventos for i in (e.get("teams") or [])}
    cache = nombres_de_equipos(base, ids_equipos, cache)

    por_liga = {}
    for evento in eventos:
        for id_liga in (evento.get("leagues") or []):
            if id_liga not in en_curso:
                continue
            equipos = evento.get("teams") or []
            if len(equipos) != 2:
                continue
            resultados = evento.get("main_results") or []
            goles = [int(r) if str(r).strip().isdigit() else None for r in resultados[:2]]
            while len(goles) < 2:
                goles.append(None)
            partido = {
                "fecha": evento.get("date", ""),
                "local": cache.get(str(equipos[0]), "Equipo " + str(equipos[0])),
                "visita": cache.get(str(equipos[1]), "Equipo " + str(equipos[1])),
                "goles_local": goles[0],
                "goles_visita": goles[1],
                "jugado": goles[0] is not None and goles[1] is not None,
                "link_fuente": evento.get("link", ""),
            }
            por_liga.setdefault(id_liga, []).append(partido)

    salida = {
        "generado": ahora.isoformat(timespec="seconds"),
        "credito": config.get("credito_obligatorio", ""),
        "ligas": [],
    }
    for id_liga, partidos in sorted(por_liga.items(), key=lambda par: clasificadas[par[0]][1]):
        partidos.sort(key=lambda p: p["fecha"])
        jugados = [p for p in partidos if p["jugado"]]
        salida["ligas"].append({
            "id": id_liga,
            "grupo": clasificadas[id_liga][0],
            "nombre": clasificadas[id_liga][1],
            "tabla": tabla_de_posiciones(jugados),
            "ultimos_resultados": list(reversed(jugados))[:12],
            # Solo los que todavia no se jugaron: un partido viejo sin resultado cargado
            # no es "proximo", es un resultado que la fuente no publico.
            "proximos_partidos": [p for p in partidos
                                  if not p["jugado"] and p["fecha"] >= corte][:12],
        })

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(l["ultimos_resultados"]) for l in salida["ligas"])
    print(str(len(salida["ligas"])) + " ligas con movimiento, " + str(total) +
          " resultados recientes -> " + str(SALIDA.relative_to(RAIZ)))
    salida["grupos"] = [{"clave": c, "titulo": tit} for c, tit, _ in GRUPOS]
    for liga in salida["ligas"][:8]:
        puntero = liga["tabla"][0] if liga["tabla"] else None
        print("  " + liga["grupo"][:9].ljust(11) + liga["nombre"][:40].ljust(42) +
              ("lidera " + puntero["equipo"] + " (" + str(puntero["pts"]) + " pts)" if puntero else "sin partidos jugados"))


if __name__ == "__main__":
    main()
