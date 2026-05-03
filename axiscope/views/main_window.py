"""Main window: toolbar at top, canvas in centre, status bar at bottom."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPainterPath, QShortcut, QTransform
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from axiscope.controllers.plot_controller import PlotController
from axiscope.models.device import DeviceModel
from axiscope.models.paper import PaperSize
from axiscope.models.settings import SettingsModel
from axiscope.tools.base_tool import BaseTool
from axiscope.tools.oscilloscope import OscilloscopeTool
from axiscope.utils.svg_loader import load_svg
from axiscope.views.canvas import CanvasView
from axiscope.views.settings_dialog import SettingsDialog
from axiscope.views.status_bar import StatusBar
from axiscope.views.tool_controls import ToolControlsPanel
from axiscope.views.toolbar import Toolbar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AxisScope")
        self.setMinimumSize(900, 640)
        self.resize(1280, 860)

        self._device = DeviceModel()
        self._settings = SettingsModel()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._toolbar = Toolbar()
        self._toolbar.paper_changed.connect(self._on_paper_changed)
        self._toolbar.load_svg_clicked.connect(self._on_load_svg)
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.settings_clicked.connect(self._on_settings)
        root_layout.addWidget(self._toolbar)

        self._svg_controls = self._build_svg_controls()
        root_layout.addWidget(self._svg_controls)

        self._tool_controls = ToolControlsPanel()
        self._tool_controls.params_changed.connect(self._on_tool_params)
        root_layout.addWidget(self._tool_controls)

        self._scene = QGraphicsScene()
        self._canvas = CanvasView(self._scene)
        root_layout.addWidget(self._canvas, stretch=1)

        self._status_bar = StatusBar()
        self._status_bar.toggle_motors_clicked.connect(self._on_toggle_motors)
        self._status_bar.toggle_pen_clicked.connect(self._on_toggle_pen)
        self._status_bar.plot_clicked.connect(self._on_plot)
        root_layout.addWidget(self._status_bar)

        self._device.connected_changed.connect(self._on_device_connection)
        self._device.info_changed.connect(self._on_device_info)

        self._plot_ctrl = PlotController(self._device, self._settings)
        self._plot_ctrl.plot_started.connect(self._on_plot_started)
        self._plot_ctrl.plot_finished.connect(self._on_plot_finished)

        self._tools: dict[str, BaseTool] = {
            "Polar Oscilloscope": OscilloscopeTool(),
        }
        self._active_tool: BaseTool | None = None
        self._svg_paths: list[QPainterPath] = []

        self._on_paper_changed("A1")
        self._setup_shortcuts()
        self._apply_theme()

    # =================================================================
    # Toolbar handlers
    # =================================================================

    def _on_paper_changed(self, name: str) -> None:
        paper = PaperSize.from_name(name)
        self._canvas.set_paper(paper)
        if self._active_tool is not None:
            self._regenerate_tool_preview()
        elif self._svg_paths:
            self._render_svg_preview()

    def _on_load_svg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open SVG", "", "SVG Files (*.svg);;All Files (*)"
        )
        if not path:
            return
        paper = PaperSize.from_name(self._toolbar.current_paper())
        stroke_mm = self._settings.data.stroke_width
        try:
            paths = load_svg(path, paper, stroke_mm)
        except Exception as exc:
            self._status_bar.set_status_text(f"SVG error: {exc}")
            return

        self._toolbar._tool_combo.blockSignals(True)
        self._toolbar._tool_combo.setCurrentText("None")
        self._toolbar._tool_combo.blockSignals(False)
        self._active_tool = None
        self._tool_controls.set_tool(None)

        self._svg_paths = paths
        self._reset_svg_controls()
        self._svg_controls.setVisible(True)
        self._render_svg_preview()

        filename = path.split("/")[-1].split(chr(92))[-1]
        self.setWindowTitle(f"AxisScope — {filename}")
        self._status_bar.set_status_text(f"Loaded: {filename}")

    def _on_tool_changed(self, name: str) -> None:
        tool = self._tools.get(name)
        if tool is not None:
            self._active_tool = tool
            self._svg_controls.setVisible(False)
            self._tool_controls.set_tool(tool)
            self._canvas.clear_preview()
            self._regenerate_tool_preview()
            self._status_bar.set_status_text(f"Tool: {name}")
        else:
            self._active_tool = None
            self._tool_controls.set_tool(None)
            self._canvas.clear_preview()
            self._status_bar.set_status_text("Ready")

    def _on_settings(self) -> None:
        dlg = SettingsDialog(self._device, self._settings, self)
        dlg.exec()

    # =================================================================
    # Tool preview
    # =================================================================

    def _on_tool_params(self, params: dict) -> None:  # noqa: ARG002
        self._regenerate_tool_preview()

    def _regenerate_tool_preview(self) -> None:
        if self._active_tool is None:
            return
        paper = PaperSize.from_name(self._toolbar.current_paper())
        stroke_mm = self._settings.data.stroke_width
        params = self._tool_controls.current_params()

        self._canvas.clear_preview()
        try:
            paths = self._active_tool.generate_paths(params, paper, stroke_mm)
            for p in paths:
                self._canvas.add_preview_path(p)
        except Exception as exc:
            self._status_bar.set_status_text(f"Tool error: {exc}")

    # =================================================================
    # SVG controls
    # =================================================================

    def _build_svg_controls(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(40)
        w.setVisible(False)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(12)

        lay.addWidget(QLabel("SVG"))
        lay.addWidget(QLabel("Scale %"))
        self._svg_scale = QDoubleSpinBox()
        self._svg_scale.setRange(10, 500)
        self._svg_scale.setValue(100)
        self._svg_scale.setSuffix(" %")
        self._svg_scale.setFixedWidth(90)
        self._svg_scale.valueChanged.connect(self._on_svg_control)
        lay.addWidget(self._svg_scale)

        lay.addWidget(QLabel("Off X"))
        self._svg_off_x = QDoubleSpinBox()
        self._svg_off_x.setRange(-500, 500)
        self._svg_off_x.setValue(0)
        self._svg_off_x.setSuffix(" mm")
        self._svg_off_x.setFixedWidth(90)
        self._svg_off_x.valueChanged.connect(self._on_svg_control)
        lay.addWidget(self._svg_off_x)

        lay.addWidget(QLabel("Off Y"))
        self._svg_off_y = QDoubleSpinBox()
        self._svg_off_y.setRange(-500, 500)
        self._svg_off_y.setValue(0)
        self._svg_off_y.setSuffix(" mm")
        self._svg_off_y.setFixedWidth(90)
        self._svg_off_y.valueChanged.connect(self._on_svg_control)
        lay.addWidget(self._svg_off_y)

        lay.addStretch()
        return w

    def _reset_svg_controls(self) -> None:
        for sb, val in [
            (self._svg_scale, 100),
            (self._svg_off_x, 0),
            (self._svg_off_y, 0),
        ]:
            sb.blockSignals(True)
            sb.setValue(val)
            sb.blockSignals(False)

    def _on_svg_control(self) -> None:
        self._render_svg_preview()

    def _render_svg_preview(self) -> None:
        if not self._svg_paths:
            return
        scale = self._svg_scale.value() / 100.0
        dx = self._svg_off_x.value()
        dy = self._svg_off_y.value()
        xform = QTransform()
        xform.scale(scale, scale)
        xform.translate(dx, dy)
        self._canvas.clear_preview()
        for p in self._svg_paths:
            self._canvas.add_preview_path(xform.map(p))

    # =================================================================
    # Keyboard shortcuts
    # =================================================================

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, self._on_load_svg)
        QShortcut(QKeySequence("Ctrl+P"), self, self._on_plot)
        QShortcut(QKeySequence("Ctrl+M"), self, self._on_toggle_motors)
        QShortcut(QKeySequence("Ctrl+Up"), self, self._on_pen_up)
        QShortcut(QKeySequence("Ctrl+Down"), self, self._on_pen_down)
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        QShortcut(QKeySequence("Ctrl+,"), self, self._on_settings)

    def _on_pen_up(self) -> None:
        if not self._device.connected or self._device.pen_raised:
            return
        self._on_toggle_pen()

    def _on_pen_down(self) -> None:
        if not self._device.connected or not self._device.pen_raised:
            return
        self._on_toggle_pen()

    def _on_escape(self) -> None:
        if self._active_tool is not None:
            self._toolbar._tool_combo.setCurrentText("None")

    # =================================================================
    # Status bar actions
    # =================================================================

    def _on_toggle_motors(self) -> None:
        if not self._device.connected:
            self._status_bar.set_status_text("Not connected")
            return
        self._device.toggle_motors()
        state = "ON" if self._device.motor_enabled else "OFF"
        self._status_bar.set_status_text(f"Motors: {state}")

    def _on_toggle_pen(self) -> None:
        if not self._device.connected:
            self._status_bar.set_status_text("Not connected")
            return
        self._device.toggle_pen()
        self._status_bar.set_pen_state(self._device.pen_raised)
        state = "raised" if self._device.pen_raised else "lowered"
        self._status_bar.set_status_text(f"Pen: {state}")

    def _on_plot(self) -> None:
        if not self._device.connected:
            self._status_bar.set_status_text("Not connected — check device")
            return
        if self._plot_ctrl.busy:
            self._status_bar.set_status_text("Plot already in progress")
            return
        paths = self._canvas.preview_paths()
        if not paths:
            self._status_bar.set_status_text("Nothing to plot")
            return
        paper = PaperSize.from_name(self._toolbar.current_paper())
        self._plot_ctrl.start_plot(paths, paper)

    def _on_plot_started(self) -> None:
        self._status_bar.set_status_text("Plotting…")
        self._status_bar._plot_btn.setEnabled(False)

    def _on_plot_finished(self) -> None:
        self._status_bar.set_status_text("Plot complete")
        self._status_bar._plot_btn.setEnabled(True)

    # =================================================================
    # Device callbacks
    # =================================================================

    def _on_device_connection(self, connected: bool) -> None:
        if connected:
            self._status_bar.set_connected(
                True, self._device.port, self._device.model
            )
        else:
            self._status_bar.set_connected(False)

    def _on_device_info(self) -> None:
        self._status_bar.set_connected(
            self._device.connected, self._device.port, self._device.model
        )

    # =================================================================
    def _apply_theme(self) -> None:
        mono_fonts = (
            '"JetBrains Mono", "Fira Code", "Cascadia Code", '
            '"SF Mono", "Consolas", "DejaVu Sans Mono", monospace'
        )
        self.setStyleSheet(
            f"""
            * {{
                font-family: {mono_fonts};
                font-size: 13px;
                background-color: #1e1e1e;
                color: #ccc;
            }}
            QPushButton {{
                background: #333;
                border: 1px solid #555;
                padding: 4px 10px;
                color: #ddd;
            }}
            QPushButton:hover {{
                background: #444;
                border-color: #888;
            }}
            QPushButton:pressed {{
                background: #555;
            }}
            QPushButton:disabled {{
                color: #666;
            }}
            QComboBox {{
                background: #333;
                border: 1px solid #555;
                padding: 3px 8px;
                color: #ddd;
            }}
            QComboBox:hover {{
                border-color: #888;
            }}
            QComboBox QAbstractItemView {{
                background: #333;
                selection-background-color: #555;
                color: #ddd;
            }}
            QLabel {{
                background: transparent;
            }}
            QGroupBox {{
                border: 1px solid #555;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QTabWidget::pane {{
                border: 1px solid #555;
            }}
            QTabBar::tab {{
                background: #2a2a2a;
                border: 1px solid #555;
                padding: 6px 14px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: #3a3a3a;
                border-bottom-color: #3a3a3a;
            }}
            QLineEdit {{
                background: #333;
                border: 1px solid #555;
                padding: 3px 6px;
                color: #ddd;
            }}
            QSpinBox, QDoubleSpinBox {{
                background: #333;
                border: 1px solid #555;
                padding: 3px 6px;
                color: #ddd;
            }}
            QCheckBox {{
                background: transparent;
            }}
        """
        )
