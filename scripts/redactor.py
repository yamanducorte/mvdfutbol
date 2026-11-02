# -*- coding: utf-8 -*-
"""Convierte transcriptos de YouTube en notas, en dos etapas.

Uso:  python scripts/redactor.py                (procesa lo pendiente)
      python scripts/redactor.py --limite 3     (solo 3, para probar)
      python scripts/redactor.py --simular       (no llama a la API: muestra que haria)

Etapa 1 (modelo barato): lee el transcripto completo y decide si hay noticia.
Etapa 2 (modelo bueno): escribe la nota, pero solo con los hechos que extrajo la
etapa 1. Nunca reescribe el transcripto: cita lo que se dijo, con minuto y link.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "fuentes.json"
PENDIENTES = RAIZ / "datos" / "hallazgos" / "pendientes.json"
NOTAS = RAIZ / "contenido" / "notas"
COSTOS = RAIZ / "datos" / "costos.json"

MODELO_FILTRO = "claude-haiku-5-5"
MODELO_REDACTOR = "claude-opus-5-5"
# (entrada, salida) en dolares por millon de tokens
PRECIOS = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.00, 20.00)}
# La consola de Windows no es UTF-8: imprimir un titulo con un caracter raro
# tiraba todo el script abajo. Que reemplace el caracter y siga de largo.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

REGLAS = """Sos el editor de un medio digital de futbol uruguayo. Trabajas sobre el
transcripto automatico de un video de YouTube de un programa deportivo.

Reglas que no se negocian:
- Solo valen hechos que esten dichos en el transcripto. Nada de completar con lo que sabes.
- El transcripto es automatico: puede tener errores de nombres. Si un nombre propio
  aparece dudoso o mal transcripto, marcalo en "dudas" en lugar de inventarlo.
- Interesa lo que dice gente del futbol (periodistas, dirigentes, tecnicos, jugadores,
  representantes): informacion, declaraciones, versiones de pases, lesiones, decisiones.
- No interesa la opinion suelta, el relato del partido ni la chicana entre hinchas.
- Esto es un medio de FUTBOL. Si el video habla de otro deporte (hipica, basquetbol,
  ciclismo), de politica general, de espectaculos o de salud, devolve es_de_futbol
  en false y es_noticia en false, por mas que el programa sea deportivo.
- Distingui informacion de rumor, pero no al reves. Un dato publico y comprobable que el
  que habla afirma de plano -un resultado, un gol, una tarjeta, un descenso, un ascenso,
  una expulsion, una lesion que ya ocurrio, una renuncia o un despido que ya paso, un
  fichaje ya firmado- es
  "confirmado". Nadie se inventa eso al aire y cualquiera lo puede verificar al dia
  siguiente: va como hecho, sin reservas y sin condicional.
- "version" es solo para lo que todavia no paso o para lo que el que habla pone en boca de
  otros: "me dicen", "se habla", "parece", "estan negociando", "no va a seguir el ano que
  viene", "lo quiere tal club", "yo creo que". Ahi si corresponde la reserva."""

ESQUEMA_FILTRO = """Devolve SOLO un objeto JSON con esta forma, sin texto alrededor:
{
  "es_noticia": true | false,
  "motivo": "una linea explicando por que si o por que no",
  "es_de_futbol": true | false,
  "importancia": 1-5,
  "titular_sugerido": "...",
  "categoria": "pases" | "seleccion" | "primera" | "juveniles" | "dirigencia" | "otro",
  "clubes": ["..."],
  "personas": ["quien lo dijo y quien es nombrado"],
  "hechos": [
    { "hecho": "que se informo, en una oracion",
      "cita": "la frase textual mas corta que lo sostiene (maximo 25 palabras)",
      "minuto": "hh:mm:ss como aparece entre corchetes en el transcripto",
      "tipo": "confirmado" | "version" }
  ],
  "dudas": ["nombres o datos que el transcripto deja dudosos"]
}"""

ESQUEMA_NOTA = """Devolve SOLO un objeto JSON con esta forma, sin texto alrededor:
{
  "titulo": "maximo 70 caracteres, sin signos de admiracion ni mayusculas gritadas",
  "bajada": "una o dos oraciones que resuman la noticia",
  "cuerpo": ["parrafo 1", "parrafo 2", "..."],
  "etiquetas": ["club o tema", "..."],
  "categoria": "la misma que trajo el filtro"
}"""


def leer_json(ruta, por_defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return por_defecto


def escribir_json(ruta, dato):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False, indent=2), encoding="utf-8")


def slug(texto):
    limpio = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", limpio.lower())).strip("-")[:70]


def solo_json(texto):
    """El modelo puede envolver el JSON en texto o en un bloque de codigo."""
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    arranque, cierre = texto.find("{"), texto.rfind("}")
    if arranque == -1 or cierre == -1:
        raise ValueError("la respuesta no trae JSON")
    return json.loads(texto[arranque:cierre + 1])


