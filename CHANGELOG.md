# CHANGELOG — addon de agentes

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
