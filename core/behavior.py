"""Decides what the pet does next: wander, sit, nap, eat, follow you around."""

import random
import time
from enum import Enum, auto

from PySide6.QtCore import QRect

from core.needs import Needs
from core.pet import Pet, State
from core.physics import Body
from core.specials import SPECIALS, TRICKS, Special

RESTING = (State.IDLE, State.SIT, State.SLEEP, State.HAPPY, State.EAT)
GROUNDED = RESTING + (State.WALK, State.SPECIAL)
FOREVER = 1e9      # "until woken"
HARD_LANDING = 1500.0
FOLLOW_GAP = 70.0  # how close it walks up to the cursor
RUN_DISTANCE = 350.0


def is_night() -> bool:
    hour = time.localtime().tm_hour
    return hour >= 23 or hour < 6


class Mode(Enum):
    WANDER = auto()
    STAY = auto()
    FOLLOW = auto()


class Brain:
    def __init__(self, pet: Pet, needs: Needs):
        self.pet = pet
        self.needs = needs
        self.mode = Mode.WANDER
        self.state = State.FALLING
        self.state_time = 0.0
        self.timer = 0.0         # seconds left in the current state
        self.target_x = 0.0
        self.goal: tuple[State, float] | None = None  # what to do on reaching target_x
        self.speed_mult = 1.0
        self.facing = 1
        self.walk_phase = 0.0
        self.squash = 0.0
        self.blink_in = random.uniform(2, 5)
        self.blink_left = 0.0
        self.events: list[str] = []  # for the window: "ate", "woke", "ouch"
        self.landed_once = False     # the drop-in when the app starts isn't worth an "ouch"
        self.special: Special | None = None
        self.cursor_x = 0.0
        self.boost = 1.0             # power-ups in the arcade game make it zoom

    @property
    def blinking(self) -> bool:
        return self.blink_left > 0

    @property
    def grounded(self) -> bool:
        return self.state in GROUNDED

    def pop_events(self) -> list[str]:
        events, self.events = self.events, []
        return events

    def _set(self, state: State, duration: float = 0.0):
        if state != self.state:
            self.state_time = 0.0
        if state != State.SPECIAL:
            self.special = None
        self.state = state
        self.timer = duration

    set_state = _set  # for tricks that hand over to normal physics (e.g. a pounce leap)

    def start_special(self, name: str, body: Body, area: QRect, **kwargs) -> bool:
        """Start a trick by name. Returns False if it can't be done right now."""
        cls = SPECIALS.get(name)
        if cls is None or not self.grounded or not cls.possible(self, body, area, self.cursor_x):
            return False
        self._wake()
        self.goal = None
        self.speed_mult = 1.0
        self._set(State.SPECIAL)
        self.special = cls(self, body, area, self.cursor_x, **kwargs)
        if name in TRICKS:
            self.events.append("trick")
        return True

    def doing(self, name: str) -> bool:
        return self.special is not None and self.special.name == name

    def _wake(self):
        if self.state == State.SLEEP:
            self.events.append("woke")

    # --- things that happen to the pet ---------------------------------------

    def grab(self):
        self._wake()
        self.goal = None
        self._set(State.DRAGGED)

    def release(self):
        self._set(State.FALLING)

    def jump(self, body: Body):
        if not self.grounded:
            return
        self._wake()
        self.goal = None
        body.vy = -780.0
        body.vx = self.facing * 120.0
        self.squash = -0.2
        self._set(State.FALLING)

    def petted(self):
        """A click. Wakes it up if it was asleep."""
        if not self.grounded or self.state == State.EAT:
            return
        self._wake()
        self.goal = None
        self._set(State.HAPPY, 2.5)

    def stroked(self) -> bool:
        """Mouse rubbing over it. Sleepers stay asleep. Returns True if it reacted."""
        if self.state in (State.SLEEP, State.EAT) or not self.grounded:
            return False
        self.goal = None
        self._set(State.HAPPY, max(self.timer, 1.8) if self.state == State.HAPPY else 1.8)
        return True

    # --- orders --------------------------------------------------------------

    def walk_to(self, x: float, then: State, duration: float, body: Body, area: QRect):
        lo, hi = area.left(), area.right() + 1 - body.w
        self.target_x = max(lo, min(hi, x))
        self.goal = (then, duration)
        self._wake()
        if abs(self.target_x - body.x) > 1:
            self.facing = 1 if self.target_x > body.x else -1
        self._set(State.WALK, 30.0)

    def heading_to(self, state: State) -> bool:
        return self.goal is not None and self.goal[0] == state

    def command(self, state: State, body: Body, area: QRect):
        """Menu orders. Ignored mid-air."""
        if not self.grounded:
            return
        self.goal = None
        if state == State.WALK:
            self._wander(body, area)
        elif state == State.SLEEP:
            self._set(State.SLEEP, FOREVER)
        else:
            self._wake()
            self._set(state, 30.0)

    def sleep_in_corner(self, side: int, body: Body, area: QRect):
        if not self.grounded:
            return
        x = area.left() if side < 0 else area.right() + 1 - body.w
        self.walk_to(x, State.SLEEP, FOREVER, body, area)

    # --- the main loop -------------------------------------------------------

    def update(self, dt: float, body: Body, area: QRect, cursor_x: float):
        self.state_time += dt
        self.cursor_x = cursor_x
        self.squash *= max(0.0, 1 - 10 * dt)  # springs back to 0
        self._update_blink(dt)
        self.needs.tick(dt, self.state)

        if self.state == State.DRAGGED:
            self.walk_phase += dt * 25  # legs flail
            return

        if self.state == State.FALLING:
            impact = body.step(dt, area)
            if impact > 300:
                self.squash = min(0.45, impact / 4000)
            if impact > HARD_LANDING and self.landed_once:
                self.events.append("ouch")
            if body.on_ground(area) and body.vy == 0 and abs(body.vx) < 20:
                self.landed_once = True
                self._rest(State.IDLE)
            return

        if self.state == State.SPECIAL:
            special = self.special
            if special.update(dt, body, area, cursor_x) and self.state == State.SPECIAL:
                self._rest(State.IDLE)
            return

        # on the ground: keep gravity/edges honest (e.g. screen resized)
        body.step(dt, area)
        self.timer -= dt

        if self.mode == Mode.FOLLOW and self.goal is None and self.state in (State.IDLE, State.WALK, State.SIT):
            self._follow(body, cursor_x)

        if self.state == State.WALK:
            self._walk(dt, body)
        elif self.state == State.SLEEP and self.timer <= 0 and self.needs.energy < 60:
            self.timer = 5.0  # still sleepy, keep snoozing
        elif self.state in RESTING and self.timer <= 0:
            if self.state == State.EAT:
                self.events.append("ate")
            self._wake()
            self._choose_next(body, area)

    def _walk(self, dt: float, body: Body):
        dx = self.target_x - body.x
        step = self.pet.walk_speed * self.speed_mult * dt
        if abs(dx) <= step:
            body.x = self.target_x
            if self.goal:
                state, duration = self.goal
                self.goal = None
                self._set(state, duration)
                self.walk_phase = 0.0
            elif self.mode != Mode.FOLLOW:
                self._rest(State.IDLE)
        elif self.timer <= 0:
            self.goal = None
            self._rest(State.IDLE)
        else:
            self.facing = 1 if dx > 0 else -1
            body.x += step * self.facing
            self.walk_phase += dt * 10 * self.speed_mult

    def _follow(self, body: Body, cursor_x: float):
        dx = cursor_x - (body.x + body.w / 2)
        if abs(dx) > FOLLOW_GAP + (40 if self.state != State.WALK else 0):  # hysteresis
            self.target_x = cursor_x - body.w / 2 - (FOLLOW_GAP * 0.6 if dx > 0 else -FOLLOW_GAP * 0.6)
            self.speed_mult = 2.4 if abs(dx) > RUN_DISTANCE else 1.3
            if self.state != State.WALK:
                self._set(State.WALK, 30.0)
            self.timer = 30.0
        elif self.state == State.WALK:
            self.facing = 1 if dx > 0 else -1
            self._rest(State.IDLE)

    def _update_blink(self, dt: float):
        if self.blink_left > 0:
            self.blink_left -= dt
            return
        self.blink_in -= dt
        if self.blink_in <= 0:
            self.blink_left = 0.14
            # sometimes a quick double blink
            self.blink_in = 0.25 if random.random() < 0.2 else random.uniform(2, 6)

    def _choose_next(self, body: Body, area: QRect):
        weights = dict(self.pet.idle_weights)
        if self.pet.specials and self.mode == Mode.WANDER and not self.needs.tired:
            weights[State.SPECIAL] = self.pet.special_weight
        if self.mode != Mode.WANDER:
            weights.pop(State.WALK, None)  # staying put, or the cursor decides
        if self.needs.tired:
            weights[State.SLEEP] = weights.get(State.SLEEP, 1) * 6
        if is_night():
            weights[State.SLEEP] = weights.get(State.SLEEP, 1) * 3
        if self.needs.sad and State.WALK in weights:
            weights[State.WALK] *= 0.5
        choice = random.choices(list(weights), list(weights.values()))[0]
        if choice == State.SPECIAL:
            tricks = random.sample(self.pet.specials, len(self.pet.specials))
            if not any(self.start_special(name, body, area) for name in tricks):
                self._rest(State.IDLE)
        elif choice == State.WALK:
            self._wander(body, area)
        else:
            self._rest(choice)

    def _rest(self, state: State):
        lo, hi = self.pet.durations.get(state, (2.0, 4.0))
        self._set(state, random.uniform(lo, hi))
        self.walk_phase = 0.0
        self.speed_mult = 1.0
        if state == State.IDLE and self.mode != Mode.FOLLOW and random.random() < 0.3:
            self.facing = -self.facing  # look around

    def _wander(self, body: Body, area: QRect):
        lo, hi = area.left(), area.right() + 1 - body.w
        distance = random.uniform(80, 500) * random.choice((-1, 1))
        self.target_x = max(lo, min(hi, body.x + distance))
        if abs(self.target_x - body.x) < 20:  # pinned against an edge: go the other way
            self.target_x = max(lo, min(hi, body.x - distance))
        self.speed_mult = 1.0
        self._set(State.WALK, 15.0)  # give up if somehow stuck
