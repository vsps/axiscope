"""AxiDraw device — wraps the AxiDraw Python API."""

from __future__ import annotations

import serial.tools.list_ports
from axidrawinternal.axidraw import AxiDraw
from PySide6.QtCore import QObject, Signal

EBB_VID = 0x04D8
EBB_PID = 0xFD92
_EBB_KEYWORDS = ("ubw", "eibotboard", "axidraw", "ebb", "ei bot")
NUDGE_MM = 6.35  # 0.25 inch

from dataclasses import dataclass


@dataclass
class DeviceInfo:
    port: str = ""
    model: str = ""
    firmware: str = ""
    description: str = ""


class DeviceModel(QObject):
    connected_changed = Signal(bool)
    position_changed = Signal(float, float)
    info_changed = Signal()

    def __init__(self):
        super().__init__()
        self._connected = False
        self._info = DeviceInfo()
        self._ad = AxiDraw()
        self._x: float = 0.0
        self._y: float = 0.0
        self._motor_enabled = False
        self._pen_raised = True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str:
        return self._info.port

    @property
    def model(self) -> str:
        return self._info.model

    @property
    def firmware(self) -> str:
        return self._info.firmware

    @property
    def motor_enabled(self) -> bool:
        return self._motor_enabled

    @property
    def pen_raised(self) -> bool:
        return self._pen_raised

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @staticmethod
    def scan_ports() -> list[DeviceInfo]:
        found: list[DeviceInfo] = []
        for pi in serial.tools.list_ports.comports():
            if pi.vid == EBB_VID and pi.pid == EBB_PID:
                found.append(
                    DeviceInfo(
                        port=pi.device,
                        model=_guess_model(pi.description),
                        description=pi.description,
                    )
                )
                continue
            desc_lower = (pi.description or "").lower()
            if any(kw in desc_lower for kw in _EBB_KEYWORDS):
                found.append(
                    DeviceInfo(
                        port=pi.device,
                        model=_guess_model(pi.description),
                        description=pi.description,
                    )
                )
        return found

    def connect(self, port: str) -> bool:
        if self._connected:
            self.disconnect()
        # Force-close any stale handle on this port
        try:
            import serial as _ser

            s = _ser.Serial(port=port, baudrate=115200, timeout=0.1)
            s.close()
        except Exception:
            pass
        self._ad.options.port = port
        try:
            self._ad.serial_connect()
        except Exception as exc:
            print(f"[DeviceModel] Connect failed: {exc}")
            return False
        self._ad.initialize_options()
        self._ad.options.pen_pos_up = 60
        self._ad.options.pen_pos_down = 30
        self._ad.step_scale = 2.0 * self._ad.params.native_res_factor
        self._ad.speed_pendown = self._ad.options.speed_pendown
        self._ad.speed_penup = self._ad.options.speed_penup
        self._info = DeviceInfo(port=port, model=_guess_model(""))
        self._connected = True
        self._motor_enabled = False
        self._pen_raised = True
        self._x, self._y = 0.0, 0.0
        self.connected_changed.emit(True)
        self.info_changed.emit()
        return True

    def disconnect(self) -> None:
        try:
            self._ad.disconnect()
        except Exception:
            pass
        self._connected = False
        self._motor_enabled = False
        self._info = DeviceInfo()
        self.connected_changed.emit(False)
        self.info_changed.emit()

    def toggle_motors(self) -> bool:
        if not self._connected:
            return False
        self._motor_enabled = not self._motor_enabled
        self._ad.options.mode = "manual"
        self._ad.options.manual_cmd = (
            "enable_xy" if self._motor_enabled else "disable_xy"
        )
        self._ad.manual_command()
        return self._motor_enabled

    def toggle_pen(self) -> bool:
        if not self._connected:
            return True
        self._pen_raised = not self._pen_raised
        self._ad.options.mode = "manual"
        self._ad.options.manual_cmd = "raise_pen" if self._pen_raised else "lower_pen"
        self._ad.manual_command()
        print(f"[DeviceModel] pen={'up' if self._pen_raised else 'down'}")
        return self._pen_raised

    def align(self) -> None:
        if not self._connected:
            return
        self._ad.options.mode = "align"
        self._ad.setup_command()
        self._motor_enabled = False
        self._pen_raised = True

    def home(self) -> None:
        if not self._connected or not self._motor_enabled:
            return
        self._ad.options.mode = "plot"
        self._ad.setup_command()
        self._ad.go_to_position(0, 0)
        self._ad.options.mode = "align"
        self._ad.setup_command()
        self._x, self._y = 0.0, 0.0

    def nudge(self, dx_mm: float, dy_mm: float) -> None:
        if not self._connected or not self._motor_enabled:
            return
        self._ad.options.mode = "plot"
        self._ad.setup_command()
        self._ad.go_to_position(self._x + dx_mm, self._y + dy_mm)
        self._x += dx_mm
        self._y += dy_mm
        self._ad.options.mode = "align"
        self._ad.setup_command()
        print(f"[DeviceModel] nudged to ({self._x:.1f}, {self._y:.1f})")

    def setup_plot_mode(self) -> None:
        self._ad.options.mode = "plot"
        self._ad.options.pen_pos_up = 60
        self._ad.options.pen_pos_down = 30
        self._ad.setup_command()

    def plot_polyline(self, vertices: list[list[float]]) -> None:
        self._ad.plot_polyline(vertices)

    def query_position(self) -> tuple[float, float]:
        return self._x, self._y


def _guess_model(description: str) -> str:
    if not description:
        return "AxiDraw"
    d = description.lower()
    if "axidraw v3" in d:
        return "AxiDraw V3"
    if "axidraw v2" in d:
        return "AxiDraw V2"
    if "axidraw mini" in d:
        return "AxiDraw Mini"
    if "axidraw se" in d:
        return "AxiDraw SE"
    return "AxiDraw"
