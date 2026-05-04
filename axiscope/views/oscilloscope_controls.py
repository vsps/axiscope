"""Custom grid controls panel for the Oscilloscope tool."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from axiscope.tools.base_tool import BaseTool

# Grid layout: each row is (label, [keys...])
GRID_ROWS = [
    (
        "SIGNAL",
        [
            "carrier_freq",
            "carrier_wave",
            "fm_freq",
            "fm_amount",
            "am_freq",
            "am_amount",
        ],
    ),
    ("ADSR", ["bypass_adsr", "attack", "decay", "sustain", "release"]),
    (
        "RENDER",
        [
            "mode",
            "y_ratio",
            "duration",
            "samples_per_rev",
            "fit",
            "final_scale",
            "center_x",
            "center_y",
        ],
    ),
]


class _ShiftDoubleSpinBox(QDoubleSpinBox):
    """Arrow/wheel = 1, Shift = 10, Ctrl = 100.  Reads modifiers live."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSingleStep(1.0)

    def _mult(self) -> int:
        from PySide6.QtWidgets import QApplication
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            return 100
        if mods & Qt.ShiftModifier:
            return 10
        return 1

    def stepBy(self, steps: int):
        super().stepBy(steps * self._mult())


class _ShiftIntSpinBox(QSpinBox):
    """Arrow/wheel = 1, Shift = 10, Ctrl = 100.  Reads modifiers live."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSingleStep(1)

    def _mult(self) -> int:
        from PySide6.QtWidgets import QApplication
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ControlModifier:
            return 100
        if mods & Qt.ShiftModifier:
            return 10
        return 1

    def stepBy(self, steps: int):
        super().stepBy(steps * self._mult())


class OscilloscopeControls(QWidget):
    """Grid-based control panel for the Oscilloscope tool.

    Emits ``params_changed(dict)`` whenever any value changes.
    """

    params_changed = Signal(dict)

    def __init__(self, tool: BaseTool, parent: QWidget | None = None):
        super().__init__(parent)
        self._tool = tool
        self._widgets: dict[str, QWidget] = {}
        self._y_ratio_cell: QWidget | None = None
        self._adsr_cells: list[QWidget] = []
        self._play_btn: QPushButton | None = None

        grid = QGridLayout(self)
        grid.setContentsMargins(8, 4, 8, 4)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(7, 1)

        defaults = {c.key: c.default for c in tool.controls}

        for row_idx, (label, keys) in enumerate(GRID_ROWS):
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "background: transparent; font-weight: bold; color: #aaa;"
                "font-size: 11px;"
            )
            grid.addWidget(lbl, row_idx, 0)

            for col_idx, key in enumerate(keys):
                ctrl = self._find_ctrl(key)
                if ctrl is None:
                    continue

                cell = QWidget()
                cell.setStyleSheet("background: transparent;")
                cell_lay = QVBoxLayout(cell)
                cell_lay.setContentsMargins(0, 0, 0, 0)
                cell_lay.setSpacing(1)

                header = QLabel(ctrl.label)
                header.setStyleSheet(
                    "background: transparent; font-size: 10px; color: #888;"
                )
                cell_lay.addWidget(header)

                if ctrl.kind == "choice":
                    w: QComboBox | QDoubleSpinBox | QSpinBox = QComboBox()
                    w.addItems(ctrl.choices)
                    w.setCurrentIndex(int(defaults.get(ctrl.key, 0)))
                    w.setFixedWidth(100)
                    w.currentIndexChanged.connect(self._emit)
                    if ctrl.key == "mode":
                        w.currentIndexChanged.connect(self._update_y_ratio_visible)
                elif ctrl.kind == "int":
                    w = _ShiftIntSpinBox()
                    w.setRange(int(ctrl.minimum), int(ctrl.maximum))
                    w.setValue(int(defaults.get(ctrl.key, 0)))
                    w.setSuffix(ctrl.suffix)
                    w.setFixedWidth(100)
                    w.valueChanged.connect(lambda _v: self._emit())
                else:
                    w = _ShiftDoubleSpinBox()
                    w.setRange(ctrl.minimum, ctrl.maximum)
                    w.setDecimals(ctrl.decimals)
                    w.setValue(defaults.get(ctrl.key, 0.0))
                    w.setSuffix(ctrl.suffix)
                    w.setFixedWidth(100)
                    w.valueChanged.connect(lambda _v: self._emit())

                cell_lay.addWidget(w)
                self._widgets[ctrl.key] = w
                grid.addWidget(cell, row_idx, col_idx + 1)

                if ctrl.key == "y_ratio":
                    self._y_ratio_cell = cell
                if ctrl.key in ("attack", "decay", "sustain", "release"):
                    self._adsr_cells.append(cell)

        self._play_btn = QPushButton("\u25b6 Play")
        self._play_btn.setFixedWidth(90)
        self._play_btn.setStyleSheet(
            "QPushButton { background: #2a6030; border: 1px solid #4a8; "
            "color: #cfc; }"
            "QPushButton:hover { background: #357040; }"
            "QPushButton:pressed { background: #408050; }"
            "QPushButton:disabled { background: #333; border-color: #555; "
            "color: #666; }"
        )
        self._play_btn.clicked.connect(self._on_play)
        grid.addWidget(self._play_btn, 3, 2)

        self._update_y_ratio_visible()

        try:
            import sounddevice  # noqa: F401

            self._has_audio = True
        except ImportError:
            self._has_audio = False
            self._play_btn.setEnabled(False)
            self._play_btn.setToolTip("Install 'sounddevice' for audio preview")

        self.setMaximumHeight(200)

    # -----------------------------------------------------------------
    def _find_ctrl(self, key: str):
        for c in self._tool.controls:
            if c.key == key:
                return c
        return None

    def _update_y_ratio_visible(self) -> None:
        mode_w = self._widgets.get("mode")
        visible = (
            mode_w is not None and getattr(mode_w, "currentIndex", lambda: 0)() == 1
        )
        if self._y_ratio_cell is not None:
            self._y_ratio_cell.setVisible(visible)

    def _emit(self) -> None:
        self.params_changed.emit(self.current_params())

    def current_params(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for key, w in self._widgets.items():
            if isinstance(w, QComboBox):
                result[key] = float(w.currentIndex())
            else:
                result[key] = w.value()
        bypass = int(result.get("bypass_adsr", 1))
        for cell in self._adsr_cells:
            cell.setEnabled(bypass == 1)
        return result

    # -----------------------------------------------------------------
    def _on_play(self) -> None:
        if not self._has_audio:
            return
        import threading

        params = self.current_params()
        self._play_btn.setEnabled(False)
        self._play_btn.setText("\u25b6 ...")

        def _play_thread():
            try:
                import sounddevice as sd

                audio = self._tool.generate_audio(params)
                if audio is not None:
                    sd.play(audio, 44100)
                    sd.wait()
            except Exception:
                pass
            finally:
                self._play_btn.setEnabled(True)
                self._play_btn.setText("\u25b6 Play")

        threading.Thread(target=_play_thread, daemon=True).start()
