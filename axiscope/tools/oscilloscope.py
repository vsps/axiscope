"""Polar oscilloscope — rose-curve / Lissajous-on-a-circle traces.

The first (master) layer defines the base signal.  Additional modulator
layers modulate the master via one of three targets:

  * Radius  (AM) — scales the distance from centre (envelope shaping)
  * Rotation (FM) — warps angular velocity (spiral / twist patterns)
  * Add     — classic additive signal mixing

Processing order: FM → master radius → AM → Add → fit + scale.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from axiscope.models.paper import PaperSize
from axiscope.tools.base_tool import BaseTool, ControlDef
from axiscope.views.tool_controls import ToolControlsPanel


class OscilloscopeTool(BaseTool):
    """Polar trace with AM/FM modulation.

    Processing chain:
      1. FM modulators warp the angular parameter theta
      2. Master layer computes base radius r on the (warped) theta
      3. AM modulators scale the radius (envelope / ring modulation)
      4. Add modulators contribute additive signals
      5. Fit normalisation and final scale are applied
    """

    name = "Polar Oscilloscope"

    @property
    def controls(self) -> list[ControlDef]:
        """Master layer: all controls including duration/samples/center."""
        return [
            ControlDef(
                key="waveform",
                label="Wave",
                default=0,
                minimum=0,
                maximum=3,
                step=1,
                decimals=0,
                kind="choice",
                choices=["|sin|", "sin", "|cos|", "triangle"],
            ),
            ControlDef(
                key="frequency",
                label="Freq",
                default=5.0,
                minimum=0.5,
                maximum=50.0,
                step=0.5,
                decimals=1,
            ),
            ControlDef(
                key="amplitude",
                label="Amp %",
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
                label="Dur",
                default=1.0,
                minimum=0.5,
                maximum=100.0,
                step=1.0,
                decimals=1,
                suffix=" rev",
            ),
            ControlDef(
                key="center_x",
                label="CX %",
                default=50.0,
                minimum=5.0,
                maximum=95.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="center_y",
                label="CY %",
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
                maximum=50000,
                step=500,
                decimals=0,
                kind="int",
            ),
            ControlDef(
                key="fit",
                label="Fit",
                default=1,
                minimum=0,
                maximum=1,
                step=1,
                decimals=0,
                kind="choice",
                choices=["Off", "On"],
            ),
            ControlDef(
                key="final_scale",
                label="Scale",
                default=100.0,
                minimum=1.0,
                maximum=500.0,
                step=5.0,
                decimals=0,
                suffix=" %",
            ),
        ]

    @property
    def modulator_controls(self) -> list[ControlDef]:
        """Modulator layers: waveform/freq/amp/phase plus a Target selector.

        Target choices:
          - Radius  (AM) — modulates the distance from centre
          - Rotation (FM) — warps angular velocity for spirals
          - Add     — simple signal addition (classic summing)
        """
        return [
            ControlDef(
                key="waveform",
                label="Wave",
                default=1,
                minimum=0,
                maximum=3,
                step=1,
                decimals=0,
                kind="choice",
                choices=["|sin|", "sin", "|cos|", "triangle"],
            ),
            ControlDef(
                key="frequency",
                label="Freq",
                default=3.0,
                minimum=0.5,
                maximum=50.0,
                step=0.5,
                decimals=1,
            ),
            ControlDef(
                key="amplitude",
                label="Amp %",
                default=30.0,
                minimum=1.0,
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
                key="target",
                label="Target",
                default=0,
                minimum=0,
                maximum=2,
                step=1,
                decimals=0,
                kind="choice",
                choices=["Radius", "Rotation", "Add"],
            ),
        ]

    # -----------------------------------------------------------------
    def generate_paths(
        self,
        params: dict[str, float],
        paper: PaperSize,
        stroke_mm: float,
    ) -> list[QPainterPath]:
        # Split flat {key_N} dict into per-layer dicts (works for N=1 too)
        layers = ToolControlsPanel.split_layers(params)

        # Master params (first layer)
        master = layers[0]
        duration = master.get("duration", 1.0)
        samples = int(master.get("samples", 2000))
        cx_frac = master.get("center_x", 50.0) / 100.0
        cy_frac = master.get("center_y", 50.0) / 100.0
        paper_w = paper.display_width
        paper_h = paper.display_height

        cx = (cx_frac - 0.5) * paper_w
        cy = (cy_frac - 0.5) * paper_h

        # Shared theta array (may be warped by FM modulators)
        theta = np.linspace(0, 2 * np.pi * duration, samples)

        # Separate modulators by target type
        modulators = layers[1:] if len(layers) > 1 else []
        fm_mods = [m for m in modulators if int(m.get("target", 0)) == 1]  # Rotation
        am_mods = [m for m in modulators if int(m.get("target", 0)) == 0]  # Radius
        add_mods = [m for m in modulators if int(m.get("target", 0)) == 2]  # Add

        # -- Phase 1: FM — warp theta (Rotation modulation) -----------
        # Each FM modulator adds angular displacement proportional to
        # its waveform.  Amp % controls the maximum warp in radians.
        for mod in fm_mods:
            freq = mod.get("frequency", 3.0)
            amp_pct = mod.get("amplitude", 30.0)
            phase_deg = mod.get("phase", 0.0)
            wf = int(mod.get("waveform", 1))
            phase_rad = np.radians(phase_deg)
            # Warp depth: 0 .. π  (100 % = ±180° shift)
            warp_depth = (amp_pct / 100.0) * np.pi
            mod_signal = self._waveform(theta * freq + phase_rad, wf)
            # Map [0, 1] → [-warp_depth, +warp_depth]
            theta = theta + (2 * mod_signal - 1) * warp_depth

        # -- Phase 2: compute master radius on (possibly warped) theta -
        freq_m = master.get("frequency", 5.0)
        amp_pct_m = master.get("amplitude", 80.0)
        phase_deg_m = master.get("phase", 0.0)
        wf_m = int(master.get("waveform", 0))
        phase_rad_m = np.radians(phase_deg_m)
        max_r_master = min(paper_w, paper_h) / 2 * (amp_pct_m / 100.0)
        r = max_r_master * self._waveform(theta * freq_m + phase_rad_m, wf_m)

        # -- Phase 3: AM — modulate radius (Radius modulation) --------
        # Each AM modulator scales the radius by its waveform.
        # Amp % controls modulation depth: at 100 % the radius can go
        # to zero when the modulator is at 0.
        for mod in am_mods:
            freq = mod.get("frequency", 3.0)
            amp_pct = mod.get("amplitude", 30.0)
            phase_deg = mod.get("phase", 0.0)
            wf = int(mod.get("waveform", 1))
            phase_rad = np.radians(phase_deg)
            depth = amp_pct / 100.0  # 0 .. 1
            mod_signal = self._waveform(theta * freq + phase_rad, wf)  # [0, 1]
            # r *= (1 - depth) + depth * mod_signal   →  range [1-depth, 1]
            r = r * ((1 - depth) + depth * mod_signal)

        # -- Phase 4: Add — classic additive synthesis -----------------
        for mod in add_mods:
            freq = mod.get("frequency", 3.0)
            amp_pct = mod.get("amplitude", 30.0)
            phase_deg = mod.get("phase", 0.0)
            wf = int(mod.get("waveform", 1))
            phase_rad = np.radians(phase_deg)
            max_r_mod = min(paper_w, paper_h) / 2 * (amp_pct / 100.0)
            mod_signal = self._waveform(theta * freq + phase_rad, wf)
            r += max_r_mod * mod_signal

        # Fit: normalize to fill available radius
        fit_on = int(master.get("fit", 1)) == 1
        if fit_on and abs(r).max() > 0:
            max_avail = min(paper_w, paper_h) / 2 * 0.95
            r = r / abs(r).max() * max_avail

        # Final scale multiplier
        final_scale = master.get("final_scale", 100.0) / 100.0
        r = r * final_scale

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
        elif kind == 1:  # sin (signed → [0,1])
            return (np.sin(t) + 1) / 2
        elif kind == 2:  # |cos|
            return np.abs(np.cos(t))
        elif kind == 3:  # triangle
            return (
                2 * np.abs(2 * (t / (2 * np.pi) - np.floor(t / (2 * np.pi) + 0.5)))
                - 0.5
                + 0.5
            )
        return np.abs(np.sin(t))
