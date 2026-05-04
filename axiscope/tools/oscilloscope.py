"""Polar oscilloscope — audio-style signal chain wrapped around a circle.

Signal flow:
  carrier(FM(freq)) → AM modulate → ADSR envelope → fit / scale → polar plot

All frequencies are in *cycles per revolution*.  A 440 Hz carrier completes
440 oscillations in one 360° rotation.  Audio preview plays back at 1 rev/s
so these numbers map directly to audible Hz.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import QWidget

from axiscope.models.paper import PaperSize
from axiscope.tools.base_tool import BaseTool, ControlDef


class OscilloscopeTool(BaseTool):
    """Audio-oscilloscope drawing tool.

    Three-line controls layout:
      Line 1 — Signal:  carrier Hz / wave / FM Hz / FM % / AM Hz / AM %
      Line 2 — ADSR:    attack % / decay % / sustain % / release %
      Line 3 — Render:  duration / samples/rev / fit / scale / cx / cy / play

    Processing order:
      1. FM phase modulation: warp the carrier phase
      2. Carrier waveform: sine | square | saw
      3. AM amplitude modulation: scale the carrier by AM oscillator
      4. ADSR envelope: per-revolution attack-decay-sustain-release
      5. Fit normalisation + final scale → polar coords
    """

    name = "Oscilloscope"

    # -- Controls -------------------------------------------------------
    @property
    def controls(self) -> list[ControlDef]:
        """Flat list of every control — used for introspection / defaults.

        The custom ``OscilloscopeControls`` widget lays these out in
        three labelled rows; this list only needs to be complete and
        key-unique.
        """
        return [
            # ── Line 1: Signal ────────────────────────────────────
            ControlDef(
                key="carrier_freq",
                label="Carrier",
                default=440.0,
                minimum=20.0,
                maximum=20000.0,
                step=10.0,
                decimals=0,
                suffix=" Hz",
            ),
            ControlDef(
                key="carrier_wave",
                label="Wave",
                default=0,
                minimum=0,
                maximum=2,
                step=1,
                decimals=0,
                kind="choice",
                choices=["Sine", "Square", "Saw"],
            ),
            ControlDef(
                key="fm_freq",
                label="FM Hz",
                default=100.0,
                minimum=0.01,
                maximum=10000.0,
                step=10.0,
                decimals=1,
                suffix=" Hz",
            ),
            ControlDef(
                key="fm_amount",
                label="FM %",
                default=0.0,
                minimum=0.0,
                maximum=100.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="am_freq",
                label="AM Hz",
                default=10.0,
                minimum=0.01,
                maximum=20000.0,
                step=10.0,
                decimals=1,
                suffix=" Hz",
            ),
            ControlDef(
                key="am_amount",
                label="AM %",
                default=0.0,
                minimum=0.0,
                maximum=100.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="offset",
                label="Offset",
                default=0.0,
                minimum=-100.0,
                maximum=100.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            # ── Line 2: ADSR ──────────────────────────────────────
            ControlDef(
                key="bypass_adsr",
                label="ADSR",
                default=0,
                minimum=0,
                maximum=1,
                step=1,
                decimals=0,
                kind="choice",
                choices=["Off", "On"],
            ),
            ControlDef(
                key="attack",
                label="Attack",
                default=5.0,
                minimum=0.0,
                maximum=50.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="decay",
                label="Decay",
                default=10.0,
                minimum=0.0,
                maximum=50.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="sustain",
                label="Sustain",
                default=80.0,
                minimum=0.0,
                maximum=100.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            ControlDef(
                key="release",
                label="Release",
                default=10.0,
                minimum=0.0,
                maximum=50.0,
                step=1.0,
                decimals=0,
                suffix=" %",
            ),
            # ── Line 3: Render ────────────────────────────────────
            ControlDef(
                key="mode",
                label="Mode",
                default=0,
                minimum=0,
                maximum=1,
                step=1,
                decimals=0,
                kind="choice",
                choices=["Polar", "Lissajous"],
            ),
            ControlDef(
                key="y_ratio",
                label="Y Ratio",
                default=2.0,
                minimum=1.0,
                maximum=10.0,
                step=0.5,
                decimals=1,
                suffix=" :1",
            ),
            ControlDef(
                key="sweep",
                label="Sweep",
                default=0,
                minimum=0,
                maximum=8,
                step=1,
                decimals=0,
                kind="choice",
                choices=["20", "40", "60", "80", "100", "120", "140", "160", "200"],
            ),
            ControlDef(
                key="duration",
                label="Dur",
                default=3.0,
                minimum=0.5,
                maximum=100.0,
                step=0.5,
                decimals=1,
                suffix=" rev",
            ),
            ControlDef(
                key="samples_per_rev",
                label="Smp/rev",
                default=20000,
                minimum=1000,
                maximum=200000,
                step=1000,
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
        ]

    # -- Custom controls widget ----------------------------------------
    def create_controls_widget(self, parent: QWidget | None = None) -> QWidget:
        from axiscope.views.oscilloscope_controls import OscilloscopeControls

        return OscilloscopeControls(self, parent)

    # -- Signal generation ---------------------------------------------
    def generate_paths(
        self,
        params: dict[str, float],
        paper: PaperSize,
        stroke_mm: float,
    ) -> list[QPainterPath]:
        master = params

        duration = master.get("duration", 3.0)
        samples_per_rev = int(master.get("samples_per_rev", 20000))
        total_samples = int(samples_per_rev * duration)

        paper_w = paper.display_width
        paper_h = paper.display_height
        cx_frac = master.get("center_x", 50.0) / 100.0
        cy_frac = master.get("center_y", 50.0) / 100.0
        cx = (cx_frac - 0.5) * paper_w
        cy = (cy_frac - 0.5) * paper_h

        # ---- theta array ---------------------------------------------
        theta = np.linspace(0, 2 * np.pi * duration, total_samples)

        # ---- Sweep & effective frequencies --------------------------
        carrier_freq = master.get("carrier_freq", 440.0)
        sweep_idx = int(master.get("sweep", 0))
        sweep_values = [20, 40, 60, 80, 100, 120, 140, 160, 200]
        sweep = sweep_values[min(sweep_idx, len(sweep_values)-1)]
        eff_carrier = carrier_freq / sweep
        eff_fm = master.get("fm_freq", 100.0) / sweep
        eff_am = master.get("am_freq", 10.0) / sweep

        # ---- FM ------------------------------------------------------
        fm_amount = master.get("fm_amount", 0.0) / 100.0
        if fm_amount > 0 and eff_fm > 0:
            phase = eff_carrier * theta + fm_amount * eff_carrier * np.sin(
                eff_fm * theta
            )
        else:
            phase = eff_carrier * theta

        # ---- Carrier waveform ----------------------------------------
        wave = int(master.get("carrier_wave", 0))
        carrier = self._waveform(phase, wave)  # [0, 1]

        # ---- AM ------------------------------------------------------
        am_amount = master.get("am_amount", 0.0) / 100.0
        if am_amount > 0 and eff_am > 0:
            am_env = 1.0 + am_amount * np.sin(eff_am * theta)
            r = carrier * am_env
        else:
            r = carrier

        # ---- ADSR envelope (per-revolution) --------------------------
        attack_pct = master.get("attack", 5.0) / 100.0
        decay_pct = master.get("decay", 10.0) / 100.0
        sustain_level = master.get("sustain", 80.0) / 100.0
        release_pct = master.get("release", 10.0) / 100.0
        bypass_adsr = int(master.get("bypass_adsr", 1)) == 0
        if not bypass_adsr and (attack_pct > 0 or decay_pct > 0 or release_pct > 0):
            r = r * self._adsr_envelope(
                theta, attack_pct, decay_pct, sustain_level, release_pct
            )

        # ---- Centre the signal (bipolar) ----------------------------
        r_min, r_max = r.min(), r.max()
        if r_max > r_min:
            r = (r - r_min) / (r_max - r_min)  # [0, 1]
        r = 2.0 * r - 1.0  # [-1, 1]
        offset_pct = master.get("offset", 0.0) / 100.0
        if offset_pct != 0:
            r = r + offset_pct

        # ---- Fit & scale ---------------------------------------------
        fit_on = int(master.get("fit", 1)) == 1
        if fit_on and abs(r).max() > 0:
            max_avail = min(paper_w, paper_h) / 2 * 0.95
            r = r / abs(r).max() * max_avail

        final_scale = master.get("final_scale", 100.0) / 100.0
        r = r * final_scale
        # Apply DC offset after fit+scale (adds to r, shifts pattern)
        offset_pct = master.get("offset", 0.0) / 100.0
        if offset_pct != 0:
            max_avail = min(paper_w, paper_h) / 2 * 0.95
            r = r + offset_pct * max_avail
        # ---- Polar or Lissajous -> Cartesian --------------------------
        mode = int(master.get("mode", 0))
        y_ratio = master.get("y_ratio", 2.0)
        half_w = paper_w / 2 * 0.95
        half_h = paper_h / 2 * 0.95
        half_scale = min(half_w, half_h)  # 1:1 for Lissajous

        if mode == 1:  # Lissajous - true X-Y oscilloscope
            # X channel: bipolar carrier [-1, +1] with AM + ADSR
            sig_x = 2.0 * carrier - 1.0
            if am_amount > 0 and eff_am > 0:
                sig_x = sig_x * am_env
            if not bypass_adsr and (attack_pct > 0 or decay_pct > 0 or release_pct > 0):
                sig_x = sig_x * self._adsr_envelope(
                    theta, attack_pct, decay_pct, sustain_level, release_pct
                )
            # Y channel: same waveform at different frequency, 90° out of phase
            y_phase = eff_carrier * theta * y_ratio + np.pi / 2
            if fm_amount > 0 and eff_fm > 0:
                y_phase = y_phase + fm_amount * eff_carrier * np.sin(eff_fm * theta)
            sig_y = 2.0 * self._waveform(y_phase, wave) - 1.0
            if am_amount > 0 and eff_am > 0:
                sig_y = sig_y * am_env
            if not bypass_adsr and (attack_pct > 0 or decay_pct > 0 or release_pct > 0):
                sig_y = sig_y * self._adsr_envelope(
                    theta, attack_pct, decay_pct, sustain_level, release_pct
                )
            # Fit: scale both axes uniformly
            if fit_on:
                peak = max(abs(sig_x).max(), abs(sig_y).max())
                if peak > 0:
                    sig_x = sig_x / peak
                    sig_y = sig_y / peak
            sig_x = sig_x * final_scale
            sig_y = sig_y * final_scale
            x = cx + sig_x * half_scale
            y = cy + sig_y * half_scale
        else:  # Polar
            x = cx + r * np.cos(theta)
            y = cy + r * np.sin(theta)

        path = QPainterPath()
        path.moveTo(QPointF(x[0], y[0]))
        for i in range(1, len(x)):
            path.lineTo(QPointF(x[i], y[i]))

        return [path]

    # -----------------------------------------------------------------
    @staticmethod
    def _waveform(phase: np.ndarray, kind: int) -> np.ndarray:
        """Map *phase* (radians) to [0, 1] for the chosen waveform."""
        if kind == 0:  # Sine
            return (np.sin(phase) + 1.0) / 2.0
        elif kind == 1:  # Square
            return (np.sign(np.sin(phase)) + 1.0) / 2.0
        elif kind == 2:  # Saw
            return (phase / (2 * np.pi)) % 1.0
        return (np.sin(phase) + 1.0) / 2.0

    @staticmethod
    def _adsr_envelope(
        theta: np.ndarray,
        attack: float,
        decay: float,
        sustain: float,
        release: float,
    ) -> np.ndarray:
        """Per-revolution ADSR envelope (one repeat every 2π).

        *attack*, *decay*, *release* are fractions of one revolution.
        *sustain* is the level (0..1) held between decay and release.
        """
        intra = (theta % (2 * np.pi)) / (2 * np.pi)  # [0, 1) per revolution
        env = np.zeros_like(intra)

        # Attack:  0 → attack
        a_mask = intra < attack
        if attack > 0:
            env[a_mask] = intra[a_mask] / attack

        # Decay:  attack → attack+decay
        d_start = attack
        d_end = attack + decay
        d_mask = (intra >= d_start) & (intra < d_end)
        if decay > 0:
            frac = (intra[d_mask] - d_start) / decay
            env[d_mask] = 1.0 - (1.0 - sustain) * frac

        # Sustain:  attack+decay → 1-release
        s_start = attack + decay
        s_end = 1.0 - release
        s_mask = (intra >= s_start) & (intra < s_end)
        env[s_mask] = sustain

        # Release:  1-release → 1
        r_start = 1.0 - release
        r_mask = intra >= r_start
        if release > 0:
            frac = (intra[r_mask] - r_start) / release
            env[r_mask] = sustain * (1.0 - frac)

        return np.clip(env, 0.0, 1.0)

    # -- Audio preview -------------------------------------------------
    def generate_audio(
        self,
        params: dict[str, float],
        sample_rate: int = 44100,
    ) -> np.ndarray | None:
        """Generate audio samples for the current parameters.

        Playback maps 1 revolution → 1 second, so *carrier_freq* and
        friends map directly to audible Hz.

        Returns a float64 NumPy array in [-1, +1] or ``None`` if
        ``sounddevice`` is not available.
        """
        try:
            import sounddevice as sd  # noqa: F401
        except ImportError:
            return None

        master = params
        duration = master.get("duration", 3.0)
        total_audio_samples = int(sample_rate * duration)

        # Time array: 1 rev = 1 s
        t = np.linspace(0, duration, total_audio_samples, endpoint=False)
        theta = 2 * np.pi * t  # convert seconds → radians

        # FM
        carrier_freq = master.get("carrier_freq", 440.0)
        fm_freq = master.get("fm_freq", 100.0)
        fm_amount = master.get("fm_amount", 0.0) / 100.0
        if fm_amount > 0 and fm_freq > 0:
            phase = carrier_freq * theta + fm_amount * carrier_freq * np.sin(
                fm_freq * theta
            )
        else:
            phase = carrier_freq * theta

        # Carrier
        wave = int(master.get("carrier_wave", 0))
        audio = self._waveform(phase, wave)  # [0, 1]

        # AM
        am_freq = master.get("am_freq", 10.0)
        am_amount = master.get("am_amount", 0.0) / 100.0
        if am_amount > 0 and am_freq > 0:
            am_env = 1.0 + am_amount * np.sin(am_freq * theta)
            audio = audio * am_env

        # ADSR
        attack_pct = master.get("attack", 5.0) / 100.0
        decay_pct = master.get("decay", 10.0) / 100.0
        sustain_level = master.get("sustain", 80.0) / 100.0
        release_pct = master.get("release", 10.0) / 100.0
        if attack_pct > 0 or decay_pct > 0 or release_pct > 0:
            audio = audio * self._adsr_envelope(
                theta, attack_pct, decay_pct, sustain_level, release_pct
            )

        # Normalise to [-1, +1]
        peak = abs(audio).max()
        if peak > 0:
            audio = audio / peak * 0.95

        return audio.astype(np.float64)
