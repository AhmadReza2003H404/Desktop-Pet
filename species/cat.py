"""Cats and kittens: chubby bodies, big heads, mismatched googly eyes."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from core.pet import PetView, State
from render.quadruped import Quadruped

PALETTES = {
    "tabby": {"base": QColor(242, 165, 85), "mark": QColor(200, 112, 48)},
    "gray": {"base": QColor(163, 168, 182), "mark": QColor(108, 113, 128)},
    "black": {"base": QColor(58, 56, 66), "light_whiskers": True},
    "siamese": {"base": QColor(246, 234, 212), "mark": QColor(98, 70, 58),
                "ear": QColor(98, 70, 58), "tail": QColor(98, 70, 58)},
    "tuxedo": {"base": QColor(52, 50, 60), "mark": QColor(250, 250, 250), "light_whiskers": True},
    "calico": {"base": QColor(252, 250, 246), "mark": QColor(236, 150, 70), "mark2": QColor(62, 56, 62),
               "ear0": QColor(236, 150, 70), "ear1": QColor(62, 56, 62), "tail": QColor(236, 150, 70)},
}


class Cat(Quadruped):
    species = "cat"
    name = "Cat"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 65.0
    idle_weights = {State.WALK: 4, State.IDLE: 3, State.SIT: 3, State.SLEEP: 1}
    whiskers = True
    specials = ["zoomies", "pounce"]
    voice = "meow"
    favorite_food = "fish"
    default_names = ["Mittens", "Mochi", "Nugget", "Pickles", "Biscuit", "Sir Fluff", "Noodle", "Meatball"]
    lines = {
        "pet": ["purrrr~", "mrrp ♥", "ok one more", "acceptable."],
        "hungry": ["feed me, human", "the bowl is EMPTY", "*stares at you*", "I will knock your mug over"],
        "fed": ["nom nom nom", "FISH!!", "you may live"],
        "thrown": ["MRAAOW", "I CAN FLY", "this is fine"],
        "ouch": ["I meant to do that", "ow.", "nobody saw that"],
        "woke": ["...rude", "5 more minutes", "I was dreaming of fish"],
        "tired": ["*yaaawn*", "nap time?"],
        "sad": ["you never pet me", "*sad meow*"],
        "idle": ["mew?", "I own this screen", "where is the red dot", "*knocks something off*", "if I fits, I sits"],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        self.pointy_ears(p, c, r)

    def idle_mouth(self, v: PetView) -> str:
        return "blep" if v.state == State.SIT and 3.0 < v.state_time % 11 < 4.6 else "w"

    def markings(self, part: str):
        variant, pal = self.variant, self.pal
        mark = pal.get("mark")

        def pen(width):
            return QPen(mark, width, Qt.SolidLine, Qt.RoundCap)

        if variant in ("tabby", "gray"):
            def stripes(p: QPainter, r: QRectF):
                if part in ("body", "chest"):
                    p.setPen(pen(4.5))
                    for k in range(4):
                        x = r.left() + r.width() * (0.2 + 0.18 * k)
                        p.drawLine(QPointF(x, r.top() - 2), QPointF(x - 3, r.top() + r.height() * 0.42))
                elif part == "head":
                    p.setPen(pen(3.5))
                    cx = r.center().x() + r.width() * 0.04
                    for dx in (-0.14, 0, 0.14):
                        x = cx + r.width() * dx
                        p.drawLine(QPointF(x, r.top() - 2), QPointF(x, r.top() + r.height() * (0.22 - abs(dx))))
                elif part == "tail":
                    p.setPen(pen(4))
                    x = r.left() + 6
                    while x < r.right():
                        p.drawLine(QPointF(x, r.top()), QPointF(x - 4, r.bottom()))
                        x += 11
            return stripes

        if variant == "siamese":
            def points(p: QPainter, r: QRectF):
                p.setPen(Qt.NoPen)
                if part == "head":
                    p.setBrush(mark.lighter(135))
                    p.drawEllipse(QPointF(r.center().x() + r.width() * 0.07, r.center().y() + r.height() * 0.2),
                                  r.width() * 0.3, r.height() * 0.28)
                elif part in ("leg", "paw"):
                    p.setBrush(mark)
                    p.drawRect(QRectF(r.left(), r.bottom() - r.height() * 0.45, r.width(), r.height() * 0.45))
            return points

        if variant == "tuxedo":
            def tux(p: QPainter, r: QRectF):
                p.setPen(Qt.NoPen)
                p.setBrush(mark)
                if part == "body":
                    p.drawEllipse(QPointF(r.right() - r.width() * 0.22, r.bottom()), r.width() * 0.3, r.height() * 0.55)
                elif part == "chest":
                    p.drawEllipse(QPointF(r.center().x() + r.width() * 0.15, r.center().y()),
                                  r.width() * 0.32, r.height() * 0.42)
                elif part == "head":
                    p.drawEllipse(QPointF(r.center().x() + r.width() * 0.07, r.bottom() - r.height() * 0.12),
                                  r.width() * 0.3, r.height() * 0.3)
                elif part in ("leg", "paw"):
                    p.drawRect(QRectF(r.left(), r.bottom() - r.height() * 0.35, r.width(), r.height() * 0.35))
            return tux

        if variant == "calico":
            def patches(p: QPainter, r: QRectF):
                p.setPen(Qt.NoPen)
                if part in ("body", "chest"):
                    p.setBrush(mark)
                    p.drawEllipse(QPointF(r.left() + r.width() * 0.3, r.top() + r.height() * 0.25),
                                  r.width() * 0.32, r.height() * 0.45)
                    p.setBrush(pal["mark2"])
                    p.drawEllipse(QPointF(r.left() + r.width() * 0.78, r.top() + r.height() * 0.15),
                                  r.width() * 0.2, r.height() * 0.3)
                elif part == "head":
                    p.setBrush(mark)
                    p.drawEllipse(QPointF(r.left() + r.width() * 0.15, r.top() + r.height() * 0.25),
                                  r.width() * 0.32, r.height() * 0.4)
                    p.setBrush(pal["mark2"])
                    p.drawEllipse(QPointF(r.right() - r.width() * 0.1, r.top()), r.width() * 0.25, r.height() * 0.3)
            return patches

        return None


class Kitten(Cat):
    species = "kitten"
    name = "Kitten"
    width = height = 92
    walk_speed = 82.0
    head_k = 1.2
    body_k = 0.82
    idle_weights = {State.WALK: 6, State.IDLE: 2, State.SIT: 2, State.SLEEP: 1}
    durations = {**Cat.durations, State.SLEEP: (10.0, 25.0)}
