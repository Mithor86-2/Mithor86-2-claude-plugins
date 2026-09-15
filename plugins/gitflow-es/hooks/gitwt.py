#!/usr/bin/env python3
"""
gitflow-es — helpers compartidos de git, worktrees y configuración del plugin.

Lo usan `safety-check.py` (guardas de worktree), `time-tracker.py` y
`time-report.py` (registro de tiempos). `session-context.py` mantiene sus
propias consultas de solo lectura porque necesita stubbearlas en tests.

Diseño:
  - Puro stdlib, compatible con Python 3.7+.
  - Todo fail-open: cualquier fallo devuelve None / el default, nunca lanza.
  - La config `gitflow-es.*` se lee de un solo golpe (`--get-regexp`) y se
    cachea por proceso: los hooks corren en cada evento y no pueden permitirse
    cinco `git config` por invocación.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Dict, List, Optional

DEFAULT_DEVELOP = "develop"
DEFAULT_PRODUCTION = "main"

# Segundos que vale la config cacheada en disco entre procesos de hook.
CONFIG_CACHE_TTL = 60

# Cache por proceso de la config `gitflow-es.*`, indexada por cwd resuelto.
_CONFIG_CACHE: Dict[str, Dict[str, str]] = {}

_TRUTHY = {"on", "true", "1", "yes", "si", "sí"}
_FALSY = {"off", "false", "0", "no"}


def run_git(args: List[str], cwd: Optional[str] = None, timeout: int = 3) -> Optional[str]:
    """Ejecuta git y devuelve stdout sin espacios, o None si falla."""
    cmd = ["git"]
    if cwd:
        cmd += ["-C", cwd]
    cmd += args
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


# --------------------------------------------------------------------------- #
# Resolución sin subprocesos
# --------------------------------------------------------------------------- #

# Los hooks corren en cada evento: el camino caliente resuelve rama y git-dir
# leyendo archivos, y solo cae a `git` si encuentra algo inesperado.


def _dot_git_path(cwd: Optional[str] = None) -> Optional[str]:
    """Busca el `.git` (carpeta o archivo) subiendo desde `cwd`."""
    try:
        path = os.path.abspath(cwd or os.getcwd())
    except OSError:
        return None
    while True:
        candidate = os.path.join(path, ".git")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def _git_dir_fast(cwd: Optional[str] = None) -> Optional[str]:
    """
    Directorio git de este worktree, leyendo archivos. En un worktree linked,
    `.git` es un archivo con `gitdir: <ruta>/.git/worktrees/<nombre>`.
    """
    dot_git = _dot_git_path(cwd)
    if not dot_git:
        return None
    if os.path.isdir(dot_git):
        return os.path.normpath(dot_git)
    try:
        with open(dot_git, "r", encoding="utf-8") as handle:
            content = handle.read().strip()
    except OSError:
        return None
    if not content.startswith("gitdir:"):
        return None
    target = content[len("gitdir:"):].strip()
    if not os.path.isabs(target):
        target = os.path.join(os.path.dirname(dot_git), target)
    return os.path.normpath(target)


def _common_git_dir_fast(cwd: Optional[str] = None) -> Optional[str]:
    """`.git` principal: en un worktree linked es el padre de `worktrees/`."""
    git_dir = _git_dir_fast(cwd)
    if not git_dir:
        return None
    marker = os.sep + "worktrees" + os.sep
    if marker in git_dir:
        return os.path.normpath(git_dir.split(marker)[0])
    return git_dir


def current_branch(cwd: Optional[str] = None) -> Optional[str]:
    """
    Rama actual leyendo `HEAD`. None si el worktree está en HEAD desacoplado o
    si no se pudo resolver (ahí cae a `git`).
    """
    git_dir = _git_dir_fast(cwd)
    if git_dir:
        try:
            with open(os.path.join(git_dir, "HEAD"), "r", encoding="utf-8") as handle:
                head = handle.read().strip()
        except OSError:
            head = ""
        if head.startswith("ref: refs/heads/"):
            return head[len("ref: refs/heads/"):] or None
        if head:
            return None  # detached: no hay rama que registrar
    return run_git(["branch", "--show-current"], cwd=cwd) or None


# --------------------------------------------------------------------------- #
# Configuración del plugin
# --------------------------------------------------------------------------- #


def config_all(cwd: Optional[str] = None) -> Dict[str, str]:
    """
    Devuelve toda la config `gitflow-es.*` como {clave_sin_prefijo: valor},
    en minúsculas (git normaliza los nombres de sección/clave). Cacheada.
    """
    key = os.path.abspath(cwd or os.getcwd())
    cached = _CONFIG_CACHE.get(key)
    if cached is not None:
        return cached

    cached_file = _config_from_disk(cwd)
    if cached_file is not None:
        _CONFIG_CACHE[key] = cached_file
        return cached_file

    values: Dict[str, str] = {}
    raw = run_git(["config", "--get-regexp", r"^gitflow-es\."], cwd=cwd)
    if raw:
        for line in raw.splitlines():
            parts = line.split(" ", 1)
            if not parts or not parts[0].startswith("gitflow-es."):
                continue
            name = parts[0][len("gitflow-es."):].strip().lower()
            values[name] = parts[1].strip() if len(parts) > 1 else ""

    _CONFIG_CACHE[key] = values
    _config_to_disk(values, cwd)
    return values


def _config_cache_file(cwd: Optional[str] = None) -> Optional[str]:
    common = common_git_dir(cwd)
    if not common:
        return None
    return os.path.join(common, "gitflow-es", "config-cache.json")


def _config_from_disk(cwd: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Config cacheada en disco, válida por `CONFIG_CACHE_TTL` segundos. Evita un
    `git config` por cada evento de hook; un cambio de configuración tarda a lo
    sumo ese TTL en verse (o se aplica ya si se borra el archivo).
    """
    path = _config_cache_file(cwd)
    if not path:
        return None
    try:
        if time.time() - os.path.getmtime(path) > CONFIG_CACHE_TTL:
            return None
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _config_to_disk(values: Dict[str, str], cwd: Optional[str] = None) -> None:
    path = _config_cache_file(cwd)
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(values, handle)
    except OSError:
        return


