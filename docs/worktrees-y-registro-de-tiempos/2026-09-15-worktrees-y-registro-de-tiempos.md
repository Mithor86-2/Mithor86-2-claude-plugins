# worktrees-y-registro-de-tiempos — 2026-09-15

## Descripción
Extiende el plugin `gitflow-es` con cuatro ajustes: diagnóstico y configuración guiada de git-flow al abrir sesión (`/git init`), la política de trabajar siempre en worktrees creados desde `develop` dejando el repo principal como worktree de control, un skill para repartir tareas independientes en worktrees paralelos y un registro local de tiempos por rama que separa trabajo, trabajo fuera de sesión, pruebas, espera del usuario e inactividad. De paso corrige el bloqueo indebido de `check_force_push` y las rutas muertas a las rules desde los subagentes, y publica la versión 0.10.0.

## Cambios de lógica de negocio
- **Worktrees obligatorios**: toda rama de trabajo nace en su propio worktree bajo `<padre-del-repo>/<repo>-worktrees/<tipo>-<slug>` (configurable con `gitflow-es.worktreeRoot`); el repo principal queda parado en `develop` como worktree de control y es el único sitio donde se cierran ramas. `hotfix/` mantiene su base en `main` como excepción estructural.
- **Cierre por postcondiciones, no por exit code**: `git-flow-avh 0.4.1` imprime «Summary of actions» y sale con código 0 aunque no mergee ni borre la rama. `/git finish` ahora verifica que la rama desapareció (`git branch --list`) y que sus commits están en `develop` (`git merge-base --is-ancestor`).
- **Nuevo bloqueo de seguridad**: `git flow <tipo> finish` dentro de un worktree linked queda bloqueado por el hook (único caso que corrompe el cierre). El resto de la política de worktrees solo emite avisos no bloqueantes, desactivables con `gitflow-es.worktrees off`.
- **`/git sync` sin checkouts**: pasa a `fetch --all --prune` más fast-forward de refs y `worktree prune`, porque `develop` y `main` quedan ocupados por worktrees.
- **Trabajo en paralelo reglado**: criterio de independencia entre tareas, una sola actualización de la base por lote, un ejecutor por worktree y cierres estrictamente secuenciales con refresco de las ramas vivas desde `develop` entre cierres.
- **Modelo de tiempos aditivo**: por rama, `total (reloj) = trabajo + trabajo_externo + pruebas + espera_usuario + inactividad`. Las pruebas se miden aparte pareando `PreToolUse`/`PostToolUse` por `tool_use_id` y se descuentan del trabajo; la espera se separa de la inactividad por el umbral `gitflow-es.idleThresholdMin` (default 15 min).
- **Validación de tiempos muertos con evidencia**: ningún hueco se declara tiempo muerto sin contrastarlo contra los `mtime` de los archivos que reporta `git status --porcelain` y los timestamps de los commits de la rama. Lo que tiene evidencia se reclasifica como trabajo fuera de sesión; se descartan las escrituras masivas (20+ archivos en 2 s) y se recortan los `mtime` futuros.
- **Descripción del trabajo capturada de fuentes mecánicas** (nunca inventada): descripción de la rama en `/git start`, primera línea de cada prompt y asunto de cada commit exitoso. Configurable con `gitflow-es.timeNotes` (`on` / `commits` / `off`).
- **Privacidad del registro**: el log vive en `<git-common-dir>/gitflow-es/tiempos/*.jsonl`, con append atómico (`O_APPEND`, una escritura ≤ 4 KB), y nunca aparece en `git status` ni se commitea.
- **Corrección de `check_force_push`**: evaluaba la línea completa y leía el `-ff` de `--no-ff` como flag de force, bloqueando comandos legítimos. Ahora cada check corre por segmento de comando y el lookbehind exige inicio de token.
- **Nuevas claves de configuración**: `worktreeRoot`, `worktrees`, `timeTracking`, `timeNotes`, `evidence`, `idleThresholdMin`, `externalGapMin`, `externalMargin`, `testPattern` y `timeLogDir`.

