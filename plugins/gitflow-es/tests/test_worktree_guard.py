"""
Tests de las guardas de worktree del hook safety-check:

  - bloqueo de `git flow <tipo> finish` dentro del worktree de la rama
  - avisos no bloqueantes de la política de worktrees
  - regresión del falso positivo de force-push con comandos compuestos
"""

import pytest


class FakeGitwt:
    """Doble de `gitwt` con lo mínimo que usan las guardas."""

    def __init__(self, linked=False, worktrees=None, policy=True):
        self._linked = linked
        self._worktrees = worktrees or {}
        self._policy = policy

    def is_linked_worktree(self, cwd=None):
        if cwd is not None:
            return cwd in self._worktrees.values()
        return self._linked

    def develop_branch(self, cwd=None):
        return "develop"

    def production_branch(self, cwd=None):
        return "main"

    def gitflow_prefix(self, kind, cwd=None):
        return "{0}/".format(kind)

    def worktree_for_branch(self, branch, cwd=None):
        return self._worktrees.get(branch)

    def flag_enabled(self, key, default=True, cwd=None):
        return self._policy if key == "worktrees" else default

    def throttle(self, key, seconds, cwd=None):
        return True


@pytest.fixture
def guard(safety, monkeypatch):
    """safety-check con los avisos limpios y sin acceso real a git."""
    monkeypatch.setattr(safety, "_ADVICES", [])
    monkeypatch.setattr(safety, "_LANG", "es")
    return safety


def advices(module):
    return list(module._ADVICES)


# --------------------------------------------------------------------------- #
# Bloqueo del finish dentro del worktree de la rama
# --------------------------------------------------------------------------- #


def test_finish_dentro_del_worktree_linked_bloquea(guard, monkeypatch, capsys):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt(linked=True))

    with pytest.raises(SystemExit) as exc:
        guard.check_finish_in_linked_worktree("git flow feature finish login", None)

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "worktree de la rama" in err
    # El mensaje debe explicar el falso éxito, que es el motivo del bloqueo.
    assert "código de salida 0" in err


@pytest.mark.parametrize(
    "command",
    [
        "git flow feature finish login",
        "git flow hotfix finish parche",
        "git flow release finish 1.2.0",
    ],
)
def test_finish_bloquea_para_todos_los_tipos(guard, monkeypatch, command):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt(linked=True))
    with pytest.raises(SystemExit):
        guard.check_finish_in_linked_worktree(command, None)


def test_finish_desde_el_control_no_bloquea(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt(linked=False))
    guard.check_finish_in_linked_worktree("git flow feature finish login", None)  # no lanza


def test_finish_sin_gitwt_no_bloquea(guard, monkeypatch):
    """Si el módulo compartido faltara, la guarda se desactiva (fail-open)."""
    monkeypatch.setattr(guard, "_gitwt", None)
    guard.check_finish_in_linked_worktree("git flow feature finish login", None)


# --------------------------------------------------------------------------- #
# Aviso: finish con el worktree de la rama todavía vivo
# --------------------------------------------------------------------------- #


def test_finish_con_worktree_vivo_avisa(guard, monkeypatch):
    fake = FakeGitwt(linked=False, worktrees={"feature/login": "/wt/feature-login"})
    monkeypatch.setattr(guard, "_gitwt", fake)

    guard.check_finish_with_live_worktree("git flow feature finish login", "develop")

    assert len(advices(guard)) == 1
    assert "/wt/feature-login" in advices(guard)[0]


def test_finish_sin_nombre_usa_la_rama_actual(guard, monkeypatch):
    fake = FakeGitwt(linked=False, worktrees={"feature/login": "/wt/feature-login"})
    monkeypatch.setattr(guard, "_gitwt", fake)

    guard.check_finish_with_live_worktree("git flow feature finish", "feature/login")

    assert len(advices(guard)) == 1


def test_finish_sin_worktree_vivo_no_avisa(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt(linked=False, worktrees={}))
    guard.check_finish_with_live_worktree("git flow feature finish login", "develop")
    assert advices(guard) == []


