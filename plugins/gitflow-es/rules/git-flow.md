# Git Flow

> **EN:** This is the single source of truth for the team's Git Flow policy.
> Content is authored in Spanish; all generated text — prose, **commit messages and
> branch names** — follows the configured language (`GITFLOW_LANG` or
> `git config gitflow-es.language`, default `es`). Branch names use
> configured-language words but stay kebab-case ASCII. Only git commands, GitFlow
> prefixes and Conventional Commit types/scopes are fixed and never translated.

## Ramas principales
- `main` — código en producción. **Nunca se modifica directamente.**
- `develop` — rama de integración. Base para todas las features y fixes.

## Tipos de rama

| Tipo | Prefijo | Base | Se fusiona en |
|------|---------|------|----------------|
| Nueva funcionalidad | `feature/` | `develop` | `develop` |
| Corrección en desarrollo | `fix/` | `develop` | `develop` |
| Refactor sin impacto funcional | `refactor/` | `develop` | `develop` |
| Configuración / dependencias | `chore/` | `develop` | `develop` |
| Corrección urgente en producción | `hotfix/` | `main` | `main` + `develop` |
| Preparación de release | `release/` | `develop` | `main` + `develop` |

## Nomenclatura de ramas
```
feature/<descripcion-corta-en-kebab-case>
fix/<descripcion-corta-en-kebab-case>
refactor/<descripcion-corta-en-kebab-case>
chore/<descripcion-corta-en-kebab-case>
hotfix/<descripcion-corta-en-kebab-case>
release/<version>
```

## Worktrees (obligatorio)

Toda rama de trabajo vive en **su propio worktree**, creado desde `develop`
actualizado. El worktree principal del repo queda como **worktree de control**:
parado en `develop`, sin editar archivos ahí, y es el único lugar donde se hacen
los cierres (`finish`), los merges y los `sync`.

| Concepto | Regla |
|----------|-------|
| Ubicación | `<padre-del-repo>/<repo>-worktrees/<tipo>-<slug>/` (configurable con `git config gitflow-es.worktreeRoot`) |
| Base | `develop` para `feature`, `fix`, `refactor`, `chore` y `release`; `main` solo para `hotfix` (excepción estructural de GitFlow) |
| Creación | `git worktree add -b <tipo>/<slug> <ruta> <base>` — un solo comando crea rama y worktree |
| Cierre | Desde el worktree de control y **después** de `git worktree remove <ruta>` |
| Excepción | Si el usuario pide explícitamente trabajar sin worktree ("sin worktree", "en el repo principal") o desde otra base ("desde main", "desde `<rama>`"), se respeta y se deja constancia |

### Ciclo completo

```bash
# 1. Actualizar la base SIEMPRE en el worktree de control
#    (no se puede hacer pull de una rama ocupada por otro worktree)
git -C <control> pull --ff-only origin develop

# 2. Crear rama + worktree en un solo paso
git worktree add -b feature/<slug> "<worktreeRoot>/feature-<slug>" develop

# 3. Trabajar dentro del worktree: ediciones y commits normales

# 4. Cerrar: volver al control, remover el worktree y recién entonces finish
cd <control>
git worktree remove "<worktreeRoot>/feature-<slug>"
git flow feature finish <slug>

# 5. Verificar que el cierre fue real (ver abajo por qué)
git branch --list feature/<slug>             # debe salir vacío
git merge-base --is-ancestor <sha> develop   # debe salir 0
```

### Por qué el cierre se hace exactamente así

`git-flow-avh` **reporta éxito aunque no haya cerrado nada**:

| Escenario | Efecto real | Lo que reporta |
|-----------|-------------|----------------|
| `finish` dentro del worktree de la rama | No mergea nada y no borra la rama | "Summary of actions… merged… removed", **exit 0** |
| `finish` desde el control con el worktree vivo | Mergea, pero no borra la rama | Lo mismo, **exit 0** |
| `worktree remove` y luego `finish` desde el control | Correcto | Correcto |

Por eso el hook `safety-check` **bloquea** el primer caso, **avisa** en el segundo,
y `/git finish` **verifica las postcondiciones** en lugar de confiar en el código
de salida.

### Consecuencias operativas

- **Una rama ocupada por un worktree no se puede hacer `checkout` ni `pull` desde
  otro.** Actualizar `develop` y `main` es siempre tarea del worktree de control.
- **`git stash` engaña entre worktrees:** el working tree es propio de cada uno,
  pero `refs/stash` es **global al repo**. Un `stash pop` desde otro worktree
  aplica cambios de otra rama. Guardá y restaurá siempre en el mismo worktree.
- **`git worktree prune`** limpia los registros de worktrees borrados a mano.
- Los avisos de esta política se apagan con `git config gitflow-es.worktrees off`.

---

## Trabajo en paralelo