## Archivos modificados
- `plugins/gitflow-es/hooks/gitwt.py` — nuevo módulo compartido: resuelve rama y git-dir leyendo archivos (sin subprocesos), lista worktrees, cachea la configuración en disco y aplica throttle.
- `plugins/gitflow-es/hooks/timelog.py` — nuevo módulo del registro: append atómico, saneado y truncado de notas, agregación por pintado de intervalos, pareo de pruebas por `tool_use_id`, escaneo incremental de evidencia y reclasificación de huecos por clústeres.
- `plugins/gitflow-es/hooks/time-tracker.py` — nuevo hook multi-evento (SessionStart, UserPromptSubmit, Stop, PreToolUse, PostToolUse, PostToolUseFailure, Notification, SessionEnd) con modo CLI `--mark` / `--describe` / `--evidence`.
- `plugins/gitflow-es/hooks/time-report.py` — nuevo CLI de reporte (`--branch`, `--all`, `--format`) en ES/EN, con tabla de actividad y tiempo de calendario para el trabajo en paralelo.
- `plugins/gitflow-es/hooks/safety-check.py` — bloqueo del `git flow finish` en worktree linked, cuatro avisos de la política de worktrees y segmentación por comando en los checks (regresión del force-push).
- `plugins/gitflow-es/hooks/session-context.py` — detección de worktree de control vs. linked, listado de worktrees activos, checklist de configuración pendiente y línea opcional de tiempos.
- `plugins/gitflow-es/hooks/hooks.json` — registra `time-tracker.py` en sus ocho eventos y actualiza la descripción del conjunto de hooks.
- `plugins/gitflow-es/hooks/i18n.py` — claves ES/EN de sesión, configuración, guardas de worktree y reporte de tiempos.
- `plugins/gitflow-es/rules/git-flow.md` — secciones «Worktrees (obligatorio)» y «Trabajo en paralelo», con la resolución explícita de las contradicciones de reglas y la nota del stash global.
- `plugins/gitflow-es/skills/git/SKILL.md` — subcomando `/git init`, `start` y `finish` en modo worktree con verificación de postcondiciones, `sync` sin checkouts y subcomando `/git worktree`.
- `plugins/gitflow-es/skills/worktrees/SKILL.md` — skill nuevo: subcomandos `listar`, `nuevo`, `paralelo`, `cerrar` y `limpiar`, más la tabla de errores típicos de git con worktrees.
- `plugins/gitflow-es/skills/tiempos/SKILL.md` — skill nuevo: consulta, descripción, exportación y enganche con `/git start` y `/git finish`.
- `plugins/gitflow-es/agents/commit-message-writer.md` — corrige la referencia a las rules (`../../rules/` → `../rules/`, ruta muerta desde `agents/`).
- `plugins/gitflow-es/agents/feature-doc-writer.md` — misma corrección de ruta a las rules.
- `plugins/gitflow-es/tests/conftest.py` — fixtures nuevas `session_context`, `gitwt`, `timelog` y `tracker`.
- `plugins/gitflow-es/tests/test_session_context.py` — suite nueva del hook de contexto de sesión.
- `plugins/gitflow-es/tests/test_worktree_guard.py` — suite nueva de las guardas de worktree y la regresión del force-push.
- `plugins/gitflow-es/tests/test_plugin_structure.py` — suite nueva de validación estructural del plugin.
- `plugins/gitflow-es/tests/test_timelog.py` — suite nueva de agregación, evidencia y concurrencia del registro.
- `plugins/gitflow-es/tests/test_time_tracker.py` — suite nueva de los eventos del hook de tiempos.
- `plugins/gitflow-es/README.md` — secciones de worktrees, trabajo en paralelo, registro de tiempos y claves de configuración; badge de versión a 0.10.0.
- `README.md` — descripción del plugin con los skills `worktrees` y `tiempos`.
- `CHANGELOG.md` — bloque `[0.10.0]` agrupado en Added / Changed / Fixed / Tests.
- `plugins/gitflow-es/.claude-plugin/plugin.json` — versión 0.10.0, descripción y keywords al día.
- `.claude-plugin/marketplace.json` — versión 0.10.0, descripción y keywords sincronizadas con `plugin.json`.
- `docs/planes/2026-09-14-worktrees-y-registro-de-tiempos.md` — plan de implementación: alcance, decisiones, contradicciones resueltas, control de progreso y bitácora.

## Paquetes instalados / actualizados
| Paquete | Versión | Motivo |
|---------|---------|--------|
| Ninguno | — | La rama no toca manifiestos de dependencias; todo corre con la stdlib de Python y `pytest` ya presente |

