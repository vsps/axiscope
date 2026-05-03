"""Dynamic controls panel with multi-layer support (up to 5 layers)."""

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

MAX_LAYERS = 5


class ToolControlsPanel(QWidget):
    """Vertical stack of control rows — one per layer — with +/- buttons
    to add/remove layers.  Rows are auto-generated from the tool's
    ``ControlDef`` list.

    Layer 0 uses ``tool.controls`` (master).  Layers 1..4 use
    ``tool.modulator_controls`` (subset — e.g. no duration/samples).

    Emits ``params_changed(dict)`` whenever any value changes.
    """

    params_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 4, 8, 4)
        self._outer.setSpacing(2)

        # Header
        header = QHBoxLayout()
        self._title_label = QLabel("")
        self._title_label.setStyleSheet("background: transparent; font-weight: bold;")
        header.addWidget(self._title_label)
        header.addStretch()

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(26, 26)
        self._add_btn.clicked.connect(self._add_layer)
        header.addWidget(self._add_btn)

        self._remove_btn = QPushButton("\u2212")
        self._remove_btn.setFixedSize(26, 26)
        self._remove_btn.clicked.connect(self._remove_layer)
        header.addWidget(self._remove_btn)
        self._outer.addLayout(header)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(2)
        self._outer.addLayout(self._rows_layout)

        self._tool: BaseTool | None = None
        self._rows: list[dict[str, QWidget]] = []

    # -----------------------------------------------------------------
    def set_tool(self, tool: BaseTool | None) -> None:
        self._clear_rows()
        if tool is None:
            self._tool = None
            self.setVisible(False)
            return
        self._tool = tool
        self._title_label.setText(tool.name)
        self._add_layer()
        self._update_buttons()
        self.setVisible(True)
        self.setMaximumHeight(220 * MAX_LAYERS + 40)
        self._emit()

    # -----------------------------------------------------------------
    def _add_layer(self) -> None:
        if len(self._rows) >= MAX_LAYERS or self._tool is None:
            return
        self._add_row()
        self._update_buttons()
        self._emit()

    def _remove_layer(self) -> None:
        if len(self._rows) <= 1:
            return
        row = self._rows.pop()
        for w in row.values():
            w.deleteLater()
        self._update_buttons()
        self._emit()

    def _update_buttons(self) -> None:
        n = len(self._rows)
        self._add_btn.setEnabled(n < MAX_LAYERS)
        self._remove_btn.setEnabled(n > 1)
        label = self._tool.name if self._tool else ""
        self._title_label.setText(f"{label}  [{n} layer{'s' if n > 1 else ''}]")

    # -----------------------------------------------------------------
    def _add_row(self) -> None:
        idx = len(self._rows)
        row_widgets: dict[str, QWidget] = {}

        # Master controls for layer 0, modulator controls for 1+
        ctrls = self._tool.controls if idx == 0 else self._tool.modulator_controls
        defaults = {c.key: c.default for c in ctrls}

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        lbl = QLabel(f"L{idx + 1}")
        lbl.setStyleSheet("background: transparent; font-size: 10px; color: #888;")
        lbl.setFixedWidth(18)
        row_layout.addWidget(lbl)

        for ctrl in ctrls:
            short = ctrl.label[:8]
            row_layout.addWidget(QLabel(short))

            if ctrl.kind == "choice":
                w: QComboBox | QDoubleSpinBox | QSpinBox = QComboBox()
                w.addItems(ctrl.choices)
                w.setCurrentIndex(int(defaults.get(ctrl.key, 0)))
                w.currentIndexChanged.connect(lambda _v: self._emit())
            elif ctrl.kind == "int":
                w = QSpinBox()
                w.setRange(int(ctrl.minimum), int(ctrl.maximum))
                w.setSingleStep(int(ctrl.step))
                w.setValue(int(defaults.get(ctrl.key, 0)))
                w.setSuffix(ctrl.suffix)
                w.setFixedWidth(140)
                w.valueChanged.connect(lambda _v: self._emit())
            else:
                w = QDoubleSpinBox()
                w.setRange(ctrl.minimum, ctrl.maximum)
                w.setSingleStep(ctrl.step)
                w.setDecimals(ctrl.decimals)
                w.setValue(defaults.get(ctrl.key, 0.0))
                w.setSuffix(ctrl.suffix)
                w.setFixedWidth(160)
                w.valueChanged.connect(lambda _v: self._emit())

            row_widgets[ctrl.key] = w
            row_layout.addWidget(w)

        row_layout.addStretch()
        self._rows_layout.addLayout(row_layout)
        self._rows.append(row_widgets)

    def _clear_rows(self) -> None:
        for row in self._rows:
            for w in row.values():
                w.deleteLater()
        self._rows.clear()
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.layout():
                _clear_layout(item.layout())

    # -----------------------------------------------------------------
    def current_params(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for i, row in enumerate(self._rows):
            for key, w in row.items():
                if isinstance(w, QComboBox):
                    result[f"{key}_{i}"] = float(w.currentIndex())
                else:
                    result[f"{key}_{i}"] = w.value()
        result["_layer_count"] = float(len(self._rows))
        return result

    @staticmethod
    def split_layers(params: dict[str, float]) -> list[dict[str, float]]:
        count = int(params.get("_layer_count", 1))
        layers: list[dict[str, float]] = []
        for i in range(count):
            layer: dict[str, float] = {}
            for key, val in params.items():
                if key.endswith(f"_{i}"):
                    layer[key[: -len(f"_{i}")]] = val
            layers.append(layer)
        return layers

    def _emit(self) -> None:
        self.params_changed.emit(self.current_params())


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
