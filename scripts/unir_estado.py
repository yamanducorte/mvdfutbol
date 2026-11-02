# -*- coding: utf-8 -*-
"""Une dos versiones de datos/estado.json en vez de dar un conflicto.

Cuando dos corridas se cruzan, las dos tocan la lista de videos ya vistos y git
no sabe resolverlo: para el son dos textos distintos. Pero semanticamente la
respuesta es obvia: lo visto por una y lo visto por la otra, todo visto. Eso es
lo que hace este script, y por eso el workflow lo llama cuando el rebase choca.

Uso:  python scripts/unir_estado.py una.json otra.json salida.json
"""
import json
import sys


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, json.JSONDecodeError):
        return {}


def unir(a, b):
    vistos = {}
    for lado in (a, b):
        for handle, ids in (lado.get("vistos") or {}).items():
            # Conserva el orden y no repite: el orden importa porque la lista se
            # recorta a los ultimos 200 y lo viejo se cae primero.
            acumulado = vistos.setdefault(handle, [])
            for ident in ids:
                if ident not in acumulado:
                    acumulado.append(ident)
    reintentos = {}
    for lado in (a, b):
        for ident, cuenta in (lado.get("reintentos") or {}).items():
            # Si las dos corridas lo intentaron, vale el numero mas alto: fueron
            # dos intentos de verdad.
            reintentos[ident] = max(reintentos.get(ident, 0), cuenta)
    corridas = [lado.get("ultima_corrida") for lado in (a, b) if lado.get("ultima_corrida")]
    unido = {"vistos": {h: ids[-200:] for h, ids in vistos.items()}, "reintentos": reintentos}
    if corridas:
        unido["ultima_corrida"] = max(corridas)
    return unido


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    una, otra, salida = sys.argv[1:4]
    unido = unir(leer(una), leer(otra))
    with open(salida, "w", encoding="utf-8") as archivo:
        json.dump(unido, archivo, ensure_ascii=False, indent=2)
    canales = len(unido["vistos"])
    videos = sum(len(v) for v in unido["vistos"].values())
    print("estado unido: " + str(canales) + " canal(es), " + str(videos) + " video(s) vistos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
