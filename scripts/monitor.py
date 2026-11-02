# -*- coding: utf-8 -*-
"""Vigila canales de YouTube y baja el transcripto de los videos nuevos.

Uso:  python scripts/monitor.py            (una pasada)
      python scripts/monitor.py --listar   (muestra que hay nuevo, sin bajar nada)

No usa API key ni cuenta: lee el RSS publico de cada canal. Solo necesita yt-dlp.
"""
import json
import os
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
         # YouTube corta por abuso si se le pide todo de golpe. Un segundo de
         # pausa por pedido es barato y evita el 429.
         "--sleep-requests", "1", "--extractor-retries", "3",
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

    return agrupar(partes)


def agrupar(partes):
    """[(marca, texto)] -> parrafos de unas 45 palabras, cada uno con su minuto.

    Las marcas son lo que despues el sitio convierte en links al segundo exacto,
    asi que tienen que quedar pegadas al texto que corresponde.
    """
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
    """Devuelve (archivo_vtt, fecha_de_subida, fallo).

    `fallo` distingue dos cosas que antes se confundian y costaban notas: que el
    video no tenga subtitulos (no hay nada que hacer) y que YouTube no nos los
    haya querido dar en este momento, por ejemplo con un 429 por pedir demasiado
    rapido. En el segundo caso el video se reintenta mas tarde.
    """
    proceso = subprocess.run(
        ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
         "--sub-langs", ",".join(idiomas), "--sub-format", "vtt",
         "--extractor-args", "youtube:lang=es",
         # Las mismas pausas y reintentos que al listar: el 429 aparece aca.
         "--sleep-requests", "1", "--sleep-subtitles", "3",
         "--retries", "5", "--extractor-retries", "3", "--retry-sleep", "5",
         "--print", "%(upload_date)s", "--no-simulate",
         "-o", str(destino_tmp / "%(id)s"),
         "https://www.youtube.com/watch?v=" + video_id],
        capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
    crudo = next((l.strip() for l in proceso.stdout.splitlines()
                  if len(l.strip()) == 8 and l.strip().isdigit()), "")
    fecha = (crudo[:4] + "-" + crudo[4:6] + "-" + crudo[6:]) if crudo \
        else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for idioma in idiomas:
        candidato = destino_tmp / (video_id + "." + idioma + ".vtt")
        if candidato.exists():
            return candidato, fecha, False
    hallado = next(iter(destino_tmp.glob(video_id + ".*.vtt")), None)
    if hallado:
        return hallado, fecha, False
    salida = (proceso.stderr or "") + "\n" + (proceso.stdout or "")
    errores = [l.strip() for l in salida.splitlines() if "ERROR" in l]
    if errores:
        print("        (YouTube no dio los subtitulos: " + errores[0][:160] + ")")
    return None, fecha, bool(errores)


# Vocabulario del fútbol uruguayo: Whisper escucha mejor los nombres propios si
# se le adelanta de que va a hablar el audio. Sin esto, "Ruglio" sale "Rulio".
PISTA = ("Futbol uruguayo. Penarol, Nacional, Danubio, Defensor Sporting, Liverpool, "
         "Montevideo Wanderers, Racing, Cerro, Rampla Juniors, Progreso, Boston River, "
         "Deportivo Maldonado, Cerro Largo, Juventud de Las Piedras, River Plate, "
         "Plaza Colonia, Miramar Misiones, Bella Vista, Albion, Oriental, Torque. "
         "AUF, Tenfield, Campeon del Siglo, Gran Parque Central, Estadio Centenario, "
         "Torneo Apertura, Torneo Clausura, Copa Uruguay, tabla anual. "
         "Diego Aguirre, Ignacio Ruglio, Maxi Gomez, Luciano Rodriguez, Sebastian Coates.")

_MODELO_WHISPER = [None]


def modelo_whisper(nombre):
    """Se carga una sola vez por corrida: arrancarlo cuesta mas que usarlo."""
    if _MODELO_WHISPER[0] is None:
        from faster_whisper import WhisperModel
        print("        cargando el modelo " + nombre + " (la primera vez lo baja)")
        # int8 en procesador: es lo que hace que esto sea viable sin tarjeta de video.
        _MODELO_WHISPER[0] = WhisperModel(nombre, device="cpu", compute_type="int8")
    return _MODELO_WHISPER[0]


