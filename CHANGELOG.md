# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/), versionado con [SemVer](https://semver.org/).

## [Unreleased]

### Fixed
- **La espera de aprobación ya no se cobra como trabajo**: el rato entre que
  se pide un permiso y la persona responde caía dentro de la ventana
  `prompt → stop` y se sumaba a *Trabajo*. Ahora el hook de `Notification`
  clasifica el aviso (por tipo o por texto, en es/en), la respuesta lo cierra
  — la herramienta al correr, o el fin de turno cuando el permiso se rechaza —
  y el intervalo va a un rubro propio, **Espera de aprobación**. Ante la duda
  no se descuenta nada: se prefiere subestimar la espera antes que inventarla.
- **Las ramas cerradas conservan su evidencia de commits**: la validación de
  tiempos muertos consultaba `git log <base>..<rama>` al *leer* el reporte, y
  ese rango queda vacío apenas la rama se mergea y se borra — justo cuando el
  reporte se mira. `/git finish` ahora congela los timestamps en el propio log
  (evento `commit_times`) antes del merge, y el reporte cae a ellos cuando git
  ya no puede responder.

### Changed
- El subcomando `release` del skill `git` documenta el cierre real del ciclo:
  verificar el prefijo de tag contra los tags existentes antes de cerrar, cómo
  pasar el mensaje del tag en macOS (donde `git flow release finish -m "texto con
  espacios"` falla por el `getopt` del sistema), la verificación de
  postcondiciones del release y cómo integrar `main` si el remoto avanzó por
  fuera antes de publicar.

## [0.10.0] — 2026-09-15

### Added
- **Worktrees obligatorios desde `develop`**: cada rama de trabajo nace en su
  propio worktree (`<padre-del-repo>/<repo>-worktrees/<tipo>-<slug>`, configurable
  con `gitflow-es.worktreeRoot`) y el repo principal queda como *worktree de
  control*: parado en `develop`, sin ediciones, y único lugar donde se cierran
  ramas. `hotfix/` mantiene su base en `main`. Documentado en la rule
  `git-flow.md` y en los subcomandos `start`, `finish`, `sync` y `worktree` del
  skill `git`.
- **Skill `worktrees`**: gestión de worktrees y orquestación de trabajo en
  paralelo — criterio de independencia entre tareas, actualización única de la
  base, un ejecutor por worktree y cierre secuencial con refresco de las ramas
  vivas desde `develop` entre cierres.
- **Skill `tiempos` y registro de tiempos por rama**: nuevos `hooks/timelog.py`,
  `hooks/time-tracker.py` y `hooks/time-report.py`. Miden cinco rubros que parten
  el reloj (trabajo, trabajo fuera de sesión, pruebas, espera del usuario e
  inactividad), separan el tiempo de pruebas pareando por `tool_use_id` y guardan
  una descripción corta del trabajo (descripción de la rama, primera línea de
  cada prompt y asunto de cada commit). El registro es local: vive en
  `<git-common-dir>/gitflow-es/tiempos/`, nunca aparece en `git status` ni se
  commitea.
- **Validación de tiempos muertos con evidencia**: ningún hueco se declara tiempo
  muerto sin contrastarlo contra los `mtime` de los archivos que reporta `git
  status` y los timestamps de los commits; lo que tiene evidencia se reclasifica
  como trabajo fuera de sesión. Descarta escrituras masivas (20+ archivos en 2 s,
  típico de un `checkout` o un build) y recorta `mtime` futuros.
- **Subcomando `/git init`**: asistente que deja el repo listo en un paso
  (git-flow, idioma, raíz de worktrees, registro de tiempos y scopes).
- **Bloqueo de `git flow <tipo> finish` dentro del worktree de la rama**: ahí
  git-flow no puede hacer checkout de `develop`, no mergea, no borra la rama y aun
  así imprime «Summary of actions» con código 0. Se agrega además un aviso cuando
  el finish corre con el worktree todavía vivo, y `/git finish` verifica las
  postcondiciones en lugar de confiar en el código de salida.
- **Avisos no bloqueantes de la política de worktrees** (crear rama sin worktree,
  base distinta de `develop`, editar en el worktree de control), desactivables con
  `gitflow-es.worktrees off`.
