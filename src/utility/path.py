from pathlib import Path
import sys

from .utils import is_bundled


def root_path() -> Path:
    return Path(sys._MEIPASS) if is_bundled() else Path.cwd()
    

def assets_path() -> Path:
    return root_path() / "assets"
    

def libs_path() -> Path:
    return root_path() / "libs"