#!/usr/bin/env python3
"""reparto — configura el ciclo de agentes (reparto.json).

Códigos de salida:
    0  configuración válida / operación hecha
    1  configuración inválida
    2  no se pudo leer o escribir

Uso:
    reparto.py validar [--rutas] [--json]
    reparto.py ver [rol]
    reparto.py set <rol> --modelo M --entorno E --cwd C --trigger T [--desde a,b] [--cada 10m]
                        [--comando "linea de comandos"]
    reparto.py acceso <rol> add|rm <ruta> [--modo rw|ro]

Sin dependencias: solo stdlib.
"""

from __future__ import annotations

import json
import os
import sys

# En consolas Windows (cp1252) un carácter fuera del juego de código rompe la salida.
# Se fuerza UTF-8 y, si falla, se reemplaza en vez de abortar.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_ERROR = 2

ENTORNOS = {"opencode", "dsh", "openclaw", "claude-code", "otro"}
TIPOS = {"agente", "humano"}
MODOS_TRIGGER = {"agente", "tiempo", "usuario"}
MODOS_ACCESO = {"rw", "ro"}
CAMPOS_ROL = {"tipo", "modelo", "entorno", "cwd", "acceso", "trigger", "comando", "entrega"}


def ruta_config(argv=None):
    """REPARTO_CONFIG > --config > ./reparto.json"""
    env = os.environ.get("REPARTO_CONFIG")
    if env:
        return os.path.expanduser(env)
    args = argv or sys.argv
    for i, a in enumerate(args):
        if a == "--config" and i + 1 < len(args):
            return os.path.expanduser(args[i + 1])
    return os.path.expanduser("reparto.json")


def cargar(ruta):
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"no existe {ruta}")
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def guardar(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, ruta)


def _abs(p, base):
    """Resuelve rutas relativas contra el directorio del archivo de configuración."""
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def validar(datos, revisar_rutas=False, base_dir="."):
    """Devuelve (errores, avisos)."""
    errores, avisos = [], []

    if not isinstance(datos, dict):
        return [("$", "la configuración debe ser un objeto JSON")], avisos
    if not isinstance(datos.get("version"), int):
        errores.append(("$.version", "falta version (entero)"))
    roles = datos.get("roles")
    if not isinstance(roles, dict) or not roles:
        errores.append(("$.roles", "tiene que haber al menos un rol"))
        return errores, avisos

    for nombre, rol in roles.items():
        base = f"$.roles.{nombre}"
        if not isinstance(rol, dict):
            errores.append((base, "el rol debe ser un objeto"))
            continue

        desconocidos = set(rol) - CAMPOS_ROL
        if desconocidos:
            errores.append((base, f"campos desconocidos: {', '.join(sorted(desconocidos))}"))

        tipo = rol.get("tipo", "agente")
        if tipo not in TIPOS:
            errores.append((f"{base}.tipo", f"tipo inválido: {tipo!r}"))
        elif tipo == "humano":
            if rol.get("modelo") not in (None, ""):
                errores.append((f"{base}.modelo", "un rol humano no lleva modelo"))
            if rol.get("entorno") not in (None, ""):
                errores.append((f"{base}.entorno", "un rol humano no lleva entorno"))
            if (rol.get("trigger") or {}).get("modo") != "usuario":
                errores.append((f"{base}.trigger", "un rol humano solo puede tener modo usuario"))
        else:
            if not isinstance(rol.get("modelo"), str) or not rol["modelo"].strip():
                errores.append((f"{base}.modelo", "falta modelo"))
            if rol.get("entorno") not in ENTORNOS:
                errores.append((f"{base}.entorno", f"entorno inválido: {rol.get('entorno')!r}"))

        # comando: lo que ejecuta el watcher para despertar al rol.
        comando = rol.get("comando")
        if tipo == "humano":
            if comando not in (None, "", []):
                errores.append((f"{base}.comando", "un rol humano no lleva comando"))
        elif comando not in (None, "", []):
            if isinstance(comando, str):
                if not comando.strip():
                    errores.append((f"{base}.comando", "el comando está vacío"))
            elif isinstance(comando, list):
                if not all(isinstance(x, str) and x.strip() for x in comando):
                    errores.append((f"{base}.comando", "cada parte del comando debe ser texto no vacío"))
            else:
                errores.append((f"{base}.comando", "el comando debe ser texto o lista de textos"))
        elif (rol.get("trigger") or {}).get("modo") in ("agente", "tiempo"):
            avisos.append((f"{base}.comando", "sin comando: el watcher no puede despertar este rol"))

        cwd = rol.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            errores.append((f"{base}.cwd", "falta cwd"))
        elif revisar_rutas and not os.path.isdir(_abs(cwd, base_dir)):
            errores.append((f"{base}.cwd", f"la ruta no existe: {cwd}"))

        accesos = rol.get("acceso", [])
        if not isinstance(accesos, list):
            errores.append((f"{base}.acceso", "debe ser lista"))
        else:
            for i, acc in enumerate(accesos):
                p = f"{base}.acceso[{i}]"
                if not isinstance(acc, dict):
                    errores.append((p, "cada acceso es {ruta, modo}"))
                    continue
                if not isinstance(acc.get("ruta"), str) or not acc["ruta"].strip():
                    errores.append((p, "falta ruta"))
                elif revisar_rutas and not os.path.exists(_abs(acc["ruta"], base_dir)):
                    errores.append((p, f"la ruta no existe: {acc['ruta']}"))
                if acc.get("modo") not in MODOS_ACCESO:
                    errores.append((p, f"modo inválido: {acc.get('modo')!r}"))

        trig = rol.get("trigger")
        if not isinstance(trig, dict):
            errores.append((f"{base}.trigger", "falta trigger"))
        else:
            modo = trig.get("modo")
            p = f"{base}.trigger"
            if modo not in MODOS_TRIGGER:
                errores.append((p, f"modo inválido: {modo!r}"))
            if modo == "agente":
                desde = trig.get("desde")
                if not isinstance(desde, list):
                    errores.append((p, "desde debe ser lista (puede ser vacía)"))
                elif not desde:
                    avisos.append((p, "modo agente con desde vacío: el rol no se despierta nunca"))
            if modo == "tiempo" and not trig.get("cada"):
                errores.append((p, "modo tiempo exige cada (ej: 10m)"))
            if modo == "usuario" and trig.get("desde"):
                avisos.append((p, "modo usuario ignora desde"))

        if not isinstance(rol.get("entrega", []), list):
            errores.append((f"{base}.entrega", "debe ser lista"))
        elif not rol.get("entrega"):
            avisos.append((f"{base}.entrega", "vacía: el rol no declara qué deja al cerrar"))

    return errores, avisos


