"""Single-row minimal toolbar."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class Toolbar(QWidget):
    """Top bar: gear, paper, load SVG, save SVG, drawing tool."""

    paper_changed = Signal(str)
    load_svg_clicked = Signal()
    save_svg_clicked = Signal()
    tool_changed = Signal(str)
    settings_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Gear button
        self._gear_btn = QPushButton("\u2699")
        self._gear_btn.setFixedSize(32, 32)
        self._gear_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self._gear_btn)

        layout.addWidget(self._sep())

        # Paper size
        layout.addWidget(QLabel("Paper:"))
        self._paper_combo = QComboBox()
        self._paper_combo.addItems(
            ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10"]
        )
        self._paper_combo.setCurrentText("A1")
        self._paper_combo.currentTextChanged.connect(self.paper_changed)
        layout.addWidget(self._paper_combo)

        layout.addWidget(self._sep())

        # Load SVG
        self._load_btn = QPushButton("Load SVG")
        self._load_btn.clicked.connect(self.load_svg_clicked)
        layout.addWidget(self._load_btn)

        # Save SVG
        self._save_btn = QPushButton("Save SVG")
        self._save_btn.clicked.connect(self.save_svg_clicked)
        layout.addWidget(self._save_btn)

        layout.addWidget(self._sep())

        # Drawing tool
        layout.addWidget(QLabel("Tool:"))
        self._tool_combo = QComboBox()
        self._tool_combo.addItem("None")
        self._tool_combo.addItem("Oscilloscope")
        self._tool_combo.currentTextChanged.connect(self.tool_changed)
        layout.addWidget(self._tool_combo)

        layout.addStretch()

    def current_paper(self) -> str:
        return self._paper_combo.currentText()

    def current_tool(self) -> str:
        return self._tool_combo.currentText()

    # -----------------------------------------------------------------
    @staticmethod
    def _sep() -> QWidget:
        w = QWidget()
        w.setFixedWidth(1)
        w.setStyleSheet("background: #555;")
        return w
