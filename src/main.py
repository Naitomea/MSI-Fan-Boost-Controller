import customtkinter as ctk

from config import APPEARANCE_MODE, COLOR_THEME

from controllers.app_controller import AppController
from ui.fan_control_window import FanControlWindow

from utility.utils import *


def close_splash(app: ctk.CTk) -> None:
    try:
        import pyi_splash

        if pyi_splash.is_alive():
            pyi_splash.close()

        app.lift()
        app.focus_force()
    except ImportError:
        pass
    except Exception:
        pass


def main() -> None:
    if is_bundled() and not is_running_as_admin():
        relaunch_as_admin()
        return
    
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)

    app = FanControlWindow()
    controller = AppController(app)
    controller.start()

    app.after(300, lambda: close_splash(app))

    app.mainloop()


if __name__ == "__main__":
    main()