def _salida(errores, avisos, como_json, extra=None):
    if como_json:
        payload = {"ok": not errores,
                   "errores": [{"path": p, "mensaje": m} for p, m in errores],
                   "avisos": [{"path": p, "mensaje": m} for p, m in avisos]}
        if extra:
            payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for p, m in errores:
        print(f"ERROR {p}: {m}")
    for p, m in avisos:
        print(f"AVISO {p}: {m}")
    if not errores:
        print("CONFIGURACION VALIDA" + (f" ({len(avisos)} aviso/s)" if avisos else ""))


def cmd_validar(args, ruta):
    datos = cargar(ruta)
    errores, avisos = validar(datos, revisar_rutas="--rutas" in args,
                              base_dir=os.path.dirname(os.path.abspath(ruta)))
    _salida(errores, avisos, "--json" in args)
    return EXIT_INVALID if errores else EXIT_OK


def cmd_ver(args, ruta):
    datos = cargar(ruta)
    roles = datos.get("roles", {})
    filtro = next((a for a in args[1:] if not a.startswith("--")), None)
    for nombre, rol in roles.items():
        if filtro and nombre != filtro:
            continue
        trig = rol.get("trigger", {})
        detalle = trig.get("modo", "?")
        if detalle == "agente":
            detalle += f" <- {', '.join(trig.get('desde') or []) or 'nadie'}"
        elif detalle == "tiempo":
            detalle += f" cada {trig.get('cada')}"
        accesos = ", ".join(f"{a.get('ruta')}:{a.get('modo')}" for a in rol.get("acceso", []))
        print(f"{nombre} ({rol.get('tipo', 'agente')})")
        if rol.get("tipo") == "humano":
            print("  humano: sin modelo, sin entorno")
            print(f"  cwd      {rol.get('cwd')}")
            print(f"  trigger  usuario")
            continue
        print(f"  modelo   {rol.get('modelo')}")
        print(f"  entorno  {rol.get('entorno')}")
        print(f"  cwd      {rol.get('cwd')}")
        print(f"  trigger  {detalle}")
        print(f"  comando  {rol.get('comando') or '(ninguno)'}")
        print(f"  acceso   {accesos or '(ninguno)'}")
    return EXIT_OK


