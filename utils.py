import ctypes
from pathlib import Path
import sys


def is_bundled() -> bool:
    return (
        getattr(sys, 'frozen', False) 
        and hasattr(sys, '_MEIPASS')
    )


def root_path() -> Path:
    return Path(sys._MEIPASS) if is_bundled() else Path.cwd()
    

def assets_path() -> Path:
    return root_path() / "assets"


def is_running_as_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
    

def relaunch_as_admin() -> None:
    script_path = Path(sys.argv[0]).resolve()
    args = " ".join([f'"{arg}"' for arg in sys.argv[1:]])

    params = f'"{script_path}" {args}'

    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        None,
        1,
    )