from __future__ import annotations

from pathlib import Path
from typing import Optional

import clr

from utility.utils import libs_path


_DLL_PATH = libs_path() / "OpenHardwareMonitorLib.dll"
clr.AddReference(str(_DLL_PATH))

from OpenHardwareMonitor.Hardware import Computer


def get_gpu_temp() -> Optional[float]:
    """
    Returns the first GPU temperature found by OpenHardwareMonitorLib.

    The DLL is expected to sit next to this file:
        OpenHardwareMonitorLib.dll
    """
    comp = Computer()
    comp.GPUEnabled = True
    comp.Open()

    try:
        for hardware in comp.Hardware:
            hardware.Update()

            if "gpu" not in hardware.Name.lower():
                continue

            for sensor in hardware.Sensors:
                if sensor.SensorType.ToString() == "Temperature" and sensor.Value is not None:
                    return float(sensor.Value)
                
            return None
    finally:
        comp.Close()