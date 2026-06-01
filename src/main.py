import argparse

import customtkinter as ctk

from config import (
    APPEARANCE_MODE, 
    COLOR_THEME,
    APP_NAME,
    DEFAULT_AUTO_MODE,
    DEFAULT_GPU_HIGH_TEMP_THRESHOLD,
    DEFAULT_GPU_LOW_TEMP_THRESHOLD,
)

from controllers.app_controller import AppController
from ui.fan_control_window import FanControlWindow

from utility.utils import *
from utility.os.windows import *
from utility.splash import *
from utility.user_prefs import UserPrefs
from pref_keys import PrefKeys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--startup",
        action="store_true",
        help="Launch app in startup mode: hidden to tray and without splash.",
    )
    return parser.parse_args()


def init_user_prefs() -> None:
    UserPrefs.init(
        app_name=APP_NAME,
        defaults={
            PrefKeys.AUTO_MODE: DEFAULT_AUTO_MODE,
            PrefKeys.GPU_HIGH_TEMP_THRESHOLD: DEFAULT_GPU_HIGH_TEMP_THRESHOLD,
            PrefKeys.GPU_LOW_TEMP_THRESHOLD: DEFAULT_GPU_LOW_TEMP_THRESHOLD,
        },
    )


def main() -> None:
    if is_bundled() and not is_running_as_admin():
        relaunch_as_admin()
        return
    
    args = parse_args()
    
    # In case splash screen not remove,
    # close it immediately in startup mode
    if args.startup:
        close_splash()

    init_user_prefs()
    
    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)

    app = FanControlWindow()
    controller = AppController(app)
    controller.start()

    if args.startup:
        app.start_hidden_to_tray()
    else:
        app.after(300, lambda: close_splash(app))

    app.mainloop()


if __name__ == "__main__":
    main()
