# CHANGELOG — addon de agentes

## 2.0.0-dev — 2026-10-24

- **M2: watcher.** `comando` por rol (texto o lista) y `herramientas/watcher/watcher.py`:
  despierta al rol por mensaje nuevo o por intervalo, con lock por pid, anti-repetición por firma,
  timeout y `--seco`. El mensaje viaja por variables de entorno, no por argumentos.
- CLI: valida `comando`, lo muestra en `ver` y lo escribe con `set --comando`. 24 tests.
- Corregido en prueba real: logs del watcher con line buffering (stdout a archivo no se perdía al cerrar) y flags con valor (`--intervalo 1`) ya no se toman como nombres de rol. 16 tests del watcher.
- **M1: el usuario como rol.** `tipo: humano` sin modelo ni entorno; trigger `usuario`.
- Estado `esperando_usuario` para decisiones, accesos y aceptaciones humanas.
- Regla: al usuario se le pide solo lo que el sistema no puede resolver.
- CLI: `ver` distingue humanos; `set --tipo humano` limpia modelo/entorno; 16 tests.
- Nuevo `ROADMAP.md` con los hitos de v2. 15 tests del watcher.

## 1.0.0 — 2026-10-24

- Entregar = copiar el handoff al buzón del destinatario (`handoff.md` §6).
- Accesos por defecto: `buzon/<rol>` rw, buzón del destinatario para quien entrega, QA `ro` sobre herramientas.
- Ciclo completo validado con dos modelos distintos y veredicto de QA con evidencia.

## 0.6 — 2026-10-22

- CLI: las rutas relativas se resuelven contra el directorio del `reparto.json`, no contra el cwd.
  Validar desde cualquier lado da el mismo resultado. 12 tests.

## 0.5 — 2026-10-22

- Regla: el QA recibe `ro` sobre las herramientas que necesita para verificar (validador, scripts).
- `handoff.md`: si el proyecto no es repo git, `repo` y `commit` van en `null` y se agrega `carpeta`.
- CLI: `entrega` vacía pasa a aviso en `validar`.

## 0.4 — 2026-10-22

- Formato canónico `reparto.json`: sin dependencias YAML, legible y escribible por stdlib.
- CLI `herramientas/reparto/reparto.py`: `validar`, `ver`, `set`, `acceso`. 11 tests.
- Códigos 0/1/2 igual que el validador: válido, inválido, no se pudo leer.
- `--rutas` verifica que las rutas declaradas existan, para el arranque del ciclo.

## 0.3 — 2026-10-22

- `reparto.yaml`: configuración por rol con modelo, entorno, cwd, accesos (`rw`/`ro`) y trigger.
- Trigger con tres modos: `agente`, `tiempo`, `usuario`, con `desde` y `cada` según corresponda.
- Permisos por ruta: el QA lee el build y escribe solo en `evidencia/`.
- Validación al arrancar: una ruta declarada que no existe bloquea el rol.

## 0.2 — 2026-10-22

- Nuevo `trigger.md`: el sistema son dos piezas, buzón + trigger. Sin trigger, el buzón está muerto.
- Cuatro tipos de trigger: loop del entorno, watcher, hook y obligación en el turno (piso universal).
- Regla de suscripción: un rol sin trigger ni obligación de leer el buzón no está en el sistema.
- Mensajería **todos con todos** entre roles; la restricción de M8 aplica a módulos, no a roles.
- Independencia de herramienta explícita: opencode, DeepSeek Harness, OpenClaw, Claude Code o genérico.

## 0.1 — 2026-10-22

- Estructura inicial: `README.md`, `reparto.md`, `handoff.md`.
- Reparto de roles definido como decisión del usuario, escrita por el orquestador.
- Contrato de handoff con envelope, seis estados y reglas de independencia.
- Sin transporte conectado: el documento describe el contenido, no el canal.

Dependencia declarada: `reglas-desarrollo@v1.2.0`.
