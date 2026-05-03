"""User settings for pen, plot and canvas."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal


@dataclass
class PlotSettings:
    """Settings that map directly to AxiDraw plot parameters."""

    # Pen
    pen_up_height: float = 60.0  # % — 0-100
    pen_down_height: float = 40.0  # % — 0-100
    pen_up_speed: float = 75.0  # % — 0-100
    pen_down_speed: float = 50.0  # % — 0-100
    pen_up_delay: float = 200.0  # ms
    pen_down_delay: float = 200.0  # ms

    # Plot
    plot_speed: float = 50.0  # % — 0-100
    acceleration: float = 75.0  # % — 0-100
    return_home: bool = True
    auto_rotate: bool = True  # kept for future use; landscape is default
    copies: int = 1
    layer: int = 1  # SVG layer to plot

    # SVG
    stroke_width: float = 1.0  # mm — overrides all SVG stroke widths

    # Canvas
    show_grid: bool = False
    grid_spacing_mm: float = 10.0


class SettingsModel(QObject):
    """Observable settings container.  Emits changed on any mutation
    so the UI and controllers can react."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self._data = PlotSettings()

    # -- accessors -----------------------------------------------------
    @property
    def data(self) -> PlotSettings:
        return self._data

    def update(self, **kwargs) -> None:
        """Update one or more fields by keyword."""
        for key, value in kwargs.items():
            if hasattr(self._data, key):
                setattr(self._data, key, value)
        self.changed.emit()

    def reset_defaults(self) -> None:
        self._data = PlotSettings()
        self.changed.emit()
