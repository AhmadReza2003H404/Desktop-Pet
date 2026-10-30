"""A food bowl that drops from the top of the screen and waits to be eaten."""

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from core.paths import LINUX
from core.physics import Body
from render.food import draw_food


class Food(QWidget):
    W, H = 58, 46

    def __init__(self, kind: str, x: float, area: QRect):
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
        self.setFixedSize(self.W, self.H)
        self.kind = kind
        self.bites = 0
        self.body = Body(x=x, y=area.top(), w=self.W, h=self.H)
        self.landed = False
        self.move(round(self.body.x), round(self.body.y))

    @property
    def center_x(self) -> float:
        return self.body.x + self.W / 2

    def step(self, dt: float, area: QRect):
        if not self.landed:
            self.body.step(dt, area)
            self.landed = self.body.on_ground(area) and self.body.vy == 0
            self.move(round(self.body.x), round(self.body.y))
        if LINUX:  # X11 bypass windows need a nudge; Windows keeps "on top" windows on top
            self.raise_()

    def set_bites(self, bites: int):
        if bites != self.bites:
            self.bites = bites
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        draw_food(p, self.kind, QRectF(0, 0, self.W, self.H), self.bites)
        p.end()
