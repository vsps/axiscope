"""Mono polar oscilloscope — rose-curve / Lissajous-on-a-circle traces."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath

from axiscope.models.paper import PaperSize
from axiscope.tools.base_tool import BaseTool, ControlDef


class OscilloscopeTool(BaseTool):
    """Draws a polar trace — a signal wrapped around a circle.

    Math:  r(theta) = R * |sin(freq * theta + phase)|
    where theta sweeps from 0 to 2π * duration.
    """

    name = "Polar Oscilloscope"

    @property
    def controls(self) -> list[ControlDef]:
        return [
            ControlDef(
                key="frequency",
                label="Frequency",
                default=5.0,
                minimum=0.5,
                maximum=50.0,
                step=0.5,
                decimals=1,
            ),
            ControlDef(
                key="amplitude",
                label="Amplitude %",
                default=80.0,
                minimum=5.0,
                maximum=95.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="phase",
                label="Phase",
                default=0.0,
                minimum=0.0,
                maximum=360.0,
                step=1.0,
                decimals=0,
                suffix="°",
            ),
            ControlDef(
                key="duration",
                label="Duration",
                default=1.0,
                minimum=0.5,
                maximum=10.0,
                step=0.5,
                decimals=1,
                suffix=" rev",
            ),
            ControlDef(
                key="center_x",
                label="Center X %",
                default=50.0,
                minimum=5.0,
                maximum=95.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="center_y",
                label="Center Y %",
                default=50.0,
                minimum=5.0,
                maximum=95.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="samples",
                label="Samples",
                default=2000,
                minimum=200,
                maximum=10000,
                step=100,
                decimals=0,
                kind="int",
            ),
            ControlDef(
                key="waveform",
                label="Waveform",
                default=0,
                minimum=0,
                maximum=3,
                step=1,
                decimals=0,
                kind="choice",
                choices=["|sin|", "sin", "|cos|", "triangle"],
            ),
        ]

    def generate_paths(
        self,
        params: dict[str, float],
        paper: PaperSize,
        stroke_mm: float,
    ) -> list[QPainterPath]:
        freq = params.get("frequency", 5.0)
        amp_frac = params.get("amplitude", 80.0) / 100.0
        phase_deg = params.get("phase", 0.0)
        duration = params.get("duration", 1.0)
        cx_frac = params.get("center_x", 50.0) / 100.0
        cy_frac = params.get("center_y", 50.0) / 100.0
        samples = int(params.get("samples", 2000))
        waveform = int(params.get("waveform", 0))

        phase_rad = np.radians(phase_deg)
        paper_w = paper.display_width
        paper_h = paper.display_height
        max_r = min(paper_w, paper_h) / 2 * amp_frac

        # Centre offset in mm (centred on paper = 0,0)
        cx = (cx_frac - 0.5) * paper_w
        cy = (cy_frac - 0.5) * paper_h

        theta = np.linspace(0, 2 * np.pi * duration, samples)
        signal = self._waveform(theta * freq + phase_rad, waveform)
        r = max_r * signal

        x = cx + r * np.cos(theta)
        y = cy + r * np.sin(theta)

        path = QPainterPath()
        path.moveTo(QPointF(x[0], y[0]))
        for i in range(1, len(x)):
            path.lineTo(QPointF(x[i], y[i]))

        return [path]

    # -----------------------------------------------------------------
    @staticmethod
    def _waveform(t: np.ndarray, kind: int) -> np.ndarray:
        if kind == 0:  # |sin|
            return np.abs(np.sin(t))
        elif kind == 1:  # sin (signed)
            return (np.sin(t) + 1) / 2  # map [-1,1] → [0,1]
        elif kind == 2:  # |cos|
            return np.abs(np.cos(t))
        elif kind == 3:  # triangle
            return (
                2 * np.abs(2 * (t / (2 * np.pi) - np.floor(t / (2 * np.pi) + 0.5)))
                - 0.5
                + 0.5
            )
        return np.abs(np.sin(t))
