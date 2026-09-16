# Política de seguridad

## Versiones soportadas

El plugin sigue SemVer y está en la serie `0.x`: solo la **última versión menor
publicada** recibe correcciones de seguridad. Al publicarse una nueva menor, la
anterior deja de recibirlas.

| Versión | Soportada |
| ------- | --------- |
| 0.10.x  | ✅ |
| < 0.10  | ❌ |

## Reportar una vulnerabilidad

Usá el **reporte privado de vulnerabilidades de GitHub**, en la pestaña
*Security* del repositorio → *Report a vulnerability*. Así el reporte queda
privado hasta que exista una corrección.

**No abras un issue público** para una vulnerabilidad: los issues son visibles
para cualquiera.

En el reporte ayuda incluir la versión del plugin, el sistema operativo, los
pasos para reproducirlo y qué impacto tiene.

Esperá una primera respuesta dentro de los **7 días**. Si se acepta, el arreglo
sale en una versión de parche y el reporte se acredita en el `CHANGELOG.md`
salvo que prefieras permanecer anónimo. Si se descarta, vas a recibir el motivo.

## Alcance

Este repositorio distribuye **plugins de Claude Code**: skills en markdown y
hooks en Python que corren localmente, con los permisos de quien los instala.
Interesan especialmente los reportes sobre:

- Ejecución de comandos no prevista desde un hook.
- Fuga de datos del repositorio o del entorno hacia afuera de la máquina.
- Operaciones destructivas de git que los hooks de seguridad deberían bloquear.

El registro de tiempos guarda datos **solo en local**, dentro de `.git/`, y
nunca se commitea ni se envía a ningún servicio.
