"""
brde.model - Table model, cell delegate and undo commands for the data grid.
"""
from __future__ import annotations

from PyQt6.QtCore import (QAbstractTableModel, QEvent, QModelIndex, QObject,
                          QSortFilterProxyModel, Qt, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QFont, QPainter, QPixmap,
                         QUndoCommand)
from PyQt6.QtWidgets import (QColorDialog, QComboBox, QCompleter,
                             QStyledItemDelegate, QLineEdit)

EDITED_BG = QColor(255, 243, 205)
EDITED_FG = QColor(140, 90, 0)
SWATCH_EDGE = QColor(120, 132, 150)
ENUM_BG = QColor(238, 246, 255)
KEY_BG = QColor(240, 240, 240)
INVALID_FG = QColor(190, 60, 60)
DIFF_BG = QColor(232, 221, 250)          # cell differs from the compared file


class SheetModel(QAbstractTableModel):
    """Displays one sheet. Enum columns render as "code - DESCRIPTION"."""

    valueChanged = pyqtSignal(str, int, int)

    def __init__(self, book, sheet_name, undo_stack, parent=None):
        super().__init__(parent)
        self.book = book
        self.sheet = sheet_name
        self.sd = book.sheets[sheet_name]
        self.undo = undo_stack
        self.show_desc = True
        self._nrows = max(len(self.sd.rows), 1)
        self._ncols = max(len(self.sd.headers), 1)

    def append_rows(self, count=1):
        self.beginInsertRows(QModelIndex(), self._nrows, self._nrows + count - 1)
        self._nrows += count
        self.endInsertRows()
        return self._nrows - count

    # ---------------------------------------------------------- basic
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._nrows

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self._ncols

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self.sd.headers[section] if section < len(self.sd.headers) else ''
            if role == Qt.ItemDataRole.ToolTipRole:
                name = self.sd.headers[section] if section < len(self.sd.headers) else ''
                e = self.sd.col_enum.get(section)
                if e == '@bool':
                    return f'{name}\nType: Yes/No (0 or 1)'
                if e:
                    return f'{name}\nReferences: Enum_{e}'
                return f'{name}\nType: free number / text'
            if role == Qt.ItemDataRole.FontRole and section in self.sd.col_enum:
                f = QFont()
                f.setBold(True)
                return f
        else:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section + 2)      # real Excel row number
        return None

    # ---------------------------------------------------------- data
    def raw(self, row, col):
        return self.book.value(self.sheet, row, col)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        val = self.raw(r, c)
        tbl = self.book.enum_for(self.sheet, c)

        if role == Qt.ItemDataRole.DisplayRole:
            if val is None:
                return ''
            if tbl and self.show_desc and isinstance(val, int):
                d = tbl.code2desc.get(val)
                return f'{val} - {d}' if d else str(val)
            return str(val)

        if role == Qt.ItemDataRole.EditRole:
            return '' if val is None else val

        if role == Qt.ItemDataRole.BackgroundRole:
            if (self.sheet, r, c) in self.book.edits:
                return QBrush(EDITED_BG)
            if (self.sheet, r, c) in self.book.diff_cells:
                return QBrush(DIFF_BG)
            if c == 0:
                return QBrush(KEY_BG)
            if tbl:
                return QBrush(ENUM_BG)

        if role == Qt.ItemDataRole.ForegroundRole:
            if (self.sheet, r, c) in self.book.edits:
                return QBrush(EDITED_FG)
            if tbl and isinstance(val, int) and val not in tbl.codes:
                return QBrush(INVALID_FG)

        if role == Qt.ItemDataRole.ToolTipRole:
            head = self.sd.headers[c] if c < len(self.sd.headers) else ''
            lines = [f'{head}  (row {r + 2})']
            if tbl:
                lines.append(f'Enum_{tbl.name}')
                if isinstance(val, int) and val not in tbl.codes:
                    lines.append('!! Code does not exist in the enum table')
            if (self.sheet, r, c) in self.book.edits:
                lines.append(f'Original: {self.book.original.get((self.sheet, r, c))}')
            d = self.book.diff_cells.get((self.sheet, r, c))
            if d:
                lines.append(f'--- compared with {self.book.diff_label} ---')
                lines.append(f'This file: {d[0]}')
                lines.append(f'Other file: {d[1]}')
            g = self.book.colour_group(self.sheet, c)
            if g:
                col = qcolour(self.book.colour_at(self.sheet, r, g))
                lines.append(f'{g.label}: '
                             + (colour_text(col, g) if col else 'incomplete'))
                lines.append('Right-click to pick this colour.')
            elif c == 0 and self.sd.colours:
                names = ' and '.join(x.label for x in self.sd.colours)
                lines.append(f'Right-click to set {names} in one go.')
            return '\n'.join(lines)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if isinstance(val, (int, float)) and not tbl:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        r, c = index.row(), index.column()
        new = coerce(value, self.raw(r, c))
        old = self.raw(r, c)
        if new == old:
            return False
        self.undo.push(SetValueCommand(self, r, c, old, new))
        return True

    def apply_value(self, r, c, value):
        self.book.set_value(self.sheet, r, c, value)
        idx = self.index(r, c)
        self.dataChanged.emit(idx, idx)
        # The colour band runs under every column of the group, so changing one
        # channel repaints cells the edit did not touch.
        g = self.book.colour_group(self.sheet, c)
        if g:
            cols = g.columns
            self.dataChanged.emit(self.index(r, min(cols)),
                                  self.index(r, max(cols)))
        self.valueChanged.emit(self.sheet, r, c)

    def refresh_all(self):
        self.beginResetModel()
        self.endResetModel()


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def coerce(value, previous):
    """Convert user-typed text into the right type (int / float / str / None)."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    s = str(value).strip()
    if s == '':
        return None
    # 'code - DESCRIPTION' coming back from a combobox.
    # Split on ' - ' with the spaces, never a bare '-', so a negative code such as
    # '-1 - NONE' keeps its sign. Only strip the label when what precedes the
    # separator really is a number, so plain text like 'Foo - Bar' survives.
    for sep in (' - ', ' — '):
        if sep in s:
            head = s.split(sep, 1)[0].strip()
            if _is_number(head):
                s = head
                break
    try:
        return int(s)
    except ValueError:
        pass
    try:
        f = float(s)
        return int(f) if f.is_integer() and isinstance(previous, int) else f
    except ValueError:
        pass
    return s


class SetValueCommand(QUndoCommand):
    def __init__(self, model, r, c, old, new):
        head = model.sd.headers[c] if c < len(model.sd.headers) else f'col {c}'
        super().__init__(f'{model.sheet}.{head} [{r + 2}]: {old} → {new}')
        self.m, self.r, self.c, self.old, self.new = model, r, c, old, new

    def redo(self):
        self.m.apply_value(self.r, self.c, self.new)

    def undo(self):
        self.m.apply_value(self.r, self.c, self.old)


class MultiSetCommand(QUndoCommand):
    """Apply values to several cells at once (paste, bulk clear, bulk revert)."""

    def __init__(self, model, cells, text='Edit multiple cells'):
        super().__init__(text)
        self.m = model
        self.cells = cells      # [(r, c, old, new)]

    def redo(self):
        for r, c, _o, n in self.cells:
            self.m.apply_value(r, c, n)

    def undo(self):
        for r, c, o, _n in self.cells:
            self.m.apply_value(r, c, o)


# ------------------------------------------------------------------ colours
def qcolour(rgba):
    """(r, g, b, a) floats 0..1 -> QColor. `rgba` may be None."""
    if rgba is None:
        return None
    r, g, b, a = rgba
    return QColor.fromRgbF(r, g, b, a)


_SWATCH_CACHE = {}


def swatch(colour, w=26, h=14):
    """A bordered rectangle of `colour`, for putting next to a number.

    Qt paints a bare QColor in DecorationRole as an unbordered block, which
    makes white and near-white channels disappear into the cell. Semi-transparent
    colours are drawn over a checkerboard, the way every paint program shows
    them, so an alpha of 0 does not read as "white".
    """
    key = (colour.rgba(), w, h)
    hit = _SWATCH_CACHE.get(key)
    if hit is not None:
        return hit
    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    if colour.alphaF() < 1.0:
        p.fillRect(0, 0, w, h, QColor(255, 255, 255))
        step, grey = 5, QColor(205, 210, 218)
        for y in range(0, h, step):
            for x in range(0, w, step):
                if (x // step + y // step) % 2:
                    p.fillRect(x, y, step, step, grey)
    p.fillRect(0, 0, w, h, colour)
    p.setPen(SWATCH_EDGE)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(0, 0, w - 1, h - 1)
    p.end()
    _SWATCH_CACHE[key] = pm
    return pm


BAND_H = 6              # thickness of the colour band under a group of cells
_CHECK = 3              # checkerboard square inside the band, for alpha


def colour_band(book, sheet, row, col):
    """(colour, joins_right) for the band under this cell, or None.

    The band is drawn along the bottom of every column of a colour group, so the
    run of cells that makes the colour carries one continuous stripe. It is not
    a decoration inside a cell: a swatch in the R cell reads as "R is blue" and
    sits beside a value of 0, which is the one thing the preview must not say.
    The band belongs to the space under a span of columns, and its width is the
    statement - these three cells are one colour.

    `joins_right` is True when the next column is in the same group, and the
    band is then drawn one pixel wider so the gridline does not chop it up.
    """
    group = book.colour_group(sheet, col)
    if group is None:
        return None
    colour = qcolour(book.colour_at(sheet, row, group))
    if colour is None:
        return None
    return colour, (col + 1) in group.columns


def paint_colour_band(painter, rect, colour, joins_right=False):
    """Draw `colour` as a band along the bottom edge of `rect`.

    A hairline rules the top of the band, for the same reason the swatches have
    a border: Data_Beams.IntPoint1 is opaque white on several rows, and an
    unruled white band on a white cell is no band at all.
    """
    h = min(BAND_H, rect.height())
    x, y = rect.left(), rect.bottom() - h + 1
    w = rect.width() + (1 if joins_right else 0)
    painter.fillRect(x, y, w, 1, SWATCH_EDGE)
    y, h = y + 1, h - 1
    if colour.alphaF() < 1.0:
        # A 10% alpha band is invisible against the cell and would read as "no
        # colour at all", so it goes over the same checkerboard the swatches use.
        painter.fillRect(x, y, w, h, QColor(255, 255, 255))
        grey = QColor(205, 210, 218)
        for iy in range(0, h, _CHECK):
            for ix in range(0, w, _CHECK):
                if (ix // _CHECK + iy // _CHECK) % 2:
                    painter.fillRect(x + ix, y + iy,
                                     min(_CHECK, w - ix), min(_CHECK, h - iy),
                                     grey)
    painter.fillRect(x, y, w, h, colour)


def colour_text(colour, group=None):
    """'#4A7BE0' - with the alpha spelled out when the group carries one."""
    hexed = '#%02X%02X%02X' % (colour.red(), colour.green(), colour.blue())
    if group is not None and group.alpha is not None:
        return f'{hexed}  alpha {colour.alphaF():.2f}'
    return hexed


def readable_on(colour):
    """Black or white, whichever stays legible on top of `colour`."""
    r, g, b = colour.redF(), colour.greenF(), colour.blueF()
    # Rec. 709 luma, blended onto white so a transparent colour is judged as it
    # is actually painted rather than as its opaque self.
    a = colour.alphaF()
    lum = ((0.2126 * r + 0.7152 * g + 0.0722 * b) * a) + (1.0 - a)
    return QColor(0, 0, 0) if lum > 0.55 else QColor(255, 255, 255)


def short_label(group):
    """The group's name with the word "colour" taken off the end.

    The label is the workbook's own wording and half of it already says colour:
    Data_Beams names its groups HeadColor and TailColor, and a group with
    nothing around its channels - Data_TeamColors, whose columns are the bare R,
    G and B - is called Colour outright. Dropping the word leaves 'Head' and '',
    so 'Pick Head colour...' and 'Pick colour...' rather than a stutter.
    """
    name = group.label
    for word in ('colour', 'color'):
        if name.lower().endswith(word):
            return name[:-len(word)]
    return name


def pick_label(groups):
    """Menu text for picking one colour, or several at once.

    Several at once names every group it will overwrite. A menu entry that sets
    four colours from one dialog has to say so before it is clicked - the four
    Data_Beams colours are the two ends and two waypoints of one gradient, and
    flattening them is a fair thing to ask for but never a thing to do by
    surprise.
    """
    if not isinstance(groups, (list, tuple)):
        groups = [groups]
    if len(groups) == 1:
        name = short_label(groups[0])
        return f'Pick {name} colour...' if name else 'Pick colour...'
    names = ' + '.join(short_label(g) or g.label for g in groups)
    return f'Pick colour ({names})...'


def colour_edits(book, sheet, row, group, colour):
    """[(col, value)] for the channels `colour` actually changes.

    A channel is left alone when it already renders to the same 8-bit level, so
    re-picking the colour that is on screen edits nothing and the dirty count
    stays honest. Without it every pick would rewrite all three channels, since
    0.449999988079071 never round-trips through a 0..255 dialog unchanged.
    """
    want = {'r': colour.redF(), 'g': colour.greenF(), 'b': colour.blueF(),
            'a': colour.alphaF()}
    out = []
    for ch in ('r', 'g', 'b', 'a'):
        col = getattr(group, {'r': 'red', 'g': 'green', 'b': 'blue',
                              'a': 'alpha'}[ch])
        if col is None:
            continue
        old = group.decode(book.value(sheet, row, col))
        if old is not None and round(old * 255) == round(want[ch] * 255):
            continue
        out.append((col, group.encode(want[ch])))
    return out


def ask_colour(parent, book, sheet, row, groups, title=None):
    """Show the colour dialog and apply the answer to one or more colours.

    `groups` is a single ColourGroup or a list of them. Data_TeamColors keeps
    the team colour and the minimap colour as two separate groups holding the
    same colour, so setting them one at a time is two dialogs to say one thing;
    passing both here makes it one dialog and one undo step.

    Returns [(col, value)] for the channels to write, [] when nothing changed,
    and None when the dialog was cancelled - the three cases the caller has to
    tell apart before pushing an undo command.
    """
    if not isinstance(groups, (list, tuple)):
        groups = [groups]
    # The dialog opens on the first group's colour, which is the one the row
    # reads left to right - and on Data_TeamColors they are the same colour
    # anyway. Alpha is offered as soon as any group has a channel for it;
    # groups without one simply ignore it.
    current = (qcolour(book.colour_at(sheet, row, groups[0]))
               or QColor(255, 255, 255))
    opts = (QColorDialog.ColorDialogOption.ShowAlphaChannel
            if any(g.alpha is not None for g in groups)
            else QColorDialog.ColorDialogOption(0))
    if title is None:
        name = ' + '.join(short_label(g) or g.label for g in groups)
        title = f'{name} - {sheet}'
    picked = QColorDialog.getColor(current, parent, title, opts)
    if not picked.isValid():
        return None
    out = []
    for g in groups:
        out.extend(colour_edits(book, sheet, row, g, picked))
    return out


# ------------------------------------------------------------------ combo boxes
def _select_all(le):
    try:
        le.selectAll()
    except RuntimeError:
        # The editor was closed inside the same event loop turn that focused it,
        # which happens when a double-click lands on another cell straight away.
        pass


class _SelectOnFocus(QObject):
    """Event filter that selects a combobox's text when it gains focus.

    Three details, and each one was arrived at the hard way.

    FocusIn goes to the COMBOBOX, not to its line edit. An editable QComboBox
    keeps the line edit as a child but takes focus itself, so a filter installed
    on the line edit is never called even though `lineEdit().hasFocus()` reports
    True afterwards. Both objects are filtered here because the mouse events go
    to the line edit while the focus events go to the combobox.

    Selecting inside FocusIn alone does not survive a click: the press and
    release arrive after it and the release places the caret. So FocusIn only
    ARMS the selection, which is then made again on the mouse release that
    completes the click. Focus arriving from the keyboard gets its selection
    from FocusIn and never sees a release, which is why both are needed.

    The obvious alternative - deferring `selectAll` by a zero-delay timer so it
    lands after the release - does work, and must not be used. Inside a QDialog
    it leaves the combobox holding focus permanently: `setFocus()` on any other
    widget in the window is then silently ignored and no FocusOut is ever
    delivered, so the box can never be tabbed or clicked out of.

    A keypress disarms, so once typing has begun a click places the caret the
    way an address bar does, for when the text is meant to be edited rather
    than replaced.
    """

    def __init__(self, cb):
        super().__init__(cb)
        self._cb = cb
        self._armed = False
        cb.installEventFilter(self)
        cb.lineEdit().installEventFilter(self)

    def eventFilter(self, _obj, ev):
        t = ev.type()
        if t == QEvent.Type.FocusIn:
            self._armed = True
            _select_all(self._cb.lineEdit())
        elif t == QEvent.Type.MouseButtonRelease and self._armed:
            self._armed = False
            _select_all(self._cb.lineEdit())
        elif t in (QEvent.Type.KeyPress, QEvent.Type.FocusOut):
            self._armed = False
        return False


def select_all_on_focus(cb):
    """Make an editable combobox replace its contents on the first keystroke.

    Both editable comboboxes in the app are really search boxes over a list too
    long to scroll - 155 units in the comparison picker, 2,900 codes in some
    enum columns - and both open showing the value already in force. Without
    this, focusing one drops a caret into the middle of that text, so typing
    "sam" over "Dragon Archer  (CLAN_DRAGON)" edits it into nonsense instead of
    searching for a Samurai, and the old value has to be cleared by hand first.

    The filter parents itself to the combobox and installs itself on both the
    combobox and its line edit, for the reasons given in `_SelectOnFocus`. A
    combobox that is not editable has no line edit and is left alone.
    """
    if cb.lineEdit() is not None:
        _SelectOnFocus(cb)
    return cb


# ------------------------------------------------------------------ delegate
class EnumDelegate(QStyledItemDelegate):
    """Enum columns get a searchable combobox; everything else a plain line edit.

    It also draws the colour band under the columns of a colour group - see
    `colour_band`. Painting it here rather than returning a decoration from the
    model is the whole point: a band is a property of a span of cells, and Qt
    has no role that says that.
    """

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book

    def _source(self, index):
        """(sheet, row, col) behind an index that may come through the filter."""
        model = index.model()
        src = model.sourceModel() if hasattr(model, 'sourceModel') else model
        sidx = model.mapToSource(index) if hasattr(model, 'mapToSource') else index
        return src.sheet, sidx.row(), sidx.column()

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        band = colour_band(self.book, *self._source(index))
        if band is not None:
            paint_colour_band(painter, option.rect, band[0], band[1])

    def createEditor(self, parent, option, index):
        model = index.model()
        src = model.sourceModel() if hasattr(model, 'sourceModel') else model
        sidx = model.mapToSource(index) if hasattr(model, 'mapToSource') else index
        tbl = self.book.enum_for(src.sheet, sidx.column())
        if not tbl:
            return QLineEdit(parent)
        cb = QComboBox(parent)
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cb.setMaxVisibleItems(20)
        for code, desc, _g in tbl.items:
            cb.addItem(f'{code} - {desc}' if desc else str(code), code)
        comp = QCompleter([cb.itemText(i) for i in range(cb.count())], cb)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        cb.setCompleter(comp)
        # Note there is no snap-back to a listed code here, the way the unit
        # picker has one. Typing a code the enum does not define is allowed on
        # purpose - setModelData passes unmatched text straight through to
        # coerce() - and it is what puts the red "code does not exist in the
        # enum table" cells on screen. The picker cannot afford that, because
        # its data is a row index rather than a value.
        return select_all_on_focus(cb)

    def setEditorData(self, editor, index):
        val = index.data(Qt.ItemDataRole.EditRole)
        if isinstance(editor, QComboBox):
            i = editor.findData(val)
            if i >= 0:
                editor.setCurrentIndex(i)
            else:
                editor.setEditText('' if val is None else str(val))
        else:
            editor.setText('' if val is None else str(val))

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            i = editor.currentIndex()
            txt = editor.currentText()
            val = editor.itemData(i) if i >= 0 and editor.itemText(i) == txt else txt
            model.setData(index, val, Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)


# ------------------------------------------------------------------ filter
class RowFilter(QSortFilterProxyModel):
    """Row filter that searches both the raw codes and the enum descriptions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.needle = ''
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_needle(self, text):
        n = text.strip().lower()
        if n == self.needle:
            return
        self.needle = n
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        if not self.needle:
            return True
        m = self.sourceModel()
        if m is None:
            return True
        book, sheet = m.book, m.sheet
        needle = self.needle
        for c in range(m.columnCount()):
            v = book.value(sheet, row, c)
            if v is None:
                continue
            if needle in str(v).lower():
                return True
            tbl = book.enum_for(sheet, c)
            if tbl and isinstance(v, int):
                d = tbl.code2desc.get(v)
                if d and needle in d.lower():
                    return True
        return False
