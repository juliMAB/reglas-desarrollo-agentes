#!/usr/bin/env python3
"""watcher — despierta a los roles cuando tienen trabajo.

Lee reparto.json, mira el buzon de cada rol y ejecuta su `comando`.
Un lock por rol impide que dos procesos despierten al mismo rol a la vez.

Codigos de salida:
    0  pasada hecha
    1  configuracion invalida o rol bloqueado (sin comando, sin buzon, desde vacio)
    2  no se pudo leer o escribir

Uso:
    watcher.py <rol> [<rol> ...] [--once] [--seco] [--intervalo 5]
               [--timeout 600] [--buzon DIR] [--estado-dir DIR] [--config RUTA]
    watcher.py --todos [--once]
    watcher.py estado <rol>

Sin --once corre en loop. --seco muestra lo que haria sin ejecutar ni recordar.
El comando recibe:
    REPARTO_ROL, REPARTO_BUZON, REPARTO_ARCHIVO, REPARTO_HANDOFF_ID, REPARTO_CONFIG

Sin dependencias: solo stdlib.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "reparto")))
import reparto as reparto_mod  # noqa: E402

EXIT_OK = 0
EXIT_BLOQUEADO = 1
EXIT_ERROR = 2

ACTIVOS = {"pedido", "entregado", "reabierto", "bloqueado", "esperando_usuario"}
INTERVALOS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _abs(p, base):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def ahora():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def segundos(txt):
    """'10m' -> 600. None si no se entiende."""
    m = re.fullmatch(r"\s*(\d+)\s*([smhd])?\s*", str(txt or ""))
    if not m:
        return None
    return int(m.group(1)) * INTERVALOS[m.group(2) or "s"]


def ruta_config(argv):
    env = os.environ.get("REPARTO_CONFIG")
    if env:
        return os.path.expanduser(env)
    for i, a in enumerate(argv):
        if a == "--config" and i + 1 < len(argv):
            return os.path.expanduser(argv[i + 1])
    return os.path.expanduser("reparto.json")


def cargar_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def guardar_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, ruta)


def firma(ruta):
    st = os.stat(ruta)
    return [st.st_mtime_ns, st.st_size]


# --- lock por rol -----------------------------------------------------------

def _pid_vivo(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def lock_vencido(ruta, timeout):
    datos = cargar_json(ruta, None)
    if isinstance(datos, dict):
        if not _pid_vivo(datos.get("pid")):
            return True
        edad = time.time() - float(datos.get("ts") or 0)
        return edad > max(timeout * 2, 60)
    try:
        return time.time() - os.stat(ruta).st_mtime > max(timeout * 2, 60)
    except OSError:
        return True


def lock_adquirir(ruta, timeout):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    for intento in (0, 1):
        try:
            fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            if intento == 0 and lock_vencido(ruta, timeout):
                try:
                    os.unlink(ruta)
                except FileNotFoundError:
                    pass
                continue
            return None
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "ts": time.time()}, fh)
        return ruta
    return None


def lock_liberar(ruta):
    if not ruta:
        return
    try:
        os.unlink(ruta)
    except FileNotFoundError:
        pass


def lock_ocupado_por(ruta):
    datos = cargar_json(ruta, {})
    return datos.get("pid", "?") if isinstance(datos, dict) else "?"


# --- lectura del buzon ------------------------------------------------------

def handoffs(rol_dir):
    """[(nombre, handoff)] de los .json del buzon del rol. Ignora lo ilegible."""
    salida = []
    try:
        nombres = sorted(os.listdir(rol_dir))
    except FileNotFoundError:
        return salida
    for nombre in nombres:
        if nombre.startswith(".") or not nombre.endswith(".json"):
            continue
        datos = cargar_json(os.path.join(rol_dir, nombre), None)
        if isinstance(datos, dict):
            salida.append((nombre, datos))
    return salida


def pendientes(rol, rol_dir, estado, desde):
    """Handoffs nuevos o modificados que le tocan al rol."""
    vistos = estado.setdefault("archivos", {})
    salida = []
    for nombre, datos in handoffs(rol_dir):
        if datos.get("para") != rol:
            continue
        if datos.get("de") == rol:
            continue
        if datos.get("estado") not in ACTIVOS:
            continue
        if desde and datos.get("de") not in desde:
            continue
        ruta = os.path.join(rol_dir, nombre)
        try:
            actual = firma(ruta)
        except OSError:
            continue
        if vistos.get(nombre, {}).get("firma") == actual:
            continue
        salida.append((nombre, ruta, datos))
    return salida


def recordar(estado, nombre, ruta, resultado):
    try:
        actual = firma(ruta)
    except OSError:
        actual = None
    estado.setdefault("archivos", {})[nombre] = {
        "firma": actual,
        "visto": ahora(),
        "resultado": resultado,
    }


# --- ejecucion --------------------------------------------------------------

def argv_comando(comando):
    if isinstance(comando, list):
        return list(comando)
    if os.name == "nt":
        return ["cmd", "/c", comando]
    return ["/bin/sh", "-c", comando]


def ejecutar(rol, comando, cwd, entorno, timeout, seco):
    argv = argv_comando(comando)
    if seco:
        print(f"SECO {rol}: {' '.join(argv)}")
        return 0
    print(f"EJECUTA {rol}: {argv[-1] if isinstance(comando, str) else ' '.join(argv)}")
    try:
        proc = subprocess.run(argv, cwd=cwd, env=entorno, timeout=timeout)
        print(f"FIN {rol}: codigo={proc.returncode}")
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(f"FIN {rol}: timeout a los {timeout}s")
        return 124
    except OSError as exc:
        print(f"FIN {rol}: no se pudo ejecutar: {exc}")
        return 127


def entorno_de(rol, cfg_path, rol_dir, archivo, handoff_id):
    env = os.environ.copy()
    env.update({
        "REPARTO_ROL": rol,
        "REPARTO_BUZON": rol_dir,
        "REPARTO_ARCHIVO": archivo or "",
        "REPARTO_HANDOFF_ID": handoff_id or "",
        "REPARTO_CONFIG": os.path.abspath(cfg_path),
    })
    return env


# --- pasada -----------------------------------------------------------------

def preparar(rol_nombre, rol, base_dir, cfg_path, buzon_base, estado_dir):
    """Devuelve (error, contexto) para el rol. error = motivo de bloqueo."""
    tipo = rol.get("tipo", "agente")
    if tipo == "humano":
        return ("humano: no se despierta", None)
    trig = rol.get("trigger") or {}
    modo = trig.get("modo")
    if modo == "usuario":
        return ("trigger usuario: no se despierta solo", None)
    if modo == "agente" and not (trig.get("desde") or []):
        return ("modo agente con desde vacio: no se despierta nunca", None)
    comando = rol.get("comando")
    if not comando:
        return ("sin comando: el watcher no puede despertarlo", None)

    cada = segundos(trig.get("cada")) if modo == "tiempo" else None
    if modo == "tiempo" and not cada:
        return (f"cada invalido: {trig.get('cada')!r} (usar 30s, 10m, 1h, 1d)", None)

    cwd = _abs(rol.get("cwd") or ".", base_dir)
    if not os.path.isdir(cwd):
        return (f"no existe el cwd: {cwd}", None)

    rol_dir = os.path.join(buzon_base, rol_nombre)
    if modo == "agente" and not os.path.isdir(rol_dir):
        return (f"no existe el buzon del rol: {rol_dir}", None)

    estado_path = os.path.join(estado_dir, f"{rol_nombre}.json")
    estado = cargar_json(estado_path, {}) or {}
    return (None, {
        "rol": rol_nombre,
        "rol_dir": rol_dir,
        "cwd": cwd,
        "comando": comando,
        "modo": modo,
        "desde": list(trig.get("desde") or []),
        "cada": cada or 0,
        "estado": estado,
        "estado_path": estado_path,
        "lock_path": os.path.join(estado_dir, f"{rol_nombre}.lock"),
    })


def pasada_rol(ctx, cfg_path, timeout, seco):
    rol = ctx["rol"]
    if ctx["modo"] == "agente":
        lista = pendientes(rol, ctx["rol_dir"], ctx["estado"], ctx["desde"])
        if not lista:
            return EXIT_OK
    else:
        ultima = float(ctx["estado"].get("ultima") or 0)
        if ctx["cada"] and time.time() - ultima < ctx["cada"]:
            return EXIT_OK
        lista = [(None, None, None)]

    lock = lock_adquirir(ctx["lock_path"], timeout)
    if not lock:
        print(f"SALTA {rol}: lock ocupado (pid {lock_ocupado_por(ctx['lock_path'])})")
        return EXIT_OK

    try:
        if ctx["modo"] == "tiempo":
            print(f"DESPIERTA {rol}: trigger tiempo (cada {ctx['cada']}s)")
            codigo = ejecutar(rol, ctx["comando"], ctx["cwd"],
                              entorno_de(rol, cfg_path, ctx["rol_dir"], "", ""),
                              timeout, seco)
            if not seco:
                ctx["estado"]["ultima"] = time.time()
        else:
            codigo = 0
            for nombre, ruta, datos in lista:
                print(f"DESPIERTA {rol} <- {nombre} ({datos.get('estado')} de {datos.get('de')},"
                      f" id {datos.get('handoff_id')})")
                codigo = ejecutar(rol, ctx["comando"], ctx["cwd"],
                                  entorno_de(rol, cfg_path, ctx["rol_dir"], ruta,
                                             datos.get("handoff_id")),
                                  timeout, seco)
                if not seco:
                    recordar(ctx["estado"], nombre, ruta, codigo)
        if not seco:
            guardar_json(ctx["estado_path"], ctx["estado"])
        return EXIT_OK
    finally:
        lock_liberar(lock)


def cmd_pasada(roles, datos, base_dir, cfg_path, buzon_base, estado_dir,
               timeout, seco, intervalo, once):
    bloqueados = 0
    contextos = []
    for nombre in roles:
        rol = datos["roles"].get(nombre)
        if rol is None:
            print(f"BLOQUEADO {nombre}: no existe en reparto.json")
            bloqueados += 1
            continue
        error, ctx = preparar(nombre, rol, base_dir, cfg_path, buzon_base, estado_dir)
        if error:
            print(f"SALTA {nombre}: {error}")
            if not error.startswith(("humano", "trigger usuario")):
                bloqueados += 1
            continue
        contextos.append(ctx)

    while True:
        for ctx in contextos:
            pasada_rol(ctx, cfg_path, timeout, seco)
        if once:
            return EXIT_BLOQUEADO if bloqueados else EXIT_OK
        time.sleep(intervalo)


def cli_estado(rol, datos, base_dir, buzon_base, estado_dir):
    if rol not in datos.get("roles", {}):
        print(f"ERROR: no existe el rol {rol}")
        return EXIT_BLOQUEADO
    rol_dir = os.path.join(buzon_base, rol)
    estado = cargar_json(os.path.join(estado_dir, f"{rol}.json"), {}) or {}
    desde = (datos["roles"][rol].get("trigger") or {}).get("desde") or []
    lista = pendientes(rol, rol_dir, estado, desde)
    if not lista:
        print(f"SIN PENDIENTES {rol}")
        return EXIT_OK
    for nombre, ruta, datos_h in lista:
        print(f"PENDIENTE {nombre}: {datos_h.get('estado')} de {datos_h.get('de')}"
              f" id {datos_h.get('handoff_id')}")
    return EXIT_OK


def main(argv):
    limpio = []
    saltar = False
    for a in argv[1:]:
        if saltar:
            saltar = False
            continue
        if a == "--config":
            saltar = True
            continue
        limpio.append(a)
    args = limpio

    ruta = ruta_config(argv)
    try:
        datos = reparto_mod.cargar(ruta)
    except FileNotFoundError as exc:
        print(f"NO SE PUDO LEER: {exc}")
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        print(f"JSON INVALIDO: {exc}")
        return EXIT_ERROR

    base_dir = os.path.dirname(os.path.abspath(ruta))
    buzon_base = _abs(_valor(args, "--buzon") or datos.get("buzon") or "buzon", base_dir)
    estado_dir = _abs(_valor(args, "--estado-dir") or ".watcher", base_dir)
    intervalo = segundos(_valor(args, "--intervalo") or "5") or 5
    timeout = segundos(_valor(args, "--timeout") or "600") or 600
    seco = "--seco" in args
    once = "--once" in args or seco

    pos = posicionales(args)

    if pos[:1] == ["estado"]:
        rol = pos[1] if len(pos) > 1 else None
        if not rol:
            print("uso: watcher.py estado <rol>")
            return EXIT_ERROR
        return cli_estado(rol, datos, base_dir, buzon_base, estado_dir)

    if "--todos" in args:
        roles = list(datos.get("roles", {}))
    else:
        roles = pos
        if not roles:
            print(__doc__.strip())
            return EXIT_ERROR

    errores, _avisos = reparto_mod.validar(datos, base_dir=base_dir)
    if errores:
        print("CONFIGURACION INVALIDA")
        for p, m in errores[:10]:
            print(f"  {p}: {m}")
        return EXIT_ERROR

    try:
        return cmd_pasada(roles, datos, base_dir, ruta, buzon_base, estado_dir,
                          timeout, seco, intervalo, once)
    except KeyboardInterrupt:
        return EXIT_OK


FLAGS_CON_VALOR = {"--config", "--intervalo", "--timeout", "--buzon", "--estado-dir"}


def posicionales(args):
    """Argumentos que no son flags ni valores de flags."""
    salida, i = [], 0
    while i < len(args):
        if args[i] in FLAGS_CON_VALOR:
            i += 2
            continue
        if args[i].startswith("--"):
            i += 1
            continue
        salida.append(args[i])
        i += 1
    return salida


def _valor(args, flag):
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv))
