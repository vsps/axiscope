# AxisScope — Project Plan

A minimal pen-plotter control app using the [AxiDraw Python API](https://github.com/evil-mad/axidraw), with a monospaced, utilitarian UI.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Required by the official AxiDraw API |
| GUI | PySide6 (Qt 6) | Mature, well-documented, native look, easy custom styling |
| Plotting / Canvas | Qt `QGraphicsScene` + `QGraphicsView` | Hardware-accelerated 2D scene graph, built-in zoom/pan, SVG support |
| SVG handling | Qt SVG module (`QtSvg`, `QtSvgWidgets`) | Reads standard SVG and exposes QPainter paths directly |
| AxiDraw API | `axidrawcontrol` from [axidraw](https://pypi.org/project/axidraw/) | Direct control of motors, pen, and plot execution |
| Math functions | `numpy` + `sympy` (optional for expression parsing) | Speed + symbolic differentiation for Lissajous / polar curves |
| Packaging | `pyinstaller` (optional) | Single .exe for distribution |

---

## Project File Structure

```
axiscope/
├── PLAN.md                     # This file
├── README.md
├── requirements.txt
├── axiscope/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── device.py           # AxiDraw device detection & state
│   │   ├── settings.py         # User settings (pen height, speed, etc.)
│   │   └── paper.py            # Paper size definitions (ISO A series)
│   ├── views/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Top-level window layout
│   │   ├── toolbar.py          # Top single-row toolbar
│   │   ├── canvas.py           # Central QGraphicsView + page outline + preview
│   │   ├── status_bar.py       # Bottom status line + action buttons
│   │   └── settings_dialog.py  # Settings popup (gear icon)
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── plot_controller.py  # Orchestrates plotting (SVG or generated paths)
│   │   └── draw_controller.py  # Orchestrates drawing tool mode
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base_tool.py        # Abstract base class for a drawing tool
│   │   └── oscilloscope.py     # Mono polar oscilloscope tool (first tool)
│   └── utils/
│       ├── __init__.py
│       ├── paths.py            # Conversion utilities (Qt paths ↔ AxiDraw paths)
│       └── svg_loader.py       # SVG file loading & preview helpers
└── tests/
```

---

## UI Layout (Wireframe)

```
┌─────────────────────────────────────────────────────────────────┐
│ [⚙] │ Paper: [A4 ▼] │ [ Load SVG ] │ Tool: [ Oscilloscope ▼ ] │   ← Toolbar
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌───────────────────┐                        │
│                    │                   │                        │
│                    │   Page outline    │                        │
│                    │   + preview       │                        │   ← Canvas
│                    │   (centered)      │                        │
│                    │                   │                        │
│                    └───────────────────┘                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  CONNECTED  │ USB: AxiDraw V3 │ X/Y: (120.5, 80.2)             │   ← Status line
│  [Toggle Motors]  [▲ Raise Pen / ▼ Lower Pen]  [ ▶ PLOT ]      │   ← Action buttons
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Toolbar (`views/toolbar.py`)

A single horizontal bar. No traditional menu bar.

| Widget | Function |
|--------|----------|
| ⚙ Gear button | Opens `SettingsDialog` popup |
| Paper dropdown | Select from ISO A sizes: A0–A10 (default A4) |
| Load SVG button | Opens file dialog, loads SVG into canvas preview |
| Tool dropdown | Select active drawing tool. Starts with one entry: **Polar Oscilloscope** |
| Tool controls panel (dynamic) | Below the toolbar or as a side panel, shows sliders/inputs for the selected tool's parameters (e.g., frequency, amplitude, phase, duration for the oscilloscope). Collapsed when in SVG mode. |

### 2. Canvas (`views/canvas.py`)

- `QGraphicsView` displaying a `QGraphicsScene`.
- Draws an outlined rectangle representing the selected paper size, scaled to fit the viewport with padding.
- **SVG mode**: Renders the loaded SVG centered inside the paper rectangle.
- **Drawing tool mode**: Renders a live preview of the generated tool paths, centered on the page.
- Scroll-wheel zoom; middle-click drag to pan. Double-click to fit-to-window.
- Grid overlay (optional, toggled in settings).

### 3. Status Bar + Action Buttons (`views/status_bar.py`)

Left-aligned status text:
- Connection state (e.g. `CONNECTED` / `DISCONNECTED`)
- Device info (USB port, model, firmware version)
- Current toolhead X/Y position (if available from API)

Right-aligned action buttons:
| Button | Function |
|--------|----------|
| **Toggle Motors** | Enable/disable stepper motors. Shows current state (latched/unlatched). |
| **▲▼ Raise/Lower Pen** | Toggle pen up/down. Label updates to reflect current state. |
| **▶ PLOT** | Start the plot. Sends current scene contents to the AxiDraw. Button shows progress ring / disabled while plotting. |

**Plot sequence** (in `plot_controller.py`):
1. Convert scene paths to AxiDraw plot commands.
2. Optionally run a bounding-box dry-run (if that API option exists).
3. Execute the plot.
4. Return pen to home/rest position.

### 4. Settings Dialog (`views/settings_dialog.py`)

Pop-up modal triggered by the gear icon. Contains tabs or sections:

**Device tab:**
- Auto-detect AxiDraw (scan USB)
- Manual USB port selection
- Device model / firmware info display

**Pen settings tab:**
- Pen-up height (% or mm)
- Pen-down height (% or mm)
- Pen-up / pen-down speed
- Pen-up delay (ms)
- Pen-down delay (ms)

**Plot settings tab:**
- Plot speed (default / max)
- Acceleration
- Return-to-home after plot (checkbox)
- Auto-rotate for landscape (checkbox)
- Number of copies
- Layer to plot (for multi-layer SVGs)

**Canvas settings tab:**
- Show grid overlay
- Grid spacing
- Refresh on settings change

### 5. Paper Model (`models/paper.py`)

Standard ISO A series dimensions in mm (always landscape):
- A0: 1189 × 841
- A1: 841 × 594
- A2: 594 × 420
- A3: 420 × 297
- A4: 297 × 210
- A5: 210 × 148
- A6: 148 × 105
- A7: 105 × 74
- A8: 74 × 52
- A9: 52 × 37
- A10: 37 × 26

Paper is always landscape by default.

### 6. Drawing Tools (`tools/`)

#### Base tool (`base_tool.py`)

Abstract interface:
```python
class BaseTool(ABC):
    name: str
    controls: list[ControlDef]          # Parameter definitions for auto-generating UI

    @abstractmethod
    def generate_paths(self, params: dict, paper: PaperSize) -> QPainterPath:
        """Return scene-space path(s) to be previewed and plotted."""
```

#### Polar Oscilloscope (`tools/oscilloscope.py`)

First drawing tool. Draws a mono polar trace on the page.

**Controls (sliders with numeric entry):**
- **Frequency** — number of polar lobes/rotations (0.1 – 100)
- **Amplitude** — max radius as % of page width (5% – 95%)
- **Phase offset** — rotation offset (0° – 360°)
- **Duration** — how many full sweeps the trace covers (0.5 – 10)
- **Center X / Y** — center point on page as % (default 50%, 50%)
- **Samples** — number of points generated (100 – 10000, default 2000)

**Math:**
```
θ(t) = 2π · freq · t          (t from 0 to duration)
r(t) = amplitude · |sin(θ(t) + phase)|   (or other waveform shapes)
x = cx + r(t) · cos(θ(t))
y = cy + r(t) · sin(θ(t))
```

**Stretch goals for future tools:** Lissajous figures, spiral generator, fractal trees, Hatch fill, Text engraver.

---

## Data Flow

```
 ┌──────────┐     ┌──────────────┐     ┌────────────┐
 │  Toolbar  │────▶│ PlotController │────▶│  AxiDraw   │
 │ (settings)│     │              │     │   API      │
 └──────────┘     │ - convert    │     └────────────┘
                  │ - preview    │
 ┌──────────┐     │ - execute    │     ┌────────────┐
 │  Canvas   │◀───▶│              │────▶│  SVG file  │
 │ (preview) │     └──────────────┘     │  loader    │
 └──────────┘                           └────────────┘
       ▲
       │
 ┌──────────┐
 │  Drawing  │
 │  Tool     │
 │ (osc, etc)│
 └──────────┘
```

1. **Settings / Device select** → updates `DeviceModel` → `PlotController` uses it for API calls.
2. **SVG Load** → `svg_loader` parses SVG → `QPainterPath` → `Canvas` preview.
3. **Drawing Tool params change** → tool generates new `QPainterPath` → `Canvas` preview updates live.
4. **PLOT button** → `PlotController` takes current preview paths → converts to AxiDraw commands → sends to device.

---

## Development Phases

### Phase 1 — Skeleton & Canvas (MVP)
- [ ] Set up project structure, `requirements.txt`, virtual env
- [ ] Implement `main.py` with `QApplication` boilerplate
- [ ] Implement `main_window.py` layout (toolbar + canvas + status bar placeholders)
- [ ] Implement `canvas.py`: page outline rectangle, zoom to fit, monospaced styling
- [ ] Implement `paper.py` with ISO A sizes
- [ ] Implement paper size dropdown in toolbar

### Phase 2 — Device & Settings ✅
- [x] Implement `device.py` — scan for AxiDraw, connect
- [x] Implement `settings.py` — all pen/speed parameters with defaults
- [x] Implement `settings_dialog.py` — settings UI popup (4 tabs)
- [x] Implement settings gear button integration
- [x] Wire up device status in status bar

### Phase 3 — SVG Plotting ✅
- [x] Implement `svg_loader.py` — load SVG, extract paths, force 1px stroke, scale to paper
- [x] Implement Load SVG button and file dialog
- [x] Preview SVG on canvas, centered on paper
- [x] Implement `plot_controller.py` — convert preview to AxiDraw commands (stub)
- [x] Implement PLOT button + progress feedback
- [x] Implement Toggle Motors and Raise/Lower Pen buttons

### Phase 4 — Drawing Tools ✅
- [x] Implement `base_tool.py` abstract class with `ControlDef`
- [x] Implement `oscilloscope.py` polar trace generator (8 controls, 4 waveforms)
- [x] Build dynamic `ToolControlsPanel` (auto-generates spinboxes/combos from ControlDefs)
- [x] Live preview on canvas — regenerates on every slider change
- [x] PLOT from drawing tool (shares same plot pipeline as SVG)
- [x] Paper change regenerates tool preview to new page size

### Phase 5 — Polish ✅
- [x] Monospaced font styling (JetBrains Mono / Fira Code / Consolas fallback)
- [x] Dark theme (full widget coverage: tabs, spinboxes, checkboxes, group boxes)
- [x] Error handling: disconnected device guards on all actions, SVG parse errors, tool errors
- [x] Keyboard shortcuts: Ctrl+O (load), Ctrl+P (plot), Ctrl+M (motors), Ctrl+Up/Down (pen), Esc (deselect tool), Ctrl+, (settings)
- [x] Packaging script (`build.py` — PyInstaller onedir with hidden imports)
- [x] Window title updates with loaded filename

---

## Key Design Decisions

1. **PySide6 over tkinter**: Better SVG support, hardware-accelerated canvas, mature layout system, proper theming.
2. **QPainterPath as internal path format**: Native Qt type, works directly with `QGraphicsScene` for preview *and* can be converted to AxiDraw coordinates for plotting.
3. **Tool plugin architecture**: `BaseTool` makes it trivial to add new drawing tools later — each tool is a single file implementing `generate_paths()` and declaring its controls.
4. **All coordinates in mm internally**: Paper sizes are in mm, the canvas maps mm → pixels for display, and the AxiDraw API uses mm — so mm is the natural internal unit.
5. **No persistent config yet (Phase 2)**: Keep it simple. Settings can be saved/loaded from a JSON file later.

---

## Questions / Open Items

- [ ] Does the user have a preferred monospaced font, or is system default monospace acceptable?
- [ ] Should the oscilloscope support multiple waveform shapes (sine, square, triangle) from the start, or just start with sine?
- [ ] For the SVG mode: should only the outline paths be plotted, or should fills be hatched? (AxiDraw cannot fill.)
- [ ] Should the app remember the last-used settings across sessions (persistent config)?
- [ ] Any preference for dark vs light default theme?