def config_get(key: str, cwd: Optional[str] = None) -> Optional[str]:
    """Valor de `gitflow-es.<key>`, o None si no está configurada."""
    value = config_all(cwd).get(key.lower())
    return value or None


def flag_enabled(key: str, default: bool = True, cwd: Optional[str] = None) -> bool:
    """Lee una clave booleana (`on`/`off`) con default explícito."""
    value = config_get(key, cwd)
    if value is None:
        return default
    value = value.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    return default


def config_int(key: str, default: int, cwd: Optional[str] = None) -> int:
    """Lee una clave entera, cayendo al default ante cualquier valor inválido."""
    value = config_get(key, cwd)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def clear_cache() -> None:
    """Limpia el cache de config (para tests)."""
    _CONFIG_CACHE.clear()


# --------------------------------------------------------------------------- #
# Ramas y worktrees
# --------------------------------------------------------------------------- #


def develop_branch(cwd: Optional[str] = None) -> str:
    """Rama de integración según git-flow (default `develop`)."""
    return run_git(["config", "--get", "gitflow.branch.develop"], cwd=cwd) or DEFAULT_DEVELOP


def production_branch(cwd: Optional[str] = None) -> str:
    """Rama de producción según git-flow (default `main`)."""
    return run_git(["config", "--get", "gitflow.branch.master"], cwd=cwd) or DEFAULT_PRODUCTION


def gitflow_prefix(kind: str, cwd: Optional[str] = None) -> str:
    """Prefijo configurado para un tipo git-flow (`feature` → `feature/`)."""
    value = run_git(["config", "--get", "gitflow.prefix.{0}".format(kind)], cwd=cwd)
    return value if value is not None else "{0}/".format(kind)


