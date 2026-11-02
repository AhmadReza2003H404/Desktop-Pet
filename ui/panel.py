"""Pet House: a normal window to look after every pet and change settings."""

from __future__ import annotations

import datetime
import math
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCursor, QPainter
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from core import progress
from core.pet import PetView, State
from ui import system
from ui.menu import SIZES
from ui.tray import pet_icon

if TYPE_CHECKING:
    from ui.app import PetApp
    from ui.pet_window import PetWindow

PREVIEW = 120
STYLE = """
QFrame#card { border: 1px solid palette(mid); border-radius: 12px; background: palette(base); }
QLabel#name { font-size: 16px; font-weight: bold; }
QLabel#title { font-size: 20px; font-weight: bold; }
QProgressBar { min-height: 14px; max-height: 14px; border-radius: 7px; text-align: center; font-size: 10px; }
"""


class PetPreview(QWidget):
    """The pet, live: blinking, breathing, looking at your mouse, in its hat."""

    def __init__(self, win: PetWindow):
        super().__init__()
        self.win = win
        self.setFixedSize(PREVIEW, PREVIEW)
        self.start = time.monotonic()
        self.happy_until = 0.0

    def mousePressEvent(self, e):
        self.win.pet_it()
        self.happy_until = time.monotonic() + 1.5

    def paintEvent(self, _):
        pet, brain = self.win.pet, self.win.brain
        cursor = self.mapFromGlobal(QCursor.pos())
        dx, dy = cursor.x() - PREVIEW / 2, cursor.y() - PREVIEW / 3
        dist = max(1.0, math.hypot(dx, dy))
        k = min(1.0, dist / 120)
        happy = time.monotonic() < self.happy_until
        view = PetView(State.HAPPY if happy else State.SIT, time.monotonic() - self.start, 1, 1, 0,
                       (dx / dist * k, dy / dist * k), 0, brain.blinking, mood=self.win.mood())
        p = QPainter(self)
        scale = PREVIEW / max(pet.width, pet.height)
        p.scale(scale, scale)
        pet.draw(p, view)
        p.end()