- **Nuevas claves de configuración**: `worktreeRoot`, `worktrees`, `timeTracking`,
  `timeNotes`, `evidence`, `idleThresholdMin`, `externalGapMin`, `externalMargin`,
  `testPattern` y `timeLogDir`.

### Changed
- `session-context` (SessionStart) pasa de avisar solo por git-flow a un
  diagnóstico completo: worktree de control vs. de trabajo, worktrees activos,
  checklist de configuración pendiente y tiempo acumulado de la rama.
- `/git sync` deja de usar `checkout` (fallaba con ramas ocupadas por otro
  worktree) y trabaja con `fetch --all --prune` más fast-forward de refs.
- `hooks/gitwt.py` (nuevo) centraliza worktrees y configuración: resuelve rama y
  git-dir leyendo archivos en vez de invocar git, y cachea la config en disco
  para no pagar un `git config` por evento de hook.

### Fixed
- **`check_force_push` bloqueaba comandos legítimos**: evaluaba la línea completa
  y leía el `-ff` de `--no-ff` como flag de force, así que un `git merge --no-ff`
  junto a un push a `develop` se tomaba por force-push. Ahora cada check corre por
  segmento de comando y el lookbehind exige inicio de token.
- Los subagentes referenciaban las rules con `../../rules/`, que desde `agents/`
  apunta fuera del plugin; corregido a `../rules/`.
- El reconocimiento de comandos de prueba tomaba como corrida cualquier ruta que
  contuviera el nombre de un runner (`/tmp/pytest-of-user/`, `pytest-cov`).

### Tests
- 195 tests (antes 66), 129 nuevos: agregación de tiempos y aditividad de los rubros,
  evidencia y escrituras masivas, escritura concurrente del log desde varios
  worktrees, eventos del tracker, guardas de worktree, contexto de sesión y
  validación estructural del plugin (frontmatter, rutas referenciadas, hooks
  declarados y sincronía de versiones).

## [0.9.0] — 2026-06-12

### Added
- **Precondición de git-flow inicializado**: antes de una acción del modelo GitFlow
  o de escritura (`start`, `finish`, `release`, `hotfix`, `commit`, `merge`, `push`,
  `tag`), el skill `git` (y `commit`) verifica si git-flow está inicializado
  (`git config --get gitflow.branch.develop`) y, si no lo está, pide confirmación al
  usuario para ejecutar `git flow init -d`. Si el usuario rechaza, continúa con `git`
  estándar cuando la acción lo permite. Las acciones de solo lectura (`status`,
  `log`, `diff`, `branch`, `checkout`, `stash`, `pull`, `sync`) no la requieren.
  Documentado también en la rule `git-flow.md`.

## [0.8.0] — 2026-06-12

### Added
- **feat(hooks)**: reforzar `safety-check` con nuevos guards y corrección del
  force-push. Arregla el regex que dejaba pasar flags cortos combinados (`-fv`,
  `-vf`, `-fu`) sin bloquear el push a ramas protegidas, sin falsos positivos en
  flags largos como `--follow-tags`. Agrega tres checks nuevos (con claves i18n
  ES/EN): `git rebase` en main/master/develop, `git branch -d/-D/--delete` de
  ramas protegidas y `git push --delete` / `push origin :rama` sobre
  main/master/develop. (ce94875)

### Changed
- **refactor(plugin)**: genericizar la configuración de proyecto y mejorar los
  flujos GitFlow. Quita los scopes y ejemplos atados a un proyecto concreto y los
  hace configurables vía `git config gitflow-es.scopes`; el paso de release ya no
  asume `app.json` (detecta el archivo de versión del stack). Alinea la
  terminología de `finish` (merge local, no "PR"), agrega un paso de push tras
  `finish` y una verificación en `undo` para no deshacer commits ya pusheados.
  (c5707e6)

### Docs
- **docs**: enfocar el README en el consumidor del plugin, eliminando las secciones
  de mantenedor y agregando una nota sobre repos privados en Instalación. (6ceb3a1)
- **docs**: agregar instrucciones de instalación para Windows (git-flow-avh vía
  Chocolatey/Scoop con Git Bash, Python 3, nota sobre el alias `python3` y entrada
  de solución de problemas). (2169e7f)