def absolute_git_dir(cwd: Optional[str] = None) -> Optional[str]:
    """Ruta absoluta del directorio git de *este* worktree."""
    value = run_git(["rev-parse", "--absolute-git-dir"], cwd=cwd)
    return os.path.normpath(value) if value else None


def common_git_dir(cwd: Optional[str] = None) -> Optional[str]:
    """
    Ruta absoluta del `.git` principal, compartido por todos los worktrees.

    Se resuelve sin `--path-format` (git ≥ 2.31) para no perder compatibilidad:
    si git devuelve una ruta relativa, se ancla al cwd.
    """
    fast = _common_git_dir_fast(cwd)
    if fast:
        return fast

    value = run_git(["rev-parse", "--git-common-dir"], cwd=cwd)
    if not value:
        return None
    if not os.path.isabs(value):
        value = os.path.join(os.path.abspath(cwd or os.getcwd()), value)
    return os.path.normpath(value)


def is_linked_worktree(cwd: Optional[str] = None) -> bool:
    """
    True si `cwd` está en un worktree creado con `git worktree add` (linked) y
    no en el worktree principal, al que llamamos "de control".
    """
    own = _git_dir_fast(cwd) or absolute_git_dir(cwd)
    common = common_git_dir(cwd)
    if not own or not common:
        return False
    return own != common


def worktree_list(cwd: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    """
    Todos los worktrees del repo como [{path, branch, detached}]. git garantiza
    que el worktree principal (de control) va primero.
    """
    raw = run_git(["worktree", "list", "--porcelain"], cwd=cwd)
    if not raw:
        return []

    trees: List[Dict[str, Optional[str]]] = []
    current: Dict[str, Optional[str]] = {}
    for line in raw.splitlines() + [""]:
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):].strip(), "branch": None, "detached": False}
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip().replace("refs/heads/", "", 1)
        elif line.strip() == "detached":
            current["detached"] = True
        elif not line.strip() and current:
            trees.append(current)
            current = {}
    return trees


def control_worktree(cwd: Optional[str] = None) -> Optional[str]:
    """Ruta del worktree de control (el principal), o None si no se pudo leer."""
    trees = worktree_list(cwd)
    return trees[0]["path"] if trees else None


def worktree_for_branch(branch: str, cwd: Optional[str] = None) -> Optional[str]:
    """Ruta del worktree que tiene `branch` checked out, o None si ninguno."""
    if not branch:
        return None
    for tree in worktree_list(cwd):
        if tree.get("branch") == branch:
            return tree.get("path")
    return None


def plugin_state_dir(cwd: Optional[str] = None) -> Optional[str]:
    """
    Directorio de estado del plugin: `<git-common-dir>/gitflow-es`. Vive dentro
    de `.git/`, así que nunca aparece en `git status` ni se commitea.
    """
    common = common_git_dir(cwd)
    if not common:
        return None
    path = os.path.join(common, "gitflow-es")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return None
    return path


def throttle(key: str, seconds: int, cwd: Optional[str] = None) -> bool:
    """
    True como máximo una vez cada `seconds` para la misma `key`. Se usa para que
    los avisos repetitivos (p. ej. editar en el worktree de control) no aparezcan
    en cada llamada a una herramienta.

    Ante cualquier problema de disco devuelve True: es preferible un aviso de más
    que perder la guarda.
    """
    state_dir = plugin_state_dir(cwd)
    if not state_dir:
        return True
    marker = os.path.join(state_dir, "throttle-{0}".format(key))
    now = time.time()
    try:
        if os.path.exists(marker) and now - os.path.getmtime(marker) < seconds:
            return False
        with open(marker, "w") as handle:
            handle.write(str(int(now)))
    except OSError:
        return True
    return True
