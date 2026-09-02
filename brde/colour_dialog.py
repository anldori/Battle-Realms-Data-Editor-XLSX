"""
brde.colour_dialog - the dialog that picks one colour.

Pure Qt: it knows about colours and about a list of colours to show beside the
one being picked, and nothing about workbooks, sheets or rows. `ask_colour()`
in `brde.model` is what turns a record into the arguments for it, and what
turns the answer back into cell edits.

It replaces `QColorDialog`, which came in two versions and neither was right.
Left to itself Qt hands the call to the platform's own panel, on Windows the
Win32 `ChooseColor` box: forty-eight fixed colours, a "Define Custom Colors"
flap, no hex field, no way to lift a colour off the screen, and no alpha
channel at all, so the four `Data_Beams` colours would lose theirs on the way
through. Qt's own dialog has the hex field and the alpha, and spends the same
quarter of its surface on forty-eight saturated colours that have nothing to do
with the file being edited, plus sixteen empty squares and a button for filling
them one at a time.

What replaces them is the same picking surface every current colour picker
uses, and one thing they do not have: the colours the sheet already holds,
with the row being edited ringed among them. Setting a team colour is not the
question "is this a nice blue"; it is "will this be told apart from the other
ten on a minimap", and that question can only be answered next to the answer.
"""
from __future__ import annotations

import math
from collections import namedtuple

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QGuiApplication, QLinearGradient,
                         QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QVBoxLayout, QWidget)

# One colour of the sheet's own palette: what it looks like, what to call it in
# a tooltip, and which row it came from so the row being edited can be ringed
# rather than merely drawn.
PaletteColour = namedtuple('PaletteColour', 'colour label row')

BG = QColor(247, 248, 250)
CARD = QColor(255, 255, 255)
LINE = QColor(226, 230, 237)
TEXT = QColor(31, 36, 48)
MUTED = QColor(107, 118, 134)
ACCENT = QColor(45, 108, 223)
WARN_FG = QColor(150, 88, 0)
CHECK_A = QColor(255, 255, 255)
CHECK_B = QColor(205, 210, 218)

# Three rows of eight swatches. The palette is there to be taken in at a
# glance, and Data_DialogueResources has 31 distinct colours - past this the
# grid stops being something the eye can compare against and becomes a wall.
PALETTE_MAX = 24

RADIUS = 8
BAR_H = 16
HANDLE = 7

# How close two colours have to be before the dialog says so. The closest pair
# in the vanilla file is 96 apart (the two cyans, TeamColor 6 and TeamColor 8),
# so under this is closer than any two colours the game itself ships as
# distinct teams, and the warning stays quiet on unmodified data.
TOO_CLOSE = 90


def readable_on(colour):
    """Black or white, whichever stays legible on top of `colour`."""
    r, g, b = colour.redF(), colour.greenF(), colour.blueF()
    # Rec. 709 luma, blended onto white so a transparent colour is judged as it
    # is actually painted rather than as its opaque self.
    a = colour.alphaF()
    lum = ((0.2126 * r + 0.7152 * g + 0.0722 * b) * a) + (1.0 - a)
    return QColor(0, 0, 0) if lum > 0.55 else QColor(255, 255, 255)


def distance(a, b):
    """How far apart two colours look, on the "redmean" approximation.

    Plain RGB distance calls a dark blue and a dark green further apart than
    the eye does. This is the cheap weighting that fixes the worst of it, and
    it is enough for the only question being asked: will these two be told
    apart on a minimap.
    """
    rm = (a.red() + b.red()) / 2
    dr, dg, db = a.red() - b.red(), a.green() - b.green(), a.blue() - b.blue()
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg
                     + (2 + (255 - rm) / 256) * db * db)


