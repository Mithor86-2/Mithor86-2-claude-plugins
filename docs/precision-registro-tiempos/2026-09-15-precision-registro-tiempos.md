# precision-registro-tiempos — 2026-09-15

## Descripción
Corrige dos defectos de precisión del registro de tiempos de `gitflow-es`, detectados al analizar por qué cuatro ramas ya cerradas habían registrado 0s de trabajo. El primero: la espera por una aprobación de permiso caía dentro de la ventana `prompt → stop` y se cobraba como *Trabajo*; ahora se clasifica el aviso, se cierra la espera con la respuesta del usuario y el intervalo va a un rubro propio, **Espera de aprobación**. El segundo: la validación de tiempos muertos consultaba `git log <base>..<rama>` al *leer* el reporte, rango que queda vacío apenas la rama se mergea y se borra, así que `/git finish` ahora congela los timestamps de los commits en el propio log antes del merge y el reporte cae a ellos cuando git ya no puede responder.

## Cambios de lógica de negocio
- **Sexto rubro en el modelo de tiempos**: `total (reloj) = trabajo + trabajo_externo + pruebas + espera_de_aprobación + espera_usuario + inactividad`. La espera de aprobación sale de la ventana de trabajo y suma a la **espera total** (`wait_total = wait + idle_user + approval`), pero **no** al tiempo efectivo (`efectivo = trabajo + pruebas`): ese rato lo decide quien aprueba, no Claude.
- **Clasificación defensiva de los avisos**: el hook de `Notification` decide si el aviso es `permission`, `idle` u `other` mirando `notification_type`, `message` y `title` con patrones en español e inglés, porque el tipo que manda Claude Code no es un contrato estable. Ante la duda se clasifica como `other` y **no se descuenta nada**: se prefiere subestimar la espera antes que inventarla.
- **Cierre de la espera de aprobación por la respuesta, no por el aviso**: el aviso de permiso es un punto en el tiempo, no un intervalo. Que cualquier herramienta corra (`PostToolUse` / `PostToolUseFailure`) prueba que el permiso se concedió y cierra la espera con un evento `notify_end`; cuando el permiso se rechaza no hay herramienta que correr, así que también cierran el fin de turno (`stop`), el siguiente `prompt`, el `session_end` y el `branch_finish`. Un sello en disco (`aprobacion-<rama>.stamp`) garantiza que la espera se cierre una sola vez y que un aviso de inactividad no deje espera pendiente.
- **La espera de aprobación solo cuenta dentro de una ventana de trabajo**: los intervalos se intersectan con las ventanas `prompt → stop` y se les resta el tiempo de pruebas, para que un permiso pedido en un hueco no se cuente dos veces (ahí ya es espera del usuario o inactividad). Un permiso pedido y una sesión cortada sin respuesta cierra en el final del reporte y lo marca como estimado.
- **Evidencia de commits congelada antes del merge**: `/git finish` invoca `--mark branch_finish`, que ahora escribe un evento `commit_times` con los timestamps de los commits de la rama **antes** de la marca de cierre y, por tanto, antes del merge y de remover el worktree. Sin esto una rama cerrada nunca podía justificar sus tiempos muertos, que es justo cuando se lee el reporte.
- **Fallback al log congelado en la lectura del reporte**: la rama viva se sigue consultando a git; la ya mergeada cae a los timestamps persistidos en el log. Si la evidencia está desactivada (`gitflow-es.evidence off`) no se congela ni se consulta nada.

