"""
Tests del hook de registro de tiempos.

El tracker corre en cada evento de la sesión: lo que se verifica acá es que
registre lo correcto por evento, que respete la configuración y que nunca
explote — un hook de medición no puede interrumpir el trabajo.
"""

import re

import pytest


class FakeTimelog:
    """Doble de `timelog` que acumula los eventos en memoria."""

    def __init__(self, tracking=True, notes="on", evidence=True):
        self.tracking = tracking
        self.notes = notes
        self.evidence = evidence
        self.events = []
        self.scans = 0

    # --- configuración ---
    def tracking_enabled(self, cwd=None):
        return self.tracking

    def notes_mode(self, cwd=None):
        return self.notes

    def evidence_enabled(self, cwd=None):
        return self.evidence

    def is_test_command(self, command, cwd=None):
        # Mismo criterio que el módulo real: `pytest` como comando, no como
        # parte de una ruta (los tmp_path de pytest contienen "pytest-of-…").
        return bool(re.search(r"(?:^|\s)pytest(?![-\w/])", command or ""))

    def sanitize_branch(self, branch):
        return (branch or "sin-rama").replace("/", "__")

    # --- registro ---
    def append_event(self, branch, event, cwd=None, **fields):
        self.events.append({"branch": branch, "event": event, **fields})
        return True

    def scan_evidence(self, worktree, since=0.0, limit=200):
        self.scans += 1
        return [("src/app.py", 1700000000.0)]

    # --- helpers de test ---
    def tipos(self):
        return [e["event"] for e in self.events]

    def primero(self, tipo):
        return next(e for e in self.events if e["event"] == tipo)


class FakeGitwt:
    def __init__(self, branch="feature/x", tmp=None, subject="feat: algo"):
        self.branch = branch
        self.tmp = tmp
        self.subject = subject
        self.branches = {}

    def current_branch(self, cwd=None):
        if cwd in self.branches:
            return self.branches[cwd]
        return self.branch

    def run_git(self, args, cwd=None, timeout=3):
        if args[:2] == ["rev-parse", "--show-toplevel"]:
            return "/repo/worktree"
        if args[:1] == ["log"]:
            return self.subject
        return None

    def plugin_state_dir(self, cwd=None):
        return str(self.tmp) if self.tmp else None

    def throttle(self, key, seconds, cwd=None):
        return True


@pytest.fixture
def entorno(tracker, tmp_path, monkeypatch):
    """tracker con timelog y gitwt falsos."""
    fake_timelog = FakeTimelog()
    fake_gitwt = FakeGitwt(tmp=tmp_path)
    monkeypatch.setattr(tracker, "timelog", fake_timelog)
    monkeypatch.setattr(tracker, "gitwt", fake_gitwt)
    return tracker, fake_timelog, fake_gitwt


def payload(event, **extra):
    base = {"hook_event_name": event, "cwd": "/repo/worktree", "session_id": "abc123456789xyz"}
    base.update(extra)
    return base


# --------------------------------------------------------------------------- #
# Eventos de sesión
# --------------------------------------------------------------------------- #


def test_session_start_registra_y_escanea_evidencia(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload("SessionStart", source="startup"))

    assert "session_start" in log.tipos()
    assert log.scans == 1
    assert "evidence" in log.tipos()


def test_session_end_escanea_antes_de_cerrar(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload("SessionEnd", reason="clear"))

    # La evidencia se registra antes del cierre: después el worktree puede
    # desaparecer y los mtime con él.
    assert log.tipos().index("evidence") < log.tipos().index("session_end")


def test_prompt_guarda_la_descripcion_del_pedido(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload("UserPromptSubmit", prompt="arreglar el login roto"))

    assert log.primero("prompt")["n"] == "arreglar el login roto"


def test_con_notas_apagadas_se_registra_la_duracion_sin_texto(entorno):
    tracker, log, _ = entorno
    log.notes = "off"
    tracker.handle_hook(payload("UserPromptSubmit", prompt="texto sensible"))

    assert log.primero("prompt")["n"] == ""


def test_stop_cierra_la_ventana_de_trabajo(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload("Stop", last_assistant_message="listo"))
    assert log.tipos() == ["stop"]


def test_notification_registra_el_motivo_de_la_espera(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload("Notification", notification_type="permission_request"))

    assert log.primero("notify")["n"] == "permission_request"


# --------------------------------------------------------------------------- #
# Pruebas y commits
# --------------------------------------------------------------------------- #


def test_comando_de_test_abre_intervalo_con_su_tool_use_id(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PreToolUse", tool_name="Bash", tool_use_id="toolu_1",
        tool_input={"command": "python3 -m pytest tests -q"},
    ))

    evento = log.primero("test_start")
    assert evento["id"] == "toolu_1"


