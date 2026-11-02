"""Retro pixel-art pets: drawn from little text grids instead of curves.

A PixelPet describes its sprite as rows of characters. Each character is a
palette key (see INK), "." is transparent. Eyes and mouths are drawn on top
so they can follow the cursor, blink and react, just like the cartoon pets.

To make a new pixel pet, subclass PixelPet, set `palettes`, `eyes` and
`mouth_at`, and return the rows to draw from frame(). Override decorate()
for extra bits such as glowing antennas or rocket flames.
"""

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QRadialGradient

from core.pet import Pet, PetView, State
from render import rig
from render.hats import draw_hat

DESIGN = 120
INK = {
    "O": "outline",
    "B": "base",
    "L": "light",
    "S": "shade",
    "P": "blush",
    "W": "white",
    "K": "screen",
    "A": "accent",
    "G": "glow",
}


def lighter(c: QColor, k: int = 135) -> QColor:
    return c.lighter(k)


def darker(c: QColor, k: int = 160) -> QColor:
    return c.darker(k)


def palette(base: QColor, **extra: QColor) -> dict[str, QColor]:
    """A full palette worked out from one base colour."""
    pal = {
        "base": base,
        "light": lighter(base, 128),
        "shade": darker(base, 125),
        "outline": darker(base, 330),
        "blush": QColor(255, 120, 150),
        "white": QColor(255, 255, 255),
        "pupil": QColor(30, 30, 60),
    }
    pal.update(extra)
    return pal


@dataclass
class EyeBox:
    col: int    # top-left cell of the eye
    row: int
    w: int = 2
    h: int = 3


