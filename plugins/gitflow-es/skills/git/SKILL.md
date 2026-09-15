---
name: git
description: Gestiona el ciclo de vida completo de ramas y commits siguiendo el modelo GitFlow del proyecto. Úsalo siempre que el usuario mencione ramas, PRs, merges, releases, hotfixes, staging, push, pull, stash, tags, o cualquier operación de git — aunque no diga "gitflow" explícitamente. Cubre los subcomandos start, finish, release, hotfix, status y operaciones básicas (add, push, pull, log, diff, stash, branch, checkout, merge, tag, undo, sync). Para generar commits, delega al skill `commit` de este mismo plugin.
---

# Git Flow

Gestiona el ciclo de vida completo de ramas y commits siguiendo el modelo GitFlow del proyecto.

> **Fuente única de verdad:** `../../rules/git-flow.md` (dentro de este plugin) define ramas principales, tipos de rama, nomenclatura, convención de commits, scopes y reglas del flujo obligatorio.
> Este skill solo describe los comandos operativos. Consultar la rule cuando haya duda de política.

## Idioma de salida

Antes de responder, detecta el idioma configurado para gitflow-es y produce
**todo** el texto generado en ese idioma — incluyendo prosa, **mensajes de commit y
nombres de rama**:
1. Si `GITFLOW_LANG` está definida, úsala.
2. Si no, ejecuta `git config --get gitflow-es.language` y usa su valor.
3. Si ninguna existe, usa español (`es`) por defecto.

Valores válidos: `es` y `en`; cualquier otro se trata como `es`. Los **nombres de
rama** usan palabras del idioma configurado pero siempre en kebab-case ASCII
(translitera tildes/ñ). Solo son fijos y **no se traducen**: los comandos git, los
prefijos GitFlow (`feature/`, `fix/`…) y los tipos de Conventional Commits (`feat`,
`fix`…).

## Precondición: git-flow inicializado

**Antes** de ejecutar una acción del modelo GitFlow o que modifique el repo,
verifica si git-flow está inicializado:

```bash
git config --get gitflow.branch.develop   # vacío / sin salida = NO inicializado
```

**Aplica a:** `start`, `finish`, `release`, `hotfix`, `commit`, `merge`, `push`, `tag`.
**No aplica a** las acciones de solo lectura o consulta: `status`, `log`, `diff`,
`branch`, `checkout`, `stash`, `pull`, `sync` (estas proceden sin validar init).

- **Si YA está inicializado:** procede con la acción.
- **Si NO está inicializado:** **detente y pide confirmación al usuario** para
  inicializarlo con los defaults del equipo:
  - Si **acepta** → ejecuta `/git init` (asistente completo: git-flow, idioma,
    raíz de worktrees y registro de tiempos) o, si el usuario solo quiere lo
    mínimo, `git flow init -d`. Luego continúa con la acción solicitada.
  - Si **rechaza** → no inicialices. Continúa con `git` estándar cuando la acción
    lo permita (`fix`/`refactor`/`chore`, commit, merge, push, tag), advirtiendo
    que los comandos `git flow` nativos (`feature`/`hotfix`/`release start/finish`)
    no estarán disponibles hasta inicializar. No vuelvas a insistir en la misma
    sesión salvo que el usuario invoque un subcomando que **requiera** git-flow.

> El hook `safety-check` ya bloquea los subcomandos `git flow <feature|hotfix|release>`
> en repos sin init; esta precondición es la capa conversacional que ofrece resolverlo.

## Configuración de idioma (precondición)

Una vez resuelta la precondición de git-flow (arriba), asegúrate de que el idioma de
gitflow-es esté configurado (revisa `GITFLOW_LANG` o
`git config --get gitflow-es.language`):

- **Si NO está configurado:** pregúntale el idioma (`es`/`en`) **antes** de hacer la
  acción solicitada y guárdalo con `git config gitflow-es.language <lang>`. (Si
  acabas de inicializar git-flow en el paso anterior, pídelo justo después del init.)
- **Si ya está configurado:** procede; genera todos los textos en ese idioma.

