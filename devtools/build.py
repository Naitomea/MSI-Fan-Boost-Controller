from pathlib import Path
import sys

import PyInstaller.__main__


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIST_PATH = PROJECT_ROOT / "dist"
WORK_PATH = PROJECT_ROOT / "build"
SPEC_PATH = PROJECT_ROOT / "spec"

SRC_PATH = PROJECT_ROOT / "src"
ASSETS_PATH = PROJECT_ROOT / "assets"
LIBS_PATH = PROJECT_ROOT / "libs"


if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config import APP_NAME, APP_VERSION
from utility.utils import remove_whitespaces


app_file = SRC_PATH / "main.py"
app_icon_path = ASSETS_PATH / "icons" / "icon.ico"
build_name = f"{remove_whitespaces(APP_NAME)}_{APP_VERSION.to_str("_")}"

PyInstaller.__main__.run([
    str(app_file),
    "--onefile",
    "--windowed",
    "--uac-admin",
    "--name",
    build_name,
    "--icon",
    str(app_icon_path),
    "--distpath",
    str(DIST_PATH),
    "--workpath",
    str(WORK_PATH),
    "--specpath",
    str(SPEC_PATH),
    "--add-data",
    f"{app_icon_path}:assets/icons/",
    "--add-data",
    f"{LIBS_PATH}:libs/",
])