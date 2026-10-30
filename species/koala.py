"""Koalas: giant fluffy ears, a nose like a jellybean, asleep 80% of the time."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from core.pet import PetView, State
from render import rig
from render.quadruped import Quadruped

FLUFF = QColor(250, 248, 245)

PALETTES = {
    "gray": {"base": QColor(162, 165, 175), "nose": QColor(48, 44, 52)},
    "silver": {"base": QColor(198, 201, 208), "nose": QColor(60, 56, 64)},
    "chocolate": {"base": QColor(140, 112, 96), "nose": QColor(45, 34, 34)},
}


class Koala(Quadruped):
    species = "koala"
    name = "Koala"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 32.0
    body_rx, body_ry = 30.0, 20.0
    leg_len = 8.0
    leg_w = 12.0
    head_r = 28.0
    head_shape = (1.12, 0.95)
    tail_kind = "stub"
    nose_kind = "koala"
    idle_weights = {State.WALK: 2, State.IDLE: 2, State.SIT: 2, State.SLEEP: 5}
    durations = {
        State.IDLE: (2.0, 5.0),
        State.SIT: (6.0, 15.0),
        State.SLEEP: (40.0, 90.0),  # koalas sleep up to 20 hours a day
    }
    specials = ["cling"]
    special_weight = 2.0
    voice = "squeak"
    favorite_food = "eucalyptus"
    default_names = ["Gumnut", "Kiki", "Snoozles", "Euca", "Fuzzy", "Nap Lord", "Blinky"]
    lines = {
        "pet": ["*sleepy happy*", "mmm, cozy", "you're like a tree but warmer"],
        "hungry": ["eucalyptus pls", "leaf o'clock", "*chews air*"],
        "fed": ["leaves!!", "munch... munch...", "now I need a nap"],
        "thrown": ["NOT THE FACE", "AAAA I'M AWAKE", "too fast!!"],
        "ouch": ["...", "I'll just lie here now"],
        "woke": ["it is not time.", "I sleep 20 hours a day for a REASON"],
        "tired": ["so... sleepy...", "*nods off mid-sentence*"],
        "sad": ["I need a hug (or a tree)"],
        "idle": ["...", "*blinks slowly*", "is that a tree?", "zZz... huh?", "I'm awake. mostly."],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        for side in (-1, 1):
            centre = c + QPointF(side * r * 0.92, -r * 0.48)
            ear = rig.ellipse_path(centre, r * 0.44, r * 0.42)
            for k in range(5):  # fluffy scalloped edge on the outside
                a = math.radians(-120 + k * 50) if side > 0 else math.radians(-60 - k * 50)
                tuft = centre + QPointF(math.cos(a) * r * 0.42, math.sin(a) * r * 0.4)
                ear = ear.united(rig.ellipse_path(tuft, r * 0.1, r * 0.1))
            rig.fill_part(p, ear, self.color("ear"))
            inner = QPainterPath()
            inner.addEllipse(centre + QPointF(side * r * 0.04, r * 0.02), r * 0.27, r * 0.26)
            p.setPen(Qt.NoPen)
            p.setBrush(FLUFF)
            p.drawPath(inner)

    def markings(self, part: str):
        def belly(p: QPainter, r: QRectF):
            p.setPen(Qt.NoPen)
            p.setBrush(FLUFF)
            if part == "body":
                p.drawEllipse(QPointF(r.center().x() + r.width() * 0.1, r.bottom()), r.width() * 0.35, r.height() * 0.4)
            elif part == "chest":
                p.drawEllipse(QPointF(r.center().x() + r.width() * 0.12, r.center().y() + r.height() * 0.08),
                              r.width() * 0.3, r.height() * 0.4)
            elif part == "head":  # fluffy white chin
                p.drawEllipse(QPointF(r.center().x() + r.width() * 0.07, r.bottom()), r.width() * 0.2, r.height() * 0.12)
        return belly