## Uso

### GitFlow

```
/git init                          → Inicializa git-flow y toda la configuración del plugin
/git start <tipo> <descripcion>   → Inicia una rama GitFlow desde la base correcta
/git finish                        → Cierra la rama actual fusionándola (merge local) en su destino
/git release <version>             → Inicia un ciclo de release
/git hotfix <descripcion>          → Inicia un hotfix urgente desde main
/git status                        → Muestra el estado GitFlow actual
/git worktree [sub]                → Lista, crea, remueve o limpia worktrees
/commit                            → Genera y aplica un commit con Conventional Commits
```

### Comandos básicos

```
/git add [archivos]               → Stagea archivos (todos o específicos)
/git push                         → Publica la rama actual en origin
/git pull                         → Actualiza la rama actual desde origin
/git log [n]                      → Muestra el historial de commits
/git diff [staged]                → Muestra diferencias actuales o staged
/git stash                        → Guarda cambios temporalmente
/git stash pop                    → Restaura el último stash
/git branch                       → Lista todas las ramas locales y remotas
/git checkout <rama>              → Cambia a una rama existente
/git merge <rama>                 → Fusiona una rama en la actual (con confirmación)
/git tag <version>                → Crea un tag en el commit actual
/git undo                         → Revierte el último commit manteniendo los cambios
/git sync                         → Sincroniza develop y main con origin
```

---

## Subcomando: init

Deja el repo listo para trabajar con el plugin en un solo paso: git-flow, idioma,
raíz de worktrees y registro de tiempos. Es lo que el hook de sesión ofrece cuando
detecta configuración incompleta.

### Flujo

1. **Diagnóstico** — leer el estado actual y mostrárselo al usuario:

   ```bash
   git config --get gitflow.branch.develop    # vacío = git-flow sin inicializar
   git config --get gitflow-es.language       # vacío = idioma sin configurar
   git config --get gitflow-es.worktreeRoot   # vacío = se usa el default
   git config --get gitflow-es.timeTracking   # vacío = se usa el default (on)
   ```

2. **git-flow** — si falta, pedir confirmación y ejecutar `git flow init -d`
   (`main` producción, `develop` integración, prefijos estándar). Si el repo no
   tiene commits, primero guiar al commit inicial.
3. **Idioma** — preguntar `es` / `en` y guardar:
   `git config gitflow-es.language <lang>`.
4. **Raíz de worktrees** — proponer el default (`<padre-del-repo>/<repo>-worktrees`)
   y confirmarlo. Si el usuario elige otra ruta, guardarla con
   `git config gitflow-es.worktreeRoot <ruta>`; **si esa ruta queda dentro del
   repo, agregarla a `.gitignore`** en el mismo paso.
5. **Registro de tiempos** — preguntar si lo quiere activo (default sí) y guardar
   `git config gitflow-es.timeTracking on|off`. Mencionar que las notas de trabajo
   (`gitflow-es.timeNotes`) y la validación por evidencia (`gitflow-es.evidence`)
   se pueden apagar por separado, y que el registro es **local**: vive dentro de
   `.git/` y nunca se commitea.
6. **Scopes de commit (opcional)** — proponer scopes a partir de la estructura real
   del repo y, si el usuario acepta, guardarlos:
   `git config gitflow-es.scopes "auth,api,ui,deps"`.
7. **Resumen** — mostrar la tabla final de configuración y el siguiente paso
   sugerido (`/git start <tipo> <descripcion>`).

### Claves de configuración

| Clave | Default | Qué controla |
| --- | --- | --- |
| `gitflow-es.language` | `es` | Idioma de todo el texto generado |
| `gitflow-es.scopes` | — | Lista de scopes válidos para Conventional Commits |
| `gitflow-es.worktreeRoot` | `<padre-del-repo>/<repo>-worktrees` | Dónde se crean los worktrees |
| `gitflow-es.timeTracking` | `on` | Registro de tiempos por rama |
| `gitflow-es.timeNotes` | `on` | Descripción del trabajo (prompts + asuntos de commit) |
| `gitflow-es.evidence` | `on` | Validación de tiempos muertos por `mtime` y commits |
| `gitflow-es.idleThresholdMin` | `15` | Minutos a partir de los cuales un hueco es inactividad |
| `gitflow-es.testPattern` | — | Regex extra para reconocer comandos de pruebas |