## Pruebas ejecutadas

### Unitarias

Comando: `python3.8 -m pytest plugins/gitflow-es/tests -q` → **195 passed**.

| Archivo de test | Tests | Pasaron | Fallaron |
|----------------|-------|---------|---------|
| `test_session_context.py` | 8 | 8 | 0 |
| `test_worktree_guard.py` | 29 | 29 | 0 |
| `test_plugin_structure.py` | 22 | 22 | 0 |
| `test_timelog.py` | 44 | 44 | 0 |
| `test_time_tracker.py` | 26 | 26 | 0 |
| **Subtotal de archivos nuevos** | **129** | **129** | **0** |
| Suite completa (incluye `test_i18n.py` y `test_safety_check.py`, preexistentes) | 195 | 195 | 0 |

#### `test_session_context.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | Fuera de un repo git el hook no imprime nada | cwd sin `.git` | Salida vacía | ✅ |
| 2 | Repo sin commits guía al commit inicial | Repo recién creado | Mensaje de commit inicial | ✅ |
| 3 | Worktree de control en `develop` avisa que no se trabaja ahí | Repo principal en `develop` | Aviso «worktree de control» | ✅ |
| 4 | Worktree linked muestra su ruta y lista los worktrees | Worktree de una rama | Ruta del worktree + listado | ✅ |
| 5 | Sin git-flow muestra checklist y propone `/git init` | Repo sin `git flow init` | Checklist con ⬜ y oferta de `/git init` | ✅ |
| 6 | Con git-flow listo pero sin idioma, pide el idioma con checklist | `gitflow-es.language` ausente | Checklist pidiendo idioma | ✅ |
| 7 | El listado de worktrees parsea el porcelain, incluido `detached` | Salida de `git worktree list --porcelain` | Worktrees parseados correctamente | ✅ |
| 8 | La línea de tiempos queda silenciosa si falta el módulo `timelog` | Sin `timelog.py` disponible | Sin línea de tiempos y sin error | ✅ |

#### `test_worktree_guard.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | `finish` dentro del worktree linked se bloquea | cwd = worktree de la rama | Bloqueo del comando | ✅ |
| 2 | El bloqueo aplica a todos los tipos (3 casos) | `feature` / `hotfix` / `release` finish | Bloqueo en los tres | ✅ |
| 3 | `finish` desde el worktree de control no se bloquea | cwd = control | Sin bloqueo | ✅ |
| 4 | Sin `gitwt` disponible no se bloquea (fail-open) | Módulo ausente | Sin bloqueo | ✅ |
| 5 | `finish` con el worktree todavía vivo emite aviso | Worktree de la rama sin remover | Aviso no bloqueante | ✅ |
| 6 | `finish` sin nombre de rama usa la rama actual | `git flow feature finish` | Resuelve la rama del cwd | ✅ |
| 7 | Sin worktree vivo no hay aviso | Worktree ya removido | Sin aviso | ✅ |
| 8 | Crear rama sin worktree avisa (4 casos) | `git checkout -b`, `git switch -c`, `git flow feature start`, `git flow release start` | Aviso en los cuatro | ✅ |
| 9 | Crear rama con worktree en el mismo comando no avisa | `git worktree add -b ...` | Sin aviso | ✅ |
| 10 | La política desactivada silencia los avisos | `gitflow-es.worktrees off` | Sin avisos | ✅ |
| 11 | Parseo de `git worktree add` (4 casos) | `-b <rama> <ruta> <base>`, hotfix desde `main`, sin `-b`, `--detach` | Rama, ruta y base extraídas | ✅ |
| 12 | Base `develop` no avisa | `worktree add` desde `develop` | Sin aviso | ✅ |
| 13 | Base remota `origin/develop` no avisa | `worktree add` desde `origin/develop` | Sin aviso | ✅ |
| 14 | Base `main` avisa | `worktree add` de una feature desde `main` | Aviso de base incorrecta | ✅ |
| 15 | `hotfix` desde `main` es excepción estructural | `worktree add -b hotfix/... main` | Sin aviso | ✅ |
| 16 | `split_commands` separa por operadores | Comando compuesto con `&&`, `;` y tubería | Lista de segmentos | ✅ |
| 17 | `merge --no-ff` no se confunde con un force-push | `git merge --no-ff` | Sin bloqueo (regresión) | ✅ |
| 18 | Un comando compuesto no contamina el push | `git merge --no-ff` seguido de un push a `develop` | Sin bloqueo (regresión) | ✅ |
| 19 | El force-push real sigue bloqueado | Push con flag de force | Bloqueo | ✅ |
| 20 | El force-push con flags cortos combinados sigue bloqueado | Push con flags cortos agrupados | Bloqueo | ✅ |
| 21 | `--follow-tags` no se confunde con force | Push con `--follow-tags` | Sin bloqueo | ✅ |

