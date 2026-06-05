#!/usr/bin/env python3
"""
gitflow-es i18n — módulo compartido de mensajes ES/EN para los hooks.

Resolución del idioma activo (prioridad):
  1. Variable de entorno `GITFLOW_LANG`.
  2. `git config --get gitflow-es.language`.
  3. Default `es`.

Cualquier valor fuera de {"es", "en"} cae a "es" (retrocompatibilidad).

Diseño:
  - Puro stdlib, compatible con Python 3.7+.
  - Lo importan safety-check.py y session-context.py (mismo directorio, así que
    CPython lo resuelve vía sys.path[0] al ejecutar el script por ruta absoluta).
  - Los strings `es` son copia exacta de los literales que tenían los hooks antes
    de la extracción, para no introducir cambios de comportamiento sin config.
"""

from __future__ import annotations

import os
import subprocess

VALID_LANGS = ("es", "en")
DEFAULT_LANG = "es"


def detect_lang(cwd=None) -> str:
    """Resuelve el idioma activo. Ver prioridad en el docstring del módulo."""
    env = (os.environ.get("GITFLOW_LANG") or "").strip().lower()
    if env in VALID_LANGS:
        return env
    if env:
        # Valor de entorno presente pero inválido → ignorar y seguir.
        return DEFAULT_LANG

    cmd = ["git", "config", "--get", "gitflow-es.language"]
    if cwd:
        cmd = ["git", "-C", cwd, "config", "--get", "gitflow-es.language"]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            cfg = result.stdout.strip().lower()
            if cfg in VALID_LANGS:
                return cfg
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return DEFAULT_LANG