# --------------------------------------------------------------------------- #
# Aviso: rama creada sin worktree
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "command",
    [
        "git checkout -b feature/login",
        "git switch -c fix/bug",
        "git flow feature start login",
        "git flow release start 1.2.0",
    ],
)
def test_crear_rama_sin_worktree_avisa(guard, monkeypatch, command):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_branch_creation_without_worktree(command, "develop")
    assert len(advices(guard)) == 1
    assert "worktree" in advices(guard)[0]


def test_crear_rama_con_worktree_en_el_mismo_comando_no_avisa(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_branch_creation_without_worktree(
        "git worktree add -b feature/login /wt/feature-login develop", "develop"
    )
    assert advices(guard) == []


def test_politica_desactivada_silencia_los_avisos(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt(policy=False))
    guard.check_branch_creation_without_worktree("git checkout -b feature/login", "develop")
    assert advices(guard) == []


# --------------------------------------------------------------------------- #
# Aviso: base del worktree distinta de develop
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "args,expected",
    [
        (" -b feature/login /wt/x develop", (None, "develop")),
        (" -b hotfix/parche /wt/h main", ("hotfix/parche", "main")),
        (" /wt/x", (None, None)),
        (" --detach /wt/x origin/develop", (None, "origin/develop")),
    ],
)
def test_parse_worktree_add(guard, args, expected):
    branch, base = guard._parse_worktree_add(args)
    expected_branch, expected_base = expected
    if expected_branch is not None:
        assert branch == expected_branch
    assert base == expected_base


def test_base_develop_no_avisa(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_worktree_base("git worktree add -b feature/x /wt/x develop", None)
    assert advices(guard) == []


def test_base_remota_develop_no_avisa(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_worktree_base("git worktree add -b feature/x /wt/x origin/develop", None)
    assert advices(guard) == []


def test_base_main_avisa(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_worktree_base("git worktree add -b feature/x /wt/x main", None)
    assert len(advices(guard)) == 1
    assert "develop" in advices(guard)[0]


def test_hotfix_desde_main_es_excepcion_estructural(guard, monkeypatch):
    monkeypatch.setattr(guard, "_gitwt", FakeGitwt())
    guard.check_worktree_base("git worktree add -b hotfix/parche /wt/h main", None)
    assert advices(guard) == []


# --------------------------------------------------------------------------- #
# Regresión: force-push mal detectado en comandos compuestos
# --------------------------------------------------------------------------- #


def test_split_commands_separa_por_operadores(guard):
    partes = guard.split_commands("git merge --no-ff fix/x && git branch -d fix/x; git status")
    assert partes == ["git merge --no-ff fix/x", "git branch -d fix/x", "git status"]


def test_merge_no_ff_no_es_force_push(guard):
    """`--no-ff` contiene `-ff`, pero no es un flag de force."""
    guard.check_force_push("git push origin develop", "develop")  # sin force: no bloquea
    guard.check_force_push("git merge --no-ff fix/x", "develop")  # no es push: no bloquea


def test_comando_compuesto_no_contamina_el_push(guard):
    """
    El caso real que falló: un merge con --no-ff y un push a develop en la misma
    línea se leían juntos y disparaban el bloqueo de force-push.
    """
    compuesto = "git merge --no-ff fix/x && git push origin develop"
    for segmento in guard.split_commands(compuesto):
        guard.check_force_push(segmento, "develop")  # ninguno debe bloquear


def test_force_push_real_sigue_bloqueado(guard):
    with pytest.raises(SystemExit):
        guard.check_force_push("git push --force origin develop", "develop")


def test_force_push_con_flags_cortos_combinados_sigue_bloqueado(guard):
    with pytest.raises(SystemExit):
        guard.check_force_push("git push -fv origin main", "main")


def test_follow_tags_no_es_force(guard):
    guard.check_force_push("git push --follow-tags origin main", "main")
