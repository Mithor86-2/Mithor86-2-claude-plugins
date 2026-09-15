#!/usr/bin/env python3
"""
gitflow-es — registro de tiempos por rama.

Guarda un JSONL por rama dentro de `<git-common-dir>/gitflow-es/tiempos/`. Al
vivir bajo `.git/`, el registro nunca aparece en `git status` ni se commitea, y
sobrevive a que se remueva el worktree de la rama.

Modelo aditivo: para cada rama,

    total (reloj) = trabajo + trabajo_externo + pruebas + espera + inactividad

- **trabajo**: ventanas `prompt → stop`, menos las pruebas que caen dentro.
- **pruebas**: intervalos de comandos de test, pareados por `tool_use_id`.
- **espera**: hueco que termina en un `prompt`, hasta el umbral de inactividad.
- **inactividad**: lo que exceda el umbral, separado en `usuario` (huecos que
  terminan esperando al usuario) y `sesion` (el resto).
- **trabajo_externo**: porciones de huecos donde hay evidencia real de actividad
  (mtime de archivos modificados o timestamps de commits). Sin este cruce,
  editar en el editor fuera de la sesión se contaría como tiempo muerto.

Los rubros se calculan pintando una partición de la línea de tiempo, así que
suman el total por construcción.

Diseño:
  - Puro stdlib, compatible con Python 3.7+.
  - Escritura con `O_APPEND` y una sola llamada a `write`: varios worktrees y
    sesiones pueden registrar a la vez sin corromper el archivo.
  - Todo fail-open: si algo falla, no se registra y nadie se entera.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import gitwt as _gitwt
except Exception:  # pragma: no cover - ruta de degradación
    _gitwt = None

# Límite de una línea del JSONL. Por debajo de PIPE_BUF (4096) un `write` con
# O_APPEND es atómico en Linux y macOS, que es lo que hace seguro escribir desde
# varios worktrees a la vez.
MAX_LINE_BYTES = 4000
MAX_NOTE_CHARS = 160

DEFAULT_IDLE_THRESHOLD = 15 * 60       # gitflow-es.idleThresholdMin
DEFAULT_EVIDENCE_GAP = 10 * 60         # gitflow-es.externalGapMin
DEFAULT_EVIDENCE_MARGIN = 5 * 60       # gitflow-es.externalMargin
# Más allá de esto, una rama abierta sin actividad deja de sumar reloj: si no,
# una rama olvidada acumularía semanas de "inactividad" y taparía lo demás.
STALE_AFTER = 24 * 3600
# Un checkout, un `worktree add` o un build reescriben cientos de archivos con el
# mismo mtime: eso no es trabajo humano.
BULK_WRITE_FILES = 20
BULK_WRITE_WINDOW = 2.0

EVENTS_WITH_NOTE = {"prompt", "commit", "branch_start", "branch_finish", "test_start"}

# Una entrada de `git status --porcelain`: dos caracteres de estado y la ruta.
STATUS_ENTRY_RE = re.compile(r"^[ ?!ACDMRTU]{1,2}\s+(?P<path>.+)$")

# Comandos que cuentan como "corrida de pruebas". `gitflow-es.testPattern` suma
# los del proyecto sin tener que tocar el plugin.
TEST_COMMAND_RE = re.compile(
    r"\b("
    r"pytest|py\.test|unittest|tox|nox|"
    r"jest|vitest|mocha|ava|cypress|playwright\s+test|"
    r"(?:npm|yarn|pnpm|bun)\s+(?:run\s+)?tests?\b|"
    r"go\s+test|cargo\s+test|mvn\s+test|gradle(?:w)?\s+test|"
    r"rspec|bundle\s+exec\s+rspec|phpunit|dotnet\s+test|flutter\s+test|"
    r"ctest|rake\s+test|mix\s+test|swift\s+test"
    # El lookahead evita los falsos positivos de rutas y paquetes que contienen
    # el nombre de un runner (`/tmp/pytest-of-user/`, `pytest-cov`), sin perder
    # las invocaciones por ruta absoluta (`/usr/bin/pytest tests`).
    r")(?![-\w/])",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Configuración y rutas
# --------------------------------------------------------------------------- #


def tracking_enabled(cwd: Optional[str] = None) -> bool:
    """`gitflow-es.timeTracking` (default on)."""
    if _gitwt is None:
        return False
    return _gitwt.flag_enabled("timeTracking", default=True, cwd=cwd)


def notes_mode(cwd: Optional[str] = None) -> str:
    """`gitflow-es.timeNotes`: on (default) | commits | off."""
    if _gitwt is None:
        return "off"
    value = (_gitwt.config_get("timeNotes", cwd) or "on").strip().lower()
    if value in ("off", "false", "0", "no"):
        return "off"
    if value == "commits":
        return "commits"
    return "on"


def evidence_enabled(cwd: Optional[str] = None) -> bool:
    """`gitflow-es.evidence` (default on)."""
    if _gitwt is None:
        return False
    return _gitwt.flag_enabled("evidence", default=True, cwd=cwd)


def idle_threshold(cwd: Optional[str] = None) -> int:
    if _gitwt is None:
        return DEFAULT_IDLE_THRESHOLD
    return _gitwt.config_int("idleThresholdMin", DEFAULT_IDLE_THRESHOLD // 60, cwd) * 60


def evidence_gap(cwd: Optional[str] = None) -> int:
    if _gitwt is None:
        return DEFAULT_EVIDENCE_GAP
    return _gitwt.config_int("externalGapMin", DEFAULT_EVIDENCE_GAP // 60, cwd) * 60


def evidence_margin(cwd: Optional[str] = None) -> int:
    if _gitwt is None:
        return DEFAULT_EVIDENCE_MARGIN
    return _gitwt.config_int("externalMargin", DEFAULT_EVIDENCE_MARGIN // 60, cwd) * 60


def test_pattern(cwd: Optional[str] = None):
    """Regex de comandos de test, con el patrón extra del proyecto si existe."""
    extra = _gitwt.config_get("testPattern", cwd) if _gitwt else None
    if not extra:
        return TEST_COMMAND_RE
    try:
        return re.compile(
            "(?:{0})|(?:{1})".format(TEST_COMMAND_RE.pattern, extra),
            re.IGNORECASE,
        )
    except re.error:
        return TEST_COMMAND_RE


def is_test_command(command: str, cwd: Optional[str] = None) -> bool:
    if not command:
        return False
    return bool(test_pattern(cwd).search(command))


def sanitize_branch(branch: str) -> str:
    """Nombre de archivo seguro para una rama (`feature/x` → `feature__x`)."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "__", (branch or "sin-rama").strip())
    return safe[:100] or "sin-rama"


