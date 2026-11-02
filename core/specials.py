"""Tricks: short scripted bits of behaviour that take over the pet for a few seconds.

Each trick moves the body itself and tells the drawing code which pose to use
through `pose` (and `value`, e.g. a roll angle). Species list the tricks they
do on their own in Pet.specials; any animal can be asked to do any of them.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QRect

from core.pet import State
from core.physics import GRAVITY, Body

if TYPE_CHECKING:
    from core.behavior import Brain


class Special:
    name = ""
    pose = "walk"  # walk | stand | crouch | spin | roll | air | dazed | slide | cling | cling_sleep

    def __init__(self, brain: Brain, body: Body, area: QRect, cursor_x: float, **kwargs):
        self.brain = brain
        self.t = 0.0
        self.value = 0.0

    @classmethod
    def possible(cls, brain: Brain, body: Body, area: QRect, cursor_x: float) -> bool:
        return True

    def update(self, dt: float, body: Body, area: QRect, cursor_x: float) -> bool:
        """Advance; return True when finished."""
        raise NotImplementedError

    # helpers

    @staticmethod
    def edges(body: Body, area: QRect) -> tuple[float, float]:
        return area.left(), area.right() + 1 - body.w

    def run_to(self, body: Body, x: float, speed: float, dt: float) -> bool:
        dx = x - body.x
        step = speed * dt
        if abs(dx) <= step:
            body.x = x
            return True
        self.brain.facing = 1 if dx > 0 else -1
        body.x += step * self.brain.facing
        self.brain.walk_phase += dt * 10 * speed / self.brain.pet.walk_speed
        return False


class Zoomies(Special):
    """Sudden sprint back and forth for no reason at all."""
    name = "zoomies"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        direction = random.choice((-1, 1))
        self.targets = []
        x = body.x
        for _ in range(random.randint(2, 3)):
            x = max(lo, min(hi, x + direction * random.uniform(250, 600)))
            self.targets.append(x)
            direction = -direction

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        if self.run_to(body, self.targets[0], self.brain.pet.walk_speed * 4.5, dt):
            self.targets.pop(0)
        return not self.targets


class Pounce(Special):
    """Wiggle the butt, then leap at the mouse cursor."""
    name = "pounce"
    pose = "crouch"

    @classmethod
    def possible(cls, brain, body, area, cursor_x):
        return 60 < abs(cursor_x - (body.x + body.w / 2)) < 450

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        dx = cursor_x - (body.x + body.w / 2)
        self.brain.facing = 1 if dx > 0 else -1
        if self.t < 0.9:
            return False
        body.vx = max(-900.0, min(900.0, dx * 1.8))
        body.vy = -650.0
        self.brain.squash = -0.25
        self.brain.events.append("pounce")
        self.brain.set_state(State.FALLING)
        return True


class TailChase(Special):
    """Spin in circles trying to catch its own tail."""
    name = "tail_chase"
    pose = "spin"

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        self.brain.facing = 1 if int(self.t / 0.2) % 2 else -1
        self.brain.walk_phase += dt * 20
        if self.t > 2.6:
            self.brain.events.append("dizzy")
            return True
        return False


class Roll(Special):
    """Curl into a ball and roll along the floor."""
    name = "roll"
    pose = "roll"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        direction = 1 if hi - body.x > body.x - lo else -1  # away from the nearest wall
        self.target = max(lo, min(hi, body.x + direction * random.uniform(150, 260)))
        self.start_x = body.x
        self.radius = 20 * brain.pet.width / 120

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        done = self.run_to(body, self.target, 140, dt)
        self.value = math.degrees(abs(body.x - self.start_x) / self.radius)
        if done:
            self.brain.events.append("dizzy")
        return done


class Pronk(Special):
    """Goat-style bouncing straight up, several times."""
    name = "pronk"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.hops = random.randint(3, 4)
        self.height = 0.0
        self.vy = 0.0
        self.pause = 0.1

    def update(self, dt, body, area, cursor_x):
        floor = body.floor(area)
        if self.pause > 0:
            self.pose = "stand"
            self.pause -= dt
            if self.pause <= 0:
                if self.hops == 0:
                    return True
                self.hops -= 1
                self.vy = -random.uniform(520, 640)
                self.brain.squash = -0.15
        else:
            self.pose = "air"
            self.vy += GRAVITY * dt
            self.height -= self.vy * dt
            lo, hi = self.edges(body, area)
            body.x = max(lo, min(hi, body.x + self.brain.facing * 50 * dt))
            if self.height <= 0:
                self.height, self.vy, self.pause = 0.0, 0.0, 0.18
                self.brain.squash = 0.2
        body.y = floor - self.height
        return False


class Headbutt(Special):
    """Charge at the edge of the screen and bonk it."""
    name = "headbutt"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        self.target = lo if body.x - lo < hi - body.x else hi
        self.dazed = 0.0

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        if self.dazed > 0:
            self.dazed -= dt
            return self.dazed <= 0
        if self.run_to(body, self.target, self.brain.pet.walk_speed * 3.5, dt):
            self.brain.squash = 0.4
            self.brain.events.append("bonk")
            body.x -= self.brain.facing * 8
            self.pose = "dazed"
            self.dazed = 1.3
        return False


class BellySlide(Special):
    """A short run-up, then flop on the belly and slide."""
    name = "belly_slide"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        self.direction = 1 if hi - body.x > body.x - lo else -1
        self.speed = 0.0

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        lo, hi = self.edges(body, area)
        if self.pose == "walk":
            self.brain.facing = self.direction
            self.run_to(body, hi if self.direction > 0 else lo, self.brain.pet.walk_speed * 2.5, dt)
            if self.t > 0.7:
                self.pose, self.speed = "slide", 430.0
                self.brain.events.append("wheee")
            return False
        self.speed -= 170 * dt
        body.x = max(lo, min(hi, body.x + self.direction * self.speed * dt))
        return self.speed <= 0 or body.x in (lo, hi)


class Cling(Special):
    """Koala move: walk to the screen edge, climb it like a tree, nap there."""
    name = "cling"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        self.side = -1 if body.x - lo < hi - body.x else 1
        self.wall_x = lo if self.side < 0 else hi
        self.climb_to = random.uniform(120, 300)
        self.climbed = 0.0
        self.nap = random.uniform(40, 90)

    def update(self, dt, body, area, cursor_x):
        if self.pose == "walk":
            body.step(dt, area)
            if self.run_to(body, self.wall_x, self.brain.pet.walk_speed * 1.2, dt):
                self.pose = "cling"
            return False
        self.brain.facing = self.side
        if self.pose == "cling":
            self.climbed += 30 * dt
            self.brain.walk_phase += dt * 6
            if self.climbed >= self.climb_to:
                self.pose = "cling_sleep"
        else:
            self.t += dt
            if self.t > self.nap:
                self.brain.events.append("woke")
                self.brain.set_state(State.FALLING)  # let go
                return True
        body.y = body.floor(area) - self.climbed
        return False


class Chase(Special):
    """Run after another pet (or anything that has an x)."""
    name = "chase"

    def __init__(self, brain, body, area, cursor_x, target: Callable[[], float] | None = None, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.target = target or (lambda: cursor_x)
        self.duration = random.uniform(4, 6)

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        lo, hi = self.edges(body, area)
        x = max(lo, min(hi, self.target() - body.w / 2))
        self.run_to(body, x, self.brain.pet.walk_speed * 2.6, dt)
        return self.t > self.duration


class Flee(Special):
    """Run away from a chaser, giggling."""
    name = "flee"

    def __init__(self, brain, body, area, cursor_x, chaser: Callable[[], float] | None = None, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.chaser = chaser or (lambda: cursor_x)
        self.duration = random.uniform(4, 6)

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        lo, hi = self.edges(body, area)
        away = hi if self.chaser() < body.x + body.w / 2 else lo
        if abs(away - body.x) < 5:  # cornered: dodge past
            away = lo if away == hi else hi
        self.run_to(body, away, self.brain.pet.walk_speed * 2.3, dt)
        return self.t > self.duration


class Fetch(Special):
    """Chase the ball and kick it around."""
    name = "fetch"

    def __init__(self, brain, body, area, cursor_x, ball=None, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.ball = ball
        self.kicks = random.randint(2, 4)

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        ball = self.ball
        if ball is None or not ball.alive or self.t > 25:
            return True
        side = 1 if ball.center_x > body.x + body.w / 2 else -1
        x = ball.center_x - body.w / 2 - side * body.w * 0.3
        lo, hi = self.edges(body, area)
        if self.run_to(body, max(lo, min(hi, x)), self.brain.pet.walk_speed * 2.6, dt):
            self.brain.facing = side
            if ball.low(area):
                ball.kick(side)
                self.brain.events.append("kick")
                self.kicks -= 1
                return self.kicks <= 0
        return False


class Laser(Special):
    """The red dot! Sprint after it, and leap when it's close."""
    name = "laser"

    def __init__(self, brain, body, area, cursor_x, target: Callable[[], float] | None = None,
                 active: Callable[[], bool] | None = None, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.target = target or (lambda: cursor_x)
        self.active = active or (lambda: False)
        self.near = 0.0

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        if not self.active():
            return True
        lo, hi = self.edges(body, area)
        dot = self.target()
        if not self.run_to(body, max(lo, min(hi, dot - body.w / 2)), self.brain.pet.walk_speed * 3.4, dt):
            self.near = 0.0
            return False
        self.brain.facing = 1 if dot > body.x + body.w / 2 else -1
        self.near += dt
        if self.near > 0.35 and random.random() < 0.04:  # got it! (no, it moved)
            body.vx = self.brain.facing * 90
            body.vy = -random.uniform(380, 560)
            self.brain.squash = -0.2
            self.brain.events.append("pounce")
            self.brain.set_state(State.FALLING)
            return True
        return False


class Dance(Special):
    """Bust a move: bounce and sway on the spot for a few seconds."""
    name = "dance"
    pose = "dance"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.duration = random.uniform(3.0, 4.5)
        brain.events.append("dance")

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        self.brain.facing = 1 if int(self.t / 0.55) % 2 else -1
        return self.t > self.duration


class Phase(Special):
    """Ghost move: turn see-through and glide across the screen."""
    name = "phase"
    pose = "phase"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        lo, hi = self.edges(body, area)
        direction = 1 if hi - body.x > body.x - lo else -1
        self.target = max(lo, min(hi, body.x + direction * random.uniform(300, 650)))
        brain.events.append("wheee")

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        fade_in = min(1.0, self.t / 0.4)
        if self.run_to(body, self.target, self.brain.pet.walk_speed * 5, dt):
            self.value = max(0.0, self.value - dt * 2.5)  # solid again
            return self.value <= 0
        self.value = fade_in
        return False


class Haunt(Special):
    """Ghost move: float way up the screen, wobble about spookily, drift back down."""
    name = "haunt"
    pose = "float"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.height = 0.0
        self.peak = random.uniform(140, 280)
        self.stay = random.uniform(3.0, 5.0)
        self.phase = "up"
        brain.events.append("boo")

    def update(self, dt, body, area, cursor_x):
        self.t += dt
        lo, hi = self.edges(body, area)
        if self.phase == "up":
            self.height += 110 * dt
            if self.height >= self.peak:
                self.phase, self.t = "hover", 0.0
        elif self.phase == "hover":
            body.x = max(lo, min(hi, body.x + math.sin(self.t * 1.8) * 90 * dt))
            self.brain.facing = 1 if math.cos(self.t * 1.8) > 0 else -1
            if self.t > self.stay:
                self.phase = "down"
        else:
            self.height -= 80 * dt
            if self.height <= 0:
                body.y = body.floor(area)
                return True
        body.y = body.floor(area) - self.height
        return False


class Rocket(Special):
    """Robot move: crouch, fire the boot rockets, and blast off."""
    name = "rocket"
    pose = "crouch"

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        if self.t < 0.6:
            return False
        self.pose = "rocket"
        if self.t < 0.75:
            return False
        body.vy = -random.uniform(900, 1200)
        body.vx = self.brain.facing * random.uniform(80, 200)
        self.brain.squash = -0.25
        self.brain.events.append("rocket")
        self.brain.set_state(State.FALLING)
        return True


class Beg(Special):
    """Hungry: sit up with big pleading eyes, bounce, and stare at you until fed."""
    name = "beg"
    pose = "beg"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.duration = random.uniform(4.0, 6.0)
        brain.events.append("beg")

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        self.brain.facing = 1 if cursor_x > body.x + body.w / 2 else -1
        if int(self.t / 1.6) != int((self.t - dt) / 1.6):
            self.brain.events.append("rumble")  # tummy grumbles every so often
        return self.t > self.duration


class Sulk(Special):
    """Unhappy: turn away from you, slump, and sigh under a little rain cloud."""
    name = "sulk"
    pose = "sulk"

    def __init__(self, brain, body, area, cursor_x, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.duration = random.uniform(6.0, 9.0)
        brain.facing = -1 if cursor_x > body.x + body.w / 2 else 1  # back to you
        brain.events.append("sulk")

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        self.t += dt
        if int(self.t / 3.0) != int((self.t - dt) / 3.0):
            self.brain.events.append("sigh")
        return self.t > self.duration


class Dots(Special):
    """Dot Dash, the arcade mini-game: race to gobble the nearest dot."""
    name = "dots"

    def __init__(self, brain, body, area, cursor_x, target: Callable[[float], float | None] | None = None,
                 active: Callable[[], bool] | None = None, **kwargs):
        super().__init__(brain, body, area, cursor_x)
        self.target = target or (lambda x: None)
        self.active = active or (lambda: False)

    def update(self, dt, body, area, cursor_x):
        body.step(dt, area)
        if not self.active():
            return True
        dot = self.target(body.x + body.w / 2)
        if dot is None:
            return True
        lo, hi = self.edges(body, area)
        speed = self.brain.pet.walk_speed * 2.8 * self.brain.boost
        self.run_to(body, max(lo, min(hi, dot - body.w / 2)), speed, dt)
        return False


SPECIALS: dict[str, type[Special]] = {
    cls.name: cls for cls in (Zoomies, Pounce, TailChase, Roll, Pronk, Headbutt, BellySlide, Cling, Chase, Flee,
                              Fetch, Laser, Dance, Phase, Haunt, Rocket, Beg, Sulk, Dots)
}

# tricks a pet can be asked to do from the menu (the rest are games and reactions)
TRICKS = {
    "zoomies": "Zoomies", "pounce": "Pounce", "tail_chase": "Chase tail", "roll": "Roll",
    "pronk": "Pronk", "headbutt": "Headbutt", "belly_slide": "Belly slide", "cling": "Climb the edge",
    "dance": "Dance", "phase": "Phase", "haunt": "Haunt", "rocket": "Rocket jump",
}
