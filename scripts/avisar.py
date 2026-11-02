# -*- coding: utf-8 -*-
"""Avisa a los buscadores que hay URLs nuevas (IndexNow).

Uso:  python scripts/avisar.py

IndexNow lo usan Bing, Yandex, Seznam y DuckDuckGo: la URL entra en cola de
rastreo en minutos. Google NO lo usa: para Google valen el sitemap de noticias,
el RSS y la frecuencia de publicacion.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "contenido" / "notas"
AVISADOS = RAIZ / "datos" / "avisados.json"
DOMINIO = "https://mvdfutbol.netlify.app"
CLAVE = "7f3c1a9d4b5e4c82a1d6e0f93b2c7a58"
PUNTO = "https://api.indexnow.org/indexnow"


def main():
    try:
        avisados = set(json.loads(AVISADOS.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        avisados = set()

    urls = []
    for archivo in NOTAS.glob("*.json"):
        try:
            slug = json.loads(archivo.read_text(encoding="utf-8")).get("slug")
        except json.JSONDecodeError:
            continue
        if slug:
            urls.append(DOMINIO + "/nota/" + slug + "/")
    nuevas = [u for u in urls if u not in avisados]
    if not nuevas:
        print("nada nuevo para avisar")
        return

    anfitrion = DOMINIO.split("//", 1)[1]
    cuerpo = json.dumps({
        "host": anfitrion,
        "key": CLAVE,
        "keyLocation": DOMINIO + "/" + CLAVE + ".txt",
        "urlList": nuevas[:100],
    }).encode("utf-8")
    pedido = urllib.request.Request(PUNTO, data=cuerpo, method="POST",
                                    headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as respuesta:
            print("IndexNow respondio " + str(respuesta.status) + " para " + str(len(nuevas)) + " URL(s)")
    except urllib.error.HTTPError as error:
        # 422 = la clave todavia no es visible en el dominio (pasa antes del primer deploy)
        print("IndexNow devolvio " + str(error.code) + ": " + error.reason)
        if error.code not in (200, 202):
            return
    except Exception as error:
        print("no se pudo avisar: " + str(error))
        return

    avisados.update(nuevas)
    AVISADOS.parent.mkdir(parents=True, exist_ok=True)
    AVISADOS.write_text(json.dumps(sorted(avisados), ensure_ascii=False, indent=1), encoding="utf-8")
    for url in nuevas:
        print("  avisada: " + url)


if __name__ == "__main__":
    main()
