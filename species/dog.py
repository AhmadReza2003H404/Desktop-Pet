"""Dogs: waggy tails, floppy or pointy ears, tongues out."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter

from core.pet import PetView, State
from render import rig
from render.quadruped import Quadruped

WHITE = QColor(252, 248, 240)
BLACK = QColor(55, 50, 55)

PALETTES = {
    "shiba": {"base": QColor(232, 150, 75), "muzzle": WHITE, "white": WHITE, "ears": "pointy"},
    "pug": {"base": QColor(226, 196, 150), "muzzle": QColor(70, 58, 60), "ear": QColor(70, 58, 60),
            "ears": "floppy"},
    "dalmatian": {"base": QColor(250, 250, 250), "muzzle": QColor(250, 250, 250), "ear": BLACK, "spots": BLACK,
                  "ears": "floppy", "tail_kind": "long"},
    "husky": {"base": QColor(128, 134, 150), "muzzle": WHITE, "white": WHITE, "ears": "pointy"},
    "corgi": {"base": QColor(236, 152, 68), "muzzle": WHITE, "white": WHITE, "ears": "big",
              "leg_k": 0.45, "tail_kind": "stub"},
}

# where dalmatian spots go, as fractions of a part's bounding box
SPOTS = {
    "body": [(0.25, 0.3, 0.09), (0.5, 0.15, 0.07), (0.7, 0.45, 0.08), (0.4, 0.6, 0.06), (0.15, 0.65, 0.05)],
    "chest": [(0.3, 0.3, 0.12), (0.7, 0.55, 0.1), (0.4, 0.8, 0.08)],
    "head": [(0.2, 0.25, 0.1), (0.85, 0.45, 0.07)],
    "leg": [(0.5, 0.4, 0.3)],
    "tail": [(0.4, 0.4, 0.12)],
}


class Dog(Quadruped):
    species = "dog"
    name = "Dog"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 80.0
    head_r = 25.0
    head_shape = (1.02, 0.95)
    leg_len = 14.0
    tail_kind = "curl"
    nose_kind = "dog"
    muzzle = (0.12, 0.33, 0.4, 0.27)
    idle_weights = {State.WALK: 6, State.IDLE: 3, State.SIT: 3, State.SLEEP: 1}
    specials = ["zoomies", "tail_chase"]
    voice = "bark"
    favorite_food = "bone"
    default_names = ["Biscuit", "Waffles", "Bean", "Rex", "Pretzel", "Sir Barks", "Toast", "Pancake"]
    lines = {
        "pet": ["best day EVER", "*tail goes brrrr*", "I love you", "again again again"],
        "hungry": ["is it dinner?", "is it dinner now?", "*puppy eyes*", "I would never beg. feed me."],
        "fed": ["BONE!!!", "nom nom nom", "you're the best human"],
        "thrown": ["WHEEEEE", "AGAIN! AGAIN!", "I'm a bird!"],
        "ouch": ["I'm ok!", "that was AWESOME", "*sneeze*"],
        "woke": ["walk?? WALK??", "huh? what? squirrel?"],
        "tired": ["*big yawn*", "zoomies tired me out"],
        "sad": ["*whimper*", "did I do something wrong?"],
        "idle": ["woof!", "squirrel?!", "who's a good boy? ME", "*sniff sniff*", "I heard a noise"],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        style = self.pal["ears"]
        if style == "pointy":
            self.pointy_ears(p, c, r, 1.25, QColor(250, 230, 220))
        elif style == "big":  # corgi: comically large
            self.pointy_ears(p, c, r, 1.55, QColor(250, 215, 205))

    def over_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        if self.pal["ears"] == "floppy":
            self.floppy_ears(p, c, r, v)

    def idle_mouth(self, v: PetView) -> str:
        if v.state in (State.WALK, State.HAPPY) or 2.0 < v.t % 9 < 5.5:
            return "pant"
        return "w"

    def markings(self, part: str):
        pal = self.pal
        if "spots" in pal:
            def spots(p: QPainter, r: QRectF):
                p.setPen(Qt.NoPen)
                p.setBrush(pal["spots"])
                for fx, fy, size in SPOTS.get(part, []):
                    p.drawEllipse(QPointF(r.left() + r.width() * fx, r.top() + r.height() * fy),
                                  r.width() * size, r.width() * size * 0.85)
            return spots

        if "white" in pal:  # white cheeks, bib and socks
            white = pal["white"]
            sock = 0.55 if self.variant == "husky" else 0.32

            def bib(p: QPainter, r: QRectF):
                p.setPen(Qt.NoPen)
                p.setBrush(white)
                if part == "body":
                    p.drawEllipse(QPointF(r.right() - r.width() * 0.2, r.bottom() - r.height() * 0.1),
                                  r.width() * 0.3, r.height() * 0.55)
                elif part == "chest":
                    p.drawEllipse(QPointF(r.center().x() + r.width() * 0.18, r.center().y() + r.height() * 0.1),
                                  r.width() * 0.35, r.height() * 0.45)
                elif part == "head":
                    if self.variant == "husky":  # the mask: white face, dark cap
                        p.drawEllipse(QPointF(r.center().x() + r.width() * 0.07, r.bottom() - r.height() * 0.2),
                                      r.width() * 0.5, r.height() * 0.42)
                        p.drawEllipse(QPointF(r.center().x() - r.width() * 0.05, r.top() + r.height() * 0.42),
                                      r.width() * 0.06, r.height() * 0.05)
                        p.drawEllipse(QPointF(r.center().x() + r.width() * 0.25, r.top() + r.height() * 0.4),
                                      r.width() * 0.06, r.height() * 0.05)
                    else:
                        for fx in (0.12, 0.88):
                            p.drawEllipse(QPointF(r.left() + r.width() * fx, r.bottom() - r.height() * 0.28),
                                          r.width() * 0.16, r.height() * 0.13)
                        if self.variant == "corgi":  # white blaze up the forehead
                            p.drawEllipse(QPointF(r.center().x() + r.width() * 0.07, r.top() + r.height() * 0.3),
                                          r.width() * 0.06, r.height() * 0.3)
                elif part in ("leg", "paw"):
                    p.drawRect(QRectF(r.left(), r.bottom() - r.height() * sock, r.width(), r.height() * sock))
                elif part == "tail" and self.variant != "corgi":
                    p.drawEllipse(QPointF(r.right(), r.top()), r.width() * 0.5, r.height() * 0.4)
            return bib

        if self.variant == "pug":
            def wrinkles(p: QPainter, r: QRectF):
                if part == "head":
                    p.setPen(QColor(150, 120, 90))
                    cx, top = r.center().x() + r.width() * 0.07, r.top() + r.height() * 0.22
                    for k in range(3):
                        y = top + k * r.height() * 0.06
                        w = r.width() * (0.12 - k * 0.02)
                        p.drawArc(QRectF(cx - w, y, w * 2, r.height() * 0.08), 20 * 16, 140 * 16)
            return wrinkles
        return None

    def tail(self, p: QPainter, v: PetView, pose: str, root: QPointF):
        if self.variant != "dalmatian" or pose not in ("stand", "sit", "sleep"):
            return super().tail(p, v, pose, root)
        if pose != "stand":
            return  # long tail tucked out of sight
        # straight tail held up, wagging
        happy = v.state in (State.HAPPY, State.EAT, State.WALK)
        angle = math.radians(35 + math.sin(v.t * (16 if happy else 3)) * (14 if happy else 5))
        tip = root + QPointF(-26 * math.cos(angle), -26 * math.sin(angle)) * self.body_k
        shape = rig.thick_line(rig.line_path(root, tip), 7 * self.body_k)
        rig.fill_part(p, shape, self.color("tail"), self.markings("tail"))


class Puppy(Dog):
    species = "puppy"
    name = "Puppy"
    width = height = 92
    walk_speed = 95.0
    head_k = 1.22
    body_k = 0.8
    idle_weights = {State.WALK: 7, State.IDLE: 2, State.SIT: 2, State.SLEEP: 1}
    durations = {**Dog.durations, State.SLEEP: (10.0, 25.0)}