class PetCard(QFrame):
    def __init__(self, win: PetWindow, app: PetApp):
        super().__init__()
        self.setObjectName("card")
        self.win, self.app = win, app
        self.shown_level = -1

        self.preview = PetPreview(win)
        self.preview.setToolTip("Click to pet")
        self.name = QLineEdit(win.pet_name)
        self.name.setMaxLength(30)
        self.name.editingFinished.connect(self._rename)
        self.level = QLabel()
        self.level.setObjectName("name")
        self.love = QProgressBar()
        self.days = QLabel()

        self.species = QComboBox()
        for cls in app.registry.values():
            self.species.addItem(cls.name, cls.species)
        self.variant = QComboBox()
        self.size = QComboBox()
        self.size.addItems(list(SIZES))
        self.hat = QComboBox()
        self.species.activated.connect(self._species_changed)
        self.variant.activated.connect(self._apply_look)
        self.size.activated.connect(self._apply_look)
        self.hat.activated.connect(lambda: win.set_hat(self.hat.currentData()))

        self.bars = {}
        for key, label in (("fullness", "🍖 Food"), ("energy", "⚡ Energy"), ("happiness", "❤ Happy")):
            bar = QProgressBar()
            bar.setFormat(f"{label}  %p%")
            self.bars[key] = bar

        self.feed = QPushButton("🍖 Feed")
        self.feed.clicked.connect(win.feed)
        buttons = [self.feed]
        for text, slot in (("⚽ Ball", win.play_ball), ("✨ Trick", win.trick), ("📍 Come here", win.come_here),
                           ("📸 Photo", win.take_photo)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.append(button)
        self.remove = QPushButton("👋 Goodbye")
        self.remove.clicked.connect(lambda: app.remove_pet(win))
        buttons.append(self.remove)

        top = QHBoxLayout()
        top.addWidget(self.name, 1)
        top.addWidget(self.level)
        grid = QGridLayout()
        for col, (label, widget) in enumerate((("Animal", self.species), ("Look", self.variant),
                                               ("Size", self.size), ("Hat", self.hat))):
            grid.addWidget(QLabel(label), 0, col)
            grid.addWidget(widget, 1, col)
        stats = QHBoxLayout()
        for bar in self.bars.values():
            stats.addWidget(bar)
        row = QHBoxLayout()
        for button in buttons:
            row.addWidget(button)

        column = QVBoxLayout()
        column.addLayout(top)
        column.addWidget(self.love)
        column.addWidget(self.days)
        column.addLayout(grid)
        column.addLayout(stats)
        column.addLayout(row)
        layout = QHBoxLayout(self)
        layout.addWidget(self.preview, 0, Qt.AlignTop)
        layout.addLayout(column, 1)
        self.sync_look()
        self.refresh()

    def sync_look(self):
        """Point the combo boxes at the pet's current species, variant, size and hat."""
        pet = self.win.pet
        self.species.setCurrentIndex(self.species.findData(pet.species))
        self.variant.clear()
        for v in pet.variants:
            self.variant.addItem(v.replace("_", " ").capitalize(), v)
        self.variant.setCurrentIndex(self.variant.findData(pet.variant))
        self.size.setCurrentText(self.win.size_name)
        self._fill_hats()

    def _fill_hats(self):
        self.hat.clear()
        for hat, label, unlocked, need in progress.hat_choices(self.win.love):
            self.hat.addItem(label if unlocked else f"🔒 {label} (Lv {need})", hat)
            if not unlocked:
                self.hat.model().item(self.hat.count() - 1).setEnabled(False)
        self.hat.setCurrentIndex(max(0, self.hat.findData(self.win.hat)))
        self.shown_level = self.win.level

    def refresh(self):
        win = self.win
        level, into, needed = progress.progress(win.love)
        self.level.setText(f"Lv {level}")
        self.love.setRange(0, round(needed * 10))
        self.love.setValue(round(into * 10))
        self.love.setFormat(f"♥ {into:.0f} / {needed:.0f} love to level {level + 1}")
        for key, bar in self.bars.items():
            bar.setValue(round(getattr(win.needs, key)))
        self.feed.setEnabled(win.food is None)
        self.days.setText(self._days_text())
        self.remove.setVisible(len(self.app.windows) > 1)
        if level != self.shown_level:
            self._fill_hats()
        if not self.name.hasFocus() and self.name.text() != win.pet_name:
            self.name.setText(win.pet_name)
        self.preview.update()

    def _days_text(self) -> str:
        win = self.win
        today = datetime.date.today()
        days = win.days_together(today)
        birthday = win.adopted.replace(year=today.year) if (win.adopted.month, win.adopted.day) != (2, 29) \
            else datetime.date(today.year, 3, 1)
        if birthday < today or (birthday == today and days == 0):  # next one, unless it's today
            birthday = birthday.replace(year=today.year + 1)
        until = (birthday - today).days
        together = "Adopted today!" if days == 0 else f"Together {days} day{'s' if days != 1 else ''}"
        return f"🗓 {together}  ·  🎂 birthday in {until} days" if until else f"🗓 {together}  ·  🎂 birthday today!"

    def _rename(self):
        name = self.name.text().strip()
        if name and name != self.win.pet_name:
            self.win.pet_name = name
            self.app.pet_changed(self.win)

    def _species_changed(self):
        cls = self.app.registry[self.species.currentData()]
        self.variant.clear()
        for v in cls.variants:
            self.variant.addItem(v.replace("_", " ").capitalize(), v)
        self._apply_look()

    def _apply_look(self):
        cls = self.app.registry[self.species.currentData()]
        self.win.size_name = self.size.currentText()
        self.win.set_pet(cls(self.variant.currentData(), SIZES[self.win.size_name]))


class PetHouse(QWidget):
    def __init__(self, app: PetApp):
        super().__init__()
        self.app = app
        self.setWindowTitle("Pet House")
        self.setStyleSheet(STYLE)
        self.resize(QSize(720, 640))
        self.cards: list[PetCard] = []

        title = QLabel("🏠 Pet House")
        title.setObjectName("title")
        self.add_species = QComboBox()
        for cls in app.registry.values():
            self.add_species.addItem(cls.name, cls.species)
        self.add_button = QPushButton("➕ Adopt")
        self.add_button.clicked.connect(lambda: app.add_pet(app.registry[self.add_species.currentData()]))
        self.laser = QPushButton("🔴 Laser")
        self.laser.setCheckable(True)
        self.laser.clicked.connect(app.toggle_laser)
        self.arcade = QPushButton("👾 Dot Dash")
        self.arcade.setCheckable(True)
        self.arcade.clicked.connect(app.toggle_arcade)
        group = QPushButton("📸 Group photo")
        group.clicked.connect(app.group_photo)
        self.group = group
        header = QHBoxLayout()
        header.addWidget(title, 1)
        header.addWidget(self.laser)
        header.addWidget(self.arcade)
        header.addWidget(group)
        header.addWidget(self.add_species)
        header.addWidget(self.add_button)

        self.list = QVBoxLayout()
        self.list.addStretch(1)
        holder = QWidget()
        holder.setLayout(self.list)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(holder)

        self.sounds = QCheckBox("Sounds")
        self.sounds.toggled.connect(app.set_sounds)
        self.login = QCheckBox("Start at login")
        self.login.toggled.connect(system.set_autostart)
        self.breaks = QCheckBox("Break reminders every")
        self.breaks.toggled.connect(lambda on: app.set_breaks(on, self.minutes.value()))
        self.minutes = QSpinBox()
        self.minutes.setRange(10, 180)
        self.minutes.setSingleStep(5)
        self.minutes.setSuffix(" min")
        self.minutes.valueChanged.connect(lambda m: app.set_breaks(self.breaks.isChecked(), m))
        self.launcher = QPushButton("Add to app menu")
        self.launcher.clicked.connect(lambda: (system.install_launcher(app.windows[0].pet), self.refresh()))
        hide = QPushButton("Hide / show pets")
        hide.clicked.connect(app.toggle_hidden)
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(app.quit)
        settings = QHBoxLayout()
        for widget in (self.sounds, self.login, self.breaks, self.minutes):
            settings.addWidget(widget)
        settings.addStretch(1)
        actions = QHBoxLayout()
        actions.addWidget(self.launcher)
        actions.addStretch(1)
        actions.addWidget(hide)
        actions.addWidget(quit_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(scroll, 1)
        layout.addLayout(settings)
        layout.addLayout(actions)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.rebuild()

    def rebuild(self):
        """Pets were added or removed: one card each."""
        for card in self.cards:
            card.deleteLater()
        self.cards = [PetCard(win, self.app) for win in self.app.windows]
        for i, card in enumerate(self.cards):
            self.list.insertWidget(i, card)
        self.refresh()

    def pet_changed(self, win: PetWindow):
        for card in self.cards:
            if card.win is win:
                card.sync_look()

    def refresh(self):
        for card in self.cards:
            card.refresh()
        app = self.app
        for box, value in ((self.sounds, app.sounds.enabled), (self.login, system.autostart_enabled()),
                           (self.breaks, app.breaks_on)):
            box.blockSignals(True)
            box.setChecked(value)
            box.blockSignals(False)
        self.minutes.blockSignals(True)
        self.minutes.setValue(app.break_minutes)
        self.minutes.blockSignals(False)
        self.add_button.setEnabled(len(app.windows) < app.max_pets)
        self.laser.setChecked(app.laser is not None)
        self.arcade.setChecked(app.arcade is not None)
        self.group.setVisible(len(app.windows) > 1)
        self.launcher.setVisible(not system.launcher_installed())
        if app.windows:
            self.setWindowIcon(pet_icon(app.windows[0].pet))

    def showEvent(self, e):
        self.timer.start(100)  # ~10 fps is plenty for the previews and bars
        super().showEvent(e)

    def hideEvent(self, e):
        self.timer.stop()
        super().hideEvent(e)
