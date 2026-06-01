from typing import Optional

import customtkinter as ctk


def close_splash(app: Optional[ctk.CTk] = None) -> None:
    try:
        import pyi_splash

        if pyi_splash.is_alive():
            pyi_splash.close()

        if app is not None:
            app.lift()
            app.focus_force()
    except ImportError:
        pass
    except Exception:
        pass