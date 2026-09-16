# Roadmap — gitflow-es

Lista de features candidatas para versiones futuras del plugin. Cada propuesta incluye objetivo, diseño técnico, casos borde y ejemplos. Este documento es un catálogo para priorizar, **no un compromiso de implementación** — las features se seleccionan según demanda real del equipo.

> Última actualización: 2026-09-15 (tras la v0.10.1).

## ✅ Implementado

| Feature | Versión | Notas |
|---------|---------|-------|
| **#1 commit-message-writer** (subagente) | v0.6.0 | El skill `commit` delega la redacción del mensaje. |
| **#2 branch-name-suggester** (skill) | v0.6.0 | Integrado en `/git start`; propone nombres en el idioma configurado. |
| **Soporte de idioma ES/EN** (no estaba en el roadmap) | v0.6.0 | `GITFLOW_LANG` / `git config gitflow-es.language`; hooks traducidos en runtime + captura guiada del idioma. |
| **#4 release-notes-writer** (subagente) | v0.7.0 | Integrado en el paso 4 de `/git release`; CHANGELOG agrupado por tipo Conventional. |
| **Worktrees obligatorios desde `develop`** (no estaba en el roadmap) | v0.10.0 | Una rama, un worktree; el repo principal queda como *worktree de control*. Incluye el bloqueo del `git flow finish` dentro del worktree de la rama —donde git-flow reporta éxito sin mergear— y la verificación de postcondiciones del cierre. |
| **Skill `worktrees`: trabajo en paralelo** (no estaba en el roadmap) | v0.10.0 | Reparte tareas independientes en un worktree por rama desde `develop`, con base actualizada una sola vez y cierres secuenciales. |
| **Skill `tiempos`: registro por rama** (cubre parte de #12) | v0.10.0 | Trabajo, trabajo fuera de sesión, pruebas, espera e inactividad; tiempos muertos validados contra `mtime` y commits; log local en `.git/gitflow-es/tiempos/`. |
| **Precisión del registro de tiempos** (no estaba en el roadmap) | v0.10.1 | Sexto rubro **Espera de aprobación**: el rato que tarda la persona en aprobar un permiso sale de *Trabajo*, con clasificación defensiva del aviso (ante la duda no se descuenta). Y la evidencia de commits se congela en el log al cerrar la rama, porque `git log <base>..<rama>` queda vacío apenas la rama se mergea — justo cuando se lee el reporte. |
| **`/git init`: asistente de configuración** (no estaba en el roadmap) | v0.10.0 | git-flow, idioma, raíz de worktrees, registro de tiempos y scopes en un paso; el hook de sesión lo ofrece cuando falta algo. |

Las secciones #1, #2 y #4 más abajo se conservan como referencia de diseño. Quedan
**8 candidatas pendientes** (#3, #5–#11) más **#12 parcialmente cubierta** por el
registro de tiempos, y **3 candidatas nuevas** que salieron de construir la v0.10.0
(#13–#15).

## Índice

1. [commit-message-writer (subagente)](#1-commit-message-writer-subagente) — ✅ v0.6.0
2. [branch-name-suggester (skill)](#2-branch-name-suggester-skill) — ✅ v0.6.0
3. [Validación de Conventional Commits (hook)](#3-validación-de-conventional-commits-hook)
4. [release-notes-writer (subagente)](#4-release-notes-writer-subagente) — ✅ v0.7.0
5. [conflict-resolver-guide (skill)](#5-conflict-resolver-guide-skill)
6. [Recordatorio de sync periódico (hook)](#6-recordatorio-de-sync-periódico-hook)
7. [history-explorer (skill)](#7-history-explorer-skill)
8. [pr-description-writer (subagente)](#8-pr-description-writer-subagente)
9. [Protección contra secretos en diff (hook)](#9-protección-contra-secretos-en-diff-hook)
10. [stash-manager (skill)](#10-stash-manager-skill)
11. [blame-explainer (subagente)](#11-blame-explainer-subagente)
12. [Métricas de flujo (hook + skill)](#12-métricas-de-flujo-hook--skill) — 🟡 parcial en v0.10.0
13. [Métricas agregadas sobre el registro de tiempos](#13-métricas-agregadas-sobre-el-registro-de-tiempos) — _nueva_
14. [worktree-doctor (skill)](#14-worktree-doctor-skill) — _nueva_
15. [Adopción asistida de la política de worktrees](#15-adopción-asistida-de-la-política-de-worktrees) — _nueva_

### Matriz de priorización rápida

| # | Feature | Tipo | Esfuerzo | Valor | Dependencias |
|---|---------|------|----------|-------|--------------|
| 1 | commit-message-writer ✅ | Subagente | M | Alto | Ninguna — _hecho en v0.6.0_ |
| 2 | branch-name-suggester ✅ | Skill | S | Alto | Ninguna — _hecho en v0.6.0_ |
| 3 | Validación Conv. Commits | Hook | S | Medio | Ninguna |
| 4 | release-notes-writer ✅ | Subagente | M | Alto | Ninguna — _hecho en v0.7.0_ |
| 5 | conflict-resolver-guide | Skill | M | Medio | Ninguna |
| 6 | Recordatorio de sync | Hook | S | Bajo | Debe recorrer todos los worktrees (v0.10.0) |
| 7 | history-explorer | Skill | S | Medio | Ninguna |
| 8 | pr-description-writer | Subagente | M | Alto | Ninguna |
| 9 | Protección secretos en diff | Hook | L | Alto | #3 (opcional) |
| 10 | stash-manager | Skill | S | Bajo | Ninguna |
| 11 | blame-explainer | Subagente | M | Medio | Ninguna |
| 12 | Métricas de flujo 🟡 | Hook + Skill | L | Bajo | _Parcial en v0.10.0_ — el resto pasa a #13 |
| 13 | Métricas agregadas de tiempos | Skill | S | Medio | Registro de tiempos (v0.10.0) |
| 14 | worktree-doctor | Skill | S | Medio | Worktrees (v0.10.0) |
| 15 | Adopción asistida de worktrees | Skill | M | Medio | Worktrees (v0.10.0) |

Esfuerzo: S = 1–2h, M = medio día, L = 1+ día.

---

## 1. commit-message-writer (subagente)

### Objetivo
Delegar a un subagente la generación del mensaje de commit a partir del diff staged, en lugar de que el skill `commit` lo haga inline. El subagente tiene contexto aislado, lee `git diff --staged` real y produce un mensaje siguiendo Conventional Commits.

### Por qué vale la pena
El skill `commit` actual pide a Claude que genere el mensaje dentro de la conversación principal, donde arrastra contexto de todo lo hablado. Un subagente dedicado lee **solo el diff** y eso reduce alucinaciones tipo "describir cambios que se hablaron pero no se implementaron".

### Diseño técnico

Archivo nuevo: `agents/commit-message-writer.md`

Frontmatter:
```yaml
---
name: commit-message-writer
description: Genera mensajes de commit siguiendo Conventional Commits del proyecto leyendo el diff staged real. Úsalo cuando el usuario pide hacer commit y el skill `commit` necesita el mensaje.
tools: Bash
---
```

Flujo del subagente:
1. `git diff --staged --stat` — vista rápida de archivos tocados.
2. `git diff --staged` — diff completo (limitar a 500 líneas; si excede, pedir diff por archivo relevante).
3. Analizar tipo dominante (`feat`, `fix`, `refactor`, etc.) inferido del diff.
4. Detectar scope dominante según rutas (`src/auth/*` → scope `auth`, `packages/api/*` → `api`, etc.).
5. Redactar asunto en imperativo, español, sin mayúscula inicial, ≤72 chars.
6. Si el diff toca ≥3 áreas distintas, avisar: "este commit parece mezclar cambios no relacionados, considera dividirlo."
7. Devolver solo el mensaje propuesto (1 línea de asunto + cuerpo opcional si el diff es complejo).

El skill `commit` se actualiza para delegar al subagente en su paso 5:
> "5. Delegar al subagente `commit-message-writer` para generar el mensaje."

### Casos borde
- **Sin staged**: el subagente detecta (`git diff --staged` vacío) y devuelve "No hay cambios staged". El skill `commit` lo intercepta y pregunta al usuario qué stagear.
- **Diff masivo (>500 líneas)**: el subagente hace un `--stat` y genera mensaje basado en archivos+stats; advierte que no leyó el diff completo.
- **Tipos mezclados**: el subagente propone el mensaje con el tipo dominante pero agrega nota "detecté también cambios de tipo X en Y archivo".
- **Scope fuera de la lista del proyecto**: el subagente usa el scope más cercano de la lista definida en `rules/git-flow.md` y deja nota.

### Ejemplo

```
[diff staged: src/auth/login.ts agrega validación de email, tests/auth/login.test.ts 3 nuevos tests]

Mensaje propuesto:
feat(auth): agregar validación de email en login

Incluye 3 nuevos tests que cubren los casos: email vacío,
formato inválido y email ya registrado.
```

---

## 2. branch-name-suggester (skill)

### Objetivo
Dado un texto libre del usuario ("quiero trabajar en el bug del OTP expirado"), proponer 2-3 nombres de rama en kebab-case con el prefijo GitFlow correcto, para que confirme antes de crear.

### Por qué vale la pena
Hoy Claude genera nombres on-the-fly y a veces quedan largos, mezclan idiomas, o no siguen kebab-case estricto. Un skill dedicado con criterios claros mejora consistencia.

### Diseño técnico

Archivo nuevo: `skills/branch-name-suggester/SKILL.md`

Frontmatter:
```yaml
---
name: branch-name-suggester
description: Propone nombres de rama en kebab-case con el prefijo GitFlow correcto a partir de una descripción libre. Úsalo siempre que se vaya a crear una rama nueva (feature, fix, hotfix, chore, refactor) y el nombre aún no esté definido.
---
```

Reglas que el skill aplica:
- Prefijo inferido del tipo (`feature/`, `fix/`, `hotfix/`, `chore/`, `refactor/`).
- Longitud total ≤50 chars (incluyendo prefijo).
- kebab-case estricto: solo `[a-z0-9-]`, sin tildes, ñ, ni espacios.
- Sin artículos (`el`, `la`, `un`) salvo que clarifiquen.
- Imperativo corto, no oración completa.
- Propone 2-3 alternativas (verbo-primero, sustantivo-primero, contexto+tema).

### Casos borde
- **Tipo no especificado**: el skill pregunta antes de proponer.
- **Descripción demasiado genérica** ("arreglar bug"): el skill pide detalle antes de proponer.
- **Descripción con nombres propios o PRs de JIRA** ("AUTH-123: arreglar login"): el skill incluye el ticket como sufijo opcional (`fix/auth-123-login-timeout`).

### Ejemplo

```
Usuario: "quiero arrancar una feature para permitir login con google"

Skill propone:
1. feature/login-con-google         ← recomendado (corto, descriptivo)
2. feature/google-auth              ← más corto, estilo técnico
3. feature/autenticacion-google     ← más formal

¿Cuál usamos?
```

---

## 3. Validación de Conventional Commits (hook)

### Objetivo
Validar con `PreToolUse` que el mensaje de `git commit -m "..."` cumpla Conventional Commits antes de ejecutarse. Bloquear si no cumple y explicar qué falta.

### Por qué vale la pena
Hoy el skill `commit` **sugiere** el formato pero no garantiza que se respete. Un hook mecánico cierra ese gap, especialmente para commits manuales que el usuario escriba.

### Diseño técnico

Extender `safety-check.py` con un check nuevo `check_commit_message_format`:

Regex estricto:
```
^(feat|fix|refactor|chore|docs|test|style|perf|ci|build)(\([a-z0-9-]+\))?!?: [a-zñáéíóú0-9].{0,70}$
```

Extrae el mensaje de `-m "..."` o de `--message=`. Si:
- Tipo no está en la lista blanca → bloquear, sugerir lista.
- Scope tiene mayúsculas o caracteres raros → bloquear.
- Descripción empieza con mayúscula → bloquear (regla del equipo).
- Descripción termina en punto → bloquear.
- Asunto >72 chars → bloquear.
- Falta el espacio después de `:` → bloquear.

### Casos borde
- **Merge commits** (`Merge branch 'X'`): no se validan, git los genera automáticamente.
- **`--amend` sin `-m`**: no hay mensaje nuevo, no validar.
- **Commits con `-F <archivo>`**: leer el archivo y validar la primera línea.
- **BREAKING CHANGE**: el `!` después del scope es válido (`feat(auth)!: ...`).
- **Opt-out por repo**: permitir `.gitflow-es-no-validate` en el root como escape hatch.

### Ejemplo

```
Usuario pide: git commit -m "Arreglé el bug del login."

Hook bloquea:
[gitflow-es safety] Mensaje no cumple Conventional Commits:
  - Empieza con mayúscula ("Arreglé" → "arreglé")
  - Termina en punto (quitar el ".")
  - Falta tipo y scope

Propuesta sugerida:
  fix(auth): arreglar bug de login
```

---

## 4. release-notes-writer (subagente)

### Objetivo
Al ejecutar `/git release <version>`, un subagente lee el rango de commits desde el último tag hasta `develop` y genera las release notes (agrupadas por tipo Conventional: feat, fix, refactor, etc.), listas para copiar al `CHANGELOG.md` o al Release de GitHub.

### Por qué vale la pena
Hoy el release es manual: Claude propone "actualiza el CHANGELOG" pero el usuario redacta. Con un subagente que lee los commits reales, el changelog se genera automáticamente y respeta lo que realmente se mergeó.

### Diseño técnico

Archivo nuevo: `agents/release-notes-writer.md`

Frontmatter:
```yaml
---
name: release-notes-writer
description: Genera release notes agrupadas por tipo Conventional Commit al preparar un release. Úsalo en el paso de "actualizar CHANGELOG" de `/git release <version>`.
tools: Bash, Write
---
```

Flujo:
1. `git describe --tags --abbrev=0` — último tag.
2. `git log <ultimo-tag>..develop --format='%h|%s|%b|---END---'` — commits desde ese tag.
3. Parsear cada commit por el prefijo Conventional (`feat`, `fix`, etc.).
4. Agrupar:
   - **Added** → `feat`
   - **Fixed** → `fix`
   - **Changed** → `refactor`, `perf`
   - **Maintenance** → `chore`, `ci`, `build`, `style`
   - **Docs** → `docs`
5. Detectar `BREAKING CHANGE:` en los cuerpos y marcar con ⚠️.
6. Escribir bloque en formato Keep a Changelog al inicio del `CHANGELOG.md`.
7. Devolver el bloque también en texto plano para que Claude lo pegue en el Release de GitHub si el usuario lo pide.

### Casos borde
- **Sin tags previos**: usa el commit inicial como base (`git rev-list --max-parents=0 HEAD`).
- **Commits sin prefijo Conventional**: los agrupa en una sección "Other" al final, en lugar de descartarlos.
- **Versión ya existe**: pregunta si sobreescribir o incrementar (`v1.2.0` → `v1.2.1`).
- **Scope "revert"**: sección dedicada "Reverted".

### Ejemplo

```markdown
## [0.6.0] — 2026-05-15

### Added
- **feat(auth)**: agregar login con Google (a1b2c3d)
- **feat(dashboard)**: widget de KPIs en tiempo real (e4f5g6h)

### Fixed
- **fix(api)**: corregir timeout en endpoint de facturación (h7i8j9k)

### Changed
- **refactor(hooks)**: extraer useFetch a un módulo aparte (l0m1n2o)

### ⚠️ Breaking changes
- **feat(auth)!**: renombrar `user_id` → `account_id` en todos los endpoints.
  Migrar cualquier cliente que use el campo anterior.
```

---

## 5. conflict-resolver-guide (skill)

### Objetivo
Cuando un `git merge`, `git rebase` o `git flow finish` falla por conflictos, un skill guía al usuario paso a paso: listar los archivos, abrir cada uno, explicar los marcadores `<<<<<<<`, ayudar a decidir, marcar como resuelto, y continuar.

### Por qué vale la pena
Los conflictos son el momento donde más usuarios se atascan o corrompen su working tree. Un skill dedicado con flujo guiado reduce errores.

### Diseño técnico

Archivo nuevo: `skills/conflict-resolver-guide/SKILL.md`

Frontmatter:
```yaml
---
name: conflict-resolver-guide
description: Guía paso a paso para resolver conflictos de merge/rebase en git. Úsalo siempre que un comando git falle con mensaje "CONFLICT" o "Automatic merge failed", o cuando el usuario mencione conflictos, merge conflicts, o tener un rebase/merge en curso.
---
```

El skill detecta el estado con:
- `git status --porcelain` — lista archivos con `UU`, `AA`, `DU`, etc.
- `git ls-files -u` — versiones en conflicto.
- `cat .git/MERGE_HEAD` / `.git/REBASE_HEAD` — saber si es merge o rebase.

Flujo guiado:
1. Mostrar lista de archivos en conflicto con su estado.
2. Para cada archivo, proponer: "abrir y decidir manualmente", "aceptar versión actual (`--ours`)", o "aceptar versión entrante (`--theirs`)".
3. Explicar los marcadores `<<<<<<< HEAD / ======= / >>>>>>> branch` si el usuario no los conoce.
4. Después de cada resolución, ejecutar `git add <archivo>`.
5. Al resolver todos, proponer `git merge --continue` o `git rebase --continue`.

Incluye un **escape hatch**: si el usuario prefiere abortar, ofrecer `git merge --abort` / `git rebase --abort` con advertencia clara.

### Casos borde
- **Conflictos en archivos binarios**: explicar que no se pueden mezclar automáticamente, hay que elegir uno u otro.
- **Conflictos de renombrado/eliminación** (`DU`, `UD`): explicar las dos versiones y ofrecer opciones.
- **Rebase interactivo con conflictos múltiples**: el skill guía por cada step del rebase, no solo el primero.

### Ejemplo

```
Usuario: "el merge falló"

Skill responde:
Veo 2 archivos en conflicto:
  - src/auth.ts (ambos modificaron las mismas líneas)
  - package.json (ambos agregaron dependencias distintas)

¿Empezamos por auth.ts? Puedo:
  a) Abrirlo y mostrarte los conflictos para que decidas
  b) Aceptar tu versión (`--ours`)
  c) Aceptar la versión de develop (`--theirs`)

(Recomendación para package.json: opción (a) — los lockfiles
de dependencias generalmente necesitan decisión manual.)
```

---

## 6. Recordatorio de sync periódico (hook)

> **Nota v0.10.0:** con la política de worktrees, el recordatorio ya no mira una
> sola copia de trabajo: debe recorrer `git worktree list` y avisar por cada rama
> atrasada respecto de `develop`. Además, `develop` suele estar checked out en el
> worktree de control, así que la actualización se hace ahí y no donde se avisa.

### Objetivo
Si la rama actual lleva >3 días sin hacer pull de su base (`develop` o `main`), el hook `SessionStart` agrega una advertencia proactiva sugiriendo correr `/git sync` para evitar conflictos grandes al finish.

### Por qué vale la pena
Ramas que se quedan "atrasadas" semanas generan conflictos masivos al cerrar. Un recordatorio temprano obliga a mergear develop frecuentemente.

### Diseño técnico

Extender `session-context.py`:
- Detectar rama de trabajo (feature/fix/etc.).
- Calcular edad del último merge de la base: `git log --format=%ct -1 <base> -- .` vs `git log --format=%ct -1 HEAD -- .`.
- Si diferencia >3 días, agregar sección:

```markdown
### ⚠️ Tu rama lleva 12 días sin sincronizar con `develop`
Considera correr `/git sync` antes de seguir trabajando para evitar
conflictos grandes al cerrar.
```

### Casos borde
- **Sin remoto configurado**: no emitir aviso (no hay base remota contra la cual sincronizar).
- **Rama recién creada**: usar fecha de creación de la rama, no del último merge.
- **Threshold configurable**: leer de `.gitflow-es.json` opcional en el root (default 3 días).

### Ejemplo
El aviso aparece en el bloque de `SessionStart` junto con el estado GitFlow, cuando aplique.

---

## 7. history-explorer (skill)

### Objetivo
Cuando el usuario pregunta algo tipo "¿quién cambió esta función?", "¿cuándo se introdujo este bug?", "¿qué commits tocaron este archivo?", el skill guía la exploración del historial con `git log`, `git blame`, `git bisect`, y formatea la salida.

### Por qué vale la pena
Muchas operaciones de investigación requieren combinar comandos git que Claude conoce pero olvida encadenar bien. Un skill concentra los flujos comunes.

### Diseño técnico

Archivo nuevo: `skills/history-explorer/SKILL.md`

Frontmatter:
```yaml
---
name: history-explorer
description: Explora el historial de git para responder preguntas tipo "quién cambió qué", "cuándo se introdujo un bug", "qué commits tocaron un archivo". Úsalo cuando el usuario pregunte sobre autoría, blame, historial, bisect, o quiera rastrear un cambio.
---
```

Flujos cubiertos:
- **"¿Quién modificó X?"** → `git log --follow -p <archivo>` + `git blame <archivo>`.
- **"¿Cuándo apareció este bug?"** → proponer `git bisect` guiado: marcar bueno/malo y seguir.
- **"¿Qué commits tocaron este módulo?"** → `git log --oneline --follow <path>`.
- **"¿Qué cambió entre estas dos versiones?"** → `git log <tag1>..<tag2> --oneline` + `git diff --stat`.

### Casos borde
- **Archivo renombrado**: usar `--follow` para rastrear a través de renombres.
- **Merge commits confusos**: ofrecer `--first-parent` para ver solo la rama principal.
- **Archivos grandes**: limitar a últimas 20 entradas por defecto, preguntar si ampliar.

### Ejemplo

```
Usuario: "quién escribió la validación de email?"

Skill:
[git blame -L :validateEmail src/auth.ts]

La función `validateEmail` fue introducida por:
  - a1b2c3d — María López, 2026-03-12
    "feat(auth): agregar validación de email en registro"

Última modificación:
  - e4f5g6h — Juan Pérez, 2026-04-05
    "fix(auth): permitir subdominios en validación de email"
```

---

## 8. pr-description-writer (subagente)

### Objetivo
Al ejecutar `/git finish` o cuando el usuario pida generar la descripción de un Pull Request, un subagente produce el texto del PR leyendo los commits y el doc de feature generado por `feature-doc-writer`, listo para pegar en GitHub/GitLab.

### Por qué vale la pena
Hoy `feature-doc-writer` genera un doc interno del equipo, pero el PR de GitHub queda con descripción vacía o genérica. Un subagente dedicado genera la descripción pública con el formato que el equipo prefiera.

### Diseño técnico

Archivo nuevo: `agents/pr-description-writer.md`

Frontmatter:
```yaml
---
name: pr-description-writer
description: Genera la descripción del Pull Request a partir de los commits de la rama y el doc de feature. Úsalo al cerrar una rama o cuando el usuario pida preparar el PR.
tools: Bash, Read
---
```

Flujo:
1. Detectar rama actual y base (`develop` o `main`).
2. Leer commits: `git log <base>..HEAD --format='%h %s'`.
3. Si existe `docs/<feature>/<fecha>-<feature>.md` (generado por `feature-doc-writer`), usarlo como fuente principal.
4. Producir plantilla:

```markdown
## ¿Qué hace este PR?
<resumen 2-3 líneas inferido de los commits>

## Cambios principales
- <lista bullet>

## Checklist
- [ ] Tests pasan localmente
- [ ] Doc de feature agregado en `docs/`
- [ ] No introduce breaking changes (o si los introduce, están documentados)

## Captura / evidencia
_A completar por el autor._

## Referencias
Closes #<ticket si se detecta en el nombre de la rama>
```

### Casos borde
- **Rama sin commits propios**: avisar que no hay contenido.
- **Nombre de rama con ticket**: detectar patrones tipo `feature/AUTH-123-...` y autorellenar `Closes #`.
- **Detectar si el repo tiene template** (`.github/pull_request_template.md`): si existe, usar ese como base en lugar del template por defecto.

### Ejemplo

```markdown
## ¿Qué hace este PR?
Agrega login con Google al flujo de autenticación, incluyendo
validación de email y 3 tests unitarios.

## Cambios principales
- Nuevo endpoint `POST /auth/google` en `src/auth/google.ts`
- Refactor del `AuthProvider` para aceptar múltiples proveedores
- Tests en `tests/auth/google.test.ts`

## Checklist
- [x] Tests pasan localmente
- [x] Doc en `docs/login-con-google/2026-05-10-login-con-google.md`
- [x] No introduce breaking changes

## Referencias
Closes #AUTH-123
```

---

## 9. Protección contra secretos en diff (hook)

### Objetivo
Extender el `PreToolUse` del safety hook para escanear el diff staged antes de un `git commit` y bloquear si detecta **valores** que parezcan secretos (API keys, tokens, passwords hardcoded), incluso si el nombre del archivo no es sospechoso.

### Por qué vale la pena
Hoy el hook bloquea `git add .env` por nombre de archivo, pero no detecta si alguien pegó una API key en medio de un archivo `.ts` legítimo. Escaneo de patrones cierra ese gap.

### Diseño técnico

Agregar función `check_staged_secrets` al `safety-check.py`. Se dispara solo en `git commit`:

1. Ejecutar `git diff --staged --unified=0 | grep '^+'` (solo líneas agregadas).
2. Matchear contra patrones conocidos:
   - AWS: `AKIA[0-9A-Z]{16}`
   - GCP: `AIza[0-9A-Za-z\-_]{35}`
   - GitHub token: `ghp_[0-9A-Za-z]{36}` / `github_pat_[0-9A-Za-z_]{82}`
   - OpenAI: `sk-[a-zA-Z0-9]{48}`
   - JWT: `eyJ[A-Za-z0-9_=]+\.[A-Za-z0-9_=]+\.?[A-Za-z0-9_.+/=]*`
   - Private key headers: `-----BEGIN (RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----`
   - Slack: `xox[baprs]-[0-9a-zA-Z]{10,48}`
   - Stripe: `sk_live_[0-9a-zA-Z]{24,}`
3. También detectar assignments sospechosos:
   - `(password|api_key|secret|token)\s*=\s*["'][^"']{16,}["']` (no archivo de test)
4. Si match, bloquear con reporte indicando archivo + línea.

### Casos borde
- **Falsos positivos en tests**: permitir si archivo es `*.test.*`, `*.spec.*`, o está en `tests/` / `fixtures/` y el valor claramente es dummy (`sk_test_...`, `AKIAIOSFODNN7EXAMPLE`).
- **Archivos binarios**: saltarlos (`git diff` los omite de todos modos).
- **Performance**: limitar el escaneo a diffs <5MB; si es mayor, emitir warning en lugar de bloqueo.
- **Escape hatch**: permitir marcar un commit con el trailer `Secret-OK: <razón>` en el cuerpo del mensaje (raro pero a veces legítimo, ej. config ejemplo).

### Ejemplo

```
Usuario: git commit -m "feat(config): add production API key"

Hook detecta:
[gitflow-es safety] Secreto detectado en el diff staged:
  archivo: src/config/production.ts, línea 12
  patrón:  AWS Access Key ID (AKIAIOSFODNN7JKLMNOP)

Acciones sugeridas:
  1. Retirar el valor del archivo: mover a variable de entorno.
  2. Rotar la credencial en AWS (ya está en el working tree, podría filtrarse).
  3. Re-stagear sin el secreto.
```

---

## 10. stash-manager (skill)

### Objetivo
Skill que amplía el `/git stash` actual con operaciones comunes: ver contenido de un stash antes de aplicarlo, nombrar stashes descriptivamente, limpiar stashes viejos, aplicar parcialmente.

### Por qué vale la pena
`git stash` es una de las operaciones más confusas de git (múltiples stashes, `pop` vs `apply`, conflictos al aplicar). Un skill con flujos dedicados reduce errores.

### Diseño técnico

Archivo nuevo: `skills/stash-manager/SKILL.md`

Frontmatter:
```yaml
---
name: stash-manager
description: Operaciones avanzadas con git stash — listar con descripción, inspeccionar sin aplicar, limpiar viejos, aplicar parcialmente, rescatar stashes perdidos. Úsalo siempre que el usuario mencione stash, stashes, guardar cambios temporales, o tenga problemas aplicando un stash.
---
```

Operaciones:
- **Crear con descripción obligatoria**: `git stash push -m "<descripción>"` (no permitir anónimos).
- **Ver contenido**: `git stash show -p stash@{N}` sin aplicar.
- **Aplicar parcial**: guiar `git checkout -p stash@{N}` para elegir hunks.
- **Limpiar viejos**: listar con fecha, sugerir los >30 días como candidatos a `git stash drop`.
- **Recuperar perdido**: `git fsck --unreachable | grep commit` + guía para recuperar stashes eliminados.

### Casos borde
- **Stash con conflictos al aplicar**: redirigir al skill `conflict-resolver-guide` (#5).
- **Working tree sucio al aplicar**: advertir y ofrecer stashear lo actual primero.
- **Muchos stashes (>10)**: advertir que suele ser señal de trabajo sin commitear, sugerir consolidar.

### Ejemplo

```
Usuario: "qué tengo guardado en stashes?"

Skill:
Tienes 3 stashes:
  stash@{0} — "WIP: refactor login" — hace 2 días
  stash@{1} — "experimento cache"   — hace 12 días
  stash@{2} — <sin descripción>     — hace 45 días ⚠️

El stash@{2} lleva 45 días y no tiene descripción.
¿Lo revisamos antes de borrarlo? Puedo mostrarte su contenido
sin aplicarlo.
```

---

## 11. blame-explainer (subagente)

### Objetivo
Cuando el usuario selecciona un bloque de código (o nombra un archivo+línea) y pregunta "¿por qué está esto así?", un subagente corre `git blame` + `git log` del commit culpable + lee el mensaje de commit + busca el PR asociado y redacta un resumen de "por qué se escribió este código".

### Por qué vale la pena
Casi nunca basta con `git blame` solo — hay que leer el commit, el PR, a veces el issue. Un subagente dedicado encadena todo eso y devuelve una explicación.

### Diseño técnico

Archivo nuevo: `agents/blame-explainer.md`

Frontmatter:
```yaml
---
name: blame-explainer
description: Explica por qué un bloque de código existe, leyendo `git blame`, el commit culpable, y el PR asociado si está disponible. Úsalo cuando el usuario pregunte "por qué está esto así", "de dónde viene este código", o similar.
tools: Bash, Read
---
```

Flujo:
1. `git blame -L <start>,<end> <archivo>` — commits y autores.
2. Para el commit más reciente del rango:
   - `git show <hash>` — ver el diff completo y el mensaje.
   - `git log --merges --ancestry-path <hash>..HEAD` — encontrar el merge commit (suele tener el PR number).
3. Si el merge commit tiene "Merge pull request #N", reportar ese PR.
4. Síntesis:
   - Autor, fecha, mensaje del commit.
   - Qué cambió exactamente en este bloque (vs. versión anterior).
   - PR asociado si existe.
   - Si hay tickets en el mensaje (AUTH-123), reportarlos.

### Casos borde
- **Código proveniente de múltiples commits**: reportar los 3 principales, no solo el más reciente.
- **Blame atribuye a "refactor masivo"**: seguir hacia atrás con `git log -L` para encontrar la autoría real del cambio funcional.
- **Sin remoto / sin PRs**: omitir la sección del PR, usar solo commits locales.

### Ejemplo

```
Usuario: "por qué src/auth.ts línea 42 tiene este timeout de 15 segundos?"

Subagente responde:
Ese timeout fue introducido por:
  commit a1b2c3d — "fix(auth): aumentar timeout a 15s por timeouts
                    en producción (AUTH-456)"
  autor: María López, 2026-03-14
  PR: #234 ("fix authentication timeout")

El commit anterior (e4f5g6h) tenía el timeout en 5s. Se aumentó
porque el ticket AUTH-456 reportaba timeouts intermitentes en
peak hours. El PR incluye también un retry con backoff, pero
eso está en `src/auth/retry.ts`.
```

---

## 12. Métricas de flujo (hook + skill)

> **🟡 Parcialmente cubierto en v0.10.0.** El registro de tiempos ya implementa la
> parte (a) de este diseño —y con más detalle del previsto—: hooks que escriben un
> JSONL append-only local por rama en `.git/gitflow-es/tiempos/`, con eventos de
> sesión, pruebas y commits, y el skill `tiempos` para consultarlo. Lo que falta es
> la parte (b): **agregar** esos datos por ventana temporal (vida promedio de rama,
> hotfixes por mes, distribución por tipo). Ese resto está en **#13**, que ya no
> necesita instrumentación nueva: solo lee lo que el registro guarda.
>
> Diferencias con lo planteado acá: el registro es **opt-out** (activo por default,
> se apaga con `gitflow-es.timeTracking off`) en vez de opt-in, y sí guarda texto
> —descripción de la rama, primera línea de cada prompt y asunto de cada commit—
> configurable con `gitflow-es.timeNotes`. Todo sigue siendo local y sin subir nada.

### Objetivo
Recolectar de forma **opcional** métricas anónimas del flujo de cada repo (tiempo promedio de vida de una feature, número de hotfixes por mes, commits por rama) y exponerlas vía skill `/git metrics`.

### Por qué vale la pena
Los equipos que usan GitFlow a veces no tienen visibilidad de su propio flujo. Métricas locales ayudan a identificar patrones (ramas que viven demasiado, exceso de hotfixes, etc.).

### Diseño técnico

Dos partes:

**a) Hook `PostToolUse` que registra eventos.**
- Cuando `git flow feature start/finish`, `git flow hotfix start/finish`, `git flow release start/finish` se ejecutan exitosamente, registrar evento en `.git/gitflow-es-metrics.jsonl` (log append-only, local, nunca se sube).
- Formato: `{"ts": 1234567890, "event": "feature.finish", "branch": "feature/login", "days_alive": 4.2}`.

**b) Skill nuevo `metrics`:**
- Lee `.git/gitflow-es-metrics.jsonl`.
- Produce reportes: tiempo promedio de features los últimos N días, cantidad de hotfixes por mes, distribución de tipos (feature vs fix vs chore), etc.

### Casos borde
- **Métricas deshabilitadas por default**: requiere explícitamente `gitflow-es.metrics.enabled=true` en git config del repo para empezar a loguear. Nada opt-out, todo opt-in.
- **Archivo grande**: rotar cada 1000 entradas, comprimir las viejas.
- **Privacidad**: nunca se registra el nombre del autor ni mensajes; solo nombres de rama y timestamps. Agregar nota en el README del plugin.
- **Compartir métricas entre el equipo**: out of scope — el archivo es local por diseño. Si un equipo quiere agregarlas, puede crear un hook custom que suba a su propio backend.

### Ejemplo

```
Usuario: /git metrics últimos 30 días

Skill:
Actividad últimos 30 días:

  Features cerradas:    14
  Vida promedio:        3.8 días
  Vida máxima:          11 días (feature/dashboard-widgets)
  Vida mínima:          4 horas

  Hotfixes:             2
  Tiempo promedio de
    hotfix (start→finish): 2.1 horas

  Distribución tipos:
    feature  ██████████ 60%
    fix      ████       25%
    chore    ██         10%
    refactor █           5%
```

---

## 13. Métricas agregadas sobre el registro de tiempos

### Objetivo
Cerrar lo que falta de #12 leyendo el registro que la v0.10.0 ya escribe: responder "¿cuánto vive una rama en este repo?", "¿cuántos hotfixes tuvimos este mes?", "¿qué proporción del tiempo se va en pruebas?" sin instrumentar nada nuevo.

### Por qué vale la pena
El dato ya está en disco, rama por rama. Lo que no existe es la mirada de conjunto: hoy `/tiempos todas` compara ramas, pero no agrupa por período ni por tipo, que es donde se ven los patrones (ramas que viven demasiado, exceso de hotfixes, pruebas que se comen el ciclo).

### Diseño técnico
- Extender `hooks/time-report.py` con `--desde`/`--hasta` y `--agrupar por-tipo|por-mes`, reutilizando `timelog.aggregate` y `timelog.calendar_time` — no hace falta tocar el tracker.
- Derivar la **vida de la rama** de los eventos `branch_start` / `branch_finish` que ya se registran; para ramas sin `branch_start` (creadas antes de la 0.10.0 o fuera de `/git start`), caer al primer evento del log y marcarlo como estimado.
- Nuevo subcomando `/tiempos resumen [período]` en el skill `tiempos`.

### Casos borde
- **Ramas abiertas**: cuentan aparte, nunca mezcladas con las cerradas — si no, el promedio de vida se infla con las que siguen vivas.
- **Trabajo en paralelo**: el promedio por rama no equivale al reloj del equipo; mostrar siempre el tiempo de calendario al lado.
- **Logs viejos**: ramas cerradas antes de la 0.10.0 no tienen registro; decirlo explícitamente en vez de reportar cero.

---

## 14. worktree-doctor (skill)

### Objetivo
Diagnosticar y arreglar el estado de los worktrees de un repo: carpetas borradas a mano que dejaron el registro colgado, worktrees con cambios sin commitear, ramas de trabajo sin worktree y worktrees de ramas ya cerradas.

### Por qué vale la pena
Salió de construir la v0.10.0: la política de un worktree por rama funciona, pero el árbol se ensucia solo con el uso —una carpeta borrada con `rm -rf`, un lote paralelo a medio cerrar— y los mensajes de git para esos casos (`already used by worktree at …`, `cannot remove the current working directory`) no dicen qué hacer.

### Diseño técnico
- `git worktree list --porcelain` + `git -C <ruta> status --porcelain` por cada worktree.
- Clasificar cada uno: **sano**, **huérfano** (registrado sin carpeta), **sucio** (cambios sin commitear), **terminado** (su rama ya fue mergeada a `develop`), **rama sin worktree**.
- Proponer la acción por categoría: `git worktree prune`, commitear o descartar, `git worktree remove`, crear el worktree faltante. Nunca ejecutar nada destructivo sin confirmación.
- Reusar `hooks/gitwt.py`, que ya resuelve worktrees y rutas sin subprocesos.

### Casos borde
- **Worktree sucio de una rama ya mergeada**: es el caso peligroso — hay trabajo sin commitear que el merge no incluyó. Frenar y avisar, jamás remover.
- **Worktree en un disco desmontado**: `status` falla; reportar "inaccesible" en vez de asumir huérfano.
- **El worktree de control**: nunca se ofrece removerlo.

---

## 15. Adopción asistida de la política de worktrees

### Objetivo
Migrar un repo que ya venía trabajando sin worktrees: detectar las ramas de trabajo existentes y ofrecer moverlas al modelo de un worktree por rama, sin perder cambios.

### Por qué vale la pena
La política de la v0.10.0 aplica limpio en ramas nuevas, pero un repo con ramas vivas creadas antes queda a mitad de camino: el hook avisa, y no hay un camino guiado para ordenarlo.

### Diseño técnico
- Listar ramas locales con prefijo GitFlow que no tengan worktree (`gitwt.worktree_for_branch` devuelve `None`).
- Para cada una, ofrecer `git worktree add "<worktreeRoot>/<tipo>-<slug>" <rama>` (sin `-b`: la rama ya existe).
- Si la rama está checked out en el worktree de control, primero mover el control a `develop`; si hay cambios sin commitear, frenar y pedir que se resuelvan.
- Registrar `branch_start` en el log de tiempos al adoptar cada rama, con nota de que el tiempo previo a la migración no está medido.

### Casos borde
- **Cambios sin commitear en la rama a migrar**: nunca migrar por encima; commitear o stashear primero (y recordar que `refs/stash` es global al repo).
- **Ramas viejas ya mergeadas**: ofrecer borrarlas en vez de darles worktree.
- **Repos sin `develop`**: derivar a `/git init` antes de migrar nada.

---

## Consideraciones transversales

### Sobre compatibilidad entre features
- #1 (`commit-message-writer`) y #3 (validación de Conventional Commits) se refuerzan: el subagente genera mensajes válidos, el hook garantiza que también los manuales lo sean.
- #4 (`release-notes-writer`) se enriquece con #3: si todos los commits cumplen Conventional, las notas salen limpias sin "Other".
- #5 (`conflict-resolver-guide`) aplica cuando #1, #4, #5 fallan por conflicto — se encadenan naturalmente, y con worktrees el conflicto se resuelve **dentro del worktree de la rama**, no en el de control.
- #11 (`blame-explainer`) y #7 (`history-explorer`) pueden compartir helpers — considerar extraer a un módulo común si se implementan ambos.
- **Todo lo que toque worktrees o rutas de git debe pasar por `hooks/gitwt.py`** (v0.10.0), que ya resuelve rama, git-dir y lista de worktrees sin subprocesos y con la config cacheada. Duplicar esa lógica es la forma más fácil de que dos partes del plugin discrepen.
- **Todo lo que agregue eventos medibles** (#13, #14) debe escribir en el registro existente (`hooks/timelog.py`) en vez de abrir un log paralelo.

### Sobre internacionalización
El soporte ES/EN está implementado desde v0.6.0: todo mensaje nuevo se agrega a `hooks/i18n.py` en **ambos** idiomas, y hay un test que falla si una clave existe en uno solo. Los skills declaran su idioma de salida al inicio y lo resuelven con `GITFLOW_LANG` → `git config gitflow-es.language` → `es`.

### Sobre configuración
El plugin ya pasó las 10 claves configurables (`language`, `scopes`, `worktreeRoot`, `worktrees`, `timeTracking`, `timeNotes`, `evidence`, `idleThresholdMin`, `externalGapMin`, `externalMargin`, `testPattern`, `timeLogDir`), todas en `git config` bajo `gitflow-es.*` y leídas de un solo golpe por `gitwt.config_all()`. La idea de un `gitflow-es.config.json` quedó descartada: `git config` ya da alcance por repo y global, no agrega un archivo nuevo al árbol y `/git init` recorre las claves de forma guiada. Regla para features nuevas: clave en `git config`, default explícito y documentada en el README y en `/git init`.

### Sobre testing
Los tests **sí son automatizados**: `python3 -m pytest plugins/gitflow-es/tests -q` (195 tests al cierre de la v0.10.0). Cada feature nueva agrega los suyos al mismo lugar. Lo que más valor dio hasta ahora:
- tests de **agregación numérica** con relojes fijos (nada que dependa de la hora real);
- **dobles** de `gitwt`/`timelog` en vez de repos de verdad, salvo para lo que se quiere probar contra git mismo;
- `test_plugin_structure.py`, que valida frontmatter, rutas referenciadas, scripts declarados en `hooks.json` y sincronía de versiones — atrapó rutas muertas que ningún test funcional hubiera visto;
- y un **repo de laboratorio** desechable para lo que solo se ve con git real (fue así como se descubrió que `git flow finish` reporta éxito sin mergear).
