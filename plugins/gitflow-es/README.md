# gitflow-es

![versión](https://img.shields.io/badge/versi%C3%B3n-0.9.0-blue)
![licencia](https://img.shields.io/badge/licencia-MIT-green)
![idioma](https://img.shields.io/badge/idioma-ES%20%2F%20EN-orange)

**Repositorio:** <https://github.com/Mithor86-2/Mithor86-2-claude-plugins> · **Plugin:** [`plugins/gitflow-es`](https://github.com/Mithor86-2/Mithor86-2-claude-plugins/tree/main/plugins/gitflow-es)

Plugin de **Git Flow para Claude Code** con idioma configurable (Español / English). Gestiona ramas, commits, releases y hotfixes siguiendo el modelo GitFlow, reforzado con hooks de seguridad y subagentes que generan documentación, mensajes de commit y changelogs a partir del histórico git real.

## Características

- **Skill `git`** — ciclo de vida completo de ramas: `start`, `finish`, `release`, `hotfix`, `status` y operaciones básicas (add, push, pull, log, diff, stash, branch, checkout, merge, tag, undo, sync).
- **Skill `commit`** — genera y aplica commits siguiendo Conventional Commits, analizando el diff staged real.
- **Skill `branch-name-suggester`** — propone 2-3 nombres de rama en kebab-case con el prefijo GitFlow correcto.
- **3 subagentes** (contexto aislado): `feature-doc-writer` (doc de la rama al cerrarla), `commit-message-writer` (mensaje de commit desde el diff) y `release-notes-writer` (CHANGELOG agrupado por tipo Conventional).
- **3 hooks mecánicos**: `PreToolUse` (bloquea operaciones git peligrosas), `PostToolUse` (pide el idioma tras `git flow init`) y `SessionStart` (imprime el estado GitFlow al abrir el repo).
- **Idioma ES/EN configurable** — todo el texto generado (prosa, mensajes de commit, nombres de rama) sale en el idioma elegido.
- **Rules empotradas** — política de ramas y formato de docs como fuente única de verdad.

> Este plugin **no aporta ni requiere connectors MCP**: opera solo con `git` y, opcionalmente, el binario `git flow`.

## Requisitos previos

- **Claude Code** con soporte de plugins/marketplace.
- **Python 3** en el `PATH` — necesario para los hooks. Viene por defecto en macOS y en distros Linux modernas. Los hooks usan solo la stdlib (sin dependencias).
  - En **Windows** instálalo desde [python.org](https://www.python.org/downloads/) o `winget install Python.Python.3`. Importante: los hooks invocan `python3`; instalar Python desde **Microsoft Store** crea ese alias. Si solo tienes `python`/`py`, revisa la sección [Solución de problemas](#solución-de-problemas).
- **`git flow` (git-flow-avh)** — **solo si vas a usar el ciclo nativo de GitFlow**: `start`/`finish` de feature/hotfix/release y `git flow init`. El resto del plugin funciona con `git` estándar.

  ```bash
  # macOS
  brew install git-flow-avh

  # Ubuntu / Debian
  sudo apt install git-flow
  ```

  ```powershell
  # Windows (Chocolatey)
  choco install gitflow-avh

  # Windows (Scoop)
  scoop install gitflow
  ```

  En Windows usa **Git Bash** (incluido en [Git para Windows](https://git-scm.com/download/win)) como shell. Guía oficial de instalación de git-flow-avh: <https://github.com/petervanderdoes/gitflow-avh/wiki/Installation>.
- **Node.js**: no se requiere.
- **Credenciales / connectors**: ninguno.

## Instalación

El plugin se distribuye en el marketplace **Mithor86-2**. Desde Claude Code:

```text
/plugin marketplace add Mithor86-2/Mithor86-2-claude-plugins
/plugin install gitflow-es@Mithor86-2
/reload-plugins
```

Verifica que quedó activo:

```text
/plugin
```

Deberías ver `gitflow-es` habilitado y un resumen tipo `3 skills · 3 agents · 3 hooks`. Si los hooks aparecen en `0`, corre `/doctor`.

Para actualizar a una versión nueva:

```text
/plugin marketplace update Mithor86-2
/reload-plugins
```

## Configuración

La única configuración del plugin es el **idioma de salida** (ES/EN). Se resuelve con esta prioridad:

| Orden | Fuente | Ejemplo |
| --- | --- | --- |
| 1 | Variable de entorno `GITFLOW_LANG` | `export GITFLOW_LANG=en` |
| 2 | `git config gitflow-es.language` | `git config gitflow-es.language en` |
| 3 | Default | `es` |

```bash
# Solo la sesión actual
export GITFLOW_LANG=en

# Persistente para este repo
git config gitflow-es.language en

# Persistente para todos los repos del usuario
git config --global gitflow-es.language en
```

Valores válidos: `es` y `en`; cualquier otro cae a español. Si abres un repo con git-flow ya inicializado y el idioma sin configurar, el plugin te lo pedirá antes de la primera acción de git. No requiere archivos de config adicionales ni permisos especiales más allá de los que Claude Code pide para ejecutar `git`.

## Uso

Claude detecta el contexto automáticamente: puedes usar los subcomandos literalmente o solo describir lo que quieres.

### Crear una rama (`git` + `branch-name-suggester`)

```text
quiero arrancar una feature para el login con Google
```

Propone 2-3 nombres (`feature/login-con-google`, …), confirma contigo y ejecuta `git flow feature start <nombre>`.

### Hacer un commit (`commit` + `commit-message-writer`)

```text
haz commit de los cambios
```

Stagea (si hace falta), el subagente lee `git diff --staged`, propone un mensaje Conventional y pide confirmación antes de `git commit`. Salida esperada:

```text
feat(auth): agregar validación de email en login
```

### Cerrar una rama (`git` + `feature-doc-writer`)

```text
cierra la rama actual
```

Genera `docs/<feature>/<YYYY-MM-DD>-<feature>.md` desde el `git log`/`git diff`, lo revisa contigo y ejecuta `git flow feature finish`.

### Preparar un release (`git` + `release-notes-writer`)

```text
/git release 0.8.0
```

Crea `release/0.8.0` y el subagente escribe el bloque del CHANGELOG agrupado por tipo Conventional (Added/Fixed/Changed/…) leyendo los commits desde el último tag.

### Ver el estado GitFlow

```text
/git status
```

Muestra rama actual, tipo GitFlow, base, destino del PR y archivos pendientes.

### Hotfix urgente

```text
necesito un hotfix para el crash al pagar
```

Parte desde `main`, crea `hotfix/<descripcion>` y avisa que el cierre va a `main` **y** a `develop`.

## Estructura del proyecto

```text
gitflow-es/
├── .claude-plugin/
│   └── plugin.json                 ← manifiesto del plugin (nombre, versión, metadata)
├── rules/                          ← fuente única de verdad, compartida por skills y subagentes
│   ├── git-flow.md                 ← política de ramas, nomenclatura, Conventional Commits
│   └── feature-docs.md             ← formato del doc que se genera al cerrar una rama
├── skills/
│   ├── git/SKILL.md                ← skill principal de operaciones git
│   ├── commit/SKILL.md             ← skill de Conventional Commits
│   └── branch-name-suggester/SKILL.md  ← propone nombres de rama
├── agents/
│   ├── feature-doc-writer.md       ← subagente: doc de la rama (en /git finish)
│   ├── commit-message-writer.md    ← subagente: mensaje de commit (por /commit)
│   └── release-notes-writer.md     ← subagente: CHANGELOG (en /git release)
├── hooks/
│   ├── hooks.json                  ← registra los hooks en Claude Code
│   ├── i18n.py                     ← mensajes ES/EN + detección de idioma (módulo compartido)
│   ├── safety-check.py             ← PreToolUse: bloquea comandos git peligrosos
│   ├── post-gitflow-init.py        ← PostToolUse: pide el idioma tras git flow init
│   └── session-context.py          ← SessionStart: imprime el estado git
├── tests/                          ← tests pytest de los hooks (safety + i18n)
└── README.md
```

## Skills incluidos

| Skill | Qué hace | Cuándo se activa (triggers) |
| --- | --- | --- |
| `git` | Ciclo de vida de ramas y commits GitFlow (start/finish/release/hotfix/status) + operaciones básicas. | Menciones de ramas, PRs, merges, releases, hotfixes, push, pull, stash, tags… aunque no se diga "gitflow". |
| `commit` | Genera y aplica un commit Conventional analizando el diff staged. | "haz commit", "guarda los cambios", "registra esto", o cuando `git` delega el mensaje. |
| `branch-name-suggester` | Propone 2-3 nombres de rama en kebab-case con prefijo GitFlow. | Al ir a crear una rama cuando el nombre no está definido, o desde `/git start`. |

Subagentes (se invocan automáticamente desde los skills, no por el usuario): **`feature-doc-writer`** (en `/git finish`), **`commit-message-writer`** (por `/commit`), **`release-notes-writer`** (en `/git release`).

## Solución de problemas

- **Tras instalar veo `0 hooks` (o los hooks no corren).** Verifica que `python3` está en el `PATH` y corre `/doctor` para ver el error. Luego `/reload-plugins`.
- **Windows: los hooks no corren / `python3` no se reconoce.** Los hooks invocan `python3`, pero el instalador de python.org crea `python` y `py`, no `python3`. Instala Python desde **Microsoft Store** (crea el alias `python3`) o añade un alias `python3` en el `PATH`. Usa **Git Bash** como shell para que los comandos `git`/`python3` se resuelvan igual que en macOS/Linux.
- **`git flow: command not found`.** No tienes git-flow-avh instalado. Instálalo (ver Requisitos) o usa ramas `fix/`, `refactor/` o `chore/`, que funcionan con `git` estándar.
- **Los textos no salen en inglés.** Configura `GITFLOW_LANG=en` o `git config gitflow-es.language en`. Cualquier valor distinto de `es`/`en` cae a español.
- **El hook bloquea mi commit en `main`.** Es intencional: el flujo exige trabajar en ramas. Crea una rama con `/git start`. (Excepción: el primer commit de un repo vacío sí se permite.)
- **Un subagente avisa que no hay nada que generar.** Asegúrate de estar en la rama correcta y de que hay commits en el rango (p. ej. `release-notes-writer` necesita commits desde el último tag).
- **No quiero que me pida el idioma cada vez.** Configúralo una vez con `git config gitflow-es.language <es|en>` (o `--global`).

## Contribución y licencia

- **Reportar bugs / proponer cambios:** abre un issue o un Pull Request en el repositorio: <https://github.com/Mithor86-2/Mithor86-2-claude-plugins>. Sigue Conventional Commits (el propio plugin te ayuda a redactarlos).
- **Tests:** los hooks tienen cobertura con `pytest`. Córrelos con `python3 -m pytest plugins/gitflow-es/tests -q` (ver [tests/README.md](tests/README.md)).
- **Licencia:** MIT — ver [LICENSE](../../LICENSE).
