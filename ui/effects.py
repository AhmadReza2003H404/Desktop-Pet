"""Hearts and speech bubbles, in a click-through window that hovers above a pet."""

import math
import random

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from render import rig

HEART_LIFE = 1.4
HEART = QColor(255, 85, 125)
CONFETTI_LIFE = 1.6
CONFETTI = [QColor(255, 90, 120), QColor(255, 200, 60), QColor(90, 180, 255), QColor(120, 220, 130),
            QColor(190, 120, 255)]


class Effects(QWidget):
    W, H = 300, 160

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.X11BypassWindowManagerHint
            | Qt.WindowTransparentForInput,  # clicks go straight through
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(self.W, self.H)
        self.hearts: list[list[float]] = []  # x, y, age, drift
        self.confetti: list[list] = []        # x, y, vx, vy, age, spin, colour
        self.bubble: str | None = None
        self.bubble_left = 0.0
        self.bubble_important = False
        self.font = QFont("Sans", 1, QFont.Bold)
        self.font.setPixelSize(13)

    @property
    def busy(self) -> bool:
        return bool(self.hearts or self.bubble or self.confetti)

    def heart(self, count: int = 1):
        for _ in range(count):
            self.hearts.append([self.W / 2 + random.uniform(-22, 22), self.H - 8,
                                -random.uniform(0, 0.35), random.uniform(-1, 1)])

    def celebrate(self, pieces: int = 40):
        for _ in range(pieces):
            self.confetti.append([self.W / 2, self.H - 20, random.uniform(-160, 160), random.uniform(-380, -180),
                                  0.0, random.uniform(0, 360), random.choice(CONFETTI)])

    def say(self, text: str, seconds: float = 3.0, important: bool = False):
        """Important bubbles (level-ups, reminders) can't be talked over by chit-chat."""
        if self.bubble and self.bubble_important and not important:
            return
        self.bubble, self.bubble_left, self.bubble_important = text, seconds, important

    def place(self, pet: QRect):
        """The bottom-centre of this window sits on the pet's head."""
        self.move(pet.center().x() - self.W // 2, pet.top() + int(pet.height() * 0.2) - self.H + 8)

    def step(self, dt: float):
        for h in self.hearts:
            h[2] += dt
            if h[2] > 0:
                h[1] -= 55 * dt
                h[0] += math.sin(h[2] * 6 + h[3] * 3) * 20 * dt + h[3] * 8 * dt
        self.hearts = [h for h in self.hearts if h[2] < HEART_LIFE]
        for c in self.confetti:
            c[3] += 520 * dt  # gravity
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[4] += dt
            c[5] += c[2] * dt * 4
        self.confetti = [c for c in self.confetti if c[4] < CONFETTI_LIFE and c[1] < self.H]
        if self.bubble:
            self.bubble_left -= dt
            if self.bubble_left <= 0:
                self.bubble = None

    def paintEvent(self, _):
        if not self.busy:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for x, y, _, _, age, spin, colour in self.confetti:
            p.save()
            p.translate(x, y)
            p.rotate(spin)
            p.setOpacity(min(1.0, (CONFETTI_LIFE - age) * 2))
            p.fillRect(QRectF(-3, -1.8, 6, 3.6), colour)
            p.restore()
        p.setOpacity(1.0)
        if self.bubble:
            self._draw_bubble(p)
        for x, y, age, _ in self.hearts:
            if age < 0:
                continue
            fade = 1 - age / HEART_LIFE
            color = QColor(HEART)
            color.setAlphaF(min(1.0, fade * 1.8))
            size = 14 + 6 * min(1.0, age * 5)  # pops in
            p.setPen(rig.outline_pen(1.6, QColor(150, 30, 60, color.alpha())))
            p.setBrush(color)
            p.drawPath(rig.heart_path(QPointF(x, y), size))
        p.end()

    def _draw_bubble(self, p: QPainter):
        metrics = QFontMetricsF(self.font)
        # long lines wrap onto a second line instead of running off the bubble
        text = metrics.boundingRect(QRectF(0, 0, self.W - 30, 200), Qt.TextWordWrap, self.bubble)
        box = QRectF(0, 0, text.width() + 20, text.height() + 12)
        box.moveBottom(self.H - 45)
        box.moveLeft(self.W / 2 + 18 - box.width() / 2)
        box.moveLeft(max(2.0, min(self.W - box.width() - 2, box.left())))

        shape = QPainterPath()
        shape.addRoundedRect(box, 10, 10)
        tail = QPainterPath(QPointF(self.W / 2 + 4, box.bottom() - 2))
        tail.lineTo(self.W / 2 - 4, box.bottom() + 12)
        tail.lineTo(self.W / 2 + 14, box.bottom() - 2)
        shape = shape.united(tail)

        alpha = min(1.0, self.bubble_left * 3)  # fade out at the end
        p.setOpacity(alpha)
        p.setPen(rig.outline_pen(2.2))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawPath(shape)
        p.setFont(self.font)
        p.setPen(rig.OUTLINE)
        p.drawText(box, Qt.AlignCenter | Qt.TextWordWrap, self.bubble)
        p.setOpacity(1.0)