def log_dir(cwd: Optional[str] = None) -> Optional[str]:
    """`<git-common-dir>/gitflow-es/tiempos/`, creado si hace falta."""
    if _gitwt is None:
        return None
    override = _gitwt.config_get("timeLogDir", cwd)
    if override:
        path = os.path.expanduser(override)
    else:
        state = _gitwt.plugin_state_dir(cwd)
        if not state:
            return None
        path = os.path.join(state, "tiempos")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path


def log_path(branch: str, cwd: Optional[str] = None) -> Optional[str]:
    directory = log_dir(cwd)
    if not directory:
        return None
    return os.path.join(directory, "{0}.jsonl".format(sanitize_branch(branch)))


def known_branches(cwd: Optional[str] = None) -> List[str]:
    """Ramas con registro, ordenadas por última actividad (más reciente primero)."""
    directory = log_dir(cwd)
    if not directory:
        return []
    try:
        files = [f for f in os.listdir(directory) if f.endswith(".jsonl")]
    except OSError:
        return []

    branches = []
    for name in files:
        path = os.path.join(directory, name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        events = read_events_file(path)
        branch = events[0].get("b") if events else name[:-6]
        branches.append((mtime, branch or name[:-6]))
    return [branch for _, branch in sorted(branches, reverse=True)]


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #


def clean_note(note: Optional[str]) -> str:
    """Una línea, sin caracteres de control, truncada. Vacío si no hay nota."""
    if not note:
        return ""
    single = " ".join(str(note).split())
    single = "".join(ch for ch in single if ch == " " or ch.isprintable())
    if len(single) > MAX_NOTE_CHARS:
        single = single[: MAX_NOTE_CHARS - 1].rstrip() + "…"
    return single


def append_event(branch: str, event: str, cwd: Optional[str] = None, **fields) -> bool:
    """
    Agrega un evento al log de `branch`. Devuelve True si se escribió.

    La línea se escribe con un solo `os.write` sobre un descriptor en O_APPEND:
    es lo que permite que varias sesiones y worktrees registren en paralelo sin
    pisarse.
    """
    path = log_path(branch, cwd)
    if not path:
        return False

    now = time.time()
    record: Dict[str, Any] = {
        "t": round(now, 3),
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "e": event,
        "b": branch,
    }
    for key, value in fields.items():
        if value is None or value == "":
            continue
        record[key] = value

    if "n" in record:
        record["n"] = clean_note(record["n"])
        if not record["n"]:
            del record["n"]

    try:
        line = json.dumps(record, ensure_ascii=False)
    except (TypeError, ValueError):
        return False

    data = (line + "\n").encode("utf-8")
    if len(data) > MAX_LINE_BYTES:
        # Recortar la nota antes que perder el evento entero.
        record.pop("n", None)
        data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        if len(data) > MAX_LINE_BYTES:
            return False

    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
    except OSError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Lectura
# --------------------------------------------------------------------------- #


def read_events_file(path: str) -> List[Dict[str, Any]]:
    """Lee un JSONL ignorando líneas corruptas (una escritura a medias no rompe)."""
    events: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(record, dict) and "t" in record:
                    events.append(record)
    except OSError:
        return []
    events.sort(key=lambda r: r.get("t", 0))
    return events


def read_events(branch: str, cwd: Optional[str] = None) -> List[Dict[str, Any]]:
    path = log_path(branch, cwd)
    if not path or not os.path.exists(path):
        return []
    return read_events_file(path)


# --------------------------------------------------------------------------- #
# Intervalos
# --------------------------------------------------------------------------- #

Interval = Tuple[float, float]


def _clip(intervals: Iterable[Interval], start: float, end: float) -> List[Interval]:
    out = []
    for a, b in intervals:
        a2, b2 = max(a, start), min(b, end)
        if b2 > a2:
            out.append((a2, b2))
    return out


def _merge(intervals: Sequence[Interval]) -> List[Interval]:
    ordered = sorted(i for i in intervals if i[1] > i[0])
    merged: List[Interval] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract(base: Sequence[Interval], holes: Sequence[Interval]) -> List[Interval]:
    result = list(base)
    for hole_start, hole_end in _merge(holes):
        nuevo: List[Interval] = []
        for start, end in result:
            if hole_end <= start or hole_start >= end:
                nuevo.append((start, end))
                continue
            if start < hole_start:
                nuevo.append((start, hole_start))
            if hole_end < end:
                nuevo.append((hole_end, end))
        result = nuevo
    return [i for i in result if i[1] > i[0]]


def _intersect(a: Sequence[Interval], b: Sequence[Interval]) -> List[Interval]:
    out: List[Interval] = []
    for a_start, a_end in a:
        for b_start, b_end in b:
            start, end = max(a_start, b_start), min(a_end, b_end)
            if end > start:
                out.append((start, end))
    return _merge(out)


def _duration(intervals: Sequence[Interval]) -> float:
    return sum(end - start for start, end in intervals)


# --------------------------------------------------------------------------- #
# Evidencia
# --------------------------------------------------------------------------- #


def scan_evidence(worktree: str, since: float = 0.0, limit: int = 200) -> List[Tuple[str, float]]:
    """
    Archivos con cambios según git y su `mtime`, más nuevos que `since`.

    Se apoya en `git status --porcelain`, así que respeta `.gitignore`: los
    artefactos de build y `node_modules` quedan afuera por construcción, sin
    tener que mantener listas de exclusión.
    """
    if _gitwt is None or not worktree:
        return []
    raw = _gitwt.run_git(["status", "--porcelain", "-z"], cwd=worktree, timeout=5)
    if not raw:
        return []

    found: List[Tuple[str, float]] = []
    now = time.time()
    for entry in raw.split("\0"):
        # Formato: `XY ruta`. No se corta por offset fijo porque la salida puede
        # llegar sin el espacio inicial del código de estado (" M a.txt").
        match = STATUS_ENTRY_RE.match(entry)
        if not match:
            continue
        relative = match.group("path").strip()
        if not relative:
            continue
        full = os.path.join(worktree, relative)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        # Un mtime en el futuro (reloj desfasado) se recorta a "ahora".
        mtime = min(mtime, now)
        if mtime > since:
            found.append((relative, mtime))
        if len(found) >= limit:
            break
    return found


def _drop_bulk_writes(evidence: Sequence[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """
    Descarta escrituras masivas: 20+ archivos en una ventana de 2 s es un
    checkout, un `worktree add` o un build reescribiendo el árbol, no trabajo.
    """
    ordered = sorted(evidence, key=lambda item: item[1])
    keep = [True] * len(ordered)

    start = 0
    for index in range(len(ordered)):
        while ordered[index][1] - ordered[start][1] > BULK_WRITE_WINDOW:
            start += 1
        if index - start + 1 >= BULK_WRITE_FILES:
            for pos in range(start, index + 1):
                keep[pos] = False
    return [item for item, keep_it in zip(ordered, keep) if keep_it]


def evidence_clusters(
    timestamps: Sequence[float],
    gap: int = DEFAULT_EVIDENCE_GAP,
    margin: int = DEFAULT_EVIDENCE_MARGIN,
) -> List[Interval]:
    """
    Agrupa timestamps de evidencia en intervalos de actividad. Un timestamp
    aislado aporta `2 × margin`; un clúster, de su primero menos margen a su
    último más margen.
    """
    ordered = sorted(timestamps)
    if not ordered:
        return []

    clusters: List[Interval] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value - previous > gap:
            clusters.append((start - margin, previous + margin))
            start = value
        previous = value
    clusters.append((start - margin, previous + margin))
    return _merge(clusters)


# --------------------------------------------------------------------------- #
# Agregación
# --------------------------------------------------------------------------- #


def aggregate(
    events: Sequence[Dict[str, Any]],
    now: Optional[float] = None,
    threshold: int = DEFAULT_IDLE_THRESHOLD,
    gap: int = DEFAULT_EVIDENCE_GAP,
    margin: int = DEFAULT_EVIDENCE_MARGIN,
    commit_times: Optional[Sequence[float]] = None,
    use_evidence: bool = True,
) -> Dict[str, Any]:
    """
    Calcula los rubros de una rama a partir de sus eventos.

    Devuelve duraciones en segundos. Los rubros parten la línea de tiempo, así
    que `trabajo + trabajo_externo + pruebas + espera + inactividad == total`.
    """
    empty = {
        "branch": None, "description": "", "start": None, "end": None,
        "total": 0.0, "work": 0.0, "external": 0.0, "tests": 0.0,
        "wait": 0.0, "idle": 0.0, "idle_user": 0.0, "idle_session": 0.0,
        "sessions": 0, "turns": 0, "test_runs": 0, "test_ok": 0, "test_failed": 0,
        "evidence_files": 0, "evidence_commits": 0, "estimated": False,
        "closed": False, "stale": False, "activities": [],
    }
    if not events:
        return empty

    now = now if now is not None else time.time()
    ordered = sorted(events, key=lambda r: r.get("t", 0))
    start = ordered[0]["t"]
    last = ordered[-1]["t"]

    finish = next((e for e in reversed(ordered) if e.get("e") == "branch_finish"), None)
    closed = finish is not None
    stale = False
    if closed:
        end = finish["t"]
    elif now - last > STALE_AFTER:
        end = last + threshold
        stale = True
    else:
        end = max(now, last)
    if end <= start:
        end = start + 1.0

    # --- ventanas de trabajo (prompt → stop) ---------------------------------
    work_windows: List[Interval] = []
    activities: List[Dict[str, Any]] = []
    turns = 0
    open_prompt: Optional[Dict[str, Any]] = None
    for event in ordered:
        kind = event.get("e")
        if kind == "prompt":
            if open_prompt is not None:
                work_windows.append((open_prompt["t"], event["t"]))
                activities.append({"start": open_prompt["t"], "end": event["t"],
                                   "note": open_prompt.get("n", ""), "commits": []})
            open_prompt = event
            turns += 1
        elif kind in ("stop", "session_end", "branch_finish") and open_prompt is not None:
            work_windows.append((open_prompt["t"], event["t"]))
            activities.append({"start": open_prompt["t"], "end": event["t"],
                               "note": open_prompt.get("n", ""), "commits": []})
            open_prompt = None
    estimated = False
    if open_prompt is not None:
        # La sesión se cortó sin `stop`: la ventana se cierra en el último evento.
        close_at = max(last, open_prompt["t"])
        work_windows.append((open_prompt["t"], close_at))
        activities.append({"start": open_prompt["t"], "end": close_at,
                           "note": open_prompt.get("n", ""), "commits": []})
        estimated = True

    work_windows = _clip(_merge(work_windows), start, end)

    # --- intervalos de pruebas (pareados por tool_use_id) --------------------
    test_intervals: List[Interval] = []
    pending: Dict[str, Dict[str, Any]] = {}
    orphan_order: List[Dict[str, Any]] = []
    test_ok = test_failed = 0
    for event in ordered:
        kind = event.get("e")
        if kind == "test_start":
            key = event.get("id")
            if key:
                pending[key] = event
            else:
                orphan_order.append(event)
        elif kind == "test_end":
            key = event.get("id")
            begin = pending.pop(key, None) if key else None
            if begin is None and orphan_order:
                begin = orphan_order.pop(0)
            if begin is None:
                continue
            test_intervals.append((begin["t"], event["t"]))
            if event.get("ok", True):
                test_ok += 1
            else:
                test_failed += 1

    # Un test que nunca cerró (sesión caída): se corta en el siguiente evento.
    for leftover in list(pending.values()) + orphan_order:
        following = [e["t"] for e in ordered if e["t"] > leftover["t"]]
        test_intervals.append((leftover["t"], following[0] if following else end))
        estimated = True

    test_intervals = _clip(_merge(test_intervals), start, end)
    test_runs = test_ok + test_failed + len(pending) + len(orphan_order)

    # --- huecos: lo que no es trabajo ni pruebas ------------------------------
    covered = _merge(list(work_windows) + list(test_intervals))
    gaps = _subtract([(start, end)], covered)

    wait_intervals: List[Interval] = []
    idle_user_intervals: List[Interval] = []
    idle_session_intervals: List[Interval] = []

    prompt_times = {round(e["t"], 3) for e in ordered if e.get("e") == "prompt"}
    for gap_start, gap_end in gaps:
        # Un hueco que termina en un `prompt` es espera del usuario; el resto es
        # inactividad de sesión (sesión cerrada, pausa larga, etc.).
        espera = round(gap_end, 3) in prompt_times
        if espera:
            limit = min(gap_end, gap_start + threshold)
            wait_intervals.append((gap_start, limit))
            if gap_end > limit:
                idle_user_intervals.append((limit, gap_end))
        else:
            idle_session_intervals.append((gap_start, gap_end))

    # --- evidencia: reclasificar huecos con actividad real -------------------
    evidence_points: List[Tuple[str, float]] = [
        (event.get("p", ""), event["t"] if event.get("m") is None else float(event["m"]))
        for event in ordered
        if event.get("e") == "evidence"
    ]
    evidence_points = [(p, m) for p, m in evidence_points if m <= now]
    evidence_files = len({p for p, _ in evidence_points if p})
    # Un mismo commit aparece dos veces: como evento registrado en vivo y como
    # timestamp de `git log`. Para las marcas de evidencia da igual (caen en el
    # mismo clúster), pero el conteo que se reporta toma una sola fuente.
    commit_events = [e["t"] for e in ordered if e.get("e") == "commit"]
    commit_log = list(commit_times or [])
    commit_points = sorted(set(round(v, 3) for v in commit_log + commit_events))
    commit_count = len(commit_log) if commit_log else len(commit_events)

    # Los eventos `activity` son observación directa (la sesión operó sobre el
    # worktree de esta rama desde otra), así que valen aunque la validación por
    # evidencia esté apagada.
    activity_points = [e["t"] for e in ordered if e.get("e") == "activity"]

    external_intervals: List[Interval] = []
    marks: List[float] = list(activity_points)
    if use_evidence:
        marks += [m for _, m in _drop_bulk_writes(evidence_points)]
        marks += commit_points

    if marks:
        clusters = evidence_clusters(marks, gap=gap, margin=margin)
        gap_intervals = wait_intervals + idle_user_intervals + idle_session_intervals
        external_intervals = _intersect(_merge(gap_intervals), clusters)
        wait_intervals = _subtract(wait_intervals, external_intervals)
        idle_user_intervals = _subtract(idle_user_intervals, external_intervals)
        idle_session_intervals = _subtract(idle_session_intervals, external_intervals)

    # --- descripción y commits por actividad ---------------------------------
    description = ""
    for event in ordered:
        if event.get("e") in ("branch_start", "describe") and event.get("n"):
            description = event["n"]
    commits = [e for e in ordered if e.get("e") == "commit"]
    for activity in activities:
        activity["commits"] = [
            c.get("n", "") for c in commits
            if activity["start"] <= c["t"] <= activity["end"] and c.get("n")
        ]
        activity["duration"] = max(0.0, activity["end"] - activity["start"])

    work_only = _subtract(work_windows, test_intervals)

    result = dict(empty)
    result.update({
        "branch": ordered[0].get("b"),
        "description": description,
        "start": start,
        "end": end,
        "total": end - start,
        "work": _duration(work_only),
        "tests": _duration(test_intervals),
        "external": _duration(external_intervals),
        "wait": _duration(wait_intervals),
        "idle_user": _duration(idle_user_intervals),
        "idle_session": _duration(idle_session_intervals),
        "sessions": len([e for e in ordered if e.get("e") == "session_start"]),
        "turns": turns,
        "test_runs": test_runs,
        "test_ok": test_ok,
        "test_failed": test_failed,
        "evidence_files": evidence_files,
        "evidence_commits": commit_count,
        "estimated": estimated,
        "closed": closed,
        "stale": stale,
        "activities": [a for a in activities if a["duration"] > 0],
    })
    result["idle"] = result["idle_user"] + result["idle_session"]
    result["effective"] = result["work"] + result["tests"]
    result["wait_total"] = result["wait"] + result["idle_user"]
    return result


# --------------------------------------------------------------------------- #
# Presentación
# --------------------------------------------------------------------------- #


def format_duration(seconds: float) -> str:
    """Duración legible: `2h 14m`, `45m`, `38s`."""
    seconds = max(0, int(round(seconds or 0)))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "{0}h {1:02d}m".format(hours, minutes)
    if minutes:
        return "{0}m".format(minutes)
    return "{0}s".format(secs)


def format_moment(epoch: Optional[float]) -> str:
    if not epoch:
        return "—"
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")


def quick_summary(branch: str, lang: str = "es", cwd: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Resumen corto para el hook de contexto. None si no hay datos."""
    events = read_events(branch, cwd)
    if not events:
        return None
    data = aggregate(
        events,
        threshold=idle_threshold(cwd),
        gap=evidence_gap(cwd),
        margin=evidence_margin(cwd),
        use_evidence=evidence_enabled(cwd),
    )
    return {
        "total": format_duration(data["total"]),
        "work": format_duration(data["work"] + data["external"]),
        "tests": format_duration(data["tests"]),
        "dead": format_duration(data["wait"] + data["idle"]),
    }


def collect_commit_times(branch: str, base: Optional[str] = None, cwd: Optional[str] = None) -> List[float]:
    """
    Timestamps de los commits de la rama. Sirven de evidencia incluso para
    commits hechos fuera de Claude.
    """
    if _gitwt is None or not branch:
        return []
    base = base or _gitwt.develop_branch(cwd)
    raw = _gitwt.run_git(["log", "--format=%ct", "{0}..{1}".format(base, branch)], cwd=cwd)
    if not raw:
        return []
    times = []
    for line in raw.splitlines():
        try:
            times.append(float(line.strip()))
        except ValueError:
            continue
    return times


def branch_report_data(branch: str, cwd: Optional[str] = None, now: Optional[float] = None) -> Dict[str, Any]:
    """Agregación completa de una rama, con la evidencia de commits incluida."""
    events = read_events(branch, cwd)
    return aggregate(
        events,
        now=now,
        threshold=idle_threshold(cwd),
        gap=evidence_gap(cwd),
        margin=evidence_margin(cwd),
        commit_times=collect_commit_times(branch, cwd=cwd) if evidence_enabled(cwd) else None,
        use_evidence=evidence_enabled(cwd),
    )


def calendar_time(reports: Sequence[Dict[str, Any]]) -> float:
    """
    Tiempo de calendario del conjunto: unión de los intervalos de cada rama. Con
    trabajo en paralelo es menor que la suma por rama.
    """
    intervals = [
        (r["start"], r["end"]) for r in reports
        if r.get("start") is not None and r.get("end") is not None
    ]
    return _duration(_merge(intervals))
