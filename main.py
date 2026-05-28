import ctypes
import sys
from pathlib import Path

import customtkinter as ctk

from config import APPEARANCE_MODE, COLOR_THEME
from app_controller import AppController
from fan_control_window import FanControlWindow


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


def main() -> None:
    if not is_running_as_admin():
        relaunch_as_admin()
        return
    
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)

    app = FanControlWindow()
    controller = AppController(app)
    controller.start()

    app.mainloop()


if __name__ == "__main__":
    main()
