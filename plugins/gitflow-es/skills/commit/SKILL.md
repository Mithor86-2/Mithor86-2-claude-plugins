---
name: commit
description: Genera y aplica commits siguiendo Conventional Commits del proyecto. Úsalo siempre que el usuario quiera hacer un commit, guardar cambios en git, registrar cambios, o mencione mensajes de commit, staging, o Conventional Commits — aunque no use la palabra "commit" explícitamente. También cuando el skill `git` delega la creación del mensaje de commit.
---

# Git Commit

Genera y aplica un commit siguiendo Conventional Commits y las convenciones del proyecto.

## Idioma de salida

Antes de responder, detecta el idioma configurado para gitflow-es y produce
**toda** tu salida al usuario en ese idioma:
1. Si `GITFLOW_LANG` está definida, úsala.
2. Si no, ejecuta `git config --get gitflow-es.language` y usa su valor.
3. Si ninguna existe, usa español (`es`) por defecto.

Valores válidos: `es` y `en`; cualquier otro se trata como `es`. El idioma afecta el
**asunto/cuerpo** del commit, pero los tipos (`feat`, `fix`…) y scopes no se traducen.

## Flujo

1. Ejecutar `git status` — verificar qué archivos están staged
2. Si no hay nada staged, mostrar los archivos modificados y preguntar cuáles stagear
3. Ejecutar `git diff --staged` — analizar el contenido real de los cambios
4. Determinar tipo y scope según los archivos y cambios detectados
5. **Redactar el mensaje** delegando al subagente `commit-message-writer`, que lee
   `git diff --staged` en contexto aislado y devuelve el mensaje propuesto siguiendo
   Conventional Commits
6. Mostrar el mensaje propuesto y pedir confirmación antes de aplicar
7. Ejecutar `git commit -m "<mensaje>"`

---

## Referencia de Conventional Commits

> **Fuente única de verdad:** `../../rules/git-flow.md` (dentro de este plugin) — sección "Convención de commits (Conventional Commits)".
> Consultar ahí la tabla completa de tipos, la lista de scopes del proyecto y el formato del mensaje.

Tipos soportados adicionales no listados en la rule (uso puntual): `style`, `test`, `perf`, `ci`, `docs`.

## Formato del mensaje

```
<tipo>(<scope>): <descripción imperativo, sin punto final>

[cuerpo opcional — explica el "por qué", no el "qué"]
```

## Ejemplos

```
feat(auth): agregar validación de peso en onboarding
fix(container): evitar crash de useFocusEffect fuera de NavigationContainer
refactor(auth): extraer lógica de scroll-to-top en componente aislado
chore(deps): actualizar expo sdk a 54.0.27
```

## Reglas

- Descripción en el **idioma configurado** (ver "Idioma de salida"; default español), imperativo, sin mayúscula inicial, sin punto final
- Máximo 72 caracteres en la primera línea
- Si afecta múltiples scopes, usar el más representativo
- **Nunca** commitear `.env`, credenciales ni binarios
- **Nunca** usar `--no-verify`
- **Nunca** commitear directamente en `main`
- En `develop` solo si el usuario lo solicita de forma explícita — ver excepción "Commit directo en `develop`" en `../../rules/git-flow.md`
- Siempre mostrar el mensaje propuesto y pedir confirmación antes de ejecutar
- El autor del commit debe ser siempre el usuario configurado en git — **nunca** pasar `--author` ni agregar `Co-Authored-By` en el cuerpo del mensaje
