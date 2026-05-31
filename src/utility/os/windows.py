import ctypes
from pathlib import Path
import subprocess
import sys
from typing import Optional

from utility.string import remove_whitespaces
from utility.utils import is_bundled

from config import APP_NAME


# -------------------------------------------------------------------------
# ADMIN
# -------------------------------------------------------------------------

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

# -------------------------------------------------------------------------
# STARTUP
# -------------------------------------------------------------------------

def get_launch_app_command() -> str:
    """
    Get the command to launch the app.

    **Bundled mode with PyInstaller:**
        *sys.executable = path to .exe*

    **Dev mode (script) :**
        *sys.executable = python.exe / pythonw.exe*
        *sys.argv[0] = main.py*
    """

    exe_path = Path(sys.executable).resolve()

    # Bundled
    if is_bundled():
        return f'"{exe_path}"'

    # Script only
    script_path = Path(sys.argv[0]).resolve()
    return f'"{exe_path}" "{script_path}"'


def enable_startup(task_name: Optional[str] = None) -> None:
    command = get_launch_app_command()
    task_name = (
        task_name 
        if task_name is not None else 
        remove_whitespaces(APP_NAME)
    )

    subprocess.run(
        [
            "schtasks",
            "/Create",
            "/TN", task_name,
            "/TR", command,
            "/SC", "ONLOGON",
            "/RL", "HIGHEST",
            "/F",
        ],
        check=True,
        shell=False,
        creationflags=_get_subprocess_creationflags(),
    )


def disable_startup(task_name: Optional[str] = None) -> None:
    task_name = (
        task_name 
        if task_name is not None else 
        remove_whitespaces(APP_NAME)
    )

    subprocess.run(
        [
            "schtasks",
            "/Delete",
            "/TN", task_name,
            "/F",
        ],
        check=True,
        shell=False,
        creationflags=_get_subprocess_creationflags(),
    )


def is_startup_enabled(task_name: Optional[str] = None) -> bool:
    task_name = (
        task_name 
        if task_name is not None else 
        remove_whitespaces(APP_NAME)
    )

    result = subprocess.run(
        [
            "schtasks",
            "/Query",
            "/TN", task_name,
        ],
        capture_output=True,
        text=True,
        shell=False,
        creationflags=_get_subprocess_creationflags(),
    )

    return result.returncode == 0

def _get_subprocess_creationflags() -> int:
    if sys.platform.startswith("win"):
        return subprocess.CREATE_NO_WINDOW

    return 0