def _valor(args, flag):
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def cmd_set(args, ruta):
    rol_nombre = next((a for a in args[1:] if not a.startswith("--")), None)
    if not rol_nombre:
        print("uso: reparto.py set <rol> --modelo M --entorno E --cwd C --trigger T")
        return EXIT_ERROR

    datos = cargar(ruta)
    roles = datos.setdefault("roles", {})
    rol = roles.setdefault(rol_nombre, {
        "modelo": "", "entorno": "opencode", "cwd": "",
        "acceso": [], "trigger": {"modo": "usuario", "desde": [], "cada": None},
        "comando": None, "entrega": [],
    })

    modelo = _valor(args, "--modelo")
    entorno = _valor(args, "--entorno")
    cwd = _valor(args, "--cwd")
    trigger = _valor(args, "--trigger")
    desde = _valor(args, "--desde")
    cada = _valor(args, "--cada")
    tipo = _valor(args, "--tipo")
    comando = _valor(args, "--comando")

    if tipo:
        rol["tipo"] = tipo
    if modelo:
        rol["modelo"] = modelo
    if entorno:
        rol["entorno"] = entorno
    if rol.get("tipo") == "humano":
        rol["modelo"] = None
        rol["entorno"] = None
        rol.setdefault("trigger", {})["modo"] = "usuario"
        rol["trigger"]["desde"] = []
        rol["trigger"]["cada"] = None
    if cwd:
        rol["cwd"] = cwd
    if trigger:
        rol.setdefault("trigger", {})["modo"] = trigger
    if desde is not None:
        rol.setdefault("trigger", {})["desde"] = [x.strip() for x in desde.split(",") if x.strip()]
    if cada is not None:
        rol.setdefault("trigger", {})["cada"] = cada or None
    if comando is not None:
        rol["comando"] = comando or None
    if rol.get("tipo") == "humano":
        rol["comando"] = None

    errores, avisos = validar(datos, revisar_rutas="--rutas" in args,
                              base_dir=os.path.dirname(os.path.abspath(ruta)))
    if errores:
        _salida(errores, avisos, "--json" in args)
        return EXIT_INVALID
    guardar(ruta, datos)
    _salida([], avisos, "--json" in args, {"rol": rol_nombre})
    return EXIT_OK


def cmd_acceso(args, ruta):
    partes = [a for a in args[1:] if not a.startswith("--")]
    if len(partes) < 3:
        print("uso: reparto.py acceso <rol> add|rm <ruta> [--modo rw|ro]")
        return EXIT_ERROR
    rol_nombre, accion, camino = partes[0], partes[1], partes[2]
    modo = _valor(args, "--modo") or "ro"

    datos = cargar(ruta)
    rol = datos.get("roles", {}).get(rol_nombre)
    if rol is None:
        print(f"ERROR: no existe el rol {rol_nombre}")
        return EXIT_INVALID

    accesos = rol.setdefault("acceso", [])
    if accion == "add":
        accesos[:] = [a for a in accesos if a.get("ruta") != camino]
        accesos.append({"ruta": camino, "modo": modo})
    elif accion == "rm":
        antes = len(accesos)
        accesos[:] = [a for a in accesos if a.get("ruta") != camino]
        if len(accesos) == antes:
            print(f"AVISO: {camino} no estaba en el acceso de {rol_nombre}")
    else:
        print("accion inválida: add | rm")
        return EXIT_ERROR

    errores, avisos = validar(datos, base_dir=os.path.dirname(os.path.abspath(ruta)))
    if errores:
        _salida(errores, avisos, "--json" in args)
        return EXIT_INVALID
    guardar(ruta, datos)
    _salida([], avisos, "--json" in args, {"rol": rol_nombre, "acceso": accion})
    return EXIT_OK


def main(argv):
    args = [a for a in argv[1:] if a != "--config"]
    # sacar el valor de --config de los args posicionales
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

    if not args:
        print(__doc__.strip())
        return EXIT_ERROR

    comando = args[0]
    try:
        if comando == "validar":
            return cmd_validar(args, ruta)
        if comando == "ver":
            return cmd_ver(args, ruta)
        if comando == "set":
            return cmd_set(args, ruta)
        if comando == "acceso":
            return cmd_acceso(args, ruta)
        print(f"comando desconocido: {comando}")
        print(__doc__.strip())
        return EXIT_ERROR
    except FileNotFoundError as exc:
        print(f"NO SE PUDO LEER: {exc}")
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        print(f"JSON INVALIDO: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv))
