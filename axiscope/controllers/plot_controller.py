"""Orchestrates sending paths to the AxiDraw device."""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPainterPath, QTransform

from axiscope.models.device import DeviceModel
from axiscope.models.paper import PaperSize
from axiscope.models.settings import SettingsModel


class PlotController(QObject):
    """Converts QPainterPath objects to AxiDraw draw_path calls."""

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

    def start_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        if self._busy or not self._device.connected or not paths:
            return
        self._busy = True
        self._abort = False
        self._paused = False
        self.plot_started.emit()
        QTimer.singleShot(0, lambda: self._execute_plot(paths, paper))

    def _execute_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        # Canvas coords are centred: (0,0) = page centre.
        # AxiDraw expects (0,0) = home (top-left corner).
        w_half = paper.display_width / 2
        h_half = paper.display_height / 2

        try:
            for path in paths:
                if self._abort:
                    break
                while self._paused and not self._abort:
                    time.sleep(0.05)
                if self._abort:
                    break

                # Flatten Bézier curves into polyline segments
                for poly in path.toSubpathPolygons(QTransform()):
                    if len(poly) < 2:
                        continue
                    vertices = [
                        [pt.x() + w_half, pt.y() + h_half] for pt in poly
                    ]
                    self._device.plot_polyline(vertices)
        finally:
            self._busy = False
            self.plot_finished.emit()
