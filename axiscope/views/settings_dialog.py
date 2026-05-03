"""Settings popup — device, pen, plot & canvas tabs."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from axiscope.models.device import DeviceInfo, DeviceModel
from axiscope.models.settings import PlotSettings, SettingsModel

# -- Helpers: labelled slider + spinbox pair --------------------------


class _LabelledSlider(QWidget):
    """A horizontal slider with a companion spinbox and label."""

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        decimals: int = 1,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(120)
        layout.addWidget(lbl)

        self._spin = QDoubleSpinBox()
        self._spin.setRange(minimum, maximum)
        self._spin.setDecimals(decimals)
        self._spin.setSuffix(suffix)
        self._spin.setFixedWidth(90 if not suffix else 110)
        self._spin.setValue(value)
        layout.addWidget(self._spin)

        self._slider = None  # not used for now; spinbox-only is cleaner
        layout.addStretch()

    @property
    def value(self) -> float:
        return self._spin.value()

    def set_value(self, v: float) -> None:
        self._spin.setValue(v)


# -- Tab pages --------------------------------------------------------


class _DeviceTab(QWidget):
    """Device detection and connection."""

    def __init__(self, device_model: DeviceModel, parent=None):
        super().__init__(parent)
        self._device = device_model

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Scan row
        scan_row = QHBoxLayout()
        self._scan_btn = QPushButton("Scan USB")
        self._scan_btn.clicked.connect(self._on_scan)
        scan_row.addWidget(self._scan_btn)
        scan_row.addStretch()
        layout.addLayout(scan_row)

        # Device list
        self._device_list = QComboBox()
        self._device_list.setMinimumWidth(200)
        layout.addWidget(self._device_list)

        # Connect / Disconnect
        btn_row = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._connect_btn.clicked.connect(self._on_connect)
        self._connect_btn.setEnabled(False)
        btn_row.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        self._disconnect_btn.setEnabled(False)
        btn_row.addWidget(self._disconnect_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Manual port entry
        manual_box = QGroupBox("Manual port")
        manual_layout = QFormLayout(manual_box)
        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("e.g. COM3 or /dev/ttyUSB0")
        manual_layout.addRow("Port:", self._port_edit)
        manual_connect = QPushButton("Connect (manual)")
        manual_connect.clicked.connect(self._on_manual_connect)
        manual_layout.addRow("", manual_connect)
        layout.addWidget(manual_box)

        # Info display
        info_box = QGroupBox("Device info")
        info_layout = QFormLayout(info_box)
        self._info_model = QLabel("—")
        self._info_firmware = QLabel("—")
        self._info_port = QLabel("—")
        info_layout.addRow("Model:", self._info_model)
        info_layout.addRow("Firmware:", self._info_firmware)
        info_layout.addRow("Port:", self._info_port)
        layout.addWidget(info_box)

        layout.addStretch()

        # Listen for device changes
        self._device.info_changed.connect(self._refresh_info)

    def _on_scan(self) -> None:
        devices = self._device.scan_ports()
        self._device_list.clear()
        if devices:
            for d in devices:
                self._device_list.addItem(f"{d.port} — {d.model}", d.port)
            self._connect_btn.setEnabled(True)
        else:
            self._device_list.addItem("No devices found")
            self._connect_btn.setEnabled(False)

    def _on_connect(self) -> None:
        port = self._device_list.currentData()
        if port:
            ok = self._device.connect(port)
            if ok:
                self._connect_btn.setEnabled(False)
                self._disconnect_btn.setEnabled(True)
                self._refresh_info()

    def _on_manual_connect(self) -> None:
        port = self._port_edit.text().strip()
        if port:
            ok = self._device.connect(port)
            if ok:
                self._connect_btn.setEnabled(False)
                self._disconnect_btn.setEnabled(True)
                self._refresh_info()

    def _on_disconnect(self) -> None:
        self._device.disconnect()
        self._connect_btn.setEnabled(True)
        self._disconnect_btn.setEnabled(False)
        self._refresh_info()

    def _refresh_info(self) -> None:
        if self._device.connected:
            self._info_model.setText(self._device.model)
            self._info_firmware.setText(self._device.firmware)
            self._info_port.setText(self._device.port)
            self._disconnect_btn.setEnabled(True)
        else:
            self._info_model.setText("—")
            self._info_firmware.setText("—")
            self._info_port.setText("—")
            self._disconnect_btn.setEnabled(False)


class _PenTab(QWidget):
    """Pen up/down height, speed, delay."""

    def __init__(self, settings: PlotSettings, parent=None):
        super().__init__(parent)
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        g = QGroupBox("Pen height")
        f = QFormLayout(g)
        self._up_height = self._add_pct(f, "Pen-up height", settings.pen_up_height)
        self._down_height = self._add_pct(
            f, "Pen-down height", settings.pen_down_height
        )
        layout.addWidget(g)

        g2 = QGroupBox("Pen speed")
        f2 = QFormLayout(g2)
        self._up_speed = self._add_pct(f2, "Pen-up speed", settings.pen_up_speed)
        self._down_speed = self._add_pct(f2, "Pen-down speed", settings.pen_down_speed)
        layout.addWidget(g2)

        g3 = QGroupBox("Pen delay")
        f3 = QFormLayout(g3)
        self._up_delay = self._add_ms(f3, "Pen-up delay", settings.pen_up_delay)
        self._down_delay = self._add_ms(f3, "Pen-down delay", settings.pen_down_delay)
        layout.addWidget(g3)

        layout.addStretch()

    # ----------------------------------------------------------------
    def collect(self) -> dict:
        return {
            "pen_up_height": self._up_height.value(),
            "pen_down_height": self._down_height.value(),
            "pen_up_speed": self._up_speed.value(),
            "pen_down_speed": self._down_speed.value(),
            "pen_up_delay": self._up_delay.value(),
            "pen_down_delay": self._down_delay.value(),
        }

    # ----------------------------------------------------------------
    @staticmethod
    def _add_pct(form: QFormLayout, label: str, value: float) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(0, 100)
        sb.setDecimals(1)
        sb.setSuffix(" %")
        sb.setValue(value)
        form.addRow(label, sb)
        return sb

    @staticmethod
    def _add_ms(form: QFormLayout, label: str, value: float) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(0, 10000)
        sb.setDecimals(0)
        sb.setSuffix(" ms")
        sb.setValue(value)
        form.addRow(label, sb)
        return sb


class _PlotTab(QWidget):
    """Plot speed, acceleration, options."""

    def __init__(self, settings: PlotSettings, parent=None):
        super().__init__(parent)
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        g = QGroupBox("Speed & acceleration")
        f = QFormLayout(g)
        self._plot_speed = self._add_pct(f, "Plot speed", settings.plot_speed)
        self._accel = self._add_pct(f, "Acceleration", settings.acceleration)
        layout.addWidget(g)

        g2 = QGroupBox("Options")
        f2 = QFormLayout(g2)
        self._return_home = QCheckBox("Return to home after plot")
        self._return_home.setChecked(settings.return_home)
        f2.addRow(self._return_home)

        self._copies = QSpinBox()
        self._copies.setRange(1, 99)
        self._copies.setValue(settings.copies)
        f2.addRow("Copies:", self._copies)

        self._layer = QSpinBox()
        self._layer.setRange(1, 100)
        self._layer.setValue(settings.layer)
        f2.addRow("SVG layer:", self._layer)
        layout.addWidget(g2)

        layout.addStretch()

    def collect(self) -> dict:
        return {
            "plot_speed": self._plot_speed.value(),
            "acceleration": self._accel.value(),
            "return_home": self._return_home.isChecked(),
            "copies": self._copies.value(),
            "layer": self._layer.value(),
        }

    @staticmethod
    def _add_pct(form: QFormLayout, label: str, value: float) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setRange(1, 100)
        sb.setDecimals(0)
        sb.setSuffix(" %")
        sb.setValue(value)
        form.addRow(label, sb)
        return sb


class _CanvasTab(QWidget):
    """Canvas display options."""

    def __init__(self, settings: PlotSettings, parent=None):
        super().__init__(parent)
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        g = QGroupBox("Grid")
        f = QFormLayout(g)
        self._show_grid = QCheckBox("Show grid overlay")
        self._show_grid.setChecked(settings.show_grid)
        f.addRow(self._show_grid)

        self._grid_spacing = QDoubleSpinBox()
        self._grid_spacing.setRange(1, 100)
        self._grid_spacing.setDecimals(0)
        self._grid_spacing.setSuffix(" mm")
        self._grid_spacing.setValue(settings.grid_spacing_mm)
        f.addRow("Grid spacing:", self._grid_spacing)
        layout.addWidget(g)

        layout.addStretch()

    def collect(self) -> dict:
        return {
            "show_grid": self._show_grid.isChecked(),
            "grid_spacing_mm": self._grid_spacing.value(),
        }


# -- Dialog -----------------------------------------------------------


class SettingsDialog(QDialog):
    """Modal settings dialog with tabs."""

    def __init__(
        self,
        device_model: DeviceModel,
        settings_model: SettingsModel,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 480)
        self.resize(540, 520)
        self.setModal(True)

        self._device = device_model
        self._settings = settings_model
        self._data = settings_model.data  # snapshot for editing

        layout = QVBoxLayout(self)

        # Tab widget
        self._tabs = QTabWidget()
        self._device_tab = _DeviceTab(device_model)
        self._pen_tab = _PenTab(self._data)
        self._plot_tab = _PlotTab(self._data)
        self._canvas_tab = _CanvasTab(self._data)

        self._tabs.addTab(self._device_tab, "Device")
        self._tabs.addTab(self._pen_tab, "Pen")
        self._tabs.addTab(self._plot_tab, "Plot")
        self._tabs.addTab(self._canvas_tab, "Canvas")
        layout.addWidget(self._tabs)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_accept(self) -> None:
        """Flush all tab values into the settings model."""
        updates = {}
        updates.update(self._pen_tab.collect())
        updates.update(self._plot_tab.collect())
        updates.update(self._canvas_tab.collect())
        self._settings.update(**updates)
        self.accept()
