"""Photo booth: framed portraits of your pets, saved to ~/Pictures/Desktop Pets."""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen

from core.pet import PetView, State
from render import rig

if TYPE_CHECKING:
    from ui.pet_window import PetWindow

SLOT = 300   # px per pet
FRAME = 26
BACKDROPS = [
    (QColor(255, 222, 233), QColor(255, 245, 214)),
    (QColor(214, 236, 255), QColor(232, 255, 236)),
    (QColor(238, 224, 255), QColor(255, 232, 240)),
]


def folder() -> Path:
    pictures = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or str(Path.home() / "Pictures")
    return Path(pictures) / "Desktop Pets"


def portrait(windows: list[PetWindow]) -> QImage:
    n = len(windows)
    width, height = SLOT * n + FRAME * 2, SLOT + 150
    img = QImage(width, height, QImage.Format_ARGB32)
    img.fill(QColor(250, 246, 238))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    # polaroid-style frame with a soft gradient backdrop
    inner = QRectF(FRAME, FRAME, width - FRAME * 2, SLOT)
    top, bottom = BACKDROPS[datetime.date.today().toordinal() % len(BACKDROPS)]
    gradient = QLinearGradient(inner.topLeft(), inner.bottomLeft())
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, bottom)
    p.setPen(Qt.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(inner, 14, 14)
    p.setBrush(QColor(255, 255, 255, 90))  # a floor for them to sit on
    p.drawEllipse(QPointF(width / 2, inner.bottom() - 18), inner.width() * 0.46, 26)

    for i, win in enumerate(windows):
        pet = win.pet
        size = SLOT * 0.8
        scale = size / max(pet.width, pet.height)
        p.save()
        p.translate(FRAME + i * SLOT + (SLOT - pet.width * scale) / 2, inner.bottom() - 18 - pet.height * scale)
        p.scale(scale, scale)
        facing = 1 if i < n / 2 or n == 1 else -1  # the group faces the middle
        pet.draw(p, PetView(State.SIT, 0.3, 0, facing, 0, (0.15 * facing, 0.25), 0, False, mood=win.mood()))
        p.restore()

    p.setPen(QPen(rig.OUTLINE))
    title = QFont("Sans", 1, QFont.Bold)
    title.setPixelSize(28)
    p.setFont(title)
    if n == 1:
        win = windows[0]
        caption = f"{win.pet_name} the {win.pet.name}"
        detail = f"Level {win.level}  ·  together {win.days_together()} days"
    else:
        caption = "The whole gang"
        detail = "  ·  ".join(w.pet_name for w in windows)
    p.drawText(QRectF(0, inner.bottom() + 18, width, 40), Qt.AlignCenter, caption)
    small = QFont("Sans", 1)
    small.setPixelSize(16)
    p.setFont(small)
    p.setPen(QColor(110, 100, 110))
    p.drawText(QRectF(0, inner.bottom() + 62, width, 26), Qt.AlignCenter, detail)
    p.drawText(QRectF(0, inner.bottom() + 90, width, 26), Qt.AlignCenter,
               f"{datetime.date.today():%B} {datetime.date.today().day}, {datetime.date.today().year}")
    p.end()
    return img


def save(windows: list[PetWindow]) -> Path:
    target = folder()
    target.mkdir(parents=True, exist_ok=True)
    name = windows[0].pet_name if len(windows) == 1 else "group"
    slug = re.sub(r"[^\w-]+", "-", name).strip("-") or "pet"
    path = target / f"{slug}-{datetime.datetime.now():%Y%m%d-%H%M%S}.png"
    portrait(windows).save(str(path))
    return path
