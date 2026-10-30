"""A bouncy ball. Pets chase and kick it; you can grab and throw it too."""

import random
import time
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QMenu, QWidget

from core.paths import LINUX
from core.physics import Body
from render import rig

LIFETIME = 60.0  # seconds before the ball poofs away
RED = QColor(235, 70, 80)


class Ball(QWidget):
    SIZE = 30

    def __init__(self, x: float, y: float, on_remove: Callable[[], None]):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.X11BypassWindowManagerHint,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.OpenHandCursor)
        self.body = Body(x=x, y=y, w=self.SIZE, h=self.SIZE, bounce=0.72, min_bounce=140, friction=0.6)
        self.angle = 0.0
        self.life = LIFETIME
        self.alive = True
        self.dragging = False
        self.trail: list[tuple[float, QPointF]] = []
        self.grab = QPointF()
        self.on_remove = on_remove
        self.setToolTip("Drag to throw · double-click or right-click to put away")

    @property
    def center_x(self) -> float:
        return self.body.x + self.SIZE / 2

    def low(self, area: QRect) -> bool:
        """Close enough to the floor for a pet to kick."""
        return not self.dragging and self.body.y >= self.body.floor(area) - 25

    def throw(self, vx: float, vy: float):
        self.body.vx, self.body.vy = vx, vy
        self.life = LIFETIME

    def kick(self, direction: int):
        self.throw(direction * random.uniform(450, 850), -random.uniform(350, 700))

    def step(self, dt: float, area: QRect):
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return
        if not self.dragging:
            self.body.step(dt, area)
            self.angle += self.body.vx * dt * 3
            self.move(round(self.body.x), round(self.body.y))
        if LINUX:  # X11 bypass windows need a nudge; Windows keeps "on top" windows on top
            self.raise_()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(min(1.0, self.life))  # fades out in its last second
        r = self.SIZE / 2 - 2
        c = QPointF(self.SIZE / 2, self.SIZE / 2)
        p.translate(c)
        p.rotate(self.angle)
        ball = rig.ellipse_path(QPointF(0, 0), r, r)

        def stripe(painter: QPainter, rect: QRectF):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 220, 90))
            band = QPainterPath()
            band.addRect(QRectF(-r, -r * 0.25, r * 2, r * 0.5))
            painter.drawPath(band)
        rig.fill_part(p, ball, RED, stripe)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 140))
        p.drawEllipse(QPointF(-r * 0.35, -r * 0.4), r * 0.25, r * 0.18)
        p.end()

    # grab and throw it yourself

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            menu = QMenu()
            menu.addAction("Put the ball away", self.on_remove)
            menu.exec(e.globalPosition().toPoint())
        elif e.button() == Qt.LeftButton:
            self.dragging = True
            self.grab = e.position()
            self.trail = [(time.monotonic(), e.globalPosition())]
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if not self.dragging:
            return
        now, pos = time.monotonic(), e.globalPosition()
        self.trail = [(t, p) for t, p in self.trail if now - t <= 0.08] + [(now, pos)]
        self.body.x, self.body.y = pos.x() - self.grab.x(), pos.y() - self.grab.y()
        self.move(round(self.body.x), round(self.body.y))

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.dragging = False
            self.on_remove()

    def mouseReleaseEvent(self, e):
        if not self.dragging:
            return
        self.dragging = False
        (t0, p0), (t1, p1) = self.trail[0], self.trail[-1]
        span = max(t1 - t0, 1e-3)
        self.throw((p1.x() - p0.x()) / span, (p1.y() - p0.y()) / span)
        self.setCursor(Qt.OpenHandCursor)
