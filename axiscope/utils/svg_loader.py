"""SVG loading with forced stroke width and paper-centering.

Parses SVG files directly via ``xml.etree`` — handles ``<path>``,
``<rect>``, ``<circle>``, ``<ellipse>``, ``<line>``, ``<polyline>``
and ``<polygon>`` elements.  All strokes are forced to a uniform width
and artwork is scaled to fit the selected paper.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from math import cos, pi, sin, sqrt, tan

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPen, QTransform

from axiscope.models.paper import PaperSize

# Regex for SVG path commands (handles comma/space separated numbers)
_PATH_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.\d*|\.?\d+)(?:[eE][-+]?\d+)?"
)
_SVG_NS = "http://www.w3.org/2000/svg"


# -- public API --------------------------------------------------------


def load_svg(
    filepath: str,
    paper: PaperSize,
    stroke_mm: float,
) -> list[QPainterPath]:
    """Load an SVG file, force all strokes to *stroke_mm* width,
    scale artwork to fit centred on *paper*, and return a list of
    ``QPainterPath`` objects.
    """

    tree = ET.parse(filepath)
    root = tree.getroot()

    # Determine viewBox
    vb_str = _attr(root, "viewBox")
    if vb_str:
        parts = [float(x) for x in vb_str.strip().split()]
        if len(parts) >= 4:
            viewbox = QRectF(parts[0], parts[1], parts[2], parts[3])
        else:
            viewbox = QRectF(0, 0, 100, 100)
    else:
        w = float(_attr(root, "width", "100"))
        h = float(_attr(root, "height", "100"))
        viewbox = QRectF(0, 0, w, h)

    # Collect all shape paths in SVG coordinates
    raw_paths: list[QPainterPath] = []
    _walk_svg(root, raw_paths)

    # Compute tight bounding-box of the actual drawing content
    content_bbox = QRectF()
    for p in raw_paths:
        if not p.isEmpty():
            content_bbox = content_bbox.united(p.boundingRect())
    if content_bbox.isEmpty():
        content_bbox = viewbox

    # Uniform scale to fit the *content* on paper with 5% margin
    paper_w = paper.display_width
    paper_h = paper.display_height
    margin = 0.05
    avail_w = paper_w * (1 - 2 * margin)
    avail_h = paper_h * (1 - 2 * margin)

    bw, bh = content_bbox.width(), content_bbox.height()
    if bw > 0 and bh > 0:
        scale = min(avail_w / bw, avail_h / bh)
    else:
        scale = 1.0

    xform = QTransform()
    xform.scale(scale, scale)
    xform.translate(-content_bbox.center().x(), -content_bbox.center().y())

    result: list[QPainterPath] = []
    for path in raw_paths:
        if path.isEmpty():
            continue
        mapped = xform.map(path)
        if not mapped.isEmpty():
            result.append(mapped)

    return result


# -- XML tree walk -----------------------------------------------------


def _walk_svg(elem: ET.Element, out: list[QPainterPath]) -> None:
    """Recursively walk the SVG XML tree and convert shape elements."""
    tag = _local_tag(elem)

    if tag == "path":
        p = _parse_path(elem)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "rect":
        p = _parse_rect(elem)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "circle":
        p = _parse_circle(elem)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "ellipse":
        p = _parse_ellipse(elem)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "line":
        p = _parse_line(elem)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "polyline":
        p = _parse_poly(elem, closed=False)
        if p and not p.isEmpty():
            out.append(p)
    elif tag == "polygon":
        p = _parse_poly(elem, closed=True)
        if p and not p.isEmpty():
            out.append(p)

    for child in elem:
        _walk_svg(child, out)


# -- shape parsers -----------------------------------------------------


def _parse_path(elem: ET.Element) -> QPainterPath | None:
    d = _attr(elem, "d")
    if not d:
        return None
    tokens = _PATH_RE.findall(d)
    path = QPainterPath()
    i = 0
    x, y = 0.0, 0.0  # current point
    start_x, start_y = 0.0, 0.0  # subpath start
    while i < len(tokens):
        cmd = tokens[i]
        if cmd.isalpha():
            i += 1
        else:
            cmd = "L"  # implicit line
        upper = cmd.upper()

        if upper == "M":
            x, y = _next_coord(tokens, i)
            path.moveTo(x, y)
            start_x, start_y = x, y
            i += 2
        elif upper == "L":
            x, y = _next_coord(tokens, i)
            path.lineTo(x, y)
            i += 2
        elif upper == "H":
            x = _next_num(tokens, i)
            path.lineTo(x, y)
            i += 1
        elif upper == "V":
            y = _next_num(tokens, i)
            path.lineTo(x, y)
            i += 1
        elif upper == "C":
            x1, y1 = _next_coord(tokens, i)
            x2, y2 = _next_coord(tokens, i + 2)
            x, y = _next_coord(tokens, i + 4)
            path.cubicTo(x1, y1, x2, y2, x, y)
            i += 6
        elif upper == "S":
            x2, y2 = _next_coord(tokens, i)
            x, y = _next_coord(tokens, i + 2)
            path.cubicTo(x, y, x2, y2, x, y)
            i += 4
        elif upper == "Q":
            x1, y1 = _next_coord(tokens, i)
            x, y = _next_coord(tokens, i + 2)
            path.quadTo(x1, y1, x, y)
            i += 4
        elif upper == "T":
            x, y = _next_coord(tokens, i)
            path.quadTo(x, y, x, y)
            i += 2
        elif upper == "A":
            rx, ry = _next_coord(tokens, i)
            rot = _next_num(tokens, i + 2)
            large = _next_num(tokens, i + 3) > 0
            sweep = _next_num(tokens, i + 4) > 0
            ex, ey = _next_coord(tokens, i + 5)
            _arc_to(path, x, y, rx, ry, rot, large, sweep, ex, ey)
            x, y = ex, ey
            i += 7
        elif upper == "Z":
            path.closeSubpath()
            x, y = start_x, start_y
        else:
            i += 1  # skip unknown
    return path


def _parse_rect(elem: ET.Element) -> QPainterPath:
    x = float(_attr(elem, "x", "0"))
    y = float(_attr(elem, "y", "0"))
    w = float(_attr(elem, "width", "0"))
    h = float(_attr(elem, "height", "0"))
    path = QPainterPath()
    path.addRect(QRectF(x, y, w, h))
    return path


def _parse_circle(elem: ET.Element) -> QPainterPath:
    cx = float(_attr(elem, "cx", "0"))
    cy = float(_attr(elem, "cy", "0"))
    r = float(_attr(elem, "r", "0"))
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), r, r)
    return path


def _parse_ellipse(elem: ET.Element) -> QPainterPath:
    cx = float(_attr(elem, "cx", "0"))
    cy = float(_attr(elem, "cy", "0"))
    rx = float(_attr(elem, "rx", "0"))
    ry = float(_attr(elem, "ry", "0"))
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), rx, ry)
    return path


def _parse_line(elem: ET.Element) -> QPainterPath:
    x1 = float(_attr(elem, "x1", "0"))
    y1 = float(_attr(elem, "y1", "0"))
    x2 = float(_attr(elem, "x2", "0"))
    y2 = float(_attr(elem, "y2", "0"))
    path = QPainterPath()
    path.moveTo(x1, y1)
    path.lineTo(x2, y2)
    return path


def _parse_poly(elem: ET.Element, closed: bool) -> QPainterPath:
    pts_str = _attr(elem, "points", "")
    coords = [float(x) for x in pts_str.replace(",", " ").split() if x]
    if len(coords) < 4:
        return QPainterPath()
    path = QPainterPath()
    path.moveTo(coords[0], coords[1])
    for i in range(2, len(coords), 2):
        path.lineTo(coords[i], coords[i + 1])
    if closed:
        path.closeSubpath()
    return path


# -- helpers -----------------------------------------------------------


def _local_tag(elem: ET.Element) -> str:
    tag = elem.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _attr(elem: ET.Element, name: str, default: str = "") -> str:
    val = elem.get(name)
    if val is not None:
        return val
    # Try with SVG namespace
    val = elem.get(f"{{{_SVG_NS}}}{name}")
    return val if val is not None else default


def _next_coord(tokens: list[str], i: int) -> tuple[float, float]:
    return float(tokens[i]), float(tokens[i + 1])


def _next_num(tokens: list[str], i: int) -> float:
    return float(tokens[i])


def _stroke_path(path: QPainterPath, pen: QPen) -> QPainterPath:
    from PySide6.QtGui import QPainterPathStroker

    s = QPainterPathStroker(pen)
    s.setWidth(pen.widthF())
    return s.createStroke(path)


# -- arc-to implementation ---------------------------------------------


def _arc_to(
    path: QPainterPath,
    x0: float,
    y0: float,
    rx: float,
    ry: float,
    rot: float,
    large: bool,
    sweep: bool,
    x1: float,
    y1: float,
) -> None:
    """Approximate an SVG arc with cubic Bézier segments."""
    if rx <= 0 or ry <= 0 or (abs(x1 - x0) < 1e-6 and abs(y1 - y0) < 1e-6):
        path.lineTo(x1, y1)
        return

    rot_rad = rot * pi / 180.0
    cos_r = cos(rot_rad)
    sin_r = sin(rot_rad)

    # Transform to normalized coordinates
    dx = (x0 - x1) / 2.0
    dy = (y0 - y1) / 2.0
    x0p = cos_r * dx + sin_r * dy
    y0p = -sin_r * dx + cos_r * dy

    # Ensure radii are large enough
    rx2 = rx * rx
    ry2 = ry * ry
    x0p2 = x0p * x0p
    y0p2 = y0p * y0p
    lam = x0p2 / rx2 + y0p2 / ry2
    if lam > 1.0:
        s = sqrt(lam)
        rx *= s
        ry *= s
        rx2 = rx * rx
        ry2 = ry * ry

    # Center of ellipse
    num = rx2 * ry2 - rx2 * y0p2 - ry2 * x0p2
    den = rx2 * y0p2 + ry2 * x0p2
    coeff = sqrt(max(0.0, num / den))
    if large == sweep:
        coeff = -coeff
    cxp = coeff * (rx * y0p) / ry
    cyp = coeff * (-ry * x0p) / rx

    cx = cos_r * cxp - sin_r * cyp + (x0 + x1) / 2.0
    cy = sin_r * cxp + cos_r * cyp + (y0 + y1) / 2.0

    # Angles
    def angle(ux: float, uy: float) -> float:
        a = atan2_safe(uy, ux)
        return a

    ux = (x0p - cxp) / rx
    uy = (y0p - cyp) / ry
    theta1 = angle(ux, uy)

    vx = (-x0p - cxp) / rx
    vy = (-y0p - cyp) / ry
    dtheta = angle(vx, vy) - theta1

    if sweep and dtheta < 0:
        dtheta += 2 * pi
    elif not sweep and dtheta > 0:
        dtheta -= 2 * pi

    # Approximate with cubics
    segments = max(4, int(abs(dtheta) / (pi / 2) + 1))
    dtheta /= segments
    t = tan(dtheta / 2.0)
    alpha = sin(dtheta) * (sqrt(4.0 + 3.0 * t * t) - 1.0) / 3.0

    for _ in range(segments):
        sin_t1 = sin(theta1)
        cos_t1 = cos(theta1)
        theta2 = theta1 + dtheta
        sin_t2 = sin(theta2)
        cos_t2 = cos(theta2)

        p1x = cx + rx * (cos_t1 * cos_r - sin_t1 * sin_r)
        p1y = cy + rx * (cos_t1 * sin_r + sin_t1 * cos_r)

        cp1x = p1x - alpha * (rx * (sin_t1 * cos_r + cos_t1 * sin_r))
        cp1y = p1y - alpha * (rx * (sin_t1 * sin_r - cos_t1 * cos_r))

        p2x = cx + rx * (cos_t2 * cos_r - sin_t2 * sin_r)
        p2y = cy + rx * (cos_t2 * sin_r + sin_t2 * cos_r)

        cp2x = p2x + alpha * (rx * (sin_t2 * cos_r + cos_t2 * sin_r))
        cp2y = p2y + alpha * (rx * (sin_t2 * sin_r - cos_t2 * cos_r))

        path.cubicTo(cp1x, cp1y, cp2x, cp2y, p2x, p2y)
        theta1 = theta2


def atan2_safe(y: float, x: float) -> float:
    """atan2 that handles edge cases."""
    from math import atan2

    return atan2(y, x)