Cuando un trabajo se descompone en tareas **independientes**, se avanzan a la vez:
una rama y un worktree por tarea, todas creadas del mismo `develop`.

### Criterio de independencia

Dos tareas son independientes si **no modifican los mismos archivos**. Si los
comparten, hay tres salidas, en orden de preferencia:

1. Agruparlas en **una sola rama**.
2. Asignarle el archivo compartido a **una** rama; las demás no lo tocan.
3. Serializar: primero la que toca el archivo compartido, después las otras.

> Archivos que casi siempre son compartidos y conviene reservar a una sola rama:
> `CHANGELOG.md`, archivos de versión, traducciones, barrels de exportación y
> configuración de rutas.

### Reglas

1. **La base se actualiza una sola vez** antes de crear el lote completo, no una
   vez por rama.
2. **Un worktree, un ejecutor.** Nunca dos agentes o sesiones escribiendo en el
   mismo worktree.
3. **Se paraleliza la implementación y las pruebas; nunca los cierres.** Merges,
   `finish`, tags y publicaciones van de a uno y con confirmación explícita del
   usuario — cada cierre cambia `develop` y el siguiente debe partir de esa versión.
4. **Después de cada cierre**, las ramas del lote que siguen vivas se actualizan
   con el nuevo `develop` (`git -C <worktree> merge develop`) antes de cerrarse.
   Así los conflictos aparecen temprano y en el worktree correcto.
5. **Orden de cierre:** primero la rama que toca los archivos más compartidos.
6. Cada rama acumula su **propio registro de tiempos**; al reportar el lote, la
   suma por rama es mayor que el reloj real — para eso está el tiempo de calendario.

---

## Convención de commits (Conventional Commits)

Descripción en **español**, imperativo, sin mayúscula inicial, sin punto final. Máximo 72 caracteres en la primera línea.

```
feat(auth): agregar inicio de sesión con Google
fix(api): corregir manejo de timeout en peticiones
refactor(ui): extraer lógica de formulario a hook reutilizable
chore(deps): actualizar dependencias de desarrollo
test(utils): agregar pruebas para formateo de fechas
docs(api): documentar endpoints de autenticación
```

### Scopes del proyecto

Los scopes son **propios de cada proyecto**: identifican el módulo o área afectada
(p. ej. `auth`, `api`, `ui`, `deps`). No existe una lista universal — defínela según
la estructura del repo.

**Configurar la lista del proyecto** (opcional, recomendado): guarda los scopes
válidos separados por comas y se usarán como referencia al redactar commits:

```bash
git config gitflow-es.scopes "auth,api,ui,store,hooks,deps,navigation"
```

Si no hay lista configurada, infiere el scope de las rutas tocadas en el diff
(p. ej. cambios en `src/auth/**` → `auth`). Si ninguno encaja con claridad, omite
el scope o usa el más cercano y deja una nota.

### Reglas de commit
- **Nunca** commitear `.env`, credenciales ni binarios
- **Nunca** usar `--no-verify`
- **Nunca** pasar `--author` ni agregar `Co-Authored-By` — el autor siempre es el usuario configurado en git
- Siempre mostrar el mensaje propuesto y pedir confirmación antes de ejecutar

---

## Flujo Obligatorio con Claude (antes de cualquier cambio)

> **Es obligatorio usar los comandos de git-flow.** Claude nunca debe crear o cerrar ramas manualmente cuando existe un comando git-flow equivalente.
>
> **Precondición — git-flow inicializado.** Antes de una acción del modelo GitFlow
> o de escritura (`start`, `finish`, `release`, `hotfix`, `commit`, `merge`,
> `push`, `tag`), verifica que git-flow esté inicializado
> (`git config --get gitflow.branch.develop`). Si **no** lo está, **pide
> confirmación** al usuario para ejecutar `git flow init -d`: si acepta,
> inicialízalo y continúa; si rechaza, sigue con `git` estándar cuando la acción
> lo permita. Las acciones de solo lectura (`status`, `log`, `diff`, `branch`,
> `checkout`, `stash`, `pull`, `sync`) no requieren esta validación.

1. Verificar la rama activa con `/git status`
2. **Nunca** modificar archivos directamente sobre `main` o `develop`
3. **Actualizar la rama base antes de crear cualquier rama** — siempre, y desde el
   **worktree de control** (una rama ocupada por otro worktree no acepta `pull`):
   ```bash
   git -C <control> pull --ff-only origin develop   # feature, fix, refactor, chore, release
   git -C <control> pull --ff-only origin main      # hotfix
   ```
