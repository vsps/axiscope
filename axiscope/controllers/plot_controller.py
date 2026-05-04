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
        self._paused = False

    @property
    def busy(self) -> bool:
        return self._busy

    def abort(self) -> None:
        self._abort = True

    def pause(self) -> None:
        self._paused = not self._paused

    # -----------------------------------------------------------------
    def start_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        if self._busy or not self._device.connected or not paths:
            return

        self._busy = True
        self._abort = False
        self._paused = False
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
                    while self._paused and not self._abort:
                        time.sleep(0.1)
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