MESSAGES = {
    "es": {
        # --- safety-check ---
        "block_default_hint": (
            "Si realmente necesitas ejecutar esto, pídele al usuario que "
            "lo haga directamente en su terminal."
        ),
        "force_push": (
            "Bloqueado: `git push --force` sobre `{target}` está prohibido por "
            "la política del equipo. Rehace los commits o haz revert en una "
            "rama de trabajo en vez de reescribir el historial compartido."
        ),
        "commit_on_main": (
            "Bloqueado: commit directo en `{branch}`. El flujo del equipo "
            "exige trabajar en una rama (`feature/*`, `fix/*`, `hotfix/*`, "
            "etc.) y cerrarla con `/git finish`."
        ),
        "no_verify": (
            "Bloqueado: `git commit --no-verify` está prohibido. Los "
            "pre-commit hooks existen por una razón — si uno está roto, "
            "arréglalo en lugar de saltártelo."
        ),
        "explicit_author": (
            "Bloqueado: `git commit --author=...` está prohibido. El autor "
            "del commit siempre debe ser el usuario configurado en git."
        ),
        "reset_hard": (
            "Bloqueado: `git reset --hard` destruye cambios sin aviso. Si "
            "realmente lo necesitas, córrelo manualmente en tu terminal."
        ),
        "clean_force": (
            "Bloqueado: `git clean -f` elimina archivos sin confirmación. "
            "Si realmente lo necesitas, córrelo manualmente o usa `git "
            "clean -n` primero para previsualizar."
        ),
        "sensitive_env": (
            "Bloqueado: parece que estás intentando añadir `.env` al commit. "
            "Los archivos `.env` no deben versionarse — agrega el archivo a "
            "`.gitignore`. Si es un `.env.example`, renómbralo."
        ),
        "sensitive_file": (
            "Bloqueado: el comando parece añadir un archivo sensible "
            "(patrón `{pattern}`). Si es un falso positivo, renombra el "
            "archivo o córrelo manualmente."
        ),
        "gitflow_not_init_reason": (
            "Bloqueado: este repo no tiene git-flow inicializado todavía, y el "
            "subcomando `git flow {subcommand}` lo requiere."
        ),
        "gitflow_not_init_hint": (
            "Para arreglarlo, propónle al usuario inicializar git-flow con "
            "los defaults del equipo:\n\n"
            "  git flow init -d\n\n"
            "Eso configura `main` como rama de producción, `develop` como "
            "rama de integración, y los prefijos estándar (feature/, "
            "hotfix/, release/, support/).\n\n"
            "Si el repo aún no tiene rama `develop`, git-flow la creará "
            "automáticamente. Una vez inicializado, reintenta el comando "
            "original."
        ),
        "edit_on_main_reason": (
            "Bloqueado: estás parado en `{branch}` y no se permite modificar "
            "archivos directamente sobre la rama de producción. Antes de "
            "editar `{file_path}`, crea una rama de trabajo."
        ),
        "edit_on_main_hint": (
            "Flujo sugerido:\n"
            "  1. Preguntarle al usuario qué tipo de cambio es "
            "(feature, fix, hotfix, chore, refactor).\n"
            "  2. Proponer un nombre de rama en kebab-case y confirmarlo.\n"
            "  3. Crear la rama con `git flow <tipo> start <nombre>` "
            "(para feature/hotfix/release) o `git checkout -b "
            "<tipo>/<nombre>` desde develop (para fix/refactor/chore).\n"
            "  4. Una vez en la rama, reintentar la edición."
        ),
        # --- session-context ---
        "sc_header": "## Estado GitFlow del repo",
        "sc_no_commits_title": "### ⚠️ Repo recién inicializado (sin commits)",
        "sc_no_commits_body": (
            "Este repo todavía no tiene ningún commit. Git necesita al menos "
            "un commit inicial antes de poder crear ramas o inicializar "
            "git-flow."
        ),
        "sc_no_commits_flow_label": (
            "**Flujo sugerido** (proponérselo al usuario, pedir OK y ejecutar):"
        ),
        "sc_no_commits_note": (
            "El hook de safety permite este primer commit en `main`/`master` "
            "como excepción explícita. A partir del segundo commit vuelve a "
            "aplicar la regla normal (solo commits desde ramas de trabajo)."
        ),
        "sc_current_branch": "- **Rama actual:** `{branch}`",
        "sc_on_protected": (
            "- ⚠️ Estás parado en `{branch}`. No modifiques archivos aquí; "
            "usa `/git start <tipo> <descripcion>` para crear una rama de trabajo."
        ),
        "sc_branch_type": "- **Tipo GitFlow:** `{kind}`",
        "sc_unknown_prefix": "- La rama no usa un prefijo GitFlow reconocido.",
        "sc_pending_changes": "- **Cambios pendientes:** {count} archivo(s)",
        "sc_clean_tree": "- Working tree limpio",
        "sc_synced": "- Sincronizada con `origin`",
        "sc_ahead": "- {ahead} commit(s) por delante de `origin`",
        "sc_behind": "- {behind} commit(s) por detrás de `origin`",
        "sc_diverged": "- Divergida: {ahead} adelante / {behind} atrás de `origin`",
        "sc_no_gitflow_title": "### ⚠️ git-flow no inicializado",
        "sc_no_gitflow_body": (
            "Este repo no tiene git-flow configurado todavía. Los subcomandos "
            "`git flow feature|hotfix|release start/finish` no funcionarán "
            "hasta que se inicialice."
        ),
        "sc_no_gitflow_action": (
            "**Acción sugerida:** preguntarle al usuario si quiere "
            "inicializarlo ahora con los defaults del equipo:"
        ),
        "sc_no_gitflow_explain": (
            "Eso configura `main` como rama de producción, `develop` como "
            "rama de integración, y los prefijos estándar (`feature/`, "
            "`hotfix/`, `release/`, `support/`). Si el repo aún no tiene "
            "rama `develop`, git-flow la creará."
        ),
    },
    "en": {
        # --- safety-check ---
        "block_default_hint": (
            "If you really need to run this, ask the user to do it directly "
            "in their terminal."
        ),
        "force_push": (
            "Blocked: `git push --force` to `{target}` is prohibited by team "
            "policy. Rebase your commits or revert in a working branch "
            "instead of rewriting shared history."
        ),
        "commit_on_main": (
            "Blocked: direct commit on `{branch}`. The team workflow requires "
            "working on a branch (`feature/*`, `fix/*`, `hotfix/*`, etc.) and "
            "closing it with `/git finish`."
        ),
        "no_verify": (
            "Blocked: `git commit --no-verify` is prohibited. Pre-commit "
            "hooks exist for a reason — if one is broken, fix it instead of "
            "skipping it."
        ),
        "explicit_author": (
            "Blocked: `git commit --author=...` is prohibited. The commit "
            "author must always be the user configured in git."
        ),
        "reset_hard": (
            "Blocked: `git reset --hard` destroys changes without warning. If "
            "you really need it, run it manually in your terminal."
        ),
        "clean_force": (
            "Blocked: `git clean -f` deletes files without confirmation. If "
            "you really need it, run it manually or use `git clean -n` first "
            "to preview."
        ),
        "sensitive_env": (
            "Blocked: it looks like you're trying to add `.env` to the commit. "
            "`.env` files must not be versioned — add the file to "
            "`.gitignore`. If it's a `.env.example`, rename it."
        ),
        "sensitive_file": (
            "Blocked: the command appears to add a sensitive file "
            "(pattern `{pattern}`). If it's a false positive, rename the "
            "file or run it manually."
        ),
        "gitflow_not_init_reason": (
            "Blocked: this repo doesn't have git-flow initialized yet, and "
            "the `git flow {subcommand}` subcommand requires it."
        ),
        "gitflow_not_init_hint": (
            "To fix it, suggest the user initialize git-flow with the team "
            "defaults:\n\n"
            "  git flow init -d\n\n"
            "That sets `main` as the production branch, `develop` as the "
            "integration branch, and the standard prefixes (feature/, "
            "hotfix/, release/, support/).\n\n"
            "If the repo doesn't have a `develop` branch yet, git-flow will "
            "create it automatically. Once initialized, retry the original "
            "command."
        ),
        "edit_on_main_reason": (
            "Blocked: you're on `{branch}` and editing files directly on the "
            "production branch is not allowed. Before editing `{file_path}`, "
            "create a working branch."
        ),
        "edit_on_main_hint": (
            "Suggested flow:\n"
            "  1. Ask the user what kind of change it is "
            "(feature, fix, hotfix, chore, refactor).\n"
            "  2. Propose a kebab-case branch name and confirm it.\n"
            "  3. Create the branch with `git flow <type> start <name>` "
            "(for feature/hotfix/release) or `git checkout -b "
            "<type>/<name>` from develop (for fix/refactor/chore).\n"
            "  4. Once on the branch, retry the edit."
        ),
        # --- session-context ---
        "sc_header": "## Repo GitFlow status",
        "sc_no_commits_title": "### ⚠️ Freshly initialized repo (no commits)",
        "sc_no_commits_body": (
            "This repo has no commits yet. Git needs at least an initial "
            "commit before you can create branches or initialize git-flow."
        ),
        "sc_no_commits_flow_label": (
            "**Suggested flow** (propose it to the user, ask for OK and run):"
        ),
        "sc_no_commits_note": (
            "The safety hook allows this first commit on `main`/`master` as "
            "an explicit exception. From the second commit on, the normal "
            "rule applies again (only commits from working branches)."
        ),
        "sc_current_branch": "- **Current branch:** `{branch}`",
        "sc_on_protected": (
            "- ⚠️ You're on `{branch}`. Don't modify files here; use "
            "`/git start <type> <description>` to create a working branch."
        ),
        "sc_branch_type": "- **GitFlow type:** `{kind}`",
        "sc_unknown_prefix": "- The branch doesn't use a recognized GitFlow prefix.",
        "sc_pending_changes": "- **Pending changes:** {count} file(s)",
        "sc_clean_tree": "- Clean working tree",
        "sc_synced": "- In sync with `origin`",
        "sc_ahead": "- {ahead} commit(s) ahead of `origin`",
        "sc_behind": "- {behind} commit(s) behind `origin`",
        "sc_diverged": "- Diverged: {ahead} ahead / {behind} behind `origin`",
        "sc_no_gitflow_title": "### ⚠️ git-flow not initialized",
        "sc_no_gitflow_body": (
            "This repo doesn't have git-flow configured yet. The "
            "`git flow feature|hotfix|release start/finish` subcommands won't "
            "work until it's initialized."
        ),
        "sc_no_gitflow_action": (
            "**Suggested action:** ask the user whether they want to "
            "initialize it now with the team defaults:"
        ),
        "sc_no_gitflow_explain": (
            "That sets `main` as the production branch, `develop` as the "
            "integration branch, and the standard prefixes (`feature/`, "
            "`hotfix/`, `release/`, `support/`). If the repo doesn't have a "
            "`develop` branch yet, git-flow will create it."
        ),
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Devuelve el mensaje `key` en `lang`, formateado con kwargs.

    Doble fallback: idioma faltante → es; clave faltante → es. Nunca lanza por
    clave/idioma desconocido (sí puede lanzar si faltan kwargs de formato, lo
    cual sería un bug del llamador, no de los datos).
    """
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    template = table.get(key) or MESSAGES[DEFAULT_LANG].get(key, "")
    if kwargs:
        return template.format(**kwargs)
    return template
