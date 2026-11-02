"""Food bowls. Each pet's favorite_food names one of the kinds below."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPolygonF

from render import rig

BOWL = QColor(225, 70, 80)


def draw_food(p: QPainter, kind: str, rect: QRectF, bites: int):
    """Draw a bowl with food in `rect`. bites 0..3: how much has been eaten."""
    p.setRenderHint(QPainter.Antialiasing)
    w, h = rect.width(), rect.height()
    rim_y = rect.bottom() - h * 0.42
    left = 1.0 - bites / 3.0

    if left > 0:
        p.save()
        p.translate(rect.center().x(), rim_y + 2)
        p.scale(0.55 + 0.45 * left, 0.55 + 0.45 * left)  # shrinks as it gets eaten
        DRAWERS.get(kind, _fish)(p, w, h)
        p.restore()

    bowl = QPainterPath(QPointF(rect.left() + 2, rim_y))
    bowl.lineTo(rect.right() - 2, rim_y)
    bowl.cubicTo(rect.right() - 6, rect.bottom(), rect.left() + 6, rect.bottom(), rect.left() + 2, rim_y)
    rig.fill_part(p, bowl, BOWL)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawRoundedRect(QRectF(rect.left() + w * 0.2, rim_y + 4, w * 0.25, 4), 2, 2)


def _fish(p: QPainter, w: float, h: float):
    body = rig.ellipse_path(QPointF(-2, -h * 0.12), w * 0.3, h * 0.17)
    tail = QPainterPath()
    tail.addPolygon(QPolygonF([QPointF(w * 0.24, -h * 0.12), QPointF(w * 0.42, -h * 0.3), QPointF(w * 0.42, h * 0.06)]))
    tail.closeSubpath()
    rig.fill_part(p, tail, QColor(120, 160, 200))
    rig.fill_part(p, body, QColor(160, 195, 225))
    p.setPen(Qt.NoPen)
    p.setBrush(rig.OUTLINE)
    p.drawEllipse(QPointF(-w * 0.2, -h * 0.15), 2, 2)


def _bone(p: QPainter, w: float, h: float):
    bone = rig.thick_line(rig.line_path(QPointF(-w * 0.25, -h * 0.12), QPointF(w * 0.25, -h * 0.12)), h * 0.16)
    for x in (-w * 0.27, w * 0.27):
        for dy in (-h * 0.08, h * 0.08):
            bone = bone.united(rig.ellipse_path(QPointF(x, -h * 0.12 + dy), h * 0.1, h * 0.1))
    rig.fill_part(p, bone, QColor(250, 245, 230))


def _bamboo(p: QPainter, w: float, h: float):
    for i, (x, tilt) in enumerate(((-w * 0.12, -10), (w * 0.1, 12))):
        p.save()
        p.translate(x, -h * 0.05)
        p.rotate(tilt)
        stalk = QPainterPath()
        stalk.addRoundedRect(QRectF(-4, -h * 0.55, 8, h * 0.55), 3, 3)
        rig.fill_part(p, stalk, QColor(140, 200, 90) if i else QColor(120, 185, 75))
        p.setPen(rig.outline_pen(1.5))
        p.drawLine(QPointF(-4, -h * 0.3), QPointF(4, -h * 0.3))
        p.restore()


def _leaves(p: QPainter, w: float, h: float, color=QColor(130, 185, 165)):
    for angle in (-35, 0, 35):
        p.save()
        p.translate(0, -h * 0.02)
        p.rotate(angle)
        leaf = QPainterPath(QPointF(0, 0))
        leaf.quadTo(w * 0.14, -h * 0.25, 0, -h * 0.48)
        leaf.quadTo(-w * 0.14, -h * 0.25, 0, 0)
        rig.fill_part(p, leaf, color)
        p.restore()


def _grass(p: QPainter, w: float, h: float):
    tuft = QPainterPath(QPointF(-w * 0.3, 0))
    for i in range(7):
        x = -w * 0.3 + i * w * 0.1
        tuft.lineTo(x + w * 0.05, -h * (0.3 + 0.12 * ((i * 3) % 4)))
        tuft.lineTo(x + w * 0.1, 0)
    tuft.closeSubpath()
    rig.fill_part(p, tuft, QColor(225, 200, 95))  # hay


def _candy(p: QPainter, w: float, h: float):
    for x, y, color in ((-w * 0.15, -h * 0.14, QColor(255, 120, 170)), (w * 0.14, -h * 0.2, QColor(120, 200, 255))):
        for side in (-1, 1):  # twisted wrapper ends
            end = QPainterPath(QPointF(x + side * w * 0.08, y))
            end.lineTo(x + side * w * 0.2, y - h * 0.09)
            end.lineTo(x + side * w * 0.2, y + h * 0.09)
            end.closeSubpath()
            rig.fill_part(p, end, color.lighter(120))
        rig.fill_part(p, rig.ellipse_path(QPointF(x, y), w * 0.1, h * 0.1), color)
        p.setPen(rig.outline_pen(1.5, QColor(255, 255, 255)))
        p.drawLine(QPointF(x - w * 0.04, y - h * 0.04), QPointF(x + w * 0.03, y + h * 0.05))


def _berries(p: QPainter, w: float, h: float):
    for x, y, color in ((-w * 0.13, -h * 0.1, QColor(200, 50, 90)), (w * 0.12, -h * 0.12, QColor(110, 70, 190)),
                        (0, -h * 0.26, QColor(230, 60, 80))):
        rig.fill_part(p, rig.ellipse_path(QPointF(x, y), w * 0.11, w * 0.11), color)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawEllipse(QPointF(x - w * 0.04, y - w * 0.04), w * 0.025, w * 0.025)
    leaf = QPainterPath(QPointF(0, -h * 0.36))
    leaf.quadTo(w * 0.12, -h * 0.5, w * 0.2, -h * 0.4)
    leaf.quadTo(w * 0.1, -h * 0.32, 0, -h * 0.36)
    rig.fill_part(p, leaf, QColor(110, 190, 90))


def _battery(p: QPainter, w: float, h: float):
    p.save()
    p.rotate(-12)
    cell = QPainterPath()
    cell.addRoundedRect(QRectF(-w * 0.28, -h * 0.34, w * 0.5, h * 0.3), 4, 4)
    rig.fill_part(p, cell, QColor(90, 210, 120))
    tip = QPainterPath()
    tip.addRoundedRect(QRectF(w * 0.22, -h * 0.25, w * 0.06, h * 0.12), 2, 2)
    rig.fill_part(p, tip, QColor(200, 200, 210))
    bolt = QPolygonF([QPointF(0, -h * 0.32), QPointF(-w * 0.07, -h * 0.18), QPointF(-w * 0.01, -h * 0.18),
                      QPointF(-w * 0.04, -h * 0.06), QPointF(w * 0.07, -h * 0.21), QPointF(w * 0.01, -h * 0.21)])
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 240, 120))
    p.drawPolygon(bolt)
    p.restore()


DRAWERS = {
    "candy": _candy,
    "berries": _berries,
    "battery": _battery,
    "fish": _fish,
    "bone": _bone,
    "bamboo": _bamboo,
    "eucalyptus": _leaves,
    "hay": _grass,
}
