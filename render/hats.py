"""Hats and accessories, drawn relative to a head (centre c, radius r).

The face sits a little forward of the head centre (3/4 view), so
"forward" is +x. Keep hats within ~1.6 r above the centre so they fit
the pet's window.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPolygonF

from render import rig

GOLD = QColor(250, 200, 60)


def draw_hat(p: QPainter, hat: str, c: QPointF, r: float, eyes: list[rig.Eye], t: float):
    drawer = HATS.get(hat)
    if drawer:
        p.save()
        drawer(p, c, r, eyes, t)
        p.restore()


def _bow(p, c, r, eyes, t):
    knot = c + QPointF(r * 0.55, -r * 0.72)
    red = QColor(240, 80, 120)
    for side in (-1, 1):
        wing = QPainterPath(knot)
        wing.lineTo(knot + QPointF(side * r * 0.38, -r * 0.24))
        wing.lineTo(knot + QPointF(side * r * 0.38, r * 0.22))
        wing.closeSubpath()
        rig.fill_part(p, wing, red)
    rig.fill_part(p, rig.ellipse_path(knot, r * 0.1, r * 0.1), red.darker(115))


def _party(p, c, r, eyes, t):
    base = c + QPointF(r * 0.05, -r * 0.78)
    cone = QPainterPath(base + QPointF(-r * 0.38, 0))
    cone.lineTo(base + QPointF(r * 0.15, -r * 0.82))
    cone.lineTo(base + QPointF(r * 0.38, 0))
    cone.quadTo(base + QPointF(0, r * 0.1), base + QPointF(-r * 0.38, 0))

    def stripes(painter: QPainter, rect: QRectF):
        painter.setPen(rig.outline_pen(r * 0.12, QColor(255, 230, 90)))
        for k in (0.3, 0.6):
            y = rect.bottom() - rect.height() * k
            painter.drawLine(QPointF(rect.left(), y + r * 0.1), QPointF(rect.right(), y - r * 0.1))
    rig.fill_part(p, cone, QColor(90, 160, 240), stripes)
    bob = math.sin(t * 6) * r * 0.03
    rig.fill_part(p, rig.ellipse_path(base + QPointF(r * 0.15, -r * 0.86 + bob), r * 0.12, r * 0.12), QColor(255, 120, 150))


def _flower(p, c, r, eyes, t):
    centre = c + QPointF(-r * 0.45, -r * 0.72)
    petal = QColor(255, 255, 255)
    for k in range(6):
        a = math.radians(k * 60 + t * 10)
        rig.fill_part(p, rig.ellipse_path(centre + QPointF(math.cos(a), math.sin(a)) * r * 0.17,
                                          r * 0.11, r * 0.11), petal)
    rig.fill_part(p, rig.ellipse_path(centre, r * 0.11, r * 0.11), QColor(255, 200, 50))


def _beanie(p, c, r, eyes, t):
    cap = QPainterPath(c + QPointF(-r * 0.92, -r * 0.42))
    cap.cubicTo(c + QPointF(-r * 0.9, -r * 1.3), c + QPointF(r * 0.9, -r * 1.3), c + QPointF(r * 0.92, -r * 0.42))
    cap.closeSubpath()
    blue = QColor(70, 130, 200)

    def ribs(painter: QPainter, rect: QRectF):
        painter.setPen(rig.outline_pen(1.2, blue.darker(125)))
        for k in range(1, 6):
            x = rect.left() + rect.width() * k / 6
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
    rig.fill_part(p, cap, blue, ribs)
    band = QPainterPath()
    band.addRoundedRect(QRectF(c.x() - r * 0.98, c.y() - r * 0.58, r * 1.96, r * 0.26), r * 0.1, r * 0.1)
    rig.fill_part(p, band, QColor(240, 240, 240))
    rig.fill_part(p, rig.ellipse_path(c + QPointF(0, -r * 1.12), r * 0.17, r * 0.17), QColor(240, 90, 90))


def _shades(p, c, r, eyes, t):
    lenses = QPainterPath()
    for centre, er in eyes:
        lenses.addRoundedRect(QRectF(centre.x() - er * 1.15, centre.y() - er * 0.75, er * 2.3, er * 1.5),
                              er * 0.45, er * 0.45)
    rig.fill_part(p, lenses, QColor(30, 30, 40))
    (a, ra), (b, rb) = eyes[0], eyes[1]
    p.setPen(rig.outline_pen(2.4))
    p.drawLine(QPointF(a.x() + ra * 1.1, a.y() - ra * 0.3), QPointF(b.x() - rb * 1.1, b.y() - rb * 0.3))
    p.setPen(rig.outline_pen(2.4, QColor(255, 255, 255, 170)))  # cool glint
    p.drawLine(QPointF(b.x() - rb * 0.5, b.y() - rb * 0.3), QPointF(b.x() - rb * 0.1, b.y() - rb * 0.5))


def _witch(p, c, r, eyes, t):
    purple = QColor(110, 70, 160)
    brim = rig.ellipse_path(c + QPointF(0, -r * 0.82), r * 1.15, r * 0.2)
    rig.fill_part(p, brim, purple)
    cone = QPainterPath(c + QPointF(-r * 0.5, -r * 0.85))
    cone.lineTo(c + QPointF(-r * 0.1, -r * 1.35))
    cone.quadTo(c + QPointF(-r * 0.3, -r * 1.6), c + QPointF(-r * 0.75, -r * 1.55))  # floppy tip
    cone.quadTo(c + QPointF(-r * 0.2, -r * 1.75), c + QPointF(r * 0.15, -r * 1.3))
    cone.lineTo(c + QPointF(r * 0.5, -r * 0.85))
    cone.closeSubpath()
    rig.fill_part(p, cone, purple)
    band = QPainterPath()
    band.addRect(QRectF(c.x() - r * 0.47, c.y() - r * 1.02, r * 0.95, r * 0.15))
    rig.fill_part(p, band, QColor(250, 170, 60))


def _crown(p, c, r, eyes, t):
    y0, y1 = c.y() - r * 0.72, c.y() - r * 1.3
    xs = [-0.5, -0.3, -0.12, 0.06, 0.24, 0.42, 0.6]
    crown = QPainterPath(QPointF(c.x() + r * xs[0], y0))
    for i, fx in enumerate(xs):
        crown.lineTo(c.x() + r * fx, y1 if i % 3 == 0 else (y0 + y1) / 2 if i % 3 == 1 else y0 - r * 0.15)
    crown.lineTo(c.x() + r * xs[-1], y0)
    crown.closeSubpath()
    rig.fill_part(p, crown, GOLD)
    p.setPen(Qt.NoPen)
    for fx, color in ((-0.2, QColor(230, 60, 90)), (0.05, QColor(80, 160, 240)), (0.32, QColor(230, 60, 90))):
        p.setBrush(color)
        p.drawEllipse(QPointF(c.x() + r * fx, y0 - r * 0.1), r * 0.06, r * 0.06)


def _pumpkin(p, c, r, eyes, t):
    centre = c + QPointF(r * 0.05, -r * 1.08)
    orange = QColor(245, 140, 40)
    body = rig.ellipse_path(centre, r * 0.52, r * 0.36)

    def ridges(painter: QPainter, rect: QRectF):
        painter.setPen(rig.outline_pen(1.4, orange.darker(130)))
        painter.setBrush(Qt.NoBrush)
        for k in (0.3, 0.7):
            painter.drawArc(QRectF(rect.left() + rect.width() * (k - 0.15), rect.top(), rect.width() * 0.3,
                                   rect.height()), 0, 360 * 16)
    rig.fill_part(p, body, orange, ridges)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(90, 50, 20))
    for side in (-1, 1):  # tiny jack-o'-lantern face
        tri = QPolygonF([centre + QPointF(side * r * 0.2 - r * 0.06, -r * 0.02),
                         centre + QPointF(side * r * 0.2 + r * 0.06, -r * 0.02),
                         centre + QPointF(side * r * 0.2, -r * 0.12)])
        p.drawPolygon(tri)
    p.drawRoundedRect(QRectF(centre.x() - r * 0.18, centre.y() + r * 0.06, r * 0.36, r * 0.1), r * 0.04, r * 0.04)
    stem = rig.thick_line(rig.line_path(centre + QPointF(0, -r * 0.32), centre + QPointF(r * 0.08, -r * 0.48)), r * 0.1)
    rig.fill_part(p, stem, QColor(90, 140, 60))


def _santa(p, c, r, eyes, t):
    red = QColor(220, 50, 60)
    sway = math.sin(t * 2) * r * 0.05
    cone = QPainterPath(c + QPointF(-r * 0.75, -r * 0.62))
    cone.quadTo(c + QPointF(-r * 0.2, -r * 1.55), c + QPointF(-r * 0.85 + sway, -r * 1.25))
    cone.quadTo(c + QPointF(r * 0.2, -r * 1.7), c + QPointF(r * 0.8, -r * 0.62))
    cone.closeSubpath()
    rig.fill_part(p, cone, red)
    band = QPainterPath()
    band.addRoundedRect(QRectF(c.x() - r * 0.88, c.y() - r * 0.75, r * 1.76, r * 0.24), r * 0.12, r * 0.12)
    rig.fill_part(p, band, QColor(250, 250, 250))
    rig.fill_part(p, rig.ellipse_path(c + QPointF(-r * 0.85 + sway, -r * 1.25), r * 0.15, r * 0.15),
                  QColor(250, 250, 250))


HATS = {
    "bow": _bow,
    "party": _party,
    "flower": _flower,
    "beanie": _beanie,
    "shades": _shades,
    "witch": _witch,
    "crown": _crown,
    "pumpkin": _pumpkin,
    "santa": _santa,
}
