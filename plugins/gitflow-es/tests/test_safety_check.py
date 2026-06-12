"""
Tests de los checks de safety-check.py.

Cada check llama a `block()` (que hace `sys.exit(2)`) cuando detecta una
violación, o retorna normalmente cuando la operación es segura. El helper
`blocked()` traduce eso a un booleano.

Correr con:  pytest plugins/gitflow-es/tests
"""

import pytest


def blocked(check, command, branch=None):
    """True si `check` bloqueó (SystemExit), False si permitió."""
    try:
        check(command, branch)
        return False
    except SystemExit as exc:
        assert exc.code == 2
        return True


# --------------------------------------------------------------------------- #
# force-push  (incluye la regresión de flags cortos combinados: -fv, -vf)
# --------------------------------------------------------------------------- #

FORCE_PUSH_CASES = [
    ("git push --force origin main", "main", True),
    ("git push -f origin main", "main", True),
    ("git push -fv origin main", "main", True),   # antes se colaba
    ("git push -vf origin main", "main", True),   # antes se colaba
    ("git push --force-with-lease origin develop", "develop", True),
    ("git push --follow-tags origin main", "main", False),  # NO es force
    ("git push origin main", "main", False),
    ("git push -f origin feature/x", "feature/x", False),   # target no protegido
]


@pytest.mark.parametrize("command,branch,expected", FORCE_PUSH_CASES)
def test_force_push(safety, command, branch, expected):
    assert blocked(safety.check_force_push, command, branch) is expected


# --------------------------------------------------------------------------- #
# rebase sobre rama protegida
# --------------------------------------------------------------------------- #

REBASE_CASES = [
    ("git rebase develop", "main", True),
    ("git rebase -i HEAD~3", "develop", True),
    ("git rebase --abort", "main", False),       # gestión de rebase en curso
    ("git rebase --continue", "develop", False),
    ("git rebase main", "feature/x", False),     # rebase desde una rama de trabajo
    ("git status", "main", False),               # no es rebase
]


@pytest.mark.parametrize("command,branch,expected", REBASE_CASES)
def test_rebase_protected(safety, command, branch, expected):
    assert blocked(safety.check_rebase_protected, command, branch) is expected


# --------------------------------------------------------------------------- #
# branch -d/-D/--delete de rama protegida
# --------------------------------------------------------------------------- #

BRANCH_DELETE_CASES = [
    ("git branch -d main", True),
    ("git branch -D develop", True),
    ("git branch --delete master", True),
    ("git branch -d feature/x", False),
    ("git branch -m main nuevo-nombre", False),  # rename, no delete
    ("git branch -a", False),
]


@pytest.mark.parametrize("command,expected", BRANCH_DELETE_CASES)
def test_branch_delete_protected(safety, command, expected):
    assert blocked(safety.check_branch_delete_protected, command) is expected


# --------------------------------------------------------------------------- #
# push que borra rama protegida (--delete / refspec con dos puntos)
# --------------------------------------------------------------------------- #

PUSH_DELETE_CASES = [
    ("git push origin --delete main", True),
    ("git push origin -d develop", True),
    ("git push origin :main", True),
    ("git push origin :refs/heads/develop", True),
    ("git push origin main", False),
    ("git push origin --delete feature/x", False),
]


@pytest.mark.parametrize("command,expected", PUSH_DELETE_CASES)
def test_push_delete_protected(safety, command, expected):
    assert blocked(safety.check_push_delete_protected, command) is expected


# --------------------------------------------------------------------------- #
# reset --hard / clean -f
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("command,expected", [
    ("git reset --hard HEAD~1", True),
    ("git reset --soft HEAD~1", False),
    ("git reset HEAD archivo.txt", False),
])
def test_reset_hard(safety, command, expected):
    assert blocked(safety.check_reset_hard, command) is expected


@pytest.mark.parametrize("command,expected", [
    ("git clean -f", True),
    ("git clean -fd", True),
    ("git clean -xf", True),
    ("git clean -n", False),
    ("git status", False),
])
def test_clean_force(safety, command, expected):
    assert blocked(safety.check_clean_force, command) is expected


# --------------------------------------------------------------------------- #
# no-verify / author
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("command,expected", [
    ("git commit -m 'x' --no-verify", True),
    ("git commit -m 'x'", False),
])
def test_no_verify(safety, command, expected):
    assert blocked(safety.check_no_verify, command) is expected


@pytest.mark.parametrize("command,expected", [
    ("git commit -m 'x' --author='A <a@b.c>'", True),
    ("git commit -m 'x'", False),
])
def test_explicit_author(safety, command, expected):
    assert blocked(safety.check_explicit_author, command) is expected


# --------------------------------------------------------------------------- #
# archivos sensibles
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("command,expected", [
    ("git add .env", True),
    ("git commit .env", True),
    ("git add .env.example", False),     # plantilla permitida
    ("git add .env.sample", False),
    ("git add id_rsa", True),
    ("git add credentials.json", True),
    ("git add cert.pem", True),
    ("git add src/index.ts", False),
])
def test_sensitive_files(safety, command, expected):
    assert blocked(safety.check_sensitive_files, command) is expected


# --------------------------------------------------------------------------- #
# commit en main (con repo_has_commits monkeypatcheado para determinismo)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("branch,has_commits,expected", [
    ("main", True, True),       # repo con commits → bloquea
    ("master", True, True),
    ("main", False, False),     # repo sin commits → permite el primer commit
    ("develop", True, False),   # develop no está en PROTECTED_BRANCHES del check
    ("feature/x", True, False),
])
def test_commit_on_main(safety, monkeypatch, branch, has_commits, expected):
    monkeypatch.setattr(safety, "repo_has_commits", lambda *a, **k: has_commits)
    assert blocked(safety.check_commit_on_main, "git commit -m 'x'", branch) is expected


# --------------------------------------------------------------------------- #
# git flow <sub> sin init (gitflow_initialized monkeypatcheado)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("command,initialized,expected", [
    ("git flow feature start x", False, True),
    ("git flow feature start x", True, False),
    ("git flow init -d", False, False),       # init nunca se bloquea
    ("git flow version", False, False),       # subcomando que no requiere init
])
def test_gitflow_not_initialized(safety, monkeypatch, command, initialized, expected):
    monkeypatch.setattr(safety, "gitflow_initialized", lambda *a, **k: initialized)
    assert blocked(safety.check_gitflow_not_initialized, command) is expected
