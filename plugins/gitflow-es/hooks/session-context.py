#!/usr/bin/env python3
"""
gitflow-es context hook (SessionStart).

Imprime un resumen del estado git al inicio de cada sesión. Solo informativo —
nunca bloquea nada. La salida se inyecta en el contexto para que Claude arranque
sabiendo en qué rama está el usuario, en qué worktree, si hay cambios pendientes
y qué configuración del plugin falta.

Si no estamos en un repo git, no imprime nada (salida vacía).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# Módulo i18n compartido (mismo directorio → resuelto vía sys.path[0]). Import
# defensivo: si fallara, _t cae a cadena vacía y el hook sigue funcionando.
try:
    import i18n as _i18n
except Exception:  # pragma: no cover - ruta de degradación
    _i18n = None

# El registro de tiempos es opcional: si el módulo no está (instalación parcial)
# la línea de tiempos simplemente no aparece.
try:
    import timelog as _timelog
except Exception:  # pragma: no cover - ruta de degradación
    _timelog = None

_LANG = "es"

PROTECTED = {"main", "master", "develop"}

# Tope de worktrees listados: en repos con muchas ramas paralelas el bloque de
# contexto no debe convertirse en una pared de texto.
MAX_WORKTREES_LISTED = 8


def _t(key: str, **kwargs) -> str:
    """Traduce `key` al idioma activo, con fallback a cadena vacía si falla."""
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


def config_get(key: str) -> Optional[str]:
    """Lee `git config --get gitflow-es.<key>`; None si no está configurada."""
    value = run(["git", "config", "--get", "gitflow-es.{0}".format(key)])
    return value or None


def lang_set() -> bool:
    """
    True si el idioma de gitflow-es ya está configurado explícitamente. Si el
    módulo i18n no está disponible, devolvemos True para no nag-ear sin razón.
    """
    if _i18n is None:
        return True
    try:
        return _i18n.lang_explicitly_set()
    except Exception:
        return True


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


def is_linked_worktree() -> bool:
    """
    True si el cwd está en un worktree *linked* (creado con `git worktree add`)
    y no en el worktree principal — el que llamamos "de control".

    En un worktree linked `--git-dir` apunta a `.git/worktrees/<nombre>`,
    mientras `--git-common-dir` sigue apuntando al `.git` principal.
    """
    git_dir = run(["git", "rev-parse", "--absolute-git-dir"])
    common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"])
    if not git_dir or not common:
        return False
    return os.path.normpath(git_dir) != os.path.normpath(common)


def worktrees() -> List[Tuple[str, str]]:
    """
    Devuelve [(rama, ruta)] de todos los worktrees del repo. La rama es el nombre
    corto, o "(detached)" si el worktree está en HEAD desacoplado.
    """
    raw = run(["git", "worktree", "list", "--porcelain"])
    if not raw:
        return []

    found: List[Tuple[str, str]] = []
    path: Optional[str] = None
    branch = "(detached)"
    for line in raw.splitlines() + [""]:
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip()
            branch = "(detached)"
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            branch = ref.replace("refs/heads/", "", 1)
        elif not line.strip() and path:
            found.append((branch, path))
            path = None
    return found


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
    upstream = run(["git", "rev-parse", "--abbrev-ref", "{0}@{{upstream}}".format(branch)])
    if not upstream:
        return None
    counts = run(["git", "rev-list", "--left-right", "--count", "{0}...HEAD".format(upstream)])
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


def config_checklist() -> List[str]:
    """
    Checklist de configuración del plugin: qué está listo y qué falta. Se muestra
    solo cuando hay algo accionable (git-flow o idioma sin configurar), para no
    repetir lo mismo en cada sesión de un repo ya configurado.
    """
    items = [
        (gitflow_initialized(), _t("sc_config_gitflow")),
        (lang_set(), _t("sc_config_lang")),
        (bool(config_get("worktreeRoot")), _t("sc_config_worktree_root")),
        (bool(config_get("timeTracking")), _t("sc_config_time")),
    ]
    lines = [_t("sc_config_title"), ""]
    for ok, label in items:
        key = "sc_config_ok" if ok else "sc_config_pending"
        lines.append(_t(key, item=label))
    lines.append("")
    lines.append(_t("sc_config_action"))
    return lines


def time_summary_line(branch: str) -> Optional[str]:
    """
    Línea de tiempos acumulados de la rama actual. Silenciosa si el registro está
    apagado, si el módulo no está disponible o si todavía no hay datos: el hook de
    contexto informa, no insiste.
    """
    if _timelog is None or not branch:
        return None
    try:
        if not _timelog.tracking_enabled():
            return None
        summary = _timelog.quick_summary(branch, lang=_LANG)
    except Exception:
        return None
    if not summary:
        return None
    return _t(
        "sc_time_line",
        total=summary["total"],
        work=summary["work"],
        tests=summary["tests"],
        idle=summary["dead"],
    )


def build_output() -> str:
    """Construye el bloque de contexto completo. Cadena vacía = no se inyecta nada."""
    if not in_git_repo():
        return ""

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
            "",
            _t("sc_lang_after_init"),
        ]
        return "\n".join(out)

    branch = run(["git", "branch", "--show-current"]) or "(detached HEAD)"
    kind = branch_type(branch)
    status_lines = run(["git", "status", "--porcelain"]) or ""
    num_changes = len([l for l in status_lines.splitlines() if l.strip()])
    linked = is_linked_worktree()

    out = []
    out.append(_t("sc_header"))
    out.append("")
    out.append(_t("sc_current_branch", branch=branch))

    if branch in PROTECTED:
        # En modo worktree el worktree principal queda parado en `develop` y se
        # usa solo para cerrar ramas: el aviso correcto no es "estás en main"
        # sino "este es el worktree de control".
        out.append(_t("sc_worktree_control") if not linked else _t("sc_on_protected", branch=branch))
    elif kind:
        out.append(_t("sc_branch_type", kind=kind))
    elif branch != "(detached HEAD)":
        out.append(_t("sc_unknown_prefix"))

    if linked:
        # La raíz del worktree, no el cwd: el usuario puede haber abierto la
        # sesión en un subdirectorio del worktree.
        out.append(_t("sc_worktree_linked", path=run(["git", "rev-parse", "--show-toplevel"]) or os.getcwd()))

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

    time_line = time_summary_line(branch)
    if time_line:
        out.append(time_line)

    # Worktrees activos: solo tiene sentido listarlos cuando hay más de uno.
    trees = worktrees()
    if len(trees) > 1:
        out.append(_t("sc_worktrees_title", count=len(trees)))
        for wt_branch, wt_path in trees[:MAX_WORKTREES_LISTED]:
            out.append(_t("sc_worktrees_item", branch=wt_branch, path=wt_path))

    # Aviso si git-flow no está inicializado (tono proactivo: Claude puede
    # ofrecer correr `/git init` después de pedir OK al usuario).
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
        out.append("")
        out.extend(config_checklist())
    elif not lang_set():
        # git-flow ya inicializado pero el idioma no está configurado: pedirlo
        # antes de cualquier acción de git.
        out.append("")
        out.append(_t("sc_lang_prompt_title"))
        out.append(_t("sc_lang_prompt_body"))
        out.append("")
        out.append("```bash")
        out.append("git config gitflow-es.language es   # o: en")
        out.append("```")
        out.append("")
        out.append(_t("sc_lang_prompt_note"))
        out.append("")
        out.extend(config_checklist())

    return "\n".join(out)


def main() -> None:
    global _LANG
    if _i18n is not None:
        try:
            _LANG = _i18n.detect_lang()
        except Exception:
            _LANG = "es"

    output = build_output()
    if output:
        print(output)


if __name__ == "__main__":
    main()
