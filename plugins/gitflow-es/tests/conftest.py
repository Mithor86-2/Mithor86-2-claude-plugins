"""
Carga los hooks (archivos con guion en el nombre, no importables como módulo
normal) vía importlib y los expone como fixtures para los tests.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"

# safety-check.py hace `import i18n`; al correr como script lo resuelve vía
# sys.path[0]. Bajo pytest replicamos eso añadiendo hooks/ al path.
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def _load(module_name: str, filename: str):
    path = HOOKS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    # i18n se importa por nombre desde safety-check; lo registramos en sys.modules
    # a través de sys.path[0] cuando corre como script. En tests basta cargarlo.
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def safety():
    return _load("safety_check", "safety-check.py")


@pytest.fixture(scope="session")
def i18n():
    return _load("i18n", "i18n.py")
