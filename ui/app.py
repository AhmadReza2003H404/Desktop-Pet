"""Owns the pet windows, the ball, the tray icon, sounds, and saving/loading."""

import datetime
import random
import time
from itertools import combinations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QActionGroup, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core import save
from core.achievements import ACHIEVEMENTS, Achievement, Tracker
from core.behavior import Mode
from core.needs import Needs
from core.pet import Pet, State
from ui import system
from ui.arcade import DotDash
from ui.ball import Ball
from ui.laser import Laser
from ui.menu import SIZES
from ui.pet_window import PetWindow
from ui.sound import Sounds
from ui.tray import Tray
from ui.weather import KINDS as WEATHER, Weather, resolve as resolve_weather

AUTOSAVE_MS = 30_000
MAX_PETS = 10
GREET_DISTANCE = 150  # px between two pets' centres
GREET_COOLDOWN = 25.0
CHASE_CHANCE = 0.02   # per second, when two pets are up for it
AWAY_AFTER = 5 * 60   # seconds without keyboard/mouse before the pets nap
LASER_SECONDS = 45
BREAK_LINES = [
    "time for a break! stand up and stretch 🙆",
    "drink some water 💧",
    "rest your eyes: look far away for 20 seconds 👀",
    "roll your shoulders, you've been sitting a while",
    "break time! wiggle a bit 🕺",
]


