from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import pystray

from PIL import Image

if TYPE_CHECKING:
    from controllers.app_controller import AppController

from config import (
    APP_NAME,
    APP_VERSION,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    DEFAULT_GPU_HIGH_TEMP_THRESHOLD,
    DEFAULT_GPU_LOW_TEMP_THRESHOLD,
)

from utility.utils import assets_path


class FanControlWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.controller: AppController = None

        # Set window properties
        self.title("MSI Fan Boost Controller")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self._set_window_title()
        self._set_window_icon()

        # App State
        self.is_quitting = False

        # System Tray
        self.tray_icon = None
        self.is_hidden_to_tray = False
        self._hide_to_tray_after_id = None

        # Settings
        self.gpu_temp_var = ctk.StringVar(value="-- °C")
        self.service_status_var = ctk.StringVar(value="Disconnected")
        self.full_blast_status_var = ctk.StringVar(value="Unknown")
        self.auto_mode_var = ctk.BooleanVar(value=False)

        self.temp_on_var = ctk.StringVar(value=str(DEFAULT_GPU_HIGH_TEMP_THRESHOLD))
        self.temp_off_var = ctk.StringVar(value=str(DEFAULT_GPU_LOW_TEMP_THRESHOLD))

        # Build
        self._configure_grid()
        self._build_ui()

        self._create_tray_icon()

        # Binding
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind("<Destroy>", self._on_destroy, add=True)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

    # -------------------------------------------------------------------------
    # UI BUILD
    # -------------------------------------------------------------------------

    def _configure_grid(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

    def _build_ui(self) -> None:
        self._build_header()
        self._build_status_cards()
        self._build_content()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=24, pady=(18, 2))

        subtitle = ctk.CTkLabel(
            header,
            text="GPU temperature monitor + YAMDCC Full Blast control",
            font=ctk.CTkFont(size=13),
            text_color=("gray35", "gray70"),
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 18))

    def _build_status_cards(self) -> None:
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))

        cards.grid_columnconfigure((0, 1, 2), weight=1, uniform="cards")

        self.gpu_card = self._create_card(
            parent=cards,
            title="GPU Temperature",
            value_var=self.gpu_temp_var,
            footer="Current GPU temperature",
        )
        self.gpu_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.service_card = self._create_card(
            parent=cards,
            title="YAMDCC Service",
            value_var=self.service_status_var,
            footer="IPC connection status",
        )
        self.service_card.grid(row=0, column=1, sticky="nsew", padx=8)

        self.full_blast_card = self._create_card(
            parent=cards,
            title="Full Blast",
            value_var=self.full_blast_status_var,
            footer="Cooler Boost state",
        )
        self.full_blast_card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        full_blast_actions = ctk.CTkFrame(
            self.full_blast_card,
            width=80,
            height=20,
            fg_color="transparent",
        )
        full_blast_actions.place(anchor=ctk.NE, relx=1.0, x=-18, y=18)
        full_blast_actions.grid_propagate(False)

        full_blast_actions.grid_columnconfigure(0, weight=2)
        full_blast_actions.grid_columnconfigure(1, weight=3)
        full_blast_actions.grid_rowconfigure(0, weight=1)
        
        btn_on = ctk.CTkButton(
            full_blast_actions,
            text="ON",
            width=1,
            command=self.on_full_blast_on_clicked,
        )
        btn_on.grid(row=0, column=0, sticky=ctk.NSEW, padx=(0, 1))

        btn_off = ctk.CTkButton(
            full_blast_actions,
            text="OFF",
            width=1,
            fg_color=("gray65", "gray30"),
            hover_color=("gray55", "gray40"),
            command=self.on_full_blast_off_clicked,
        )
        btn_off.grid(row=0, column=1, sticky=ctk.NSEW, padx=(1, 0))

    def _create_card(
        self,
        parent: ctk.CTkBaseClass,
        title: str,
        value_var: ctk.StringVar,
        footer: str,
    ) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, corner_radius=16)
        frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray30", "gray70"),
        )
        title_label.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

        value_label = ctk.CTkLabel(
            frame,
            textvariable=value_var,
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        value_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 2))

        footer_label = ctk.CTkLabel(
            frame,
            text=footer,
            font=ctk.CTkFont(size=12),
            text_color=("gray35", "gray60"),
        )
        footer_label.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))

        return frame

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 18))

        content.grid_columnconfigure(0, weight=2, uniform="content")
        content.grid_columnconfigure(1, weight=3, uniform="content")
        content.grid_rowconfigure(0, weight=1)

        self._build_auto_controls(content)
        self._build_log_panel(content)

    def _build_auto_controls(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=16)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        frame.grid_columnconfigure(1, weight=1)

        title = ctk.CTkLabel(
            frame,
            text="Auto Mode",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 12))

        auto_switch = ctk.CTkSwitch(
            frame,
            text="",
            variable=self.auto_mode_var,
            command=self.on_auto_mode_changed,
        )
        auto_switch.place(anchor=ctk.NE, relx=1.0, x=48, y=18)
        auto_switch._text_label.grid_remove()

        temp_on_label = ctk.CTkLabel(frame, text="Enable at")
        temp_on_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 6))

        temp_on_entry = ctk.CTkEntry(frame, textvariable=self.temp_on_var, width=80)
        temp_on_entry.grid(row=1, column=1, sticky="ew", padx=(8, 18), pady=(0, 6))

        unit_label_1 = ctk.CTkLabel(frame, text="°C", text_color=("gray35", "gray65"))
        unit_label_1.grid(row=1, column=2, sticky="w", padx=(0, 18), pady=(0, 6))

        temp_off_label = ctk.CTkLabel(frame, text="Disable at")
        temp_off_label.grid(row=2, column=0, sticky="w", padx=18, pady=6)

        temp_off_entry = ctk.CTkEntry(frame, textvariable=self.temp_off_var, width=80)
        temp_off_entry.grid(row=2, column=1, sticky="ew", padx=(8, 18), pady=6)

        unit_label_2 = ctk.CTkLabel(frame, text="°C", text_color=("gray35", "gray65"))
        unit_label_2.grid(row=2, column=2, sticky="w", padx=(0, 18), pady=6)

        save_btn = ctk.CTkButton(
            frame,
            text="Apply Thresholds",
            command=self.on_thresholds_apply_clicked,
        )
        save_btn.grid(row=3, column=0, columnspan=3, sticky="ew", padx=18, pady=6)

        note = ctk.CTkLabel(
            frame,
            text="Recommended: use two thresholds to avoid rapid ON/OFF flickering.",
            wraplength=250,
            justify="left",
            text_color=("gray35", "gray65"),
            font=ctk.CTkFont(size=12),
        )
        note.grid(row=4, column=0, columnspan=3, sticky="w", padx=18, pady=(6, 14))

    def _build_log_panel(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=16)
        frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            frame,
            text="Logs",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))

        self.log_box = ctk.CTkTextbox(frame)
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        self.log_box.configure(state="disabled")

    def _set_window_title(self) -> None:
        self.title(f"{APP_NAME} ({APP_VERSION})")

    def _set_window_icon(self) -> None:
        icon_path = assets_path() / "icons" / "icon.ico"
        self.iconbitmap(icon_path, default=icon_path)

    def _create_tray_icon(self) -> None:
        image = Image.open(assets_path() / "icons" / "icon.ico")

        menu = pystray.Menu(
            pystray.MenuItem("Show", self._on_tray_show_window, default=True),
            pystray.MenuItem("Full Blast ON", self._on_tray_full_blast_on),
            pystray.MenuItem("Full Blast OFF", self._on_tray_full_blast_off),
            pystray.MenuItem("Quit", self._on_tray_quit),
        )

        self.tray_icon = pystray.Icon(
            "MSIFanController",
            image,
            APP_NAME,
            menu,
        )
        
        self.tray_icon.run_detached(setup=self._setup_tray_icon)

    def _setup_tray_icon(self, icon) -> None:
        icon.visible = False

    # -------------------------------------------------------------------------
    # EVENT CALLBACKS
    # -------------------------------------------------------------------------

    def _on_window_unmap(self, event=None) -> None:
        """
        Called when the window is minimized.
        If the state is 'iconic', hide to system tray.
        """

        if self.is_quitting:
            return

        # Only react to main window, not on children widgets
        if event is not None and event.widget is not self:
            return

        if self.is_hidden_to_tray or self.state() != "iconic":
            return
        
        # Prevent multiple hide_to_tray calls
        if self._hide_to_tray_after_id is not None:
            return

        self._hide_to_tray_after_id = self.after(100, self._hide_to_tray_from_minimize)

    def _on_tray_show_window(self, icon=None, item=None) -> None:
        self.after(0, self.show_from_tray)

    def _on_tray_full_blast_on(self, icon=None, item=None) -> None:
        self.after(0, self.on_full_blast_on_clicked)

    def _on_tray_full_blast_off(self, icon=None, item=None) -> None:
        self.after(0, self.on_full_blast_off_clicked)

    def _on_tray_quit(self, icon=None, item=None) -> None:
        self.after(0, self.quit_app)

    def _on_destroy(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return

        self._clear_tray_icon()

    def _clear_tray_icon(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.visible = False
                self.tray_icon.stop()
            except Exception:
                pass

            self.tray_icon = None

    # -------------------------------------------------------------------------
    # SYSTEM TRAY INTERACTION METHODS
    # -------------------------------------------------------------------------

    def _hide_to_tray_from_minimize(self) -> None:
        self._hide_to_tray_after_id = None

        if self.is_quitting or self.is_hidden_to_tray:
            return

        if self.state() == "iconic":
            self.hide_to_tray()

    def hide_to_tray(self) -> None:
        if self.is_quitting or self.is_hidden_to_tray:
            return

        if self.tray_icon is not None:
            self.tray_icon.visible = True

        self.is_hidden_to_tray = True
        self.withdraw()

        self.append_log("Application minimized to system tray.")

    def show_from_tray(self) -> None:
        self.is_hidden_to_tray = False

        self.deiconify()
        self.lift()
        self.focus_force()

        if self.tray_icon is not None:
            self.tray_icon.visible = False

        self.append_log("Application restored from tray.")

    def quit_app(self) -> None:
        if self.is_quitting:
            return
        
        self.is_quitting = True

        if self._hide_to_tray_after_id is not None:
            try:
                self.after_cancel(self._hide_to_tray_after_id)
            except Exception:
                pass

            self._hide_to_tray_after_id = None

        self._clear_tray_icon()

        self.quit()
        self.destroy()

    # -------------------------------------------------------------------------
    # PUBLIC METHODS TO CALL FROM BACKEND
    # -------------------------------------------------------------------------

    def set_gpu_temperature(self, temperature: float | int | None) -> None:
        if temperature is None:
            self.gpu_temp_var.set("-- °C")
            return

        self.gpu_temp_var.set(f"{temperature:.0f} °C")

    def set_yamdcc_connected(self, connected: bool) -> None:
        self.service_status_var.set("Connected" if connected else "Disconnected")

    def set_full_blast_state(self, enabled: bool | None) -> None:
        if enabled is None:
            self.full_blast_status_var.set("Unknown")
        else:
            self.full_blast_status_var.set("ON" if enabled else "OFF")

    def get_auto_mode_enabled(self) -> bool:
        return self.auto_mode_var.get()

    def get_thresholds(self) -> tuple[float, float]:
        temp_on = float(self.temp_on_var.get().replace(",", "."))
        temp_off = float(self.temp_off_var.get().replace(",", "."))
        return temp_on, temp_off

    def append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # -------------------------------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------------------------------

    def on_full_blast_on_clicked(self) -> None:
        if self.controller:
            self.controller.request_full_blast_on()
        else:
            self.append_log("UI: Full Blast ON requested.")

    def on_full_blast_off_clicked(self) -> None:
        if self.controller:
            self.controller.request_full_blast_off()
        else:
            self.append_log("UI: Full Blast OFF requested.")

    def on_full_blast_toggle_clicked(self) -> None:
        if self.controller:
            self.controller.request_full_blast_toggle()
        else:
            self.append_log("UI: Full Blast toggle requested.")

    def on_refresh_clicked(self) -> None:
        if self.controller:
            self.controller.refresh_now()
        else:
            self.append_log("UI: status refresh requested.")

    def on_auto_mode_changed(self) -> None:
        if self.controller:
            self.controller.on_auto_mode_changed()
        else:
            enabled = self.auto_mode_var.get()
            self.append_log(f"UI: auto mode {'enabled' if enabled else 'disabled'}.")

    def on_thresholds_apply_clicked(self) -> None:
        if self.controller:
            self.controller.on_thresholds_apply_clicked()
            return

        try:
            temp_on, temp_off = self.get_thresholds()

            if temp_off >= temp_on:
                self.append_log("Warning: disable threshold should be lower than enable threshold.")
                return

            self.append_log(f"UI: thresholds applied. ON={temp_on:.0f}°C / OFF={temp_off:.0f}°C")

        except ValueError:
            self.append_log("Error: invalid temperature threshold.")