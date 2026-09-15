# Plan de implementación — Worktrees obligatorios, paralelismo y registro de tiempos

- **Fecha:** 2026-09-14
- **Rama:** `feature/worktrees-y-registro-de-tiempos`
- **Worktree:** `../Mithor86-2-claude-plugins-worktrees/feature-worktrees-y-registro-de-tiempos` (base: `develop`)
- **Autor:** Miguel Torres
- **Estado global:** ✅ Finalizada
- **Requerimiento:** Extender el plugin `gitflow-es` con (1) validación y configuración guiada de git-flow al abrir sesión, (2) regla de trabajar siempre en worktrees creados desde `develop`, (3) soporte para paralelizar trabajo con worktrees y (4) un registro de tiempos por rama que separe trabajo, pruebas, espera del usuario e inactividad.

## Alcance

- **Incluye:**
  - Subcomando `/git init` — asistente que inicializa git-flow y deja la config del plugin completa (idioma, scopes, worktrees, tiempos).
  - `session-context.py` extendido: config pendiente, worktrees activos, worktree de control y estado del registro de tiempos.
  - Regla de worktrees en `rules/git-flow.md` + flujos `start`/`finish`/`sync` del skill `git` reescritos en modo worktree, con **verificación de postcondiciones** del finish.
  - Avisos de worktree y **bloqueo del `git flow finish` dentro de un worktree linked** dentro de `safety-check.py`.
  - Skill nuevo `worktrees` — gestión de worktrees y orquestación de trabajo paralelo desde `develop`.
  - Subsistema de tiempos: `hooks/timelog.py` (módulo), `hooks/time-tracker.py` (hook multi-evento), `hooks/time-report.py` (CLI) y skill `tiempos`, con **descripción corta del trabajo** por rama y por ventana de actividad.
  - Claves i18n ES/EN para todo lo nuevo; tests pytest; READMEs, CHANGELOG y bump a 0.10.0.
- **No incluye:**
  - Persistencia compartida o commiteada del registro de tiempos (**todo local**, en `<git-common-dir>/gitflow-es/tiempos/`).
  - Bloqueo duro de la creación de ramas fuera del flujo de worktree (**solo aviso**; el único bloqueo nuevo es el del `finish` roto).
  - Desglose de tiempos dentro de documentos versionados (plan, feature-doc, CHANGELOG).
- **Componentes afectados:** `plugins/gitflow-es/{rules,skills,hooks,tests}`, `README.md` (raíz y plugin), `CHANGELOG.md`, `.claude-plugin/marketplace.json`, `plugins/gitflow-es/.claude-plugin/plugin.json`.

## Decisiones (confirmadas con el usuario)

| # | Decisión | Elección |
|---|----------|----------|
| 1 | Repo de trabajo | `git flow init -d` ejecutado, `develop` creada, la feature se desarrolla en worktree desde `develop` |
| 2 | Ubicación de worktrees | Hermano del repo: `<padre>/<repo>-worktrees/<tipo>-<slug>/` (override: `git config gitflow-es.worktreeRoot`) |
| 3 | Registro de tiempos | Todo local, nada se commitea (`<git-common-dir>/gitflow-es/tiempos/*.jsonl`) |
| 4 | Estrictez de la regla de worktrees | Rules + skill obligan; el hook **avisa**, no bloquea |
| 5 | `git flow finish` dentro de un worktree linked | **Bloqueado** por el hook (excepción puntual a la decisión 4: ahí el comando siempre miente) |
| 6 | Ejecución de este plan | Secuencial en este worktree; el flujo paralelo se valida en la fase 5 con worktrees desechables |

## Hallazgo que condiciona el diseño (validado en laboratorio)

`git-flow-avh 0.4.1` **no es confiable en su código de salida al hacer `finish`**. Reproducido en repos de prueba:

| Escenario | Efecto real | Lo que reporta |
|---|---|---|
| `finish` dentro del worktree de la rama | `checkout develop` falla ("already used by worktree"), no mergea, no borra la rama | `Summary of actions: merged… removed…`, **exit 0** |
| `finish` desde el control con el worktree vivo | Mergea a `develop`, **no** borra la rama | Igual, **exit 0** |
| `worktree remove` → `finish` desde el control | Correcto | Correcto |

