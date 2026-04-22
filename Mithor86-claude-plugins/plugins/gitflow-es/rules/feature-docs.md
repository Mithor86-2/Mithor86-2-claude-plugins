# Documentación por Feature

Al hacer el **finish de una rama**, Claude debe crear este archivo **automáticamente** como parte del flujo de `/git finish`, antes de ejecutar el merge.

> Si el usuario invoca `/git finish` sin que exista el doc, Claude debe generarlo primero y pedir confirmación antes de continuar con el merge.

```
docs/
└── <nombre-de-la-feature>/
    └── <YYYY-MM-DD>-<nombre-de-la-feature>.md
```

---

## Contenido obligatorio

```markdown
# [nombre-feature] — YYYY-MM-DD

## Descripción
Resumen de los cambios realizados.

## Cambios de lógica de negocio
- Lista de cambios en reglas de negocio, flujos o comportamientos.

## Archivos modificados
- `ruta/al/archivo.ts` — descripción del cambio

## Paquetes instalados / actualizados
| Paquete | Versión | Motivo |
|---------|---------|--------|

## Pruebas ejecutadas

### Unitarias
| Archivo de test | Tests | Pasaron | Fallaron |
|----------------|-------|---------|---------|

#### `<nombre-del-archivo>.test.ts`
| # | Descripción del test | Parámetros de entrada | Resultado esperado | ✅/❌ |
|---|---------------------|----------------------|-------------------|------|
| 1 | descripción corta   | `param: valor`       | `retorna X`       | ✅   |

### Pruebas manuales / de integración
| # | Escenario | Pasos / Datos de entrada | Resultado esperado | Resultado obtenido | ✅/❌ |
|---|-----------|--------------------------|-------------------|-------------------|------|

## Resultado
✅ Rama cerrada exitosamente / ⚠️ Pendiente de revisión
```

---

## Cuándo se crea

| Situación | Acción |
|-----------|--------|
| `/git finish` en rama `feature/*` | Claude genera el doc automáticamente antes del merge |
| `/git finish` en rama `fix/*` | Claude genera el doc automáticamente antes del merge |
| `/git finish` en rama `hotfix/*` | Claude genera el doc automáticamente antes del merge |
| Rama `chore/*` o `refactor/*` sin cambios de lógica | Opcional — preguntar al usuario si desea generarlo |

> El archivo debe crearse y confirmarse con el usuario **antes** de ejecutar el finish de la rama.