## Archivos modificados
- `plugins/gitflow-es/hooks/time-tracker.py` — clasificación del aviso (`notification_kind`), apertura y cierre de la espera de aprobación con sello en disco, cierre enganchado en `UserPromptSubmit`, `Stop` y `PostToolUse`/`PostToolUseFailure`, y `freeze_commit_times` invocado desde `--mark branch_finish`.
- `plugins/gitflow-es/hooks/timelog.py` — rubro `approval` en la agregación: pintado de los intervalos permiso → respuesta, acotados a las ventanas de trabajo y sin el tiempo de pruebas; `CLOSES_APPROVAL`; `persisted_commit_times` y el fallback de `branch_report_data` a los commits congelados.
- `plugins/gitflow-es/hooks/time-report.py` — fila del rubro nuevo en la tabla del reporte por rama.
- `plugins/gitflow-es/hooks/i18n.py` — clave `tr_bucket_approval` en español («Espera de aprobación») e inglés («Waiting on approval»).
- `plugins/gitflow-es/skills/git/SKILL.md` — el paso de `/git finish` explica que la evidencia se congela antes de remover el worktree **y** antes del merge, porque después `git log <base>..<rama>` ya no devuelve nada.
- `plugins/gitflow-es/skills/tiempos/SKILL.md` — tabla de rubros a seis, la nota de que la espera de aprobación no se le cobra a Claude y la fila de `/git finish` al día.
- `plugins/gitflow-es/README.md` — ejemplo de reporte con el rubro nuevo y su espera total recalculada, y la tabla «Qué mide» a seis rubros.
- `plugins/gitflow-es/tests/test_time_tracker.py` — 19 casos nuevos: clasificación de avisos y ciclo de vida de la espera de aprobación, más el congelado de commits y su orden respecto de la marca de cierre.
- `plugins/gitflow-es/tests/test_timelog.py` — 10 casos nuevos de agregación del rubro `approval` y del rescate por commits congelados; `suma_rubros` incluye el rubro nuevo, de modo que los tests preexistentes de partición del reloj siguen cubriendo la invariante.
- `CHANGELOG.md` — dos entradas en `Fixed` de `[Unreleased]`, una por defecto corregido.

## Paquetes instalados / actualizados
| Paquete | Versión | Motivo |
|---------|---------|--------|
| Ninguno | — | La rama no toca manifiestos de dependencias; todo corre con la stdlib de Python y `pytest` ya presente |

## Pruebas ejecutadas

### Unitarias

Comando: `python3.8 -m pytest plugins/gitflow-es/tests -q` dentro del worktree de la rama → **224 passed**.

| Archivo de test | Tests | Pasaron | Fallaron |
|----------------|-------|---------|---------|
| `test_time_tracker.py` (45 en total; 19 nuevos en esta rama) | 45 | 45 | 0 |
| `test_timelog.py` (54 en total; 10 nuevos en esta rama) | 54 | 54 | 0 |
| **Casos nuevos de esta rama** | **29** | **29** | **0** |
| Suite completa (incluye los archivos no modificados aquí) | 224 | 224 | 0 |

#### `test_time_tracker.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | `notification_kind` clasifica el aviso (8 casos) | `permission_request`, `tool_permission`, «needs your permission», «necesita autorización», `idle_prompt`, «waiting for your input», texto ajeno y cadena vacía | `permission` ×4, `idle` ×2, `other` ×2 | ✅ |
| 2 | El permiso se reconoce por el texto, no solo por el tipo | `Notification` con `message: "Claude needs your permission"` | Evento `notify` con `k=permission` | ✅ |
| 3 | Correr la herramienta cierra la espera de aprobación | `Notification` de permiso → `PostToolUse` de `Write` | Eventos `notify`, `notify_end` | ✅ |
| 4 | Un permiso rechazado se cierra al terminar el turno | `Notification` de permiso → `Stop` | Eventos `notify`, `notify_end`, `stop` | ✅ |
| 5 | El prompt siguiente también cierra la espera | `Notification` de permiso → `UserPromptSubmit` | Eventos `notify`, `notify_end`, `prompt` | ✅ |
| 6 | La espera se cierra una sola vez | Permiso → `PostToolUse` → `Stop` | Un único `notify_end` | ✅ |
| 7 | Un aviso de inactividad no deja espera pendiente | `idle_prompt` → `Stop` | Sin `notify_end`; el `notify` queda con `k=idle` | ✅ |
| 8 | El cierre de rama congela los commits | `freeze_commit_times` con 2 commits | Devuelve `2` y escribe `commit_times` con ambos timestamps | ✅ |
| 9 | Sin commits no se escribe el congelado | Rama sin commits propios | Devuelve `0`, sin evento `commit_times` | ✅ |
| 10 | Con la evidencia apagada no se congela nada | `gitflow-es.evidence off` | Devuelve `0`, sin evento `commit_times` | ✅ |
| 11 | La marca de cierre congela los commits antes de la marca | `--mark branch_finish --note "cerrada"` | `commit_times` presente y anterior a `branch_finish` | ✅ |
| 12 | La marca de inicio no congela commits | `--mark branch_start --note "arranca"` | Sin evento `commit_times` | ✅ |

