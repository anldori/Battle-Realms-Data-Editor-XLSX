"""
brde.matchup_ui - the "Compare units" window.

Pick two units, read their stats side by side, and see which one beats which.
All of the arithmetic lives in `brde/matchup.py`; this file only draws it, which
is why the rules can be tested without a display.

Colour is the shortest sentence on the page, so it means one thing throughout:
green is good for the unit whose column it sits in, red is bad for it, and the
deeper the shade the stronger the reading. In the armour section that reads as
resistant or vulnerable, and in the matchup section as an attack that lands or
one that bounces off. Because each matchup column holds what that unit does TO
the other one, both readings point the same way and a column can be scanned top
to bottom without stopping to work out whose side a number is on.
"""
from __future__ import annotations

import csv
import os

from PyQt6.QtCore import (QAbstractTableModel, QEvent, QModelIndex, QObject, Qt,
                          pyqtSignal)
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                             QCompleter, QDialog, QFileDialog, QHBoxLayout,
                             QHeaderView, QLabel, QMenu, QMessageBox,
                             QPushButton, QTableView, QVBoxLayout)

from . import matchup
from .model import select_all_on_focus

SECTION_BG = QColor(233, 238, 246)
SECTION_FG = QColor(28, 43, 69)
MUTED_FG = QColor(120, 132, 150)

# Signed rank from matchup.rate() -> cell background. One ramp, and it runs the same
# way at both ends: positive is good for the unit in that column, negative is bad, and
# the further from zero the deeper the colour. Deep red is therefore the strongest
# thing the page can say, and rank -3 always gets it.
#
# Rank -3 arrives from two directions and both deserve that weight. In the armour
# section it is a multiplier of 2.0 or more, meaning the unit takes double damage or
# worse - the Dragon Spearman's AMPiercing of 4.0, which is the example the whole
# feature exists to explain. In the matchup section it is an attack the other unit is
# immune to, which lands nothing and can never kill. Giving -3 its own calmer colour
# for the second reading is what once painted the first one as if it barely mattered,
# so that a 1.25 sat in red beside a 4.0 that did not.
RANK_BG = {
    3: QColor(190, 231, 203),
    2: QColor(223, 243, 229),
    1: QColor(240, 249, 243),
    -1: QColor(253, 236, 230),
    -2: QColor(249, 213, 202),
    -3: QColor(240, 176, 156),
}


class _CommitOnReturn(QObject):
    """Takes Enter away from Qt in the unit pickers, and resolves it here.

    Qt's own answer to Enter over half-typed text is wrong for this window. With
    the completion popup open and no row highlighted in it - which is the state
    after simply typing, since nothing is highlighted until an arrow key is
    pressed - QComboBox lands on the first item in the list, so "sam" selects
    the Dragon Archer rather than the Dragon Samurai. It is not a near miss, it
    is the wrong unit, and the box then reads a name the columns do not hold.

    So the key is intercepted before the completer sees it. The filter is
    installed after `setCompleter`, and Qt calls the most recently installed
    filter first, which is what puts this ahead of the completer's own.

    A row highlighted with the arrow keys is a real choice and is let through
    untouched; everything else is settled by `_settle` and the event is eaten,
    so nothing downstream gets to guess. Eating it also stops Enter reaching the
    dialog, which would otherwise be free to press a button while the user
    thinks they are still picking a unit.
    """

    def __init__(self, settle, parent=None):
        super().__init__(parent)
        self._settle = settle

    def eventFilter(self, obj, ev):
        if (ev.type() != QEvent.Type.KeyPress
                or ev.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter)):
            return False
        comp = obj.completer()
        popup = comp.popup() if comp is not None else None
        if popup is not None and popup.isVisible():
            if popup.currentIndex().isValid():
                return False
            popup.hide()
        self._settle(obj)
        return True


