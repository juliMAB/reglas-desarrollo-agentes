# handoff.md — qué viaja entre roles

> Un handoff es el paquete que un rol le deja a otro. Si no está en el paquete, no existe.
> El transporte (buzón de archivos, hub, cola) es indiferente: el contenido es este.

## 1. Envelope

```json
{
  "handoff_id": "beneficios-ctor-20261022T0116-01",
  "estado": "pedido",
  "de": "orquestador",
  "para": "constructor",
  "reply_to": null,
  "pedido": "app Android que muestre una frase del día desde un servicio propio",
  "skill": "reglas-desarrollo@v1.2.0",
  "reparto": "reparto.md#constructor",
  "artefactos": {
    "repo": "git@github.com:usuario/frase-del-dia.git",
    "commit": null,
    "contrato": "frase/v1.0.0",
    "evidencia": null
  },
  "criterios": [
    "muestra una frase con autor con el servicio arriba",
    "con el servicio caído muestra error y reintentar",
    "con lista vacía muestra estado vacío"
  ],
  "ts": "2026-10-22T01:16:00-03:00"
}
```

## 2. Estados

| Estado | Significa | Quién lo pone |
|---|---|---|
| `pedido` | trabajo asignado, sin empezar | orquestador |
| `en_curso` | rol trabajando | rol destino |
| `entregado` | artefactos listos para revisar | constructor |
| `aprobado` | QA verificó y aceptó | qa |
| `reabierto` | QA encontró un fallo | qa |
| `bloqueado` | falta un dato, acceso o modelo | cualquier rol |

Un `reabierto` siempre incluye: qué falló, cómo se reproduce, y qué evidencia lo muestra.

## 3. Reglas

1. **Sin `handoff_id` no se responde.** Un mensaje sin id es una conversación nueva, no una respuesta.
2. **Los artefactos viajan por referencia**, no pegados: repo + commit + ruta. Un archivo pegado en
   un mensaje no es evidencia, porque no se puede verificar.
3. **Un handoff = un objetivo.** Tres cosas son tres handoffs.
4. **El QA no recibe el razonamiento del constructor.** Recibe el pedido, los criterios y los
   artefactos. Si necesita el "por qué", el entregable está mal documentado.
5. **No viajan secretos.** Credenciales, tokens y claves quedan en el host; el handoff referencia
   el nombre del secreto, nunca el valor.
6. **El estado lo cambia el rol que corresponde.** El constructor no se pone `aprobado`.
7. **Silencio no es avance.** Un handoff sin cambio de estado en el plazo acordado se reporta como
   bloqueado.
8. **Si el proyecto no es un repo git**, `repo` va en `null`, `commit` en `null` y se agrega
   `carpeta` con la ruta. Una ruta local no se presenta como repo: el QA no puede fijar qué versión
   revisó si no hay commit.

## 4. Flujo mínimo

```
orquestador ──pedido──► constructor ──entregado──► qa
                              ▲                      │
                              └──── reabierto ────────┤
                                                     │
orquestador ◄──────────── aprobado ──────────────────┘
```

## 5. Qué NO viaja

- Transcripciones completas de la sesión.
- Archivos binarios (APK, capturas) dentro del mensaje: van por ruta o por repo.
- Decisiones sin registro: si una decisión afecta el entregable, va al `README.md` del proyecto o
  al `CHANGELOG`.

## 6. Entregar no es actualizar el propio buzón

Entregar significa depositar el handoff en el buzón del **destinatario**:

1. Copiar el archivo a `buzon/<destinatario>/`.
2. Dejar `para` en el destinatario y `estado` en `entregado`.
3. Conservar el `handoff_id` y agregar `reply_to` con el id del pedido original.
4. El archivo que queda en el buzón propio es registro, no entrega.

Un handoff que solo cambió de estado en el buzón del emisor **no fue entregado**: el destinatario
no lo ve y el ciclo queda detenido sin error visible.
