# Tests de gitflow-es

Tests de los hooks y módulos Python del plugin: seguridad, i18n, contexto de
sesión, guardas de worktree y registro de tiempos.

## Requisitos

- Python 3.7+
- `pytest` (`pip install pytest`)

## Correr

Desde la raíz del repo o desde `plugins/gitflow-es`:

```bash
python3 -m pytest plugins/gitflow-es/tests -q
```

## Qué cubren

- `test_safety_check.py` — cada check del hook `safety-check.py`: force-push
  (incluida la regresión de flags cortos combinados `-fv`/`-vf`), rebase y
  borrado de ramas protegidas, `reset --hard`, `clean -f`, `--no-verify`,
  `--author`, archivos sensibles, commit en `main` y `git flow` sin init.
- `test_worktree_guard.py` — guardas de worktree: bloqueo de `git flow <tipo>
  finish` dentro del worktree de la rama (donde git-flow reporta éxito sin
  mergear), avisos no bloqueantes de la política, parseo de `git worktree add` y
  la regresión del force-push mal detectado en comandos compuestos (`--no-ff`).
- `test_session_context.py` — el bloque de contexto de SessionStart: repo sin
  commits, worktree de control vs. de trabajo, listado de worktrees y checklist
  de configuración pendiente.
- `test_timelog.py` — el modelo de tiempos: que los cinco rubros sumen el reloj,
  separación de espera e inactividad por umbral, pareo de pruebas por
  `tool_use_id`, intervalos huérfanos, validación de tiempos muertos con
  evidencia (incluido el descarte de escrituras masivas y de `mtime` futuros),
  escritura concurrente del log y parseo de `git status --porcelain`.
- `test_time_tracker.py` — el hook de registro: qué se anota en cada evento,
  cierre de intervalos de test aunque el test falle, captura de descripciones
  según `timeNotes`, atribución de trabajo a otra rama y degradación silenciosa
  cuando el registro está apagado o el payload viene incompleto.
- `test_i18n.py` — formateo y fallbacks de `i18n.t`, presencia de claves en
  ambos idiomas y resolución de `detect_lang` por variable de entorno.
- `test_plugin_structure.py` — estructura del plugin: frontmatter de skills y
  agentes, rutas relativas referenciadas que existen, scripts declarados en
  `hooks.json` y versión sincronizada entre `plugin.json`, `marketplace.json` y
  el CHANGELOG.