4. **Preguntar el tipo de cambio** — solo si el usuario NO lo indicó ya en su mensaje
5. **Proponer el nombre de la rama** y confirmar con el usuario
6. **Crear la rama y su worktree** solo después de confirmación — `git worktree add -b <tipo>/<slug> <ruta> <base>` (modo worktree, default) o el comando git-flow correspondiente si el usuario pidió trabajar sin worktree
7. Realizar los cambios en archivos
8. Proponer mensaje de commit siguiendo Conventional Commits y pedir confirmación
9. _(Opcional)_ Si el proyecto cuenta con un comando o script de pruebas, puedes sugerirle al usuario ejecutarlo antes del finish. Si el proyecto no tiene pruebas automatizadas o el usuario prefiere omitirlas, continuar al siguiente paso sin bloquear.
10. Hacer el finish con git-flow.

### Manejo de conflictos en finish

Si un `finish` falla por conflictos de merge:
1. **Detener inmediatamente** — no intentar resolver automáticamente
2. Reportar los archivos en conflicto:
   > "El finish falló por conflictos en: [archivos]. Resuélvelos manualmente y avísame para continuar."
3. Esperar confirmación del usuario de que los conflictos están resueltos
4. Reintentar el finish solo después de esa confirmación

### Reglas estrictas
> Claude **nunca debe modificar archivos** sin haber definido y confirmado la rama de trabajo.
> Claude **nunca debe commitear directamente** en `main`. En `develop` solo si el usuario lo solicita **explícitamente** (ver excepción abajo).
> Claude **debe crear la rama git al inicio de cada fase** — antes de tocar cualquier archivo.
> Claude **crea las ramas con `git worktree add -b`** (modo worktree) o con `git flow <tipo> start` (modo sin worktree, solo si el usuario lo pidió). `git checkout -b` y `git switch -c` quedan prohibidos en ambos modos.
> Claude **debe cerrar con comandos git-flow** para los tipos soportados — nunca merge manual cuando hay equivalente git-flow — y **verificar el resultado**, porque `git flow finish` reporta éxito aunque no haya mergeado.
> Claude **siempre debe actualizar la rama base desde el worktree de control** antes de crear cualquier rama nueva, incluso con git-flow nativo.

### Excepción — Commit directo en `develop`

El usuario puede solicitar commits directos en `develop` saltándose el flujo de rama de trabajo. Condiciones:

- **Solo para `develop`** — nunca para `main`.
- La solicitud debe ser **explícita**. Frases válidas: "commit directo en develop", "sin rama", "commit en develop", "directo a develop".
- Una aprobación genérica ("sí", "ok", "aplicar") **no** activa la excepción — el usuario debe mencionar `develop` o "directo".
- Claude debe seguir mostrando el mensaje propuesto y pedir confirmación antes de ejecutar.
- Claude debe seguir las convenciones de Conventional Commits normalmente.
- Si estás en `develop` y el usuario pide "hacer commit" sin especificar, preguntar si quiere crear rama o commitear directo.

---

## Comandos git-flow por tipo de rama

> **Nota:** este flujo usa `feature`, `hotfix` y `release`. git-flow también
> ofrece `support` y `bugfix`; no forman parte del flujo del equipo, pero si se
> usan, el hook de seguridad exige que el repo tenga `git flow init` igual que
> con los demás subcomandos.

### Tipos con soporte nativo git-flow

La **creación** usa worktrees; el **cierre** usa el comando git-flow desde el
worktree de control, con el worktree de la rama ya removido.

```bash
# feature
git -C <control> pull --ff-only origin develop
git worktree add -b feature/<nombre> "<worktreeRoot>/feature-<nombre>" develop
# finish (desde <control>):
git worktree remove "<worktreeRoot>/feature-<nombre>" && git flow feature finish <nombre>

# hotfix (única excepción de base: parte de main)
git -C <control> pull --ff-only origin main
git worktree add -b hotfix/<nombre> "<worktreeRoot>/hotfix-<nombre>" main
# finish (desde <control>):
git worktree remove "<worktreeRoot>/hotfix-<nombre>" && git flow hotfix finish <nombre>

# release
git -C <control> pull --ff-only origin develop
git worktree add -b release/<version> "<worktreeRoot>/release-<version>" develop
# finish (desde <control>):
git worktree remove "<worktreeRoot>/release-<version>" && git flow release finish <version>
```

### Tipos sin soporte nativo git-flow

```bash
# fix, refactor, chore — idéntico patrón
git -C <control> pull --ff-only origin develop
git worktree add -b fix/<nombre> "<worktreeRoot>/fix-<nombre>" develop
# finish (desde <control>, con el worktree ya removido):
git worktree remove "<worktreeRoot>/fix-<nombre>"
git merge --no-ff fix/<nombre> && git branch -d fix/<nombre>
```

> En el worktree de control ya estamos parados en `develop`, así que el `finish`
> manual **no lleva `git checkout develop`**: ese checkout fallaría si `develop`
> estuviera ocupado por otro worktree.

### Modo sin worktree (solo si el usuario lo pide)

```bash
git flow feature start <nombre>     # crea y hace checkout en el worktree actual
git flow feature finish <nombre>    # verificar postcondiciones igual
```