def costo(modelo, uso):
    entrada, salida = PRECIOS.get(modelo, (0, 0))
    return (uso.input_tokens * entrada + uso.output_tokens * salida) / 1_000_000


def anotar_costo(registro, modelo, uso):
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dia = registro.setdefault(hoy, {})
    fila = dia.setdefault(modelo, {"llamadas": 0, "tokens_entrada": 0, "tokens_salida": 0, "usd": 0.0})
    fila["llamadas"] += 1
    fila["tokens_entrada"] += uso.input_tokens
    fila["tokens_salida"] += uso.output_tokens
    fila["usd"] = round(fila["usd"] + costo(modelo, uso), 5)
    return registro


def pedir(cliente, modelo, system, mensaje, max_tokens, esfuerzo, pensar=True):
    """esfuerzo importa: estos modelos piensan antes de responder y el pensamiento
    consume max_tokens. Con el transcripto entero adentro, un esfuerzo alto se come
    todo el presupuesto y devuelve una respuesta vacia."""
    extra = {} if pensar else {"thinking": {"type": "disabled"}}
    respuesta = cliente.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        output_config={"effort": esfuerzo},
        system=system,
        messages=[{"role": "user", "content": mensaje}],
        **extra,
    )
    texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
    if not texto.strip():
        raise ValueError("respuesta vacia (stop_reason=" + str(respuesta.stop_reason) +
                         ", salida=" + str(respuesta.usage.output_tokens) + " tokens)")
    return texto, respuesta.usage


def filtrar(cliente, transcripto, canal, registro):
    extra = ""
    if canal.get("solo_futbol"):
        extra = ("\nEste canal no es solo de futbol. Si el video no trae a gente del futbol "
                 "hablando de futbol, devolve es_de_futbol en false y es_noticia en false.")
    texto, uso = pedir(cliente, MODELO_FILTRO, REGLAS + extra + "\n\n" + ESQUEMA_FILTRO,
                       transcripto, 6000, "low", pensar=False)
    anotar_costo(registro, MODELO_FILTRO, uso)
    return solo_json(texto), uso


def redactar(cliente, hallazgo, pendiente, registro):
    contexto = {
        "fuente": pendiente["fuente"],
        "programa": pendiente["titulo"],
        "link_del_video": pendiente["video"],
        "fecha": pendiente["publicado"],
        "hechos": hallazgo.get("hechos", []),
        "clubes": hallazgo.get("clubes", []),
        "personas": hallazgo.get("personas", []),
        "categoria": hallazgo.get("categoria", "otro"),
        "dudas": hallazgo.get("dudas", []),
    }
    system = (REGLAS + """

Escribis la nota para publicar. Como se escribe:
- Espanol rioplatense, voseo, sobrio. Como escribe un diario, no como habla un hincha.
- 250 a 450 palabras, parrafos cortos.
- El primer parrafo dice la noticia completa: que paso, quien lo dijo y donde.
- Atribui siempre: nombra el programa y la fuente. El lector tiene que poder ir al video.
- Las citas textuales van entre comillas y son cortas. No reproduzcas parrafos del
  transcripto: contalo con tus palabras y cita solo la frase que importa.
- Lo que el filtro marco como "confirmado" se escribe derecho, en afirmativo, como lo
  escribiria cualquier diario: "Danubio descendio a la Segunda Division". Nada de
  "supuestamente", "habria", "al parecer" ni "debe tomarse como una version": es un hecho.
  La atribucion va igual, pero una sola vez y en el cuerpo, no pegada a cada oracion.
- El titulo de un hecho confirmado no lleva "segun informo tal": dice la noticia y punto.
  El "segun" en el titulo se usa solo cuando lo que se titula es una version o la opinion
  de alguien.
- Lo que el filtro marco como "version" se escribe como version ("segun dijo", "trascendio",
  "manejo la posibilidad"), nunca como hecho confirmado.
- No escribas sobre el video ni sobre el transcripto. Al lector no le importa que "el dato
  aparece al comienzo del video" ni que "el tramo no permite precisar de quien se trata":
  si un dato no se entiende, se omite y listo. Si nombras el minuto, escribilo asi:
  "minuto 5:52", porque el sitio lo convierte en un link al segundo exacto del video.
- Si hay algo en "dudas", no lo afirmes: omitilo o escribilo con la reserva correspondiente.
- Nada de titulos carnada, nada de preguntas en el titulo, nada de emojis.

""" + ESQUEMA_NOTA)
    texto, uso = pedir(cliente, MODELO_REDACTOR, system,
                       json.dumps(contexto, ensure_ascii=False, indent=1), 8000, "medium")
    anotar_costo(registro, MODELO_REDACTOR, uso)
    return solo_json(texto), uso


