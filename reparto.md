# reparto.md — quién hace qué

> Este archivo lo decide el usuario, por conversación. El orquestador lo escribe y el usuario lo
> aprueba. Es configuración, no código: cambiarlo no requiere tocar nada más.
> Sin este archivo completo, el trabajo no arranca.

## Formato

| Rol | Modelo | Puede | No puede | Entrega |
|---|---|---|---|---|
| `constructor` | `<proveedor/modelo>` | crear y modificar el proyecto; correr su build | aprobar su propio trabajo; tocar la evidencia del QA | repo + commit + `evidencia/` |
| `qa` | `<proveedor/modelo>` | instalar, ejecutar, capturar; reabrir | modificar código del proyecto | veredicto en `evidencia/QA-<slug>.md` |
| `orquestador` | `<proveedor/modelo>` | asignar, desbloquear, integrar | construir o aprobar | `reparto.md` actualizado + estado |
| `verificador` (opcional) | `<proveedor/modelo>` | auditar contratos, puertos, evidencia | construir, aprobar producto | informe de auditoría |

## Reglas del reparto

1. **Un rol, una sesión.** Un agente no cambia de rol a mitad del trabajo.
2. **El que construye no aprueba.** Aunque sea el único disponible: en ese caso el trabajo queda
   "entregado sin aprobar", no "aprobado".
3. **Quien no tiene modelo asignado no arranca.** No se sustituye por el orquestador.
4. **Los permisos son por rol, no por persona.** El `constructor` no edita `evidencia/QA-*`.
5. **El modelo es una decisión del usuario.** El orquestador propone, no impone.
6. **Cambiar el reparto en medio de un ciclo** exige cerrar el ciclo actual o reiniciarlo, no
   mezclar quién empezó con quién termina.
7. **Independiente de la herramienta.** Los roles pueden correr en la misma herramienta o en
tres distintas. El addon no asume OpenClaw, ni sesiones de un agente en particular, ni un
orquestador central. Solo asume que cada rol puede leer estos archivos y usar el buzón.
8. **El orquestador también es un rol con modelo asignado.** No es el humano ni el dueño de la
herramienta; es un agente más, sujeto a las mismas reglas. El humano decide y aprueba el reparto.

## Ejemplo

| Rol | Modelo | Puede | No puede | Entrega |
|---|---|---|---|---|
| `constructor` | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | crear el proyecto, build, pruebas locales | aprobar; editar evidencia del QA | repo + `evidencia/<slug>.md` |
| `qa` | `openrouter/stealth/space-bunny-alpha` | instalar, ejecutar, capturar, reabrir | tocar `src/` | `evidencia/QA-<slug>.md` con veredicto |
| `orquestador` | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | asignar, desbloquear, integrar | construir o aprobar | estado del ciclo |
| `verificador` (opcional) | `sin asignar` | auditar contratos, puertos, evidencia | construir, aprobar producto | informe de auditoría |

## Asignación pendiente

Si un rol figura como `sin asignar`, el ciclo está bloqueado. El orquestador lo reporta y espera.
