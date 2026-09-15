---
name: worktrees
description: Gestiona worktrees de git y reparte trabajo en paralelo siguiendo el modelo GitFlow del proyecto. Úsalo cuando el usuario mencione worktrees, quiera avanzar varias tareas a la vez, pida paralelizar, hable de "varias ramas al mismo tiempo", o cuando un requerimiento se pueda descomponer en tareas independientes. También para listar, crear, remover o limpiar worktrees existentes.
---

# Worktrees y trabajo en paralelo

Gestiona los worktrees del repo y reparte tareas independientes en ramas
paralelas, todas nacidas de `develop`.

> **Fuente única de verdad:** `../../rules/git-flow.md` → secciones "Worktrees
> (obligatorio)" y "Trabajo en paralelo". Este skill describe la operación; la
> política vive en la rule.

## Idioma de salida

Detecta el idioma configurado (`GITFLOW_LANG`, luego
`git config --get gitflow-es.language`, default `es`) y produce **todo** el texto
generado en ese idioma, incluyendo nombres de rama (kebab-case ASCII).

## Conceptos

| Concepto | Qué es |
| --- | --- |
| **Worktree de control** | El repo principal. Queda parado en `develop`, no se editan archivos ahí y es el único lugar donde se cierran ramas |
| **Worktree de rama** | Una copia de trabajo por rama, en `<worktreeRoot>/<tipo>-<slug>/` |
| **`worktreeRoot`** | `git config gitflow-es.worktreeRoot`; default `<padre-del-repo>/<repo>-worktrees` |

## Uso

```
/worktrees                        → Lista worktrees, ramas y cuál es el de control
/worktrees nuevo <tipo> <desc>    → Crea una rama con su worktree (igual que /git start)
/worktrees paralelo <tareas>      → Reparte N tareas independientes en N worktrees
/worktrees cerrar <rama>          → Cierra una rama del lote (delega en /git finish)
/worktrees limpiar                → Remueve worktrees terminados y corre prune
```

---

## Subcomando: paralelo

Reparte varias tareas independientes, cada una en su rama y su worktree, todas
desde `develop`.

### 1. Verificar que las tareas son realmente independientes

**Antes** de crear nada, evaluar los archivos que tocaría cada tarea:

- **Independientes** → van en paralelo.
- **Comparten archivos** → hay tres salidas, en orden de preferencia:
  1. Agrupar esas tareas en **una sola rama** (lo más simple).
  2. Asignarle el archivo compartido a **una** rama y que las demás no lo toquen.
  3. Serializar: hacer primero la que toca el archivo compartido y las demás después.

> Archivos que casi siempre son compartidos y conviene reservar a una sola rama:
> `CHANGELOG.md`, archivos de versión (`package.json`, `plugin.json`…), archivos
> de traducciones, barrels/índices de exportación y configuración de rutas.

Mostrar el reparto propuesto al usuario y confirmarlo antes de crear worktrees.

### 2. Actualizar la base UNA sola vez

```bash
git -C <control> pull --ff-only origin develop
```

No repetir el pull por cada rama: todos los worktrees se crean del mismo punto.

### 3. Crear un worktree por tarea

```bash
git worktree add -b feature/<slug-1> "<worktreeRoot>/feature-<slug-1>" develop
git worktree add -b fix/<slug-2>     "<worktreeRoot>/fix-<slug-2>"     develop
```

Registrar cada rama en el log de tiempos con su descripción (skill `tiempos`), de
modo que cada una acumule su propio tiempo aunque se trabajen a la vez.

### 4. Trabajar en paralelo

- **Un worktree, un ejecutor.** Nunca dos agentes o sesiones escribiendo en el
  mismo worktree: se pisan el índice de git y el working tree.
- Cada worktree corre **sus propias pruebas**, dentro de su carpeta.
- Si una tarea necesita algo que otra está construyendo, **no es independiente**:
  volver al paso 1.

### 5. Cerrar de a una (nunca en paralelo)

Los merges **no** se paralelizan: cada cierre cambia `develop` y el siguiente
debe partir de esa versión nueva.

1. Elegir el orden: **primero la rama que toca los archivos más compartidos**, así
   las demás integran ese cambio temprano y los conflictos aparecen ya resueltos.
2. Cerrar con `/git finish` (que remueve el worktree, cierra desde el control y
   verifica las postcondiciones).
3. **Actualizar las ramas que siguen vivas** con el nuevo `develop`:
   ```bash
   git -C "<worktreeRoot>/<otra-rama>" merge develop
   ```
   Si aparece conflicto, resolverlo en ese worktree **antes** de cerrarlo.
4. Repetir hasta vaciar el lote.

### 6. Reportar

Al terminar el lote, mostrar el estado de cada rama (cerrada / pendiente / con
conflicto) y el reporte `/tiempos todas`, que separa el tiempo por rama e informa
además el **tiempo de calendario**: la suma por rama es mayor que el reloj real
cuando hubo trabajo simultáneo.

---

## Subcomando: listar

1. `git worktree list` — ruta, sha y rama de cada worktree
2. Marcar cuál es el de control (el primero que devuelve git)
3. Señalar worktrees huérfanos (carpeta borrada a mano) y ofrecer `git worktree prune`
4. Para cada worktree de rama, indicar si tiene cambios sin commitear
   (`git -C <ruta> status --porcelain`)

---

## Subcomando: limpiar

1. Listar los worktrees cuyas ramas ya fueron cerradas
2. Verificar que no tienen cambios sin commitear — si los tienen, **detenerse y
   preguntar**
3. `git worktree remove "<ruta>"` por cada uno (nunca `rm -rf`: deja el registro colgado)
4. `git worktree prune` al final
5. Confirmar el estado resultante

---

## Errores comunes y qué significan

| Mensaje de git | Causa | Salida |
| --- | --- | --- |
| `'<rama>' is already used by worktree at …` | Intentaste hacer checkout/pull de una rama ocupada por otro worktree | Trabajar en ese worktree, o actualizar la rama desde ahí |
| `cannot remove the current working directory` | Estás parado dentro del worktree que querés remover | Ir al worktree de control primero |
| `cannot delete branch '<rama>' used by worktree at …` | Estás cerrando una rama con su worktree todavía vivo | `git worktree remove` y recién después el finish |
| `fatal: '<ruta>' already exists` | Quedó la carpeta de un worktree removido a mano | `git worktree prune` y volver a crear |

## Reglas de seguridad

- **Nunca** trabajar dos tareas en el mismo worktree.
- **Nunca** paralelizar merges, cierres, tags o publicaciones — siempre de a uno y con confirmación.
- **Nunca** borrar un worktree con `rm -rf`: usar `git worktree remove`.
- Remover un worktree **no** borra la rama ni sus commits; cerrar la rama es trabajo de `/git finish`.
