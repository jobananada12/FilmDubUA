from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

class ReactionWidget(QWidget):
    """Interactive reaction-video placeholder/layer for the 9:16 canvas."""
    geometryChanged = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.path = ''
        self.circular = False
        self.x, self.y, self.w, self.h = .5, .78, .42, .30
        self._drag_start = None
        self._start = None
        self._resize = False
        self.setMinimumSize(80, 60)

    def set_video(self, path):
        self.path = path
        self.show()
        self.update()

    def set_circular(self, enabled):
        self.circular = enabled
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        self._drag_start = e.globalPosition().toPoint()
        self._start = (self.x, self.y, self.w, self.h)

    def mouseMoveEvent(self, e):
        if self._drag_start is None:
            return
        d = e.globalPosition().toPoint() - self._drag_start
        # Normalized movement; actual canvas maps this to its 9:16 coordinate space.
        self.x = max(0.0, min(1.0, self._start[0] + d.x()/max(1,self.parent().width())))
        self.y = max(0.0, min(1.0, self._start[1] + d.y()/max(1,self.parent().height())))
        self.geometryChanged.emit(self.x,self.y,self.w,self.h)
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag_start = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(Qt.white, 2))
        if self.circular:
            path = QPainterPath(); path.addEllipse(self.rect()); p.drawPath(path)
        else:
            p.drawRoundedRect(self.rect(), 12, 12)
        p.drawText(self.rect(), Qt.AlignCenter, Path(self.path).name if self.path else '👤 Моє відео')
