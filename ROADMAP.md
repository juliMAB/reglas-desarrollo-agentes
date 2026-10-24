# ROADMAP — v2

> Regla de la casa: el documento no se toca sin un ciclo que lo justifique. Cada ítem entra
> cuando hay una corrida real que lo pide, no por prolijidad.

## M1 — El usuario dentro del ciclo ✅

- `tipo: humano` en `reparto.json`: sin modelo, sin entorno, trigger `usuario`.
- Estado `esperando_usuario` en el handoff.
- El usuario responde con `de: "usuario"` y `reply_to`, como cualquier rol.
- Regla: se le pide solo lo que el sistema no puede resolver (decisión, acceso, aceptación, acción física).
- CLI: `ver` distingue humanos; `set --tipo humano` limpia modelo y entorno; 16 tests.

## M2 — Watcher: el trigger real ✅

- `comando` por rol: texto (`/bin/sh -c`, `cmd /c`) o lista de argumentos. Recibe el mensaje por
  variables de entorno, no por argumentos.
- `herramientas/watcher/watcher.py`: mira `buzon/<rol>/`, ejecuta el comando del rol que
  corresponde, en su `cwd`, con timeout.
- Respeta `trigger.modo`: `agente` (mensaje nuevo), `tiempo` (cada `cada`), `usuario` (nunca).
- Lock por rol con pid: dos mensajes no despiertan dos procesos. Lock con pid muerto se limpia.
- Anti-repetición por firma (mtime + tamaño); `--seco` para ensayar; `estado <rol>` para ver pendientes.
- Criterio de aceptación cumplido en tests: mensaje en `buzon/qa/` despierta al QA sin intervención
  humana, y con el lock tomado no hay segunda ejecución. 15 tests del watcher, 24 del CLI.

## M3 — Validador de handoffs

- El CLI actual valida el reparto, no el mensaje.
- Validar: `handoff_id` único, `estado` en la lista, `de`/`para` existentes en el reparto, `reply_to`
  apuntando a un handoff real, artefactos por referencia y no pegados.
- Códigos 0/1/2, igual que el resto.

## M4 — Transporte: hub de `agentes-chat`

- El contrato de handoff es el contenido; el hub es una implementación.
- Conectar sin cambiar el documento: adaptador que traduce handoff ↔ mensaje del hub.
- Requisito: no atar el addon a PowerShell ni a una máquina.

## Fuera de alcance

- Interfaz gráfica.
- Selección automática de modelos.
- Notificaciones push.
