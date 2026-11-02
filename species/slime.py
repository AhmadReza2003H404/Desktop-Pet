"""Pixel slimes: wobbly jelly blobs that get around by hopping."""

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter

from core.pet import PetView, State
from render.pixel import EyeBox, PixelPet, palette

PALETTES = {
    "lime": palette(QColor(130, 220, 90)),
    "ocean": palette(QColor(80, 170, 240)),
    "strawberry": palette(QColor(250, 110, 140)),
    "grape": palette(QColor(170, 110, 230)),
    "honey": palette(QColor(255, 190, 60)),
    "golden": palette(QColor(250, 205, 70), light=QColor(255, 250, 200), outline=QColor(120, 80, 10)),
}

BODY = [
    "......OOOO......",
    "....OOLLBBOO....",
    "...OBLLBBBBBO...",
    "..OBLLBBBBBBBO..",
    ".OBBLBBBBBBBBBO.",
    ".OBBBBBBBBBBBBO.",
    "OBBBBBBBBBBBBBBO",
    "OBPPBBBBBBBBPPBO",
    "OBBBBBBBBBBBBBBO",
    "OSBBBBBBBBBBBBSO",
    ".OSSBBBBBBBBSSO.",
    "..OOOOOOOOOOOO..",
]


class Slime(PixelPet):
    species = "slime"
    name = "Pixel Slime"
    palettes = PALETTES
    variants = list(PALETTES)
    walk_speed = 50.0
    eyes = [EyeBox(4, 4), EyeBox(10, 4)]
    mouth_at = (6, 7)
    favorite_food = "berries"
    voice = "bloop"
    specials = ["pronk", "roll", "dance"]
    special_weight = 1.4
    default_names = ["Gloop", "Jiggles", "Wobble", "Blobby", "Squish", "Jelly", "Goo-Goo", "Bloop"]
    lines = {
        "pet": ["*jiggles happily*", "squish squish ♥", "boing~"],
        "hungry": ["berries...?", "*sad wobble*", "I'm a hungry blob"],
        "fed": ["*absorbs berry*", "yum!! I'm 2% bigger now", "bloop!"],
        "thrown": ["SPLAT INCOMING", "wheeee-SPLAT", "I'm aerodynamic-ish!"],
        "ouch": ["*splat*", "I'll reshape in a sec"],
        "woke": ["*wobbles awake*", "blub?"],
        "tired": ["*melts a little*", "puddle mode..."],
        "sad": ["*deflates*"],
        "idle": ["bloop.", "*wobble wobble*", "I am mostly jelly", "boing?", "squish!"],
        "dance": ["♪ jiggle jiggle ♪", "*wobbles to the beat*"],
        "dizzy": ["@_@ blooorp", "I'm all mixed up"],
    }

    def frame(self, v: PetView) -> list[str]:
        return BODY

    def _hop(self, v: PetView) -> float:
        return abs(math.sin(v.walk_phase * 0.6))

    def lift(self, v: PetView) -> float:
        if v.state == State.WALK:
            return self._hop(v) * 16
        return 0.0

    def _pose(self, p: QPainter, v: PetView, h: float, lift: float) -> float:
        if v.state == State.WALK:
            hop = self._hop(v)
            squish = 0.2 * (1 - hop) - 0.1  # flat on landing, tall in the air
            p.scale(1 + squish, 1 - squish)
        elif v.state in (State.IDLE, State.SIT, State.SLEEP):
            wob = math.sin(v.t * (2 if v.state == State.SLEEP else 3.2)) * 0.04
            if v.state == State.SLEEP:
                p.scale(1.15 + wob, 0.8 - wob)
            else:
                p.scale(1 + wob, 1 - wob)
        return super()._pose(p, v, h, lift)

    def decorate(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        # a shiny jelly highlight
        shine = QColor(255, 255, 255, 190)
        self._block(p, origin, px, 4, 2, 1, 1, shine)
        self._block(p, origin, px, 3, 3, 1, 1, shine)
