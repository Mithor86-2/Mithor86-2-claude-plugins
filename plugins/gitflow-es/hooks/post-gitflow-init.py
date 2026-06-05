#!/usr/bin/env python3
"""
gitflow-es post-init hook (PostToolUse sobre Bash).

Cuando se acaba de ejecutar `git flow init` con éxito y el idioma de gitflow-es
todavía no está configurado, inyecta un mensaje pidiéndole a Claude que le
pregunte al usuario en qué idioma quiere los textos generados — en el mismo
turno, sin esperar al próximo SessionStart.

Mecanismo: imprime en stdout el JSON
  {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}
y sale con código 0. Si no aplica, no imprime nada (sale 0 en silencio).

Diseño:
  - Puro stdlib, compatible con Python 3.7+.
  - Fail-open: cualquier fallo interno termina en silencio (exit 0), nunca
    interrumpe el flujo.
"""

from __future__ import annotations

import json
import re
import sys

try:
    import i18n as _i18n
except Exception:  # pragma: no cover - ruta de degradación
    _i18n = None


def _tool_failed(payload: dict) -> bool:
    """
    True solo si hay evidencia clara de que el comando falló. Ante la duda
    (formato desconocido del resultado), asumimos éxito y no bloqueamos el aviso.
    """
    for key in ("tool_output", "tool_response", "tool_result"):
        result = payload.get(key)
        if isinstance(result, dict):
            code = result.get("exit_code", result.get("exitCode"))
            if isinstance(code, int) and code != 0:
                return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    if payload.get("tool_name") != "Bash":
        return

    command = (payload.get("tool_input", {}) or {}).get("command", "") or ""
    if not re.search(r"\bgit\s+flow\s+init\b", command):
        return

    if _tool_failed(payload):
        return

    if _i18n is None:
        return

    try:
        if _i18n.lang_explicitly_set():
            return  # Ya configurado: no hay nada que preguntar.
        lang = _i18n.detect_lang()
        message = _i18n.t("post_init_lang_prompt", lang)
    except Exception:
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
