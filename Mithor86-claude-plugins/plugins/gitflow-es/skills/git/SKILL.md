---
name: git
description: Gestiona el ciclo de vida completo de ramas y commits siguiendo el modelo GitFlow del proyecto. Úsalo siempre que el usuario mencione ramas, PRs, merges, releases, hotfixes, staging, push, pull, stash, tags, o cualquier operación de git — aunque no diga "gitflow" explícitamente. Cubre los subcomandos start, finish, release, hotfix, status y operaciones básicas (add, push, pull, log, diff, stash, branch, checkout, merge, tag, undo, sync). Para generar commits, delega al skill `commit` de este mismo plugin.
---

# Git Flow

Gestiona el ciclo de vida completo de ramas y commits siguiendo el modelo GitFlow del proyecto.

> **Fuente única de verdad:** `../../rules/git-flow.md` (dentro de este plugin) define ramas principales, tipos de rama, nomenclatura, convención de commits, scopes y reglas del flujo obligatorio.
> Este skill solo describe los comandos operativos. Consultar la rule cuando haya duda de política.

## Uso

### GitFlow

```
/git start <tipo> <descripcion>   → Inicia una rama GitFlow desde la base correcta
/git finish                        → Cierra la rama actual y genera el PR al destino correcto
/git release <version>             → Inicia un ciclo de release
/git hotfix <descripcion>          → Inicia un hotfix urgente desde main
/git status                        → Muestra el estado GitFlow actual
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

## Subcomando: start

Crea una rama desde la base correcta según el tipo.

> **Obligatorio usar comandos git-flow** para los tipos que tienen soporte nativo.

### Flujo

1. Verificar que no hay cambios sin commitear (`git status`)
2. Según el tipo, usar el comando git-flow correspondiente o git manual
3. Confirmar la rama creada y la base usada

### Tipos de ramas y comandos

| Tipo       | Comando git-flow (obligatorio si aplica)             | Fallback manual (solo si no hay git-flow) |
| ---------- | ---------------------------------------------------- | ----------------------------------------- |
| `feature`  | `git flow feature start <nombre>`                    | —                                         |
| `hotfix`   | `git flow hotfix start <nombre>`                     | —                                         |
| `release`  | `git flow release start <version>`                   | —                                         |
| `fix`      | _(no soportado)_ `git checkout -b fix/<nombre>`      | desde `develop`                           |
| `refactor` | _(no soportado)_ `git checkout -b refactor/<nombre>` | desde `develop`                           |
| `chore`    | _(no soportado)_ `git checkout -b chore/<nombre>`    | desde `develop`                           |

### Reglas

- Siempre en **kebab-case**, sin espacios ni caracteres especiales
- Máximo 50 caracteres en el nombre
- **Nunca** usar `git checkout -b` para tipos con soporte git-flow nativo (`feature`, `hotfix`, `release`)

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
6. Ejecutar el comando git-flow correspondiente (o git manual si no aplica)

### Comandos por tipo de rama

| Tipo de rama | Comando (obligatorio)                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------ |
| `feature/*`  | `git flow feature finish <nombre>`                                                               |
| `hotfix/*`   | `git flow hotfix finish <nombre>`                                                                |
| `release/*`  | `git flow release finish <version>`                                                              |
| `fix/*`      | `git checkout develop && git merge --no-ff fix/<nombre> && git branch -d fix/<nombre>`           |
| `refactor/*` | `git checkout develop && git merge --no-ff refactor/<nombre> && git branch -d refactor/<nombre>` |
| `chore/*`    | `git checkout develop && git merge --no-ff chore/<nombre> && git branch -d chore/<nombre>`       |

> `git flow feature/hotfix/release finish` ejecuta automáticamente el merge, elimina la rama y crea el tag si aplica.

---

## Subcomando: commit

> Delega al skill `commit` de este mismo plugin — fuente única de verdad para commits.
> Invocar `/commit` directamente en lugar de este subcomando.

---

## Subcomando: release

Inicia el proceso formal de release siguiendo GitFlow.

### Flujo

1. Verificar que `develop` está actualizado (`git pull origin develop`)
2. Crear rama `release/<version>` desde `develop`
3. Mostrar los commits incluidos desde el último tag (`git log <ultimo-tag>..develop --oneline`)
4. Recordar las tareas de release:
   - Actualizar versión en `app.json`
   - Actualizar `CHANGELOG` si existe
   - Hacer commit de los cambios de versión: `chore(release): bump version to <version>`
5. Al terminar, usar `/git finish` para fusionar en `main` y `develop`

---

## Subcomando: hotfix

Inicia un hotfix urgente desde `main`.

### Flujo

1. Verificar rama actual y cambios pendientes
2. Cambiar a `main` y actualizar (`git pull origin main`)
3. Crear rama `hotfix/<descripcion>` desde `main`
4. Informar que al terminar se debe hacer PR a `main` **y** a `develop`

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
2. Pedir confirmación explícita
3. Ejecutar `git reset --soft HEAD~1`
4. Confirmar que los cambios siguen disponibles con `git status`

**Regla:** solo funciona en commits locales que no han sido pusheados.

---

### sync

Sincroniza las ramas `develop` y `main` con origin.

**Flujo:**

1. Verificar que no hay cambios sin commitear
2. Ejecutar:
   ```
   git checkout develop && git pull origin develop
   git checkout main && git pull origin main
   ```
3. Volver a la rama original donde estaba el usuario
4. Confirmar que ambas ramas están actualizadas

---

## Reglas generales de seguridad

- **Siempre** mostrar la acción propuesta y pedir confirmación antes de ejecutarla
- **Nunca** hacer `git push` sin que el usuario lo solicite explícitamente
- **Nunca** operar directamente sobre `main` o `develop` — siempre a través de una rama de trabajo con `/git finish`
- **Nunca** usar `git reset --hard`, `git push --force` o `git clean -f` sin confirmación explícita
- Si se detecta que la rama actual es `main` o `develop`, advertir y detener la operación
