# Git Flow

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

## Convención de commits (Conventional Commits)

Descripción en **español**, imperativo, sin mayúscula inicial, sin punto final. Máximo 72 caracteres en la primera línea.

```
feat(weight): agregar registro de peso semanal
fix(auth): corregir validación de OTP expirado
refactor(hooks): extraer lógica de useMutation
chore(deps): actualizar expo-notifications a 0.32.16
test(utils): agregar pruebas para maskEmail
docs(hooks): documentar useWeightForm con JSDoc
```

### Scopes del proyecto
- Features: `auth`, `weight`, `nutrition`, `medication`, `mental`, `measure`, `fisical`, `dream`, `dashboard`, `profile`, `notification`
- Infraestructura: `navigation`, `ui`, `store`, `api`, `hooks`, `constants`

### Reglas de commit
- **Nunca** commitear `.env`, credenciales ni binarios
- **Nunca** usar `--no-verify`
- **Nunca** pasar `--author` ni agregar `Co-Authored-By` — el autor siempre es el usuario configurado en git
- Siempre mostrar el mensaje propuesto y pedir confirmación antes de ejecutar

---

## Flujo Obligatorio con Claude (antes de cualquier cambio)

> **Es obligatorio usar los comandos de git-flow.** Claude nunca debe crear o cerrar ramas manualmente cuando existe un comando git-flow equivalente.

1. Verificar la rama activa con `/git status`
2. **Nunca** modificar archivos directamente sobre `main` o `develop`
3. **Actualizar la rama base antes de crear cualquier rama** — siempre, incluso con git-flow nativo:
   ```bash
   git pull origin develop   # para feature, fix, refactor, chore
   git pull origin main      # para hotfix
   ```
4. **Preguntar el tipo de cambio** — solo si el usuario NO lo indicó ya en su mensaje
5. **Proponer el nombre de la rama** y confirmar con el usuario
6. **Crear la rama** solo después de confirmación — usando el comando git-flow correspondiente
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
> Claude **debe usar comandos git-flow** para tipos soportados — nunca `git checkout -b` ni merge manual cuando hay equivalente git-flow.
> Claude **siempre debe hacer pull de la rama base** antes de crear cualquier rama nueva, incluso con git-flow nativo.

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

### Tipos con soporte nativo git-flow

```bash
# feature
git pull origin develop
git flow feature start <nombre>
git flow feature finish <nombre>

# hotfix
git pull origin main
git flow hotfix start <nombre>
git flow hotfix finish <nombre>

# release
git pull origin develop
git flow release start <version>
git flow release finish <version>
```

### Tipos sin soporte nativo git-flow

```bash
# fix
git checkout develop && git pull origin develop
git checkout -b fix/<nombre>
# finish:
git checkout develop && git merge --no-ff fix/<nombre> && git branch -d fix/<nombre>

# refactor
git checkout develop && git pull origin develop
git checkout -b refactor/<nombre>
# finish: igual que fix

# chore
git checkout develop && git pull origin develop
git checkout -b chore/<nombre>
# finish: igual que fix
```