- **docs(plugin)**: reescribir el README con estructura completa (características,
  requisitos, instalación, configuración, uso por skill, estructura, tabla de
  skills, solución de problemas, contribución y licencia). (a735646)
- **docs**: precisar que git flow solo se requiere para el ciclo nativo de
  feature/hotfix/release; el resto del plugin funciona con git estándar. (7e59d10)

### Other
- **test(hooks)**: agregar suite pytest para `safety-check` e i18n, cubriendo cada
  check del hook de seguridad y el módulo i18n (66 tests). (7613fc9)

## [0.7.1] — 2026-06-05

### Changed
- **Metadata del plugin**: `plugin.json` ahora declara el autor real y los campos
  `homepage` y `repository`; antes tenía un autor placeholder.

### Docs
- README del plugin: nueva sección **Instalación**, corrección del conteo de hooks
  ("dos" → "tres", tras añadir el `PostToolUse`) y sección de **Licencia**.

## [0.7.0] — 2026-06-05

### Added
- **Subagente `release-notes-writer`** (tools `Bash`, `Write`): al preparar un
  release, lee el rango de commits desde el último tag, los agrupa por tipo
  Conventional Commit (Added/Fixed/Changed/Maintenance/Docs, más Breaking changes,
  Reverted y Other) y escribe el bloque del release en formato Keep a Changelog al
  inicio del `CHANGELOG.md`. Respeta el idioma configurado en la prosa; los
  encabezados de sección y los tipos de commit quedan fijos.

### Changed
- `skills/git/SKILL.md` delega la actualización del CHANGELOG a `release-notes-writer`
  en el paso 4 del subcomando `release`.

## [0.6.0] — 2026-06-04

### Added
- **Soporte de idioma ES/EN configurable** vía `GITFLOW_LANG` (env) o
  `git config gitflow-es.language` (default `es`). Nuevo módulo compartido
  `hooks/i18n.py` con `detect_lang()`, `lang_explicitly_set()` y un diccionario
  `MESSAGES` por idioma; los hooks `safety-check.py` y `session-context.py`
  traducen sus mensajes en runtime. **Todo el texto generado** —prosa, mensajes de
  commit y nombres de rama— se produce en el idioma configurado (los nombres de
  rama usan palabras del idioma, siempre en kebab-case ASCII). Quedan fijos los
  comandos git, los prefijos GitFlow y los tipos de Conventional Commits.
- **Solicitud guiada del idioma**: `session-context` pide configurar el idioma
  **después** de `git flow init` si aún no está inicializado, y **antes** de
  cualquier acción de git si git-flow ya está inicializado pero el idioma no se ha
  configurado. El skill `git` aplica esta precondición.
- **Hook `PostToolUse` `post-gitflow-init.py`**: detecta un `git flow init`
  exitoso y, si el idioma no está configurado, inyecta un mensaje
  (`hookSpecificOutput.additionalContext`) para que Claude pregunte el idioma en el
  mismo turno, sin esperar al próximo `SessionStart`.
- **Skill `branch-name-suggester`**: propone 2-3 nombres de rama en kebab-case con
  el prefijo GitFlow correcto a partir de una descripción libre (translitera tildes/ñ,
  ≤50 chars, detecta tickets JIRA).
- **Subagente `commit-message-writer`** (tool `Bash`): genera el mensaje de
  Conventional Commits leyendo `git diff --staged` en contexto aislado.

### Changed
- `skills/git/SKILL.md` delega la propuesta de nombre de rama a
  `branch-name-suggester` en el subcomando `start`.
- `skills/commit/SKILL.md` delega la redacción del mensaje a `commit-message-writer`
  (paso 5) y su regla de idioma pasó de "español" a "idioma configurado".
- `rules/git-flow.md`, `rules/feature-docs.md`, los skills y los subagentes incluyen
  una nota de idioma; los encabezados de formato fijo de los docs de feature nunca
  se traducen.

### Notes
- Default `es` mantiene retrocompatibilidad total: sin configuración, el
  comportamiento (y los textos) es idéntico a 0.5.2. Los nombres de rama, tipos de
  commit, scopes y encabezados de los docs de feature nunca se traducen.

## [0.5.2] — 2026-04-23

