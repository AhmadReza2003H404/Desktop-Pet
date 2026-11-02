"""Pixel ghosts: friendly little retro arcade spooks that float instead of walk.

They phase through the air, drift up the screen to haunt it, and love to
sneak up on the other pets and say BOO."""

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter

from core.pet import PetView, State
from render.pixel import EyeBox, PixelPet, glow, palette

PALETTES = {
    "minty": palette(QColor(120, 230, 190)),
    "lavender": palette(QColor(185, 160, 245)),
    "lemon": palette(QColor(255, 225, 95)),
    "bubblegum": palette(QColor(255, 150, 200)),
    "sky": palette(QColor(120, 190, 255)),
    "sheet": palette(QColor(240, 242, 250), outline=QColor(95, 100, 130)),
    "midnight": palette(QColor(55, 70, 150), white=QColor(255, 250, 210), pupil=QColor(255, 120, 90),
                        outline=QColor(20, 22, 50), light=QColor(95, 115, 200)),
}

BODY = [
    "......OOOO......",
    "....OOBBBBOO....",
    "...OLLBBBBBBO...",
    "..OLLBBBBBBBBO..",
    "..OLBBBBBBBBBO..",
    ".OBBBBBBBBBBBBO.",
    ".OBBBBBBBBBBBBO.",
    "OOBBBBBBBBBBBBOO",
    "OBBPPBBBBBBPPBBO",
    ".OOBBBBBBBBBBOO.",
    "..OBBBBBBBBBBO..",
    "..OBBBBBBBBBSO..",
    "..OSBBBBBBBSSO..",
]
# the hem ripples between two frames as it floats
HEMS = [
    ["..OBSSBBSSBBSO..",
     "..OO.OOSSO.OOO..",
     "......OO........"],
    ["..OSBBSSBBSSBO..",
     "..OOO.OSSOO.OO..",
     "........OO......"],
]


class Ghost(PixelPet):
    species = "ghost"
    name = "Pixel Ghost"
    palettes = PALETTES
    variants = list(PALETTES)
    hover = 14.0
    bob = 4.0
    walk_speed = 60.0
    eyes = [EyeBox(4, 4), EyeBox(10, 4)]
    mouth_at = (6, 7)
    favorite_food = "candy"
    voice = "ooo"
    specials = ["phase", "haunt", "dance", "zoomies"]
    special_weight = 1.6
    idle_weights = {State.WALK: 5, State.IDLE: 3, State.SIT: 1, State.SLEEP: 1}
    default_names = ["Boo-Bit", "Wisp", "Pixel", "Spooks", "Glimmer", "Casper-8", "Mochi", "Blip"]
    lines = {
        "pet": ["*happy ghostly noises*", "oooOOOooo ♥", "you can touch me??"],
        "hungry": ["I hunger... for candy", "*ghostly tummy rumble*", "sweets... pls..."],
        "fed": ["SUGAR RUSH", "candy!!! boo-tiful", "*glows brighter*"],
        "thrown": ["I CAN FLY ANYWAY", "wheeeOOOO", "you can't throw a ghost!!"],
        "ouch": ["I'm a ghost, that didn't hurt. ow.", "*fizzles*"],
        "woke": ["who disturbs my slumber?!", "boo? ...oh it's you"],
        "tired": ["*fading out*", "need... spooky... nap"],
        "sad": ["I feel invisible...", "nobody sees me"],
        "idle": ["boo.", "*floats menacingly*", "oooOOOooo", "I'm not scary, I'm cute",
                 "8-bit and proud", "hi! I live here now"],
        "boo": ["BOO!", "BOO!!!", "Boo! hehehe"],
        "friend": ["hey! wanna get spooked?", "*waves a little ghost arm*"],
        "laser": ["a ghost dot?!", "I can float faster!"],
        "night": ["peak haunting hours ✨", "it's late... spooky time"],
        "dance": ["♪ boogie-oogie-oo ♪", "*spooky shuffle*"],
        "wheee": ["*whooosh*"],
    }

    def frame(self, v: PetView) -> list[str]:
        speed = 4 if v.state in (State.WALK, State.SPECIAL) else 2.5
        return BODY + HEMS[int(v.t * speed) % 2]

    def lift(self, v: PetView) -> float:
        lift = super().lift(v)
        if v.state == State.WALK:
            lift += math.sin(v.walk_phase * 0.5) * 2
        elif v.state == State.SIT:
            lift *= 0.5  # settles down low to rest
        return lift

    def decorate(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        if v.state == State.SPECIAL and v.special == "phase":
            # a sparkly trail while gliding through the air
            for k in range(4):
                a = v.t * 6 + k * 1.7
                c = origin + QPointF(-px * (2 + k * 2.5), px * (5 + math.sin(a) * 2.5))
                glow(p, c, px * (1.6 - k * 0.3), QColor(self.colour("light").red(), self.colour("light").green(),
                                                        self.colour("light").blue(), 200))
