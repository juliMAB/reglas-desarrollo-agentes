#!/usr/bin/env python3
"""vista — tablero read-only del ciclo de agentes.

Lee reparto.json, escribio por el watcher no toca nada:
  .watcher/turno/<rol>.json   estado del turno
  .watcher/eventos.jsonl      bitacora
  .watcher/logs/<rol>.log     salida del comando del rol
  buzon/<rol>/*.json          handoffs pendientes

Uso:
    vista.py [--config RUTA] [--puerto 3040] [--host 127.0.0.1]
             [--estado-dir DIR] [--buzon DIR]

GET /              pagina
GET /api/estado    JSON con roles y ultimos eventos
GET /api/log?rol=  salida del rol (texto)

Sin dependencias: solo stdlib.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "watcher")))
import watcher  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 2


def _valor(args, flag):
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def tail(ruta, n=12):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            lineas = fh.read().splitlines()
    except FileNotFoundError:
        return []
    return lineas[-n:]


def ultimos_eventos(ruta, n=40):
    eventos = []
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                if linea.strip():
                    try:
                        eventos.append(json.loads(linea))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        return []
    return eventos[-n:]


def _derivar(rol, turno):
    if turno.get("estado"):
        return turno["estado"]
    if rol.get("tipo") == "humano":
        return "no aplica"
    trig = (rol.get("trigger") or {}).get("modo")
    if trig == "usuario":
        return "manual"
    if not rol.get("comando"):
        return "sin comando"
    return "dormido"


def construir_estado(cfg_path, estado_dir=None, buzon_dir=None):
    datos = watcher.reparto_mod.cargar(cfg_path)
    base = os.path.dirname(os.path.abspath(cfg_path))
    estado_dir = estado_dir or os.path.join(base, ".watcher")
    buzon_base = buzon_dir or watcher._abs(datos.get("buzon") or "buzon", base)

    roles = []
    for nombre, rol in datos.get("roles", {}).items():
        turno_path = os.path.join(estado_dir, "turno", f"{nombre}.json")
        turno = watcher.cargar_json(turno_path, {}) or {}
        trig = rol.get("trigger") or {}
        desde = list(trig.get("desde") or [])
        pendientes = []
        if (rol.get("tipo") or "agente") == "agente" and trig.get("modo") == "agente":
            estado_archivos = watcher.cargar_json(
                os.path.join(estado_dir, f"{nombre}.json"), {}) or {}
            pendientes = [h.get("handoff_id") or nombre_archivo
                          for nombre_archivo, _ruta, h in watcher.pendientes(
                              nombre, os.path.join(buzon_base, nombre),
                              estado_archivos, desde)]
        detalle_trigger = trig.get("modo") or "?"
        if detalle_trigger == "agente":
            detalle_trigger += " <- " + (", ".join(desde) or "nadie")
        elif detalle_trigger == "tiempo":
            detalle_trigger += " cada " + str(trig.get("cada"))

        roles.append({
            "nombre": nombre,
            "tipo": rol.get("tipo") or "agente",
            "modelo": rol.get("modelo"),
            "entorno": rol.get("entorno"),
            "trigger": detalle_trigger,
            "estado": _derivar(rol, turno),
            "con": turno.get("con"),
            "handoff_id": turno.get("handoff_id"),
            "desde": turno.get("desde"),
            "resultado": turno.get("resultado"),
            "motivo": turno.get("motivo"),
            "operacion": turno.get("operacion"),
            "pendientes": pendientes,
            "log": tail(os.path.join(estado_dir, "logs", f"{nombre}.log"), 12),
        })

    return {
        "generado": watcher.ahora(),
        "roles": roles,
        "eventos": ultimos_eventos(os.path.join(estado_dir, "eventos.jsonl"), 40),
    }


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ciclo de agentes</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 20px; background: #0d1117; color: #c9d1d9;
         font: 14px/1.45 -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
           margin-bottom: 16px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
  h1 { font-size: 18px; margin: 0; font-weight: 600; }
  .tenue { color: #8b949e; font-size: 12px; }
  .grilla { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }
  .tarjeta { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
             padding: 14px; display: flex; flex-direction: column; gap: 8px; }
  .fila { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
  .rol { font-size: 15px; font-weight: 600; }
  .badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid;
           text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; }
  .meta { display: grid; grid-template-columns: 88px 1fr; gap: 2px 8px; font-size: 13px; }
  .meta dt { color: #8b949e; }
  .meta dd { margin: 0; overflow-wrap: anywhere; }
  .log { background: #0d1117; border: 1px solid #21262d; border-radius: 6px;
         padding: 8px; margin: 0; max-height: 150px; overflow: auto;
         font: 11px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; color: #adbac7;
         white-space: pre-wrap; }
  .vacio { color: #6e7681; font-style: italic; }
  h2 { font-size: 14px; margin: 22px 0 8px; color: #8b949e; font-weight: 600; }
  .eventos { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
             padding: 10px 12px; max-height: 300px; overflow: auto;
             font: 12px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .evento { display: flex; gap: 10px; }
  .evento .hora { color: #6e7681; }
  .evento .quien { color: #58a6ff; min-width: 90px; }
  .evento .accion { color: #c9d1d9; min-width: 80px; }
  .evento .detalle { color: #8b949e; overflow-wrap: anywhere; }
  .trabajando { color: #d29922; border-color: #d29922; }
  .termino { color: #3fb950; border-color: #3fb950; }
  .fallo { color: #f85149; border-color: #f85149; }
  .bloqueado { color: #db6d28; border-color: #db6d28; }
  .dormido, .manual, .no-aplica, .sin-comando { color: #8b949e; border-color: #484f58; }
</style>
</head>
<body>
<header>
  <h1>Ciclo de agentes</h1>
  <span class="tenue" id="actualizado">cargando…</span>
  <span class="tenue" id="resumen"></span>
</header>
<div class="grilla" id="roles"></div>
<h2>Eventos</h2>
<div class="eventos" id="eventos"><span class="vacio">sin eventos</span></div>
<script>
const COLORES = ["trabajando","termino","fallo","bloqueado","dormido","manual","no-aplica","sin-comando"];
function hace(iso) {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (isNaN(t)) return iso;
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 60) return "hace " + s + "s";
  if (s < 3600) return "hace " + Math.floor(s/60) + "m";
  return "hace " + Math.floor(s/3600) + "h";
}
function el(tag, clase, texto) {
  const n = document.createElement(tag);
  if (clase) n.className = clase;
  if (texto !== undefined && texto !== null) n.textContent = texto;
  return n;
}
function fila(etiqueta, valor) {
  const d = el("div","meta");
  d.appendChild(el("dt", null, etiqueta));
  d.appendChild(el("dd", null, valor));
  return d;
}
function tarjeta(r) {
  const c = el("div","tarjeta");
  const cab = el("div","fila");
  cab.appendChild(el("span","rol", r.nombre));
  const estado = r.estado || "dormido";
  const clase = "badge " + estado.replaceAll(" ", "-");
  cab.appendChild(el("span", clase, estado));
  c.appendChild(cab);

  const meta = el("div","meta");
  meta.appendChild(el("dt", null, "con"));
  meta.appendChild(el("dd", null, r.con || "—"));
  meta.appendChild(el("dt", null, "handoff"));
  meta.appendChild(el("dd", null, r.handoff_id || "—"));
  meta.appendChild(el("dt", null, "desde"));
  meta.appendChild(el("dd", null, hace(r.desde)));
  meta.appendChild(el("dt", null, "trigger"));
  meta.appendChild(el("dd", null, r.trigger || "—"));
  if (r.modelo) {
    meta.appendChild(el("dt", null, "modelo"));
    meta.appendChild(el("dd", null, r.modelo));
  }
  if (r.operacion) {
    meta.appendChild(el("dt", null, "operación"));
    meta.appendChild(el("dd", null, r.operacion));
  }
  if (r.pendientes && r.pendientes.length) {
    meta.appendChild(el("dt", null, "pendientes"));
    meta.appendChild(el("dd", null, r.pendientes.join(", ")));
  }
  if (r.resultado !== null && r.resultado !== undefined) {
    meta.appendChild(el("dt", null, "resultado"));
    meta.appendChild(el("dd", null, String(r.resultado)));
  }
  if (r.motivo) {
    meta.appendChild(el("dt", null, "motivo"));
    meta.appendChild(el("dd", null, r.motivo));
  }
  c.appendChild(meta);

  const log = el("pre","log");
  log.textContent = (r.log && r.log.length) ? r.log.join("\n") : "(sin salida todavía)";
  c.appendChild(log);
  return c;
}
function evento(e) {
  const d = el("div","evento");
  d.appendChild(el("span","hora", (e.ts || "").slice(11,19)));
  d.appendChild(el("span","quien", e.rol || ""));
  d.appendChild(el("span","accion", e.accion || ""));
  const detalle = Object.entries(e)
    .filter(([k,v]) => !["ts","rol","accion"].includes(k) && v !== null && v !== "")
    .map(([k,v]) => k + "=" + v).join("  ");
  d.appendChild(el("span","detalle", detalle));
  return d;
}
async function refrescar() {
  try {
    const r = await fetch("/api/estado", {cache:"no-store"});
    const d = await r.json();
    document.getElementById("roles").replaceChildren(...d.roles.map(tarjeta));
    document.getElementById("eventos").replaceChildren(
      ...(d.eventos.length ? d.eventos.map(evento) : [el("span","vacio","sin eventos")]));
    const activos = d.roles.filter(x => x.estado === "trabajando").length;
    document.getElementById("resumen").textContent =
      d.roles.length + " roles · " + activos + " trabajando";
    document.getElementById("actualizado").textContent = "actualizado " + hace(d.generado);
  } catch (err) {
    document.getElementById("actualizado").textContent = "sin conexión con la vista";
  }
}
refrescar();
setInterval(refrescar, 2000);
</script>
</body>
</html>
"""