def bajar_audio(video_id, tmp):
    """Baja el audio tal como viene, sin reconvertir: asi no necesita ffmpeg.

    Devuelve (archivo, motivo). Si el archivo es None, el motivo trae lo ultimo
    que dijo yt-dlp, que es lo unico que sirve para entender por que fallo.
    """
    proceso = subprocess.run(
        ["yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
         "--no-playlist", "--retries", "3",
         "-o", str(tmp / (video_id + ".audio.%(ext)s")),
         "https://www.youtube.com/watch?v=" + video_id],
        capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace")
    # Un .part es una bajada cortada: pasarselo a Whisper daria texto trunco.
    completos = [a for a in tmp.glob(video_id + ".audio.*")
                 if a.suffix not in (".part", ".ytdl") and a.stat().st_size > 0]
    if completos:
        return completos[0], ""
    for basura in tmp.glob(video_id + ".audio.*"):
        basura.unlink()
    salida = (proceso.stderr or "") + "\n" + (proceso.stdout or "")
    lineas = [l.strip() for l in salida.splitlines() if l.strip()]
    # Lo que explica la falla son las lineas de ERROR o WARNING; el resto es el
    # relato de lo que fue intentando, que no sirve para nada.
    utiles = [l for l in lineas if "ERROR" in l or "WARNING" in l or "Sign in" in l]
    return None, (" | ".join(utiles[:3]) if utiles
                  else (" | ".join(lineas[-3:]) if lineas else "yt-dlp no dijo nada"))


def whisper_disponible():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def transcribir_audio(video_id, tmp, ajustes):
    """Pasa el audio a texto con marcas de tiempo. Devuelve None si no se pudo.

    Esto corre en el procesador y no cuesta plata: no es la API de Claude. Lo que
    si cuesta es el transcripto que sale de aca, porque despues lo lee el filtro.
    """
    audio = None
    try:
        audio, motivo = bajar_audio(video_id, tmp)
        if not audio:
            print("        !! no se pudo bajar el audio: " + motivo[:300])
            return None
        modelo = modelo_whisper(ajustes.get("modelo", "small"))
        segmentos, _ = modelo.transcribe(
            str(audio), language="es", vad_filter=True, initial_prompt=PISTA)
        partes = []
        for seg in segmentos:
            frase = (seg.text or "").strip()
            if not frase:
                continue
            total = int(seg.start)
            marca = "%02d:%02d:%02d" % (total // 3600, total % 3600 // 60, total % 60)
            partes.append((marca, frase))
        if not partes:
            print("        !! el audio no dio texto")
            return None
        return agrupar(partes)
    except Exception as error:
        print("        !! Whisper fallo: " + str(error))
        return None
    finally:
        if audio and audio.exists():
            audio.unlink()


def reintentar(estado, handle, video, parametros, contar=True):
    """Desmarca el video para que la proxima corrida lo intente de nuevo.

    YouTube tarda en generar los subtitulos automaticos, y ademas corta por
    abuso: un video que hoy no los da puede darlos en la corrida siguiente.
    Tirarlo en el primer intento es perder la nota. Despues de unos cuantos
    intentos se da por perdido, asi no queda reintentando para siempre.

    `contar=False` es para cuando el video se posterga por decision nuestra
    (se lleno el cupo de la corrida): eso no es un intento fallido.
    """
    if contar:
        tope = parametros.get("reintentos_sin_subtitulos", 6)
        cuenta = estado["reintentos"].get(video["id"], 0) + 1
        if cuenta > tope:
            estado["reintentos"].pop(video["id"], None)
            return False
        estado["reintentos"][video["id"]] = cuenta
    ya_vistos = estado["vistos"].setdefault(handle, [])
    if ya_vistos and ya_vistos[-1] == video["id"]:
        ya_vistos.pop()
    return True


def main():
    fuentes = leer_json(FUENTES, {})
    parametros = fuentes.get("parametros", {})
    idiomas = parametros.get("idiomas_subtitulos", ["es"])
    whisper = fuentes.get("whisper", {})
    cupo = parametros.get("transcriptos_por_corrida", 8)
    bajados = 0
    transcritos_whisper = 0   # intentos de esta corrida (es lo que topea)
    hechos_whisper = 0        # los que efectivamente salieron
    if whisper.get("activo") and whisper.get("saltear_en_la_nube", True) and os.environ.get("CI"):
        # YouTube rechaza las bajadas de audio desde las IPs de los centros de
        # datos ("Sign in to confirm you're not a bot"), asi que en la nube
        # intentarlo es perder minutos. En la maquina de casa funciona.
        print("  (Whisper apagado en la nube: YouTube no deja bajar audio desde ahi)")
        whisper = dict(whisper, activo=False)
    if whisper.get("activo") and not whisper_disponible():
        # Pasa en la maquina de casa, donde no hace falta instalarlo: el que
        # transcribe es GitHub. Se apaga y los videos sin subtitulos se saltean,
        # igual que antes, en vez de quedar marcados como procesados.
        print("  (faster-whisper no esta instalado aca: los videos sin subtitulos se saltean)")
        whisper = dict(whisper, activo=False)
    estado = leer_json(ESTADO, {"vistos": {}})
    estado.setdefault("reintentos", {})
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
            # Cupo por corrida. Pedirle a YouTube los subtitulos de veinte videos
            # seguidos termina en 429 y perdemos todos; de a pocos por hora no.
            if bajados >= cupo:
                estado["vistos"].setdefault(handle, []).append(video["id"])
                reintentar(estado, handle, video, parametros, contar=False)
                print("     - cupo de la corrida lleno, queda para la proxima: " +
                      video["titulo"][:45])
                continue
            bajados += 1
            vtt, fecha, fallo_subs = bajar_transcripto(video["id"], idiomas, tmp)
            estado["vistos"].setdefault(handle, []).append(video["id"])
            # Un video de hace un mes no es noticia: se marca visto y se sigue.
            # Va antes que Whisper para no gastar minutos de maquina al aire.
            dias = parametros.get("dias_maximos", 7)
            limite = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
            if fecha < limite:
                print("     - viejo (" + fecha + "): " + video["titulo"][:50])
                continue
            por_whisper = False
            if not vtt and fallo_subs:
                if reintentar(estado, handle, video, parametros):
                    print("     - YouTube no dio los subtitulos ahora, se reintenta: " +
                          video["titulo"][:45])
                else:
                    print("     - sin subtitulos despues de varios intentos: " +
                          video["titulo"][:50])
                continue
            if vtt:
                texto = limpiar_vtt(vtt)
            else:
                # No todos los canales dejan subtitulos automaticos, y justo ahi
                # suele estar la nota. Se escucha el audio y se escribe solo.
                tope = whisper.get("maximo_por_corrida", 2)
                if not whisper.get("activo"):
                    if reintentar(estado, handle, video, parametros):
                        print("     - sin subtitulos todavia, se reintenta: " + video["titulo"][:48])
                    else:
                        print("     - sin subtitulos: " + video["titulo"][:60])
                    continue
                if transcritos_whisper >= tope:
                    print("     - sin subtitulos, queda para la proxima corrida (ya van " +
                          str(tope) + "): " + video["titulo"][:50])
                    # Se lo saca de los vistos para que la proxima corrida lo agarre.
                    ya_vistos = estado["vistos"].setdefault(handle, [])
                    if ya_vistos and ya_vistos[-1] == video["id"]:
                        ya_vistos.pop()
                    continue
                if video["duracion"] > whisper.get("duracion_maxima_seg", 3600):
                    print("     - sin subtitulos y muy largo para transcribir (" +
                          str(video["duracion"] // 60) + " min): " + video["titulo"][:50])
                    continue
                print("     ~ sin subtitulos, escuchando el audio (" +
                      str(video["duracion"] // 60) + " min): " + video["titulo"][:50])
                # El tope cuenta intentos, no exitos: bajar el audio y transcribir
                # lleva minutos, y una corrida tiene que terminar aunque falle todo.
                transcritos_whisper += 1
                texto = transcribir_audio(video["id"], tmp, whisper)
                if not texto:
                    reintentar(estado, handle, video, parametros)
                    continue
                hechos_whisper += 1
                por_whisper = True
            archivo = TRANSCRIPCIONES / (fecha + "_" + handle.lstrip("@") + "_" + video["id"] + ".txt")
            archivo.write_text(
                "FUENTE: " + nombre + " (" + handle + ")\n"
                "VIDEO: https://www.youtube.com/watch?v=" + video["id"] + "\n"
                "TITULO: " + video["titulo"] + "\n"
                "PUBLICADO: " + fecha + "\n"
                "ORIGEN: " + ("audio transcripto por Whisper (puede errar nombres propios)"
                              if por_whisper else "subtitulos automaticos de YouTube") + "\n"
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
            estado["reintentos"].pop(video["id"], None)
            nuevos_total += 1
            print("     + " + archivo.name + "  (" + str(len(texto.split())) + " palabras)")

    if not solo_listar:
        for handle in estado["vistos"]:
            estado["vistos"][handle] = estado["vistos"][handle][-200:]
        estado["ultima_corrida"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        escribir_json(ESTADO, estado)
        escribir_json(PENDIENTES, pendientes)
        sin_revisar = sum(1 for p in pendientes if p["estado"] == "sin_revisar")
        extra = (" (" + str(hechos_whisper) + " por audio con Whisper, " +
                 str(transcritos_whisper) + " intento(s))" if transcritos_whisper else "")
        print("\n" + str(nuevos_total) + " transcripto(s) nuevo(s)" + extra +
              ". Pendientes de redaccion: " + str(sin_revisar))


if __name__ == "__main__":
    main()
