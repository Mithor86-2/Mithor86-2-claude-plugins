# Tests de gitflow-es

Tests de los hooks Python del plugin (regex de seguridad e i18n).

## Requisitos

- Python 3.7+
- `pytest` (`pip install pytest`)

## Correr

Desde la raíz del repo o desde `plugins/gitflow-es`:

```bash
python3 -m pytest plugins/gitflow-es/tests -q
```

## Qué cubren

- `test_safety_check.py` — cada check del hook `safety-check.py`: force-push
  (incluida la regresión de flags cortos combinados `-fv`/`-vf`), rebase y
  borrado de ramas protegidas, `reset --hard`, `clean -f`, `--no-verify`,
  `--author`, archivos sensibles, commit en `main` y `git flow` sin init.
- `test_i18n.py` — formateo y fallbacks de `i18n.t`, presencia de claves en
  ambos idiomas y resolución de `detect_lang` por variable de entorno.