**Consecuencias de diseño:**
1. El `finish` **siempre** corre en el worktree de control y **después** de remover el worktree de la rama.
2. `/git finish` valida postcondiciones en lugar del exit code: `git branch --list <rama>` vacío **y** `git merge-base --is-ancestor <sha> develop`.
3. `safety-check.py` bloquea `git flow <tipo> finish` cuando el cwd es un worktree linked.

## Contradicciones de reglas detectadas y su resolución

| # | Choque | Resolución que se implementa |
|---|--------|------------------------------|
| C1 | "Nunca `git checkout -b` para tipos nativos" + "obligatorio usar comandos git-flow" ⟂ crear toda rama con `git worktree add -b` | La **creación** admite `git worktree add -b` (modo worktree, default) o `git flow <tipo> start` (modo sin worktree). `git checkout -b` / `git switch -c` siguen prohibidos. git-flow sigue siendo obligatorio en el **cierre** |
| C2 | `finish` de `fix`/`refactor`/`chore` con `git checkout develop` ⟂ `develop` ocupado por el worktree de control | Todos los finish corren en el control; desde un worktree linked el checkout de `develop` es imposible por diseño de git |
| C3 | "Siempre `pull origin develop` antes de crear la rama" ⟂ estar dentro de un worktree | La base se actualiza en el control (`git -C <control> pull --ff-only origin develop`) y luego se crea el worktree |
| C4 | "Worktrees siempre desde develop" ⟂ GitFlow: `hotfix` nace de `main` | Excepción estructural: `hotfix/` → worktree desde `main`; `release/` → desde `develop`. No requiere petición explícita del usuario |
| C5 | Aviso "estás en main, no modifiques archivos" ⟂ el control queda parado en `develop` | El aviso pasa a ser "worktree de control — no se trabaja aquí", aplicado a `main` **y** `develop` |
| C6 | Excepción "commit directo en develop" ⟂ regla de worktrees | Se mantiene; se ejerce en el control, único sitio con `develop` checked out |
| C7 | "Paralelizar todo lo posible" ⟂ "nunca merge/push sin confirmación" | El paralelismo cubre implementación y tests; los cierres son secuenciales y confirmados uno por uno |
| C8 | "El registro no se commitea" ⟂ resumir tiempos en plan/feature-doc | Los documentos versionados no llevan desglose de tiempos; `/tiempos exportar` escribe fuera del repo bajo pedido |
| C9 | `/git sync` con `checkout develop && checkout main` ⟂ ramas ocupadas por worktrees | Sync sin checkouts: `fetch --all --prune`, fast-forward de refs desde el control y `worktree prune` |
| C10 | `stash` parece por worktree pero `refs/stash` es global | Nota explícita en la rule y aviso en el skill |

## Optimizaciones incorporadas

**Diseño**
1. **Worktree de control** parado en `develop`, nunca usado para trabajar: elimina de raíz C2, C3 y C9.
2. `/git finish` verifica postcondiciones en vez de confiar en el exit code de git-flow.
3. Los avisos de worktree viven dentro de `safety-check.py` (ya parsea comandos git, detecta rama y tiene i18n) en vez de un hook nuevo: un proceso menos por llamada a Bash y cero lógica duplicada.
4. Un solo `fetch`/actualización de `develop` por lote paralelo, no uno por rama.
5. El slug del `branch-name-suggester` se reusa como nombre de rama, carpeta del worktree y archivo del log.

**Rendimiento del tracker** (corre en cada evento)
6. Cero subprocesos en el camino caliente: rama y `git-common-dir` se resuelven leyendo `.git` y `HEAD`, con fallback a `git`. En `PreToolUse` se sale por regex antes de tocar disco.
7. Config leída de un golpe con `git config --get-regexp '^gitflow-es\.'` y cacheada por proceso.
8. Append atómico (`O_APPEND` + una sola escritura ≤ 4 KB, comando truncado) y un JSONL por rama → seguro con varios worktrees escribiendo a la vez.

**Exactitud de la medición**
9. Pareo de intervalos de test por `tool_use_id`, no por texto del comando.
10. `PostToolUseFailure` también cierra el intervalo (un test que falla no puede dejarlo abierto).
11. Inactividad desglosada en `inactividad_usuario` (dentro de huecos stop→prompt) e `inactividad_sesion`; así `espera_total = espera + inactividad_usuario` sin romper la aditividad de los cuatro rubros. Los intervalos abiertos por cierre abrupto se cortan en el último evento y se marcan "estimado".
12. En `--all`: suma por rama **y** tiempo de calendario (unión de intervalos), para no inflar totales con ramas trabajadas en paralelo.