def crear_handler(cfg_path, estado_dir=None, buzon_dir=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            pass

        def _enviar(self, codigo, tipo, cuerpo):
            datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(datos)

        def do_GET(self):
            ruta = urlparse(self.path)
            try:
                if ruta.path in ("/", "/index.html"):
                    return self._enviar(200, "text/html; charset=utf-8", HTML)
                if ruta.path == "/api/estado":
                    estado = construir_estado(cfg_path, estado_dir, buzon_dir)
                    return self._enviar(200, "application/json; charset=utf-8",
                                        json.dumps(estado, ensure_ascii=False))
                if ruta.path == "/api/log":
                    rol = (parse_qs(ruta.query).get("rol") or [""])[0]
                    datos = watcher.reparto_mod.cargar(cfg_path)
                    base = os.path.dirname(os.path.abspath(cfg_path))
                    carpeta = estado_dir or os.path.join(base, ".watcher")
                    if rol not in datos.get("roles", {}):
                        return self._enviar(404, "text/plain; charset=utf-8", "rol desconocido")
                    texto = "\n".join(tail(os.path.join(carpeta, "logs", f"{rol}.log"), 200))
                    return self._enviar(200, "text/plain; charset=utf-8", texto)
                return self._enviar(404, "text/plain; charset=utf-8", "no encontrado")
            except FileNotFoundError as exc:
                return self._enviar(500, "application/json; charset=utf-8",
                                    json.dumps({"error": str(exc)}))
            except Exception as exc:  # noqa: BLE001
                return self._enviar(500, "application/json; charset=utf-8",
                                    json.dumps({"error": repr(exc)}))

    return Handler


def main(argv):
    args = argv[1:]
    cfg = _valor(args, "--config") or os.environ.get("REPARTO_CONFIG") or "reparto.json"
    cfg = os.path.expanduser(cfg)
    puerto = int(_valor(args, "--puerto") or 3040)
    host = _valor(args, "--host") or "127.0.0.1"
    estado_dir = _valor(args, "--estado-dir")
    buzon_dir = _valor(args, "--buzon")
    try:
        datos = watcher.reparto_mod.cargar(cfg)
    except FileNotFoundError as exc:
        print(f"NO SE PUDO LEER: {exc}")
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        print(f"JSON INVALIDO: {exc}")
        return EXIT_ERROR
    base = os.path.dirname(os.path.abspath(cfg))
    estado_dir = watcher._abs(estado_dir or ".watcher", base)
    buzon_dir = watcher._abs(buzon_dir or (datos.get("buzon") or "buzon"), base)

    servidor = ThreadingHTTPServer((host, puerto), crear_handler(cfg, estado_dir, buzon_dir))
    print(f"vista: http://{host}:{servidor.server_address[1]}/")
    print(f"config: {os.path.abspath(cfg)}")
    print(f"roles: {', '.join(datos.get('roles', {}))}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
