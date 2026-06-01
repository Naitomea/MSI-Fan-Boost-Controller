import base64
import ctypes
from pathlib import Path
import subprocess
import sys
from typing import Optional

from utility.string import remove_whitespaces
from utility.utils import is_bundled

from config import APP_NAME


# -------------------------------------------------------------------------
# ADMIN PUBLIC API
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
# POWERSHELL HELPERS
# -------------------------------------------------------------------------

def _ps_quote(value: str | Path) -> str:
    """
    Quote a value for PowerSheel with single quotes.
    """
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _ps_encode(script: str) -> str:
    """
    To use with ***PowerShell -EncodedCommand***
    which expects Base64 encoding in UTF-16LE.
    """
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _run_powershell_script(script: str) -> None:
    encoded_script = _ps_encode(script)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_script,
        ],
        capture_output=True,
        text=True,
        errors="replace",
        shell=False,
        creationflags=_get_subprocess_creationflags(),
    )

    if result.returncode != 0:
        raise RuntimeError(
            "PowerShell command failed.\n"
            f"returncode: {result.returncode}\n\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )
    

# -------------------------------------------------------------------------
# STARTUP HELPERS
# -------------------------------------------------------------------------

def _get_startup_task_name(task_name: Optional[str] = None) -> str:
    return (
        task_name 
        if task_name is not None else 
        f"{remove_whitespaces(APP_NAME)}_startup"
    )


def _get_app_launch_info(*args) -> tuple[Path, str, Path]:
    """
    Get the information needed to launch the application

    :return: executable to launch, arguments, working directory
    :rtype: tuple(Path, str, Path)
    """

    args_str = " ".join(str(arg) for arg in args)

    if is_bundled():
        app_exe = Path(sys.executable).resolve()
        return app_exe, args_str, app_exe.parent

    # Dev mode
    project_dir = Path(__file__).resolve().parents[3]

    pythonw_exe = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    python_exe = project_dir / ".venv" / "Scripts" / "python.exe"
    main_script = project_dir / "src" / "main.py"

    # Prevent showing console in dev mode with pythonw, 
    # fallback to python.exe.
    launcher = pythonw_exe if pythonw_exe.exists() else python_exe

    dev_args = f'"{main_script}"'
    if args_str:
        dev_args += f" {args_str}"

    return launcher, dev_args, project_dir


def _build_startup_launcher_script(
    *app_args: str,
    splash_screen: bool,
) -> str:
    """
    PowerShell script that launches the application.

    **If splash_screen=False:**
        add *PYINSTALLER_SUPPRESS_SPLASH_SCREEN=1* before launches the app.
    """
    app_exe, app_args_str, working_dir = _get_app_launch_info(*app_args)

    lines = [
        "$ErrorActionPreference = 'Stop'",
        "$psi = New-Object System.Diagnostics.ProcessStartInfo",
        f"$psi.FileName = {_ps_quote(app_exe)}",
        f"$psi.Arguments = {_ps_quote(app_args_str)}",
        f"$psi.WorkingDirectory = {_ps_quote(working_dir)}",
        "$psi.UseShellExecute = $false",
        "$psi.CreateNoWindow = $true",
    ]

    if not splash_screen:
        lines.append(
            "$psi.EnvironmentVariables['PYINSTALLER_SUPPRESS_SPLASH_SCREEN'] = '1'"
        )

    lines.append("[System.Diagnostics.Process]::Start($psi) | Out-Null")

    return "; ".join(lines)


def _build_register_startup_task_script(
    task_name: str,
    *app_args: str,
    splash_screen: bool,
) -> str:
    """
    PowerShell script that records the scheduled task.
    """
    launcher_script = _build_startup_launcher_script(
        *app_args,
        splash_screen=splash_screen,
    )

    encoded_launcher_script = _ps_encode(launcher_script)

    launcher_args = (
        "-NoProfile "
        "-ExecutionPolicy Bypass "
        "-WindowStyle Hidden "
        f"-EncodedCommand {encoded_launcher_script}"
    )

    return (
        "$ErrorActionPreference = 'Stop'; "
        "$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name; "
        f"$taskName = {_ps_quote(task_name)}; "
        "$action = New-ScheduledTaskAction "
        "-Execute 'powershell.exe' "
        f"-Argument {_ps_quote(launcher_args)}; "
        "$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity; "
        "$principal = New-ScheduledTaskPrincipal "
        "-UserId $identity "
        "-LogonType Interactive "
        "-RunLevel Highest; "
        "$settings = New-ScheduledTaskSettingsSet "
        "-AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries; "
        "Register-ScheduledTask "
        "-TaskName $taskName "
        "-Action $action "
        "-Trigger $trigger "
        "-Principal $principal "
        "-Settings $settings "
        "-Force | Out-Null"
    )


# -------------------------------------------------------------------------
# STARTUP PUBLIC API
# -------------------------------------------------------------------------

def enable_startup(
    *app_args: str,
    splash_screen: bool = False,
    task_name: Optional[str] = None,
) -> None:
    """
    Enable automatic startup when Windows starts.

    **Recommended Example:**
        *enable_startup("--startup")*

    **With splash:**
        *enable_startup("--startup", splash_screen=True)*
    """
    resolved_task_name = _get_startup_task_name(task_name)

    script = _build_register_startup_task_script(
        resolved_task_name,
        *app_args,
        splash_screen=splash_screen,
    )

    _run_powershell_script(script)


def disable_startup(task_name: Optional[str] = None) -> None:
    resolved_task_name = _get_startup_task_name(task_name)

    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$taskName = {_ps_quote(resolved_task_name)}; "
        "if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { "
        "Unregister-ScheduledTask -TaskName $taskName -Confirm:$false "
        "}"
    )

    _run_powershell_script(script)


def is_startup_enabled(task_name: Optional[str] = None) -> bool:
    resolved_task_name = _get_startup_task_name(task_name)

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                f"if (Get-ScheduledTask -TaskName {_ps_quote(resolved_task_name)} "
                "-ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
            ),
        ],
        capture_output=True,
        text=True,
        errors="replace",
        shell=False,
        creationflags=_get_subprocess_creationflags(),
    )

    return result.returncode == 0


# -------------------------------------------------------------------------
# SUBPROCESS HELPERS
# -------------------------------------------------------------------------

def _get_subprocess_creationflags() -> int:
    if sys.platform.startswith("win"):
        return subprocess.CREATE_NO_WINDOW

    return 0