#### `test_plugin_structure.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | El plugin expone skills y agentes | Árbol del plugin | Listas no vacías | ✅ |
| 2 | Frontmatter válido de cada skill (5 casos) | `branch-name-suggester`, `commit`, `git`, `tiempos`, `worktrees` | `name` y `description` presentes y válidos | ✅ |
| 3 | Frontmatter válido de cada agente (3 casos) | `commit-message-writer`, `feature-doc-writer`, `release-notes-writer` | Frontmatter válido | ✅ |
| 4 | Las rutas relativas referenciadas existen (10 casos) | 5 `SKILL.md`, 3 agentes y 2 rules | Todas las rutas resuelven dentro del plugin | ✅ |
| 5 | Los scripts declarados en `hooks.json` existen | `hooks.json` | Todos los `.py` declarados existen | ✅ |
| 6 | Versión sincronizada entre `plugin.json` y `marketplace.json` | Ambos manifiestos | Misma versión | ✅ |
| 7 | El CHANGELOG documenta la versión actual | `CHANGELOG.md` + `plugin.json` | Bloque `[0.10.0]` presente | ✅ |

#### `test_timelog.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | `clean_note` deja una sola línea | Texto multilínea | Una línea saneada | ✅ |
| 2 | `clean_note` trunca a 160 caracteres | Texto largo | ≤ 160 caracteres | ✅ |
| 3 | `clean_note` devuelve vacío para `None` | `None` | Cadena vacía | ✅ |
| 4 | `sanitize_branch` normaliza el nombre de rama | Rama con `/` y caracteres especiales | Nombre apto para archivo | ✅ |
| 5 | Reconocimiento de comandos de prueba (7 casos) | `pytest`, `npm test`, `yarn run test:unit`, `go test ./...`, `cargo test`, `git status`, `echo` | Solo los cinco runners se reconocen como test | ✅ |
| 6 | Escritura y lectura de eventos | Eventos JSONL | Los eventos vuelven íntegros | ✅ |
| 7 | No se guardan notas vacías | Evento con nota vacía | Campo omitido | ✅ |
| 8 | Las líneas corruptas no rompen la lectura | JSONL con basura intercalada | Se ignoran las líneas malas | ✅ |
| 9 | Cada evento cabe en una escritura atómica | Eventos con notas y comandos largos | ≤ 4 KB por línea | ✅ |
| 10 | Las escrituras concurrentes no se pisan | Varios procesos escribiendo a la vez | Todas las líneas íntegras | ✅ |
| 11 | `known_branches` ordena por actividad | Varios logs de rama | Orden por actividad reciente | ✅ |
| 12 | Los rubros suman el total | Sesión completa simulada | `total = trabajo + externo + pruebas + espera + inactividad` | ✅ |
| 13 | Las pruebas se descuentan del trabajo | Ventana con un test dentro | El trabajo excluye el tiempo del test | ✅ |
| 14 | Las pruebas se parean por `tool_use_id` | Tests solapados | Cada intervalo cierra con su par | ✅ |
| 15 | Una prueba sin cierre se corta en el siguiente evento | `PreToolUse` huérfano | Intervalo cerrado y marcado estimado | ✅ |
| 16 | Espera e inactividad se separan por el umbral | Hueco mayor al umbral | Espera hasta el umbral, resto inactividad | ✅ |
| 17 | El hueco entre sesiones es inactividad de sesión | `SessionEnd` → `SessionStart` | Rubro `inactividad_sesion` | ✅ |
| 18 | Un hueco sin evidencia queda como tiempo muerto | Hueco sin archivos ni commits | Inactividad confirmada | ✅ |
| 19 | Un hueco con archivos modificados se reclasifica como trabajo externo | `mtime` dentro del hueco | Rubro `trabajo_externo` | ✅ |
| 20 | Con la evidencia desactivada no se reclasifica | `gitflow-es.evidence off` | Hueco sin reclasificar | ✅ |
| 21 | Los commits cuentan como evidencia | Commit dentro del hueco | Reclasificado a trabajo externo | ✅ |
| 22 | Una escritura masiva no cuenta como trabajo | 20+ archivos con el mismo `mtime` en 2 s | Clúster descartado | ✅ |
| 23 | Los `mtime` en el futuro se ignoran | Reloj desfasado | Sin evidencia generada | ✅ |
| 24 | La actividad en otra rama cuenta como trabajo externo | Eventos dirigidos a otro worktree | Se atribuyen a la otra rama | ✅ |
| 25 | Descripción y commits por ventana de actividad | Eventos `prompt` y `commit` | Tabla de actividad con texto y commits | ✅ |
| 26 | `describe` sobreescribe la descripción de la rama | Dos descripciones sucesivas | Prevalece la última | ✅ |
| 27 | Una rama abandonada no acumula reloj infinito | Log sin cierre | Total acotado al último evento | ✅ |
| 28 | Sin eventos devuelve vacío | Log inexistente | Reporte vacío, sin error | ✅ |
| 29 | Formato de duración (5 casos) | `0`, `45`, `600`, `3600`, `8040` segundos | `0s`, `45s`, `10m`, `1h 00m`, `2h 14m` | ✅ |
| 30 | El tiempo de calendario no infla el trabajo paralelo | Dos ramas solapadas | Unión de intervalos, no suma | ✅ |
| 31 | `scan_evidence` parsea aunque falte el espacio inicial | Porcelain sin el espacio del código de estado | Rutas completas | ✅ |
| 32 | `scan_evidence` también funciona con el espacio inicial | Porcelain estándar | Rutas completas | ✅ |
| 33 | `scan_evidence` es incremental | Segundo escaneo | Solo archivos con `mtime` posterior al sello | ✅ |
| 34 | `scan_evidence` ignora rutas que ya no existen | Archivo borrado | Se omite sin error | ✅ |

