---
name: branch-name-suggester
description: Propone 2-3 nombres de rama en kebab-case con el prefijo GitFlow correcto a partir de una descripción libre. Úsalo cuando el usuario va a crear una rama y describe qué quiere hacer pero aún no ha decidido el nombre, o cuando el skill `git` necesita proponer un nombre en su subcomando `start`. Aplica las reglas de nomenclatura de `../../rules/git-flow.md`.
---

# branch-name-suggester

Convierte una descripción libre ("quiero arreglar el bug del OTP expirado") en
2-3 nombres de rama listos para usar, con el prefijo GitFlow correcto y en
kebab-case estricto. No creas la rama — solo propones; el skill `git` (o el
usuario) confirma y crea.

## Idioma de salida

Antes de responder, detecta el idioma configurado para gitflow-es y produce
**toda** tu salida al usuario en ese idioma:
1. Si `GITFLOW_LANG` está definida, úsala.
2. Si no, ejecuta `git config --get gitflow-es.language` y usa su valor.
3. Si ninguna existe, usa español (`es`) por defecto.

Valores válidos: `es` y `en`; cualquier otro se trata como `es`. El idioma afecta
tanto la **prosa** (preguntas, explicaciones) como las **palabras de los nombres de
rama** que propongas (en `en` propón nombres en inglés; en `es`, en español). Los
nombres van **siempre** en kebab-case ASCII: **nunca con tildes, ñ ni espacios** (ver
reglas abajo). Los prefijos GitFlow (`feature/`, `fix/`…) son fijos.

## Fuente de verdad

`../../rules/git-flow.md` define los tipos de rama, sus prefijos y la base de cada
uno. Consúltala ante cualquier duda de política. Los prefijos válidos son:
`feature/`, `fix/`, `hotfix/`, `chore/`, `refactor/` (y `release/` para releases).

## Reglas de generación

- **Prefijo según el tipo**: infiérelo del verbo/intención ("agregar/añadir" →
  `feature/`; "arreglar/corregir" → `fix/`; "urgente en producción" → `hotfix/`;
  "actualizar deps/config" → `chore/`; "refactorizar/extraer" → `refactor/`).
- **Idioma de las palabras**: usa el idioma configurado (en `en` propón nombres en
  inglés, en `es` en español).
- **kebab-case estricto**: solo `[a-z0-9-]`. **Translitera** tildes y ñ a ASCII
  (á→a, é→e, í→i, ó→o, ú→u, ü→u, ñ→n). Sin espacios ni mayúsculas.
- **Longitud total ≤ 50 caracteres** (incluyendo el prefijo).
- **Sin artículos** (`el`, `la`, `un`, `the`, `a`) salvo que aporten claridad.
- **Imperativo corto**, no una oración completa.
- Propón **2-3 alternativas** ordenadas de más a menos recomendada, marcando la
  primera con `← recomendado`.

## Casos borde

- **Tipo no especificado**: si no puedes inferir con confianza si es feature/fix/
  etc., **pregunta el tipo** antes de proponer. No adivines entre `fix` y `feature`.
- **Descripción demasiado genérica** ("arreglar cosas", "hacer cambios"): pide un
  poco más de detalle antes de proponer.
- **Ticket detectado** (regex `[A-Z]+-\d+`, ej. `AUTH-123`): ofrece una variante con
  el ticket como sufijo (`fix/auth-123-login-timeout`) y deja que el usuario elija.

## Integración con `git`

Cuando el skill `git` esté en el subcomando `start` y necesite un nombre, delega
aquí: devuelve las 2-3 alternativas y deja que `git` las muestre y confirme con el
usuario **antes** de crear la rama.

## Ejemplos

```
Usuario: "quiero arrancar una feature para permitir login con Google"

1. feature/login-con-google      ← recomendado (claro y corto)
2. feature/google-auth           (estilo técnico, más breve)
3. feature/autenticacion-google  (más formal)

¿Cuál usamos?
```

```
Usuario: "arreglar AUTH-456: el timeout de sesión es muy corto"

1. fix/auth-456-session-timeout  ← recomendado (incluye ticket)
2. fix/session-timeout           (sin ticket)
3. fix/auth-session-timeout      (con scope, sin número)
```

```
Usuario: "necesito cambiar algo en el proyecto"
→ La descripción es muy genérica. ¿Qué quieres cambiar exactamente y de qué tipo
  es (feature, fix, chore, refactor)?
```

```
[idioma configurado = en] User: "I want to add Google login"

1. feature/google-login          ← recommended
2. feature/login-with-google     (more descriptive)
3. feature/google-auth           (technical, shorter)
```
