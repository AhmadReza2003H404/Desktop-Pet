"""Drawing helpers shared by all species: outlined body parts, googly eyes,
little faces, and floating effects like Zzz and sweat drops."""

import math
from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPainterPathStroker, QPen

OUTLINE = QColor(45, 32, 32)
BLUSH = QColor(255, 110, 140, 105)
MOUTH_INSIDE = QColor(125, 40, 55)
TONGUE = QColor(255, 135, 150)

Markings = Callable[[QPainter, QRectF], None]


def outline_pen(width: float = 3.0, color: QColor = OUTLINE) -> QPen:
    return QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def thick_line(path: QPainterPath, width: float) -> QPainterPath:
    """Turn a thin path (a tail, a leg) into a fillable shape with round ends."""
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setCapStyle(Qt.RoundCap)
    stroker.setJoinStyle(Qt.RoundJoin)
    return stroker.createStroke(path).simplified()


def line_path(a: QPointF, b: QPointF) -> QPainterPath:
    path = QPainterPath(a)
    path.lineTo(b)
    return path


def ellipse_path(c: QPointF, rx: float, ry: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(c, rx, ry)
    return path


def fill_part(p: QPainter, path: QPainterPath, color: QColor,
              markings: Markings | None = None, shade: int = 0):
    """Fill a body part, paint markings clipped inside it, then outline it."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(path)
    if markings or shade:
        p.setClipPath(path, Qt.IntersectClip)
        rect = path.boundingRect()
        if markings:
            markings(p, rect)
        if shade:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, shade))
            p.drawRect(rect)
    p.restore()
    p.setPen(outline_pen())
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


Eye = tuple[QPointF, float]  # centre, radius


def googly_eyes(p: QPainter, eyes: list[Eye], look: tuple[float, float],
                wide: bool = False, jitter_t: float | None = None, pupil: str = "round"):
    """Big white eyes whose pupils roll towards `look` (a vector of length <= 1).
    pupil: "round", or "bar" for a goat's sideways slot."""
    for i, (c, r) in enumerate(eyes):
        if wide:
            r *= 1.2
        p.setPen(outline_pen(2.5))
        p.setBrush(Qt.white)
        p.drawEllipse(c, r, r)
        pr = r * (0.38 if wide else 0.48)
        reach = r - pr - 1.5
        off = QPointF(look[0] * reach, look[1] * reach)
        if jitter_t is not None:
            off += QPointF(math.sin(jitter_t * 31 + i * 2) * 1.5, math.cos(jitter_t * 27 + i) * 1.5)
        p.setPen(Qt.NoPen)
        p.setBrush(OUTLINE)
        if pupil == "bar":
            p.drawRoundedRect(QRectF(c.x() + off.x() - pr * 1.1, c.y() + off.y() - pr * 0.42, pr * 2.2, pr * 0.84),
                              pr * 0.4, pr * 0.4)
            continue
        p.drawEllipse(c + off, pr, pr)
        p.setBrush(Qt.white)
        p.drawEllipse(c + off + QPointF(-pr * 0.35, -pr * 0.4), pr * 0.32, pr * 0.32)


def closed_eyes(p: QPainter, eyes: list[Eye], style: str = "sleep"):
    """style: "sleep" (‿), "happy" (^) or "blink" (—)."""
    p.setPen(outline_pen(2.8))
    p.setBrush(Qt.NoBrush)
    for c, r in eyes:
        path = QPainterPath(QPointF(c.x() - r * 0.7, c.y()))
        if style == "sleep":
            path.quadTo(c.x(), c.y() + r * 0.65, c.x() + r * 0.7, c.y())
        elif style == "happy":
            path.quadTo(c.x(), c.y() - r * 0.8, c.x() + r * 0.7, c.y())
        else:
            path.lineTo(c.x() + r * 0.7, c.y())
        p.drawPath(path)


def worried_brows(p: QPainter, eyes: list[Eye]):
    """Eyebrows tilted up in the middle: hungry or sad."""
    p.setPen(outline_pen(2.4))
    centre_x = sum(c.x() for c, _ in eyes) / len(eyes)
    for c, r in eyes:
        inner = 1 if c.x() < centre_x else -1  # which way is the middle of the face
        p.drawLine(QPointF(c.x() - inner * r * 0.75, c.y() - r * 1.2),
                   QPointF(c.x() + inner * r * 0.55, c.y() - r * 1.55))


def droopy_lids(p: QPainter, eyes: list[Eye], skin: QColor):
    """Heavy eyelids over the top half of each eye: tired."""
    for c, r in eyes:
        p.save()
        lid = QPainterPath()
        lid.addEllipse(c, r, r)
        p.setClipPath(lid)
        p.setPen(Qt.NoPen)
        p.setBrush(skin)
        p.drawRect(QRectF(c.x() - r, c.y() - r, r * 2, r * 0.95))
        p.restore()
        p.setPen(outline_pen(2.4))
        p.drawLine(QPointF(c.x() - r * 0.9, c.y() - r * 0.08), QPointF(c.x() + r * 0.9, c.y() - r * 0.08))


def blush(p: QPainter, spots: list[QPointF], r: float):
    p.setPen(Qt.NoPen)
    p.setBrush(BLUSH)
    for c in spots:
        p.drawEllipse(c, r, r * 0.6)


def w_mouth(p: QPainter, at: QPointF, size: float, blep: bool = False):
    """The classic :3 mouth, optionally with the tongue poking out."""
    if blep:
        p.setPen(outline_pen(1.8))
        p.setBrush(TONGUE)
        p.drawRoundedRect(QRectF(at.x() - size * 0.22, at.y() + size * 0.05, size * 0.44, size * 0.5),
                          size * 0.2, size * 0.2)
    p.setPen(outline_pen(2.2))
    p.setBrush(Qt.NoBrush)
    path = QPainterPath(QPointF(at.x() - size * 0.55, at.y()))
    path.quadTo(at.x() - size * 0.3, at.y() + size * 0.45, at.x(), at.y())
    path.quadTo(at.x() + size * 0.3, at.y() + size * 0.45, at.x() + size * 0.55, at.y())
    p.drawPath(path)


def open_mouth(p: QPainter, at: QPointF, size: float):
    p.setPen(outline_pen(2.2))
    p.setBrush(MOUTH_INSIDE)
    p.drawEllipse(QPointF(at.x(), at.y() + size * 0.35), size * 0.32, size * 0.42)


def pant_mouth(p: QPainter, at: QPointF, size: float, t: float):
    """Happy dog mouth: open, tongue flopping out."""
    p.setPen(outline_pen(2.0))
    p.setBrush(MOUTH_INSIDE)
    mouth = QPainterPath(QPointF(at.x() - size * 0.45, at.y()))
    mouth.quadTo(at.x(), at.y() + size * 0.9, at.x() + size * 0.45, at.y())
    mouth.closeSubpath()
    p.drawPath(mouth)
    bounce = abs(math.sin(t * 9)) * size * 0.12
    p.setBrush(TONGUE)
    p.drawRoundedRect(QRectF(at.x() - size * 0.2, at.y() + size * 0.25, size * 0.4, size * 0.55 + bounce),
                      size * 0.2, size * 0.2)
    p.setPen(outline_pen(1.2))
    p.drawLine(QPointF(at.x(), at.y() + size * 0.35), QPointF(at.x(), at.y() + size * 0.6 + bounce))


def zzz(p: QPainter, origin: QPointF, t: float, scale: float = 1.0):
    """Floating Z's rising from `origin`. Draw unmirrored, in window space."""
    font = QFont("Sans", 1, QFont.Black)
    for i in range(3):
        phase = (t * 0.45 + i / 3) % 1.0
        font.setPixelSize(max(1, round((9 + phase * 9) * scale)))
        p.setFont(font)
        alpha = int(255 * min(1.0, (1 - phase) * 2.2))
        pos = origin + QPointF((phase * 18 + math.sin(t * 2 + i) * 3) * scale, -phase * 34 * scale)
        p.setPen(QColor(90, 110, 200, alpha))
        p.drawText(pos, "z" if phase < 0.4 else "Z")


def sweat_drop(p: QPainter, at: QPointF, size: float = 8.0):
    p.setPen(outline_pen(1.5, QColor(60, 120, 200)))
    p.setBrush(QColor(140, 200, 255))
    drop = QPainterPath(at)
    drop.quadTo(at.x() + size, at.y() + size * 1.6, at.x(), at.y() + size * 1.9)
    drop.quadTo(at.x() - size, at.y() + size * 1.6, at.x(), at.y())
    p.drawPath(drop)


def heart_path(c: QPointF, size: float) -> QPainterPath:
    s = size
    path = QPainterPath(QPointF(c.x(), c.y() + s * 0.35))
    path.cubicTo(c.x() - s * 0.1, c.y() + s * 0.25, c.x() - s * 0.55, c.y() - s * 0.05, c.x() - s * 0.5, c.y() - s * 0.25)
    path.cubicTo(c.x() - s * 0.45, c.y() - s * 0.5, c.x() - s * 0.1, c.y() - s * 0.5, c.x(), c.y() - s * 0.22)
    path.cubicTo(c.x() + s * 0.1, c.y() - s * 0.5, c.x() + s * 0.45, c.y() - s * 0.5, c.x() + s * 0.5, c.y() - s * 0.25)
    path.cubicTo(c.x() + s * 0.55, c.y() - s * 0.05, c.x() + s * 0.1, c.y() + s * 0.25, c.x(), c.y() + s * 0.35)
    return path
