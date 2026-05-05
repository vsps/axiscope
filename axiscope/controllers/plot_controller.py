"""Orchestrates sending paths to the AxiDraw device."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPainterPath, QTransform

from axiscope.models.device import DeviceModel
from axiscope.models.paper import PaperSize
from axiscope.models.settings import SettingsModel


class _PlotWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        device: DeviceModel,
        paths: list[QPainterPath],
        paper: PaperSize,
        abort_flag: list[bool],
    ):
        super().__init__()
        self._device = device
        self._paths = paths
        self._paper = paper
        self._abort = abort_flag  # shared mutable flag

    def run(self) -> None:
        w_half = self._paper.display_width / 2
        h_half = self._paper.display_height / 2
        try:
            for path in self._paths:
                if self._abort[0]:
                    break
                for poly in path.toSubpathPolygons(QTransform()):
                    if self._abort[0]:
                        break
                    if len(poly) < 2:
                        continue
                    vertices = [
                        [pt.x() + w_half, pt.y() + h_half] for pt in poly
                    ]
                    self._device.plot_polyline(vertices)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


class PlotController(QObject):
    plot_started = Signal()
    plot_finished = Signal()
    plot_error = Signal(str)

    def __init__(self, device: DeviceModel, settings: SettingsModel):
        super().__init__()
        self._device = device
        self._settings = settings
        self._busy = False
        self._abort_flag: list[bool] = [False]
        self._thread: QThread | None = None
        self._worker: _PlotWorker | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def abort(self) -> None:
        self._abort_flag[0] = True

    def start_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        if self._busy or not self._device.connected or not paths:
            return
        self._busy = True
        self._abort_flag = [False]
        self.plot_started.emit()

        self._worker = _PlotWorker(self._device, paths, paper, self._abort_flag)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._thread.start()

    def _on_worker_done(self) -> None:
        self._busy = False
        self.plot_finished.emit()

    def _on_worker_error(self, msg: str) -> None:
        self.plot_error.emit(msg)