def test_comando_normal_no_abre_intervalo_de_test(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PreToolUse", tool_name="Bash", tool_use_id="toolu_1",
        tool_input={"command": "git status"},
    ))

    assert "test_start" not in log.tipos()


def test_test_fallido_cierra_su_intervalo(entorno):
    """Si el cierre dependiera del éxito, un test roto quedaría contando para siempre."""
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PostToolUse", tool_name="Bash", tool_use_id="toolu_1",
        tool_input={"command": "pytest"}, tool_response={"exit_code": 1},
    ))

    assert log.primero("test_end")["ok"] is False


def test_post_tool_use_failure_tambien_cierra(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PostToolUseFailure", tool_name="Bash", tool_use_id="toolu_1",
        tool_input={"command": "pytest"}, error="boom",
    ))

    assert log.primero("test_end")["ok"] is False


def test_test_exitoso_se_registra_como_ok(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PostToolUse", tool_name="Bash", tool_use_id="toolu_1",
        tool_input={"command": "pytest"}, tool_response={"exit_code": 0},
    ))

    assert log.primero("test_end")["ok"] is True


def test_commit_exitoso_registra_su_asunto(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PostToolUse", tool_name="Bash", tool_use_id="toolu_2",
        tool_input={"command": 'git commit -m "feat: algo"'},
        tool_response={"exit_code": 0},
    ))

    assert log.primero("commit")["n"] == "feat: algo"


def test_commit_fallido_no_se_registra(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook(payload(
        "PostToolUse", tool_name="Bash", tool_use_id="toolu_2",
        tool_input={"command": "git commit -m x"}, tool_response={"exit_code": 1},
    ))

    assert "commit" not in log.tipos()


def test_con_notas_en_commits_se_guarda_el_asunto(entorno):
    tracker, log, _ = entorno
    log.notes = "commits"
    tracker.handle_hook(payload(
        "PostToolUse", tool_name="Bash", tool_use_id="toolu_2",
        tool_input={"command": "git commit -m x"}, tool_response={"exit_code": 0},
    ))

    assert "commit" in log.tipos()


# --------------------------------------------------------------------------- #
# Atribución en trabajo paralelo
# --------------------------------------------------------------------------- #


def test_trabajo_dirigido_a_otro_worktree_se_atribuye_a_esa_rama(entorno, tmp_path):
    tracker, log, git = entorno
    otro = tmp_path / "wt-otra"
    otro.mkdir()
    git.branches[str(otro)] = "feature/otra"

    tracker.handle_hook(payload(
        "PreToolUse", tool_name="Bash", tool_use_id="t",
        tool_input={"command": "git -C {0} status".format(otro)},
    ))

    actividad = log.primero("activity")
    assert actividad["branch"] == "feature/otra"


def test_trabajo_en_el_propio_worktree_no_genera_actividad_extra(entorno, tmp_path):
    tracker, log, git = entorno
    propio = tmp_path / "wt-propia"
    propio.mkdir()
    git.branches[str(propio)] = "feature/x"  # la misma rama de la sesión

    tracker.handle_hook(payload(
        "PreToolUse", tool_name="Bash", tool_use_id="t",
        tool_input={"command": "cd {0} && ls".format(propio)},
    ))

    assert "activity" not in log.tipos()


# --------------------------------------------------------------------------- #
# Degradación
# --------------------------------------------------------------------------- #


def test_registro_desactivado_no_escribe_nada(entorno):
    tracker, log, _ = entorno
    log.tracking = False
    tracker.handle_hook(payload("UserPromptSubmit", prompt="hola"))

    assert log.events == []


def test_head_desacoplado_no_registra(entorno):
    tracker, log, git = entorno
    git.branch = None
    tracker.handle_hook(payload("UserPromptSubmit", prompt="hola"))

    assert log.events == []


def test_evidencia_desactivada_no_escanea(entorno):
    tracker, log, _ = entorno
    log.evidence = False
    tracker.handle_hook(payload("SessionStart"))

    assert log.scans == 0
    assert "session_start" in log.tipos()


def test_payload_incompleto_no_explota(entorno):
    tracker, log, _ = entorno
    tracker.handle_hook({})
    tracker.handle_hook(payload("PreToolUse", tool_name="Bash"))
    tracker.handle_hook(payload("PostToolUse", tool_name="Read", tool_input={}))

    assert "test_start" not in log.tipos()


@pytest.mark.parametrize(
    "payload_dict,esperado",
    [
        ({"tool_response": {"exit_code": 0}}, False),
        ({"tool_response": {"exit_code": 2}}, True),
        ({"tool_response": {"is_error": True}}, True),
        ({"tool_response": "salida en texto"}, False),
        ({"hook_event_name": "PostToolUseFailure"}, True),
        ({}, False),
    ],
)
def test_deteccion_de_fallo_de_herramienta(tracker, payload_dict, esperado):
    assert tracker.tool_failed(payload_dict) is esperado