### Modelo de tiempos (aditivo)

Para cada rama, `total (reloj) = trabajo + trabajo_externo + pruebas + espera_usuario + inactividad`:

- **trabajo** — ventanas `UserPromptSubmit → Stop`, menos el tiempo de pruebas contenido en ellas.
- **trabajo_externo** — porciones de huecos donde hay evidencia de actividad real fuera de la sesión (ver validación abajo).
- **pruebas** — intervalos `PreToolUse → PostToolUse|PostToolUseFailure` de comandos de test, pareados por `tool_use_id`.
- **espera_usuario** — hueco `Stop → siguiente UserPromptSubmit`, hasta el umbral de inactividad.
- **inactividad** — lo que exceda el umbral (default 15 min, `gitflow-es.idleThresholdMin`), desglosada en `usuario` y `sesion`.

### Validación de tiempos muertos con evidencia

Los eventos de hook solo ven lo que pasa dentro de la sesión: si el usuario edita en su editor o commitea por fuera, ese tiempo caería como "inactividad" siendo trabajo real. Por eso **ningún hueco se declara tiempo muerto sin contrastarlo**:

**Fuentes de evidencia** (ambas baratas y acotadas a la rama, nunca un escaneo del repo completo):
1. `mtime` de los archivos que `git status --porcelain` reporta como modificados/sin trackear en ese worktree — respeta `.gitignore`, así que artefactos de build y `node_modules` quedan fuera por construcción.
2. Timestamps de commits de la rama (`git log --format=%cI <base>..HEAD`), que además cubren commits hechos fuera de Claude.

**Algoritmo de reclasificación** (corre sobre los huecos ya clasificados; la evidencia tiene precedencia sobre espera e inactividad):
1. Se agrupan los timestamps de evidencia en clústeres, cortando cuando hay más de `gitflow-es.externalGapMin` minutos entre dos consecutivos (default 10).
2. Cada clúster aporta el intervalo `[primero - margen, último + margen]` con `gitflow-es.externalMargin` (default 5 min); un timestamp aislado aporta `2 × margen`.
3. La intersección de esos intervalos con el hueco pasa a **trabajo_externo**; el resto del hueco conserva su clasificación (`espera_usuario` o `inactividad`).
4. Los `mtime` en el futuro (reloj desfasado) se recortan al momento del reporte y no generan evidencia.
5. **Descarte de escrituras masivas:** si 20 o más archivos comparten `mtime` dentro de una ventana de 2 segundos, es un `checkout`/`worktree add`/build reescribiendo el árbol, no trabajo humano — ese clúster se descarta. Es el falso positivo más probable de este método.

**Captura:** la evidencia se escanea en `SessionStart` y `SessionEnd` (incremental, solo archivos con `mtime` posterior al último escaneo) y **obligatoriamente antes de remover el worktree en `/git finish`** — después de removerlo los `mtime` ya no existen. Se guarda como eventos `evidence` (una línea por archivo, para no romper el append atómico).

**En el reporte:** los tiempos muertos salen validados, no crudos —
`Tiempos muertos: 1h 03m confirmados (sin evidencia de actividad) · 22m reclasificados como trabajo fuera de sesión (evidencia: 4 archivos, 2 commits)`.
Se desactiva con `git config gitflow-es.evidence off`.

### Descripción del trabajo realizado

El registro no guarda solo duraciones: cada rama y cada ventana de trabajo llevan una descripción corta, obtenida de fuentes mecánicas (nunca inventada por el modelo):

| Nivel | Fuente | Cuándo se captura |
|-------|--------|-------------------|
| Rama | Descripción que el usuario dio en `/git start`; editable con `/tiempos describir "<texto>"` | Evento `branch_start` |
| Ventana de trabajo | Primera línea del prompt del usuario, saneada a una línea y truncada a 160 caracteres | Evento `prompt` (`UserPromptSubmit`) |
| Entregable | Asunto del commit (`git log -1 --format=%s`, leído solo tras un `git commit` exitoso) | Evento `commit` (`PostToolUse`) |
| Cierre | Línea de resumen que registra `/git finish` | Evento `branch_finish` |