#### `test_timelog.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | La espera de permiso no se cobra como trabajo | `prompt` 0s, `notify(permission)` 10s, `notify_end` 70s, `stop` 80s | `approval = 60`, `work = 20`, los rubros suman el total | ✅ |
| 2 | El aviso de inactividad no descuenta trabajo | `notify(idle)` dentro de la ventana de trabajo | `approval = 0`, `work = 80` | ✅ |
| 3 | Un aviso sin clasificar no descuenta trabajo | `notify` sin campo `k` | `approval = 0`, `work = 80` | ✅ |
| 4 | Un permiso fuera de la ventana de trabajo no descuenta | `notify(permission)` en el hueco entre dos turnos | `approval = 0`, `wait = 20`, sin doble conteo | ✅ |
| 5 | Un permiso rechazado se cierra con el fin del turno | `notify(permission)` 10s, `stop` 50s | `approval = 40`, `work = 10` | ✅ |
| 6 | La espera de aprobación suma a la espera total | Turno con un permiso pedido y resuelto | `wait_total = wait + idle_user + approval` | ✅ |
| 7 | Varias esperas de permiso en el mismo turno | Dos ciclos `notify` / `notify_end` en una ventana de 100s | `approval = 40`, `work = 60` | ✅ |
| 8 | `persisted_commit_times` lee la lista congelada | Evento `commit_times` con dos timestamps | Los dos timestamps, en orden | ✅ |
| 9 | `persisted_commit_times` ignora lo que no sirve | `m` que no es lista; lista con `"x"` y `None` | Solo el valor numérico válido | ✅ |
| 10 | Los commits congelados rescatan el hueco de una rama cerrada | Log de rama cerrada agregado con y sin `commit_times` | Sin rescate `external = 0`; con rescate `external > 0`, `evidence_commits = 2` y los rubros suman el total | ✅ |

### Pruebas manuales / de integración
| # | Escenario | Pasos / Datos de entrada | Resultado esperado | Resultado obtenido | ✅/❌ |
|---|-----------|--------------------------|-------------------|-------------------|------|
| 1 | Espera de aprobación real | Provocar una petición de permiso, tardar ~1 min en aceptarla y pedir `/tiempos` | Ese rato aparece en *Espera de aprobación*, no en *Trabajo*; los seis rubros suman el total | Pendiente | ⚠️ |
| 2 | Permiso rechazado | Provocar una petición de permiso y rechazarla | La espera se cierra igual (sin herramienta que corra) y no se cobra como trabajo | Pendiente | ⚠️ |
| 3 | Reporte de una rama ya cerrada | Cerrar una rama con `/git finish` y consultar su reporte después del merge | Los huecos con commits siguen justificados como *trabajo fuera de sesión* gracias a los timestamps congelados | Pendiente | ⚠️ |
| 4 | Reporte en inglés | `gitflow-es.language en` y pedir el reporte | El rubro aparece como *Waiting on approval* | Pendiente | ⚠️ |
| 5 | A completar por el autor | — | — | — | ⚠️ |

## Resultado
⚠️ Pendiente de revisión — suite automatizada en verde (224/224); las pruebas manuales siguen pendientes de validación humana.

---

### Notas

- La suite se ejecutó con `python3.8 -m pytest plugins/gitflow-es/tests -q` dentro del worktree de la rama: **224 passed** (195 eran el corte de `develop`; los 29 restantes son los casos nuevos de esta rama). `python3` (3.13) no tiene `pytest` instalado en este equipo.
- El diff contra `develop` suma 460 inserciones y 13 eliminaciones en 10 archivos: por debajo del umbral de 500 líneas, así que se leyó completo y las descripciones por archivo salen del diff, no solo del mensaje de commit.
- Los escenarios manuales 1 a 4 se derivaron de los comportamientos que cambia el diff; ninguno se ejecutó. La fila 5 queda abierta para lo que el autor quiera agregar.
- Contexto del hallazgo (fuera del diff): los dos defectos se detectaron analizando por qué cuatro ramas ya cerradas habían registrado 0s de trabajo.
