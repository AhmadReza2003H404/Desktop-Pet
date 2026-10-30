"""Pandas: round, slow, mostly made of bamboo."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter

from core.pet import PetView, State
from render.quadruped import Quadruped


def _panda(base: QColor, dark: QColor) -> dict:
    return {"base": base, "dark": dark, "leg": dark, "ear": dark}


PALETTES = {
    "classic": _panda(QColor(250, 250, 247), QColor(42, 40, 46)),
    "qinling": _panda(QColor(246, 238, 226), QColor(122, 88, 66)),  # the real brown panda
}


class Panda(Quadruped):
    species = "panda"
    name = "Panda"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 42.0
    body_rx, body_ry = 38.0, 23.0
    leg_len = 9.0
    leg_w = 13.0
    head_r = 28.0
    head_shape = (1.1, 0.95)
    tail_kind = "stub"
    nose_kind = "bear"
    muzzle = (0.1, 0.3, 0.34, 0.24)
    idle_weights = {State.WALK: 3, State.IDLE: 3, State.SIT: 4, State.SLEEP: 2}
    specials = ["roll"]
    voice = "grunt"
    favorite_food = "bamboo"
    default_names = ["Bao", "Dumpling", "Mochi", "Oreo", "Bamboo Bob", "Chonk", "Po"]
    lines = {
        "pet": ["*happy panda noises*", "hehe", "squish me more"],
        "hungry": ["bamboo?", "I've only eaten 12 kg today", "*sad chewing sounds*"],
        "fed": ["BAMBOO!", "crunch crunch", "50 more please"],
        "thrown": ["I'm too round for this", "WOOOAH", "panda go brrr"],
        "ouch": ["*rolls over*", "I bounced!", "meant to do that"],
        "woke": ["...bamboo?", "I was busy being cute"],
        "tired": ["roll... nap... roll...", "*big panda yawn*"],
        "sad": ["even pandas need hugs"],
        "idle": ["*rolls*", "I am a professional at sitting", "do I look fluffy?", "chomp"],
    }

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        self.round_ears(p, c, r, size=0.32, spread=0.74)

    def under_eyes(self, p: QPainter, f: QPointF, r: float):
        # the droopy eye patches that make pandas look permanently confused
        p.setPen(Qt.NoPen)
        p.setBrush(self.pal["dark"])
        for side, (x, y, size) in ((-1, (-0.4, -0.1, 0.3)), (1, (0.36, -0.13, 0.36))):
            p.save()
            p.translate(f + QPointF(r * (x + side * 0.04), r * (y + 0.06)))
            p.rotate(side * -28)
            p.drawEllipse(QPointF(0, 0), r * size * 1.25, r * size * 1.55)
            p.restore()

    def markings(self, part: str):
        dark = self.pal["dark"]

        def shoulders(p: QPainter, r: QRectF):
            p.setPen(Qt.NoPen)
            p.setBrush(dark)
            if part == "body":  # dark band over the shoulders and front legs
                p.drawEllipse(QPointF(r.left() + r.width() * 0.7, r.top() + r.height() * 0.35),
                              r.width() * 0.16, r.height() * 0.8)
            elif part == "chest":
                p.drawEllipse(QPointF(r.center().x(), r.top()), r.width() * 0.62, r.height() * 0.28)
        return shoulders
