"""Position, velocity, gravity and screen-edge collisions for one pet."""

from dataclasses import dataclass

from PySide6.QtCore import QRect

GRAVITY = 2200.0       # px/s^2
BOUNCE = 0.35          # fraction of speed kept when hitting floor or walls
GROUND_FRICTION = 8.0  # how fast sliding stops on the floor
MAX_SPEED = 3000.0


@dataclass
class Body:
    x: float
    y: float
    w: int
    h: int
    vx: float = 0.0
    vy: float = 0.0
    bounce: float = BOUNCE
    min_bounce: float = 500.0  # slower than this and it stops bouncing
    friction: float = GROUND_FRICTION

    def floor(self, area: QRect) -> float:
        return area.bottom() + 1 - self.h

    def on_ground(self, area: QRect) -> bool:
        return self.y >= self.floor(area) - 0.5

    def step(self, dt: float, area: QRect) -> float:
        """Advance one tick. Returns the impact speed if it hit the floor, else 0."""
        self.vx = max(-MAX_SPEED, min(MAX_SPEED, self.vx))
        self.vy = max(-MAX_SPEED, min(MAX_SPEED, self.vy))

        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        left, right = area.left(), area.right() + 1 - self.w
        if self.x < left:
            self.x, self.vx = left, -self.vx * self.bounce
        elif self.x > right:
            self.x, self.vx = right, -self.vx * self.bounce

        if self.y < area.top():
            self.y, self.vy = area.top(), 0.0

        impact = 0.0
        floor = self.floor(area)
        if self.y >= floor:
            self.y = floor
            impact = self.vy
            self.vy = -self.vy * self.bounce if self.vy > self.min_bounce else 0.0
            self.vx *= max(0.0, 1 - self.friction * dt)
        return impact
