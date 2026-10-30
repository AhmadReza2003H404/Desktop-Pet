"""Goats: sideways pupils, a beard, and an opinion about everything."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

from core.pet import PetView, State
from render import rig
from render.quadruped import Quadruped

HORN = QColor(214, 198, 168)
HOOF = QColor(80, 70, 72)
EAR_INSIDE = QColor(255, 180, 190)

PALETTES = {
    "white": {"base": QColor(248, 246, 240), "beard": QColor(235, 230, 220)},
    "brown": {"base": QColor(172, 122, 82), "beard": QColor(240, 232, 220), "muzzle": QColor(240, 232, 220)},
    "spotted": {"base": QColor(248, 246, 240), "beard": QColor(235, 230, 220), "patch": QColor(150, 98, 64),
                "ear1": QColor(150, 98, 64)},
    "black": {"base": QColor(66, 62, 70), "beard": QColor(66, 62, 70), "muzzle": QColor(235, 230, 222)},
}

PATCHES = {
    "body": [(0.3, 0.35, 0.22), (0.72, 0.7, 0.15)],
    "chest": [(0.4, 0.55, 0.3)],
    "head": [(0.85, 0.2, 0.2)],
}


class Goat(Quadruped):
    species = "goat"
    name = "Goat"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 72.0
    body_rx, body_ry = 32.0, 17.0
    leg_len = 20.0
    leg_w = 8.0
    head_r = 23.0
    head_shape = (0.88, 1.05)
    tail_kind = "stub"
    nose_kind = "goat"
    muzzle = (0.16, 0.45, 0.34, 0.28)
    pupil = "bar"
    idle_weights = {State.WALK: 6, State.IDLE: 3, State.SIT: 2, State.SLEEP: 1}
    specials = ["pronk", "headbutt", "zoomies"]
    voice = "bleat"
    favorite_food = "hay"
    default_names = ["Gary", "Billy", "Chaos", "Pepper", "Clover", "Mr. Bleat", "Tin Can"]
    lines = {
        "pet": ["meh ♥", "acceptable petting", "*happy bleat*"],
        "hungry": ["I will eat your cables", "MEEEH (hungry)", "is that paper? can I eat it?"],
        "fed": ["HAY!", "crunch crunch", "tastes like a sock. 10/10"],
        "thrown": ["MEEEEEEEH", "GOAT AIRLINES", "YOLO"],
        "ouch": ["I'm fine. I'm a goat.", "headbutt the floor back"],
        "woke": ["MEH?!", "who dares"],
        "tired": ["*yawns like a scream*"],
        "sad": ["meh..."],
        "idle": ["MEEEH", "*screams for no reason*", "I ate your homework", "*headbutts nothing*",
                 "everything is food if you try"],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        # horns sweep backwards; the far one first, a bit darker
        for side in (-1, 1):
            root = c + QPointF(side * r * 0.28 - r * 0.02, -r * 0.82)
            tip = c + QPointF(side * r * 0.2 - r * 0.78, -r * 1.42)
            horn = QPainterPath(root)
            horn.cubicTo(root + QPointF(0, -r * 0.45), tip + QPointF(r * 0.38, -r * 0.12), tip)
            shape = rig.thick_line(horn, r * (0.2 if side > 0 else 0.18))

            def rings(painter: QPainter, rect: QRectF):
                painter.setPen(rig.outline_pen(1.2, HORN.darker(125)))
                for k in (0.3, 0.5, 0.7):
                    x = rect.left() + rect.width() * k
                    painter.drawLine(QPointF(x, rect.top()), QPointF(x + 4, rect.bottom()))
            rig.fill_part(p, shape, HORN, rings, 0 if side > 0 else 25)

        # ears stick out sideways and droop a little
        for i, side in enumerate((-1, 1)):
            flop = math.sin(v.walk_phase) * 6 if v.state == State.WALK else 0
            if v.state == State.DRAGGED:
                flop = math.sin(v.t * 20 + i) * 20
            p.save()
            p.translate(c + QPointF(side * r * 0.72, -r * 0.3))
            p.rotate(-side * 68 + flop)
            rig.fill_part(p, rig.ellipse_path(QPointF(0, r * 0.3), r * 0.17, r * 0.32), self.color("ear", i))
            p.setPen(Qt.NoPen)
            p.setBrush(EAR_INSIDE)
            p.drawEllipse(QPointF(0, r * 0.34), r * 0.08, r * 0.2)
            p.restore()

    def over_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        sway = math.sin(v.t * 2.5) * r * 0.04
        beard = QPainterPath(c + QPointF(r * 0.05, r * 0.95))
        beard.lineTo(c + QPointF(r * 0.4, r * 0.92))
        beard.quadTo(c + QPointF(r * 0.35, r * 1.2), c + QPointF(r * 0.24 + sway, r * 1.42))
        beard.quadTo(c + QPointF(r * 0.12, r * 1.15), c + QPointF(r * 0.05, r * 0.95))
        rig.fill_part(p, beard, self.pal["beard"])

    def idle_mouth(self, v: PetView) -> str:
        # every so often: the famous goat scream
        return "scream" if v.state == State.IDLE and 1.0 < v.state_time % 13 < 2.2 else "w"

    def markings(self, part: str):
        patch = self.pal.get("patch")

        def coat(p: QPainter, r: QRectF):
            p.setPen(Qt.NoPen)
            if patch is not None:
                p.setBrush(patch)
                for fx, fy, size in PATCHES.get(part, []):
                    p.drawEllipse(QPointF(r.left() + r.width() * fx, r.top() + r.height() * fy),
                                  r.width() * size, r.height() * size * 1.2)
            if part in ("leg", "paw"):  # little hooves
                p.setBrush(HOOF)
                p.drawRect(QRectF(r.left(), r.bottom() - r.height() * (0.2 if part == "leg" else 0.5),
                                  r.width(), r.height()))
        return coat
