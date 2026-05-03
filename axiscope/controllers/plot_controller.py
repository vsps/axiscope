"""Orchestrates sending paths to the AxiDraw device."""

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPainterPath

from axiscope.models.device import DeviceModel
from axiscope.models.paper import PaperSize
from axiscope.models.settings import SettingsModel


class PlotController(QObject):
    """Takes QPainterPath objects + settings and drives the AxiDraw API.

    Currently a stub — once the AxiDraw Python API is available, the
    ``_execute_plot`` method will be replaced with real device calls."""

    plot_started = Signal()
    plot_finished = Signal()

    def __init__(self, device: DeviceModel, settings: SettingsModel):
        super().__init__()
        self._device = device
        self._settings = settings
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    # -----------------------------------------------------------------
    def start_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        """Begin plotting *paths* to the device."""
        if self._busy:
            return
        if not self._device.connected:
            return
        if not paths:
            return

        self._busy = True
        self.plot_started.emit()

        # Simulate async plot with a zero-timer so the UI doesn't freeze
        QTimer.singleShot(0, lambda: self._execute_plot(paths, paper))

    # -----------------------------------------------------------------
    def _execute_plot(self, paths: list[QPainterPath], paper: PaperSize) -> None:
        """Internal — run the actual plot sequence.

        TODO: replace with axidraw API calls:
          - home / move to start
          - for each path:
              - pen up → move to start → pen down → trace path → pen up
          - return home if settings say so
        """
        # For now, just simulate a brief delay then report done.
        print(
            f"[PlotController] Plotting {len(paths)} paths "
            f"on {paper.name} ({paper.display_width}x{paper.display_height}mm)"
        )
        # In a real implementation this would be an async / threaded call.
        QTimer.singleShot(500, self._on_plot_done)

    def _on_plot_done(self) -> None:
        self._busy = False
        self.plot_finished.emit()
