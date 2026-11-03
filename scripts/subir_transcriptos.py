# -*- coding: utf-8 -*-
"""Baja los transcriptos de YouTube desde esta maquina y los sube al repo.

Por que existe: YouTube bloquea a las maquinas de GitHub (pide confirmar que no
sos un robot, y los subtitulos dan 429), asi que el unico paso que tiene que
correr en casa es la bajada. Todo lo demas -filtrar, escribir las notas,
publicar el sitio y las tablas- lo sigue haciendo la nube sola.

Lo corre la tarea programada de Windows cada hora. Tambien se puede correr a
mano cuando quieras ponerte al dia:

    python scripts/subir_transcriptos.py
    python scripts/subir_transcriptos.py --ver    (muestra el registro y sale)

Si la maquina estuvo apagada no se pierde nada: el monitor mira hasta 7 dias
para atras (`dias_maximos` en fuentes.json).
"""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TMP = RAIZ / "datos" / "tmp"
REGISTRO = TMP / "bajar.log"
CANDADO = TMP / "bajar.lock"
ESTADO = "datos/estado.json"
MINUTOS_DE_CANDADO = 110

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def anotar(texto):
    linea = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] " + texto
    print(linea)
    try:
        with open(REGISTRO, "a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")
    except OSError:
        pass


def git(*argumentos, mostrar=False):
    """Corre git y devuelve (codigo, salida)."""
    proceso = subprocess.run(["git"] + list(argumentos), cwd=str(RAIZ),
                             capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    salida = ((proceso.stdout or "") + (proceso.stderr or "")).strip()
    if mostrar and salida:
        anotar("  git " + argumentos[0] + ": " + salida.splitlines()[-1][:160])
    return proceso.returncode, salida


def unir_estado_en_conflicto():
    """Resuelve el unico conflicto esperable: la lista de videos ya vistos.

    Si dos corridas (esta y la de la nube) miraron canales, las dos tocaron el
    mismo archivo y git ve dos textos distintos. La respuesta correcta es sumar:
    lo visto por una y lo visto por la otra, todo visto.
    """
    codigo, sin_resolver = git("diff", "--name-only", "--diff-filter=U")
    pendientes = [l.strip() for l in sin_resolver.splitlines() if l.strip()]
    if not pendientes:
        return True
    if pendientes != [ESTADO]:
        anotar("  !! hay conflictos que no se resuelven solos: " + ", ".join(pendientes))
        return False
    una, otra = TMP / "estado_nube.json", TMP / "estado_local.json"
    for etapa, destino in ((":2:" + ESTADO, una), (":3:" + ESTADO, otra)):
        codigo, contenido = git("show", etapa)
        if codigo != 0:
            anotar("  !! no pude leer " + etapa)
            return False
        destino.write_text(contenido, encoding="utf-8")
    proceso = subprocess.run([sys.executable, "scripts/unir_estado.py",
                              str(una), str(otra), ESTADO],
                             cwd=str(RAIZ), capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    if proceso.returncode != 0:
        anotar("  !! no pude unir el estado: " + (proceso.stderr or "")[:200])
        return False
    anotar("  " + (proceso.stdout or "").strip())
    git("add", ESTADO)
    return True


def ponerse_al_dia():
    """Trae lo que hizo la nube antes de mirar canales, para no pisarlo."""
    git("fetch", "--quiet", "origin", "main")
    codigo, _ = git("rebase", "origin/main")
    if codigo == 0:
        return True
    if not unir_estado_en_conflicto():
        git("rebase", "--abort")
        return False
    entorno = dict(os.environ, GIT_EDITOR="true")
    proceso = subprocess.run(["git", "rebase", "--continue"], cwd=str(RAIZ),
                             capture_output=True, text=True, env=entorno,
                             encoding="utf-8", errors="replace")
    if proceso.returncode != 0:
        anotar("  !! el rebase no pudo seguir, lo aborto")
        git("rebase", "--abort")
        return False
    return True


def subir():
    """Commitea los transcriptos nuevos y los empuja, reintentando si hace falta."""
    git("add", "datos", "contenido")
    codigo, _ = git("diff", "--staged", "--quiet")
    if codigo == 0:
        anotar("sin transcriptos nuevos, no hay nada que subir")
        return True
    sello = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git("-c", "user.name=mvdfutbol-casa", "-c", "user.email=bot@users.noreply.github.com",
        "commit", "-m", "Transcriptos bajados en casa al " + sello)
    for intento in (1, 2, 3):
        codigo, salida = git("push")
        if codigo == 0:
            anotar("subido (intento " + str(intento) + ")")
            return True
        anotar("  el push no entro, me pongo al dia y reintento")
        if not ponerse_al_dia():
            return False
    codigo, salida = git("push")
    if codigo != 0:
        anotar("!! no pude subir: " + salida.splitlines()[-1][:200] if salida else "!! no pude subir")
        return False
    return True


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    if "--ver" in sys.argv:
        print(REGISTRO.read_text(encoding="utf-8") if REGISTRO.exists() else "(todavia no hay registro)")
        return 0

    # Candado: si la corrida anterior sigue andando, esta se va sin hacer nada.
    if CANDADO.exists():
        edad = (datetime.now().timestamp() - CANDADO.stat().st_mtime) / 60
        if edad < MINUTOS_DE_CANDADO:
            anotar("ya hay una corrida andando (hace " + str(int(edad)) + " min), salgo")
            return 0
        anotar("habia un candado viejo de " + str(int(edad)) + " min, lo piso")
    CANDADO.write_text(datetime.now().isoformat(), encoding="utf-8")

    try:
        anotar("--- arranca la bajada ---")
        if not ponerse_al_dia():
            anotar("!! no pude ponerme al dia con el repo, no sigo")
            return 1
        proceso = subprocess.run([sys.executable, "scripts/monitor.py"], cwd=str(RAIZ),
                                 capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
        for linea in (proceso.stdout or "").splitlines():
            if linea.strip() and ("+" in linea or "!!" in linea or "transcripto(s)" in linea):
                anotar("  " + linea.strip()[:200])
        if proceso.returncode != 0:
            anotar("!! el monitor termino mal: " + (proceso.stderr or "")[-300:])
            return 1
        return 0 if subir() else 1
    finally:
        try:
            CANDADO.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
