"""Friendship: love points earned by caring for a pet, levels, and the hats they unlock."""

import datetime
import math

LEVEL_STEP = 10  # level 2 at 10 love, 3 at 30, 4 at 60, 5 at 100...

# how much love each kind of care earns
LOVE = {"pet": 1.0, "stroke": 0.5, "fed": 3.0, "kick": 0.5, "greet": 2.0, "trick": 0.5}

# id, label, level needed
HATS = [
    ("none", "No hat", 1),
    ("bow", "Bow", 2),
    ("party", "Party hat", 3),
    ("flower", "Flower", 4),
    ("beanie", "Beanie", 5),
    ("shades", "Sunglasses", 6),
    ("witch", "Witch hat", 7),
    ("crown", "Crown", 8),
]

# id, label, (first month, day), (last month, day): free for everyone in season
SEASONAL = [
    ("pumpkin", "Pumpkin", (10, 15), (11, 5)),
    ("santa", "Santa hat", (12, 1), (12, 31)),
]


def threshold(level: int) -> float:
    """Love needed to reach `level`."""
    return LEVEL_STEP * (level - 1) * level / 2


def level_for(love: float) -> int:
    level = int((math.sqrt(1 + 8 * max(0.0, love) / LEVEL_STEP) - 1) / 2) + 1
    while threshold(level + 1) <= love:  # guard against float rounding
        level += 1
    return level


def progress(love: float) -> tuple[int, float, float]:
    """(level, love into this level, love needed for the next)."""
    level = level_for(love)
    start = threshold(level)
    return level, love - start, threshold(level + 1) - start


def in_season(start: tuple[int, int], end: tuple[int, int], today: datetime.date | None = None) -> bool:
    today = today or datetime.date.today()
    return start <= (today.month, today.day) <= end


def hat_choices(love: float, today: datetime.date | None = None) -> list[tuple[str, str, bool, int]]:
    """Every hat as (id, label, unlocked, level needed). Seasonal ones only show in season."""
    level = level_for(love)
    hats = [(hat, label, level >= need, need) for hat, label, need in HATS]
    for hat, label, start, end in SEASONAL:
        if in_season(start, end, today):
            hats.append((hat, f"{label} (seasonal)", True, 1))
    return hats


def unlocked_at(level: int) -> list[str]:
    return [label for _, label, need in HATS if need == level]


def hat_allowed(hat: str, love: float, today: datetime.date | None = None) -> bool:
    return any(h == hat and ok for h, _, ok, _ in hat_choices(love, today))
