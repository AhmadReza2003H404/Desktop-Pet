"""Fullness, energy and happiness. They drift down over time; nothing ever dies."""

from dataclasses import asdict, dataclass

from core.pet import State

FULLNESS_DECAY = 100 / (3 * 3600)   # empty after ~3 hours
ENERGY_DECAY = 100 / (5 * 3600)     # tired after ~5 hours awake
SLEEP_REGEN = 100 / (8 * 60)        # a full recharge takes an 8 minute nap
HAPPINESS_DECAY = 100 / (4 * 3600)
AWAY_FLOOR = 15.0  # being away for days never drops a need below this


def _clamp(value: float, floor: float = 0.0) -> float:
    return max(floor, min(100.0, value))


@dataclass
class Needs:
    fullness: float = 80.0
    energy: float = 90.0
    happiness: float = 80.0

    @property
    def hungry(self) -> bool:
        return self.fullness < 30

    @property
    def tired(self) -> bool:
        return self.energy < 25

    @property
    def sad(self) -> bool:
        return self.happiness < 30

    def tick(self, dt: float, state: State):
        self.fullness = _clamp(self.fullness - FULLNESS_DECAY * dt)
        if state == State.SLEEP:
            self.energy = _clamp(self.energy + SLEEP_REGEN * dt)
        else:
            self.energy = _clamp(self.energy - ENERGY_DECAY * dt)
        self.happiness = _clamp(self.happiness - HAPPINESS_DECAY * dt)

    def catch_up(self, seconds: float):
        """Apply time spent while the app was closed (the pet was awake and alone)."""
        seconds = max(0.0, seconds)
        self.fullness = _clamp(self.fullness - FULLNESS_DECAY * seconds, min(self.fullness, AWAY_FLOOR))
        self.energy = _clamp(self.energy - ENERGY_DECAY * seconds, min(self.energy, AWAY_FLOOR))
        self.happiness = _clamp(self.happiness - HAPPINESS_DECAY * seconds, min(self.happiness, AWAY_FLOOR))

    def fed(self):
        self.fullness = _clamp(self.fullness + 35)
        self.happiness = _clamp(self.happiness + 8)

    def cheer(self, amount: float):
        self.happiness = _clamp(self.happiness + amount)

    def to_dict(self) -> dict:
        return {k: round(v, 2) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict | None) -> "Needs":
        data = data or {}
        return cls(**{k: _clamp(float(data[k])) for k in ("fullness", "energy", "happiness") if k in data})
