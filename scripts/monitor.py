# -*- coding: utf-8 -*-
"""Vigila canales de YouTube y baja el transcripto de los videos nuevos.

Uso:  python scripts/monitor.py            (una pasada)
      python scripts/monitor.py --listar   (muestra que hay nuevo, sin bajar nada)

No usa API key ni cuenta: lee el RSS publico de cada canal. Solo necesita yt-dlp.
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fuentes.json"
DATOS = RAIZ / "datos"
TRANSCRIPCIONES = DATOS / "transcripciones"
ESTADO = DATOS / "estado.json"
CANALES = DATOS / "canales.json"
PENDIENTES = DATOS / "hallazgos" / "pendientes.json"
AGENTE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
ENTIDADES = {"amp": "&", "quot": '"', "apos": "'", "#39": "'", "lt": "<", "gt": ">"}
# La consola de Windows no es UTF-8: imprimir un titulo con un caracter raro
# tiraba todo el script abajo. Que reemplace el caracter y siga de largo.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def leer_json(ruta, por_defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def escribir_json(ruta, dato):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False, indent=2), encoding="utf-8")


def id_de_canal(handle, cache):
    """Resuelve @handle -> channel_id (UC...) una sola vez y lo deja cacheado."""
    if handle in cache:
        return cache[handle]
    pedido = urllib.request.Request("https://www.youtube.com/" + handle,
                                    headers={"User-Agent": AGENTE})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as respuesta:
            html = respuesta.read().decode("utf-8", "replace")
    except Exception:
        return None
    hallado = re.search(r'"(?:externalId|channelId)":"(UC[A-Za-z0-9_-]{20,})"', html)
    ident = hallado.group(1) if hallado else None
    if ident:
        cache[handle] = ident
        escribir_json(CANALES, cache)
    return ident


def videos_del_canal(id_canal, cuantos=8):
    """Ultimos videos del canal, el mas nuevo primero.

    El feed RSS de YouTube quedo fuera de servicio (404 para cualquier canal),
    asi que la deteccion va por yt-dlp.
    """
    salida = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--playlist-end", str(cuantos),
         "--extractor-args", "youtube:lang=es",
         "--print", "%(id)s\t%(duration)s\t%(title)s",
         "https://www.youtube.com/channel/" + id_canal + "/videos"],
        capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
    videos = []
    for linea in salida.stdout.splitlines():
        partes = linea.split("\t")
        if len(partes) < 3 or len(partes[0]) != 11:
            continue
        videos.append({
            "id": partes[0],
            "duracion": int(partes[1]) if partes[1].isdigit() else 0,
            "titulo": partes[2].strip(),
        })
    return videos


def limpiar_vtt(ruta):
    """Convierte los subtitulos automaticos en texto corrido con marcas de tiempo.

    YouTube repite cada linea agregandole palabras al final, asi que el texto se
    arma pegando unicamente la parte nueva de cada bloque.
    """
    bruto = ruta.read_text(encoding="utf-8", errors="replace")
    bloques = re.findall(r"(\d\d:\d\d:\d\d)\.\d{3} --> .*?\n(.*?)(?=\n\n|\Z)", bruto, re.S)
    partes = []
    acumulado = ""
    for marca, cuerpo in bloques:
        linea = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cuerpo).replace("\n", " ")).strip()
        if not linea or acumulado.endswith(linea):
            continue
        solape = 0
        for largo in range(min(len(linea), 300), 0, -1):
            if acumulado.endswith(linea[:largo]):
                solape = largo
                break
        nuevo = linea[solape:].strip()
        if not nuevo:
            continue
        acumulado = (acumulado + " " + nuevo).strip()
        partes.append((marca, nuevo))

    parrafos = []
    buffer = []
    marca_inicio = None
    palabras = 0
    for marca, texto in partes:
        if marca_inicio is None:
            marca_inicio = marca
        buffer.append(texto)
        palabras += len(texto.split())
        if palabras >= 45:
            parrafos.append("[" + marca_inicio + "] " + " ".join(buffer))
            buffer, marca_inicio, palabras = [], None, 0
    if buffer:
        parrafos.append("[" + str(marca_inicio) + "] " + " ".join(buffer))
    return "\n\n".join(parrafos)


def bajar_transcripto(video_id, idiomas, destino_tmp):
    """Devuelve (archivo_vtt, fecha_de_subida). El archivo es None si no hay subtitulos."""
    proceso = subprocess.run(
        ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
         "--sub-langs", ",".join(idiomas), "--sub-format", "vtt",
         "--extractor-args", "youtube:lang=es",
         "--print", "%(upload_date)s", "--no-simulate",
         "-o", str(destino_tmp / "%(id)s"),
         "https://www.youtube.com/watch?v=" + video_id],
        capture_output=True, text=True, timeout=300, encoding="utf-8", errors="replace")
    crudo = next((l.strip() for l in proceso.stdout.splitlines()
                  if len(l.strip()) == 8 and l.strip().isdigit()), "")
    fecha = (crudo[:4] + "-" + crudo[4:6] + "-" + crudo[6:]) if crudo \
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for idioma in idiomas:
        candidato = destino_tmp / (video_id + "." + idioma + ".vtt")
        if candidato.exists():
            return candidato, fecha
    return next(iter(destino_tmp.glob(video_id + ".*.vtt")), None), fecha


def main():
    fuentes = leer_json(FUENTES, {})
    parametros = fuentes.get("parametros", {})
    idiomas = parametros.get("idiomas_subtitulos", ["es"])
    estado = leer_json(ESTADO, {"vistos": {}})
    cache_canales = leer_json(CANALES, {})
    solo_listar = "--listar" in sys.argv

    tmp = DATOS / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    TRANSCRIPCIONES.mkdir(parents=True, exist_ok=True)
    pendientes = leer_json(PENDIENTES, [])
    nuevos_total = 0

    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None

    for canal in fuentes.get("youtube", []):
        if not canal.get("activo", True):
            continue
        if solo and solo.lower() not in (canal["handle"].lower(), canal["nombre"].lower()):
            continue
        handle = canal["handle"]
        nombre = canal["nombre"]
        ident = id_de_canal(handle, cache_canales)
        if not ident:
            print("  !! " + nombre + " (" + handle + "): no se pudo resolver el canal")
            continue
        try:
            videos = videos_del_canal(ident, parametros.get("videos_por_canal", 6))
        except Exception as error:
            print("  !! " + nombre + ": no se pudo listar el canal (" + str(error) + ")")
            continue
        # Hay videos que aparecen en dos canales (colaboraciones): si ya se bajo
        # por otro canal, no se vuelve a bajar ni se duplica la nota.
        vistos = set(estado["vistos"].get(handle, []))
        vistos |= {v for ids in estado["vistos"].values() for v in ids}
        minimo = parametros.get("duracion_minima_seg", 0)
        maximo = parametros.get("duracion_maxima_seg", 99999)
        nuevos = [v for v in videos if v["id"] not in vistos]
        print("  " + nombre + ": " + str(len(videos)) + " listados, " + str(len(nuevos)) + " nuevos")
        if solo_listar:
            for video in nuevos:
                print("     - " + str(video["duracion"] // 60) + " min  " + video["titulo"][:70])
            continue
        for video in nuevos:
            if not minimo <= video["duracion"] <= maximo:
                estado["vistos"].setdefault(handle, []).append(video["id"])
                print("     - fuera de rango (" + str(video["duracion"]) + "s): " + video["titulo"][:50])
                continue
            vtt, fecha = bajar_transcripto(video["id"], idiomas, tmp)
            estado["vistos"].setdefault(handle, []).append(video["id"])
            if not vtt:
                print("     - sin subtitulos: " + video["titulo"][:60])
                continue
            # Un video de hace un mes no es noticia: se marca visto y se sigue.
            dias = parametros.get("dias_maximos", 7)
            limite = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
            if fecha < limite:
                print("     - viejo (" + fecha + "): " + video["titulo"][:50])
                continue
            texto = limpiar_vtt(vtt)
            archivo = TRANSCRIPCIONES / (fecha + "_" + handle.lstrip("@") + "_" + video["id"] + ".txt")
            archivo.write_text(
                "FUENTE: " + nombre + " (" + handle + ")\n"
                "VIDEO: https://www.youtube.com/watch?v=" + video["id"] + "\n"
                "TITULO: " + video["titulo"] + "\n"
                "PUBLICADO: " + fecha + "\n"
                "PALABRAS: " + str(len(texto.split())) + "\n\n" + texto + "\n",
                encoding="utf-8")
            for sobrante in tmp.glob(video["id"] + ".*"):
                sobrante.unlink()
            pendientes.append({
                "transcripto": str(archivo.relative_to(RAIZ)).replace("\\", "/"),
                "fuente": nombre,
                "titulo": video["titulo"],
                "video": "https://www.youtube.com/watch?v=" + video["id"],
                "publicado": fecha,
                "estado": "sin_revisar",
            })
            nuevos_total += 1
            print("     + " + archivo.name + "  (" + str(len(texto.split())) + " palabras)")

    if not solo_listar:
        for handle in estado["vistos"]:
            estado["vistos"][handle] = estado["vistos"][handle][-200:]
        estado["ultima_corrida"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        escribir_json(ESTADO, estado)
        escribir_json(PENDIENTES, pendientes)
        sin_revisar = sum(1 for p in pendientes if p["estado"] == "sin_revisar")
        print("\n" + str(nuevos_total) + " transcripto(s) nuevo(s). Pendientes de redaccion: " + str(sin_revisar))


if __name__ == "__main__":
    main()
