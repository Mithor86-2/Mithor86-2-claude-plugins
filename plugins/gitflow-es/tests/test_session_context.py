"""Tests del hook de contexto de sesión (session-context.py)."""

import pytest


def make_run(responses, default=None):
    """
    Devuelve un stub de `run` que resuelve por coincidencia de subcadena sobre el
    comando ya unido. `responses` es una lista de (fragmento, valor) evaluada en
    orden, así que las reglas más específicas van primero.
    """

    def _run(cmd):
        joined = " ".join(cmd)
        for fragment, value in responses:
            if fragment in joined:
                return value
        return default

    return _run


WORKTREE_PORCELAIN = """worktree /repo
HEAD 1111111111111111111111111111111111111111
branch refs/heads/develop

worktree /repo-worktrees/feature-x
HEAD 2222222222222222222222222222222222222222
branch refs/heads/feature/x

worktree /repo-worktrees/suelto
HEAD 3333333333333333333333333333333333333333
detached
"""


@pytest.fixture
def sc(session_context, monkeypatch):
    """session-context con idioma fijo en es y sin acceso real a git."""
    monkeypatch.setattr(session_context, "_LANG", "es")
    monkeypatch.setenv("GITFLOW_LANG", "es")
    return session_context


def test_sin_repo_git_no_imprime_nada(sc, monkeypatch):
    monkeypatch.setattr(sc, "run", make_run([("rev-parse --is-inside-work-tree", "false")]))
    assert sc.build_output() == ""


def test_repo_sin_commits_guia_al_commit_inicial(sc, monkeypatch):
    monkeypatch.setattr(sc, "run", make_run([("rev-parse --is-inside-work-tree", "true")]))
    monkeypatch.setattr(sc, "repo_has_commits", lambda: False)

    out = sc.build_output()

    assert "Repo recién inicializado" in out
    assert "git flow init -d" in out


def test_worktree_de_control_en_develop_avisa_que_no_se_trabaja_ahi(sc, monkeypatch):
    monkeypatch.setattr(
        sc,
        "run",
        make_run(
            [
                ("rev-parse --is-inside-work-tree", "true"),
                ("branch --show-current", "develop"),
                ("status --porcelain", ""),
                ("worktree list", WORKTREE_PORCELAIN),
            ]
        ),
    )
    monkeypatch.setattr(sc, "repo_has_commits", lambda: True)
    monkeypatch.setattr(sc, "is_linked_worktree", lambda: False)
    monkeypatch.setattr(sc, "gitflow_initialized", lambda: True)
    monkeypatch.setattr(sc, "lang_set", lambda: True)

    out = sc.build_output()

    assert "Worktree de control" in out
    assert "/git start" in out
    # Repo ya configurado: no se repite el bloque de configuración.
    assert "Configuración de gitflow-es" not in out


def test_worktree_linked_muestra_su_ruta_y_lista_los_worktrees(sc, monkeypatch):
    monkeypatch.setattr(
        sc,
        "run",
        make_run(
            [
                ("rev-parse --is-inside-work-tree", "true"),
                ("branch --show-current", "feature/x"),
                ("status --porcelain", "M archivo.py"),
                ("worktree list", WORKTREE_PORCELAIN),
                ("rev-parse --show-toplevel", "/repo-worktrees/feature-x"),
            ]
        ),
    )
    monkeypatch.setattr(sc, "repo_has_commits", lambda: True)
    monkeypatch.setattr(sc, "is_linked_worktree", lambda: True)
    monkeypatch.setattr(sc, "gitflow_initialized", lambda: True)
    monkeypatch.setattr(sc, "lang_set", lambda: True)

    out = sc.build_output()

    assert "Worktree de trabajo:** `/repo-worktrees/feature-x`" in out
    assert "**Worktrees activos:** 3" in out
    assert "`feature/x` → `/repo-worktrees/feature-x`" in out
    assert "Cambios pendientes:** 1" in out


def test_sin_gitflow_muestra_checklist_y_propone_git_init(sc, monkeypatch):
    monkeypatch.setattr(
        sc,
        "run",
        make_run(
            [
                ("rev-parse --is-inside-work-tree", "true"),
                ("branch --show-current", "main"),
                ("status --porcelain", ""),
                ("worktree list", ""),
            ]
        ),
    )
    monkeypatch.setattr(sc, "repo_has_commits", lambda: True)
    monkeypatch.setattr(sc, "is_linked_worktree", lambda: False)
    monkeypatch.setattr(sc, "gitflow_initialized", lambda: False)
    monkeypatch.setattr(sc, "lang_set", lambda: True)
    monkeypatch.setattr(sc, "config_get", lambda key: None)

    out = sc.build_output()

    assert "git-flow no inicializado" in out
    assert "Configuración de gitflow-es" in out
    assert "/git init" in out
    # Los cuatro ítems del checklist, todos pendientes salvo el idioma.
    assert out.count("- ⬜ ") == 3
    assert "- ✅ idioma de salida" in out


def test_gitflow_ok_pero_idioma_sin_configurar_pide_idioma_con_checklist(sc, monkeypatch):
    monkeypatch.setattr(
        sc,
        "run",
        make_run(
            [
                ("rev-parse --is-inside-work-tree", "true"),
                ("branch --show-current", "feature/x"),
                ("status --porcelain", ""),
                ("worktree list", ""),
            ]
        ),
    )
    monkeypatch.setattr(sc, "repo_has_commits", lambda: True)
    monkeypatch.setattr(sc, "is_linked_worktree", lambda: False)
    monkeypatch.setattr(sc, "gitflow_initialized", lambda: True)
    monkeypatch.setattr(sc, "lang_set", lambda: False)
    monkeypatch.setattr(sc, "config_get", lambda key: "algo" if key == "worktreeRoot" else None)

    out = sc.build_output()

    assert "Configura el idioma de gitflow-es" in out
    assert "Configuración de gitflow-es" in out
    assert "- ✅ raíz de worktrees" in out
    assert "- ⬜ idioma de salida" in out


def test_worktrees_parsea_porcelain_incluido_detached(sc, monkeypatch):
    monkeypatch.setattr(sc, "run", make_run([("worktree list", WORKTREE_PORCELAIN)]))

    assert sc.worktrees() == [
        ("develop", "/repo"),
        ("feature/x", "/repo-worktrees/feature-x"),
        ("(detached)", "/repo-worktrees/suelto"),
    ]


def test_linea_de_tiempos_silenciosa_sin_modulo_timelog(sc, monkeypatch):
    monkeypatch.setattr(sc, "_timelog", None)
    assert sc.time_summary_line("feature/x") is None