class MatchupModel(QAbstractTableModel):
    """Three columns: the field name, then one column per unit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.names = ['', '']

    def set_page(self, rows, name_a, name_b):
        self.beginResetModel()
        self.rows = rows
        self.names = [name_a, name_b]
        self.endResetModel()
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 2)

    def tooltip(self, it):
        """The whole line, so a narrowed column still gives up its contents.

        Hovering any cell reports the field name and BOTH values rather than
        only the one under the pointer: the point of the window is the
        comparison, and at that moment the other column may be off screen.
        """
        if isinstance(it, matchup.Section):
            return it.title
        lines = [it.label.strip()]
        for name, value in zip(self.names, (it.a, it.b)):
            if value:
                lines.append(f'{name}: {value}')
        return '\n'.join(lines)

    def item(self, row):
        return self.rows[row] if 0 <= row < len(self.rows) else None

    # ------------------------------------------------------------ Qt overrides
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 3

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if o != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return ['', self.names[0], self.names[1]][s]
        if role == Qt.ItemDataRole.FontRole and s > 0:
            f = QFont()
            f.setBold(True)
            return f
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        it = self.rows[index.row()]
        c = index.column()

        if role == Qt.ItemDataRole.ToolTipRole:
            return self.tooltip(it)

        if isinstance(it, matchup.Section):
            if role == Qt.ItemDataRole.DisplayRole:
                return it.title.upper() if c == 0 else ''
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(SECTION_BG)
            if role == Qt.ItemDataRole.ForegroundRole:
                return QBrush(SECTION_FG)
            if role == Qt.ItemDataRole.FontRole:
                f = QFont()
                f.setBold(True)
                return f
            return None

        side = 'a' if c == 1 else ('b' if c == 2 else None)
        if role == Qt.ItemDataRole.DisplayRole:
            if c == 0:
                return '    ' * it.indent + it.label
            return it.a if c == 1 else it.b
        if role == Qt.ItemDataRole.BackgroundRole and side:
            rank = it.rank_a if side == 'a' else it.rank_b
            if rank:
                return QBrush(RANK_BG.get(max(-3, min(3, rank))))
        if role == Qt.ItemDataRole.FontRole and side and it.better == side:
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.ItemDataRole.ForegroundRole and c == 0 and it.indent:
            return QBrush(MUTED_FG)
        if role == Qt.ItemDataRole.TextAlignmentRole and side:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if isinstance(self.rows[index.row()], matchup.Section):
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class MatchupWindow(QDialog):
    """Unit versus unit. Non-modal, so the grid stays usable behind it."""

    jumpRequested = pyqtSignal(str, int, int)          # sheet, row, col
    detailRequested = pyqtSignal(str, int)             # sheet, row

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book
        self.units = matchup.unit_list(book)
        self._a = self._b = None

        self.setWindowTitle('Compare units')
        self.resize(980, 760)
        self.setSizeGripEnabled(True)

        v = QVBoxLayout(self)

        # ---- pickers
        bar = QHBoxLayout()
        self.cb_a = self._picker()
        self.cb_b = self._picker()
        bar.addWidget(QLabel('Unit:'))
        bar.addWidget(self.cb_a, 1)
        self.b_swap = QPushButton('<->')
        self.b_swap.setToolTip('Swap the two units')
        self.b_swap.setFixedWidth(44)
        self.b_swap.clicked.connect(self._swap)
        bar.addWidget(self.b_swap)
        bar.addWidget(QLabel('against:'))
        bar.addWidget(self.cb_b, 1)
        v.addLayout(bar)

        opts = QHBoxLayout()
        self.chk_tech = QCheckBox('Apply techniques (fully upgraded)')
        self.chk_tech.setChecked(True)
        self.chk_tech.setToolTip(
            'Show what each unit becomes once every technique that names it has\n'
            'been researched. Values that a technique moves are shown as\n'
            '"base -> upgraded". Untick to compare the raw sheet values.')
        self.chk_tech.toggled.connect(lambda _o: self.refresh())
        opts.addWidget(self.chk_tech)
        opts.addStretch(1)
        v.addLayout(opts)

        # ---- verdict
        self.lbl_verdict = QLabel('Pick two units to compare.')
        self.lbl_verdict.setWordWrap(True)
        self.lbl_verdict.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_verdict.setStyleSheet(
            'background:#f4f7fc; border:1px solid #d8dee8; border-radius:5px;'
            'padding:9px 11px; color:#1c2b45;')
        v.addWidget(self.lbl_verdict)

        # ---- table
        self.model = MatchupModel(self)
        self.tbl = QTableView()
        self.tbl.setModel(self.model)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(22)
        hh = self.tbl.horizontalHeader()
        # Interactive throughout so every column can be dragged. The two unit
        # columns still start out sharing whatever is left over, which is what
        # setStretchLastSection plus an explicit width for the first two gives.
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        hh.setMinimumSectionSize(60)
        self.tbl.setColumnWidth(0, 260)
        self.tbl.setColumnWidth(1, 320)
        self.tbl.setWordWrap(False)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._on_context_menu)
        v.addWidget(self.tbl, 1)

        # ---- buttons
        row = QHBoxLayout()
        self.b_detail_a = QPushButton('Details')
        self.b_detail_a.clicked.connect(lambda: self._open_detail('a'))
        row.addWidget(self.b_detail_a)
        self.b_detail_b = QPushButton('Details')
        self.b_detail_b.clicked.connect(lambda: self._open_detail('b'))
        row.addWidget(self.b_detail_b)
        b_csv = QPushButton('Export to CSV...')
        b_csv.clicked.connect(self._export)
        row.addWidget(b_csv)
        row.addStretch(1)
        b_close = QPushButton('Close')
        b_close.clicked.connect(self.close)
        row.addWidget(b_close)
        v.addLayout(row)

        self.lbl_hint = QLabel(
            'A unit\'s armour multiplier scales the damage it takes, so above 1 '
            'is a weakness and below 1 is resistance. Green is good for the unit '
            'in that column, red is bad for it.')
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet('color:#5a6b85;')
        v.addWidget(self.lbl_hint)

        if len(self.units) >= 2:
            self.cb_a.setCurrentIndex(0)
            self.cb_b.setCurrentIndex(1)
        self.cb_a.currentIndexChanged.connect(lambda _i: self.refresh())
        self.cb_b.currentIndexChanged.connect(lambda _i: self.refresh())
        self.refresh()

    def _picker(self):
        """A dropdown of every named unit, searchable by typing any part of it."""
        cb = QComboBox()
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cb.setMaxVisibleItems(24)
        for row, name, clan in self.units:
            cb.addItem(f'{name}  ({clan})' if clan else name, row)
        comp = QCompleter([cb.itemText(i) for i in range(cb.count())], cb)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        cb.setCompleter(comp)
        select_all_on_focus(cb)
        # Enter is handled here rather than by Qt; see _CommitOnReturn. Losing
        # focus needs no help - QComboBox puts the current item's text back by
        # itself - but the connection is kept as the belt to that braces.
        cb.installEventFilter(_CommitOnReturn(self._settle, cb))
        cb.lineEdit().editingFinished.connect(lambda c=cb: self._settle(c))
        return cb

    def _settle(self, cb):
        """Put a picker back onto a real unit once free typing is over.

        The insert policy is NoInsert, so text naming no unit leaves
        currentIndex where it was and never emits currentIndexChanged. Without
        this the box would sit reading "samura" while everything below it still
        meant Dragon Archer, which is the one state the window must never be in:
        the box is the only thing on screen naming what the columns hold.

        Half-typed text is resolved the way the completer's own list resolves
        it, by the same case-insensitive "contains" rule, but only when exactly
        one unit matches. "samura" and "berserker" each name one unit and are
        taken; "wolf b" names three and "dragon" names sixteen, and guessing
        between them would be worse than doing nothing, so those snap back too.
        This is what makes Enter work on a partial name, and it is deliberately
        not conditioned on whether the completion popup happens to be open:
        Qt passes Enter through to the line edit when no row in that popup is
        highlighted, so a rule that skipped while it was visible would leave the
        box reading "samura" in exactly the case that matters most.

        The grid's enum dropdown deliberately has no equivalent: there, an
        unlisted code is a legitimate thing to type. See EnumDelegate.
        """
        typed = cb.currentText().strip()
        i = cb.findText(typed, Qt.MatchFlag.MatchFixedString)
        if i < 0 and typed:
            hits = [n for n in range(cb.count())
                    if typed.lower() in cb.itemText(n).lower()]
            if len(hits) == 1:
                i = hits[0]
        if i >= 0:
            cb.setCurrentIndex(i)          # emits currentIndexChanged -> refresh
            cb.setEditText(cb.itemText(i))
        elif cb.currentIndex() >= 0:
            cb.setEditText(cb.itemText(cb.currentIndex()))

    # ------------------------------------------------------------ selection
    def show_units(self, row_a, row_b=None):
        """Point the window at one or both units, from outside."""
        for cb, row in ((self.cb_a, row_a), (self.cb_b, row_b)):
            if row is None:
                continue
            i = cb.findData(row)
            if i >= 0:
                cb.blockSignals(True)
                cb.setCurrentIndex(i)
                cb.blockSignals(False)
        self.refresh()

    def _swap(self):
        ia, ib = self.cb_a.currentIndex(), self.cb_b.currentIndex()
        for cb, i in ((self.cb_a, ib), (self.cb_b, ia)):
            cb.blockSignals(True)
            cb.setCurrentIndex(i)
            cb.blockSignals(False)
        self.refresh()

    # ------------------------------------------------------------ rendering
    def refresh(self):
        """Recompute the page. Also called when a cell is edited anywhere."""
        ra, rb = self.cb_a.currentData(), self.cb_b.currentData()
        if ra is None or rb is None:
            self.model.set_page([], '', '')
            self.lbl_verdict.setText('This file has no units to compare.')
            self.b_detail_a.setEnabled(False)
            self.b_detail_b.setEnabled(False)
            return
        a, b, v, rows = matchup.compare_units(
            self.book, ra, rb, self.chk_tech.isChecked())
        self._a, self._b = a, b
        self.model.set_page(rows, a.title, b.title)
        self._span_sections()
        self.lbl_verdict.setText(self._verdict_html(v))
        self.b_detail_a.setEnabled(True)
        self.b_detail_b.setEnabled(True)
        self.b_detail_a.setText(f'Details: {a.title}')
        self.b_detail_b.setText(f'Details: {b.title}')
        self.setWindowTitle(f'Compare units - {a.title} vs {b.title}')

    def _span_sections(self):
        """Let each section header run the full width of the table.

        Section titles are sentences - "Counter matchup - each column is what
        that unit does to the other" - and narrowing the field column would
        otherwise chop them off, which is exactly the column a user narrows to
        make room for the numbers.
        """
        self.tbl.clearSpans()
        for r, it in enumerate(self.model.rows):
            if isinstance(it, matchup.Section):
                self.tbl.setSpan(r, 0, 1, 3)

    @staticmethod
    def _verdict_html(v):
        """The verdict sentence, with the winning unit's name in bold."""
        text = v.text
        winner = None
        if v.winner == 'a':
            winner = v.a.title
        elif v.winner == 'b':
            winner = v.b.title
        if winner and text.startswith(winner):
            text = f'<b>{winner}</b>' + text[len(winner):]
        return text

    # ------------------------------------------------------------ actions
    def _unit(self, side):
        return self._a if side == 'a' else self._b

    def _open_detail(self, side):
        u = self._unit(side)
        if u is not None:
            self.detailRequested.emit(matchup.UNIT_SHEET, u.row)

    def _on_context_menu(self, pos):
        idx = self.tbl.indexAt(pos)
        if not idx.isValid():
            return
        m = QMenu(self)
        for side in ('a', 'b'):
            u = self._unit(side)
            if u is None:
                continue
            a1 = m.addAction(f'Show {u.title} in grid')
            a1.triggered.connect(
                lambda _c=False, r=u.row: self.jumpRequested.emit(
                    matchup.UNIT_SHEET, r, 0))
            a2 = m.addAction(f'Details for {u.title}')
            a2.triggered.connect(
                lambda _c=False, r=u.row: self.detailRequested.emit(
                    matchup.UNIT_SHEET, r))
            m.addSeparator()
        if not m.isEmpty():
            m.exec(self.tbl.viewport().mapToGlobal(pos))

    def _export(self, *_):
        if self._a is None or self._b is None:
            return
        base = os.path.splitext(os.path.basename(self.book.path))[0]
        default = os.path.join(
            os.path.dirname(self.book.path),
            f'{base}_{self._a.title}_vs_{self._b.title}.csv'.replace(' ', '_'))
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export comparison', default,
            'CSV file (*.csv);;Text file (*.txt);;All files (*.*)')
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
                w = csv.writer(fh)
                w.writerow(['# File', self.book.path])
                w.writerow(['# Techniques applied',
                            'yes' if self.chk_tech.isChecked() else 'no'])
                w.writerow([])
                w.writerow(['', self._a.title, self._b.title])
                for it in self.model.rows:
                    if isinstance(it, matchup.Section):
                        w.writerow([])
                        w.writerow([it.title.upper()])
                    else:
                        w.writerow(['    ' * it.indent + it.label, it.a, it.b])
        except Exception as e:
            QMessageBox.critical(self, 'Compare units',
                                 f'Could not write the file:\n{e}')
            return
        self.lbl_hint.setText(f'Exported the comparison to {path}')