#### `test_time_tracker.py`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | `SessionStart` registra y escanea evidencia | Payload de `SessionStart` | Evento de sesión + escaneo | ✅ |
| 2 | `SessionEnd` escanea antes de cerrar | Payload de `SessionEnd` | Escaneo previo al cierre | ✅ |
| 3 | El prompt guarda la descripción del pedido | `UserPromptSubmit` | Primera línea saneada como nota | ✅ |
| 4 | Con las notas apagadas se registra la duración sin texto | `gitflow-es.timeNotes off` | Evento sin nota | ✅ |
| 5 | `Stop` cierra la ventana de trabajo | Payload de `Stop` | Ventana cerrada | ✅ |
| 6 | `Notification` registra el motivo de la espera | Payload de `Notification` | Evento de espera con motivo | ✅ |
| 7 | Un comando de test abre intervalo con su `tool_use_id` | `PreToolUse` de `pytest` | Intervalo abierto con el id | ✅ |
| 8 | Un comando normal no abre intervalo de test | `PreToolUse` de `git status` | Sin intervalo | ✅ |
| 9 | Un test fallido cierra su intervalo | `PostToolUse` con error | Intervalo cerrado | ✅ |
| 10 | `PostToolUseFailure` también cierra | Payload de fallo | Intervalo cerrado | ✅ |
| 11 | Un test exitoso se registra como `ok` | `PostToolUse` sin error | Intervalo cerrado como ok | ✅ |
| 12 | Un commit exitoso registra su asunto | `git commit` con éxito | Evento `commit` con el asunto | ✅ |
| 13 | Un commit fallido no se registra | `git commit` con error | Sin evento de commit | ✅ |
| 14 | Con `timeNotes=commits` se guarda solo el asunto | `gitflow-es.timeNotes commits` | Commits con texto, prompts sin él | ✅ |
| 15 | El trabajo dirigido a otro worktree se atribuye a esa rama | `git -C <ruta>` o `cd <ruta>` en el comando | Evento en la rama destino | ✅ |
| 16 | El trabajo en el propio worktree no genera actividad extra | Comando local | Sin evento `activity` adicional | ✅ |
| 17 | El registro desactivado no escribe nada | `gitflow-es.timeTracking off` | Log sin cambios | ✅ |
| 18 | Un `HEAD` desacoplado no registra | Worktree en detached HEAD | Sin escritura | ✅ |
| 19 | Con la evidencia desactivada no se escanea | `gitflow-es.evidence off` | Sin escaneo | ✅ |
| 20 | Un payload incompleto no explota | Payload con campos faltantes | Fail-open, sin excepción | ✅ |
| 21 | Detección de fallo de herramienta (6 casos) | Payloads con y sin señal de error | Clasificación correcta en los seis | ✅ |