def main():
    limite = None
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
    simular = "--simular" in sys.argv

    fuentes = leer_json(FUENTES, {})
    por_handle = {}
    for canal in fuentes.get("youtube", []):
        por_handle[canal["nombre"]] = canal
    pendientes = leer_json(PENDIENTES, [])
    # Lo mas nuevo primero: si hay que cortar por limite, que se corte lo viejo.
    cola = sorted((p for p in pendientes if p.get("estado") == "sin_revisar"),
                  key=lambda p: p.get("publicado", ""), reverse=True)
    if limite:
        cola = cola[:limite]
    # Si un video ya tiene nota, no se vuelve a escribir (puede venir repetido
    # desde dos canales que publicaron lo mismo).
    ya_escritos = set()
    for archivo in NOTAS.glob("*.json"):
        try:
            ya_escritos.add(json.loads(archivo.read_text(encoding="utf-8"))["fuente"]["video"])
        except (json.JSONDecodeError, KeyError):
            continue
    descartadas_repetidas = [p for p in cola if p["video"] in ya_escritos]
    for pendiente in descartadas_repetidas:
        pendiente["estado"] = "repetido"
    cola = [p for p in cola if p["video"] not in ya_escritos]
    if descartadas_repetidas:
        print(str(len(descartadas_repetidas)) + " ya tenian nota (mismo video en dos canales)")

    if not cola:
        print("no hay transcriptos pendientes")
        return
    print(str(len(cola)) + " transcripto(s) para revisar")

    if simular:
        for pendiente in cola:
            palabras = len((RAIZ / pendiente["transcripto"]).read_text(encoding="utf-8").split())
            print("  [simulado] " + pendiente["fuente"] + " | " + pendiente["titulo"][:50] +
                  " | " + str(palabras) + " palabras ~ USD " +
                  str(round(palabras * 1.35 * PRECIOS[MODELO_FILTRO][0] / 1_000_000, 5)) + " de filtro")
        return

    import anthropic
    # En la nube la key viene del secret; en local, de .env (que no entra al repo).
    archivo_env = RAIZ / ".env"
    if archivo_env.exists():
        for linea in archivo_env.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                nombre, valor = linea.split("=", 1)
                os.environ.setdefault(nombre.strip(), valor.strip())
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("falta ANTHROPIC_API_KEY en el entorno")
        return
    cliente = anthropic.Anthropic()
    registro = leer_json(COSTOS, {})
    escritas = descartadas = 0

    for pendiente in cola:
        archivo = RAIZ / pendiente["transcripto"]
        if not archivo.exists():
            pendiente["estado"] = "sin_archivo"
            continue
        transcripto = archivo.read_text(encoding="utf-8")
        canal = por_handle.get(pendiente["fuente"], {})
        try:
            hallazgo, _ = filtrar(cliente, transcripto, canal, registro)
        except Exception as error:
            print("  !! filtro fallo en " + archivo.name + ": " + str(error))
            continue

        if not hallazgo.get("es_noticia") or (canal.get("solo_futbol") and not hallazgo.get("es_de_futbol", True)):
            pendiente["estado"] = "descartado"
            pendiente["motivo"] = hallazgo.get("motivo", "")
            descartadas += 1
            print("  - descartado: " + pendiente["titulo"][:50] + " (" + hallazgo.get("motivo", "")[:60] + ")")
            continue

        try:
            nota, _ = redactar(cliente, hallazgo, pendiente, registro)
        except Exception as error:
            print("  !! redaccion fallo en " + archivo.name + ": " + str(error))
            continue

        fecha = pendiente["publicado"][:10]
        nota.update({
            "slug": fecha + "-" + slug(nota.get("titulo", "nota")),
            "fecha": fecha,
            "publicado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "importancia": hallazgo.get("importancia", 3),
            "fuente": {"nombre": pendiente["fuente"], "programa": pendiente["titulo"],
                       "video": pendiente["video"]},
            "hechos": hallazgo.get("hechos", []),
        })
        escribir_json(NOTAS / (nota["slug"] + ".json"), nota)
        pendiente["estado"] = "escrita"
        pendiente["nota"] = nota["slug"]
        escritas += 1
        print("  + " + nota["titulo"][:70])

    escribir_json(PENDIENTES, pendientes)
    escribir_json(COSTOS, registro)
    hoy = registro.get(datetime.now(timezone.utc).strftime("%Y-%m-%d"), {})
    gasto = round(sum(f["usd"] for f in hoy.values()), 4)
    print("\n" + str(escritas) + " nota(s) escrita(s), " + str(descartadas) +
          " descartada(s). Gasto de hoy: USD " + str(gasto))


if __name__ == "__main__":
    main()