> Todas son de repo. Para aplicarlas a todos los repos del usuario, agregar
> `--global` (p. ej. `git config --global gitflow-es.language en`).

---

## Subcomando: start

Crea una rama desde la base correcta según el tipo.

> **Obligatorio usar comandos git-flow** para los tipos que tienen soporte nativo.

> **Modo worktree (default).** Cada rama nace en su propio worktree desde
> `develop`. Ver `../../rules/git-flow.md` → "Worktrees (obligatorio)".

### Flujo

1. Verificar que no hay cambios sin commitear (`git status`)
2. **Proponer el nombre de la rama** delegando al skill `branch-name-suggester`:
   pásale la descripción libre del usuario; muestra las 2-3 alternativas en
   kebab-case que devuelva y confirma una con el usuario antes de crear la rama.
   El slug confirmado se reusa tal cual para la rama, la carpeta del worktree y
   el registro de tiempos.
3. **Resolver la ruta del worktree**:
   ```bash
   git rev-parse --show-toplevel                  # raíz del worktree actual
   git config --get gitflow-es.worktreeRoot       # vacío → default
   ```
   Default: `<padre-del-repo>/<nombre-del-repo>-worktrees/<tipo>-<slug>`.
4. **Actualizar la base en el worktree de control** (nunca desde otro worktree):
   ```bash
   git -C <control> pull --ff-only origin develop   # o main, si es hotfix
   ```
5. **Crear rama + worktree** en un solo comando y confirmar el resultado:
   ```bash
   git worktree add -b <tipo>/<slug> "<ruta>" <base>
   ```
6. **Registrar el inicio de la rama en el log de tiempos** con la descripción que
   dio el usuario (ver skill `tiempos`).
7. Informar la ruta del worktree creado y **que el trabajo continúa ahí**.

### Tipos de ramas y comandos

| Tipo       | Base     | Comando (modo worktree)                                          |
| ---------- | -------- | ---------------------------------------------------------------- |
| `feature`  | `develop`| `git worktree add -b feature/<slug> "<ruta>" develop`             |
| `fix`      | `develop`| `git worktree add -b fix/<slug> "<ruta>" develop`                 |
| `refactor` | `develop`| `git worktree add -b refactor/<slug> "<ruta>" develop`            |
| `chore`    | `develop`| `git worktree add -b chore/<slug> "<ruta>" develop`               |
| `release`  | `develop`| `git worktree add -b release/<version> "<ruta>" develop`          |
| `hotfix`   | `main`   | `git worktree add -b hotfix/<slug> "<ruta>" main`                 |

> En **modo sin worktree** (solo si el usuario lo pide explícitamente) los tipos
> con soporte nativo usan `git flow <tipo> start <nombre>` y el resto queda
> bloqueado por política: `git checkout -b` y `git switch -c` nunca se usan.

### Reglas

- Siempre en **kebab-case**, sin espacios ni caracteres especiales (el skill `branch-name-suggester` aplica estas reglas y propone alternativas)
- Máximo 50 caracteres en el nombre
- **Nunca** usar `git checkout -b` ni `git switch -c` — la rama se crea con `git worktree add -b` o con `git flow <tipo> start`
- `hotfix/` es la **única** excepción de base (parte de `main`); cualquier otra base distinta de `develop` requiere pedido explícito del usuario

---

## Subcomando: finish

Cierra la rama actual fusionándola en su destino según GitFlow.

> **Obligatorio usar comandos git-flow** para los tipos que tienen soporte nativo.

### Flujo

