"""Menus, shared by right-clicking a pet and the tray icon."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QInputDialog, QMenu

from core import progress
from core.behavior import Mode
from core.pet import State

if TYPE_CHECKING:
    from ui.app import PetApp
    from ui.pet_window import PetWindow

SIZES = {"Small": 0.75, "Medium": 1.0, "Large": 1.35}
MODES = (("Random walk", Mode.WANDER), ("Stay here", Mode.STAY), ("Follow my mouse", Mode.FOLLOW))


def stats_line(win: PetWindow) -> str:
    n = win.needs
    return f"🍖 {n.fullness:.0f}%   ⚡ {n.energy:.0f}%   ❤ {n.happiness:.0f}%"


def fill_menu(menu: QMenu, win: PetWindow, app: PetApp):
    """Everything about one pet."""
    header = menu.addAction(f"{win.pet_name} the {win.pet.name}  ·  Lv {win.level}")
    header.setEnabled(False)
    menu.addAction(stats_line(win)).setEnabled(False)
    menu.addSeparator()

    menu.addAction("Pet", win.pet_it)
    feed = menu.addAction("Feed", win.feed)
    feed.setEnabled(win.food is None)
    menu.addAction("Play ball", win.play_ball)
    if app.ball is not None:
        menu.addAction("Put the ball away", app.remove_ball)
    menu.addAction("Do a trick!", win.trick)
    menu.addAction("Come here!", win.come_here)
    menu.addAction("📸 Take a photo", win.take_photo)
    menu.addSeparator()

    menu.addAction("Sit here", lambda: win.command(State.SIT))
    menu.addAction("Sleep here", lambda: win.command(State.SLEEP))
    corner = menu.addMenu("Sleep in corner")
    corner.addAction("Left", lambda: win.sleep_in_corner(-1))
    corner.addAction("Right", lambda: win.sleep_in_corner(1))

    behaviour = menu.addMenu("Behaviour")
    group = QActionGroup(behaviour)
    for label, mode in MODES:
        action = behaviour.addAction(label, lambda m=mode: win.set_mode(m))
        action.setCheckable(True)
        action.setChecked(win.brain.mode == mode)
        group.addAction(action)
    menu.addSeparator()

    menu.addAction("Rename…", lambda: _rename(win))

    change = menu.addMenu("Change pet")
    for cls in app.registry.values():
        sub = change.addMenu(cls.name)
        for variant in cls.variants:
            action = sub.addAction(variant.replace("_", " ").capitalize(),
                                   lambda c=cls, v=variant: win.set_pet(c(v, SIZES[win.size_name])))
            action.setCheckable(True)
            action.setChecked(type(win.pet) is cls and win.pet.variant == variant)

    hats = menu.addMenu("Hat")
    group = QActionGroup(hats)
    for hat, label, unlocked, need in progress.hat_choices(win.love):
        action = hats.addAction(label if unlocked else f"🔒 {label} (Lv {need})", lambda h=hat: win.set_hat(h))
        action.setCheckable(True)
        action.setChecked(win.hat == hat)
        action.setEnabled(unlocked)
        group.addAction(action)

    size_menu = menu.addMenu("Size")
    group = QActionGroup(size_menu)
    for label in SIZES:
        action = size_menu.addAction(label, lambda l=label: _resize(win, l))
        action.setCheckable(True)
        action.setChecked(win.size_name == label)
        group.addAction(action)

    if len(app.windows) > 1:
        menu.addAction(f"Say goodbye to {win.pet_name}", lambda: app.remove_pet(win))


def _rename(win: PetWindow):
    name, ok = QInputDialog.getText(None, "Rename", f"New name for {win.pet_name}:", text=win.pet_name)
    if ok and name.strip():
        win.pet_name = name.strip()[:30]
        win.app.pet_changed(win)


def _resize(win: PetWindow, size: str):
    win.size_name = size
    win.set_pet(type(win.pet)(win.pet.variant, SIZES[size]))
