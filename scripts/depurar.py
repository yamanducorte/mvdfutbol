# -*- coding: utf-8 -*-
"""Saca notas repetidas: dos canales pueden publicar el mismo video.

Uso:  python scripts/depurar.py            (muestra que haria)
      python scripts/depurar.py --aplicar  (borra)

Dos notas del mismo video son la misma noticia contada dos veces: a Google le
parece contenido duplicado y al lector le parece relleno. Se queda la mas nueva.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "contenido" / "notas"


def main():
    aplicar = "--aplicar" in sys.argv
    porvideo = {}
    for archivo in sorted(NOTAS.glob("*.json")):
        try:
            nota = json.loads(archivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        hallado = re.search(r"v=([A-Za-z0-9_-]{11})", nota.get("fuente", {}).get("video", ""))
        if not hallado:
            continue
        porvideo.setdefault(hallado.group(1), []).append((nota.get("publicado_utc", ""), archivo, nota))

    sobran = 0
    for video, lista in porvideo.items():
        if len(lista) < 2:
            continue
        lista.sort(key=lambda x: x[0], reverse=True)
        print("video " + video + ": se queda «" + lista[0][2]["titulo"][:60] + "»")
        for _, archivo, nota in lista[1:]:
            print("   borra «" + nota["titulo"][:60] + "»  (" + archivo.name[:50] + ")")
            sobran += 1
            if aplicar:
                archivo.unlink()
    if not sobran:
        print("sin repetidas")
    elif not aplicar:
        print("\n" + str(sobran) + " repetida(s). Corre con --aplicar para borrarlas.")
    else:
        print("\n" + str(sobran) + " repetida(s) borrada(s).")


if __name__ == "__main__":
    main()