class PixelPet(Pet):
    palettes: dict[str, dict[str, QColor]] = {}
    px: float = 5.0          # size of one sprite pixel, in design units
    hover: float = 0.0       # floats this far above the ground (ghosts)
    bob: float = 0.0         # how much it bobs up and down while floating
    eyes: list[EyeBox] = []
    sclera = True            # white eyes with pupils; False = glowing pupils only (screen faces)
    pupil_w, pupil_h = 1, 2
    mouth_at: tuple[int, int] = (0, 0)   # cell where the mouth's left corner goes
    shadow = True

    def __init__(self, variant: str | None = None, scale: float = 1.0):
        super().__init__(variant, scale)
        self.pal = self.palettes[self.variant]

    # --- hooks ---------------------------------------------------------------

    def frame(self, v: PetView) -> list[str]:
        """The sprite rows for this moment."""
        raise NotImplementedError

    def lift(self, v: PetView) -> float:
        """Extra height off the ground this frame (hops, bobbing)."""
        if self.hover:
            return self.hover + math.sin(v.t * 2.6) * self.bob
        return 0.0

    def decorate(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        """Draw extras over the sprite. origin is the sprite's top-left corner."""

    def colour(self, key: str) -> QColor:
        return self.pal.get(key) or self.pal["base"]

    # --- frame ---------------------------------------------------------------

    def size_cells(self, rows: list[str]) -> tuple[int, int]:
        return max(len(r) for r in rows), len(rows)

    def draw(self, p: QPainter, v: PetView):
        s = self.width / DESIGN
        outer = p.transform()
        p.save()
        p.setRenderHint(QPainter.Antialiasing, False)
        p.translate(self.width / 2, self.height - 3 * s)
        p.scale(s, s)

        rows = self.frame(v)
        cols, nrows = self.size_cells(rows)
        px = self.px
        w, h = cols * px, nrows * px
        lift = self.lift(v)
        if v.state == State.SLEEP:
            lift *= 0.35  # ghosts sink low when they nap

        if self.shadow and v.state not in (State.DRAGGED, State.FALLING):
            self._shadow(p, w, lift)

        p.scale(1 + v.squash, 1 - v.squash)
        opacity = self._pose(p, v, h, lift)
        p.setOpacity(p.opacity() * opacity)
        p.scale(v.facing, 1)
        p.translate(0, -lift)

        origin = QPointF(-w / 2, -h)
        self._cells(p, rows, origin, px)
        self._face(p, v, origin, px)
        self.decorate(p, v, origin, px)

        head_r = w * 0.3
        head_c = QPointF(0, origin.y() + head_r * 0.85)
        eye_spots = [(origin + QPointF((e.col + e.w / 2) * px, (e.row + e.h / 2) * px), e.w * px * 0.6)
                     for e in self.eyes]
        p.setRenderHint(QPainter.Antialiasing)
        draw_hat(p, self.hat, head_c, head_r, eye_spots, v.t)
        anchor = outer.inverted()[0].map(p.transform().map(QPointF(w * 0.2, origin.y())))
        p.restore()

        if v.state == State.SLEEP:
            rig.zzz(p, anchor + QPointF(4 * s, 0), v.t, s)
        elif v.state == State.DRAGGED:
            rig.sweat_drop(p, anchor + QPointF(12 * s, 6 * s), 6 * s)

    def _shadow(self, p: QPainter, w: float, lift: float):
        k = max(0.35, 1 - lift / 60)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(45 * k)))
        p.drawEllipse(QPointF(0, -2), w * 0.36 * k, 4 * k)
        p.restore()

    def _pose(self, p: QPainter, v: PetView, h: float, lift: float) -> float:
        """Whole-body transforms for states and tricks. Returns opacity."""
        if v.state == State.DRAGGED:
            p.translate(0, -h * 0.5)
            p.rotate(math.sin(v.walk_phase * 0.6) * 14)
            p.translate(0, h * 0.5)
        elif v.state == State.HAPPY:
            p.translate(0, -abs(math.sin(v.t * 9)) * 5)
        elif v.state == State.EAT:
            p.rotate(6 + math.sin(v.t * 14) * 2)
        elif v.state == State.SPECIAL:
            name = v.special
            if name == "spin":
                p.rotate(math.sin(v.t * 24) * 10)
            elif name == "roll":
                p.translate(0, -h / 2 - lift)
                p.rotate(v.special_value)
                p.translate(0, h / 2 + lift)
            elif name == "crouch":
                p.scale(1.12, 0.78)
            elif name == "dance":
                p.translate(0, -abs(math.sin(v.t * 7)) * 8)
                p.rotate(math.sin(v.t * 7) * 12)
            elif name == "phase":
                return 1 - 0.75 * v.special_value
            elif name == "float":
                p.rotate(math.sin(v.t * 5) * 8)
            elif name == "slide":
                p.scale(1.2, 0.75)
            elif name in ("cling", "cling_sleep"):
                p.rotate(-12)
            elif name == "dazed":
                p.rotate(math.sin(v.t * 18) * 6)
        return 1.0

    def _cells(self, p: QPainter, rows: list[str], origin: QPointF, px: float):
        p.setPen(Qt.NoPen)
        pad = 0.35  # overlap neighbours a hair so scaling never shows seams
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                key = INK.get(ch)
                if key is None:
                    continue
                p.setBrush(self.colour(key))
                p.drawRect(QRectF(origin.x() + c * px, origin.y() + r * px, px + pad, px + pad))

    # --- face ----------------------------------------------------------------

    def _block(self, p: QPainter, origin: QPointF, px: float, col: float, row: float, w: float, h: float,
               color: QColor):
        p.setBrush(color)
        p.drawRect(QRectF(origin.x() + col * px, origin.y() + row * px, w * px + 0.35, h * px + 0.35))

    def _face(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        p.setPen(Qt.NoPen)
        ink = self.colour("pupil")
        look = (v.look[0] * v.facing, v.look[1])
        if v.state == State.SLEEP or v.special == "cling_sleep":
            eyes = "sleep"
        elif v.state == State.HAPPY:
            eyes = "happy"
        elif v.special in ("spin", "dazed", "roll"):
            eyes = "dizzy"
        elif v.blink:
            eyes = "blink"
        else:
            eyes = "open"

        for e in self.eyes:
            if eyes == "sleep" or eyes == "blink":
                self._block(p, origin, px, e.col, e.row + e.h - 1, e.w, 1, ink if self.sclera else self.colour("glow"))
            elif eyes == "happy":  # ^ ^
                c = self.colour("glow") if not self.sclera else ink
                self._block(p, origin, px, e.col, e.row + 1, 1, 1, c)
                self._block(p, origin, px, e.col + e.w - 1, e.row + 1, 1, 1, c)
                if e.w > 2:
                    self._block(p, origin, px, e.col + 1, e.row, e.w - 2, 1, c)
                else:
                    self._block(p, origin, px, e.col + 0.5, e.row + 0.4, 1, 0.8, c)
            elif eyes == "dizzy":
                c = self.colour("glow") if not self.sclera else ink
                if self.sclera:
                    self._block(p, origin, px, e.col, e.row, e.w, e.h, self.colour("white"))
                spin = int(v.t * 12) % 4
                dc, dr = [(0, 0), (1, 0), (1, 1), (0, 1)][spin]
                self._block(p, origin, px, e.col + min(dc, e.w - 1), e.row + min(dr, e.h - 1) + 0.5, 1, 1, c)
            else:
                if self.sclera:
                    self._block(p, origin, px, e.col, e.row, e.w, e.h, self.colour("white"))
                pw, ph = self.pupil_w, self.pupil_h
                # pupils jump a whole pixel at a time, like an old arcade sprite
                dc = round((look[0] + 1) / 2 * (e.w - pw))
                dr = round((look[1] + 1) / 2 * (e.h - ph))
                self._block(p, origin, px, e.col + dc, e.row + dr, pw, ph,
                            ink if self.sclera else self.colour("glow"))
                if v.mood == "tired":
                    self._block(p, origin, px, e.col, e.row, e.w, 1, self.colour("base"))
                elif v.mood in ("sad", "hungry"):
                    brow = self.colour("outline")
                    self._block(p, origin, px, e.col, e.row - 1 + 0.4, 1, 0.5, brow)
                    self._block(p, origin, px, e.col + e.w - 1, e.row - 1, 1, 0.5, brow)

        self._mouth(p, v, origin, px)

    def mouth_kind(self, v: PetView) -> str:
        if v.state == State.EAT:
            return "open" if math.sin(v.t * 14) > 0 else "flat"
        if v.state in (State.DRAGGED, State.FALLING) or v.special in ("rocket", "dazed"):
            return "open"
        if v.state == State.SLEEP:
            return "flat"
        if v.mood in ("sad", "hungry"):
            return "sad"
        return "smile"

    def _mouth(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        col, row = self.mouth_at
        ink = self.colour("pupil") if self.sclera else self.colour("glow")
        kind = self.mouth_kind(v)
        if kind == "smile":
            for dc, dr in ((0, 0), (1, 1), (2, 1), (3, 0)):
                self._block(p, origin, px, col + dc, row + dr, 1, 1, ink)
        elif kind == "sad":
            for dc, dr in ((0, 1), (1, 0), (2, 0), (3, 1)):
                self._block(p, origin, px, col + dc, row + dr, 1, 1, ink)
        elif kind == "open":
            self._block(p, origin, px, col + 1, row, 2, 2, ink)
            if self.sclera:
                self._block(p, origin, px, col + 1, row + 1.4, 2, 0.6, QColor(255, 130, 150))
        else:
            self._block(p, origin, px, col + 1, row + 1, 2, 1, ink)


def glow(p: QPainter, c: QPointF, radius: float, color: QColor):
    """A soft round glow, for antennas, power-ups and flames."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    g = QRadialGradient(c, radius)
    inner = QColor(color)
    g.setColorAt(0, inner)
    mid = QColor(color)
    mid.setAlpha(110)
    g.setColorAt(0.4, mid)
    edge = QColor(color)
    edge.setAlpha(0)
    g.setColorAt(1, edge)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(c, radius, radius)
    p.restore()
