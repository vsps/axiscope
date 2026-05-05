<pre>
░█▀█░█░█░▀█▀░█▀▀░█▀▀░█▀▀░█▀▀░█▀█░█▀▀
░█▀█░▄▀▄░░█░░▀▀█░█░░░█░░░█░█░█▀▀░█▀▀
░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░░░▀▀▀
</pre>

A desktop plotter UI for [AxiDraw](https://axidraw.com/) pen plotters. Load and position SVGs, control the device directly, and generate artwork with built-in generative tools.

## Features

- **Device control** — connect over USB, engage/disengage motors, raise/lower pen, nudge position, align and home
- **SVG import** — load any SVG, scale and offset it, then send it to the plotter
- **SVG export** — save canvas paths as clean SVG files
- **Oscilloscope tool** — polar/Lissajous waveform generator with FM, AM, ADSR envelope, and real-time audio preview
- **Live preview** — OpenGL-accelerated canvas with zoom and pan

## Requirements

- Python 3.10+
- [pyaxidraw](https://axidraw.com/doc/py_api/) — install separately (not on PyPI; see below)
- AxiDraw connected via USB

## Install

**1. Install pyaxidraw** (follow the official instructions):

```
pip install https://cdn.evilmadscientist.com/dl/ad/public/AxiDraw_API.zip
```

**2. Clone and install dependencies:**

```
git clone https://github.com/vsps/axiscope.git
cd axiscope
pip install -r requirements.txt
```

**3. Run:**

```
python -m axiscope.main
```

## Usage

1. Open **Settings** (⚙ or `Ctrl+,`) → **Device** tab → scan for your AxiDraw and connect
2. Click **ENGAGE MOTORS** to lock the axes
3. Use the nudge arrows (▲▼◀▶) to position the pen over your paper's home corner
4. Load an SVG or select a generative tool from the toolbar
5. Click **▶ PLOT** to draw

## Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Load SVG |
| `Ctrl+S` | Save SVG |
| `Ctrl+P` | Plot |
| `Ctrl+M` | Toggle motors |
| `Ctrl+↑` / `Ctrl+↓` | Pen up / down |
| `Ctrl+,` | Settings |
| `Esc` | Deselect tool |
