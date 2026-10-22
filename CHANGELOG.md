# CHANGELOG — addon de agentes

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
