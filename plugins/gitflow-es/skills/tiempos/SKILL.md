---
name: tiempos
description: Consulta y administra el registro de tiempos por rama — cuánto tardó el trabajo, cuánto se fue en pruebas y cuánto fue tiempo muerto. Úsalo cuando el usuario pregunte cuánto tardó algo, pida un reporte de tiempos o de horas, quiera saber en qué se fue el tiempo de una rama, pida registrar o corregir la descripción del trabajo, o mencione tiempos muertos, inactividad o tiempo de pruebas. También lo invocan `/git start` y `/git finish` para abrir y cerrar el registro de cada rama.
---

# Registro de tiempos

Reporta cuánto tomó cada rama y en qué se fue ese tiempo, separando trabajo,
pruebas, espera del usuario e inactividad, con una descripción corta de lo que se
hizo.

> El registro es **local**: vive en `<git-common-dir>/gitflow-es/tiempos/`, es
> decir dentro de `.git/`. Nunca aparece en `git status`, nunca se commitea y
> sobrevive a que se remueva el worktree de la rama.

## Idioma de salida

Detecta el idioma configurado (`GITFLOW_LANG`, luego
`git config --get gitflow-es.language`, default `es`) y pásalo al reporte con
`--lang`.

## Scripts

Relativo a este skill, los scripts viven en `../../hooks/`:

| Script | Para qué |
| --- | --- |
| `../../hooks/time-report.py` | Genera el reporte (markdown o JSON) |
| `../../hooks/time-tracker.py` | Registra marcas explícitas (`--mark`, `--describe`, `--evidence`) |

Si la variable `$CLAUDE_PLUGIN_ROOT` está disponible, usala como raíz
(`$CLAUDE_PLUGIN_ROOT/hooks/…`).

## Uso

```
/tiempos                          → Reporte de la rama actual
/tiempos rama <nombre>            → Reporte de otra rama
/tiempos todas                    → Comparativa de todas las ramas con registro
/tiempos describir "<texto>"      → Fija o corrige la descripción de la rama
/tiempos nota "<texto>"           → Anota a mano el trabajo en curso
/tiempos exportar [ruta]          → Guarda el reporte fuera del repo
/tiempos estado                   → Dice si el registro está activo y dónde vive
```

---

## Subcomando: reporte (default)

```bash
python3 "<plugin>/hooks/time-report.py" --lang es
python3 "<plugin>/hooks/time-report.py" --branch feature/login --lang es
```

Mostrá la salida tal cual: ya viene formateada y traducida. Al comentarla,
apoyate en estas definiciones:

| Rubro | Qué es |
| --- | --- |
| **Trabajo** | Ventanas `prompt → stop`, sin el tiempo de pruebas |
| **Trabajo fuera de sesión** | Huecos con evidencia real de actividad (archivos modificados o commits) |
| **Pruebas** | Corridas de tests, medidas de inicio a fin de cada comando |
| **Espera del usuario** | Desde que Claude terminó hasta el siguiente mensaje, hasta el umbral |
| **Inactividad** | Lo que pasa del umbral (default 15 min) |

Los cinco rubros suman el total de reloj. **Efectivo** = trabajo + pruebas.

---

## Subcomando: todas

```bash
python3 "<plugin>/hooks/time-report.py" --all --lang es
```

Además de la tabla por rama informa el **tiempo de calendario** (unión de los
intervalos). Con trabajo en paralelo, la suma por rama es mayor que el reloj real:
al comentarlo, usá el calendario para el "cuánto tardó" y la suma por rama para el
"cuánto costó cada cosa".

---

## Subcomando: describir / nota

```bash
python3 "<plugin>/hooks/time-tracker.py" --describe "migrar el login a OAuth"
python3 "<plugin>/hooks/time-tracker.py" --mark nota --note "esperando review del API"
```

La descripción de la rama se registra automáticamente en `/git start` con lo que
pidió el usuario; `describir` la corrige después.

---

## Subcomando: exportar

1. Generar el reporte con `--format md` (o `--format json` si lo piden para otra herramienta).
2. Escribirlo **fuera del repo** (por ejemplo en el directorio de trabajo del usuario
   o en `/tmp`), o pegarlo en el chat.
3. **Nunca** commitear el desglose de tiempos: el registro es local por diseño.

---

## Subcomando: estado

1. `git config --get gitflow-es.timeTracking` — `off` significa que no se registra nada.
2. `git rev-parse --git-common-dir` — el registro vive en `<eso>/gitflow-es/tiempos/`.
3. Informar qué ramas tienen registro (`--all`) y cuáles configuraciones están activas
   (`timeNotes`, `evidence`, `idleThresholdMin`).

---

## Enganche con el ciclo de ramas

| Momento | Qué hace |
| --- | --- |
| `/git start` | `--mark branch_start --note "<descripción del usuario>"` |
| Durante el trabajo | Los hooks registran solos: prompts, pruebas, commits y esperas |
| `/git finish` | `--mark branch_finish --note "<resumen>"` **antes** de remover el worktree (después ya no hay `mtime` que escanear), y luego se muestra el reporte |

## Configuración

| Clave | Default | Qué controla |
| --- | --- | --- |
| `gitflow-es.timeTracking` | `on` | Activa o apaga todo el registro |
| `gitflow-es.timeNotes` | `on` | `on` (prompts + commits), `commits` (solo asuntos de commit), `off` (solo duraciones) |
| `gitflow-es.evidence` | `on` | Validar tiempos muertos con `mtime` y commits |
| `gitflow-es.idleThresholdMin` | `15` | Minutos desde los que un hueco es inactividad |
| `gitflow-es.externalGapMin` | `10` | Separación máxima entre evidencias del mismo bloque |
| `gitflow-es.externalMargin` | `5` | Margen que aporta cada bloque de evidencia |
| `gitflow-es.testPattern` | — | Regex extra para reconocer los comandos de test del proyecto |

Si el usuario pregunta por privacidad: con `timeNotes=on` se guarda la **primera
línea de cada prompt** (truncada a 160 caracteres) y el asunto de cada commit, en
disco local dentro de `.git/`. Con `commits` solo se guardan los asuntos de commit;
con `off`, únicamente duraciones.

## Reglas

- **Nunca** inventar tiempos ni descripciones: todo sale del registro real.
- Si no hay datos para una rama, decirlo tal cual (`/git start` es el que abre el registro).
- **Nunca** commitear los reportes ni el JSONL.
- Si el usuario pide apagar el registro, usar `git config gitflow-es.timeTracking off`
  y avisar que los datos ya registrados siguen en disco (se borran con `rm` del archivo
  de la rama, que se puede mostrar con `estado`).
