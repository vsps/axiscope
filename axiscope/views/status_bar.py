"""Bottom status bar with device info and action buttons."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class StatusBar(QWidget):
    """Status text on the left, action buttons on the right."""

    toggle_motors_clicked = Signal()
    toggle_pen_clicked = Signal()
    plot_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 8, 2)
        layout.setSpacing(12)

        # Status label
        self._status_label = QLabel("DISCONNECTED")
        self._status_label.setStyleSheet("color: #f44;")
        layout.addWidget(self._status_label)

        # Separator
        self._sep1 = QLabel("|")
        layout.addWidget(self._sep1)

        # Device info
        self._device_label = QLabel("USB: --")
        layout.addWidget(self._device_label)

        # Separator
        self._sep2 = QLabel("|")
        layout.addWidget(self._sep2)

        # Position
        self._pos_label = QLabel("X/Y: (---, ---)")
        layout.addWidget(self._pos_label)

        layout.addStretch()

        # Action buttons
        self._motor_btn = QPushButton("Toggle Motors")
        self._motor_btn.clicked.connect(self.toggle_motors_clicked)
        layout.addWidget(self._motor_btn)

        self._pen_btn = QPushButton("\u25b4 Raise Pen")
        self._pen_btn.clicked.connect(self.toggle_pen_clicked)
        layout.addWidget(self._pen_btn)

        self._plot_btn = QPushButton("\u25b6 PLOT")
        self._plot_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 4px 16px; }"
        )
        self._plot_btn.clicked.connect(self.plot_clicked)
        layout.addWidget(self._plot_btn)

    # -----------------------------------------------------------------
    def set_connected(self, connected: bool, port: str = "", model: str = "") -> None:
        if connected:
            self._status_label.setText("CONNECTED")
            self._status_label.setStyleSheet("color: #4f4;")
            self._device_label.setText(f"USB: {port}  |  {model}")
        else:
            self._status_label.setText("DISCONNECTED")
            self._status_label.setStyleSheet("color: #f44;")
            self._device_label.setText("USB: --")

    def set_position(self, x: float | None, y: float | None) -> None:
        if x is not None and y is not None:
            self._pos_label.setText(f"X/Y: ({x:.1f}, {y:.1f})")
        else:
            self._pos_label.setText("X/Y: (---, ---)")

    def set_pen_state(self, raised: bool) -> None:
        if raised:
            self._pen_btn.setText("\u25b4 Raise Pen")
        else:
            self._pen_btn.setText("\u25be Lower Pen")

    def set_status_text(self, text: str) -> None:
        """Temporarily override the status label (e.g. for errors / info)."""
        self._status_label.setText(text)