def paint_checker(p, rect, step=6):
    """The transparency checkerboard, under anything that can be see-through."""
    p.fillRect(rect, CHECK_A)
    for iy in range(0, rect.height(), step):
        for ix in range(0, rect.width(), step):
            if (ix // step + iy // step) % 2:
                p.fillRect(rect.left() + ix, rect.top() + iy,
                           min(step, rect.width() - ix),
                           min(step, rect.height() - iy), CHECK_B)


def paint_handle(p, centre, r=HANDLE):
    """A white ring with a dark hairline, legible on any colour under it."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(0, 0, 0, 90), 3))
    p.drawEllipse(centre, r + 1, r + 1)
    p.setPen(QPen(QColor(255, 255, 255), 2))
    p.drawEllipse(centre, r, r)


class SVPlane(QWidget):
    """Saturation across, value down, for one hue.

    Painted as three gradients rather than pixel by pixel: the hue flat, white
    fading out to the right, black fading in downwards. That costs nothing to
    redraw, so the hue slider can drive it live.
    """

    changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 232)
        self._h, self._s, self._v = 0.0, 1.0, 1.0
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_hsv(self, h, s, v):
        self._h, self._s, self._v = h, s, v
        self.update()

    def handle_pos(self):
        """Where the ring is drawn, which is not quite where the colour is.

        At full saturation and full value the point is the top right corner,
        and a ring centred on it would be clipped to a quarter circle by the
        edge of the widget. The ring is therefore kept a radius inside, and
        the plane still reports the colour the mouse actually landed on.
        """
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        pad = HANDLE + 2
        x = r.left() + self._s * r.width()
        y = r.top() + (1.0 - self._v) * r.height()
        return QPoint(int(min(r.right() - pad, max(r.left() + pad, x))),
                      int(min(r.bottom() - pad, max(r.top() + pad, y))))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        p.save()
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor.fromHsvF(self._h, 1.0, 1.0))
        white = QLinearGradient(r.left(), 0, r.right(), 0)
        white.setColorAt(0.0, QColor(255, 255, 255))
        white.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), white)
        black = QLinearGradient(0, r.top(), 0, r.bottom())
        black.setColorAt(0.0, QColor(0, 0, 0, 0))
        black.setColorAt(1.0, QColor(0, 0, 0))
        p.fillRect(self.rect(), black)
        p.restore()
        p.setPen(QPen(LINE, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        paint_handle(p, self.handle_pos())

    def _take(self, pos):
        w, h = max(1, self.width() - 1), max(1, self.height() - 1)
        s = min(1.0, max(0.0, pos.x() / w))
        v = 1.0 - min(1.0, max(0.0, pos.y() / h))
        self._s, self._v = s, v
        self.update()
        self.changed.emit(s, v)

    def mousePressEvent(self, e):
        self._take(e.position())

    def mouseMoveEvent(self, e):
        self._take(e.position())


class Bar(QWidget):
    """A horizontal track with a round handle. Hue and alpha share it."""

    changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(BAR_H + HANDLE * 2)
        self._t = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def track(self):
        y = (self.height() - BAR_H) // 2
        return QRect(HANDLE, y, self.width() - HANDLE * 2, BAR_H)

    def set_value(self, t):
        self._t = min(1.0, max(0.0, t))
        self.update()

    def fill(self, p, rect):
        raise NotImplementedError

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tr = self.track()
        path = QPainterPath()
        path.addRoundedRect(QRectF(tr), BAR_H / 2, BAR_H / 2)
        p.save()
        p.setClipPath(path)
        self.fill(p, tr)
        p.restore()
        p.setPen(QPen(LINE, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        paint_handle(p, QPoint(tr.left() + int(self._t * tr.width()),
                               tr.center().y()))

    def _take(self, pos):
        tr = self.track()
        self._t = min(1.0, max(0.0, (pos.x() - tr.left()) / max(1, tr.width())))
        self.update()
        self.changed.emit(self._t)

    def mousePressEvent(self, e):
        self._take(e.position())

    def mouseMoveEvent(self, e):
        self._take(e.position())


class HueBar(Bar):
    def fill(self, p, rect):
        g = QLinearGradient(rect.left(), 0, rect.right(), 0)
        for i in range(7):
            g.setColorAt(i / 6.0, QColor.fromHsvF(min(0.999, i / 6.0), 1, 1))
        p.fillRect(rect, g)


class AlphaBar(Bar):
    """Transparent to opaque, in the colour being picked, over a checkerboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._c = QColor(0, 0, 0)

    def set_colour(self, c):
        self._c = QColor(c)
        self.update()

    def fill(self, p, rect):
        paint_checker(p, rect, 5)
        clear, solid = QColor(self._c), QColor(self._c)
        clear.setAlpha(0)
        solid.setAlpha(255)
        g = QLinearGradient(rect.left(), 0, rect.right(), 0)
        g.setColorAt(0.0, clear)
        g.setColorAt(1.0, solid)
        p.fillRect(rect, g)


class Compare(QWidget):
    """The colour in the file, and the colour about to replace it.

    One rounded chip split down the middle, because either colour on its own
    says very little. The left half is clickable: it is the way back to what
    the file holds, which the stock dialog offers only by being cancelled.
    """

    reverted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self._old = QColor(255, 255, 255)
        self._new = QColor(255, 255, 255)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_colours(self, old, new):
        self._old, self._new = QColor(old), QColor(new)
        self.setToolTip(f'In the file: {self._old.name().upper()}\n'
                        f'New: {self._new.name().upper()}\n'
                        'Click the left half to put the old colour back.')
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, RADIUS, RADIUS)
        left = self.rect().adjusted(0, 0, -self.width() // 2, 0)
        right = left.translated(self.width() // 2, 0)
        halves = ((left, self._old, 'in the file', Qt.AlignmentFlag.AlignLeft),
                  (right, self._new, 'new', Qt.AlignmentFlag.AlignRight))
        p.save()
        p.setClipPath(path)
        for rect, col, _txt, _align in halves:
            if col.alpha() < 255:
                paint_checker(p, rect, 6)
            p.fillRect(rect, col)
        p.restore()
        p.setPen(QPen(LINE, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        # Before anything is picked both halves hold the same colour, and with
        # no seam the chip reads as one block that says nothing.
        p.setPen(QPen(QColor(255, 255, 255, 150), 1))
        p.drawLine(right.left(), 4, right.left(), self.height() - 4)
        f = QFont()
        f.setPointSize(8)
        p.setFont(f)
        for rect, col, txt, align in halves:
            p.setPen(readable_on(col))
            p.drawText(rect.adjusted(9, 0, -9, -6),
                       Qt.AlignmentFlag.AlignBottom | align, txt)

    def mousePressEvent(self, e):
        if e.position().x() < self.width() / 2:
            self.reverted.emit()


class Palette(QWidget):
    """The colours the sheet already holds, as round swatches.

    The one belonging to the row being edited is ringed in the accent colour,
    so the palette says "here is where you are among them" rather than merely
    "here are some colours".
    """

    picked = pyqtSignal(QColor)

    DOT = 22
    GAP = 7
    COLS = 8
    # Room around the grid for what is drawn outside a swatch: the ring on the
    # row being edited sits 2.5 pixels clear of it, and even without a ring the
    # first swatch would meet the edge of the widget exactly and lose the outer
    # half of its own outline to it - which reads as a circle with a flat side.
    PAD = 3

    def __init__(self, entries, current_row=None, parent=None):
        super().__init__(parent)
        self._entries = list(entries)
        self._current = current_row
        self._hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self.sizeHint().height())

    def _rows(self):
        return max(1, (len(self._entries) + self.COLS - 1) // self.COLS)

    def _span(self, n):
        return self.PAD * 2 + n * self.DOT + (n - 1) * self.GAP

    def sizeHint(self):
        return QSize(self._span(self.COLS), self._span(self._rows()))

    def dot_rect(self, i):
        c, r = i % self.COLS, i // self.COLS
        return QRect(self.PAD + c * (self.DOT + self.GAP),
                     self.PAD + r * (self.DOT + self.GAP),
                     self.DOT, self.DOT)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, entry in enumerate(self._entries):
            r = QRectF(self.dot_rect(i))
            if entry.colour.alpha() < 255:
                p.save()
                path = QPainterPath()
                path.addEllipse(r)
                p.setClipPath(path)
                paint_checker(p, self.dot_rect(i), 5)
                p.restore()
            p.setBrush(entry.colour)
            p.setPen(QPen(LINE, 1))
            p.drawEllipse(r.adjusted(0.5, 0.5, -0.5, -0.5))
            if entry.row == self._current or i == self._hover:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(ACCENT if entry.row == self._current else MUTED,
                              2))
                p.drawEllipse(r.adjusted(-2.5, -2.5, 2.5, 2.5))

    def index_at(self, pos):
        for i in range(len(self._entries)):
            if self.dot_rect(i).contains(pos):
                return i
        return -1

    def mouseMoveEvent(self, e):
        i = self.index_at(e.position().toPoint())
        if i != self._hover:
            self._hover = i
            self.setToolTip(self._entries[i].label if i >= 0 else '')
            self.update()

    def leaveEvent(self, _e):
        self._hover = -1
        self.update()

    def mousePressEvent(self, e):
        i = self.index_at(e.position().toPoint())
        if i >= 0:
            self.picked.emit(self._entries[i].colour)


class _CommitOnReturn(QObject):
    """Enter in the hex box commits the hex, not the dialog.

    A QLineEdit inside a QDialog answers Enter by triggering the default
    button, so typing a hex and pressing Enter would close the dialog on a
    colour the user never saw applied. The first Enter therefore applies the
    text and stops there; once the box already reads as the current colour,
    there is nothing left to apply and Enter goes through to "Set colour" as
    it normally would.
    """

    def __init__(self, dialog):
        super().__init__(dialog)
        self.d = dialog

    def eventFilter(self, obj, ev):
        if (ev.type() == QEvent.Type.KeyPress
                and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)):
            if self.d.hex_is_pending():
                self.d.apply_hex()
                return True
        return False


def label(text, muted=False, bold=False, warn=False):
    lb = QLabel(text)
    f = lb.font()
    f.setBold(bold)
    if muted:
        f.setPointSize(max(7, f.pointSize() - 1))
    lb.setFont(f)
    lb.setStyleSheet('color: %s;'
                     % (WARN_FG if warn else MUTED if muted else TEXT).name())
    return lb


STYLE = """
QDialog { background: %(bg)s; }
QLabel { color: %(text)s; }
QLineEdit {
    background: %(card)s; border: 1px solid %(line)s; border-radius: 6px;
    padding: 6px 8px; color: %(text)s; selection-background-color: %(accent)s;
}
QLineEdit:focus { border: 1px solid %(accent)s; }
QPushButton {
    background: %(card)s; border: 1px solid %(line)s; border-radius: 7px;
    padding: 7px 16px; color: %(text)s;
}
QPushButton:hover { border: 1px solid %(muted)s; }
QPushButton#primary {
    background: %(accent)s; border: 1px solid %(accent)s; color: white;
    font-weight: bold;
}
QPushButton#primary:hover { background: #2559b8; }
""" % {'bg': BG.name(), 'card': CARD.name(), 'line': LINE.name(),
       'text': TEXT.name(), 'muted': MUTED.name(), 'accent': ACCENT.name()}


class ColourDialog(QDialog):
    """Pick one colour, with the colours the file already holds beside it."""

    def __init__(self, colour, palette=(), current_row=None, alpha=False,
                 heading='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('Pick colour')
        self.setStyleSheet(STYLE)
        self._alpha = alpha
        self._entries = list(palette)
        self._row = current_row
        self._old = QColor(colour)
        self._c = QColor(colour)
        # Grey and black have no hue at all - QColor answers -1 - so the hue
        # is kept here rather than read back off the colour. Dragging the
        # value down to black and up again returns the colour that was there
        # instead of snapping to red, and the hue slider does not jump about
        # while the value slides through zero.
        self._h = max(0.0, self._c.hueF())

        self.plane = SVPlane()
        self.hue = HueBar()
        self.abar = AlphaBar()
        self.compare = Compare()
        self.hex = QLineEdit()
        self.hex.setFont(QFont('Consolas', 11))
        self.hex.setMaxLength(7)
        self.hex.installEventFilter(_CommitOnReturn(self))
        self.chans = [QLineEdit() for _ in range(4 if alpha else 3)]
        for e in self.chans:
            e.setFixedWidth(52)
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(self.plane, 1)
        left.addWidget(self.hue)
        if alpha:
            left.addWidget(self.abar)
        else:
            self.abar.hide()

        right = QVBoxLayout()
        right.setSpacing(8)
        if heading:
            right.addWidget(label(heading, bold=True))
        right.addWidget(self.compare)
        # The hex box holds red, green and blue only. Qt writes an alpha into
        # a hex as #AARRGGBB while the rest of the world reads #RRGGBBAA, and
        # a value that means two things is worse than one the slider owns
        # outright - so alpha is a channel box and a slider, never a hex.
        right.addWidget(label('Hex', muted=True))
        right.addWidget(self.hex)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        for i, name in enumerate(('R', 'G', 'B', 'A')[:len(self.chans)]):
            grid.addWidget(label(name, muted=True), 0, i,
                           Qt.AlignmentFlag.AlignHCenter)
            grid.addWidget(self.chans[i], 1, i)
        right.addLayout(grid)
        right.addSpacing(4)
        self.pal = Palette(self._entries, current_row)
        if self._entries:
            right.addWidget(label('Colours in this sheet', muted=True))
            right.addWidget(self.pal)
        else:
            self.pal.hide()
        self.warn = label('', muted=True, warn=True)
        self.warn.setWordWrap(True)
        right.addWidget(self.warn)
        right.addStretch(1)

        cols = QHBoxLayout()
        cols.setSpacing(16)
        cols.addLayout(left, 1)
        cols.addLayout(right)

        self.b_screen = QPushButton('Pick from screen')
        self.b_cancel = QPushButton('Cancel')
        self.b_ok = QPushButton('Set colour')
        self.b_ok.setObjectName('primary')
        self.b_ok.setDefault(True)
        bottom = QHBoxLayout()
        bottom.addWidget(self.b_screen)
        bottom.addStretch(1)
        bottom.addWidget(self.b_cancel)
        bottom.addWidget(self.b_ok)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 14)
        outer.setSpacing(14)
        outer.addLayout(cols, 1)
        outer.addLayout(bottom)

        self.plane.changed.connect(self._from_plane)
        self.hue.changed.connect(self._from_hue)
        self.abar.changed.connect(self._from_alpha)
        self.pal.picked.connect(self.set_colour)
        self.compare.reverted.connect(lambda: self.set_colour(self._old))
        self.hex.editingFinished.connect(self.apply_hex)
        for e in self.chans:
            e.editingFinished.connect(self._from_channels)
        self.b_cancel.clicked.connect(self.reject)
        self.b_ok.clicked.connect(self.accept)
        self.b_screen.clicked.connect(self.start_screen_pick)

        self._picking = False
        self._sync()

    # ------------------------------------------------------------- state
    def colour(self):
        return QColor(self._c)

    def set_colour(self, c):
        c = QColor(c)
        if not self._alpha:
            c.setAlpha(255)
        self._c = c
        if c.hueF() >= 0:
            self._h = c.hueF()
        self._sync()

    def _sync(self):
        """Put the colour into every control, including the one that set it.

        An earlier version skipped any field that had focus, on the grounds
        that text should not be rewritten under the caret. The hex box holds
        focus from the moment the dialog opens, so that rule left it reading
        the old colour while the plane, the channels and the preview had all
        moved on. Nothing here is typed into continuously - the text boxes
        report on editingFinished, which is a keypress or a focus leaving -
        so there is no caret to protect and every control is simply told.
        """
        _h, s, v, a = self._c.getHsvF()
        self.plane.set_hsv(self._h, s, v)
        self.hue.set_value(self._h)
        self.abar.set_colour(self._c)
        self.abar.set_value(a)
        self.compare.set_colours(self._old, self._c)
        self.hex.setText(self._c.name(QColor.NameFormat.HexRgb).upper())
        vals = [self._c.red(), self._c.green(), self._c.blue(),
                self._c.alpha()]
        for e, val in zip(self.chans, vals):
            e.setText(str(val))
        self._warn_if_close()

    def near_row(self):
        """The palette entry this colour is about to be confused with, or None.

        Not a refusal and not a dialog: two teams are allowed to look alike if
        that is what the mod wants. It is the one thing the sheet knows and
        the person picking cannot see, so it is said quietly and in place.
        """
        near = sorted((distance(self._c, e.colour), i)
                      for i, e in enumerate(self._entries)
                      if e.row != self._row or self._row is None)
        if near and near[0][0] < TOO_CLOSE:
            return self._entries[near[0][1]]
        return None

    def _warn_if_close(self):
        entry = self.near_row()
        if entry is None:
            self.warn.setText('')
            return
        # The label carries the row number after a double space, which is for
        # a tooltip rather than for a sentence.
        self.warn.setText('⚠  Close to %s - hard to tell apart in play.'
                          % entry.label.split('  ')[0])

    # ------------------------------------------------------------ inputs
    def _from_plane(self, s, v):
        self.set_colour(QColor.fromHsvF(self._h, s, v, self._c.alphaF()))

    def _from_hue(self, t):
        self._h = min(0.999, t)
        _h, s, v, a = self._c.getHsvF()
        self.set_colour(QColor.fromHsvF(self._h, s, v, a))

    def _from_alpha(self, t):
        c = QColor(self._c)
        c.setAlphaF(t)
        self._c = c
        self._sync()

    def hex_is_pending(self):
        """True when the hex box holds a colour that is not the current one."""
        c = self._parse_hex()
        return c is not None and c.rgb() != self._c.rgb()

    def _parse_hex(self):
        txt = self.hex.text().strip()
        if txt and not txt.startswith('#'):
            txt = '#' + txt
        c = QColor(txt)
        return c if c.isValid() else None

    def apply_hex(self):
        # Unparseable text puts the current colour back rather than clearing
        # it, so half a hex can never be committed by pressing Enter.
        c = self._parse_hex()
        self.set_colour(c if c is not None else self._c)

    def _from_channels(self):
        vals = []
        cur = [self._c.red(), self._c.green(), self._c.blue(), self._c.alpha()]
        for e, old in zip(self.chans, cur):
            try:
                vals.append(min(255, max(0, int(e.text()))))
            except ValueError:
                vals.append(old)
        while len(vals) < 4:
            vals.append(self._c.alpha())
        self.set_colour(QColor(*vals))

    # ------------------------------------------------- pick from screen
    def start_screen_pick(self):
        self._picking = True
        self.grabMouse(Qt.CursorShape.CrossCursor)

    def screen_colour(self, gpos):
        scr = QGuiApplication.screenAt(gpos) or QGuiApplication.primaryScreen()
        if scr is None:
            return None
        img = scr.grabWindow(0, gpos.x(), gpos.y(), 1, 1).toImage()
        return None if img.isNull() else QColor(img.pixel(0, 0))

    def mouseMoveEvent(self, e):
        if self._picking:
            c = self.screen_colour(e.globalPosition().toPoint())
            if c is not None:
                self.set_colour(c)

    def mouseReleaseEvent(self, e):
        if not self._picking:
            return
        self._picking = False
        self.releaseMouse()
        c = self.screen_colour(e.globalPosition().toPoint())
        if c is not None:
            self.set_colour(c)


def pick_colour(parent, current, palette=(), current_row=None, alpha=False,
                heading=''):
    """Run the dialog. The chosen QColor, or None if it was cancelled."""
    d = ColourDialog(current, palette, current_row, alpha, heading, parent)
    if d.exec() != QDialog.DialogCode.Accepted:
        return None
    return d.colour()
