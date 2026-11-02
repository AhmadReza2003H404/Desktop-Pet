"""Shared skeleton for four-legged pets: all the poses (stand, walk, sit, sleep,
dangle, eat, purr) live here. A species only describes its look: proportions,
palettes, ears, nose, tail and coat markings.

To make a new animal, subclass Quadruped, set `palettes` and the proportions,
and override whichever hooks it needs (behind_head, over_head, markings...)."""

import math
from dataclasses import replace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF

from core.pet import Pet, PetView, State
from render import rig
from render.hats import draw_hat

DESIGN = 120  # drawn in a 120x120 design box, then scaled to the pet's size
CAT_NOSE = QColor(255, 140, 160)
DARK_NOSE = QColor(40, 34, 38)


class Quadruped(Pet):
    palettes: dict[str, dict] = {}

    # proportions, in design units
    body_rx, body_ry = 34.0, 19.0
    leg_len = 12.0      # how far the body floats above the ground
    leg_w = 10.0
    head_r = 26.0
    head_shape = (1.08, 0.95)  # head ellipse x/y multipliers
    head_k = 1.0        # head size multiplier (babies have big heads)
    body_k = 1.0
    tail_kind = "long"  # long | curl | stub
    tail_w = 9.0

    # face
    nose_kind = "cat"   # cat | dog | bear | koala | goat
    muzzle: tuple[float, float, float, float] | None = None  # x, y offset and rx, ry, in head radii
    whiskers = False
    pupil = "round"

    def __init__(self, variant: str | None = None, scale: float = 1.0):
        super().__init__(variant, scale)
        self.pal = self.palettes[self.variant]

    # --- hooks for species ---------------------------------------------------

    def color(self, part: str, index: int | None = None) -> QColor:
        """Colour of a part ("leg", "ear", "tail", "muzzle"...), falling back to the base coat."""
        if index is not None and f"{part}{index}" in self.pal:
            return self.pal[f"{part}{index}"]
        return self.pal.get(part, self.pal["base"])

    def markings(self, part: str) -> rig.Markings | None:
        """Coat pattern painted inside a part: "body", "chest", "head", "leg", "paw", "tail"."""
        return None

    def behind_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        """Ears, horns... anything the head should overlap."""

    def over_head(self, p: QPainter, c: QPointF, r: float, v: PetView):
        """Floppy ears, beards, hats... drawn on top of the face."""

    def under_eyes(self, p: QPainter, f: QPointF, r: float):
        """Eye patches and the like, under the eyes but over the head."""

    def idle_mouth(self, v: PetView) -> str:
        """Mouth when nothing special is happening: "w", "blep" or "pant"."""
        return "w"

    def leg_k(self) -> float:
        return self.pal.get("leg_k", 1.0)

    # --- frame ---------------------------------------------------------------

    def draw(self, p: QPainter, v: PetView):
        s = self.width / DESIGN
        p.setRenderHint(QPainter.Antialiasing)
        outer = p.transform()
        p.save()
        p.translate(self.width / 2, self.height - 3 * s)
        p.scale(s * (1 + v.squash), s * (1 - v.squash))
        p.scale(v.facing, 1)
        look = (v.look[0] * v.facing, v.look[1])

        if v.state == State.SPECIAL:
            pose, drawn = self.special_pose(p, v)
        else:
            pose = {
                State.SIT: self.pose_sit,
                State.HAPPY: self.pose_sit,
                State.SLEEP: self.pose_sleep,
                State.DRAGGED: self.pose_dangle,
            }.get(v.state, self.pose_stand)
            drawn = v
        head_top = pose(p, drawn, look)
        anchor = outer.inverted()[0].map(p.transform().map(head_top))
        p.restore()

        # overlays are drawn unmirrored so text and drops read the right way
        if v.state == State.SLEEP or v.special == "cling_sleep":
            rig.zzz(p, anchor + QPointF(4 * s, 0), v.t, s)
        elif v.state == State.DRAGGED:
            rig.sweat_drop(p, anchor + QPointF(30 * s, 6 * s), 6 * s)

    def special_pose(self, p: QPainter, v: PetView):
        """Map a trick's pose name to a drawing function (and the view to draw it with)."""
        name = v.special
        if name == "crouch":  # low, butt wiggling, about to pounce
            p.scale(1.1, 0.8)
            p.rotate(math.sin(v.t * 30) * 1.5)
            return self.pose_stand, replace(v, state=State.IDLE)
        if name == "spin":
            p.rotate(math.sin(v.t * 24) * 8)
            return self.pose_stand, replace(v, state=State.WALK)
        if name == "roll":
            return self.pose_ball, v
        if name in ("air", "dazed"):
            return self.pose_stand, replace(v, state=State.FALLING)
        if name == "slide":
            return self.pose_slide, v
        if name in ("cling", "cling_sleep"):
            return self.pose_cling, v
        if name == "beg":  # sitting up, bouncing, huge pleading eyes
            p.translate(0, -abs(math.sin(v.t * 7)) * 4)
            p.rotate(math.sin(v.t * 3) * 3)
            return (lambda p_, v_, look: self.pose_sit(p_, v_, (look[0], -0.6), wide=True)), \
                replace(v, state=State.SIT, mood="hungry")
        if name == "sulk":  # slumped, head down, swaying sadly
            p.scale(1.04, 0.93)
            p.rotate(-3 + math.sin(v.t * 1.2) * 1.5)
            return (lambda p_, v_, look: self.pose_sit(p_, v_, (0.25, 1.0))), \
                replace(v, state=State.SIT, mood="sad")
        if name == "dance":
            p.translate(0, -abs(math.sin(v.t * 7)) * 7)
            p.rotate(math.sin(v.t * 7) * 9)
            return self.pose_stand, replace(v, state=State.WALK, walk_phase=v.t * 14)
        if name in ("stand", "phase", "float", "rocket"):
            if name == "phase":
                p.setOpacity(p.opacity() * (1 - 0.7 * v.special_value))
            return self.pose_stand, replace(v, state=State.IDLE)
        return self.pose_stand, replace(v, state=State.WALK)

    # --- poses (local space: x forward, ground at y=0) -----------------------
    # each returns the top of the head, where Zzz and sweat drops go

    def pose_stand(self, p: QPainter, v: PetView, look) -> QPointF:
        bk, hk = self.body_k, self.head_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        walking = v.state == State.WALK
        falling = v.state == State.FALLING
        eating = v.state == State.EAT
        swing = math.sin(v.walk_phase)
        breathe = 1 + 0.025 * math.sin(v.t * 2.4)
        if walking:
            p.translate(0, -abs(swing) * 2.5)
        cy = -(self.leg_len * self.leg_k() + ry - 5)
        hip = cy + ry * 0.3

        def leg(x, phase, shade=0):
            dx = math.sin(v.walk_phase + phase) * 6 if walking else 0
            lift = max(0.0, -math.cos(v.walk_phase + phase)) * 3 if walking else 0
            if falling:
                dx = 7 if x > 0 else -7
            self.leg(p, QPointF(x, hip), QPointF(x + dx, -5 - lift), shade)

        # far side first, darker
        leg(-rx * 0.72, math.pi, 30)
        leg(rx * 0.42, 0, 30)
        self.tail(p, v, "stand", QPointF(-rx * 0.85, cy - ry * 0.25))
        body = rig.ellipse_path(QPointF(0, cy), rx, ry * breathe)
        rig.fill_part(p, body, self.color("body"), self.markings("body"))
        leg(-rx * 0.5, 0)
        leg(rx * 0.62, math.pi)

        r = self.head_r * hk
        if eating:  # face down in the bowl, bobbing as it chews
            c = QPointF(rx * 0.95, -r * 0.75 + abs(math.sin(v.t * 7)) * 2)
            self.head(p, c, r, v, (0.3, 1.0), eyes="happy", mouth="munch")
        else:
            c = QPointF(rx * 0.6, cy - ry * 0.55 - 18 * hk)
            self.head(p, c, r, v, look, wide=falling)
        return c + QPointF(0, -r)

    def pose_sit(self, p: QPainter, v: PetView, look, wide: bool = False) -> QPointF:
        bk, hk = self.body_k, self.head_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        breathe = 1 + 0.025 * math.sin(v.t * 2.4)
        happy = v.state == State.HAPPY
        if happy:  # purring: a little happy wiggle
            p.rotate(math.sin(v.t * 16) * 2.5)

        self.leg(p, QPointF(rx * 0.32, -ry * 1.4), QPointF(rx * 0.32, -5), 30)
        haunch = rig.ellipse_path(QPointF(-rx * 0.38, -ry * 0.75), rx * 0.62, ry * 0.8)
        rig.fill_part(p, haunch, self.color("body"), self.markings("body"), 15)
        self.tail(p, v, "sit_behind", QPointF(-rx * 0.85, -ry * 0.6))
        bcy, bry = -ry * 1.55, ry * 1.45 * breathe
        body = rig.ellipse_path(QPointF(0, bcy), rx * 0.62, bry)
        rig.fill_part(p, body, self.color("body"), self.markings("chest"))
        self.leg(p, QPointF(rx * 0.12, -ry * 1.3), QPointF(rx * 0.12, -5))
        self.tail(p, v, "sit", QPointF(-rx * 0.85, -6))

        r = self.head_r * hk
        c = QPointF(rx * 0.1, bcy - bry - 10 * hk)
        self.head(p, c, r, v, look, eyes="happy" if happy else "open", wide=wide)
        return c + QPointF(0, -r)

    def pose_sleep(self, p: QPainter, v: PetView, look) -> QPointF:
        bk, hk = self.body_k, self.head_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        breathe = 1 + 0.05 * math.sin(v.t * 1.3)  # slow, deep breaths

        body = rig.ellipse_path(QPointF(-4, -ry * 0.92 * breathe), rx * 1.12, ry * 0.92 * breathe)
        rig.fill_part(p, body, self.color("body"), self.markings("body"))
        self.tail(p, v, "sleep", QPointF(-rx * 1.0, -9))

        r = (self.head_r - 2) * hk
        c = QPointF(rx * 0.62, -r * 0.92)
        p.save()
        p.translate(c)
        p.rotate(-12)  # head resting on its paws, tilted
        self.head(p, QPointF(0, 0), r, v, look, eyes="sleep", mouth="none")
        p.restore()
        for dx in (-7, 6):
            paw = rig.ellipse_path(QPointF(c.x() + dx * bk, -4), 7 * bk, 4.5 * bk)
            rig.fill_part(p, paw, self.color("leg"), self.markings("paw"))
        return c + QPointF(0, -r)

    def pose_dangle(self, p: QPainter, v: PetView, look) -> QPointF:
        """Held up by the scruff: body hangs long, paws flailing."""
        bk, hk = self.body_k, self.head_k
        flail = math.sin(v.walk_phase)
        bcy = -40 * bk
        brx, bry = self.body_ry * bk, 30 * bk
        bottom = bcy + bry

        self.tail(p, v, "dangle", QPointF(0, bottom - 6))
        for side in (-1, 1):
            self.leg(p, QPointF(side * 8 * bk, bottom - 10),
                     QPointF(side * (10 + flail * side * 4) * bk, bottom + 6 - abs(flail) * 2))
        body = rig.ellipse_path(QPointF(0, bcy), brx, bry)
        rig.fill_part(p, body, self.color("body"), self.markings("chest"))
        for side in (-1, 1):
            wave = math.sin(v.walk_phase + side) * 6
            self.leg(p, QPointF(side * 10 * bk, bcy - bry * 0.45),
                     QPointF(side * 26 * bk, bcy - bry * 0.1 + wave))

        r = (self.head_r - 1) * hk
        c = QPointF(0, bcy - bry - 12 * hk)
        self.head(p, c, r, v, look, wide=True, mouth="scream", jitter=True)
        return c + QPointF(0, -r)

    def pose_ball(self, p: QPainter, v: PetView, look) -> QPointF:
        """Curled into a ball, tumbling: v.special_value is the roll angle."""
        bk, hk = self.body_k, self.head_k
        radius = self.body_ry * bk * 1.3
        p.translate(0, -radius - 1)
        p.rotate(v.special_value)
        for angle in (200, 250, 300):  # paws poking out around the edge
            a = math.radians(angle)
            paw = rig.ellipse_path(QPointF(math.cos(a) * radius, math.sin(a) * radius), 6 * bk, 5 * bk)
            rig.fill_part(p, paw, self.color("leg"), self.markings("paw"))
        self.tail(p, v, "sit_behind", QPointF(-radius * 0.9, radius * 0.3))
        rig.fill_part(p, rig.ellipse_path(QPointF(0, 0), radius, radius), self.color("body"), self.markings("body"))
        r = (self.head_r - 6) * hk
        c = QPointF(radius * 0.35, -radius * 0.15)
        self.head(p, c, r, v, look, eyes="sleep", mouth="w")
        return QPointF(0, -radius * 1.4)

    def pose_slide(self, p: QPainter, v: PetView, look) -> QPointF:
        """Flat on its belly, legs stretched out, zooming along."""
        bk, hk = self.body_k, self.head_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        self.leg(p, QPointF(-rx * 0.6, -ry * 0.5), QPointF(-rx * 1.3, -5), 30)
        self.leg(p, QPointF(rx * 0.4, -ry * 0.6), QPointF(rx * 1.15, -7), 30)
        body = rig.ellipse_path(QPointF(-2, -ry * 0.8), rx * 1.1, ry * 0.8)
        rig.fill_part(p, body, self.color("body"), self.markings("body"))
        self.leg(p, QPointF(-rx * 0.5, -ry * 0.4), QPointF(-rx * 1.2, -4))
        self.leg(p, QPointF(rx * 0.5, -ry * 0.5), QPointF(rx * 1.25, -5))
        r = (self.head_r - 2) * hk
        c = QPointF(rx * 0.75, -r * 0.95)
        self.head(p, c, r, v, look, eyes="happy", mouth="pant")
        return c + QPointF(0, -r)

    def pose_cling(self, p: QPainter, v: PetView, look) -> QPointF:
        """Hugging the edge of the screen like a tree trunk (the wall is in front)."""
        bk, hk = self.body_k, self.head_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        asleep = v.special == "cling_sleep"
        climb = math.sin(v.walk_phase) * 3 if not asleep else 0
        p.translate(26, -8)
        bcy, bry = -ry * 1.5, ry * 1.4
        self.leg(p, QPointF(rx * 0.1, bcy - bry * 0.3), QPointF(rx * 0.95, bcy - bry * 0.8 - climb), 30)
        self.leg(p, QPointF(0, bcy + bry * 0.6), QPointF(rx * 0.9, bcy + bry * 0.6 + climb), 30)
        self.tail(p, v, "sit_behind", QPointF(-rx * 0.55, bcy + bry * 0.7))
        body = rig.ellipse_path(QPointF(0, bcy), rx * 0.62, bry)
        rig.fill_part(p, body, self.color("body"), self.markings("chest"))
        self.leg(p, QPointF(-rx * 0.05, bcy + bry * 0.5), QPointF(rx * 0.85, bcy + bry * 0.35 - climb))
        r = self.head_r * hk
        c = QPointF(-rx * 0.05, bcy - bry - 8 * hk)
        self.head(p, c, r, v, look, eyes="sleep" if asleep else "open", mouth="none" if asleep else None)
        self.leg(p, QPointF(rx * 0.15, bcy - bry * 0.45), QPointF(rx * 0.95, bcy - bry * 0.95 + climb))
        return c + QPointF(0, -r)

    # --- parts ---------------------------------------------------------------

    def leg(self, p: QPainter, top: QPointF, foot: QPointF, shade: int = 0):
        shape = rig.thick_line(rig.line_path(top, foot), self.leg_w * self.body_k)
        rig.fill_part(p, shape, self.color("leg"), self.markings("leg"), shade)

    def tail(self, p: QPainter, v: PetView, pose: str, root: QPointF):
        bk = self.body_k
        rx, ry = self.body_rx * bk, self.body_ry * bk
        kind = self.pal.get("tail_kind", self.tail_kind)
        happy = v.state in (State.HAPPY, State.EAT, State.WALK)

        if kind == "stub":
            if pose in ("stand", "sit_behind", "dangle"):
                wiggle = math.sin(v.t * (14 if happy else 3)) * 1.5
                stub = rig.ellipse_path(root + QPointF(-2, -4 + wiggle), 7 * bk, 6 * bk)
                rig.fill_part(p, stub, self.color("tail"), self.markings("tail"))
            return

        tail = QPainterPath(root)
        if kind == "curl":  # dog: a curl over the back that wags
            if pose not in ("stand", "sit_behind", "dangle"):
                return
            wag = math.sin(v.t * (18 if happy else 4)) * (8 if happy else 3)
            if pose == "dangle":
                tail.cubicTo(root + QPointF(-10, 6), root + QPointF(wag - 6, 22), root + QPointF(wag, 18))
            else:
                tip = root + QPointF(-4 + wag, -22 * bk)
                tail.cubicTo(root + QPointF(-14, 0), tip + QPointF(-14, 6), tip)
                tail.quadTo(tip + QPointF(6, -2), tip + QPointF(5, 6))
        elif pose == "stand":
            walking = v.state == State.WALK
            tip = QPointF(-rx * 1.3 + math.sin(v.t * (7 if v.state == State.EAT else 2.2)) * 6,
                          root.y() + ry * 0.25 - (48 if walking else 38) * bk)
            tail.cubicTo(root + QPointF(-14, 4), tip + QPointF(-4, 20), tip)
        elif pose == "sit":  # curled around the front paws, tip flicking
            tail.cubicTo(-rx * 0.6, 3, rx * 0.3, 3, rx * 0.72, -4)
            tail.quadTo(rx * 0.95, -6, rx * 0.95 + math.sin(v.t * 1.7) * 3, -12 - max(0, math.sin(v.t * 1.7)) * 4)
        elif pose == "sleep":
            tail.cubicTo(-rx * 0.6, 4, rx * 0.5, 4, rx * 1.05, -5)
        elif pose == "dangle":
            tip = QPointF(math.sin(v.walk_phase) * 9, -4)
            tail.cubicTo(root + QPointF(0, 12), tip + QPointF(0, -12), tip)
        else:
            return
        rig.fill_part(p, rig.thick_line(tail, self.tail_w * bk), self.color("tail"), self.markings("tail"))

    def head(self, p: QPainter, c: QPointF, r: float, v: PetView, look,
             eyes: str = "open", mouth: str | None = None, wide=False, jitter=False):
        """eyes: open | happy | sleep. mouth: w | blep | pant | munch | scream | none (None = idle_mouth)."""
        self.behind_head(p, c, r, v)
        sx, sy = self.head_shape
        rig.fill_part(p, rig.ellipse_path(c, r * sx, r * sy), self.color("head"), self.markings("head"))

        f = c + QPointF(r * 0.14, r * 0.1)  # face sits a bit forward: 3/4 view
        self.under_eyes(p, f, r)
        if self.muzzle:
            mx, my, mrx, mry = self.muzzle
            snout = rig.ellipse_path(f + QPointF(r * mx, r * my), r * mrx, r * mry)
            rig.fill_part(p, snout, self.color("muzzle"))
            nose = f + QPointF(r * mx, r * (my - mry * 0.45))
        else:
            nose = f + QPointF(0, r * 0.2)

        eye_spots = [(f + QPointF(-r * 0.38, -r * 0.14), r * 0.3),
                     (f + QPointF(r * 0.34, -r * 0.17), r * 0.36)]  # mismatched = funnier
        rig.blush(p, [f + QPointF(-r * 0.62, r * 0.28), f + QPointF(r * 0.62, r * 0.26)], r * 0.17)
        if eyes in ("sleep", "happy"):
            rig.closed_eyes(p, eye_spots, eyes)
        elif v.blink and not wide:
            rig.closed_eyes(p, eye_spots, "blink")
        else:
            rig.googly_eyes(p, eye_spots, look, wide=wide, jitter_t=v.t if jitter else None, pupil=self.pupil)
            if not wide and v.mood == "tired":
                rig.droopy_lids(p, eye_spots, self.color("head"))
            elif not wide and v.mood in ("sad", "hungry"):
                rig.worried_brows(p, eye_spots)

        mouth_at = self.nose(p, nose, r)
        if mouth is None:
            mouth = self.idle_mouth(v)
        if mouth == "scream" or (mouth == "munch" and math.sin(v.t * 14) > 0):
            rig.open_mouth(p, mouth_at, r * (0.4 if mouth == "scream" else 0.28))
        elif mouth == "pant":
            rig.pant_mouth(p, mouth_at, r * 0.42, v.t)
        elif mouth != "none":
            rig.w_mouth(p, mouth_at, r * 0.32, blep=mouth == "blep")

        if self.whiskers:
            light = self.pal.get("light_whiskers", False)
            p.setPen(QPen(QColor(235, 235, 235) if light else rig.OUTLINE, 1.4, Qt.SolidLine, Qt.RoundCap))
            for side in (-1, 1):
                for k, dy in enumerate((-0.04, 0.12)):
                    start = f + QPointF(side * r * 0.5, r * (0.2 + dy))
                    p.drawLine(start, start + QPointF(side * r * 0.55, r * (dy * 2 - 0.05 + k * 0.12)))
        self.over_head(p, c, r, v)
        draw_hat(p, self.hat, c, r, eye_spots, v.t)

    def nose(self, p: QPainter, at: QPointF, r: float) -> QPointF:
        """Draw the nose; returns where the mouth goes."""
        kind = self.nose_kind
        p.setPen(rig.outline_pen(1.6))
        if kind == "cat":
            p.setBrush(self.pal.get("nose", CAT_NOSE))
            p.drawPolygon(QPolygonF([at + QPointF(-r * 0.1, -r * 0.05), at + QPointF(r * 0.1, -r * 0.05),
                                     at + QPointF(0, r * 0.07)]))
            return at + QPointF(0, r * 0.1)
        p.setBrush(self.pal.get("nose", DARK_NOSE))
        if kind == "koala":  # big, shiny, ridiculous
            p.drawRoundedRect(at.x() - r * 0.2, at.y() - r * 0.12, r * 0.4, r * 0.48, r * 0.18, r * 0.18)
            nose_bottom = at.y() + r * 0.36
        elif kind == "goat":
            p.setBrush(Qt.NoBrush)
            p.setPen(rig.outline_pen(2.0))
            for side in (-1, 1):
                p.drawLine(at + QPointF(side * r * 0.08, 0), at + QPointF(side * r * 0.14, r * 0.05))
            nose_bottom = at.y() + r * 0.06
        else:  # dog / bear: rounded dark nose
            path = QPainterPath(at + QPointF(-r * 0.16, -r * 0.06))
            path.quadTo(at + QPointF(0, -r * 0.14), at + QPointF(r * 0.16, -r * 0.06))
            path.quadTo(at + QPointF(r * 0.12, r * 0.1), at + QPointF(0, r * 0.1))
            path.quadTo(at + QPointF(-r * 0.12, r * 0.1), at + QPointF(-r * 0.16, -r * 0.06))
            p.drawPath(path)
            nose_bottom = at.y() + r * 0.1
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 150))
        if kind != "goat":
            p.drawEllipse(at + QPointF(-r * 0.05, -r * 0.04), r * 0.04, r * 0.025)
        return QPointF(at.x(), nose_bottom + r * 0.04)

    # --- shared ear shapes ---------------------------------------------------

    def pointy_ears(self, p: QPainter, c: QPointF, r: float, height: float = 1.3,
                    inner: QColor = QColor(255, 175, 190, 200)):
        for i, side in enumerate((-1, 1)):
            ear = QPainterPath()
            ear.addPolygon(QPolygonF([c + QPointF(side * r * 0.95, -r * 0.3),
                                      c + QPointF(side * r * 0.78, -r * height),
                                      c + QPointF(side * r * 0.12, -r * 0.82)]))
            ear.closeSubpath()
            rig.fill_part(p, ear, self.color("ear", i))
            k = (height - 0.3) / 1.0
            p.setPen(Qt.NoPen)
            p.setBrush(inner)
            p.drawPolygon(QPolygonF([c + QPointF(side * r * 0.8, -r * 0.45),
                                     c + QPointF(side * r * 0.74, -r * (0.3 + 0.78 * k)),
                                     c + QPointF(side * r * 0.3, -r * 0.8)]))

    def round_ears(self, p: QPainter, c: QPointF, r: float, size: float = 0.32,
                   spread: float = 0.72, inner: QColor | None = None):
        for i, side in enumerate((-1, 1)):
            centre = c + QPointF(side * r * spread, -r * spread)
            rig.fill_part(p, rig.ellipse_path(centre, r * size, r * size), self.color("ear", i))
            if inner is not None:
                p.setPen(Qt.NoPen)
                p.setBrush(inner)
                p.drawEllipse(centre + QPointF(-side * r * 0.04, r * 0.04), r * size * 0.55, r * size * 0.55)

    def floppy_ears(self, p: QPainter, c: QPointF, r: float, v: PetView, length: float = 0.8):
        dangled = v.state == State.DRAGGED
        for i, side in enumerate((-1, 1)):
            # Qt rotates clockwise, so -side swings each ear's tip outwards
            if dangled:  # ears flap up like helicopter blades
                angle = -side * (150 + math.sin(v.t * 22 + i) * 25)
            else:
                bounce = math.sin(v.walk_phase) * 8 if v.state == State.WALK else math.sin(v.t * 1.5 + i) * 2
                angle = -side * 30 + bounce
            p.save()
            p.translate(c + QPointF(side * r * 0.88, -r * 0.55))
            p.rotate(angle)
            ear = rig.ellipse_path(QPointF(0, r * length * 0.5), r * 0.26, r * length * 0.5)
            rig.fill_part(p, ear, self.color("ear", i))
            p.restore()