class PetApp(QObject):
    def __init__(self, registry: dict[str, type[Pet]], species: str | None = None, variant: str | None = None):
        super().__init__()
        self.registry = registry
        self.windows: list[PetWindow] = []
        self.ball: Ball | None = None
        self.panel = None  # Pet House window, made on first open
        self.laser: Laser | None = None
        self.laser_until = 0.0
        self.arcade: DotDash | None = None
        self.weather: Weather | None = None
        self.away_since: float | None = None  # wall-clock time you left the computer
        self.ticks = 0
        self.max_pets = MAX_PETS
        self.last_greet = 0.0
        self.tray = Tray(self) if QSystemTrayIcon.isSystemTrayAvailable() else None

        state = save.load() or {}
        settings = state.get("settings", {})
        self.sounds = Sounds(enabled=settings.get("sounds", True))
        self.breaks_on = bool(settings.get("breaks", False))
        self.break_minutes = int(settings.get("break_minutes", 50))
        self.next_break = time.monotonic() + self.break_minutes * 60
        self.achievements = Tracker.from_dict(state.get("achievements"))
        self.weather_kind = settings.get("weather", "off") if settings.get("weather") in WEATHER else "off"
        records = state.get("pets", [])
        away = time.time() - state.get("saved_at", time.time())
        if species:  # command line wins, but keep the old pet's name and needs
            first = records[0] if records else {}
            if first.get("species") != species:
                first = {k: v for k, v in first.items() if k in ("needs", "size", "mode", "x")}
            records = [{**first, "species": species, "variant": variant}] + records[1:]
        for record in records or [{"species": "cat"}]:
            self.windows.append(self._spawn(record, away))

        for win in self.windows:
            win.show_all()
        self._count_family()
        if self.weather_kind != "off":
            self._start_weather()
        if self.tray:
            self.tray.refresh()
            self.tray.show()

        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self.save)
        self.autosave.start(AUTOSAVE_MS)
        self.social = QTimer(self)
        self.social.timeout.connect(self._socialise)
        self.social.start(1000)
        self.ball_timer = QTimer(self)
        self.ball_timer.timeout.connect(self._step_ball)
        self.last_ball_tick = time.monotonic()
        QApplication.instance().aboutToQuit.connect(self.save)

    # --- pets ----------------------------------------------------------------

    def _spawn(self, record: dict, away: float = 0) -> PetWindow:
        cls = self.registry.get(record.get("species")) or next(iter(self.registry.values()))
        size = record.get("size") if record.get("size") in SIZES else "Medium"
        variant = record.get("variant") if record.get("variant") in cls.variants else None
        pet = cls(variant, SIZES[size])
        needs = Needs.from_dict(record.get("needs"))
        needs.catch_up(away)
        mode = Mode.__members__.get(record.get("mode", ""), Mode.WANDER)
        name = record.get("name") or self._fresh_name(cls)
        love = float(record.get("love", 0.0))
        try:
            adopted = datetime.date.fromisoformat(record["adopted"])
        except (KeyError, TypeError, ValueError):
            adopted = None
        return PetWindow(self, pet, name, size, needs, mode, record.get("x"), love, record.get("hat", "none"),
                         adopted, record.get("celebrated"))

    def _fresh_name(self, cls: type[Pet]) -> str:
        taken = {w.pet_name for w in self.windows}
        free = [n for n in cls.default_names if n not in taken]
        return random.choice(free or cls.default_names)

    def add_pet(self, cls: type[Pet]):
        if len(self.windows) >= MAX_PETS:
            return
        area = QGuiApplication.primaryScreen().availableGeometry()
        record = {"species": cls.species, "variant": random.choice(cls.variants),
                  "x": random.uniform(area.left(), area.right() - cls.width)}
        win = self._spawn(record)
        self.windows.append(win)
        win.show_all()
        win.say("friend")
        self._count_family()
        self.save()
        if self.panel:
            self.panel.rebuild()

    def remove_pet(self, win: PetWindow):
        if len(self.windows) <= 1:
            return
        self.windows.remove(win)
        win.close_all()
        self.save()
        if self.panel:
            self.panel.rebuild()

    def pet_changed(self, win: PetWindow):
        if self.tray and self.windows and win is self.windows[0]:
            self.tray.refresh()
        if self.panel:
            self.panel.pet_changed(win)

    def open_panel(self):
        from ui.panel import PetHouse  # only built when first needed
        if self.panel is None:
            self.panel = PetHouse(self)
        self.panel.rebuild()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def show_all(self):
        for win in self.windows:
            win.show_all()
        if self.ball:
            self.ball.show()

    def toggle_hidden(self):
        if not any(w.isVisible() for w in self.windows):
            return self.show_all()
        for win in self.windows:
            win.hide_all()
        if self.ball:
            self.ball.hide()

    # --- pets together -------------------------------------------------------

    def _socialise(self):
        """Once a second: nearby pets greet each other; now and then one chases another."""
        self.ticks += 1
        self._maybe_remind()
        if self.laser and time.monotonic() > self.laser_until:
            self.toggle_laser()
        if self.ticks % 5 == 0:
            self._check_away()
        if self.ticks % 600 == 2:  # every 10 minutes, and right after start
            self._check_occasions()
        free = [w for w in self.windows
                if w.isVisible() and w.brain.mode == Mode.WANDER and w.brain.goal is None
                and w.brain.state in (State.IDLE, State.SIT, State.WALK)]
        if len(free) < 2:
            return
        now = time.monotonic()
        if now - self.last_greet > GREET_COOLDOWN:
            for a, b in combinations(free, 2):
                if abs(self._centre(a) - self._centre(b)) < GREET_DISTANCE and random.random() < 0.3:
                    self._greet(a, b)
                    self.last_greet = now
                    return
        if random.random() < CHASE_CHANCE:
            a, b = random.sample(free, 2)
            area = a._area()
            if a.brain.start_special("chase", a.body, area, target=lambda: self._centre(b)):
                b.brain.start_special("flee", b.body, b._area(), chaser=lambda: self._centre(a))
                a.say("friend")

    def _maybe_remind(self):
        if not self.breaks_on or time.monotonic() < self.next_break:
            return
        self.next_break = time.monotonic() + self.break_minutes * 60
        shown = [w for w in self.windows if w.isVisible()]
        if shown:
            random.choice(shown).remind(random.choice(BREAK_LINES))

    def _check_away(self):
        idle = system.idle_seconds()
        if idle is None:
            return
        if idle > AWAY_AFTER:
            if self.away_since is None:
                self.away_since = time.time() - idle
            for win in self.windows:  # every check, so a pet that was mid-air also tucks in
                if win.brain.state != State.SLEEP and win.brain.grounded:
                    win.command(State.SLEEP)
        elif self.away_since is not None and idle < 5:
            gone = time.time() - self.away_since
            self.away_since = None
            for win in self.windows:
                win.welcome_back(gone)

    def _check_occasions(self):
        if any([win.celebrate_today() for win in self.windows]):
            self.sounds.play("boing")
            self.save()

    def toggle_laser(self):
        if self.laser:
            self.laser.stop()
            self.laser = None
            return
        self.laser = Laser()
        self.laser.show()
        self.laser_until = time.monotonic() + LASER_SECONDS

    def group_photo(self):
        from ui import photo
        shown = [w for w in self.windows]
        path = photo.save(shown)
        self.sounds.play("shutter")
        self.record("photos")
        for win in shown:
            win.effects.heart(2)
        shown[0].effects.say(f"📸 group photo saved to Pictures/{path.parent.name}", 4.0, important=True)
        return path

    def set_breaks(self, on: bool, minutes: int):
        self.breaks_on, self.break_minutes = on, minutes
        self.next_break = time.monotonic() + minutes * 60
        self.save()

    def set_sounds(self, on: bool):
        self.sounds.enabled = on
        self.save()

    @staticmethod
    def _centre(win: PetWindow) -> float:
        return win.body.x + win.body.w / 2

    def _greet(self, a: PetWindow, b: PetWindow):
        ghosts = [w for w in (a, b) if w.pet.species == "ghost"]
        if ghosts and random.random() < 0.6:
            ghost = ghosts[0]
            victim = b if ghost is a else a
            self._boo(ghost, victim)
            return
        for me, other in ((a, b), (b, a)):
            me.brain.petted()
            me.brain.facing = 1 if self._centre(other) > self._centre(me) else -1
            me.effects.heart(2)
            me.needs.cheer(5)
            me.add_love("greet")
        a.say("friend")

    def _boo(self, ghost: PetWindow, victim: PetWindow):
        """A ghost sneaks up on a friend and spooks them. They jump out of their skin."""
        ghost.brain.facing = 1 if self._centre(victim) > self._centre(ghost) else -1
        ghost.brain.petted()
        ghost.say("boo")
        ghost.effects.music(2, "✦✧")
        ghost.add_love("greet")
        if victim.pet.species == "ghost":
            victim.say("boo")  # you can't spook a ghost
            victim.effects.heart(1)
            return
        victim.brain.jump(victim.body)
        victim.say("spooked")
        self.sounds.play("boing", 0.8)
        self.record("boos")

    # --- arcade, weather, achievements ---------------------------------------

    def toggle_arcade(self):
        if self.arcade:
            game, self.arcade = self.arcade, None
            game.stop()
            return
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.arcade = DotDash(area, self._arcade_finished)
        self.arcade.show()
        self.sounds.play("powerup")
        for win in self.windows:
            if win.isVisible() and win.brain.state == State.SLEEP:
                win.command(State.IDLE)  # nobody sleeps through the arcade
        self.record("games")

    def _arcade_finished(self, scores: dict[int, tuple[str, int]]):
        self.arcade = None
        if self.panel:
            self.panel.arcade.setChecked(False)
        if not scores:
            return
        best = max(score for _, score in scores.values())
        self.best("best_score", best)
        for win in self.windows:
            name, score = scores.get(id(win), (win.pet_name, 0))
            if score == best and best > 0:
                win.effects.celebrate(50)
                win.effects.say(f"I WON with {score} points! 🏆", 5.0, important=True)
                win.love += 3
                win.brain.start_special("dance", win.body, win._area())
            elif score:
                win.say("lost")
        self.sounds.play("fanfare")
        self.save()

    def set_weather(self, kind: str):
        self.weather_kind = kind
        if self.weather:
            self.weather.stop()
            self.weather = None
        if kind != "off":
            self._start_weather()
            self.record("weather")
            shown = [w for w in self.windows if w.isVisible()]
            if shown:
                random.choice(shown).say(resolve_weather(kind))
        self.save()

    def _start_weather(self):
        if resolve_weather(self.weather_kind) == "off":
            return
        self.weather = Weather(self.weather_kind)
        self.weather.show()

    def record(self, stat: str, amount: int = 1):
        self._announce(self.achievements.bump(stat, amount))

    def best(self, stat: str, value: int):
        self._announce(self.achievements.at_least(stat, value))

    def _count_family(self):
        self.best("pets_at_once", len(self.windows))
        self.best("kinds_at_once", len({w.pet.species for w in self.windows}))

    def _announce(self, unlocked: list[Achievement]):
        if not unlocked:
            return
        shown = [w for w in self.windows if w.isVisible()] or self.windows
        if not shown:
            return
        win = random.choice(shown)
        a = unlocked[0]
        win.effects.celebrate(50)
        win.effects.say(f"{a.icon} Achievement unlocked: {a.title}!", 6.0, important=True)
        self.sounds.play("fanfare")
        if self.tray and self.tray.isVisible():
            self.tray.showMessage("Achievement unlocked!", f"{a.icon} {a.title}: {a.description}",
                                  QSystemTrayIcon.Information, 5000)

    # --- the ball ------------------------------------------------------------

    def throw_ball(self, win: PetWindow):
        x = win.body.x + win.body.w / 2 - Ball.SIZE / 2
        y = win.body.y + win.body.h * 0.3
        if self.ball is None or not self.ball.alive:
            self.ball = Ball(x, y, self.remove_ball)
            if win.isVisible():
                self.ball.show()
            self.last_ball_tick = time.monotonic()
            self.ball_timer.start(16)
        else:
            self.ball.body.x, self.ball.body.y = x, y
        self.ball.throw(win.brain.facing * random.uniform(400, 800), -random.uniform(500, 800))
        self.sounds.play("boing", 0.6)

    def _step_ball(self):
        now = time.monotonic()
        dt = min(now - self.last_ball_tick, 0.05)
        self.last_ball_tick = now
        ball = self.ball
        if ball is None:
            return self.ball_timer.stop()
        area = (QGuiApplication.screenAt(ball.geometry().center()) or QGuiApplication.primaryScreen()).availableGeometry()
        ball.step(dt, area)
        if not ball.alive:
            self.remove_ball()

    def remove_ball(self):
        if self.ball is None:
            return
        self.ball.alive = False  # pets playing fetch notice and stop
        self.ball.close()
        self.ball = None
        self.ball_timer.stop()

    # --- app-wide menu -------------------------------------------------------

    def fill_app_menu(self, menu: QMenu):
        menu.addAction("🏠 Open Pet House…", self.open_panel)
        laser = menu.addAction("🔴 Laser pointer", self.toggle_laser)
        laser.setCheckable(True)
        laser.setChecked(self.laser is not None)
        arcade = menu.addAction("👾 Dot Dash (arcade game)", self.toggle_arcade)
        arcade.setCheckable(True)
        arcade.setChecked(self.arcade is not None)
        weather = menu.addMenu("🌦 Weather")
        group = QActionGroup(weather)
        for kind, label in WEATHER.items():
            action = weather.addAction(label, lambda k=kind: self.set_weather(k))
            action.setCheckable(True)
            action.setChecked(self.weather_kind == kind)
            group.addAction(action)
        done = len(self.achievements.unlocked)
        trophies = menu.addMenu(f"🏆 Achievements ({done}/{len(ACHIEVEMENTS)})")
        for a in ACHIEVEMENTS:
            have, goal = self.achievements.progress(a)
            got = a.id in self.achievements.unlocked
            label = f"{a.icon} {a.title}: {a.description}" if got else \
                f"🔒 {a.title}: {a.description}" + (f" ({have}/{goal})" if goal > 1 else "")
            item = trophies.addAction(label)
            item.setEnabled(got)
        if len(self.windows) > 1:
            menu.addAction("📸 Group photo", self.group_photo)
        add = menu.addMenu("Add a pet")
        add.setEnabled(len(self.windows) < MAX_PETS)
        for cls in self.registry.values():
            add.addAction(cls.name, lambda c=cls: self.add_pet(c))

        sounds = menu.addAction("Sounds", lambda: self.set_sounds(not self.sounds.enabled))
        sounds.setCheckable(True)
        sounds.setChecked(self.sounds.enabled)
        breaks = menu.addAction(f"Break reminders ({self.break_minutes} min)",
                                 lambda: self.set_breaks(not self.breaks_on, self.break_minutes))
        breaks.setCheckable(True)
        breaks.setChecked(self.breaks_on)
        login = menu.addAction("Start at login", lambda: system.set_autostart(not system.autostart_enabled()))
        login.setCheckable(True)
        login.setChecked(system.autostart_enabled())
        if not system.launcher_installed():
            menu.addAction("Add to app menu", lambda: system.install_launcher(self.windows[0].pet))
        menu.addSeparator()
        menu.addAction("Quit", self.quit)

    # --- saving --------------------------------------------------------------

    def save(self):
        save.save({
            "saved_at": time.time(),
            "settings": {"sounds": self.sounds.enabled, "breaks": self.breaks_on,
                         "break_minutes": self.break_minutes, "weather": self.weather_kind},
            "achievements": self.achievements.to_dict(),
            "pets": [{
                "species": w.pet.species,
                "variant": w.pet.variant,
                "name": w.pet_name,
                "size": w.size_name,
                "mode": w.brain.mode.name,
                "needs": w.needs.to_dict(),
                "love": round(w.love, 1),
                "hat": w.hat,
                "adopted": w.adopted.isoformat(),
                "celebrated": sorted(w.celebrated),
                "x": round(w.body.x),
            } for w in self.windows],
        })
        if self.tray:
            self.tray.refresh()

    def quit(self):
        self.save()
        for win in self.windows:
            win.close_all()
        if self.ball:
            self.ball.close()
        if self.panel:
            self.panel.close()
        if self.laser:
            self.laser.stop()
        if self.arcade:
            self.arcade.stop()
        if self.weather:
            self.weather.stop()
        QApplication.quit()
