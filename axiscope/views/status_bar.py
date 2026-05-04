"""Bottom status bar with device info and action buttons."""

from PySide6.QtCore import Signal
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
    home_clicked = Signal()
    align_clicked = Signal()
    plot_clicked = Signal()
    pause_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 8, 2)
        layout.setSpacing(10)

        self._status_label = QLabel("DISCONNECTED")
        self._status_label.setStyleSheet("color: #f44;")
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("|"))

        self._device_label = QLabel("USB: --")
        layout.addWidget(self._device_label)

        layout.addWidget(QLabel("|"))

        self._pos_label = QLabel("X/Y: (---, ---)")
        layout.addWidget(self._pos_label)

        layout.addStretch()

        self._motor_btn = QPushButton("ENGAGE MOTORS")
        self._motor_btn.clicked.connect(self.toggle_motors_clicked)
        layout.addWidget(self._motor_btn)

        self._pen_btn = QPushButton("\u25b4 Raise Pen")
        self._pen_btn.clicked.connect(self.toggle_pen_clicked)
        layout.addWidget(self._pen_btn)

        self._home_btn = QPushButton("\u2302 Home")
        self._home_btn.clicked.connect(self.home_clicked)
        layout.addWidget(self._home_btn)

        self._align_btn = QPushButton("ALIGN")
        self._align_btn.clicked.connect(self.align_clicked)
        layout.addWidget(self._align_btn)

        self._plot_btn = QPushButton("\u25b6 PLOT")
        self._plot_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 4px 16px; }"
        )
        self._plot_btn.clicked.connect(self.plot_clicked)
        layout.addWidget(self._plot_btn)

        self._pause_btn = QPushButton("\u23f8 Pause")
        self._pause_btn.clicked.connect(self.pause_clicked)
        self._pause_btn.setVisible(False)
        layout.addWidget(self._pause_btn)

        self._cancel_btn = QPushButton("\u2716 Cancel")
        self._cancel_btn.setStyleSheet(
            "QPushButton { color: #f88; font-weight: bold; }"
        )
        self._cancel_btn.clicked.connect(self.cancel_clicked)
        self._cancel_btn.setVisible(False)
        layout.addWidget(self._cancel_btn)

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

    def set_motor_state(self, engaged: bool) -> None:
        self._motor_btn.setText("DISENGAGE MOTORS" if engaged else "ENGAGE MOTORS")

    def set_position(self, x: float | None, y: float | None) -> None:
        if x is not None and y is not None:
            self._pos_label.setText(f"X/Y: ({x:.1f}, {y:.1f})")
        else:
            self._pos_label.setText("X/Y: (---, ---)")

    def set_pen_state(self, raised: bool) -> None:
        self._pen_btn.setText("\u25b4 Raise Pen" if raised else "\u25be Lower Pen")

    def set_plotting(self, active: bool, paused: bool = False) -> None:
        self._plot_btn.setVisible(not active)
        self._pause_btn.setVisible(active)
        self._cancel_btn.setVisible(active)
        if active:
            self._pause_btn.setText("\u25b6 Resume" if paused else "\u23f8 Pause")

    def set_status_text(self, text: str) -> None:
        self._status_label.setText(text)
