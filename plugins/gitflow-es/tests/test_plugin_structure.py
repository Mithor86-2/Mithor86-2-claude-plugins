"""
Tests estructurales del plugin: frontmatter de skills y agentes, rutas
referenciadas que existen, hooks declarados que apuntan a archivos reales y
versión sincronizada entre plugin.json y el marketplace.

Son baratos y atrapan justo los errores que no se ven hasta que el plugin se
instala en otra máquina.
"""

import json
import re
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent

SKILLS = sorted(PLUGIN_ROOT.glob("skills/*/SKILL.md"))
AGENTS = sorted(PLUGIN_ROOT.glob("agents/*.md"))


def parse_frontmatter(path: Path) -> dict:
    """Parsea el frontmatter YAML plano (clave: valor) de un .md."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "{0} no arranca con frontmatter".format(path.name)
    end = text.index("\n---\n", 4)
    block = text[4:end]

    data = {}
    key = None
    for line in block.splitlines():
        match = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            data[key] = match.group(2).strip()
        elif key and line.strip():
            # Continuación de una descripción multilínea.
            data[key] = "{0} {1}".format(data[key], line.strip()).strip()
    return data


def test_hay_skills_y_agentes():
    assert SKILLS, "no se encontró ningún SKILL.md"
    assert AGENTS, "no se encontró ningún agente"


@pytest.mark.parametrize("skill_path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_tiene_frontmatter_valido(skill_path):
    data = parse_frontmatter(skill_path)

    assert data.get("name") == skill_path.parent.name, (
        "el name del frontmatter debe coincidir con la carpeta del skill"
    )
    description = data.get("description", "")
    assert len(description) >= 40, "la descripción debe explicar cuándo usar el skill"


@pytest.mark.parametrize("agent_path", AGENTS, ids=lambda p: p.stem)
def test_agente_tiene_frontmatter_valido(agent_path):
    data = parse_frontmatter(agent_path)

    assert data.get("name") == agent_path.stem
    assert len(data.get("description", "")) >= 40


@pytest.mark.parametrize(
    "doc_path",
    SKILLS + AGENTS + sorted(PLUGIN_ROOT.glob("rules/*.md")),
    ids=lambda p: "{0}/{1}".format(p.parent.name, p.name),
)
def test_rutas_relativas_referenciadas_existen(doc_path):
    """
    Las rules y skills se referencian entre sí con rutas relativas (`../../rules/
    git-flow.md`). Si una se mueve o se renombra, el modelo termina leyendo una
    ruta muerta y aplicando la política equivocada.
    """
    text = doc_path.read_text(encoding="utf-8")
    referencias = set(re.findall(r"`((?:\.\./)+[A-Za-z0-9_./-]+\.md)`", text))

    for referencia in referencias:
        destino = (doc_path.parent / referencia).resolve()
        assert destino.exists(), "{0} referencia una ruta inexistente: {1}".format(
            doc_path.name, referencia
        )


def test_hooks_declarados_existen():
    """Cada comando declarado en hooks.json debe apuntar a un script real."""
    config = json.loads((PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))

    declarados = 0
    for event, entries in config.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                command = hook.get("command", "")
                for nombre in re.findall(r"hooks/([A-Za-z0-9_-]+\.py)", command):
                    declarados += 1
                    assert (PLUGIN_ROOT / "hooks" / nombre).exists(), (
                        "{0} declara hooks/{1}, que no existe".format(event, nombre)
                    )
    assert declarados > 0, "hooks.json no declara ningún script"


def test_version_sincronizada_entre_plugin_y_marketplace():
    plugin = json.loads(
        (PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads(
        (REPO_ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )

    entrada = next(
        (p for p in marketplace["plugins"] if p["name"] == plugin["name"]), None
    )
    assert entrada is not None, "el plugin no está listado en el marketplace"
    assert entrada["version"] == plugin["version"], (
        "marketplace.json y plugin.json declaran versiones distintas"
    )


def test_changelog_documenta_la_version_actual():
    plugin = json.loads(
        (PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[{0}]".format(plugin["version"]) in changelog, (
        "la versión actual no tiene entrada en el CHANGELOG"
    )
