"""Achievements: little goals that unlock as you play with your pets.

The app counts things (pets given, meals served, dots eaten...) in `stats`;
an achievement unlocks the moment its counter reaches the goal."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    description: str
    stat: str
    goal: int
    icon: str = "🏆"


ACHIEVEMENTS = [
    Achievement("hello", "Hello, friend", "Pet a pet for the first time", "pets", 1, "👋"),
    Achievement("petter", "Professional petter", "Give 100 pets", "pets", 100, "🤲"),
    Achievement("chef", "Little chef", "Serve 10 meals", "meals", 10, "🍳"),
    Achievement("buffet", "All-you-can-eat", "Serve 50 meals", "meals", 50, "🍰"),
    Achievement("fetch", "Fetch champion", "Pets kicked the ball 25 times", "kicks", 25, "⚽"),
    Achievement("circus", "Circus act", "Watch 20 tricks", "tricks", 20, "🎪"),
    Achievement("disco", "Dance party", "Watch your pets dance 10 times", "dances", 10, "🕺"),
    Achievement("cheese", "Say cheese", "Take a photo", "photos", 1, "📸"),
    Achievement("family", "Full house", "Have 5 pets at once", "pets_at_once", 5, "🏠"),
    Achievement("zoo", "Zookeeper", "Keep 4 different kinds of pet at once", "kinds_at_once", 4, "🦁"),
    Achievement("bff", "Best friends", "Reach friendship level 5 with a pet", "best_level", 5, "💖"),
    Achievement("royal", "Royalty", "Reach friendship level 8 and earn the crown", "best_level", 8, "👑"),
    Achievement("arcade", "Insert coin", "Play a round of Dot Dash", "games", 1, "👾"),
    Achievement("gobbler", "Dot gobbler", "Eat 100 dots in Dot Dash", "dots", 100, "🟡"),
    Achievement("powered", "Powered up!", "Grab a power dot", "powerups", 1, "⚡"),
    Achievement("champ", "High score", "Score 300 points in one round of Dot Dash", "best_score", 300, "🥇"),
    Achievement("spooked", "Spooky friends", "See a ghost spook another pet", "boos", 1, "👻"),
    Achievement("weather", "Weather wizard", "Change the weather", "weather", 1, "🌦"),
    Achievement("liftoff", "Liftoff", "Watch a robot rocket-jump", "rockets", 1, "🚀"),
    Achievement("yeet", "Yeet", "Throw a pet really hard", "throws", 1, "🫳"),
]
BY_ID = {a.id: a for a in ACHIEVEMENTS}


@dataclass
class Tracker:
    stats: dict[str, int] = field(default_factory=dict)
    unlocked: set[str] = field(default_factory=set)

    def bump(self, stat: str, amount: int = 1) -> list[Achievement]:
        """Add to a counter. Returns anything that just unlocked."""
        self.stats[stat] = self.stats.get(stat, 0) + amount
        return self._check(stat)

    def at_least(self, stat: str, value: int) -> list[Achievement]:
        """Record a best-ever value (a high score, the most pets at once)."""
        if value > self.stats.get(stat, 0):
            self.stats[stat] = value
        return self._check(stat)

    def _check(self, stat: str) -> list[Achievement]:
        new = [a for a in ACHIEVEMENTS
               if a.stat == stat and a.id not in self.unlocked and self.stats.get(stat, 0) >= a.goal]
        self.unlocked.update(a.id for a in new)
        return new

    def progress(self, a: Achievement) -> tuple[int, int]:
        return min(self.stats.get(a.stat, 0), a.goal), a.goal

    def to_dict(self) -> dict:
        return {"stats": dict(self.stats), "unlocked": sorted(self.unlocked)}

    @classmethod
    def from_dict(cls, data: dict | None) -> "Tracker":
        data = data or {}
        stats = {str(k): int(v) for k, v in (data.get("stats") or {}).items() if isinstance(v, (int, float))}
        unlocked = {u for u in data.get("unlocked") or [] if u in BY_ID}
        return cls(stats, unlocked)
