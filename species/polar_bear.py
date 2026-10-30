"""Polar bears: big, fluffy, slightly confused about where the ice went."""

import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath

from core.pet import PetView, State
from render import rig
from render.quadruped import Quadruped

SCARF = QColor(220, 60, 70)
SCARF_STRIPE = QColor(250, 240, 230)

PALETTES = {
    "snow": {"base": QColor(250, 250, 246)},
    "cream": {"base": QColor(246, 236, 212)},
    "scarf": {"base": QColor(250, 250, 246), "scarf": True},
}


class PolarBear(Quadruped):
    species = "polar_bear"
    name = "Polar bear"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 50.0
    body_rx, body_ry = 40.0, 21.0
    leg_len = 11.0
    leg_w = 13.0
    head_r = 24.0
    head_shape = (1.0, 0.9)
    tail_kind = "stub"
    nose_kind = "bear"
    muzzle = (0.2, 0.3, 0.42, 0.27)
    idle_weights = {State.WALK: 4, State.IDLE: 3, State.SIT: 2, State.SLEEP: 2}
    specials = ["belly_slide", "roll"]
    voice = "grunt"
    favorite_food = "fish"
    default_names = ["Snowball", "Blizzard", "Frosty", "Igloo", "Marshmallow", "Polo", "Chill Bill"]
    lines = {
        "pet": ["*happy bear grumble*", "warm hands!", "hug accepted"],
        "hungry": ["fish? anyone?", "*belly growls like thunder*", "I could eat a whole iceberg"],
        "fed": ["fishy!!", "crunchy and cold, perfect"],
        "thrown": ["RAAAWR", "BEAR OVERBOARD", "whee!"],
        "ouch": ["the floor is not snow", "*thud*"],
        "woke": ["is it winter yet?", "I was hibernating!"],
        "tired": ["hibernation mode: soon"],
        "sad": ["it's cold and lonely here"],
        "idle": ["is it chilly in here or is it me?", "*sniffs for seals*", "I miss the ice", "brr... nope, I'm fine"],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        self.round_ears(p, c, r, size=0.26, spread=0.76, inner=QColor(215, 212, 215))
        if self.pal.get("scarf"):
            self._scarf(p, c, r, v)

    def _scarf(self, p: QPainter, c: QPointF, r: float, v: PetView):
        # loose end flaps behind; it flutters when walking or falling
        flutter = math.sin(v.t * (14 if v.state in (State.WALK, State.FALLING) else 2)) * 4
        end = QPainterPath(c + QPointF(-r * 0.5, r * 0.85))
        end.lineTo(c + QPointF(-r * 1.15, r * 1.25 + flutter))
        end.lineTo(c + QPointF(-r * 0.95, r * 1.45 + flutter))
        end.lineTo(c + QPointF(-r * 0.3, r * 1.05))
        end.closeSubpath()
        rig.fill_part(p, end, SCARF)
        band = rig.ellipse_path(c + QPointF(0, r * 0.88), r * 0.85, r * 0.25)

        def stripes(painter: QPainter, rect: QRectF):
            painter.setPen(rig.outline_pen(3, SCARF_STRIPE))
            for k in (0.3, 0.55, 0.8):
                x = rect.left() + rect.width() * k
                painter.drawLine(QPointF(x, rect.top()), QPointF(x - 4, rect.bottom()))
        rig.fill_part(p, band, SCARF, stripes)
