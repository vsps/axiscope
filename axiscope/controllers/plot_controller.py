"""Orchestrates sending paths to the AxiDraw device."""

from __future__ import annotations

import math
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPainterPath

from axiscope.models.device import DeviceModel
from axiscope.models.paper import PaperSize
from axiscope.models.settings import SettingsModel

# AxiDraw V3/A5: ~80 steps/mm at default microstepping
STEPS_PER_MM = 80.0
# Maximum XY speed in mm/s (conservative default)
DEFAULT_SPEED_MM_S = 50.0
# Minimum segment duration in ms (EBB floor)
MIN_SEGMENT_MS = 2


class PlotController(QObject):
    """Converts QPainterPath objects to EBB stepper-move commands."""

    plot_started = Signal()
    plot_finished = Signal()

    def __init__(self, device: DeviceModel, settings: SettingsModel):
        super().__init__()
        self._device = device
        self._settings = settings
        self._busy = False
        self._abort = False

    @property
    def busy(self) -> bool:
        return self._busy

    def abort(self) -> None:
        self._abort = True

    # -----------------------------------------------------------------
    def start_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        if self._busy or not self._device.connected or not paths:
            return

        self._busy = True
        self._abort = False
        self.plot_started.emit()
        QTimer.singleShot(0, lambda: self._execute_plot(paths, paper))

    # -----------------------------------------------------------------
    def _execute_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        speed = self._settings.data.plot_speed or DEFAULT_SPEED_MM_S
        pen_up_pos = self._settings.data.pen_up_height
        pen_down_pos = self._settings.data.pen_down_height

        self._ebb("EM,1\r")  # enable motors
        time.sleep(0.05)

        try:
            for pi, path in enumerate(paths):
                if self._abort:
                    break
                n = path.elementCount()
                if n < 2:
                    continue

                # -- pen up, move to first point --
                self._ebb(f"SP,{pen_up_pos}\r")
                time.sleep(0.2)
                px, py = path.elementAt(0).x, path.elementAt(0).y
                self._move_to(px, py, speed * 2)
                time.sleep(0.05)

                # -- pen down, trace path --
                self._ebb(f"SP,{pen_down_pos}\r")
                time.sleep(0.2)

                for i in range(1, n):
                    if self._abort:
                        break
                    ex, ey = path.elementAt(i).x, path.elementAt(i).y
                    self._move_to(ex, ey, speed)

                # -- pen up after path --
                self._ebb(f"SP,{pen_up_pos}\r")
                time.sleep(0.15)

        finally:
            if not self._abort:
                self._ebb("SP,0\r")  # pen up
            self._busy = False
            self.plot_finished.emit()

    # -----------------------------------------------------------------
    def _move_to(self, x_mm: float, y_mm: float, speed_mm_s: float) -> None:
        """Send an SM command to move to (*x_mm*, *y_mm*) at the given speed."""
        sx = int(round(x_mm * STEPS_PER_MM))
        sy = int(round(y_mm * STEPS_PER_MM))

        # Get current position from device tracking
        cx = self._device._x or 0
        cy = self._device._y or 0

        dx = abs(sx - cx)
        dy = abs(sy - cy)
        dist_mm = math.sqrt(
            (x_mm - cx / STEPS_PER_MM) ** 2 + (y_mm - cy / STEPS_PER_MM) ** 2
        )
        if dist_mm < 0.001:
            return

        dur_ms = max(MIN_SEGMENT_MS, int(dist_mm / speed_mm_s * 1000))
        self._ebb(f"SM,{dur_ms},{sx - cx},{sy - cy}\r")
        self._device._x, self._device._y = sx, sy

    def _ebb(self, cmd: str) -> None:
        """Send a raw command to the EBB (fire-and-forget)."""
        if self._device._ser and self._device._ser.is_open:
            try:
                self._device._ser.reset_input_buffer()
                self._device._ser.write(cmd.encode("ascii"))
                # Small delay so EBB can process
                time.sleep(0.005)
            except Exception:
                pass
