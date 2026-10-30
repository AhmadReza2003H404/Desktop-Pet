"""A small transparent, frameless, always-on-top window that hosts one pet."""

from __future__ import annotations

import datetime
import math
import random
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QMenu, QWidget

from core.behavior import Brain, Mode, is_night
from core.needs import Needs
from core import progress
from core.pet import Pet, PetView, State
from core.paths import LINUX
from core.physics import Body
from ui.effects import Effects
from ui.food import Food
from ui.menu import fill_menu

if TYPE_CHECKING:
    from ui.app import PetApp

FPS = 60
THROW_SAMPLE_SECONDS = 0.08  # how much recent drag movement counts towards a throw
DRAG_THRESHOLD = 6           # px the mouse must move before a click becomes a drag
STROKE_PER_HEART = 350       # px of rubbing the mouse over the pet per heart
BIG_THROW = 1400             # px/s


def _ordinal(n: int) -> str:
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


class PetWindow(QWidget):
    def __init__(self, app: PetApp, pet: Pet, name: str, size: str, needs: Needs,
                 mode: Mode = Mode.WANDER, x: float | None = None, love: float = 0.0, hat: str = "none",
                 adopted: datetime.date | None = None, celebrated: list[str] | None = None):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # no taskbar / alt-tab entry
            | Qt.X11BypassWindowManagerHint,  # GNOME won't reposition or stack it
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)  # hover events, for stroking

        self.app = app
        self.pet_name = name
        self.size_name = size
        self.needs = needs
        self.love = love
        self.adopted = adopted or datetime.date.today()
        self.celebrated = set(celebrated or [])  # occasions already partied for
        self.hat = hat if progress.hat_allowed(hat, love) else "none"
        self.effects = Effects()
        self.food: Food | None = None

        area = self._area()
        start_x = x if x is not None else area.center().x() - pet.width / 2
        self.body = Body(x=start_x, y=area.top(), w=pet.width, h=pet.height)
        self.brain: Brain | None = None
        self.set_pet(pet)
        self.brain.mode = mode

        self.start = time.monotonic()
        self.last_tick = self.start
        self.press_pos: QPointF | None = None
        self.dragging = False
        self.grab_offset = QPointF()
        self.drag_trail: list[tuple[float, QPointF]] = []
        self.last_hover: QPointF | None = None
        self.stroke = 0.0
        self.chat_in = random.uniform(20, 60)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000 // FPS)

    # --- setup ---------------------------------------------------------------

    def set_pet(self, pet: Pet):
        """Swap in a different animal or size; it drops in from where the old one stood."""
        bottom = self.body.y + self.body.h
        mode = self.brain.mode if self.brain else Mode.WANDER
        self.body.x += (self.body.w - pet.width) / 2
        self.pet = pet
        pet.hat = getattr(self, "hat", "none")
        self.brain = Brain(pet, self.needs)
        self.brain.mode = mode
        self.body.w, self.body.h = pet.width, pet.height
        self.body.y = bottom - pet.height - 40
        self.body.vx = self.body.vy = 0
        self.setFixedSize(pet.width, pet.height)
        self._sync_position()
        self.app.pet_changed(self)

    def show_all(self):
        self.show()
        self.effects.show()
        if self.food:
            self.food.show()

    def hide_all(self):
        self.hide()
        self.effects.hide()
        if self.food:
            self.food.hide()

    def close_all(self):
        self.timer.stop()
        for w in (self.effects, self.food):
            if w:
                w.close()
        self.close()

    def _area(self):
        screen = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _sync_position(self):
        self.move(round(self.body.x), round(self.body.y))

    # --- actions (menu, tray) -----------------------------------------------

    def say(self, kind: str):
        options = self.pet.lines.get(kind) or Pet.lines.get(kind)
        if options:
            self.effects.say(random.choice(options))
            if random.random() < 0.6:
                self.app.sounds.play(self.pet.voice)

    @property
    def level(self) -> int:
        return progress.level_for(self.love)

    def add_love(self, kind: str):
        before = self.level
        self.love += progress.LOVE.get(kind, 0.0)
        if self.level > before:
            unlocked = progress.unlocked_at(self.level)
            self.effects.celebrate()
            self.effects.say(f"Level {self.level}! ♥" + (f" New hat: {unlocked[0]}" if unlocked else ""), 4.5,
                             important=True)
            self.app.sounds.play("boing")
            self.app.pet_changed(self)

    def set_hat(self, hat: str):
        if progress.hat_allowed(hat, self.love):
            self.hat = self.pet.hat = hat
            self.effects.heart(1)
            self.app.pet_changed(self)

    def come_here(self):
        """Drop in from the top of the screen above the mouse."""
        area = self._area()
        cursor = QCursor.pos()
        self.brain.grab()
        self.body.x = max(area.left(), min(area.right() + 1 - self.body.w, cursor.x() - self.body.w / 2))
        self.body.y = area.top()
        self.body.vx = self.body.vy = 0
        self.brain.release()
        self._sync_position()
        if not self.isVisible():
            self.show_all()

    def remind(self, text: str):
        """Break reminder: a long bubble, a little noise, and a trick to catch your eye."""
        self.effects.say(text, 9.0, important=True)
        self.effects.heart(2)
        self.app.sounds.play(self.pet.voice)
        if self.brain.grounded and self.brain.state != State.SLEEP:
            self.trick()

    def days_together(self, today: datetime.date | None = None) -> int:
        return ((today or datetime.date.today()) - self.adopted).days

    def occasion(self, today: datetime.date | None = None) -> tuple[str, str] | None:
        """Today's reason to party, as (unique key, message), if any."""
        today = today or datetime.date.today()
        days = self.days_together(today)
        years = today.year - self.adopted.year
        if days > 0 and years > 0 and (today.month, today.day) == (self.adopted.month, self.adopted.day):
            return f"birthday-{today.year}", f"It's my {years}{_ordinal(years)} birthday! 🎂"
        milestones = {7: "one week", 30: "one month", 100: "100 days", 200: "200 days", 500: "500 days"}
        if days in milestones:
            return f"days-{days}", f"We've been friends for {milestones[days]}! 🎉"
        return None

    def celebrate_today(self) -> bool:
        found = self.occasion()
        if not found or found[0] in self.celebrated:
            return False
        key, message = found
        self.celebrated.add(key)
        self.pet.hat = "party"  # party hat for the rest of this session; your chosen hat comes back later
        self.effects.celebrate(60)
        self.effects.heart(4)
        self.effects.say(message, 8.0, important=True)
        self.app.sounds.play(self.pet.voice)
        self.love += 5
        return True

    def welcome_back(self, away_seconds: float):
        """You came back to the computer."""
        if not self.isVisible():
            return
        self.brain.petted()  # wakes up and wiggles
        hours = away_seconds / 3600
        if hours >= 1:
            text = f"you were gone {hours:.0f} hour{'s' if hours >= 1.5 else ''}! I missed you ♥"
        else:
            text = random.choice(self.pet.lines.get("welcome") or Pet.lines["welcome"])
        self.effects.say(text, 5.0, important=True)
        self.effects.heart(3)
        self.app.sounds.play(self.pet.voice)

    def take_photo(self):
        from ui import photo
        path = photo.save([self])
        self.app.sounds.play("shutter")
        self.effects.say(f"📸 saved to Pictures/{path.parent.name}", 4.0, important=True)
        self.effects.heart(2)
        return path

    def mood(self) -> str:
        if self.needs.hungry:
            return "hungry"
        if self.needs.tired:
            return "tired"
        if self.needs.sad:
            return "sad"
        return ""

    def trick(self):
        """Menu: do one of this animal's tricks (or zoomies if none fit right now)."""
        area = self._area()
        for name in random.sample(self.pet.specials, len(self.pet.specials)) + ["zoomies"]:
            if self.brain.start_special(name, self.body, area):
                return

    def play_ball(self):
        self.app.throw_ball(self)

    def pet_it(self):
        was_asleep = self.brain.state == State.SLEEP
        self.brain.petted()
        if self.brain.state != State.HAPPY:
            return
        self.needs.cheer(6)
        self.effects.heart(3)
        self.app.sounds.play("pop", 0.6)
        self.add_love("pet")
        if not was_asleep and random.random() < 0.4:
            self.say("pet")

    def feed(self):
        if self.food:
            return
        area = self._area()
        x = self.body.x + self.body.w / 2 + random.uniform(-260, 260) - Food.W / 2
        x = max(area.left(), min(area.right() + 1 - Food.W, x))
        self.food = Food(self.pet.favorite_food, x, area)
        if self.isVisible():
            self.food.show()

    def command(self, state: State):
        self.brain.command(state, self.body, self._area())

    def sleep_in_corner(self, side: int):
        self.brain.sleep_in_corner(side, self.body, self._area())

    def set_mode(self, mode: Mode):
        self.brain.mode = mode
        if mode == Mode.STAY and self.brain.state == State.WALK and self.brain.goal is None:
            self.command(State.IDLE)

    # --- frame ---------------------------------------------------------------

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.05)  # don't explode after a stall
        self.last_tick = now
        if not self.isVisible():
            return

        area = self._area()
        self.brain.update(dt, self.body, area, QCursor.pos().x())
        for event in self.brain.pop_events():  # before food, so a finished bowl is gone
            self._on_event(event)
        self._tend_food(dt, area)
        self._tend_ball(area)
        self._tend_laser(area)
        self._chatter(dt)
        self.stroke = max(0.0, self.stroke - 120 * dt)

        if self.brain.state != State.DRAGGED:
            self._sync_position()
        if LINUX:  # X11 bypass windows need a nudge; Windows keeps "on top" windows on top
            self.raise_()
        self.effects.step(dt)
        self.effects.place(self.geometry())
        if LINUX:
            self.effects.raise_()
        self.effects.update()
        self.update()

    def _tend_food(self, dt: float, area):
        food = self.food
        if not food:
            return
        food.step(dt, area)
        if self.brain.state == State.EAT:
            food.set_bites(min(3, int(self.brain.state_time / 0.9)))
        elif food.landed and self.brain.grounded and not self.brain.heading_to(State.EAT):
            # stand beside the bowl, facing it, mouth over it
            side = 1 if food.center_x >= self.body.x + self.body.w / 2 else -1
            target = food.center_x - self.body.w / 2 - side * self.body.w * 0.3
            self.brain.walk_to(target, State.EAT, 3.0, self.body, area)
            self.brain.facing = side

    def _tend_laser(self, area):
        laser = self.app.laser
        if (laser is None or self.brain.doing("laser") or self.brain.mode == Mode.STAY
                or self.brain.state not in (State.IDLE, State.SIT, State.WALK, State.HAPPY)):
            return
        if self.brain.start_special("laser", self.body, area, target=lambda: laser.x,
                                    active=lambda: self.app.laser is laser):
            if random.random() < 0.15:
                self.say("laser")

    def _tend_ball(self, area):
        ball = self.app.ball
        if (ball is None or not ball.alive or self.food or self.brain.mode != Mode.WANDER
                or self.needs.tired or self.brain.state not in (State.IDLE, State.SIT, State.WALK)
                or self.brain.goal is not None):
            return
        if self.brain.start_special("fetch", self.body, area, ball=ball):
            self.needs.cheer(4)

    def _on_event(self, event: str):
        sounds = self.app.sounds
        if event == "ate":
            sounds.play("munch")
            self.needs.fed()
            self.add_love("fed")
            self.effects.heart(2)
            self.say("fed")
            if self.food:
                self.food.close()
                self.food = None
        elif event in ("woke", "ouch", "dizzy", "wheee"):
            self.say(event)
        elif event == "bonk":
            sounds.play("bonk")
            self.say("bonk")
        elif event == "pounce":
            sounds.play("boing", 0.7)
        elif event == "kick":
            sounds.play("pop", 0.8)
            self.needs.cheer(3)
            self.add_love("kick")

    def _chatter(self, dt: float):
        self.chat_in -= dt
        if self.chat_in > 0:
            return
        self.chat_in = random.uniform(40, 120)
        if self.brain.state in (State.SLEEP, State.DRAGGED, State.FALLING) or self.effects.bubble:
            return
        if self.needs.hungry:
            self.say("hungry")
        elif is_night() and random.random() < 0.5:
            self.say("night")
        elif self.needs.tired:
            self.say("tired")
        elif self.needs.sad:
            self.say("sad")
        elif random.random() < 0.5:
            self.say("idle")

    def _look(self) -> tuple[float, float]:
        centre = self.geometry().center()
        cursor = QCursor.pos()
        dx, dy = cursor.x() - centre.x(), cursor.y() - (centre.y() - 10)
        dist = math.hypot(dx, dy)
        if dist < 1:
            return 0.0, 0.0
        strength = min(1.0, dist / 150)
        return dx / dist * strength, dy / dist * strength

    def view(self) -> PetView:
        return PetView(
            state=self.brain.state,
            t=time.monotonic() - self.start,
            state_time=self.brain.state_time,
            facing=self.brain.facing,
            squash=self.brain.squash,
            look=self._look(),
            walk_phase=self.brain.walk_phase,
            blink=self.brain.blinking,
            special=self.brain.special.pose if self.brain.special else "",
            special_value=self.brain.special.value if self.brain.special else 0.0,
            mood=self.mood(),
        )

    def paintEvent(self, _):
        p = QPainter(self)
        self.pet.draw(p, self.view())
        p.end()

    # --- mouse: click = pet, drag = carry/throw, rub = stroke, double = jump --

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.press_pos = e.globalPosition()
            self.grab_offset = e.position()
            self.drag_trail = [(time.monotonic(), e.globalPosition())]
        elif e.button() == Qt.RightButton:
            menu = QMenu()
            fill_menu(menu, self, self.app)
            menu.addSeparator()
            self.app.fill_app_menu(menu)
            menu.exec(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        pos = e.globalPosition()
        if self.press_pos is not None and e.buttons() & Qt.LeftButton:
            if not self.dragging:
                if (pos - self.press_pos).manhattanLength() < DRAG_THRESHOLD:
                    return
                self.dragging = True
                self.brain.grab()
                self.setCursor(Qt.ClosedHandCursor)
            now = time.monotonic()
            self.drag_trail.append((now, pos))
            self.drag_trail = [(t, p) for t, p in self.drag_trail if now - t <= THROW_SAMPLE_SECONDS]
            self.body.x = pos.x() - self.grab_offset.x()
            self.body.y = pos.y() - self.grab_offset.y()
            self._sync_position()
            return

        # hovering with no button held: rubbing the pet
        if self.last_hover is not None:
            self.stroke += (pos - self.last_hover).manhattanLength()
        self.last_hover = pos
        if self.stroke >= STROKE_PER_HEART:
            self.stroke = 0
            reacted = self.brain.stroked()
            self.needs.cheer(2)
            self.effects.heart(1)
            self.add_love("stroke")
            if reacted and random.random() < 0.25:
                self.say("pet")

    def leaveEvent(self, _):
        self.last_hover = None

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.dragging:
            (t0, p0), (t1, p1) = self.drag_trail[0], self.drag_trail[-1]
            span = max(t1 - t0, 1e-3)
            self.body.vx = (p1.x() - p0.x()) / span
            self.body.vy = (p1.y() - p0.y()) / span
            self.brain.release()
            self.unsetCursor()
            if math.hypot(self.body.vx, self.body.vy) > BIG_THROW:
                self.app.sounds.play("whoosh", 0.8)
                self.say("thrown")
        elif self.press_pos is not None:
            self.pet_it()
        self.dragging = False
        self.press_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton and self.brain.grounded:
            self.brain.jump(self.body)
            self.app.sounds.play("boing", 0.7)
