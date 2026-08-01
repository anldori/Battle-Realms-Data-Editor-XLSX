"""
brde.model - Table model, cell delegate and undo commands for the data grid.
"""
from __future__ import annotations

from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QSortFilterProxyModel,
                          Qt, pyqtSignal)
from PyQt6.QtGui import QBrush, QColor, QFont, QUndoCommand
from PyQt6.QtWidgets import QComboBox, QCompleter, QStyledItemDelegate, QLineEdit

EDITED_BG = QColor(255, 243, 205)
EDITED_FG = QColor(140, 90, 0)
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


# ------------------------------------------------------------------ delegate
class EnumDelegate(QStyledItemDelegate):
    """Enum columns get a searchable combobox; everything else a plain line edit."""

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book

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
        return cb

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
