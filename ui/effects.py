"""Hearts and speech bubbles, in a click-through window that hovers above a pet."""

import math
import random

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from render import rig
from render.food import draw_food

HEART_LIFE = 1.4
HEART = QColor(255, 85, 125)
CONFETTI_LIFE = 1.6
CONFETTI = [QColor(255, 90, 120), QColor(255, 200, 60), QColor(90, 180, 255), QColor(120, 220, 130),
            QColor(190, 120, 255)]


class Effects(QWidget):
    W, H = 300, 220

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
        self.notes: list[list] = []           # x, y, age, drift, symbol, colour
        self.craving: str | None = None       # food shown in a thought bubble while begging
        self.craving_left = 0.0
        self.cloud_left = 0.0                 # little rain cloud while sulking
        self.drops: list[list[float]] = []    # x, y
        self.age = 0.0
        self.bubble: str | None = None
        self.bubble_left = 0.0
        self.bubble_important = False
        self.font = QFont("Sans", 1, QFont.Bold)
        self.font.setPixelSize(13)
        self.note_font = QFont("Sans", 1, QFont.Bold)
        self.note_font.setPixelSize(18)

    @property
    def busy(self) -> bool:
        return bool(self.hearts or self.bubble or self.confetti or self.notes or self.craving or self.cloud_left > 0)

    def heart(self, count: int = 1):
        for _ in range(count):
            self.hearts.append([self.W / 2 + random.uniform(-22, 22), self.H - 8,
                                -random.uniform(0, 0.35), random.uniform(-1, 1)])

    def music(self, count: int = 1, symbols: str = "♪♫♬"):
        """Floating music notes (or any little symbols, like ✦ sparkles)."""
        for _ in range(count):
            self.notes.append([self.W / 2 + random.uniform(-30, 30), self.H - 14, -random.uniform(0, 0.5),
                               random.uniform(-1, 1), random.choice(symbols), random.choice(CONFETTI)])

    def think_of(self, food: str, seconds: float = 4.5):
        """A thought bubble with the food it's dreaming about."""
        self.craving, self.craving_left = food, seconds

    def rain_cloud(self, seconds: float = 7.0):
        self.cloud_left = seconds

    def cheer_up(self):
        """Petted or fed: the gloom and cravings vanish."""
        self.craving, self.craving_left, self.cloud_left = None, 0.0, 0.0
        self.drops.clear()

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
        self.age += dt
        if self.craving:
            self.craving_left -= dt
            if self.craving_left <= 0:
                self.craving = None
        self.cloud_left = max(0.0, self.cloud_left - dt)
        if self.cloud_left > 0 and random.random() < dt * 14:
            self.drops.append([self.W / 2 + random.uniform(-20, 20), self.H - 52])
        for d in self.drops:
            d[1] += 140 * dt
        self.drops = [d for d in self.drops if d[1] < self.H]
        for h in self.hearts:
            h[2] += dt
            if h[2] > 0:
                h[1] -= 55 * dt
                h[0] += math.sin(h[2] * 6 + h[3] * 3) * 20 * dt + h[3] * 8 * dt
        self.hearts = [h for h in self.hearts if h[2] < HEART_LIFE]
        for n in self.notes:
            n[2] += dt
            if n[2] > 0:
                n[1] -= 45 * dt
                n[0] += math.sin(n[2] * 5 + n[3] * 3) * 30 * dt
        self.notes = [n for n in self.notes if n[2] < HEART_LIFE * 1.3]
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
        for x, y, age, _, symbol, colour in self.notes:
            if age < 0:
                continue
            p.setOpacity(max(0.0, min(1.0, (HEART_LIFE * 1.3 - age) * 2)))
            p.setFont(self.note_font)
            p.setPen(colour.darker(115))
            p.drawText(QPointF(x - 7, y), symbol)
        p.setOpacity(1.0)
        if self.cloud_left > 0 or self.drops:
            self._draw_cloud(p)
        if self.craving:
            self._draw_thought(p)
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

    def _draw_cloud(self, p: QPainter):
        p.setPen(rig.outline_pen(1.4, QColor(70, 120, 200)))
        p.setBrush(QColor(140, 190, 250))
        for x, y in self.drops:
            p.drawEllipse(QPointF(x, y), 2.2, 3.2)
        if self.cloud_left <= 0:
            return
        p.setOpacity(min(1.0, self.cloud_left * 2, self.age))
        c = QPointF(self.W / 2 + math.sin(self.age * 1.5) * 4, self.H - 62)
        cloud = QPainterPath()
        for dx, dy, r in ((-16, 4, 11), (-4, -4, 14), (12, 0, 12), (22, 6, 8), (0, 8, 10), (-24, 8, 7)):
            cloud = cloud.united(rig.ellipse_path(c + QPointF(dx, dy), r, r))
        rig.fill_part(p, cloud, QColor(150, 155, 170))
        p.setOpacity(1.0)

    def _draw_thought(self, p: QPainter):
        alpha = min(1.0, self.craving_left * 2)
        p.setOpacity(alpha)
        c = QPointF(self.W / 2 + 62, self.H - 70 + math.sin(self.age * 2.5) * 3)
        p.setPen(rig.outline_pen(2.0))
        p.setBrush(QColor(255, 255, 255, 245))
        for k, r in enumerate((3.5, 5.5)):  # little bubbles leading up to the thought
            p.drawEllipse(QPointF(self.W / 2 + 22 + k * 12, self.H - 34 - k * 11), r, r)
        cloud = QPainterPath()
        for dx, dy, r in ((-14, 0, 17), (12, -2, 18), (0, -10, 16), (0, 10, 15)):
            cloud = cloud.united(rig.ellipse_path(c + QPointF(dx, dy), r, r))
        p.drawPath(cloud)
        p.save()
        p.translate(c.x() - 22, c.y() - 20)
        p.scale(0.78, 0.78)
        draw_food(p, self.craving, QRectF(0, 0, 58, 46), 0)
        p.restore()
        p.setOpacity(1.0)

    def _draw_bubble(self, p: QPainter):
        metrics = QFontMetricsF(self.font)
        # long lines wrap onto a second line instead of running off the bubble
        text = metrics.boundingRect(QRectF(0, 0, self.W - 30, 200), Qt.TextWordWrap, self.bubble)
        box = QRectF(0, 0, text.width() + 20, text.height() + 12)
        box.moveBottom(self.H - (112 if self.craving or self.cloud_left > 0 else 45))  # above any cloud
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
