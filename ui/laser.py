"""The laser pointer: a glowing red dot that follows the mouse. Clicks pass through."""

import math
import time

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from core.paths import LINUX


class Laser(QWidget):
    SIZE = 36

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.X11BypassWindowManagerHint
            | Qt.WindowTransparentForInput,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.start = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._follow)
        self.timer.start(16)
        self._follow()

    @property
    def x(self) -> float:
        return QCursor.pos().x()

    def _follow(self):
        pos = QCursor.pos()
        self.move(pos.x() - self.SIZE // 2, pos.y() - self.SIZE // 2)
        if LINUX:  # X11 bypass windows need a nudge; Windows keeps "on top" windows on top
            self.raise_()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.SIZE / 2, self.SIZE / 2)
        pulse = 1 + 0.15 * math.sin((time.monotonic() - self.start) * 12)
        glow = QRadialGradient(c, self.SIZE / 2 * pulse)
        glow.setColorAt(0, QColor(255, 40, 40, 255))
        glow.setColorAt(0.25, QColor(255, 30, 30, 230))
        glow.setColorAt(0.5, QColor(255, 0, 0, 90))
        glow.setColorAt(1, QColor(255, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(c, self.SIZE / 2, self.SIZE / 2)
        p.setBrush(QColor(255, 230, 230))
        p.drawEllipse(c, 2.5, 2.5)
        p.end()

    def stop(self):
        self.timer.stop()
        self.close()
