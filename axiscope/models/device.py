"""AxiDraw device detection and EBB serial communication."""

from __future__ import annotations

import time
from dataclasses import dataclass

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal

# -- EBB constants ----------------------------------------------------
EBB_VID = 0x04D8
EBB_PID = 0xFD92
EBB_BAUD = 115200
EBB_TIMEOUT = 1.0

# Patterns that identify an AxiDraw / EBB in the port description
_EBB_KEYWORDS = ("ubw", "eibotboard", "axidraw", "ebb", "ei bot")


@dataclass
class DeviceInfo:
    port: str = ""
    model: str = ""
    firmware: str = ""
    description: str = ""


class DeviceModel(QObject):
    """Holds connection state and device info.  Communicates with the
    EiBotBoard (EBB) over a serial port for real hardware control."""

    connected_changed = Signal(bool)
    position_changed = Signal(float, float)
    info_changed = Signal()

    def __init__(self):
        super().__init__()
        self._connected = False
        self._info = DeviceInfo()
        self._ser: serial.Serial | None = None
        self._x: float | None = None
        self._y: float | None = None
        self._motor_enabled = False
        self._pen_raised = True

    # -- properties ----------------------------------------------------
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
    def x(self) -> float | None:
        return self._x

    @property
    def y(self) -> float | None:
        return self._y

    # -- scanning ------------------------------------------------------
    @staticmethod
    def scan_ports() -> list[DeviceInfo]:
        """Return a list of detected AxiDraw / EBB devices."""
        found: list[DeviceInfo] = []
        for pi in serial.tools.list_ports.comports():
            # Match by VID/PID first (most reliable)
            if pi.vid == EBB_VID and pi.pid == EBB_PID:
                found.append(
                    DeviceInfo(
                        port=pi.device,
                        model=_guess_model(pi.description),
                        description=pi.description,
                    )
                )
                continue

            # Fallback: match by description keywords
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

    # -- connection ----------------------------------------------------
    def connect(self, port: str) -> bool:
        """Open serial connection to the EBB on *port* and query firmware."""
        if self._connected:
            self.disconnect()

        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=EBB_BAUD,
                timeout=EBB_TIMEOUT,
                write_timeout=EBB_TIMEOUT,
            )
        except (OSError, serial.SerialException) as exc:
            print(f"[DeviceModel] Failed to open {port}: {exc}")
            return False

        # Query firmware version
        fw = self._ebb_command("V\r")
        model = _guess_model(self._info.description or fw)

        self._info = DeviceInfo(
            port=port,
            model=model,
            firmware=fw.strip() if fw else "unknown",
            description=self._info.description,
        )
        self._connected = True
        self._motor_enabled = False
        self._pen_raised = True
        self.connected_changed.emit(True)
        self.info_changed.emit()
        return True

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._ser and self._ser.is_open:
            try:
                # Disable motors before closing
                self._ebb_command("EM,0\r")
            except Exception:
                pass
            self._ser.close()
        self._ser = None
        self._connected = False
        self._motor_enabled = False
        self._pen_raised = True
        self._info = DeviceInfo()
        self.connected_changed.emit(False)
        self.info_changed.emit()

    # -- hardware actions -----------------------------------------------
    def toggle_motors(self) -> bool:
        """Enable/disable stepper motors. Returns new state."""
        if not self._connected:
            return False
        self._motor_enabled = not self._motor_enabled
        cmd = "EM,1\r" if self._motor_enabled else "EM,0\r"
        self._ebb_command(cmd)
        return self._motor_enabled

    def toggle_pen(self) -> bool:
        """Raise/lower pen. Returns True if pen is now raised."""
        if not self._connected:
            return True
        self._pen_raised = not self._pen_raised
        cmd = "SP,0\r" if self._pen_raised else "SP,1\r"
        self._ebb_command(cmd)
        return self._pen_raised

    def query_position(self) -> tuple[float | None, float | None]:
        """Poll current toolhead position from the EBB."""
        # EBB doesn't natively track absolute position — we'd need to
        # maintain our own step counter.  For now return last known.
        return self._x, self._y

    # -- raw EBB command -----------------------------------------------
    def _ebb_command(self, cmd: str) -> str:
        """Send a raw command string to the EBB and return the response."""
        if not self._ser or not self._ser.is_open:
            return ""
        try:
            self._ser.reset_input_buffer()
            self._ser.write(cmd.encode("ascii"))
            time.sleep(0.02)
            resp = self._ser.read_until(b"\r\n")
            return resp.decode("ascii", errors="replace")
        except (OSError, serial.SerialException) as exc:
            print(f"[DeviceModel] EBB command '{cmd.strip()}' failed: {exc}")
            return ""


# -- helpers -----------------------------------------------------------


def _guess_model(description: str) -> str:
    """Heuristic to guess the AxiDraw model from a description string.
    The exact model will be refined once firmware is queried."""
    if not description:
        return "AxiDraw"
    d = description.lower()
    # Match specific model strings
    if "axidraw v3" in d or "axidraw v3" in d:
        return "AxiDraw V3"
    if "axidraw v2" in d:
        return "AxiDraw V2"
    if "axidraw mini" in d:
        return "AxiDraw Mini"
    if "axidraw se" in d:
        return "AxiDraw SE"
    # EBB / UBW detected but model unknown — firmware query will refine
    if "ebb" in d or "ubw" in d or "eibotboard" in d:
        return "AxiDraw"
    return "AxiDraw"