- **Privacidad / configuración:** como esto persiste texto de los prompts (siempre local, dentro de `.git/`, nunca commiteado), es configurable con `git config gitflow-es.timeNotes`: `on` (default: prompts + commits), `commits` (solo asuntos de commit) u `off` (solo duraciones). Las notas se guardan saneadas (una línea, sin caracteres de control, ≤ 160 caracteres) para no romper el append atómico.
- **En el reporte:** además del desglose de tiempos aparece una tabla de actividad — inicio, duración de la ventana, descripción y commits producidos en ella — para leer de un vistazo en qué se fue el tiempo de la rama.

## Criterios de aceptación

- [ ] Al abrir sesión sin git-flow, el bloque de contexto ofrece `/git init` y lista la config pendiente; con git-flow listo, muestra worktrees activos y estado de tiempos.
- [ ] `/git start <tipo> <desc>` actualiza la base en el control y crea rama + worktree (`develop`, o `main` para `hotfix`); se puede pedir explícitamente no usar worktree.
- [ ] `/git finish` desde dentro del worktree: valida limpio, vuelve al control, remueve el worktree, cierra con git-flow y **verifica** que la rama se borró y sus commits están en `develop`.
- [ ] `git flow ... finish` dentro de un worktree linked queda **bloqueado** por el hook, con mensaje que explica el falso éxito.
- [ ] Crear rama sin worktree o desde otra base produce **aviso**, nunca bloqueo.
- [ ] El skill `worktrees` describe reparto de N tareas independientes en N worktrees desde `develop`, actualización única de la base y cierre secuencial.
- [ ] `/tiempos` muestra inicio, fin, total y desglose; los cuatro rubros suman el total.
- [ ] El reporte incluye la descripción de la rama y una tabla de actividad (ventana, duración, descripción, commits); con `gitflow-es.timeNotes=off` se registran duraciones sin texto.
- [ ] Ningún hueco se reporta como tiempo muerto sin contrastarlo contra `mtime` de archivos y timestamps de commits: los huecos con evidencia se reclasifican como trabajo externo y los cinco rubros siguen sumando el total.
- [ ] El registro nunca aparece en `git status`.
- [ ] `python3.8 -m pytest plugins/gitflow-es/tests -q` en verde, con tests nuevos de timelog, tracker, advisor y bloqueo del finish.
- [ ] READMEs, CHANGELOG, `plugin.json` y `marketplace.json` en **0.10.0**.

## Control de progreso

### Fase 1 — Validación y configuración al abrir sesión (Ajuste 1)
| # | Tarea | Estado |
|---|-------|--------|
| 1.1 | `session-context.py`: config pendiente (git-flow, idioma, worktreeRoot, tiempos), worktrees activos, identificación del worktree de control y aviso C5 | ✅ Finalizada |
| 1.2 | Subcomando `/git init` en `skills/git/SKILL.md`: init + idioma + scopes + `worktreeRoot` + tiempos (+ `.gitignore` si el root queda dentro del repo) | ✅ Finalizada |
| 1.3 | Claves i18n ES/EN de sesión/config | ✅ Finalizada |
| 1.4 | Tests: `test_session_context.py` (sin commits, sin git-flow, config incompleta, con worktrees) | ✅ Finalizada |
| 1.5 | Docs: sección de configuración del README del plugin (nuevas keys de `git config`) | ✅ Finalizada |

### Fase 2 — Worktrees obligatorios desde develop (Ajuste 2)
| # | Tarea | Estado |
|---|-------|--------|
| 2.1 | `rules/git-flow.md`: sección "Worktrees (obligatorio)" + resolución explícita de C1-C6, C9, C10 | ✅ Finalizada |
| 2.2 | `skills/git/SKILL.md`: `start` y `finish` en modo worktree (con verificación de postcondiciones y **escaneo de evidencia de tiempos antes de remover el worktree**), `sync` sin checkouts, subcomando `/git worktree` | ✅ Finalizada |
| 2.3 | `safety-check.py`: bloqueo de `git flow <tipo> finish` en worktree linked + avisos de worktree (rama sin worktree, base distinta de `develop`, edición en el control) | ✅ Finalizada |
| 2.4 | Claves i18n ES/EN del bloqueo y los avisos | ✅ Finalizada |
| 2.5 | Tests: bloqueo del finish en worktree linked, avisos que sí/no disparan, silencio en `git worktree add` | ✅ Finalizada |
| 2.6 | Docs: README del plugin — sección Worktrees, con la tabla del falso éxito de git-flow | ✅ Finalizada |

