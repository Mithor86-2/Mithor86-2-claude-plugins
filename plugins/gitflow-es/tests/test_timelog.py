"""
Tests del módulo de registro de tiempos.

Lo central: los rubros deben **partir** la línea de tiempo (suman el total) y los
tiempos muertos deben validarse contra evidencia real antes de declararse muertos.
"""

import json
import os

import pytest

BASE = 1_700_000_000.0  # epoch fijo: los tests no dependen del reloj real


@pytest.fixture
def log(timelog, tmp_path, monkeypatch):
    """timelog escribiendo en un directorio temporal."""
    monkeypatch.setattr(timelog, "log_dir", lambda cwd=None: str(tmp_path))
    return timelog


def evento(offset, tipo, **extra):
    record = {"t": BASE + offset, "e": tipo, "b": "feature/x"}
    record.update(extra)
    return record


def suma_rubros(data):
    return data["work"] + data["external"] + data["tests"] + data["wait"] + data["idle"]


# --------------------------------------------------------------------------- #
# Notas y nombres
# --------------------------------------------------------------------------- #


def test_clean_note_deja_una_sola_linea(timelog):
    assert timelog.clean_note("hola\nmundo\t  otra") == "hola mundo otra"


def test_clean_note_trunca_a_160_caracteres(timelog):
    nota = timelog.clean_note("x" * 300)
    assert len(nota) <= 160
    assert nota.endswith("…")


def test_clean_note_vacia_para_none(timelog):
    assert timelog.clean_note(None) == ""


def test_sanitize_branch(timelog):
    assert timelog.sanitize_branch("feature/login-oauth") == "feature__login-oauth"
    assert timelog.sanitize_branch("") == "sin-rama"


@pytest.mark.parametrize(
    "comando,esperado",
    [
        ("python3 -m pytest tests -q", True),
        ("npm test", True),
        ("yarn run test:unit", True),
        ("go test ./...", True),
        ("cargo test", True),
        ("git status", False),
        ("echo 'no es un test'", False),
    ],
)
def test_reconocimiento_de_comandos_de_prueba(timelog, comando, esperado):
    assert timelog.is_test_command(comando) is esperado


# --------------------------------------------------------------------------- #
# Escritura y lectura
# --------------------------------------------------------------------------- #


def test_append_y_read_eventos(log):
    assert log.append_event("feature/x", "prompt", n="hacer algo") is True
    assert log.append_event("feature/x", "stop") is True

    eventos = log.read_events("feature/x")
    assert [e["e"] for e in eventos] == ["prompt", "stop"]
    assert eventos[0]["n"] == "hacer algo"
    assert eventos[0]["b"] == "feature/x"
    assert "ts" in eventos[0]


def test_append_no_guarda_notas_vacias(log):
    log.append_event("feature/x", "stop", n="   ")
    assert "n" not in log.read_events("feature/x")[0]


def test_lineas_corruptas_no_rompen_la_lectura(log):
    log.append_event("feature/x", "prompt", n="válido")
    with open(log.log_path("feature/x"), "a", encoding="utf-8") as handle:
        handle.write("{esto no es json\n")
    log.append_event("feature/x", "stop")

    assert [e["e"] for e in log.read_events("feature/x")] == ["prompt", "stop"]


def test_cada_evento_cabe_en_una_escritura_atomica(log):
    """Una línea por debajo de PIPE_BUF es lo que hace seguro el append paralelo."""
    log.append_event("feature/x", "prompt", n="x" * 500)
    with open(log.log_path("feature/x"), "rb") as handle:
        for linea in handle:
            assert len(linea) < 4096
            json.loads(linea.decode("utf-8"))