### Pruebas manuales / de integración
| # | Escenario | Pasos / Datos de entrada | Resultado esperado | Resultado obtenido | ✅/❌ |
|---|-----------|--------------------------|-------------------|-------------------|------|
| 1 | Instalación de la versión nueva | `/plugin marketplace update Mithor86-2` y `/reload-plugins` | Resumen con 5 skills · 3 agents · 8 hooks; si los hooks quedan en 0, correr `/doctor` | Pendiente | ⚠️ |
| 2 | Arranque de sesión configurado | Abrir Claude Code en este repo | Bloque de estado con rama, worktree de trabajo, worktrees activos y línea de tiempos; sin bloque de configuración | Pendiente | ⚠️ |
| 3 | Arranque sin configurar | Abrir una sesión en un repo sin `git flow init` | Aviso de git-flow faltante + checklist con ⬜ y oferta de `/git init` | Pendiente | ⚠️ |
| 4 | Ciclo completo de rama | `/git start feature <descripción>` → trabajar → `/git finish` | Worktree creado desde `develop`, cierre desde el control con worktree removido y verificación de que la rama se borró y sus commits están en `develop` | Pendiente | ⚠️ |
| 5 | Guarda del finish roto | Dentro del worktree de una rama, pedir `git flow feature finish <x>` | El hook lo bloquea y explica por qué | Pendiente | ⚠️ |
| 6 | Lote paralelo | `/worktrees paralelo` con dos tareas independientes | Dos worktrees desde `develop`, trabajo simultáneo, cierres de a uno con refresco desde `develop` | Pendiente | ⚠️ |
| 7 | Reporte de tiempos | `/tiempos` tras una sesión real de trabajo | Cinco rubros que suman el total, pruebas separadas y tabla de actividad con descripciones y commits | Pendiente | ⚠️ |
| 8 | Validación de tiempos muertos | Editar archivos del worktree fuera de Claude 20 minutos y volver | Ese rato aparece como *trabajo fuera de sesión*, no como inactividad | Pendiente | ⚠️ |
| 9 | Privacidad del registro | `git status` y `git log` tras varias sesiones | El registro nunca aparece; vive en `.git/gitflow-es/tiempos/` | Pendiente | ⚠️ |

## Resultado
⚠️ Pendiente de revisión — suite automatizada en verde (195/195); las 9 pruebas manuales siguen pendientes de validación humana.

---

### Notas

- La suite completa se ejecutó con `python3.8 -m pytest plugins/gitflow-es/tests -q` dentro del worktree de la rama: **195 passed**. De esos, 129 son tests nuevos de esta rama (5 archivos) y 66 provienen de la suite previa en `develop` (`test_i18n.py` con 11 y `test_safety_check.py` con 55, no modificados aquí). El CHANGELOG y el plan citaban «74 antes» —el corte posterior a la fase 1— y se corrigieron a 66 tras esta verificación.
- El diff contra `develop` suma 4.795 inserciones y 116 eliminaciones en 26 archivos; superaba el umbral de lectura completa, así que las descripciones por archivo se derivaron de los mensajes de commit, del `--stat` y del diff de los manifiestos, los agentes y `conftest.py`.
- Los bugs encontrados y corregidos durante el desarrollo (falso éxito de `git flow finish`, `check_force_push`, rutas muertas en los subagentes, parseo de `git status --porcelain`, sello de evidencia, doble conteo de commits y falsos positivos de comandos de prueba) están detallados en `docs/planes/2026-09-14-worktrees-y-registro-de-tiempos.md`.
- Limitación conocida: el plugin instalado en la sesión de desarrollo seguía siendo 0.9.0, así que los hooks nuevos se probaron inyectando payloads reales y en repos de laboratorio, no por activación automática del harness.
