"""AxiDraw device — wraps the pyaxidraw interactive API."""

from __future__ import annotations

from dataclasses import dataclass

import serial.tools.list_ports
from pyaxidraw import axidraw as _pyaxidraw
from PySide6.QtCore import QObject, Signal

EBB_VID = 0x04D8
EBB_PID = 0xFD92
_EBB_KEYWORDS = ("ubw", "eibotboard", "axidraw", "ebb", "ei bot")
NUDGE_MM = 6.35  # 0.25 inch


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
        self._ad: _pyaxidraw.AxiDraw | None = None
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

    def connect(self, port: str, model: int = 1) -> bool:
        if self._connected:
            self.disconnect()
        ad = _pyaxidraw.AxiDraw()
        ad.interactive()
        ad.options.units = 2  # millimetres
        ad.options.port = port
        ad.options.model = model
        ad.options.pen_pos_up = 60
        ad.options.pen_pos_down = 30
        try:
            result = ad.connect()
        except Exception as exc:
            print(f"[DeviceModel] connect failed: {exc}")
            try:
                ad.disconnect()
            except Exception:
                pass
            return False
        if not result:
            print("[DeviceModel] connect() returned False")
            return False
        # connect() enables motors; disable so user must manually engage
        ad.usb_command("EM,0,0\r")
        self._ad = ad
        self._info = DeviceInfo(port=port, model=_guess_model(""))
        self._connected = True
        self._motor_enabled = False
        self._pen_raised = True
        self._x, self._y = 0.0, 0.0
        self.connected_changed.emit(True)
        self.info_changed.emit()
        return True

    def disconnect(self) -> None:
        if self._ad is not None:
            try:
                self._ad.disconnect()
            except Exception:
                pass
            self._ad = None
        self._connected = False
        self._motor_enabled = False
        self._info = DeviceInfo()
        self.connected_changed.emit(False)
        self.info_changed.emit()

    def toggle_motors(self) -> bool:
        if not self._connected or self._ad is None:
            return False
        self._motor_enabled = not self._motor_enabled
        if self._motor_enabled:
            self._ad.enable_motors()
        else:
            self._ad.usb_command("EM,0,0\r")
        return self._motor_enabled

    def toggle_pen(self) -> bool:
        if not self._connected or self._ad is None:
            return True
        self._pen_raised = not self._pen_raised
        if self._pen_raised:
            self._ad.penup()
        else:
            self._ad.pendown()
        print(f"[DeviceModel] pen={'up' if self._pen_raised else 'down'}")
        return self._pen_raised

    def align(self) -> None:
        if not self._connected or self._ad is None:
            return
        self._ad.penup()
        self._ad.usb_command("EM,0,0\r")
        self._motor_enabled = False
        self._pen_raised = True

    def home(self) -> None:
        if not self._connected or not self._motor_enabled or self._ad is None:
            return
        self._ad.moveto(0.0, 0.0)
        self._x, self._y = 0.0, 0.0
        self._pen_raised = True

    def nudge(self, dx_mm: float, dy_mm: float) -> None:
        if not self._connected or not self._motor_enabled or self._ad is None:
            return
        target_x = max(0.0, self._x + dx_mm)
        target_y = max(0.0, self._y + dy_mm)
        self._ad.moveto(target_x, target_y)  # always pen-up move
        self._x = target_x
        self._y = target_y
        self._pen_raised = True
        print(f"[DeviceModel] nudged to ({self._x:.1f}, {self._y:.1f})")

    def update_pen_settings(self, up_pct: float, down_pct: float) -> None:
        """Push new pen heights to the device servo without moving it."""
        if self._ad is None:
            return
        self._ad.options.pen_pos_up = int(up_pct)
        self._ad.options.pen_pos_down = int(down_pct)
        self._ad.pen.servo_init(self._ad)

    def plot_path(self, vertices: list[list[float]], abort_check) -> bool:
        """
        Plot one polyline segment-by-segment so abort/pause is checked between
        every vertex.  abort_check() blocks while paused and returns True when
        the plot should stop.  Returns True if completed, False if aborted.
        """
        if self._ad is None or len(vertices) < 2:
            return True
        self._ad.moveto(vertices[0][0], vertices[0][1])
        for x, y in vertices[1:]:
            if abort_check():
                self._ad.penup()
                self._pen_raised = True
                return False
            self._ad.lineto(x, y)
        self._ad.penup()
        self._pen_raised = True
        return True

    def plot_polyline(self, vertices: list[list[float]]) -> None:
        """Plot a polyline via draw_path (no abort checking)."""
        if self._ad is not None:
            self._ad.draw_path(vertices)

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
