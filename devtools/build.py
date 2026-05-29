from pathlib import Path
import sys

import PyInstaller.__main__


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DIST_PATH = PROJECT_ROOT / "dist"
WORK_PATH = PROJECT_ROOT / "build"
SPEC_PATH = PROJECT_ROOT / "spec"

ASSETS_PATH = PROJECT_ROOT / "assets"


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_NAME, APP_VERSION


app_file = PROJECT_ROOT / "main.py"
app_icon_path = ASSETS_PATH / "icons" / "icon.ico"
build_name = f"{"".join(APP_NAME.split())}_{APP_VERSION.to_str("_")}"

lib_path = PROJECT_ROOT / "OpenHardwareMonitorLib.dll"

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
    f"{lib_path}:.",
])