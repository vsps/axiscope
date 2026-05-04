"""Custom 3-line controls panel for the Oscilloscope tool.

Line 1 — SIGNAL : carrier Hz / wave / FM Hz / FM % / AM Hz / AM %
Line 2 — ADSR   : attack % / decay % / sustain % / release %
Line 3 — RENDER : dur / smp/rev / fit / scale / cx% / cy% / [▶ Play]
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from axiscope.tools.base_tool import BaseTool


class OscilloscopeControls(QWidget):
    """Three-row custom control panel for the Oscilloscope tool.

    Emits ``params_changed(dict)`` whenever any value changes.
    """

    params_changed = Signal(dict)

    def __init__(self, tool: BaseTool, parent: QWidget | None = None):
        super().__init__(parent)
        self._tool = tool
        self._widgets: dict[str, QWidget] = {}
        self._play_btn: QPushButton | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(2)

        # -- Row labels -------------------------------------------------
        for label, keys in [
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
            ("ADSR", ["attack", "decay", "sustain", "release"]),
            (
                "RENDER",
                [
                    "duration",
                    "samples_per_rev",
                    "fit",
                    "final_scale",
                    "center_x",
                    "center_y",
                ],
            ),
        ]:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(label)
            lbl.setStyleSheet(
                "background: transparent; font-weight: bold; color: #aaa;"
                "font-size: 11px;"
            )
            lbl.setFixedWidth(52)
            row.addWidget(lbl)

            for key in keys:
                ctrl = self._find_ctrl(key)
                if ctrl is None:
                    continue

                defaults = {c.key: c.default for c in tool.controls}

                row.addWidget(QLabel(ctrl.label[:7]))

                if ctrl.kind == "choice":
                    w: QComboBox | QDoubleSpinBox | QSpinBox = QComboBox()
                    w.addItems(ctrl.choices)
                    w.setCurrentIndex(int(defaults.get(ctrl.key, 0)))
                    w.currentIndexChanged.connect(self._emit)
                elif ctrl.kind == "int":
                    w = QSpinBox()
                    w.setRange(int(ctrl.minimum), int(ctrl.maximum))
                    w.setSingleStep(int(ctrl.step))
                    w.setValue(int(defaults.get(ctrl.key, 0)))
                    w.setSuffix(ctrl.suffix)
                    w.setFixedWidth(120)
                    w.valueChanged.connect(lambda _v: self._emit())
                else:
                    w = QDoubleSpinBox()
                    w.setRange(ctrl.minimum, ctrl.maximum)
                    w.setSingleStep(ctrl.step)
                    w.setDecimals(ctrl.decimals)
                    w.setValue(defaults.get(ctrl.key, 0.0))
                    w.setSuffix(ctrl.suffix)
                    w.setFixedWidth(120)
                    w.valueChanged.connect(lambda _v: self._emit())

                self._widgets[ctrl.key] = w
                row.addWidget(w)

            row.addStretch()
            root.addLayout(row)

        # -- Play button ------------------------------------------------
        play_row = QHBoxLayout()
        play_row.setSpacing(8)
        play_row.addStretch()
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
        play_row.addWidget(self._play_btn)
        play_row.addStretch()
        root.addLayout(play_row)

        # Check sounddevice availability
        try:
            import sounddevice  # noqa: F401

            self._has_audio = True
        except ImportError:
            self._has_audio = False
            self._play_btn.setEnabled(False)
            self._play_btn.setToolTip("Install 'sounddevice' for audio preview")

        self.setMaximumHeight(150)

    # -----------------------------------------------------------------
    def _find_ctrl(self, key: str):
        for c in self._tool.controls:
            if c.key == key:
                return c
        return None

    def _emit(self) -> None:
        self.params_changed.emit(self.current_params())

    def current_params(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for key, w in self._widgets.items():
            if isinstance(w, QComboBox):
                result[key] = float(w.currentIndex())
            else:
                result[key] = w.value()
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