### Fase 3 — Trabajo en paralelo con worktrees (Ajuste 3)
| # | Tarea | Estado |
|---|-------|--------|
| 3.1 | Skill nuevo `skills/worktrees/SKILL.md`: crear/listar/limpiar y orquestar N tareas desde `develop` (base actualizada una sola vez, cierre secuencial) | ✅ Finalizada |
| 3.2 | `rules/git-flow.md`: sección "Trabajo en paralelo" — criterio de independencia, un worktree por rama, orden de cierre, refresco desde `develop` entre cierres (C7) | ✅ Finalizada |
| 3.3 | Tests: validación estructural de skills (frontmatter y rutas referenciadas existentes) | ✅ Finalizada |
| 3.4 | Docs: README del plugin y del repo — skill `worktrees` | ✅ Finalizada |

### Fase 4 — Registro de tiempos por rama (Ajuste 4)
| # | Tarea | Estado |
|---|-------|--------|
| 4.1 | `hooks/timelog.py`: rutas sin subprocesos, append atómico, saneado/truncado de notas, parsing y agregación del modelo aditivo (incl. intervalos abiertos y desglose de inactividad) | ✅ Finalizada |
| 4.1b | `hooks/timelog.py`: escaneo incremental de evidencia (`git status --porcelain` + `mtime`, `git log --format=%cI`) y reclasificación de huecos por clústeres con margen y recorte de relojes desfasados | ✅ Finalizada |
| 4.2 | `hooks/time-tracker.py`: hook multi-evento (SessionStart, UserPromptSubmit, Stop, PreToolUse, PostToolUse, PostToolUseFailure, Notification, SessionEnd), pareo por `tool_use_id`, eventos `activity` throttled para ramas paralelas, captura de notas (prompt + asunto de commit) según `gitflow-es.timeNotes`, escaneo de evidencia en inicio/fin de sesión, modo CLI `--mark` / `--note` / `--evidence` | ✅ Finalizada |
| 4.3 | `hooks/time-report.py`: CLI (`--branch`, `--all`, `--format md\|json`) en ES/EN, con tabla de actividad (descripción + commits), línea de tiempos muertos validados vs. reclasificados y tiempo de calendario en `--all` | ✅ Finalizada |
| 4.4 | `hooks.json`: registrar el tracker en sus eventos; patrón de tests configurable (`gitflow-es.testPattern`) | ✅ Finalizada |
| 4.5 | Skill nuevo `skills/tiempos/SKILL.md` (`estado`, `rama`, `todas`, `describir`, `nota`, `exportar`, `reset`) + enganche en `/git start` (descripción de la rama) y `/git finish` (línea de cierre) | ✅ Finalizada |
| 4.6 | Claves i18n ES/EN del reporte | ✅ Finalizada |
| 4.7 | Tests: `test_timelog.py` (aditividad con cinco rubros, umbral, pareo por id, huérfanos, concurrencia de append, saneado/truncado de notas, clústeres de evidencia, hueco con y sin evidencia, `mtime` futuro) y `test_time_tracker.py` (payload por evento, fail-open, tracking off, `timeNotes` en sus tres modos, `evidence off`) | ✅ Finalizada |
| 4.8 | Docs: README del plugin — sección Registro de tiempos (qué mide, descripciones capturadas, dónde vive, cómo se consulta, cómo se desactivan las notas) | ✅ Finalizada |

### Fase 5 — Cierre
| # | Tarea | Estado |
|---|-------|--------|
| 5.1 | Suite completa en verde: `python3.8 -m pytest plugins/gitflow-es/tests -q` | ✅ Finalizada |
| 5.2 | Prueba manual: ciclo worktree completo + **flujo paralelo con dos worktrees desechables** desde `develop`, verificando atribución de tiempos por rama y el bloqueo del finish roto | ✅ Finalizada |
| 5.3 | Resumen + pasos de pruebas manuales en este plan (sin desglose de tiempos, por C8) | ✅ Finalizada |
| 5.4 | CHANGELOG `[0.10.0]` + bump en `plugin.json`, `marketplace.json` y badge del README | ✅ Finalizada |
| 5.5 | `/git finish`: feature-doc, remover worktree, merge local a `develop` desde el control y verificación de postcondiciones (sin push) | ⬜ Pendiente |

