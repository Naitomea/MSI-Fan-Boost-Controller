from __future__ import annotations

import threading
from typing import Optional

from ui.fan_control_window import FanControlWindow
from core.yamdcc_client import YAMDCCClient, YAMDCCError
from core.temperature import get_gpu_temp


class AppController:
    """
    Glues together:
      - FanControlWindow: UI only
      - YAMDCCClient: YAMDCC service IPC
      - temperature.get_gpu_temp: GPU temperature provider

    The controller keeps blocking work away from the UI thread.
    """

    def __init__(
        self,
        window: FanControlWindow,
        yamdcc: YAMDCCClient | None = None,
        poll_interval_ms: int = 1000,
    ) -> None:
        self.window = window
        self.yamdcc = yamdcc or YAMDCCClient()
        self.poll_interval_ms = poll_interval_ms

        self.full_blast_enabled: Optional[bool] = None
        self._poll_running = False
        self._fan_command_running = False
        self._closed = False

        # This is the link used by FanControlWindow callbacks.
        self.window.controller = self
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.window.append_log("Application started.")
        self.refresh_now()
        self._schedule_next_poll()

    def close(self) -> None:
        self._closed = True
        self.window.destroy()

    # ------------------------------------------------------------------
    # UI callback targets
    # ------------------------------------------------------------------

    def request_full_blast_on(self) -> None:
        self._run_fan_command("on", lambda: self.yamdcc.enable_full_blast())

    def request_full_blast_off(self) -> None:
        self._run_fan_command("off", lambda: self.yamdcc.disable_full_blast())

    def request_full_blast_toggle(self) -> None:
        self._run_fan_command("toggle", lambda: self.yamdcc.toggle_full_blast())

    def refresh_now(self) -> None:
        self._refresh_service_status()
        self._poll_temperature_once()

    def on_auto_mode_changed(self) -> None:
        enabled = self.window.get_auto_mode_enabled()
        self.window.append_log(f"Auto mode {'enabled' if enabled else 'disabled'}.")

    def on_thresholds_apply_clicked(self) -> None:
        try:
            high_temp, low_temp = self.window.get_thresholds()
        except ValueError:
            self.window.append_log("Error: invalid temperature threshold.")
            return

        if low_temp >= high_temp:
            self.window.append_log("Warning: disable threshold should be lower than enable threshold.")
            return

        self.window.append_log(
            f"Thresholds applied. ON={high_temp:.0f}°C / OFF={low_temp:.0f}°C"
        )

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------

    def _refresh_service_status(self) -> None:
        connected = self.yamdcc.is_service_available()
        self.window.set_yamdcc_connected(connected)

    def _schedule_next_poll(self) -> None:
        if self._closed:
            return

        self.window.after(self.poll_interval_ms, self._poll_loop)

    def _poll_loop(self) -> None:
        if self._closed:
            return

        self._refresh_service_status()
        self._poll_temperature_once()
        self._schedule_next_poll()

    def _poll_temperature_once(self) -> None:
        if self._poll_running:
            return

        self._poll_running = True

        def worker() -> None:
            temp: float | None = None
            error: Exception | None = None

            try:
                temp = get_gpu_temp()
            except Exception as exc:
                error = exc

            self._ui(lambda: self._on_temperature_result(temp, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_temperature_result(self, temp: float | None, error: Exception | None) -> None:
        self._poll_running = False

        if error is not None:
            self.window.set_gpu_temperature(None)
            self.window.append_log(f"Temperature error: {error}")
            return

        self.window.set_gpu_temperature(temp)

        if temp is not None and self.window.get_auto_mode_enabled():
            self._handle_auto_mode(temp)

    def _handle_auto_mode(self, gpu_temp: float) -> None:
        try:
            high_temp, low_temp = self.window.get_thresholds()
        except ValueError:
            self.window.append_log("Auto mode paused: invalid thresholds.")
            return

        if low_temp >= high_temp:
            self.window.append_log("Auto mode paused: OFF threshold must be lower than ON threshold.")
            return

        if gpu_temp >= high_temp and self.full_blast_enabled is not True:
            self.window.append_log(f"GPU {gpu_temp:.0f}°C >= {high_temp:.0f}°C -> Full Blast ON.")
            self.request_full_blast_on()

        elif gpu_temp <= low_temp and self.full_blast_enabled is True:
            self.window.append_log(f"GPU {gpu_temp:.0f}°C <= {low_temp:.0f}°C -> Full Blast OFF.")
            self.request_full_blast_off()

    def _run_fan_command(self, label: str, command) -> None:
        if self._fan_command_running:
            self.window.append_log("Fan command already running, please wait.")
            return

        self._fan_command_running = True
        self.window.append_log(f"Full Blast {label} requested...")

        def worker() -> None:
            error: Exception | None = None

            try:
                command()
            except Exception as exc:
                error = exc

            self._ui(lambda: self._on_fan_command_done(label, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_fan_command_done(self, label: str, error: Exception | None) -> None:
        self._fan_command_running = False

        if error is not None:
            self.window.set_yamdcc_connected(False)

            if isinstance(error, YAMDCCError):
                self.window.append_log(f"YAMDCC error: {error}")
            else:
                self.window.append_log(f"Unexpected error: {error}")

            return

        self.window.set_yamdcc_connected(True)

        if label == "on":
            self.full_blast_enabled = True
            self.window.set_full_blast_state(True)
            self.window.append_log("Full Blast enabled.")

        elif label == "off":
            self.full_blast_enabled = False
            self.window.set_full_blast_state(False)
            self.window.append_log("Full Blast disabled.")

        else:
            # We cannot read the actual state from YAMDCC, so toggle makes it unknown.
            self.full_blast_enabled = None
            self.window.set_full_blast_state(None)
            self.window.append_log("Full Blast toggled.")

    def _ui(self, callback) -> None:
        if not self._closed:
            self.window.after(0, callback)
