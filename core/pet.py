"""The Pet interface. Every animal in species/ subclasses Pet."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtGui import QPainter


class State(Enum):
    IDLE = auto()
    WALK = auto()
    SIT = auto()
    SLEEP = auto()
    HAPPY = auto()    # being petted
    EAT = auto()
    SPECIAL = auto()  # a trick: zoomies, rolling, pouncing... see core/specials.py
    DRAGGED = auto()
    FALLING = auto()


@dataclass
class PetView:
    """Everything a Pet needs to know to draw one frame."""

    state: State
    t: float              # seconds since start, for idle animations
    state_time: float     # seconds spent in the current state
    facing: int           # 1 = right, -1 = left
    squash: float         # >0 squashed flat (landing), <0 stretched tall
    look: tuple[float, float]  # unit-ish vector from pet towards the cursor (screen space)
    walk_phase: float     # advances while walking or flailing, drives leg swing
    blink: bool           # eyes shut for a moment
    special: str = ""     # during State.SPECIAL: the pose the trick wants ("roll", "slide"...)
    special_value: float = 0.0  # pose parameter, e.g. the roll angle in degrees
    mood: str = ""        # "", "hungry", "sad" or "tired": changes the face a little


class Pet(ABC):
    """Subclass this, set the class attributes, implement draw(), and drop the
    file into species/. The registry picks it up automatically."""

    species: str = ""     # unique id, e.g. "cat"
    name: str = ""        # shown in menus, e.g. "Cat"
    variants: list[str] = ["default"]
    width: int = 120
    height: int = 120
    walk_speed: float = 70.0  # px per second
    favorite_food: str = "fish"  # a kind render/food.py knows how to draw
    default_names: list[str] = ["Buddy"]
    voice: str = ""       # a sound name from ui/sound.py, played when it talks
    specials: list[str] = []  # tricks from core/specials.py this animal does on its own
    special_weight: float = 1.0

    # how likely each resting choice is when the pet decides what to do next
    idle_weights: dict[State, float] = {State.WALK: 4, State.IDLE: 3, State.SIT: 2, State.SLEEP: 1}
    # (min, max) seconds for each resting state
    durations: dict[State, tuple[float, float]] = {
        State.IDLE: (1.5, 4.0),
        State.SIT: (4.0, 12.0),
        State.SLEEP: (15.0, 40.0),
    }

    # things the pet says in speech bubbles, keyed by situation
    lines: dict[str, list[str]] = {
        "pet": ["hehe", "♥", "more pls"],
        "hungry": ["feed me...", "*stomach rumbles*"],
        "fed": ["yum!", "nom nom"],
        "thrown": ["WHEEE", "AAAAA"],
        "ouch": ["ow.", "my dignity"],
        "woke": ["huh?!", "five more minutes"],
        "tired": ["*yawn*"],
        "sad": ["nobody pets me anymore"],
        "idle": ["hmm", "la la la"],
        "bonk": ["BONK", "ow."],
        "dizzy": ["@_@", "the room is spinning"],
        "wheee": ["WHEEEE"],
        "friend": ["hi friend!", "*sniff sniff*", "oh hey!"],
        "night": ["it's late... go to bed?", "*yawn* bedtime?"],
        "welcome": ["welcome back! ♥", "you're back!!", "I missed you!", "where did you go?!"],
        "laser": ["THE DOT!!", "I WILL CATCH IT", "red dot red dot red dot"],
        "photo": ["say cheese!", "*poses*", "get my good side"],
        "dance": ["♪ ♫ ♪", "*shows off some moves*", "dance party!!"],
        "spooked": ["AAAAA!", "a GHOST?!", "don't DO that!!", "*jumps out of skin*"],
        "arcade": ["dots!!", "mine mine mine!", "nom nom nom", "I'm gonna win!"],
        "power": ["POWER UP! ⚡", "I feel FAST", "zoom zoom!"],
        "won": ["I WON! 🏆", "champion!!", "high score, baby!"],
        "lost": ["good game!", "rematch?", "I let you win"],
        "snow": ["snow!! ❄", "brrr, it's chilly", "can we build a snowpet?"],
        "rain": ["it's raining!", "*shakes off water*", "puddles!!"],
        "leaves": ["crunchy leaves!", "autumn vibes 🍂", "*chases a leaf*"],
        "petals": ["so pretty 🌸", "*sneezes at a petal*", "spring!!"],
        "fireflies": ["tiny lights!", "ooh, sparkly ✨", "can I catch one?"],
    }

    def __init__(self, variant: str | None = None, scale: float = 1.0):
        if variant is not None and variant not in self.variants:
            raise ValueError(f"{self.species} has no variant {variant!r}; pick one of {self.variants}")
        self.variant = variant or self.variants[0]
        self.hat = "none"     # accessory from render/hats.py
        self.scale = scale
        self.width = round(type(self).width * scale)
        self.height = round(type(self).height * scale)

    @abstractmethod
    def draw(self, p: QPainter, view: PetView) -> None:
        """Draw the pet into a width x height box. The ground is the bottom edge."""
