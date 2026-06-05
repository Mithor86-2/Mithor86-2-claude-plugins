# Mithor86-2-claude-plugins

Marketplace personal de plugins de Claude Code. Por ahora contiene un plugin:

- **[gitflow-es](./plugins/gitflow-es/README.md)** — Skills, subagentes y hooks de Git Flow con idioma configurable ES/EN (`git`, `commit`, `branch-name-suggester`).

## Instalación

### 1. Requisitos previos

- [Claude Code](https://claude.com/claude-code) instalado.
- `git flow` (git-flow-avh) **solo si vas a usar el ciclo nativo de GitFlow** (`start`/`finish` de feature/hotfix/release y `git flow init`). El resto del plugin funciona con `git` estándar.
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

  En Windows usa **Git Bash** ([Git para Windows](https://git-scm.com/download/win)) como shell.
- Python 3 (viene por defecto en macOS y distros Linux modernas; el hook está en Python puro sin dependencias). En **Windows** instálalo desde [python.org](https://www.python.org/downloads/) o `winget install Python.Python.3`; como los hooks invocan `python3`, conviene instalarlo desde **Microsoft Store** (crea ese alias).

### 2. Agregar el marketplace

Desde Claude Code, una sola vez por máquina:

```
/plugin marketplace add <url-o-path>
```

Opciones:

- **GitHub público/privado:** `/plugin marketplace add Mithor86-2/Mithor86-2-claude-plugins`
- **URL completa:** `/plugin marketplace add https://github.com/Mithor86-2/Mithor86-2-claude-plugins`
- **Ruta local** (para desarrollo): `/plugin marketplace add /ruta/absoluta/a/Mithor86-2-claude-plugins`

> Si el repo es privado, igual funciona siempre que tengas acceso y `git clone` (SSH o HTTPS) ande en tu terminal: Claude Code reutiliza las credenciales de git del sistema.

### 3. Instalar el plugin

```
/plugin install gitflow-es@Mithor86-2
```

Eso instala los skills (`git` y `commit`), el subagente (`feature-doc-writer`), los hooks de seguridad y contexto, y las rules empotradas.

### 4. Recargar y verificar

```
/reload-plugins
```

Deberías ver un resumen tipo `2 skills · 1 agents · 2 hooks` (si los hooks quedan en `0`, corre `/doctor` para ver el error).

Luego:

```
/plugin
```

Debe listar `gitflow-es` como habilitado.

### 5. Probar

Abre Claude Code en un repo git cualquiera. Al iniciar, deberías ver un bloque `## Estado GitFlow del repo` con la rama actual. Si el repo no está inicializado con `git flow init`, el bloque lo avisa y sugiere el flujo correcto.

## Actualizar el plugin

Cuando se publique una nueva versión:

```
/plugin marketplace update Mithor86-2
/reload-plugins
```

Si hay cambios incompatibles o no se recargan:

```
/plugin uninstall gitflow-es@Mithor86-2
/plugin install gitflow-es@Mithor86-2
/reload-plugins
```

## Desinstalar

```
/plugin uninstall gitflow-es@Mithor86-2
/plugin marketplace remove Mithor86-2
```

## Estructura del repo

```
Mithor86-2-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json                  ← catálogo del marketplace
├── plugins/
│   └── gitflow-es/                       ← el plugin en sí
│       ├── .claude-plugin/plugin.json
│       ├── rules/
│       │   ├── git-flow.md
│       │   └── feature-docs.md
│       ├── skills/
│       │   ├── git/SKILL.md
│       │   └── commit/SKILL.md
│       ├── agents/
│       │   └── feature-doc-writer.md     ← subagente para generar el doc al finish
│       ├── hooks/
│       │   ├── hooks.json
│       │   ├── safety-check.py           ← bloquea operaciones git peligrosas
│       │   └── session-context.py        ← imprime estado git al iniciar sesión
│       └── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
└── README.md
```

## Licencia

MIT — ver [LICENSE](./LICENSE).