1. Detectar la rama actual con `git branch --show-current`
2. Listar los commits incluidos: `git log <base>..HEAD --oneline`
3. **Generar la documentación de la rama** delegando al subagente `feature-doc-writer`:
   - Obligatorio para ramas `feature/*`, `fix/*` y `hotfix/*`
   - Opcional (preguntar al usuario) para `chore/*` y `refactor/*` sin cambios de lógica
   - El subagente lee `git log <base>..HEAD` y `git diff <base>...HEAD` y produce el archivo `docs/<feature>/<YYYY-MM-DD>-<feature>.md` con el formato del equipo (definido en `../../rules/feature-docs.md`)
   - Revisar la salida del subagente con el usuario antes de continuar — las secciones de "Pruebas manuales" siempre quedan en `⚠️` hasta validación humana
4. _(Opcional)_ Si el proyecto cuenta con un comando de pruebas (ej. `/run-tests`, `npm test`, `pytest`), puedes sugerirle al usuario ejecutarlo antes del finish. **No bloquear** el finish por esto: si el proyecto no tiene pruebas automatizadas, o el usuario prefiere omitirlas, continuar sin fricción.
5. Mostrar resumen y pedir confirmación antes de fusionar
6. **Cerrar la rama en modo worktree** — el orden importa y no es negociable:
   ```bash
   # a. guardar el sha de la rama, para verificar después
   SHA=$(git rev-parse HEAD)

   # b. registrar la evidencia de tiempos ANTES de remover el worktree
   #    (al removerlo desaparecen los mtime de los archivos)
   python3 "<plugin>/hooks/time-tracker.py" --mark branch_finish --note "<resumen>"

   # c. salir del worktree, removerlo y cerrar desde el worktree de control
   cd <control>
   git worktree remove "<ruta-del-worktree>"
   git flow feature finish <slug>       # o el merge manual para fix/refactor/chore
   ```
7. **Verificar las postcondiciones** — `git flow finish` imprime "Summary of
   actions" y sale con código 0 incluso cuando no mergeó ni borró nada, así que
   el éxito se comprueba, no se asume:
   ```bash
   git branch --list <tipo>/<slug>               # debe salir VACÍO
   git merge-base --is-ancestor $SHA develop     # debe salir 0
   ```
   Si alguna falla: **detenerse y reportarlo** — no reintentar a ciegas.
