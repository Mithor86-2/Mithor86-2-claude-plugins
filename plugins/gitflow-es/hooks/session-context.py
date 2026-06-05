#!/usr/bin/env python3
"""
gitflow-es context hook (SessionStart).

Imprime un resumen del estado git al inicio de cada sesión. Solo informativo —
nunca bloquea nada. La salida se inyecta en el contexto para que Claude arranque
sabiendo en qué rama está el usuario, si hay cambios pendientes, etc.

Si no estamos en un repo git, no imprime nada (salida vacía).
"""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional

# Módulo i18n compartido (mismo directorio → resuelto vía sys.path[0]). Import
# defensivo: si fallara, _t cae a español embebido y el hook sigue funcionando.
try:
    import i18n as _i18n
except Exception:  # pragma: no cover - ruta de degradación
    _i18n = None

_LANG = "es"


def _t(key: str, **kwargs) -> str:
    """Traduce `key` al idioma activo, con fallback a la clave cruda si falla."""
    if _i18n is not None:
        return _i18n.t(key, _LANG, **kwargs)
    return ""


def run(cmd: List[str]) -> Optional[str]:
    """Ejecuta un comando y devuelve stdout, o None si falla."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def in_git_repo() -> bool:
    return run(["git", "rev-parse", "--is-inside-work-tree"]) == "true"


def gitflow_initialized() -> bool:
    """True si el repo tiene git-flow inicializado (config gitflow.branch.develop)."""
    return bool(run(["git", "config", "--get", "gitflow.branch.develop"]))


def repo_has_commits() -> bool:
    """True si el repo tiene al menos un commit."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def branch_type(branch: str) -> Optional[str]:
    """Detecta el tipo GitFlow a partir del prefijo."""
    prefixes = {
        "feature/": "feature",
        "fix/": "fix",
        "hotfix/": "hotfix",
        "release/": "release",
        "refactor/": "refactor",
        "chore/": "chore",
    }
    for prefix, kind in prefixes.items():
        if branch.startswith(prefix):
            return kind
    return None


def ahead_behind(branch: str) -> Optional[tuple]:
    """Devuelve (ahead, behind) respecto a origin/<branch>, o None si no aplica."""
    if not branch:
        return None
    upstream = run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"])
    if not upstream:
        return None
    counts = run(["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"])
    if not counts:
        return None
    parts = counts.split()
    if len(parts) != 2:
        return None
    try:
        behind, ahead = int(parts[0]), int(parts[1])
        return ahead, behind
    except ValueError:
        return None


def main() -> None:
    global _LANG
    if _i18n is not None:
        try:
            _LANG = _i18n.detect_lang()
        except Exception:
            _LANG = "es"

    if not in_git_repo():
        return  # Sin salida = no se inyecta nada

    # Caso especial: repo recién inicializado sin commits.
    # No tiene sentido mostrar "rama actual" con ahead/behind; guiamos al
    # usuario hacia el primer commit y luego hacia `git flow init -d`.
    if not repo_has_commits():
        out = [
            _t("sc_header"),
            "",
            _t("sc_no_commits_title"),
            "",
            _t("sc_no_commits_body"),
            "",
            _t("sc_no_commits_flow_label"),
            "",
            "```bash",
            "git add .",
            'git commit -m "chore: initial commit"',
            "git flow init -d",
            "```",
            "",
            _t("sc_no_commits_note"),
        ]
        print("\n".join(out))
        return

    branch = run(["git", "branch", "--show-current"]) or "(detached HEAD)"
    kind = branch_type(branch)
    status_lines = run(["git", "status", "--porcelain"]) or ""
    num_changes = len([l for l in status_lines.splitlines() if l.strip()])

    out = []
    out.append(_t("sc_header"))
    out.append("")
    out.append(_t("sc_current_branch", branch=branch))

    if branch in {"main", "master", "develop"}:
        out.append(_t("sc_on_protected", branch=branch))
    elif kind:
        out.append(_t("sc_branch_type", kind=kind))
    elif branch != "(detached HEAD)":
        out.append(_t("sc_unknown_prefix"))

    if num_changes > 0:
        out.append(_t("sc_pending_changes", count=num_changes))
    else:
        out.append(_t("sc_clean_tree"))

    ab = ahead_behind(branch)
    if ab is not None:
        ahead, behind = ab
        if ahead == 0 and behind == 0:
            out.append(_t("sc_synced"))
        elif ahead > 0 and behind == 0:
            out.append(_t("sc_ahead", ahead=ahead))
        elif behind > 0 and ahead == 0:
            out.append(_t("sc_behind", behind=behind))
        else:
            out.append(_t("sc_diverged", ahead=ahead, behind=behind))

    # Aviso si git-flow no está inicializado (tono proactivo: Claude puede
    # ofrecer correr `git flow init -d` después de pedir OK al usuario).
    if not gitflow_initialized():
        out.append("")
        out.append(_t("sc_no_gitflow_title"))
        out.append(_t("sc_no_gitflow_body"))
        out.append("")
        out.append(_t("sc_no_gitflow_action"))
        out.append("")
        out.append("```bash")
        out.append("git flow init -d")
        out.append("```")
        out.append("")
        out.append(_t("sc_no_gitflow_explain"))

    print("\n".join(out))


if __name__ == "__main__":
    main()
