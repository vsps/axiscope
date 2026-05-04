"""GPU-accelerated canvas: page outline, preview, zoom/pan."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from axiscope.models.paper import PaperSize

# -- Colors -----------------------------------------------------------
BG_COLOR = QColor(30, 30, 30)
PAGE_FILL = QColor(255, 255, 255)
PAGE_STROKE = QColor(100, 100, 100)
PREVIEW_STROKE = QColor(0, 0, 0, 200)
GRID_COLOR = QColor(80, 80, 80, 60)

PADDING_RATIO = 0.10  # 10% padding around the page in the viewport


class PageOutlineItem(QGraphicsItem):
    """A rectangle representing the paper, painted as a white filled rect
    with a grey border.  Previews are drawn on top by adding paths to the
    same scene."""

    def __init__(self, rect: QRectF, parent=None):
        super().__init__(parent)
        self._rect = rect
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-2, -2, 2, 2)

    def paint(
        self,
        painter: QPainter,
        option,
        widget=None,  # noqa: ARG002
    ):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(PAGE_FILL))
        painter.setPen(QPen(PAGE_STROKE, 0.5))
        painter.drawRect(self._rect)


class CanvasView(QGraphicsView):
    """QGraphicsView with GPU viewport, scroll-zoom and middle-drag pan."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self.setViewport(QOpenGLWidget())
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)

        self._pan_start = None
        self._paper_size: PaperSize | None = None
        self._page_item: PageOutlineItem | None = None
        self._preview_items: list[QGraphicsItem] = []

    # -----------------------------------------------------------------
    def set_paper(self, paper: PaperSize) -> None:
        """Rebuild the scene for *paper*; center and fit it."""
        self._paper_size = paper
        scene = self.scene()
        scene.clear()
        self._preview_items.clear()

        w, h = paper.display_width, paper.display_height
        page_rect = QRectF(-w / 2, -h / 2, w, h)
        self._page_item = PageOutlineItem(page_rect)
        scene.addItem(self._page_item)
        scene.setSceneRect(page_rect.adjusted(-20, -20, 20, 20))
        self.fitInView(page_rect, Qt.KeepAspectRatio)

    # -----------------------------------------------------------------
    def clear_preview(self) -> None:
        for item in self._preview_items:
            self.scene().removeItem(item)
        self._preview_items.clear()

    def add_preview_path(self, path: QPainterPath) -> None:
        """Add a preview path on top of the page."""
        pen = QPen(PREVIEW_STROKE, 0.5)
        pen.setCosmetic(True)
        item = self.scene().addPath(path, pen)
        self._preview_items.append(item)

    def preview_paths(self) -> list[QPainterPath]:
        """Return all currently displayed preview paths (for plotting)."""
        paths: list[QPainterPath] = []
        for item in self._preview_items:
            if hasattr(item, "path"):
                paths.append(item.path())
        return paths

    # -----------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._page_item is not None:
            self.fitInView(self._page_item.boundingRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_start is not None:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._pan_start = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._page_item is not None:
            self.fitInView(self._page_item.boundingRect(), Qt.KeepAspectRatio)
        event.accept()
