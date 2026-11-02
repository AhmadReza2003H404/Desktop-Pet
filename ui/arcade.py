"""Dot Dash: an arcade mini-game played along the bottom of your screen.

A trail of glowing dots appears and every pet races to gobble them up. Power
dots give a burst of speed, and a bonus star sometimes drops in. Most points
when the clock runs out wins. Clicks pass straight through the game."""

from __future__ import annotations

import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from core.paths import LINUX
from render.pixel import glow

BAND = 120          # px tall strip along the bottom of the screen
DOT_Y = 30          # px above the floor
SPACING = 46
ROUND_SECONDS = 60
READY_SECONDS = 2.0
POINTS = {"dot": 10, "power": 50, "star": 150}
DOT = QColor(255, 236, 140)
POWER = QColor(255, 120, 220)
STAR = QColor(255, 210, 60)
HUD_BG = QColor(18, 16, 40, 215)
HUD_FG = QColor(255, 236, 140)


@dataclass
class Dot:
    x: float          # screen x of its centre
    kind: str = "dot"
    born: float = 0.0  # stars blink away after a while


class DotDash(QWidget):
    def __init__(self, area: QRect, on_finish: Callable[[dict[int, tuple[str, int]]], None]):
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
        self.area = QRect(area)
        self.setGeometry(area.left(), area.bottom() + 1 - BAND, area.width(), BAND)
        self.on_finish = on_finish
        self.start = time.monotonic()
        self.wave = 0
        self.dots: list[Dot] = []
        self.scores: dict[int, tuple[str, int]] = {}  # id(pet window) -> (name, points)
        self.pops: list[list] = []  # x, age, text: floating "+10"s
        self.next_star = random.uniform(10, 20)
        self.wave_in = 0.0  # pause before the next wave appears
        self.finished = False
        self.hud_font = QFont("Monospace", 1, QFont.Black)
        self.hud_font.setStyleHint(QFont.Monospace)
        self.hud_font.setPixelSize(15)
        self.big_font = QFont("Monospace", 1, QFont.Black)
        self.big_font.setStyleHint(QFont.Monospace)
        self.big_font.setPixelSize(30)
        self._new_wave()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        self.timer.start(33)

    # --- the game ------------------------------------------------------------

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start

    @property
    def running(self) -> bool:
        return not self.finished and self.elapsed >= READY_SECONDS

    @property
    def time_left(self) -> float:
        return max(0.0, ROUND_SECONDS + READY_SECONDS - self.elapsed)

    def _new_wave(self):
        self.wave += 1
        left, right = self.area.left() + 40, self.area.right() - 40
        count = max(4, int((right - left) / SPACING))
        powers = set(random.sample(range(count), min(count, 3, 1 + self.wave // 2)))
        self.dots = [Dot(left + i * (right - left) / max(1, count - 1), "power" if i in powers else "dot")
                     for i in range(count)]

    def nearest(self, x: float) -> float | None:
        if not self.running or not self.dots:
            return None
        # stars are worth a detour
        return min(self.dots, key=lambda d: abs(d.x - x) * (0.4 if d.kind == "star" else 1.0)).x

    def eat(self, key: int, name: str, left: float, right: float) -> list[str]:
        """A pet's mouth spans left..right (screen x). Eats any dots there; returns their kinds."""
        if not self.running:
            return []
        eaten = [d for d in self.dots if left <= d.x <= right]
        if not eaten:
            return []
        self.dots = [d for d in self.dots if d not in eaten]
        points = sum(POINTS[d.kind] for d in eaten)
        _, total = self.scores.get(key, (name, 0))
        self.scores[key] = (name, total + points)
        for d in eaten:
            self.pops.append([d.x - self.area.left(), 0.0, f"+{POINTS[d.kind]}"])
        if not any(d.kind != "star" for d in self.dots):
            self.wave_in = 1.5
        return [d.kind for d in eaten]

    def _step(self):
        dt = 0.033
        if not self.finished and self.time_left <= 0:
            self.finished = True
            self.finish_at = time.monotonic() + 2.5
        if self.finished and time.monotonic() > getattr(self, "finish_at", 0):
            self.stop()
            self.on_finish(self.scores)
            return
        if self.running and self.wave_in > 0:
            self.wave_in -= dt
            if self.wave_in <= 0:
                self._new_wave()
        if self.running:
            self.next_star -= dt
            if self.next_star <= 0:
                self.next_star = random.uniform(12, 22)
                x = random.uniform(self.area.left() + 60, self.area.right() - 60)
                self.dots.append(Dot(x, "star", self.elapsed))
            self.dots = [d for d in self.dots if d.kind != "star" or self.elapsed - d.born < 8]
        for pop in self.pops:
            pop[1] += dt
        self.pops = [p for p in self.pops if p[1] < 1.0]
        if LINUX and int(self.elapsed * 30) % 15 == 0:  # stay over other apps; pets raise themselves above us
            self.raise_()
        self.update()

    def stop(self):
        self.timer.stop()
        self.close()

    # --- drawing -------------------------------------------------------------

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self.elapsed
        y = BAND - DOT_Y
        for d in self.dots:
            x = d.x - self.area.left()
            if d.kind == "dot":
                glow(p, QPointF(x, y), 11, QColor(255, 236, 140, 120))
                p.setPen(Qt.NoPen)
                p.setBrush(DOT)
                p.drawRect(QRectF(x - 4, y - 4, 8, 8))
            elif d.kind == "power":
                pulse = 1 + 0.25 * math.sin(t * 8 + d.x)
                glow(p, QPointF(x, y), 20 * pulse, QColor(255, 120, 220, 170))
                p.setPen(Qt.NoPen)
                p.setBrush(POWER)
                p.drawRect(QRectF(x - 8, y - 8, 16, 16))
                p.setBrush(QColor(255, 255, 255, 200))
                p.drawRect(QRectF(x - 5, y - 5, 4, 4))
            else:
                age = t - d.born
                if age > 6 and int(age * 8) % 2:
                    continue  # blinking away
                glow(p, QPointF(x, y - 6), 26, QColor(255, 220, 80, 170))
                self._star(p, QPointF(x, y - 6 + math.sin(t * 5) * 3), 13, t)

        p.setFont(self.hud_font)
        for x, age, text in self.pops:
            p.setOpacity(1 - age)
            p.setPen(QColor(40, 30, 10))
            p.drawText(QPointF(x - 13, y - 22 - age * 40), text)
            p.setPen(HUD_FG)
            p.drawText(QPointF(x - 14, y - 23 - age * 40), text)
        p.setOpacity(1.0)
        self._hud(p)

        if t < READY_SECONDS or self.finished or self.wave_in > 0:
            if self.finished:
                word = "GAME OVER"
            elif self.wave_in > 0:
                word = f"WAVE {self.wave + 1}!"
            else:
                word = "READY?" if t < READY_SECONDS * 0.6 else "GO!"
            p.setFont(self.big_font)
            box = QRectF(0, 36, self.width(), 40)
            p.setPen(QColor(30, 20, 60))
            p.drawText(box.translated(3, 3), Qt.AlignCenter, word)
            p.setPen(HUD_FG if not self.finished else POWER)
            p.drawText(box, Qt.AlignCenter, word)
        p.end()

    def _star(self, p: QPainter, c: QPointF, r: float, t: float):
        path = QPainterPath()
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5 + math.sin(t * 3) * 0.2
            rr = r if k % 2 == 0 else r * 0.45
            point = c + QPointF(math.cos(a) * rr, math.sin(a) * rr)
            if k == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        p.setPen(QColor(150, 90, 0))
        p.setBrush(STAR)
        p.drawPath(path)

    def _hud(self, p: QPainter):
        ranked = sorted(self.scores.values(), key=lambda s: -s[1])[:4]
        parts = [f"DOT DASH  WAVE {self.wave}  ⏱ {math.ceil(self.time_left):02d}"]
        parts += [f"{'👑' if i == 0 else '  '}{name[:10]} {score}" for i, (name, score) in enumerate(ranked)]
        text = "   ".join(parts)
        p.setFont(self.hud_font)
        width = p.fontMetrics().horizontalAdvance(text) + 24
        box = QRectF(10, 4, min(width, self.width() - 20), 26)
        p.setPen(Qt.NoPen)
        p.setBrush(HUD_BG)
        p.drawRoundedRect(box, 6, 6)
        p.setPen(HUD_FG)
        p.drawText(box.adjusted(12, 0, -12, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