8. **Publicar el resultado** (con confirmación). El `finish` actualiza las ramas
   base **solo en local**; el equipo no ve nada hasta que se publique. Ofrecer
   publicar según el tipo de rama:
   - `feature/`, `fix/`, `refactor/`, `chore/` → publicar `develop`
   - `hotfix/`, `release/` → publicar `main` y `develop`, más los tags
     (estas ramas mergean en `main` **y** `develop` y crean tag)

   **Nunca** publicar sin confirmación explícita del usuario (ver "Reglas
   generales de seguridad").
9. Mostrar el **reporte de tiempos de la rama** (skill `tiempos`) como cierre.

### Comandos por tipo de rama

Todos se ejecutan **desde el worktree de control** y **con el worktree de la rama
ya removido**.

| Tipo de rama | Comando (obligatorio)                                                    |
| ------------ | ------------------------------------------------------------------------ |
| `feature/*`  | `git flow feature finish <nombre>`                                       |
| `hotfix/*`   | `git flow hotfix finish <nombre>`                                        |
| `release/*`  | `git flow release finish <version>`                                      |
| `fix/*`      | `git merge --no-ff fix/<nombre>` y luego `git branch -d fix/<nombre>`    |
| `refactor/*` | `git merge --no-ff refactor/<nombre>` y luego `git branch -d refactor/<nombre>` |
| `chore/*`    | `git merge --no-ff chore/<nombre>` y luego `git branch -d chore/<nombre>` |

> El worktree de control ya está parado en `develop`: por eso el merge manual
> **no lleva `git checkout develop`** (ese checkout fallaría si otro worktree
> tuviera `develop` ocupado).

> ⛔ **Nunca** ejecutar `git flow <tipo> finish` dentro del worktree de la rama:
> git-flow no puede hacer checkout de `develop` ahí, no mergea, no borra la rama
> y aun así reporta éxito. El hook `safety-check` bloquea ese caso.

---

## Subcomando: commit

> Delega al skill `commit` de este mismo plugin — fuente única de verdad para commits.
> Invocar `/commit` directamente en lugar de este subcomando.

---

## Subcomando: release

Inicia el proceso formal de release siguiendo GitFlow.

### Flujo

1. Verificar que `develop` está actualizado (`git -C <control> pull --ff-only origin develop`)
2. **Verificar el prefijo de tag antes de cerrar** — si el repo ya tiene tags, el
   prefijo configurado debe coincidir con ellos, o el release quedará con un tag
   fuera de convención:
   ```bash
   git tag --sort=-version:refname | head -3    # p. ej. v0.9.0 → usan prefijo "v"
   git config --get gitflow.prefix.versiontag   # vacío = git-flow tagueará "0.10.0"
   git config gitflow.prefix.versiontag v       # alinearlo si hace falta
   ```
3. Crear la rama `release/<version>` en su worktree desde `develop`:
   `git worktree add -b release/<version> "<ruta>" develop`
4. Mostrar los commits incluidos desde el último tag (`git log <ultimo-tag>..develop --oneline`)
5. Tareas de release dentro del worktree:
   - Actualizar la versión en el archivo del proyecto según el stack
     (`package.json`, `app.json`, `pyproject.toml`, `Cargo.toml`, `composer.json`, etc.)
   - **Actualizar el `CHANGELOG`** delegando al subagente `release-notes-writer`: lee
     el rango de commits desde el último tag y genera el bloque del release agrupado
     por tipo Conventional (Keep a Changelog), escribiéndolo al inicio del
     `CHANGELOG.md`. Revisar su salida con el usuario antes de continuar.
   - Revisar que la documentación siga describiendo el proyecto real (estructura,
     conteo de skills/hooks, badges de versión).
   - Hacer commit de los cambios de versión: `chore(release): bump version to <version>`
6. Al terminar, cerrar con `/git finish`, que fusiona en `main` **y** `develop` y crea el tag.

### Cómo pasar el mensaje del tag (trampa de git-flow en macOS)

`git flow release finish -m "Release v1.2.0"` **falla** con el `getopt` que trae
macOS:

```text
flags:FATAL the available getopt does not support spaces in options
```

Y `git flow release finish` sin `-m` abre un editor para el mensaje del tag anotado;
si el mensaje queda vacío, git aborta el tag y el release queda a medias. Dos salidas:

```bash
# a) mensaje sin espacios
git flow release finish -m Release-v1.2.0 1.2.0

# b) editor de un solo uso que escribe el mensaje (permite espacios)
cat > /tmp/tagmsg.sh <<'EOS'
#!/bin/sh
printf '%s\n' "Release v1.2.0 — resumen corto" > "$1"
EOS
chmod +x /tmp/tagmsg.sh
GIT_MERGE_AUTOEDIT=no GIT_EDITOR=/tmp/tagmsg.sh git flow release finish 1.2.0
```

`GIT_MERGE_AUTOEDIT=no` evita además que se abra el editor en los merges a `main`
y a `develop`.

### Verificar el cierre del release

Igual que con las features, el código de salida de git-flow no alcanza:

```bash
git branch --list release/<version>                  # debe salir vacío
git tag --list v<version>                            # debe existir
git merge-base --is-ancestor <sha-del-release> main     # debe salir 0
git merge-base --is-ancestor <sha-del-release> develop  # debe salir 0
```

### Publicar el release

Con confirmación explícita del usuario, y recordando que `main` puede haber
avanzado por fuera (merges desde la web, archivos creados en GitHub):

```bash
git fetch origin
git log --oneline main..origin/main   # si trae algo, integrarlo ANTES de publicar
```

Si el remoto tiene commits propios, integrarlos con un merge normal y volver a
publicar — **nunca** con `--force`.

---

## Subcomando: hotfix

Inicia un hotfix urgente desde `main`.

### Flujo

1. Verificar rama actual y cambios pendientes
2. Cambiar a `main` y actualizar (`git pull origin main`)
3. Crear rama `hotfix/<descripcion>` desde `main`
4. Informar que al terminar se cierra con `/git finish`, que fusiona el hotfix en `main` **y** en `develop`

---

## Subcomando: status

### Flujo

1. Ejecutar `git branch --show-current` — rama actual
2. Ejecutar `git status` — cambios staged/unstaged
3. Ejecutar `git log --oneline -5` — últimos commits
4. Detectar el tipo de rama y mostrar:
   - Rama actual y su tipo GitFlow
   - Base de la rama (develop o main)
   - Destino del PR cuando se haga `/git finish`
   - Archivos pendientes de commit

---

## Subcomando: worktree

Gestiona los worktrees del repo. Para repartir varias tareas a la vez, ver el
skill `worktrees` de este mismo plugin.

```
/git worktree              → Lista los worktrees y qué rama tiene cada uno
/git worktree add <rama>   → Crea el worktree de una rama existente
/git worktree remove       → Remueve el worktree de la rama indicada
/git worktree prune        → Limpia registros de worktrees borrados a mano
```

**Flujo para listar:**

1. `git worktree list` — ruta, sha y rama de cada worktree
2. Identificar el **worktree de control** (el primero: el repo principal) y marcarlo
3. Señalar worktrees huérfanos (carpeta borrada a mano) y ofrecer `git worktree prune`

**Flujo para remover:**

1. Verificar que el worktree no tiene cambios sin commitear (`git -C <ruta> status --porcelain`)
2. Pedir confirmación mostrando qué se va a remover
3. `git worktree remove "<ruta>"` (nunca `rm -rf`: dejaría el registro colgado)
4. Si el usuario venía trabajando ahí, informar que la sesión continúa en el worktree de control

**Regla:** remover el worktree **no** borra la rama ni sus commits — solo la copia
de trabajo. Cerrar la rama sigue siendo trabajo de `/git finish`.

---

## Comandos básicos

### add

Stagea archivos para el próximo commit.

**Flujo:**

1. Si se pasan argumentos, stagear esos archivos: `git add <archivos>`
2. Si no hay argumentos, mostrar `git status` y preguntar qué desea stagear:
   - `todo` → `git add .`
   - `interactivo` → listar archivos y confirmar uno a uno
3. Confirmar qué quedó staged con `git status`

**Regla:** nunca stagear `.env`, archivos de credenciales ni binarios grandes.

---

### push

Publica la rama actual en origin.

**Flujo:**

1. Verificar la rama actual con `git branch --show-current`
2. Advertir si la rama es `main` o `develop` — requiere confirmación explícita
3. Si la rama no tiene upstream: `git push -u origin <rama>`
4. Si ya tiene upstream: `git push`
5. Confirmar que la rama fue publicada correctamente

---

### pull

Actualiza la rama actual desde origin.

**Flujo:**

1. Ejecutar `git status` — si hay cambios sin commitear, sugerir hacer stash primero
2. Ejecutar `git pull origin <rama-actual>`
3. Informar si hubo conflictos y qué archivos los tienen

---

### log

Muestra el historial de commits de forma legible.

**Flujo:**

1. Si hay argumento numérico `n`, mostrar los últimos `n` commits
2. Por defecto mostrar los últimos 10: `git log --oneline --graph --decorate -10`
3. Presentar el historial de forma clara con rama, autor y fecha

---

### diff

Muestra las diferencias del working tree o del área staged.

**Flujo:**

1. Sin argumentos: `git diff` — cambios no staged
2. Con argumento `staged`: `git diff --staged` — cambios en staging area
3. Con nombre de archivo: `git diff <archivo>`
4. Resumir los cambios detectados en lenguaje natural

---

### stash

Guarda cambios temporales sin commitear.

**Flujo para `stash`:**

1. Ejecutar `git stash push -m "<descripcion>"` — pedir descripción si no se proporcionó
2. Confirmar qué se guardó con `git stash list`

**Flujo para `stash pop`:**

1. Mostrar `git stash list` — listar stashes disponibles
2. Si hay más de uno, preguntar cuál restaurar
3. Ejecutar `git stash pop` o `git stash apply stash@{n}`
4. Informar si hay conflictos

---

### branch

Lista las ramas del repositorio.

**Flujo:**

1. Ejecutar `git branch -a` — locales y remotas
2. Resaltar la rama actual
3. Clasificar por tipo GitFlow (feature/, fix/, release/, hotfix/)

---

### checkout

Cambia a una rama existente.

**Flujo:**

1. Verificar si hay cambios sin commitear — sugerir stash si los hay
2. Ejecutar `git checkout <rama>`
3. Confirmar la rama activa y su tipo GitFlow

**Regla:** no usar para crear ramas nuevas — usar `/git start` en su lugar.

---

### merge

Fusiona una rama en la rama actual.

**Flujo:**

1. Verificar que la rama actual no es `main` ni `develop` directamente (advertir si es así)
2. Mostrar los commits que se incorporarán: `git log HEAD..<rama> --oneline`
3. Pedir confirmación antes de ejecutar
4. Ejecutar `git merge <rama> --no-ff` (sin fast-forward para preservar historial)
5. Informar resultado y conflictos si los hay

**Regla:** nunca hacer merge directamente sobre `main` o `develop` — siempre desde una rama de trabajo con `/git finish`.

---

### tag

Crea un tag semántico en el commit actual.

**Flujo:**

1. Verificar que la rama actual es `main` (los tags se crean sobre producción)
2. Mostrar el último tag existente: `git tag --sort=-version:refname | head -5`
3. Crear el tag anotado: `git tag -a <version> -m "Release <version>"`
4. Preguntar si desea hacer push del tag: `git push origin <version>`

**Formato de versión:** Semver — `v1.0.0`, `v1.1.0`, `v1.0.1`

---

### undo

Revierte el último commit manteniendo los cambios en el working tree.

**Flujo:**

1. Mostrar el último commit: `git log --oneline -1`
2. **Verificar que el commit no fue pusheado**: comparar con el upstream
   (`git log @{u}..HEAD --oneline`, o `git status -sb`). Si el último commit ya
   está en `origin`, **detenerse y avisar** — deshacerlo reescribiría historial
   compartido; ofrecer `git revert` en su lugar.
3. Pedir confirmación explícita
4. Ejecutar `git reset --soft HEAD~1`
5. Confirmar que los cambios siguen disponibles con `git status`

**Regla:** solo funciona en commits locales que no han sido pusheados. Si ya se
pusheó, usar `git revert` (que crea un commit inverso) en vez de `undo`.

---

### sync

Sincroniza las ramas `develop` y `main` con origin.

**Flujo (sin checkouts — compatible con worktrees):**

1. Verificar que no hay cambios sin commitear
2. Traer todo y limpiar referencias muertas:
   ```bash
   git fetch --all --prune
   git worktree prune
   ```
3. Actualizar `develop` y `main` **sin cambiar de rama**:
   - La rama checked out en el worktree de control se actualiza ahí con
     `git -C <control> pull --ff-only origin <rama>`.
   - La otra se adelanta por ref, sin tocar ningún working tree:
     ```bash
     git fetch origin main:main    # falla si main está ocupada por un worktree
     ```
     Si falla porque está ocupada, actualizarla desde el worktree que la tiene.
4. Confirmar el estado de ambas ramas y listar los worktrees activos

> **Nunca** `git checkout <rama>` para sincronizar: si esa rama está ocupada por
> otro worktree, git la rechaza y el flujo queda a medias.

---

## Reglas generales de seguridad

- **Siempre** mostrar la acción propuesta y pedir confirmación antes de ejecutarla
- **Nunca** hacer `git push` sin que el usuario lo solicite explícitamente
- **Nunca** operar directamente sobre `main` o `develop` — siempre a través de una rama de trabajo con `/git finish`
- **Nunca** usar `git reset --hard`, `git push --force` o `git clean -f` sin confirmación explícita
- Si se detecta que la rama actual es `main` o `develop`, advertir y detener la operación
