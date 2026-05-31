import customtkinter as ctk


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