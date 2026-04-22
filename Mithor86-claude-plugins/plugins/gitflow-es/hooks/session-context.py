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
    if not in_git_repo():
        return  # Sin salida = no se inyecta nada

    branch = run(["git", "branch", "--show-current"]) or "(detached HEAD)"
    kind = branch_type(branch)
    status_lines = run(["git", "status", "--porcelain"]) or ""
    num_changes = len([l for l in status_lines.splitlines() if l.strip()])

    out = []
    out.append("## Estado GitFlow del repo")
    out.append("")
    out.append(f"- **Rama actual:** `{branch}`")

    if branch in {"main", "master", "develop"}:
        out.append(
            f"- ⚠️ Estás parado en `{branch}`. No modifiques archivos aquí; "
            f"usa `/git start <tipo> <descripcion>` para crear una rama de trabajo."
        )
    elif kind:
        out.append(f"- **Tipo GitFlow:** `{kind}`")
    elif branch != "(detached HEAD)":
        out.append(f"- La rama no usa un prefijo GitFlow reconocido.")

    if num_changes > 0:
        out.append(f"- **Cambios pendientes:** {num_changes} archivo(s)")
    else:
        out.append("- Working tree limpio")

    ab = ahead_behind(branch)
    if ab is not None:
        ahead, behind = ab
        if ahead == 0 and behind == 0:
            out.append("- Sincronizada con `origin`")
        elif ahead > 0 and behind == 0:
            out.append(f"- {ahead} commit(s) por delante de `origin`")
        elif behind > 0 and ahead == 0:
            out.append(f"- {behind} commit(s) por detrás de `origin`")
        else:
            out.append(f"- Divergida: {ahead} adelante / {behind} atrás de `origin`")

    print("\n".join(out))


if __name__ == "__main__":
    main()