## Resumen y pruebas manuales

### Qué quedó implementado

| Ajuste pedido | Cómo se resolvió |
|---------------|------------------|
| 1. Validar git-flow al abrir sesión y ofrecer configurarlo | `session-context.py` reporta worktree de control vs. de trabajo, worktrees activos, checklist de configuración y tiempo acumulado de la rama; el subcomando `/git init` deja git-flow, idioma, raíz de worktrees, registro de tiempos y scopes en un paso |
| 2. Worktrees siempre, desde `develop` | Regla en `git-flow.md` + `start`/`finish`/`sync`/`worktree` del skill `git`; el hook avisa cuando no se sigue y **bloquea** el único caso que corrompe el cierre (`git flow finish` dentro del worktree de la rama) |
| 3. Paralelizar con worktrees desde `develop` | Skill `worktrees` + sección "Trabajo en paralelo" en la rule: criterio de independencia, base actualizada una vez, un ejecutor por worktree, cierres secuenciales y refresco desde `develop` entre cierres |
| 4. Registro de tiempos con tiempos muertos y pruebas por separado | `timelog.py` + `time-tracker.py` + `time-report.py` + skill `tiempos`: cinco rubros que suman el reloj, pruebas medidas aparte, tiempos muertos validados contra `mtime` y commits, y descripción corta del trabajo por rama, ventana y commit |

### Bugs encontrados y corregidos durante el desarrollo

1. **`git flow finish` miente** (git-flow-avh 0.4.1): dentro del worktree de la rama no mergea, no borra la rama y sale con código 0 igual. Se bloquea ese caso y el finish verifica postcondiciones.
2. **`check_force_push` bloqueaba comandos legítimos**: leía la línea completa y tomaba el `-ff` de `--no-ff` como flag de force. Ahora evalúa por segmento de comando.
3. **Rutas muertas en los subagentes**: referenciaban `../../rules/`, que desde `agents/` apunta fuera del plugin.
4. **Parseo de `git status --porcelain`**: el `.strip()` de `run_git` se come el espacio del código de estado, así que las rutas salían mutiladas y el escaneo de evidencia no encontraba nada.
5. **Sello de evidencia**: se escribía al terminar el escaneo; un archivo modificado mientras corría quedaba fuera para siempre.
6. **Doble conteo de commits** como evidencia (evento en vivo + `git log`).
7. **Falsos positivos de comandos de prueba**: una ruta como `/tmp/pytest-of-user/` contaba como corrida de tests.

### Pruebas automatizadas

`python3.8 -m pytest plugins/gitflow-es/tests -q` → **195 tests en verde**: 66 existían antes de esta rama y 129 son nuevos.

### Pruebas manuales — ⚠️ pendientes de validación humana

| # | Escenario | Pasos | Resultado esperado |
|---|-----------|-------|--------------------|
| 1 | Instalación de la versión nueva | `/plugin marketplace update Mithor86-2` y `/reload-plugins` | Resumen con **5 skills · 3 agents · 8 hooks**; si los hooks quedan en 0, correr `/doctor` |
| 2 | Arranque de sesión configurado | Abrir Claude Code en este repo | Bloque de estado con rama, worktree de trabajo, worktrees activos y línea de tiempos; sin bloque de configuración |
| 3 | Arranque sin configurar | Abrir una sesión en un repo sin `git flow init` | Aviso de git-flow faltante + checklist con ⬜ y oferta de `/git init` |
| 4 | Ciclo completo de rama | `/git start feature <descripción>` → trabajar → `/git finish` | Worktree creado desde `develop`, cierre desde el control con worktree removido y verificación de que la rama se borró y sus commits están en `develop` |
| 5 | Guarda del finish roto | Dentro del worktree de una rama, pedir `git flow feature finish <x>` | El hook lo bloquea y explica por qué |
| 6 | Lote paralelo | `/worktrees paralelo` con dos tareas independientes | Dos worktrees desde `develop`, trabajo simultáneo, cierres de a uno con refresco desde `develop` |
| 7 | Reporte de tiempos | `/tiempos` tras una sesión real de trabajo | Cinco rubros que suman el total, pruebas separadas y tabla de actividad con descripciones y commits |
| 8 | Validación de tiempos muertos | Editar archivos del worktree fuera de Claude 20 minutos y volver | Ese rato aparece como *trabajo fuera de sesión*, no como inactividad |
| 9 | Privacidad del registro | `git status` y `git log` tras varias sesiones | El registro nunca aparece; vive en `.git/gitflow-es/tiempos/` |

