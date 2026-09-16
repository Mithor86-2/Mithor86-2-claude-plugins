#!/usr/bin/env python3
"""
gitflow-es — reporte del registro de tiempos.

    time-report.py                      # rama actual, markdown
    time-report.py --branch feature/x
    time-report.py --all                # todas las ramas con registro
    time-report.py --format json

Lo consume el skill `tiempos`; también sirve suelto desde la terminal.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import gitwt
    import i18n
    import timelog
except Exception as error:  # pragma: no cover - instalación incompleta
    print("gitflow-es: no se pudieron cargar los módulos del plugin ({0})".format(error),
          file=sys.stderr)
    sys.exit(1)


def _t(key: str, lang: str, **kwargs) -> str:
    return i18n.t(key, lang, **kwargs)


def _pct(value: float, total: float) -> str:
    if not total:
        return "0%"
    return "{0}%".format(int(round(100.0 * value / total)))


def render_branch(data: Dict[str, Any], lang: str, cwd: Optional[str] = None) -> str:
    """Reporte markdown de una rama."""
    if not data or not data.get("start"):
        return _t("tr_no_data", lang, branch=data.get("branch") or "?")

    fmt = timelog.format_duration
    total = data["total"]
    lines: List[str] = []

    lines.append(_t("tr_title", lang, branch=data["branch"]))
    lines.append("")
    if data.get("description"):
        lines.append(_t("tr_description", lang, description=data["description"]))
    else:
        lines.append(_t("tr_no_description", lang))

    end = timelog.format_moment(data["end"]) if data.get("closed") else _t("tr_in_progress", lang)
    lines.append(_t("tr_period", lang,
                    start=timelog.format_moment(data["start"]),
                    end=end,
                    total=fmt(total)))
    lines.append("")

    filas = [
        (_t("tr_bucket_work", lang), data["work"]),
        (_t("tr_bucket_external", lang), data["external"]),
        (_t("tr_bucket_tests", lang), data["tests"]),
        (_t("tr_bucket_approval", lang), data["approval"]),
        (_t("tr_bucket_wait", lang), data["wait"]),
        (_t("tr_bucket_idle", lang), data["idle"]),
    ]
    lines.append(_t("tr_bucket_header", lang))
    lines.append("|---|---|---|")
    for etiqueta, valor in filas:
        lines.append("| {0} | {1} | {2} |".format(etiqueta, fmt(valor), _pct(valor, total)))
    lines.append("")

    lines.append(_t("tr_effective", lang,
                    effective=fmt(data["effective"]),
                    wait_total=fmt(data["wait_total"])))
    lines.append(_t("tr_counters", lang,
                    sessions=data["sessions"], turns=data["turns"],
                    tests=data["test_runs"], ok=data["test_ok"], failed=data["test_failed"]))

    muertos = data["wait"] + data["idle"]
    if data["external"] > 0:
        lines.append(_t("tr_dead_validated", lang,
                        confirmed=fmt(muertos), external=fmt(data["external"]),
                        files=data["evidence_files"], commits=data["evidence_commits"]))
    else:
        lines.append(_t("tr_dead_no_evidence", lang, confirmed=fmt(muertos)))

    if not timelog.evidence_enabled(cwd):
        lines.append(_t("tr_evidence_off", lang))
    if data.get("estimated"):
        lines.append(_t("tr_estimated", lang))

    actividades = [a for a in data.get("activities", []) if a.get("note") or a.get("commits")]
    if actividades:
        lines.append("")
        lines.append(_t("tr_activity_title", lang))
        lines.append("")
        lines.append(_t("tr_activity_header", lang))
        lines.append("|---|---|---|---|")
        for actividad in actividades:
            commits = " · ".join(actividad.get("commits") or []) or "—"
            lines.append("| {0} | {1} | {2} | {3} |".format(
                timelog.format_moment(actividad["start"])[-5:],
                fmt(actividad["duration"]),
                actividad.get("note") or "—",
                commits,
            ))

    return "\n".join(lines)


def render_all(reports: List[Dict[str, Any]], lang: str) -> str:
    """Tabla comparativa de todas las ramas con registro."""
    if not reports:
        return _t("tr_no_data", lang, branch="*")

    fmt = timelog.format_duration
    lines = [_t("tr_all_title", lang), "", _t("tr_all_header", lang), "|---|---|---|---|---|---|"]
    for data in reports:
        estado = _t("tr_closed", lang) if data.get("closed") else _t("tr_open", lang)
        lines.append("| `{0}` | {1} | {2} | {3} | {4} | {5} |".format(
            data["branch"], fmt(data["total"]),
            fmt(data["work"] + data["external"]), fmt(data["tests"]),
            fmt(data["wait"] + data["idle"]), estado,
        ))

    lines.append("")
    lines.append(_t("tr_calendar", lang, calendar=fmt(timelog.calendar_time(reports))))
    return "\n".join(lines)


def main() -> int:
    argv = sys.argv[1:]
    branch = None
    todas = False
    formato = "md"
    lang = None

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--branch" and index + 1 < len(argv):
            branch = argv[index + 1]
            index += 1
        elif arg in ("--all", "--todas"):
            todas = True
        elif arg == "--format" and index + 1 < len(argv):
            formato = argv[index + 1]
            index += 1
        elif arg == "--lang" and index + 1 < len(argv):
            lang = argv[index + 1]
            index += 1
        index += 1

    cwd = os.getcwd()
    lang = lang if lang in ("es", "en") else i18n.detect_lang(cwd)

    if todas:
        reports = [timelog.branch_report_data(b, cwd) for b in timelog.known_branches(cwd)]
        reports = [r for r in reports if r.get("start")]
        if formato == "json":
            print(json.dumps(reports, ensure_ascii=False, indent=2))
        else:
            print(render_all(reports, lang))
        return 0

    branch = branch or gitwt.current_branch(cwd)
    if not branch:
        print(_t("tr_no_data", lang, branch="?"))
        return 0

    data = timelog.branch_report_data(branch, cwd)
    if formato == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_branch(data, lang, cwd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
