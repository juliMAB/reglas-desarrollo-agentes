# trigger.md — cómo se entera un agente de que tiene un mensaje

> Un buzón sin trigger es un cajón cerrado. El mensaje existe, pero nadie lo lee.
> El sistema son dos piezas, no una: **buzón** (el dato) **+ trigger** (lo que despierta).

## 1. Buzón

El mensaje vive como datos en un lugar compartido:

- archivos (`buzon/<rol>/msg-*.json`), o
- un endpoint HTTP que devuelve JSON.

Formato del mensaje: el de `handoff.md`. Nada más. No se depende de un lenguaje, un sistema
operativo ni una herramienta.

**Todos con todos.** Cualquier rol puede escribirle a cualquier otro. El buzón es un espacio
común, no una jerarquía. La restricción de "no se hablan entre sí" aplica a **módulos de software**
(regla M8 de la skill), no a roles de un mismo ciclo.

## 2. Trigger

Cuatro formas, de más automática a más manual. Cualquiera sirve si está declarada:

| Tipo | Cómo funciona | Requiere |
|---|---|---|
| **Loop del entorno** | el propio entorno corre el agente cada N minutos | una tarea programada |
| **Watcher** | un proceso ve el mensaje y ejecuta al agente (`exec` de una CLI) | `comando` por rol |
| **Hook** | el entorno dispara un turno cuando llega un evento | soporte de hooks |
| **Obligación en el turno** | la instrucción del rol dice "leé el buzón al inicio y al final" | nada, solo disciplina |

La cuarta es el piso universal. Funciona en cualquier chat con IA, incluso en uno donde el humano
aprieta Enter. Es más lenta, pero no depende de ninguna capacidad especial.

## 3. Suscripción

Un rol está **suscripto** si cumple al menos una:

- tiene un trigger que lo despierta, o
- su instrucción de arranque obliga a leer el buzón al inicio y al final de cada turno.

Si no cumple ninguna, no está en el sistema, aunque tenga rol asignado.

### Modo declarado → mecanismo

El `modo` en `reparto.yaml` no impone una tecnología; dice qué tiene que pasar.

| `modo` | Qué tiene que pasar | Mecanismo típico |
|---|---|---|
| `agente` | el rol se despierta cuando otro le deja un mensaje | watcher o hook |
| `tiempo` | el rol revisa cada intervalo, haya o no mensaje | loop del entorno o cron |
| `usuario` | el rol actúa solo cuando el humano lo invoca | el humano, o obligación en el turno |

En los tres casos, si no hay automatización disponible, rige el piso universal: leer el buzón al
inicio y al final del turno. Eso convierte cualquier chat en un participante válido, más lento
pero funcional.

## 4. Watcher incluido

`herramientas/watcher/watcher.py` implementa el mecanismo sin depender de la herramienta:

```
watcher.py --todos                 # loop: mira todos los buzones
watcher.py qa --once               # una pasada, útil para cron o para probar
watcher.py estado qa               # qué tiene pendiente el rol
watcher.py qa --seco               # muestra qué haría, sin ejecutar ni recordar
```

Qué garantiza:

- **Solo despierta por trabajo real.** Un handoff despierta si `para` es el rol, `de` es otro rol,
  el `estado` pide acción (`pedido`, `entregado`, `reabierto`, `bloqueado`, `esperando_usuario`) y
  `de` está en `desde`.
- **No repite.** Guarda firma (mtime + tamaño) por archivo en `.watcher/<rol>.json`. El mismo
  archivo sin cambios no despierta dos veces; si el rol lo modifica, sí.
- **No superpone.** Un lock por rol (`.watcher/<rol>.lock`, con pid) impide que dos mensajes
  despierten dos procesos a la vez. Un lock con pid muerto se limpia solo.
- **Respeta el modo.** `usuario` nunca se despierta; `tiempo` corre cada `cada`; `agente` solo con
  mensaje.
- **Registra el resultado.** Cada despertar queda con código de salida. Un comando fallido no se
  reintenta en loop hasta que el archivo cambie.

El mensaje no se pasa por argumentos: el comando lo lee de `REPARTO_ARCHIVO` (y
`REPARTO_HANDOFF_ID`). Por eso el mismo comando sirve para cualquier mensaje.

## 5. Ejemplos por entorno

Son ejemplos, no requisitos. La regla es la de arriba.

| Entorno | Trigger posible |
|---|---|
| OpenClaw | automations o hooks |
| opencode | script que lo ejecuta con `run` cuando hay mensaje |
| DeepSeek Harness | plugin o hook del harness |
| Claude Code | hook de evento |
| Chat genérico | obligación en el turno, o el humano pegando el mensaje |
| Consola | cron + `exec` del agente |

## 6. Regla de oro

Si un rol no puede ser despertado, el ciclo no se apoya en él. Se declara bloqueado, no se asume
que "va a mirar".