### Added
- **Excepción "primer commit"**: el safety hook permite `git commit`, `Write`, `Edit`, `MultiEdit` y `NotebookEdit` en `main`/`master` cuando el repo todavía no tiene commits. Es la única forma de crear el commit inicial antes de poder ramificar.
- **Aviso proactivo al iniciar sesión** sobre repos vacíos: `session-context` detecta repos sin commits y muestra el flujo sugerido (`git add .` → `git commit -m "chore: initial commit"` → `git flow init -d`).

### Notes
- A partir del segundo commit la regla normal vuelve a aplicar (solo commits desde ramas de trabajo).

## [0.5.1] — 2026-04-23

### Added
- **Detección de git-flow no inicializado**: `session-context` avisa al inicio de sesión cuando el repo no tiene `git flow init`, y sugiere correr `git flow init -d`.
- **Bloqueo de comandos `git flow <sub>`** en repos sin init: safety hook bloquea `git flow feature|hotfix|release|support|bugfix start/finish` si falta el init, con mensaje claro. `git flow init` y `git flow version` siguen pasando.

## [0.5.0] — 2026-04-22

### Added
- **Protección de ediciones en ramas de producción**: el safety hook ahora también se registra para `Write`, `Edit`, `MultiEdit` y `NotebookEdit`, y bloquea cualquier edición de archivos cuando la rama del repo que contiene el archivo es `main`/`master`. El mensaje incluye el flujo sugerido para crear una rama de trabajo antes de editar.

### Notes
- `develop` no está en la lista de ramas protegidas para edición, respetando la excepción documentada de "Commit directo en develop" que el skill `git` maneja cuando el usuario lo pide explícitamente.

## [0.4.0] — 2026-04-22

### Added
- **Subagente `feature-doc-writer`**: al ejecutar `/git finish` sobre ramas `feature/*`, `fix/*` o `hotfix/*`, se delega a un subagente con contexto aislado que lee `git log` y `git diff` contra la rama base y genera el archivo `docs/<feature>/<YYYY-MM-DD>-<feature>.md` con el formato del equipo. Tools restringidas: `Bash` (solo lectura) y `Write` (solo en `docs/`).

### Changed
- Paso 3 del flujo de `finish` en `skills/git/SKILL.md` ahora delega al subagente en lugar de describir que Claude genere el doc inline.

## [0.3.0] — 2026-04-22

### Added
- **Hook `PreToolUse` sobre Bash** (`safety-check.py`): bloquea comandos git destructivos — force-push a `main`/`master`/`develop`, commit directo a `main`/`master`, `--no-verify`, `--author`, `reset --hard`, `clean -f`, y `git add`/`commit` que incluya archivos sensibles (`.env`, `id_rsa`, `credentials.*`, `.pem`, etc).
- **Hook `SessionStart`** (`session-context.py`): al abrir Claude Code en un repo git imprime un resumen del estado (rama actual, tipo GitFlow, archivos pendientes, ahead/behind respecto a origin).

### Notes
- Hooks escritos en Python puro sin dependencias externas (solo stdlib). Compatibles con Python 3.7+.

## [0.2.0] — 2026-04-22

### Added
- **Skill `commit`**: genera mensajes de Conventional Commits analizando el diff real de los cambios staged, siguiendo los scopes y convenciones del proyecto.

### Changed
- Rules movidas al root del plugin (`plugins/gitflow-es/rules/`) para compartirse entre `git` y `commit` sin duplicación.
- Paso de pruebas en `/git finish` pasó de obligatorio a opcional, sugerencia en lugar de bloqueo.

## [0.1.0] — 2026-04-22

### Added
- Estructura inicial del marketplace y del plugin `gitflow-es`.
- Skill `git` cubriendo start/finish/release/hotfix/status y operaciones básicas (add, push, pull, log, diff, stash, branch, checkout, merge, tag, undo, sync).
- Rules empotradas: `rules/git-flow.md` (política del flujo) y `rules/feature-docs.md` (formato del doc al cerrar rama).

[0.6.0]: #060--2026-06-04
[0.5.2]: #052--2026-04-23
[0.5.1]: #051--2026-04-23
[0.5.0]: #050--2026-04-22
[0.4.0]: #040--2026-04-22
[0.3.0]: #030--2026-04-22
[0.2.0]: #020--2026-04-22
[0.1.0]: #010--2026-04-22
