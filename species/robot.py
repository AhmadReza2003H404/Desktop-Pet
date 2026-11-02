"""Pixel robots: little 8-bit bots with a screen for a face and a rocket in their boots."""

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter

from core.pet import PetView, State
from render.pixel import EyeBox, PixelPet, glow, palette

PALETTES = {
    "silver": palette(QColor(185, 195, 210), glow=QColor(90, 240, 255), screen=QColor(20, 35, 50),
                      accent=QColor(255, 90, 90)),
    "retro_red": palette(QColor(225, 80, 70), glow=QColor(255, 230, 90), screen=QColor(40, 20, 20),
                         accent=QColor(255, 210, 80)),
    "toy_blue": palette(QColor(80, 140, 230), glow=QColor(140, 255, 140), screen=QColor(15, 25, 50),
                        accent=QColor(255, 200, 60)),
    "mint": palette(QColor(130, 215, 180), glow=QColor(255, 130, 200), screen=QColor(20, 45, 40),
                    accent=QColor(255, 120, 160)),
    "gold": palette(QColor(240, 195, 70), glow=QColor(120, 220, 255), screen=QColor(45, 30, 10),
                    accent=QColor(230, 70, 90), outline=QColor(110, 70, 10)),
}

HEAD = [
    "......OO......",
    "......OO......",
    "..OOOOOOOOOO..",
    ".OLLLBBBBBBBO.",
    ".OBOOOOOOOOBO.",
    ".OBOKKKKKKOBO.",
    "OOBOKKKKKKOBOO",
    "OAOOKKKKKKOOAO",
    "OOBOKKKKKKOBOO",
    ".OBOOOOOOOOBO.",
    ".OSBBBBBBBBSO.",
    "..OOOOOOOOOO..",
]
BODY = [
    "...OOBBBBOO...",
    "..OBBLAABBBO..",
    ".OSOBBAABBOSO.",
    ".OSOBBBBBBOSO.",
    ".OOOSBBBBSOOO.",
    "....OOOOOO....",
]
LEGS = [
    ["....OBO.OBO...", "...OOOO.OOOO.."],   # standing
    ["...OBO...OBO..", "..OOOO...OOOO."],   # step
    ["....OBOOBO....", "...OOOOOOOO..."],   # step
]


class Robot(PixelPet):
    species = "robot"
    name = "Pixel Robot"
    palettes = PALETTES
    variants = list(PALETTES)
    px = 4.6
    walk_speed = 55.0
    eyes = [EyeBox(4, 5, 2, 2), EyeBox(8, 5, 2, 2)]
    sclera = False
    pupil_w, pupil_h = 1, 2
    mouth_at = (5, 7)
    favorite_food = "battery"
    voice = "beep"
    specials = ["rocket", "dance", "zoomies"]
    special_weight = 1.3
    default_names = ["Bolt", "Beep", "Sprocket", "Unit-7", "Byte", "Gizmo", "Pixel", "Chip"]
    lines = {
        "pet": ["HAPPINESS.EXE ♥", "*happy beeping*", "affection received!"],
        "hungry": ["battery low 🔋", "please insert battery", "power at 12%..."],
        "fed": ["FULLY CHARGED ⚡", "*bzzt* delicious", "100%!!"],
        "thrown": ["ERROR ERROR", "GYROSCOPE FAILURE", "WHEEE.wav"],
        "ouch": ["*clank*", "minor dent detected"],
        "woke": ["rebooting...", "system online. hi!"],
        "tired": ["entering sleep mode...", "low power..."],
        "sad": ["loneliness.exe has stopped responding"],
        "idle": ["beep boop", "*whirr*", "scanning... you look nice", "0101 ♥", "compiling a joke...",
                 "I dream of electric sheep"],
        "dance": ["♪ robot dance protocol ♪", "*does the robot*"],
        "laser": ["TARGET ACQUIRED", "tracking red object..."],
        "night": ["it's late, human. rest required", "*dims screen*"],
    }

    def frame(self, v: PetView) -> list[str]:
        if v.state == State.WALK or (v.state == State.SPECIAL and v.special == "walk"):
            legs = LEGS[1 + int(v.walk_phase / math.pi) % 2]
        else:
            legs = LEGS[0]
        return HEAD + BODY + legs

    def lift(self, v: PetView) -> float:
        if v.state == State.SPECIAL and v.special == "rocket":
            return 16.0  # room for the flames
        if v.state == State.WALK:
            return abs(math.sin(v.walk_phase)) * 1.5
        return 0.0

    def decorate(self, p: QPainter, v: PetView, origin: QPointF, px: float):
        # antenna light pulses
        pulse = 0.5 + 0.5 * math.sin(v.t * (8 if v.state == State.HAPPY else 3))
        tip = origin + QPointF(7 * px, -px * 0.6)
        g = QColor(self.colour("accent"))
        g.setAlpha(int(140 + 115 * pulse))
        glow(p, tip, px * (1.6 + pulse), g)
        self._block(p, origin, px, 6.5, -1.2, 1, 1, self.colour("accent"))
        if v.state == State.SPECIAL and v.special == "rocket":
            rows = len(self.frame(v))
            for k, col in enumerate((4.5, 9.5)):
                flame = origin + QPointF(col * px, rows * px + px * (1.5 + math.sin(v.t * 40 + k) * 0.6))
                glow(p, flame, px * 3.2, QColor(255, 160, 40, 230))
                glow(p, flame, px * 1.6, QColor(255, 250, 200, 255))