### Limitaciones conocidas

- La evidencia por `mtime` no distingue quién escribió: un autoguardado del editor o un formateador que toque archivos dentro de un hueco cuenta como trabajo externo. Se apaga con `git config gitflow-es.evidence off`.
- La atribución de trabajo en paralelo se apoya en `cd <ruta>` o `git -C <ruta>` dentro del comando; trabajo dirigido a otro worktree por otros medios se le carga a la rama de la sesión.
- El plugin instalado en la sesión donde se desarrolló seguía siendo 0.9.0, así que los hooks nuevos se probaron inyectando payloads reales y en repos de laboratorio, no por activación automática del harness.

## Bitácora

- 2026-09-15 — Fase 5: suite en verde (195 tests), laboratorio del ciclo completo y del lote paralelo con dos worktrees, verificación del bloqueo (exit 2 dentro del worktree linked, 0 desde el control), release 0.10.0 en CHANGELOG, `plugin.json`, `marketplace.json` y badge.
- 2026-09-15 — Fase 4 finalizada: `timelog.py` (agregación aditiva, evidencia, append atómico), `time-tracker.py` (8 eventos + CLI), `time-report.py` (ES/EN, markdown y JSON), skill `tiempos` y wiring de hooks. La prueba end-to-end destapó tres bugs, ya corregidos con test: rutas mutiladas al parsear `git status --porcelain` (el `.strip()` de `run_git` se come el espacio del código de estado), el sello de evidencia escrito al final del escaneo en vez del inicio, y un mismo commit contado dos veces como evidencia. También se ajustó el regex de comandos de test para que una ruta como `/tmp/pytest-of-user/` no cuente como corrida. Suite: 195 tests en verde.
- 2026-09-15 — Fase 3 finalizada: skill `worktrees` (criterio de independencia, lote paralelo, cierre secuencial, tabla de errores de git) y sección "Trabajo en paralelo" en la rule. Los tests estructurales nuevos detectaron que los dos agentes referenciaban `../../rules/` (ruta muerta desde `agents/`); corregido a `../rules/`. Suite: 123 tests en verde.
- 2026-09-15 — Fase 2 finalizada: política de worktrees en la rule y el skill `git`, módulo compartido `gitwt.py`, bloqueo del finish en worktree linked, cuatro avisos no bloqueantes y subcomando `/git worktree`. **Bug encontrado de paso:** `check_force_push` leía todo el comando compuesto y tomaba el `-ff` de `--no-ff` como flag de force — bloqueaba flujos legítimos del propio plugin. Corregido con segmentación por comando y lookbehind más estricto, con tests de regresión. Suite: 103 tests en verde.
- 2026-09-15 — Fase 1 finalizada: `session-context.py` reporta worktrees y checklist de configuración, `/git init` documentado en el skill `git`, 85 claves i18n en ES/EN y `test_session_context.py` (8 tests). Suite: 74 tests en verde.
- 2026-09-14 — `git flow init -d` ejecutado (`main` producción, `develop` integración), `gitflow-es.language=es`, worktree de la feature creado desde `develop`. Plan creado.
- 2026-09-15 — Los tiempos muertos se validan contra evidencia real (`mtime` de archivos modificados + timestamps de commits); aparece el rubro `trabajo_externo` y la evidencia se captura antes de remover el worktree en el finish.
- 2026-09-15 — El registro de tiempos incorpora descripción corta del trabajo (rama, ventana de actividad, commits y cierre), configurable con `gitflow-es.timeNotes`.
- 2026-09-15 — Validación de reglas: 10 contradicciones resueltas y 12 optimizaciones incorporadas. Laboratorio con git-flow-avh 0.4.1 demuestra falso éxito del `finish` en worktrees; se agregan bloqueo y verificación de postcondiciones. Decisiones 5 y 6 confirmadas con el usuario.
