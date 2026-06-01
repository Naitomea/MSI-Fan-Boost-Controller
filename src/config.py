from utility.version import Version, BuildType


APP_NAME = "MSI Fan Boost Controller"
APP_VERSION = Version(0, 7, 0, BuildType.FINAL, 2)

WINDOW_WIDTH = 750
WINDOW_HEIGHT = 500

APPEARANCE_MODE = "system"   # "system", "dark" ou "light"
COLOR_THEME = "blue"         # "blue", "dark-blue" ou "green"

DEFAULT_AUTO_MODE = False
DEFAULT_GPU_HIGH_TEMP_THRESHOLD = 75.0
DEFAULT_GPU_LOW_TEMP_THRESHOLD = 60.0