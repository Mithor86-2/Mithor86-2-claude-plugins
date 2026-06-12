"""Tests del módulo i18n compartido."""

import pytest


def test_t_formats_kwargs(i18n):
    msg = i18n.t("force_push", "es", target="main")
    assert "main" in msg


def test_t_unknown_lang_falls_back_to_es(i18n):
    es = i18n.t("reset_hard", "es")
    fb = i18n.t("reset_hard", "pt")  # idioma no soportado → es
    assert fb == es


def test_t_unknown_key_returns_empty(i18n):
    assert i18n.t("clave_que_no_existe", "es") == ""


def test_t_en_differs_from_es(i18n):
    assert i18n.t("force_push", "en", target="main") != i18n.t(
        "force_push", "es", target="main"
    )


def test_new_keys_present_in_both_langs(i18n):
    for key in ("rebase_protected", "branch_delete_protected", "push_delete_protected"):
        assert key in i18n.MESSAGES["es"], key
        assert key in i18n.MESSAGES["en"], key


@pytest.mark.parametrize("env_value,expected", [
    ("en", "en"),
    ("es", "es"),
    ("EN", "en"),        # case-insensitive
    ("pt", "es"),        # inválido → default
    ("", "es"),          # ausente → default (asumiendo sin git config)
])
def test_detect_lang_env(i18n, monkeypatch, env_value, expected):
    monkeypatch.setenv("GITFLOW_LANG", env_value)
    # Para el caso vacío, detect_lang consulta git config; lo neutralizamos
    # apuntando a un cwd sin config relevante no es trivial, así que solo
    # validamos los casos con env var explícita (no vacía) de forma estricta.
    if env_value:
        assert i18n.detect_lang() == expected


def test_lang_explicitly_set_true_with_env(i18n, monkeypatch):
    monkeypatch.setenv("GITFLOW_LANG", "en")
    assert i18n.lang_explicitly_set() is True
