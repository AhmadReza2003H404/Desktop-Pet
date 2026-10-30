"""Tray icon: shows the first pet's face, everyone's stats, and the menus."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from core.pet import Pet, PetView, State
from ui.menu import fill_menu, stats_line

if TYPE_CHECKING:
    from ui.app import PetApp

ICON_SIZE = 64


def pet_icon(pet: Pet) -> QIcon:
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    scale = ICON_SIZE / max(pet.width, pet.height)
    p.scale(scale, scale)
    pet.draw(p, PetView(State.SIT, 0, 0, 1, 0, (0.2, 0.3), 0, False))
    p.end()
    return QIcon(pixmap)


class Tray(QSystemTrayIcon):
    def __init__(self, app: PetApp):
        super().__init__()
        self.app = app
        self.menu = QMenu()
        self.menu.aboutToShow.connect(self._rebuild)
        self.setContextMenu(self.menu)
        self.activated.connect(self._clicked)

    def refresh(self):
        if not self.app.windows:
            return
        self.setIcon(pet_icon(self.app.windows[0].pet))
        self.setToolTip("\n".join(f"{w.pet_name}: {stats_line(w)}" for w in self.app.windows))

    def _rebuild(self):
        self.menu.clear()
        windows = self.app.windows
        hidden = not any(w.isVisible() for w in windows)
        self.menu.addAction("Show pets" if hidden else "Hide pets", self.app.toggle_hidden)
        self.menu.addSeparator()
        if len(windows) == 1:
            fill_menu(self.menu, windows[0], self.app)
        else:
            for win in windows:
                fill_menu(self.menu.addMenu(f"{win.pet_name} the {win.pet.name}"), win, self.app)
        self.menu.addSeparator()
        self.app.fill_app_menu(self.menu)
        self.refresh()

    def _clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.app.open_panel()
