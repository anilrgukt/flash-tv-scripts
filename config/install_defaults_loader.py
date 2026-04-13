from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def load_install_defaults_module() -> object:
    module_name = "flash_tv_install_defaults"
    existing_module = sys.modules.get(module_name)
    if existing_module is not None:
        return existing_module

    module_path = Path(__file__).with_name("install_defaults.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("install_defaults.py could not be loaded.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
