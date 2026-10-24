# reglas-desarrollo-agentes

Addon de la skill [reglas-desarrollo](https://github.com/juliMAB/reglas-desarrollo) (tag `v1.2.0`).

Define **quién hace cada parte y cómo se pasa el trabajo** entre agentes. No repite las reglas de
construcción: las usa.

El usuario puede ser parte del ciclo como un rol más (`tipo: humano`): recibe handoffs, aprueba
puertas, responde bloqueos y veta. No se le pide nada que un rol pueda hacer.

## Qué es y qué no es

**Es:**
- El reparto de roles y modelos, decidido por el usuario.
- El contrato de handoff entre roles.
- Las reglas de independencia (quién puede aprobar qué).

**No es:**
- El transporte. El buzón, el hub y los wake-ups son una implementación, no este documento.
- Las reglas de arquitectura, puertos o QA: viven en la skill v1.2.0.
- Un componente de OpenClaw. El addon no depende de OpenClaw ni de ningún orquestador central:
  los roles pueden correr en sesiones separadas de la misma herramienta, o en herramientas
  distintas, siempre que puedan leer estos archivos y usar el buzón.

## Independencia de herramienta

Nada acá asume una plataforma. Sirve en cualquier entorno de chat con IA que pueda leer el buzón y
ejecutar un turno: OpenClaw, opencode, DeepSeek Harness, Claude Code, o uno sin nombre.

El sistema son dos piezas: **buzón** (los mensajes como datos) y **trigger** (lo que obliga al rol a
mirarlos). Ver `trigger.md`.

Cualquier rol puede escribirle a cualquier otro. El buzón es un espacio común, no una jerarquía.
El humano decide el reparto y lo aprueba; ningún agente es el dueño del ciclo.

## Dependencia

```
skill: juliMAB/reglas-desarrollo @ v1.2.0
```

Por tag, no por rama. Si la skill cambia, este addon decide cuándo migrar.

## Archivos

| Archivo | Qué define |
|---|---|
| `reparto.json` | Configuración real: modelos, entorno, cwd, accesos y triggers |
| `reparto.md` | Explicación de los campos, reglas y uso del CLI |
| `herramientas/reparto/` | CLI `reparto.py`: validar, ver, set, acceso (11 tests) |
| `handoff.md` | Qué viaja entre roles y en qué formato |
| `trigger.md` | Buzón + mecanismo que despierta a cada rol |
| `CHANGELOG.md` | Qué cambió y por qué |

## Cómo se usa

1. El usuario dice, en una conversación, qué modelo hace cada rol.
2. El orquestador escribe `reparto.md` con eso. El usuario lo revisa.
3. Cada rol arranca en su sesión con su parte de `reparto.md` y el `handoff.md`.
4. El trabajo se mueve por handoffs, no por conversación libre.

Sin `reparto.md` completo, el trabajo no arranca. Un rol sin modelo asignado es un bloqueo, no una
invitación a improvisar.

## Estado

Borrador. Sin transporte conectado todavía.
