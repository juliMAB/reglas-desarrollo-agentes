# reparto.md — quién hace qué, cómo se despierta y a qué entra

> La configuración vive en `reparto.yaml`. Este archivo explica los campos y las reglas.
> Lo escribe el orquestador, lo aprueba el humano. Sin `reparto.yaml` válido, el ciclo no arranca.

## Campos por rol

| Campo | Qué define |
|---|---|
| `modelo` | proveedor/modelo exacto que ejecuta el rol |
| `entorno` | dónde corre: opencode, dsh, openclaw, claude-code, otro |
| `cwd` | carpeta donde arranca la sesión del rol |
| `acceso` | lista de rutas con modo `rw` o `ro` |
| `trigger` | cómo se entera de que tiene trabajo |
| `entrega` | qué artefactos deja al cerrar |

## Trigger

Tres modos, tal como se configuran:

| `modo` | Significa | Campos que aplican |
|---|---|---|
| `agente` | lo despierta otro agente al dejarle un mensaje | `desde`: lista de roles habilitados |
| `tiempo` | corre cada intervalo, haya o no mensaje | `cada`: `10m`, `1h`, `1d` |
| `usuario` | solo cuando el humano lo invoca | ninguno |

`desde` vacío equivale a "ninguno". Un rol con `modo: agente` y `desde: []` no se despierta nunca:
es un bloqueo declarado, no un olvido.

## Acceso

1. **`cwd` es la raíz del rol.** Todo lo que no esté declarado en `acceso` queda fuera, aunque esté
   dentro de `cwd`.
2. **`rw` solo donde hace falta.** El `constructor` escribe en su proyecto; el `qa` escribe
   únicamente en `evidencia/` y lee el resto.
3. **El build se lee, no se modifica.** Si el QA necesita el APK o el binario, va como `ro`.
4. **Se verifica al arrancar.** Si una ruta declarada no existe, el rol queda bloqueado. No se crea
   sola ni se asume.
5. **Un rol no otorga accesos.** Solo el humano, a través del orquestador.

## Reglas del reparto

1. **Un rol, una sesión.** Un agente no cambia de rol a mitad del trabajo.
2. **El que construye no aprueba.** Si es el único disponible, el trabajo queda "entregado sin
   aprobar", no "aprobado".
3. **Quien no tiene modelo asignado no arranca.** No lo sustituye el orquestador.
4. **Los permisos son por rol, no por persona.**
5. **El modelo es decisión del usuario.** El orquestador propone, no impone.
6. **Cambiar el reparto a mitad de ciclo** exige cerrar o reiniciar el ciclo.
7. **Independiente de la herramienta.** Los roles pueden mezclar entornos.
8. **El orquestador es un rol más**, con modelo y trigger propios. No es el humano ni el dueño de
   la herramienta.
9. **Todos con todos.** Cualquier rol escribe a cualquier otro por el buzón. La restricción de M8
   aplica a módulos de software, no a roles.

## Ejemplo mínimo

```yaml
roles:
  constructor:
    trigger: { modo: agente, desde: ["orquestador"] }
    acceso: [{ ruta: "~/proyectos/app", modo: rw }]
  qa:
    trigger: { modo: agente, desde: ["constructor"] }
    acceso: [{ ruta: "~/proyectos/app/build", modo: ro }]
  orquestador:
    trigger: { modo: usuario }
```

El archivo completo, con todos los campos, es `reparto.yaml`.
