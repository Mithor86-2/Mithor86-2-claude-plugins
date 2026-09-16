#!/usr/bin/env python3
"""
gitflow-es time tracker (hook multi-evento + CLI).

Registra la línea de tiempo de cada rama en `<git-common-dir>/gitflow-es/tiempos/`.
Nunca imprime nada ni bloquea: si algo falla, no registra y la sesión sigue igual.

Eventos que consume:

| Evento              | Qué registra                                             |
|---------------------|----------------------------------------------------------|
| `SessionStart`      | `session_start` + escaneo incremental de evidencia        |
| `UserPromptSubmit`  | `prompt` con la descripción corta de lo pedido            |
| `Stop`              | `stop` (fin de la ventana de trabajo)                     |
| `PreToolUse`        | `test_start` si el comando es de pruebas; `activity` si la |
|                     | herramienta apunta al worktree de otra rama               |
| `PostToolUse(Failure)` | `test_end` (con resultado), `commit` (asunto del commit) |
|                     | y `notify_end`: la herramienta corrió, hubo permiso        |
| `Notification`      | `notify` — motivo de la espera (permiso, input…)          |
| `SessionEnd`        | `session_end` + escaneo de evidencia                      |

Modo CLI (lo usan los skills `git` y `tiempos`):

    time-tracker.py --mark branch_start --note "descripción de la rama"
    time-tracker.py --mark branch_finish --note "resumen del cierre"
        # además congela la evidencia: mtime de los archivos y timestamps de
        # los commits, que tras el merge ya no se pueden recuperar
    time-tracker.py --describe "nueva descripción"
    time-tracker.py --evidence          # fuerza un escaneo (antes de remover el worktree)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import gitwt
    import timelog
except Exception:  # pragma: no cover - ruta de degradación
    gitwt = None
    timelog = None

# `cd <ruta>` o `git -C <ruta>`: así se detecta trabajo dirigido al worktree de
# otra rama (lotes en paralelo), para que ese tiempo no se le cargue a la rama
# de la sesión.
TARGET_PATH_RE = re.compile(
    r"(?:\bcd|\bgit\s+-C)\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|]+))"
)
GIT_COMMIT_RE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b")
ACTIVITY_THROTTLE_SECONDS = 60

# El `notification_type` que manda Claude Code no es un contrato estable, así
# que la espera de permiso se reconoce por el tipo *o* por el texto del aviso,
# en los dos idiomas. Ante la duda se clasifica como `other` y no se descuenta
# nada: preferimos subestimar la espera antes que inventarla.
NOTIFY_PERMISSION_RE = re.compile(
    r"permis|permiss|aprob|approv|autoriz|author", re.IGNORECASE
)
NOTIFY_IDLE_RE = re.compile(r"idle|waiting|espera", re.IGNORECASE)


def tool_failed(payload: dict) -> bool:
    """True solo si hay evidencia clara de que la herramienta falló."""
    if payload.get("hook_event_name") == "PostToolUseFailure":
        return True
    for key in ("tool_response", "tool_output", "tool_result"):
        result = payload.get(key)
        if isinstance(result, dict):
            code = result.get("exit_code", result.get("exitCode"))
            if isinstance(code, int) and code != 0:
                return True
            if result.get("is_error") is True:
                return True
    return False


def notification_kind(payload: dict) -> str:
    """De qué espera habla el aviso: `permission`, `idle` u `other`."""
    raw = " ".join(
        str(payload.get(key) or "")
        for key in ("notification_type", "message", "title")
    )
    if NOTIFY_PERMISSION_RE.search(raw):
        return "permission"
    if NOTIFY_IDLE_RE.search(raw):
        return "idle"
    return "other"


def approval_stamp_path(branch: str, cwd: Optional[str]) -> Optional[str]:
    state = gitwt.plugin_state_dir(cwd)
    if not state:
        return None
    return os.path.join(state, "aprobacion-{0}.stamp".format(timelog.sanitize_branch(branch)))


def open_approval_wait(branch: str, cwd: Optional[str]) -> None:
    """Deja constancia de que hay un permiso pendiente de respuesta."""
    stamp = approval_stamp_path(branch, cwd)
    if not stamp:
        return
    try:
        with open(stamp, "w") as handle:
            handle.write(str(int(time.time())))
    except OSError:
        pass


def close_approval_wait(branch: str, cwd: Optional[str], session: str) -> None:
    """
    Cierra la espera de permiso abierta, si la hay.

    El aviso de permiso es un punto en el tiempo, no un intervalo: sin este
    cierre no habría con qué acotar la espera. Se llama cuando el usuario ya
    respondió — al correr la herramienta aprobada, y también al terminar el
    turno o al escribir otro prompt, que es como se ve un permiso rechazado.
    """
    stamp = approval_stamp_path(branch, cwd)
    if not stamp or not os.path.exists(stamp):
        return
    try:
        os.remove(stamp)
    except OSError:
        return  # sin poder limpiarlo, no se registra: mejor eso que duplicar
    timelog.append_event(branch, "notify_end", cwd=cwd, s=session)


def freeze_commit_times(branch: str, cwd: Optional[str]) -> int:
    """
    Congela en el log los timestamps de los commits de la rama.

    Tiene que pasar ANTES del merge: después `git log <base>..<rama>` no
    devuelve nada y la rama cerrada se queda sin evidencia con la que
    justificar sus tiempos muertos.
    """
    if not timelog.evidence_enabled(cwd):
        return 0
    times = timelog.collect_commit_times(branch, cwd=cwd)
    if not times:
        return 0
    if not timelog.append_event(branch, "commit_times", cwd=cwd,
                               m=[round(value, 3) for value in times]):
        return 0
    return len(times)


def evidence_stamp_path(branch: str, cwd: Optional[str]) -> Optional[str]:
    state = gitwt.plugin_state_dir(cwd)
    if not state:
        return None
    return os.path.join(state, "evidence-{0}.stamp".format(timelog.sanitize_branch(branch)))


def scan_evidence(branch: str, cwd: Optional[str]) -> int:
    """
    Registra los archivos modificados y su `mtime` desde el último escaneo. Es
    lo que después permite distinguir un hueco muerto de uno en el que el
    usuario estuvo trabajando por fuera de la sesión.
    """
    if not timelog.evidence_enabled(cwd):
        return 0

    worktree = gitwt.run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if not worktree:
        return 0

    # El corte se marca con el inicio del escaneo: si un archivo cambia mientras
    # este corre, entra en el próximo en vez de perderse.
    started = time.time()
    stamp = evidence_stamp_path(branch, cwd)
    since = 0.0
    if stamp and os.path.exists(stamp):
        try:
            since = os.path.getmtime(stamp)
        except OSError:
            since = 0.0

    registrados = 0
    for path, mtime in timelog.scan_evidence(worktree, since=since):
        if timelog.append_event(branch, "evidence", cwd=cwd, p=path, m=round(mtime, 3)):
            registrados += 1

    if stamp:
        try:
            with open(stamp, "w") as handle:
                handle.write(str(int(started)))
            os.utime(stamp, (started, started))
        except OSError:
            pass
    return registrados


def record_activity_for_other_branch(command: str, session_branch: str, cwd: Optional[str]) -> None:
    """
    Si el comando apunta al worktree de otra rama, deja un evento `activity` en
    el log de *esa* rama. Sin esto, el trabajo en lotes paralelos se le cargaría
    entero a la rama de la sesión. Throttled a uno por minuto y por rama.
    """
    match = TARGET_PATH_RE.search(command or "")
    if not match:
        return
    target = next((g for g in match.groups() if g), None)
    if not target or not os.path.isdir(target):
        return

    other = gitwt.current_branch(target)
    if not other or other == session_branch:
        return
    if not gitwt.throttle("activity-{0}".format(timelog.sanitize_branch(other)),
                          ACTIVITY_THROTTLE_SECONDS, cwd=cwd):
        return

    timelog.append_event(other, "activity", cwd=cwd, w=target)


def handle_hook(payload: dict) -> None:
    event = payload.get("hook_event_name") or ""
    cwd = payload.get("cwd") or os.getcwd()

    if not timelog.tracking_enabled(cwd):
        return

    branch = gitwt.current_branch(cwd)
    if not branch:
        return  # HEAD desacoplado o fuera de un repo: no hay rama que medir

    session = (payload.get("session_id") or "")[:12]
    notes = timelog.notes_mode(cwd)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    if event == "SessionStart":
        timelog.append_event(branch, "session_start", cwd=cwd, s=session,
                             n=payload.get("source") or "")
        scan_evidence(branch, cwd)

    elif event == "UserPromptSubmit":
        close_approval_wait(branch, cwd, session)
        note = payload.get("prompt", "") if notes == "on" else ""
        timelog.append_event(branch, "prompt", cwd=cwd, s=session, n=note)

    elif event == "Stop":
        close_approval_wait(branch, cwd, session)
        timelog.append_event(branch, "stop", cwd=cwd, s=session)

    elif event == "PreToolUse":
        if tool_name != "Bash" or not command:
            return
        if timelog.is_test_command(command, cwd):
            timelog.append_event(branch, "test_start", cwd=cwd, s=session,
                                 id=payload.get("tool_use_id") or "",
                                 n=command if notes == "on" else "")
        else:
            record_activity_for_other_branch(command, branch, cwd)

    elif event in ("PostToolUse", "PostToolUseFailure"):
        # Que la herramienta haya corrido prueba que el permiso se concedió,
        # sea cual sea la herramienta: el filtro de Bash va después.
        close_approval_wait(branch, cwd, session)
        if tool_name != "Bash" or not command:
            return
        failed = tool_failed(payload)
        if timelog.is_test_command(command, cwd):
            timelog.append_event(branch, "test_end", cwd=cwd, s=session,
                                 id=payload.get("tool_use_id") or "", ok=not failed)
        elif GIT_COMMIT_RE.search(command) and not failed and notes != "off":
            subject = gitwt.run_git(["log", "-1", "--format=%s"], cwd=cwd)
            if subject:
                timelog.append_event(branch, "commit", cwd=cwd, s=session, n=subject)

    elif event == "Notification":
        kind = notification_kind(payload)
        timelog.append_event(branch, "notify", cwd=cwd, s=session,
                             n=payload.get("notification_type") or "", k=kind)
        if kind == "permission":
            open_approval_wait(branch, cwd)

    elif event == "SessionEnd":
        scan_evidence(branch, cwd)
        timelog.append_event(branch, "session_end", cwd=cwd, s=session,
                             n=payload.get("reason") or "")


def handle_cli(argv) -> int:
    """Modo CLI: marcas explícitas que registran los skills."""
    cwd = os.getcwd()
    mark = note = branch = None
    evidence = False

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--mark" and index + 1 < len(argv):
            mark = argv[index + 1]
            index += 1
        elif arg == "--note" and index + 1 < len(argv):
            note = argv[index + 1]
            index += 1
        elif arg == "--branch" and index + 1 < len(argv):
            branch = argv[index + 1]
            index += 1
        elif arg == "--describe" and index + 1 < len(argv):
            mark, note = "describe", argv[index + 1]
            index += 1
        elif arg == "--evidence":
            evidence = True
        index += 1

    branch = branch or gitwt.current_branch(cwd)
    if not branch:
        print("gitflow-es: no hay rama activa para registrar", file=sys.stderr)
        return 1

    if not timelog.tracking_enabled(cwd):
        print("gitflow-es: registro de tiempos desactivado (gitflow-es.timeTracking off)")
        return 0

    hecho = []
    if evidence:
        hecho.append("evidencia: {0} archivo(s)".format(scan_evidence(branch, cwd)))
    if mark:
        # El cierre necesita la evidencia ANTES de que se remueva el worktree.
        if mark == "branch_finish" and not evidence:
            hecho.append("evidencia: {0} archivo(s)".format(scan_evidence(branch, cwd)))
        if mark == "branch_finish":
            # ...y los commits ANTES del merge, que es lo que vacía el rango.
            congelados = freeze_commit_times(branch, cwd)
            if congelados:
                hecho.append("commits congelados: {0}".format(congelados))
        timelog.append_event(branch, mark, cwd=cwd, n=note or "")
        hecho.append("evento `{0}` registrado en `{1}`".format(mark, branch))

    print("gitflow-es: " + " · ".join(hecho) if hecho else "gitflow-es: nada que registrar")
    return 0


def main() -> None:
    if gitwt is None or timelog is None:
        sys.exit(0)

    argv = sys.argv[1:]
    if argv:
        try:
            sys.exit(handle_cli(argv))
        except Exception as error:  # pragma: no cover - el CLI sí reporta
            print("gitflow-es: no se pudo registrar ({0})".format(error), file=sys.stderr)
            sys.exit(1)

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        sys.exit(0)

    try:
        handle_hook(payload if isinstance(payload, dict) else {})
    except Exception:
        pass  # Un hook de medición jamás debe interrumpir la sesión.
    sys.exit(0)


if __name__ == "__main__":
    main()
