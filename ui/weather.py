"""Weather: snow, rain, autumn leaves, cherry blossoms or fireflies drifting over your desktop.

One transparent, click-through window covers the screen. "Auto" picks the
weather from the season."""

from __future__ import annotations

import datetime
import math
import random
import time

from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from core.paths import LINUX
from render.pixel import glow

KINDS = {
    "off": "Off",
    "auto": "Auto (by season)",
    "snow": "❄ Snow",
    "rain": "🌧 Rain",
    "leaves": "🍂 Autumn leaves",
    "petals": "🌸 Cherry blossoms",
    "fireflies": "✨ Fireflies",
}
COUNTS = {"snow": 110, "rain": 160, "leaves": 40, "petals": 50, "fireflies": 36}
LEAF_COLOURS = [QColor(230, 120, 40), QColor(200, 70, 40), QColor(240, 180, 50), QColor(170, 90, 40)]
PETAL_COLOURS = [QColor(255, 190, 210), QColor(255, 215, 228), QColor(250, 170, 200)]


def seasonal(today: datetime.date | None = None) -> str:
    month = (today or datetime.date.today()).month
    if month in (12, 1, 2):
        return "snow"
    if month in (3, 4, 5):
        return "petals"
    if month in (9, 10, 11):
        return "leaves"
    return "fireflies"


def resolve(kind: str, today: datetime.date | None = None) -> str:
    return seasonal(today) if kind == "auto" else kind


class Weather(QWidget):
    def __init__(self, kind: str):
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
        self.kind = resolve(kind)
        self.area: QRect = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(self.area)
        self.start = time.monotonic()
        self.last = self.start
        self.parts: list[list[float]] = [self._spawn(anywhere=True) for _ in range(COUNTS.get(self.kind, 0))]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(33)

    def _spawn(self, anywhere: bool = False) -> list[float]:
        """x, y, speed, size, phase, colour index."""
        w, h = self.area.width(), self.area.height()
        y = random.uniform(0, h) if anywhere else random.uniform(-60, -10)
        kind = self.kind
        if kind == "rain":
            return [random.uniform(-100, w), y, random.uniform(700, 1000), random.uniform(10, 20), 0, 0]
        if kind == "fireflies":
            return [random.uniform(0, w), random.uniform(h * 0.35, h), random.uniform(10, 30),
                    random.uniform(2, 4), random.uniform(0, 6.28), 0]
        speed = {"snow": (35, 90), "leaves": (50, 110), "petals": (40, 80)}[kind]
        size = {"snow": (2, 5), "leaves": (7, 12), "petals": (5, 8)}[kind]
        return [random.uniform(0, w), y, random.uniform(*speed), random.uniform(*size), random.uniform(0, 6.28),
                random.randrange(4)]

    def _step(self):
        now = time.monotonic()
        dt = min(0.05, now - self.last)
        self.last = now
        t = now - self.start
        h = self.area.height()
        for i, q in enumerate(self.parts):
            if self.kind == "rain":
                q[0] += q[2] * 0.18 * dt
                q[1] += q[2] * dt
            elif self.kind == "fireflies":
                q[0] += math.sin(t * 0.7 + q[4]) * q[2] * dt
                q[1] += math.cos(t * 0.5 + q[4] * 1.3) * q[2] * dt
                continue
            else:
                q[1] += q[2] * dt
                q[0] += math.sin(t * 1.3 + q[4]) * 25 * dt + (12 if self.kind != "snow" else 0) * dt
            if q[1] > h + 20:
                self.parts[i] = self._spawn()
        if LINUX and int(t * 30) % 15 == 0:
            self.raise_()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = time.monotonic() - self.start
        kind = self.kind
        if kind == "rain":
            p.setPen(QPen(QColor(170, 200, 255, 150), 1.6, Qt.SolidLine, Qt.RoundCap))
            for x, y, speed, length, _, _ in self.parts:
                p.drawLine(QPointF(x, y), QPointF(x - length * 0.18, y - length))
        elif kind == "snow":
            p.setPen(Qt.NoPen)
            for x, y, _, size, _, _ in self.parts:
                p.setBrush(QColor(255, 255, 255, 215))
                p.drawEllipse(QPointF(x, y), size, size)
        elif kind == "fireflies":
            for x, y, _, size, phase, _ in self.parts:
                blink = 0.5 + 0.5 * math.sin(t * 2.2 + phase * 3)
                glow(p, QPointF(x, y), size * 4, QColor(220, 255, 120, int(40 + 160 * blink)))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(250, 255, 200, int(80 + 175 * blink)))
                p.drawEllipse(QPointF(x, y), size * 0.6, size * 0.6)
        else:
            colours = LEAF_COLOURS if kind == "leaves" else PETAL_COLOURS
            for x, y, _, size, phase, ci in self.parts:
                p.save()
                p.translate(x, y)
                p.rotate(math.degrees(t * 1.5 + phase) % 360)
                p.scale(1, 0.55 + 0.45 * math.sin(t * 3 + phase))  # tumbling
                shape = QPainterPath(QPointF(-size, 0))
                shape.quadTo(0, -size * 0.8, size, 0)
                shape.quadTo(0, size * 0.8, -size, 0)
                p.setPen(Qt.NoPen)
                p.setBrush(colours[int(ci) % len(colours)])
                p.drawPath(shape)
                p.restore()
        p.end()

    def stop(self):
        self.timer.stop()
        self.close()
