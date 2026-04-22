# gitflow-es

Plugin de Git Flow en español para Claude Code. Gestiona ramas, commits, releases y hotfixes siguiendo el modelo GitFlow, con validaciones y confirmaciones en cada paso.

## Qué incluye

Dos skills que Claude activa automáticamente según el contexto:

- **`git`** — gestiona el ciclo de vida de ramas (start / finish / release / hotfix / status) y operaciones cotidianas (add, push, pull, log, diff, stash, branch, checkout, merge, tag, undo, sync). Se activa cuando el usuario menciona ramas, PRs, merges o cualquier operación de git.
- **`commit`** — genera mensajes siguiendo Conventional Commits, analizando el diff real de los cambios staged. Se activa cuando el usuario quiere hacer commit o guardar cambios.

Y las **rules** que ambos skills comparten (fuente única de verdad del flujo):

- `rules/git-flow.md` — ramas, nomenclatura, Conventional Commits, scopes del proyecto, flujo obligatorio.
- `rules/feature-docs.md` — formato del doc que se genera al cerrar una rama.

Y dos **hooks** que refuerzan el flujo a nivel mecánico (no dependen de que Claude recuerde las reglas):

- **`PreToolUse` safety hook** — intercepta comandos Bash antes de ejecutarse y bloquea operaciones git peligrosas (ver sección "Safety hook" abajo).
- **`SessionStart` context hook** — al abrir Claude Code en un repo git, imprime un resumen del estado: rama actual, tipo GitFlow, cambios pendientes, ahead/behind respecto a origin.

Y un **subagente** que delega una tarea específica a un contexto aislado:

- **`feature-doc-writer`** — invocado automáticamente en el paso 3 de `/git finish`, genera el archivo `docs/<feature>/<YYYY-MM-DD>-<feature>.md` leyendo `git log` y `git diff` contra la rama base, en lugar de depender de la memoria conversacional. Solo tiene acceso a `Bash` (lectura) y `Write` (sobre `docs/`).

## Uso

Una vez instalado, Claude detecta el contexto automáticamente. Ejemplos:

- _"quiero arrancar una feature para el login con google"_ → activa `git`, hace `git flow feature start login-con-google`.
- _"cierra la rama actual"_ → activa `git`, genera el doc de la feature, pide confirmación y hace el finish.
- _"necesito un hotfix urgente para el crash al pagar"_ → activa `git`, parte desde `main` y crea `hotfix/*`.
- _"haz commit de los cambios"_ → activa `commit`, analiza el diff, propone mensaje y pide confirmación.

Los subcomandos `/git start`, `/git finish`, `/commit`, etc. descritos en los SKILL.md son referencias del flujo — el usuario puede usarlos literalmente o simplemente describir lo que quiere.

## Pruebas antes del finish (opcional)

El flujo de `/git finish` incluye un paso _opcional_ en el que Claude puede sugerir ejecutar las pruebas del proyecto antes de cerrar la rama. Si tu proyecto tiene un comando/script de pruebas (ej. `/run-tests`, `npm test`, `pytest`), Claude puede proponérselo al usuario. Si no lo tiene, el finish procede sin fricción.

## Safety hook — qué bloquea

El hook `PreToolUse` corre antes de cada comando Bash y antes de cada edición de archivo (Write / Edit / MultiEdit / NotebookEdit) y bloquea estos patrones mecánicamente (aunque Claude intente ejecutarlos):

| Patrón detectado | Motivo |
| ---------------- | ------ |
| Editar cualquier archivo estando parado en `main` o `master` | Regla del flujo: nunca se modifica la rama de producción directamente — se exige crear una rama de trabajo primero |
| `git push --force` / `-f` / `--force-with-lease` sobre `main`, `master` o `develop` | Reescribir historial compartido rompe el trabajo del equipo |
| `git commit` estando parado en `main` o `master` | Regla del flujo: se trabaja siempre en ramas |
| `git commit --no-verify` | Saltarse los pre-commit hooks oculta problemas |
| `git commit --author=...` | El autor siempre debe ser el usuario configurado en git |
| `git reset --hard` | Destruye cambios sin aviso |
| `git clean -f` / `-fd` / `-xf` | Elimina archivos sin confirmación (usar `-n` para previsualizar) |
| `git add` / `git commit` con `.env`, `id_rsa`, `credentials.json`, `.pem`, etc. | Previene leaks de credenciales |

Cuando bloquea, el hook devuelve un mensaje claro en español indicando qué violó y sugiriendo la alternativa correcta. **`develop` no está en la lista de ramas protegidas para edición** — las ediciones en `develop` se permiten para respetar la excepción documentada "Commit directo en develop" que el skill `git` maneja cuando el usuario lo solicita explícitamente.

El usuario siempre puede correr el comando o hacer la edición directamente en su terminal / editor si realmente lo necesita — el hook solo aplica a las acciones de Claude.

## Requisitos para los hooks

- **Python 3** en el `PATH`. Ya viene instalado por defecto en macOS y en todas las distros Linux modernas. Los hooks no tienen dependencias fuera de la stdlib.

## Dependencias externas

- `git flow` instalado en el sistema:
  - macOS: `brew install git-flow-avh`
  - Ubuntu / Debian: `sudo apt install git-flow`

## Seguridad

Todas las acciones destructivas o con efecto remoto requieren confirmación explícita:

- Nunca hace `git push` sin autorización.
- Nunca opera directo sobre `main` o `develop` — siempre a través de una rama de trabajo.
- Nunca usa `--force`, `reset --hard` ni `clean -f` sin confirmación.

## Estructura

```
gitflow-es/
├── .claude-plugin/
│   └── plugin.json
├── rules/                          ← compartidas por skills y subagentes
│   ├── git-flow.md
│   └── feature-docs.md
├── skills/
│   ├── git/
│   │   └── SKILL.md                ← referencia ../../rules/
│   └── commit/
│       └── SKILL.md                ← referencia ../../rules/
├── agents/
│   └── feature-doc-writer.md       ← subagente invocado en /git finish
├── hooks/
│   ├── hooks.json                  ← registra los hooks en Claude Code
│   ├── safety-check.py             ← PreToolUse (bloquea comandos peligrosos)
│   └── session-context.py          ← SessionStart (imprime estado git)
└── README.md
```
