# mi-equipo-claude-plugins

Marketplace de plugins de Claude Code para el equipo. Por ahora contiene un plugin:

- **[gitflow-es](./plugins/gitflow-es/README.md)** — Skills de Git Flow en español (`git` + `commit`).

## Instalación (para cada compañero)

### 1. Requisitos previos

- Tener Claude Code instalado.
- Tener `git flow` instalado localmente:
  ```bash
  # macOS
  brew install git-flow-avh

  # Ubuntu / Debian
  sudo apt install git-flow
  ```

### 2. Agregar el marketplace

Desde Claude Code, una sola vez por máquina:

```
/plugin marketplace add <url-del-repo>
```

Reemplaza `<url-del-repo>` por la URL de este repositorio (ej. `https://github.com/mi-equipo/mi-equipo-claude-plugins`, o una ruta local tipo `./mi-equipo-claude-plugins` si están probando sin subirlo a remoto todavía).

### 3. Instalar el plugin

```
/plugin install gitflow-es@mi-equipo
```

Eso instala los dos skills (`git` y `commit`) y las rules empotradas.

### 4. Verificar

```
/plugin
```

Debes ver `gitflow-es` listado como instalado. A partir de ahí, Claude activará los skills automáticamente cuando menciones ramas, commits, merges, PRs, etc.

## Actualizar el plugin

Cuando se publique una nueva versión:

```
/plugin marketplace update mi-equipo
/plugin install gitflow-es@mi-equipo
```

## Desinstalar

```
/plugin uninstall gitflow-es@mi-equipo
```

## Estructura del repo

```
mi-equipo-claude-plugins/
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
└── README.md
```

## Cómo agregar más plugins al marketplace

1. Crear una carpeta nueva en `plugins/<nombre-del-plugin>/`.
2. Agregar `plugins/<nombre-del-plugin>/.claude-plugin/plugin.json`.
3. Agregar la entrada correspondiente en `.claude-plugin/marketplace.json`, en el array `plugins`.
4. Commit, push y pedir al equipo que corra `/plugin marketplace update mi-equipo`.

## Publicar el repo

Para que tus compañeros puedan agregar el marketplace vía `/plugin marketplace add`, este repo debe estar accesible por git:

- **GitHub / GitLab público** — cualquiera con la URL puede instalar.
- **Privado** — funciona si cada persona tiene acceso al repo y `git clone` vía SSH o HTTPS anda en su terminal. Claude Code reutiliza las credenciales de git del sistema.

## Licencia

MIT.