def test_escrituras_concurrentes_no_se_pisan(log):
    """Simula dos worktrees registrando sobre la misma rama."""
    import threading

    def escribir(indice):
        for _ in range(20):
            log.append_event("feature/x", "prompt", n="worktree-{0}".format(indice))

    hilos = [threading.Thread(target=escribir, args=(i,)) for i in range(4)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    eventos = log.read_events("feature/x")
    assert len(eventos) == 80  # ninguna línea perdida ni entremezclada


def test_known_branches_ordena_por_actividad(log):
    log.append_event("feature/vieja", "prompt")
    os.utime(log.log_path("feature/vieja"), (BASE, BASE))
    log.append_event("feature/nueva", "prompt")

    assert log.known_branches()[0] == "feature/nueva"


# --------------------------------------------------------------------------- #
# Agregación
# --------------------------------------------------------------------------- #


def test_los_rubros_suman_el_total(timelog):
    eventos = [
        evento(0, "session_start"),
        evento(10, "prompt", n="pedido"),
        evento(70, "test_start", id="t1"),
        evento(100, "test_end", id="t1", ok=True),
        evento(130, "stop"),
        evento(3000, "prompt", n="segundo pedido"),
        evento(3100, "stop"),
        evento(3200, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 3200, threshold=900)

    assert data["total"] == pytest.approx(3200)
    assert suma_rubros(data) == pytest.approx(data["total"])


def test_pruebas_se_descuentan_del_trabajo(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(10, "test_start", id="t1"),
        evento(40, "test_end", id="t1", ok=True),
        evento(100, "stop"),
        evento(100, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 100)

    assert data["tests"] == pytest.approx(30)
    assert data["work"] == pytest.approx(70)
    assert data["effective"] == pytest.approx(100)


def test_pruebas_se_parean_por_tool_use_id(timelog):
    """Dos corridas solapadas no deben cruzarse."""
    eventos = [
        evento(0, "prompt"),
        evento(10, "test_start", id="a"),
        evento(20, "test_start", id="b"),
        evento(30, "test_end", id="b", ok=False),
        evento(60, "test_end", id="a", ok=True),
        evento(100, "stop"),
        evento(100, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 100)

    assert data["test_runs"] == 2
    assert data["test_ok"] == 1
    assert data["test_failed"] == 1
    assert data["tests"] == pytest.approx(50)  # unión de 10-60 y 20-30


def test_prueba_sin_cierre_se_corta_en_el_siguiente_evento(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(10, "test_start", id="a"),
        evento(40, "stop"),
        evento(40, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 40)

    assert data["tests"] == pytest.approx(30)
    assert data["estimated"] is True


def test_espera_e_inactividad_se_separan_por_el_umbral(timelog):
    """Un hueco de 30 min con umbral de 15 → 15 de espera y 15 de inactividad."""
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(1860, "prompt"),   # 30 min después
        evento(1900, "stop"),
        evento(1900, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 1900, threshold=900)

    assert data["wait"] == pytest.approx(900)
    assert data["idle_user"] == pytest.approx(900)
    assert data["idle_session"] == pytest.approx(0)
    assert data["wait_total"] == pytest.approx(1800)
    assert suma_rubros(data) == pytest.approx(data["total"])


def test_hueco_entre_sesiones_es_inactividad_de_sesion(timelog):
    eventos = [
        evento(0, "session_start"),
        evento(10, "prompt"),
        evento(60, "stop"),
        evento(70, "session_end"),
        evento(5000, "session_start"),
        evento(5010, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 5010, threshold=900)

    # El hueco largo entre sesiones no es espera del usuario.
    assert data["idle_session"] > 4000
    # Lo único que cuenta como espera son los 10 s entre abrir la sesión y el
    # primer prompt: ahí sí se estaba esperando a que el usuario escribiera.
    assert data["wait"] == pytest.approx(10)
    assert suma_rubros(data) == pytest.approx(data["total"])


# --------------------------------------------------------------------------- #
# Validación de tiempos muertos con evidencia
# --------------------------------------------------------------------------- #


def test_hueco_sin_evidencia_queda_como_tiempo_muerto(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(7200, "prompt"),
        evento(7260, "stop"),
        evento(7260, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 7260, threshold=900)

    assert data["external"] == pytest.approx(0)
    assert data["idle_user"] > 0


def test_hueco_con_archivos_modificados_se_reclasifica_como_trabajo_externo(timelog):
    """El caso que motiva el cruce: el usuario estuvo editando en su editor."""
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(3600, "evidence", p="src/app.py", m=BASE + 3000),
        evento(3600, "evidence", p="src/otro.py", m=BASE + 3300),
        evento(7200, "prompt"),
        evento(7260, "stop"),
        evento(7260, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 7260, threshold=900, margin=300, gap=600)

    assert data["external"] > 0
    assert data["evidence_files"] == 2
    assert suma_rubros(data) == pytest.approx(data["total"])


def test_evidencia_desactivada_no_reclasifica(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(3600, "evidence", p="src/app.py", m=BASE + 3000),
        evento(7200, "prompt"),
        evento(7260, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 7260, use_evidence=False)

    assert data["external"] == pytest.approx(0)


def test_commits_cuentan_como_evidencia(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(7200, "prompt"),
        evento(7260, "branch_finish"),
    ]
    data = timelog.aggregate(
        eventos, now=BASE + 7260, commit_times=[BASE + 3000], margin=300
    )

    assert data["external"] == pytest.approx(600)  # 2 × margen
    assert data["evidence_commits"] == 1


def test_escritura_masiva_no_cuenta_como_trabajo(timelog):
    """Un checkout reescribe cientos de archivos con el mismo mtime."""
    eventos = [evento(0, "prompt"), evento(60, "stop")]
    eventos += [
        evento(3600, "evidence", p="archivo-{0}.py".format(i), m=BASE + 3000 + (i % 2))
        for i in range(25)
    ]
    eventos += [evento(7200, "prompt"), evento(7260, "branch_finish")]

    data = timelog.aggregate(eventos, now=BASE + 7260)

    assert data["external"] == pytest.approx(0)


def test_mtime_en_el_futuro_se_ignora(timelog):
    eventos = [
        evento(0, "prompt"),
        evento(60, "stop"),
        evento(3600, "evidence", p="src/app.py", m=BASE + 99999),
        evento(7200, "prompt"),
        evento(7260, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 7260)

    assert data["external"] == pytest.approx(0)


def test_actividad_en_otra_rama_cuenta_como_trabajo_externo(timelog):
    """Trabajo dirigido a esta rama desde otro worktree (lote en paralelo)."""
    eventos = [
        evento(0, "branch_start", n="rama del lote"),
        evento(3600, "activity", w="/wt/feature-x"),
        evento(7200, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 7200, margin=300)

    assert data["external"] == pytest.approx(600)


# --------------------------------------------------------------------------- #
# Descripciones, actividades y presentación
# --------------------------------------------------------------------------- #


def test_descripcion_y_commits_por_actividad(timelog):
    eventos = [
        evento(0, "branch_start", n="migrar el login"),
        evento(10, "prompt", n="armar el formulario"),
        evento(50, "commit", n="feat(auth): agregar formulario"),
        evento(100, "stop"),
        evento(100, "branch_finish"),
    ]
    data = timelog.aggregate(eventos, now=BASE + 100)

    assert data["description"] == "migrar el login"
    assert data["activities"][0]["note"] == "armar el formulario"
    assert data["activities"][0]["commits"] == ["feat(auth): agregar formulario"]


def test_describe_sobreescribe_la_descripcion(timelog):
    eventos = [
        evento(0, "branch_start", n="descripción vieja"),
        evento(10, "describe", n="descripción corregida"),
        evento(20, "branch_finish"),
    ]
    assert timelog.aggregate(eventos, now=BASE + 20)["description"] == "descripción corregida"


def test_rama_abandonada_no_acumula_reloj_infinito(timelog):
    """Una rama abierta hace semanas no debe reportar semanas de inactividad."""
    eventos = [evento(0, "prompt"), evento(60, "stop")]
    data = timelog.aggregate(eventos, now=BASE + 30 * 24 * 3600, threshold=900)

    assert data["stale"] is True
    assert data["total"] < 24 * 3600


def test_sin_eventos_devuelve_vacio(timelog):
    data = timelog.aggregate([])
    assert data["total"] == 0
    assert data["activities"] == []


@pytest.mark.parametrize(
    "segundos,esperado",
    [(0, "0s"), (45, "45s"), (600, "10m"), (3600, "1h 00m"), (8040, "2h 14m")],
)
def test_format_duration(timelog, segundos, esperado):
    assert timelog.format_duration(segundos) == esperado


def test_calendar_time_no_infla_el_trabajo_paralelo(timelog):
    """Dos ramas trabajadas a la vez no suman el doble de reloj."""
    reports = [
        {"start": BASE, "end": BASE + 3600},
        {"start": BASE + 1800, "end": BASE + 5400},
    ]
    assert timelog.calendar_time(reports) == pytest.approx(5400)


# --------------------------------------------------------------------------- #
# Escaneo de evidencia
# --------------------------------------------------------------------------- #


@pytest.fixture
def repo_falso(timelog, tmp_path, monkeypatch):
    """Devuelve (timelog, ruta) con `git status` simulado."""

    def fake_status(salida):
        monkeypatch.setattr(
            timelog._gitwt, "run_git",
            lambda args, cwd=None, timeout=3: salida,
        )

    return timelog, tmp_path, fake_status


def test_scan_evidence_parsea_aunque_falte_el_espacio_inicial(repo_falso):
    """
    Regresión: `run_git` normaliza con `.strip()` y se lleva el espacio inicial
    del código de estado (" M a.txt" → "M a.txt"). Cortar por offset fijo
    devolvía rutas mutiladas y el escaneo no encontraba nada.
    """
    timelog, tmp_path, fake_status = repo_falso
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    fake_status("M a.txt\0?? b.txt\0")

    encontrados = timelog.scan_evidence(str(tmp_path), since=0)

    assert sorted(ruta for ruta, _ in encontrados) == ["a.txt", "b.txt"]


def test_scan_evidence_con_espacio_inicial_tambien_funciona(repo_falso):
    timelog, tmp_path, fake_status = repo_falso
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    fake_status(" M a.txt\0")

    assert [ruta for ruta, _ in timelog.scan_evidence(str(tmp_path), since=0)] == ["a.txt"]


def test_scan_evidence_es_incremental(repo_falso):
    """Solo devuelve lo modificado después del corte."""
    timelog, tmp_path, fake_status = repo_falso
    archivo = tmp_path / "a.txt"
    archivo.write_text("x", encoding="utf-8")
    fake_status("M a.txt\0")

    futuro = archivo.stat().st_mtime + 60
    assert timelog.scan_evidence(str(tmp_path), since=futuro) == []


def test_scan_evidence_ignora_rutas_que_ya_no_existen(repo_falso):
    timelog, tmp_path, fake_status = repo_falso
    fake_status("D borrado.txt\0")

    assert timelog.scan_evidence(str(tmp_path), since=0) == []
