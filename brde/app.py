r"""
brde.app - the main window.

Editor for the Battle Realms.xlsx game data file. Every column that references
a code table (Enum_*) is edited through a dropdown instead of a raw number.

Run:  python br_editor.py  [path\to\Battle Realms.xlsx]
  or: python -m brde       [path\to\Battle Realms.xlsx]
"""
from __future__ import annotations

import os
import sys
import traceback

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QKeySequence, QUndoStack
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                             QProgressDialog, QPushButton, QSizePolicy,
                             QSplitter, QStackedWidget, QStatusBar, QTableView,
                             QToolBar, QVBoxLayout, QWidget)

from . import about, compare, core, detail
from .model import (EnumDelegate, MultiSetCommand, RowFilter, SetValueCommand,
                    SheetModel, coerce)

APP_NAME = 'Battle Realms Data Editor'
ORG = 'BRDE'

STYLE = """
QMainWindow, QWidget { font-size: 12px; }
QListWidget { border: none; background: #fbfbfd; }
QListWidget::item { padding: 5px 8px; }
QListWidget::item:selected { background: #2d6cdf; color: white; }
QTableView {
    gridline-color: #dfe3e8;
    selection-background-color: #cfe0ff;
    selection-color: #000;
    alternate-background-color: #fafbfc;
}
QHeaderView::section {
    background: #eef1f5; padding: 4px 6px; border: 0;
    border-right: 1px solid #d8dde3; border-bottom: 1px solid #d8dde3;
}
QLineEdit { padding: 4px 6px; border: 1px solid #c9ced6; border-radius: 4px; }
QToolBar { border-bottom: 1px solid #dfe3e8; spacing: 4px; padding: 3px; }
QMenuBar { background: #f4f6f9; border-bottom: 1px solid #dfe3e8; }
QMenuBar::item { padding: 5px 11px; }
QMenuBar::item:selected { background: #2d6cdf; color: white; }
#Welcome { background: #ffffff; }
#WelcomeTitle { font-size: 24px; font-weight: bold; color: #1c2b45; }
#WelcomeSub { font-size: 13px; color: #5a6b85; }
#BigButton {
    font-size: 15px; font-weight: bold; color: white; background: #2d6cdf;
    border: none; border-radius: 6px; padding: 12px 30px;
}
#BigButton:hover { background: #2559b8; }
#RecentLink {
    text-align: left; border: 1px solid #dfe3e8; border-radius: 5px;
    padding: 8px 12px; background: #fbfbfd; color: #1c2b45;
}
#RecentLink:hover { background: #eef3fc; border-color: #2d6cdf; }
"""

MAX_RECENT = 8

HELP_TEXT = """\
OPENING A FILE
  File > Open file...  (Ctrl+O)  or drag a .xlsx file onto the window.

EDITING
  Double-click a cell to edit it.
  Cells in columns that reference a code table show a DROPDOWN - pick from the
  list instead of typing a number. Type a few characters to search long lists.
  Edited cells are highlighted in yellow; hover to see the original value.
  Cells in red hold a code that does not exist in the enum table.

KEYBOARD SHORTCUTS
  Ctrl+O  open file           Ctrl+S  save
  Ctrl+Z  undo                Ctrl+Y  redo
  Ctrl+C  copy                Ctrl+V  paste (Excel-style, tab separated)
  Ctrl+R  revert to original  Del     clear cell
  Ctrl+F  filter rows         Ctrl+P  go to sheet
  Ctrl+E  list edited cells   Ctrl+Shift+N  add row
  Ctrl+I  find a record       Ctrl+Shift+I  details for the selected row

RECORD DETAILS  (Record > Find record..., Ctrl+I)
  Type a unit or building name - "samurai", "dojo" - and pick it from the list.
  Everything about that record is shown on one page: cost, health, armour, and
  the damage and range of each weapon it carries, read straight out of
  Data_Weapons. "Referenced by" at the bottom lists every other row that points
  at this record.
  Values are editable here exactly as in the grid, including the dropdowns, and
  a field that lives on another record edits that record.
  Double-click a FIELD NAME shown in blue to open the record it points at, and
  use "< Back" to return. "Show in grid" jumps to the row in the main window.
  Ctrl+Shift+I, or right-clicking a cell, opens the row you are already on.

RIGHT-CLICK ON AN ENUM CELL
  "Go to Data_..."      opens the exact record being referenced.
  "Open code table..."  shows the full list of codes.

COMPARING TWO FILES
  Compare > Compare with another file...  (Ctrl+D)
  Pick a second .xlsx and every difference is listed: sheet, row, column,
  your value and theirs. Differing cells are also tinted purple in the grid.
  Double-click a row in the report to jump straight to that cell.
  "Take other value" copies their value into your file as a normal edit.
  "Export to CSV..." saves the whole report.
  Rows are matched by their Type key, not by position, so inserting a
  record does not make every row below it look changed.

SAVING
  Ctrl+S overwrites the open file and creates a timestamped .bak copy first.
  Only the edited cells are patched inside the XML; the rest of the file stays
  byte-for-byte identical, so the game reads it exactly as before.
"""


class MainWindow(QMainWindow):
    def __init__(self, path=None, settings=None):
        """settings: pass one in to redirect where preferences are stored.

        Left alone it is `QSettings(ORG, APP_NAME)`, which on Windows means
        HKCU\\Software\\BRDE\\Battle Realms Data Editor in the registry. The
        test suite supplies an ini file in a temporary directory instead, so a
        test run cannot fill the user's real "Open recent" list. Note that
        QSettings.setDefaultFormat() cannot do this for us: the
        (organization, application) constructor always uses the native format.
        """
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1440, 860)
        self.settings = settings if settings is not None \
            else QSettings(ORG, APP_NAME)

        self.book: core.BRWorkbook | None = None
        self.model: SheetModel | None = None
        self.proxy = RowFilter(self)
        self.undo = QUndoStack(self)
        self.undo.cleanChanged.connect(lambda _c: self._update_title())
        self._models: dict[str, SheetModel] = {}
        self._compare_dlg = None
        self._compare_result = None
        self._detail_dlg = None

        self._build_ui()
        self.setAcceptDrops(True)
        if path and os.path.exists(path):
            QTimer.singleShot(80, lambda: self.open_file(path))

    # -------------------------------------------------------------- UI
    def _build_ui(self):
        # ============================ shared actions
        def mkact(text, slot=None, shortcut=None, tip=None):
            a = QAction(text, self)
            if slot:
                a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            if tip:
                a.setToolTip(tip)
                a.setStatusTip(tip)
            return a

        self.a_open = mkact('&Open file...', self.on_open, 'Ctrl+O',
                            'Choose a Battle Realms.xlsx file')
        self.a_save = mkact('&Save', self.on_save, 'Ctrl+S')
        self.a_saveas = mkact('Save &As...', self.on_save_as, 'Ctrl+Shift+S')
        self.a_close = mkact('&Close file', self.on_close_file)
        self.a_quit = mkact('E&xit', lambda: self.close(), 'Ctrl+Q')
        self.a_undo = self.undo.createUndoAction(self, '&Undo')
        self.a_undo.setShortcut(QKeySequence('Ctrl+Z'))
        self.a_redo = self.undo.createRedoAction(self, '&Redo')
        self.a_redo.setShortcut(QKeySequence('Ctrl+Y'))
        self.a_copy = mkact('&Copy', self.on_copy, 'Ctrl+C')
        self.a_paste = mkact('&Paste', self.on_paste, 'Ctrl+V')
        self.a_clear = mkact('C&lear cells', self.on_clear, 'Del')
        self.a_revert = mkact('Re&vert to original', self.on_revert_cell, 'Ctrl+R',
                              'Restore the selected cells to their original values')
        self.a_addrow = mkact('Add &row', self.on_add_row, 'Ctrl+Shift+N')
        self.a_edits = mkact('List &edited cells...', self.on_show_edits, 'Ctrl+E')
        self.a_detail = mkact(
            'Find &record...', self.on_detail, 'Ctrl+I',
            'Search a unit or building by name and see all of its stats on one page')
        self.a_detail_row = mkact(
            '&Details for the selected row', self.on_detail_row, 'Ctrl+Shift+I',
            'Open the record under the cursor in the details window')
        self.a_compare = mkact('&Compare with another file...', self.on_compare,
                               'Ctrl+D',
                               'Pick a second .xlsx and list every difference')
        self.a_cmp_again = mkact('Compare with &last file again', self.on_compare_last)
        self.a_cmp_show = mkact('&Show last report', self.on_compare_show)
        self.a_cmp_clear = mkact('Cl&ear comparison', self.on_compare_clear,
                                 None, 'Remove the comparison highlighting')
        self.a_find = mkact('&Filter rows', self.focus_filter, 'Ctrl+F')
        self.a_gosheet = mkact('&Go to sheet...', self.on_goto_sheet, 'Ctrl+P')
        self.a_desc = mkact('Show enum &descriptions')
        self.a_desc.setCheckable(True)
        self.a_desc.setChecked(True)
        self.a_desc.toggled.connect(self.on_toggle_desc)
        self.a_help = mkact('&How to use', self.on_help, 'F1')
        self.a_about = mkact('&About', self.on_about)

        # ============================ menu bar
        mb = self.menuBar()
        m_file = mb.addMenu('&File')
        m_file.addAction(self.a_open)
        self.m_recent = m_file.addMenu('Open &recent')
        m_file.addSeparator()
        m_file.addAction(self.a_save)
        m_file.addAction(self.a_saveas)
        m_file.addSeparator()
        m_file.addAction(self.a_close)
        m_file.addAction(self.a_quit)

        m_edit = mb.addMenu('&Edit')
        m_edit.addAction(self.a_undo)
        m_edit.addAction(self.a_redo)
        m_edit.addSeparator()
        m_edit.addAction(self.a_copy)
        m_edit.addAction(self.a_paste)
        m_edit.addAction(self.a_clear)
        m_edit.addSeparator()
        m_edit.addAction(self.a_revert)
        m_edit.addAction(self.a_addrow)

        m_view = mb.addMenu('&View')
        m_view.addAction(self.a_desc)
        m_view.addSeparator()
        m_view.addAction(self.a_find)
        m_view.addAction(self.a_gosheet)
        m_view.addAction(self.a_edits)

        m_rec = mb.addMenu('&Record')
        m_rec.addAction(self.a_detail)
        m_rec.addAction(self.a_detail_row)

        m_cmp = mb.addMenu('&Compare')
        m_cmp.addAction(self.a_compare)
        m_cmp.addAction(self.a_cmp_again)
        m_cmp.addSeparator()
        m_cmp.addAction(self.a_cmp_show)
        m_cmp.addAction(self.a_cmp_clear)

        m_help = mb.addMenu('&Help')
        m_help.addAction(self.a_help)
        m_help.addAction(self.a_about)

        # ============================ toolbar
        tb = QToolBar('Main')
        tb.setMovable(False)
        self.addToolBar(tb)
        for a in (self.a_open, self.a_save, self.a_saveas):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.a_undo)
        tb.addAction(self.a_redo)
        tb.addSeparator()
        tb.addAction(self.a_revert)
        tb.addAction(self.a_edits)
        tb.addAction(self.a_addrow)
        tb.addSeparator()
        tb.addAction(self.a_detail)
        tb.addAction(self.a_compare)
        tb.addSeparator()

        self.chk_desc = QCheckBox('Show enum descriptions')
        self.chk_desc.setChecked(True)
        self.chk_desc.toggled.connect(self.a_desc.setChecked)
        tb.addWidget(self.chk_desc)

        tb.addWidget(QLabel('   Filter rows: '))
        self.ed_filter = QLineEdit()
        self.ed_filter.setPlaceholderText('type to filter the current sheet...')
        self.ed_filter.setFixedWidth(260)
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(250)
        self._filter_timer.timeout.connect(
            lambda: self.proxy.set_needle(self.ed_filter.text()))
        self.ed_filter.textChanged.connect(lambda _t: self._filter_timer.start())
        tb.addWidget(self.ed_filter)

        # ---- left: sheet list
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)
        lv.setSpacing(5)
        self.ed_sheet = QLineEdit()
        self.ed_sheet.setPlaceholderText('Find sheet...')
        self.ed_sheet.textChanged.connect(self._filter_sheets)
        lv.addWidget(self.ed_sheet)
        self.lst = QListWidget()
        self.lst.currentItemChanged.connect(self.on_sheet_changed)
        lv.addWidget(self.lst)

        # ---- right: data grid
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)
        self.lbl_sheet = QLabel('  No file open. Press Ctrl+O to open Battle Realms.xlsx')
        f = QFont()
        f.setBold(True)
        self.lbl_sheet.setFont(f)
        self.lbl_sheet.setContentsMargins(8, 6, 8, 6)
        rv.addWidget(self.lbl_sheet)

        self.tbl = QTableView()
        self.tbl.setModel(self.proxy)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.tbl.setEditTriggers(QTableView.EditTrigger.DoubleClicked
                                 | QTableView.EditTrigger.SelectedClicked
                                 | QTableView.EditTrigger.EditKeyPressed
                                 | QTableView.EditTrigger.AnyKeyPressed)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self.on_context_menu)
        self.tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        # measure widths from ~40 rows only, so big sheets open fast
        self.tbl.horizontalHeader().setResizeContentsPrecision(40)
        self.tbl.verticalHeader().setDefaultSectionSize(22)
        rv.addWidget(self.tbl)

        self.sp = QSplitter()
        self.sp.addWidget(left)
        self.sp.addWidget(right)
        self.sp.setStretchFactor(0, 0)
        self.sp.setStretchFactor(1, 1)
        self.sp.setSizes([280, 1160])

        # ---- welcome screen, shown while no file is open
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_welcome())     # 0
        self.stack.addWidget(self.sp)                   # 1
        self.setCentralWidget(self.stack)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.lbl_status = QLabel('Ready')
        self.status.addWidget(self.lbl_status, 1)
        self.lbl_dirty = QLabel('')
        self.status.addPermanentWidget(self.lbl_dirty)

        self.setStyleSheet(STYLE)

        # copy / paste / clear shortcuts scoped to the table
        for seq, fn in (('Ctrl+C', self.on_copy), ('Ctrl+V', self.on_paste),
                        ('Delete', self.on_clear)):
            a = QAction(self)
            a.setShortcut(QKeySequence(seq))
            a.triggered.connect(fn)
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.tbl.addAction(a)

        self._rebuild_recent_menu()
        self._set_file_actions_enabled(False)

    # ------------------------------------------------------- welcome screen
    def _build_welcome(self):
        w = QWidget()
        w.setObjectName('Welcome')
        v = QVBoxLayout(w)
        v.setContentsMargins(60, 50, 60, 50)
        v.setSpacing(10)
        v.addStretch(1)

        t = QLabel('Battle Realms Data Editor')
        t.setObjectName('WelcomeTitle')
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t)

        s = QLabel('Game data editor for the .xlsx version of Battle Realms.\n'
                   'Every column that references a code table gets a dropdown.')
        s.setObjectName('WelcomeSub')
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(s)
        v.addSpacing(24)

        btn = QPushButton('  Open Battle Realms.xlsx...  ')
        btn.setObjectName('BigButton')
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(self.on_open)
        row = QVBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
        v.addLayout(row)
        v.addSpacing(8)

        hint = QLabel('or drag a .xlsx file onto this window  \u00b7  Ctrl+O')
        hint.setObjectName('WelcomeSub')
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(hint)
        v.addSpacing(26)

        self.lbl_recent_title = QLabel('Recent files')
        self.lbl_recent_title.setObjectName('WelcomeSub')
        self.lbl_recent_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.lbl_recent_title)

        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(6)
        self.recent_box.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        v.addLayout(self.recent_box)

        v.addStretch(2)
        return w

    # -------------------------------------------------------- recent files
    def _recent_list(self):
        v = self.settings.value('recent', [])
        if isinstance(v, str):
            v = [v]
        return [p for p in (v or []) if p]

    def _push_recent(self, path):
        path = os.path.abspath(path)
        lst = [p for p in self._recent_list() if os.path.normcase(p) != os.path.normcase(path)]
        lst.insert(0, path)
        self.settings.setValue('recent', lst[:MAX_RECENT])
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        lst = self._recent_list()
        self.m_recent.clear()
        if not lst:
            a = self.m_recent.addAction('(no recent files)')
            a.setEnabled(False)
        else:
            for i, p in enumerate(lst):
                a = self.m_recent.addAction(f'&{i + 1}.  {os.path.basename(p)}')
                a.setToolTip(p)
                a.setStatusTip(p)
                a.triggered.connect(lambda _c=False, path=p: self._open_recent(path))
            self.m_recent.addSeparator()
            self.m_recent.addAction('Clear list', self._clear_recent)

        # quick-open buttons on the welcome screen
        while self.recent_box.count():
            it = self.recent_box.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for p in lst[:5]:
            b = QPushButton(f'{os.path.basename(p)}      {os.path.dirname(p)}')
            b.setObjectName('RecentLink')
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumWidth(560)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            b.setToolTip(p)
            b.clicked.connect(lambda _c=False, path=p: self._open_recent(path))
            self.recent_box.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        self.lbl_recent_title.setVisible(bool(lst))

    def _clear_recent(self):
        self.settings.setValue('recent', [])
        self._rebuild_recent_menu()

    def _open_recent(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, APP_NAME,
                                f'File not found:\n{path}\n\n'
                                'It may have been moved or deleted.')
            lst = [p for p in self._recent_list()
                   if os.path.normcase(p) != os.path.normcase(path)]
            self.settings.setValue('recent', lst)
            self._rebuild_recent_menu()
            return
        self.open_file(path)

    def _set_file_actions_enabled(self, on):
        # a_undo / a_redo manage their own enabled state via QUndoStack
        for a in (self.a_save, self.a_saveas, self.a_close, self.a_copy,
                  self.a_paste, self.a_clear, self.a_revert, self.a_addrow,
                  self.a_edits, self.a_find, self.a_gosheet, self.a_desc,
                  self.a_detail, self.a_detail_row, self.a_compare,
                  self.a_cmp_again):
            a.setEnabled(on)
        # these two only make sense once a comparison has actually been run
        if not on:
            self.a_cmp_show.setEnabled(False)
            self.a_cmp_clear.setEnabled(False)
        self.chk_desc.setEnabled(on)
        self.ed_filter.setEnabled(on)
        self.ed_sheet.setEnabled(on)

    # -------------------------------------------------------- drag and drop
    def dragEnterEvent(self, ev):
        md = ev.mimeData()
        if md.hasUrls() and any(u.toLocalFile().lower().endswith(('.xlsx', '.xlsm'))
                                for u in md.urls()):
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        for u in ev.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(('.xlsx', '.xlsm')):
                self.open_file(p)
                ev.acceptProposedAction()
                return

    # -------------------------------------------------------------- file
    def on_open(self):
        last = self.settings.value('lastdir', os.path.expanduser('~'))
        p, _ = QFileDialog.getOpenFileName(
            self, 'Open Battle Realms data file', last,
            'Excel workbook (*.xlsx *.xlsm);;All files (*.*)')
        if p:
            self.open_file(p)

    def open_file(self, path):
        if self.book and self.book.dirty and not self._confirm_discard():
            return
        dlg = QProgressDialog('Reading workbook...', None, 0, 100, self)
        dlg.setWindowTitle(APP_NAME)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.setCancelButton(None)
        dlg.show()
        QApplication.processEvents()

        def prog(i, total, name):
            dlg.setValue(int(i * 100 / max(total, 1)))
            dlg.setLabelText(f'Reading: {name}')
            QApplication.processEvents()

        try:
            self.book = core.BRWorkbook(path, progress=prog)
        except Exception as e:
            dlg.close()
            QMessageBox.critical(self, APP_NAME,
                                 f'Could not open the file:\n{e}\n\n{traceback.format_exc()}')
            return
        dlg.close()
        self.settings.setValue('lastdir', os.path.dirname(path))
        self._push_recent(path)
        self._discard_comparison()
        self._discard_detail()
        self._models.clear()
        self.undo.clear()
        self._set_file_actions_enabled(True)
        self.stack.setCurrentIndex(1)
        self._fill_sheet_list()
        self._update_title()
        n_drop = sum(len(s.col_enum) for s in self.book.sheets.values())
        self.lbl_status.setText(
            f'{os.path.basename(path)} - {len(self.book.sheets)} sheets, '
            f'{len(self.book.enums)} code tables, {n_drop} dropdown columns')

    def on_close_file(self):
        if not self.book:
            return
        if self.book.dirty and not self._confirm_discard():
            return
        self._discard_comparison()
        self._discard_detail()
        self.book = None
        self.model = None
        self._models.clear()
        self.undo.clear()
        self.proxy.setSourceModel(None)
        self.lst.clear()
        self.ed_filter.clear()
        self.stack.setCurrentIndex(0)
        self._set_file_actions_enabled(False)
        self._rebuild_recent_menu()
        self._update_title()
        self.lbl_status.setText('File closed. Use File > Open file... to open another one.')

    def on_save(self):
        if not self.book:
            return
        if not self.book.dirty:
            self.lbl_status.setText('No changes to save.')
            return
        self._do_save(self.book.path)

    def on_save_as(self):
        if not self.book:
            return
        p, _ = QFileDialog.getSaveFileName(self, 'Save As', self.book.path,
                                           'Excel workbook (*.xlsx)')
        if p:
            self._do_save(p)

    def _do_save(self, dest):
        try:
            n = len(self.book.edits)
            out = self.book.save(dest, backup=True)
        except Exception as e:
            QMessageBox.critical(self, APP_NAME,
                                 f'Save failed:\n{e}\n\n{traceback.format_exc()}')
            return
        self.undo.clear()
        for m in self._models.values():
            m.refresh_all()
        if self._detail_dlg is not None:
            self._detail_dlg.refresh()
        self._update_title()
        self.lbl_status.setText(f'Saved {n} cells to {out}  (.bak backup created)')

    def _confirm_discard(self):
        r = QMessageBox.question(
            self, APP_NAME,
            f'{len(self.book.edits)} cells are still unsaved. Discard these changes?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return r == QMessageBox.StandardButton.Yes

    def closeEvent(self, ev):
        if self.book and self.book.dirty and not self._confirm_discard():
            ev.ignore()
        else:
            ev.accept()

    # -------------------------------------------------------------- sheets
    def _fill_sheet_list(self):
        self.lst.clear()
        groups = [('DATA TABLES', lambda n: n.startswith('Data_')),
                  ('CODE TABLES (ENUM)', lambda n: n.startswith('Enum_')),
                  ('OTHER', lambda n: not n.startswith(('Data_', 'Enum_')))]
        for title, pred in groups:
            names = [n for n in self.book.sheet_order if pred(n)]
            if not names:
                continue
            it = QListWidgetItem(f'- {title} -')
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            fo = QFont()
            fo.setBold(True)
            fo.setPointSize(8)
            it.setFont(fo)
            self.lst.addItem(it)
            for n in names:
                sd = self.book.sheets[n]
                item = QListWidgetItem(n)
                item.setData(Qt.ItemDataRole.UserRole, n)
                item.setToolTip(f'{n}\n{len(sd.rows)} rows x {len(sd.headers)} columns\n'
                                f'{len(sd.col_enum)} dropdown columns')
                self.lst.addItem(item)
        for i in range(self.lst.count()):
            if self.lst.item(i).data(Qt.ItemDataRole.UserRole):
                self.lst.setCurrentRow(i)
                break

    def _filter_sheets(self, text):
        t = text.strip().lower()
        for i in range(self.lst.count()):
            it = self.lst.item(i)
            n = it.data(Qt.ItemDataRole.UserRole)
            it.setHidden(bool(n) and t not in n.lower())

    def on_sheet_changed(self, cur, _prev):
        if not cur or not self.book:
            return
        name = cur.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        self.show_sheet(name)

    def _model_for(self, name):
        if name not in self._models:
            m = SheetModel(self.book, name, self.undo, self)
            m.valueChanged.connect(self._on_value_changed)
            self._models[name] = m
        return self._models[name]

    def _on_value_changed(self, _sheet, _row, _col):
        """Any cell changed, from the grid, a paste, an undo or the detail window."""
        self._update_title()
        if self._detail_dlg is not None:
            self._detail_dlg.refresh()

    def show_sheet(self, name, focus_row=None, focus_col=0):
        self.model = self._model_for(name)
        self.model.show_desc = self.chk_desc.isChecked()
        self.proxy.setSourceModel(self.model)
        self.tbl.setItemDelegate(EnumDelegate(self.book, self.tbl))
        sd = self.book.sheets[name]
        self.lbl_sheet.setText(
            f'  {name}     {len(sd.rows)} rows \u00d7 {len(sd.headers)} columns     '
            f'{len(sd.col_enum)} dropdown columns')
        self.tbl.resizeColumnsToContents()
        for c in range(self.model.columnCount()):
            w = self.tbl.columnWidth(c)
            self.tbl.setColumnWidth(c, max(60, min(w + 12, 320)))
        # keep the sheet list selection in sync
        for i in range(self.lst.count()):
            if self.lst.item(i).data(Qt.ItemDataRole.UserRole) == name:
                self.lst.blockSignals(True)
                self.lst.setCurrentRow(i)
                self.lst.blockSignals(False)
                break
        if focus_row is not None:
            src = self.model.index(focus_row, focus_col)
            idx = self.proxy.mapFromSource(src)
            if idx.isValid():
                self.tbl.setCurrentIndex(idx)
                self.tbl.scrollTo(idx, QTableView.ScrollHint.PositionAtCenter)
        self._update_title()

    def on_toggle_desc(self, on):
        if self.chk_desc.isChecked() != on:
            self.chk_desc.blockSignals(True)
            self.chk_desc.setChecked(on)
            self.chk_desc.blockSignals(False)
        for m in self._models.values():
            m.show_desc = on
            m.refresh_all()

    def focus_filter(self):
        self.ed_filter.setFocus()
        self.ed_filter.selectAll()

    def on_goto_sheet(self):
        if not self.book:
            return
        names = list(self.book.sheet_order)
        cur = names.index(self.model.sheet) if self.model else 0
        name, ok = QInputDialog.getItem(self, 'Go to sheet', 'Sheet:',
                                        names, cur, True)
        if ok and name in self.book.sheets:
            self.show_sheet(name)

    def on_help(self):
        QMessageBox.information(self, 'How to use', HELP_TEXT)

    def on_about(self):
        about.AboutDialog(self).exec()

    # -------------------------------------------------------------- edits
    def _sel_source(self):
        return [self.proxy.mapToSource(i) for i in self.tbl.selectedIndexes()]

    def on_copy(self):
        idxs = self.tbl.selectedIndexes()
        if not idxs:
            return
        idxs.sort(key=lambda i: (i.row(), i.column()))
        rows = {}
        for i in idxs:
            rows.setdefault(i.row(), []).append(
                str(i.data(Qt.ItemDataRole.EditRole) or ''))
        txt = '\n'.join('\t'.join(v) for _k, v in sorted(rows.items()))
        QApplication.clipboard().setText(txt)
        self.lbl_status.setText(f'Copied {len(idxs)} cells')

    def on_paste(self):
        if not self.model:
            return
        txt = QApplication.clipboard().text()
        cur = self.tbl.currentIndex()
        if not txt or not cur.isValid():
            return
        base = self.proxy.mapToSource(cur)
        grid = [line.split('\t') for line in txt.replace('\r\n', '\n').split('\n')]
        cells = []
        for dr, line in enumerate(grid):
            for dc, raw in enumerate(line):
                r, c = base.row() + dr, base.column() + dc
                if r >= self.model.rowCount() or c >= self.model.columnCount():
                    continue
                old = self.model.raw(r, c)
                new = coerce(raw, old)
                if new != old:
                    cells.append((r, c, old, new))
        if cells:
            self.undo.push(MultiSetCommand(self.model, cells,
                                           f'Paste {len(cells)} cells'))
            self.lbl_status.setText(f'Pasted {len(cells)} cells')

    def on_clear(self):
        if not self.model:
            return
        cells = []
        for i in self._sel_source():
            old = self.model.raw(i.row(), i.column())
            if old is not None:
                cells.append((i.row(), i.column(), old, None))
        if cells:
            self.undo.push(MultiSetCommand(self.model, cells,
                                           f'Clear {len(cells)} cells'))

    def on_revert_cell(self):
        if not self.model:
            return
        cells = []
        for i in self._sel_source():
            key = (self.model.sheet, i.row(), i.column())
            if key in self.book.edits:
                cells.append((i.row(), i.column(),
                              self.book.edits[key], self.book.original[key]))
        if cells:
            self.undo.push(MultiSetCommand(self.model, cells,
                                           f'Revert {len(cells)} cells'))

    def on_add_row(self):
        if not self.model:
            return
        r = self.model.append_rows(1)
        idx = self.proxy.mapFromSource(self.model.index(r, 0))
        if idx.isValid():
            self.tbl.setCurrentIndex(idx)
            self.tbl.scrollTo(idx)
        self.lbl_status.setText(
            f'Added an empty row (Excel row {r + 2}). '
            'Fill it in, then press Ctrl+S to write it to the file.')

    def on_show_edits(self):
        if not self.book or not self.book.edits:
            QMessageBox.information(self, APP_NAME, 'No cells have been edited yet.')
            return
        lines = []
        for (sh, r, c), v in sorted(self.book.edits.items()):
            head = self.book.sheets[sh].headers[c] if c < len(self.book.sheets[sh].headers) else c
            lines.append(f'{sh} \u00b7 row {r + 2} \u00b7 {head}:  '
                         f'{self.book.original.get((sh, r, c))}  \u2192  {v}')
        item, ok = QInputDialog.getItem(
            self, f'{len(lines)} edited cells', 'Select one to jump to it:',
            lines, 0, False)
        if ok and item:
            i = lines.index(item)
            (sh, r, c) = sorted(self.book.edits.keys())[i]
            self.show_sheet(sh, r, c)

    # -------------------------------------------------------------- details
    def on_detail(self):
        if not self.book:
            return
        if self._detail_dlg is None:
            d = detail.DetailWindow(self.book, self)
            d.jumpRequested.connect(self._on_detail_jump)
            d.editRequested.connect(self._on_detail_edit)
            d.finished.connect(self._on_detail_closed)
            self._detail_dlg = d
        self._detail_dlg.show()
        self._detail_dlg.raise_()
        self._detail_dlg.activateWindow()

    def on_detail_row(self):
        """Open the details window on whichever record the cursor sits in."""
        if not self.model:
            return
        idx = self.tbl.currentIndex()
        if not idx.isValid():
            self.lbl_status.setText(
                'Select a cell first, then use Details for the selected row.')
            return
        sheet = self.model.sheet
        if sheet.startswith('Enum_'):
            self.lbl_status.setText(
                'Code tables have no detail page. Pick a row in a Data_ sheet.')
            return
        self._detail_for(sheet, self.proxy.mapToSource(idx).row())

    def _detail_for(self, sheet, row):
        """Open the detail window straight on one record, from the grid."""
        self.on_detail()
        if self._detail_dlg is not None:
            self._detail_dlg.show_record(sheet, row)

    def _on_detail_closed(self, _result):
        d, self._detail_dlg = self._detail_dlg, None
        if d is not None:
            d.deleteLater()

    def _discard_detail(self):
        """Drop the detail window. Its search index belongs to the old file."""
        if self._detail_dlg is not None:
            d, self._detail_dlg = self._detail_dlg, None
            d.finished.disconnect(self._on_detail_closed)
            d.close()
            d.deleteLater()

    def _on_detail_jump(self, sheet, row, col):
        if sheet in self.book.sheets:
            self.show_sheet(sheet, row, col)
            self.raise_()
            self.activateWindow()

    def _on_detail_edit(self, sheet, row, col, value):
        """An edit typed into the detail window. Same path as editing the grid,
        so undo, the dirty count and the yellow highlight all behave alike."""
        model = self._model_for(sheet)
        old = model.raw(row, col)
        new = coerce(value, old)
        if new == old:
            return
        self.undo.push(SetValueCommand(model, row, col, old, new))

    # ------------------------------------------------------------- compare
    def on_compare(self):
        if not self.book:
            return
        last = self.settings.value('comparedir') or os.path.dirname(self.book.path)
        path, _ = QFileDialog.getOpenFileName(
            self, 'Choose the file to compare against', last,
            'Excel workbook (*.xlsx *.xlsm);;All files (*.*)')
        if path:
            self._run_compare(path)

    def on_compare_last(self):
        last = self.settings.value('comparelast')
        if not self.book:
            return
        if not last:
            self.on_compare()
            return
        if not os.path.exists(last):
            QMessageBox.warning(self, APP_NAME,
                                f'File not found:\n{last}\n\n'
                                'It may have been moved or deleted.')
            return
        self._run_compare(last)

    def _run_compare(self, other_path):
        if os.path.normcase(os.path.abspath(other_path)) == \
                os.path.normcase(os.path.abspath(self.book.path)):
            QMessageBox.information(
                self, APP_NAME,
                'That is the file you already have open. Choose a different one '
                'to compare against.')
            return
        if self.book.dirty:
            r = QMessageBox.question(
                self, APP_NAME,
                f'You have {len(self.book.edits)} unsaved edits.\n\n'
                'The comparison uses your edited values, so unsaved changes will '
                'show up as differences. Continue?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return

        dlg = QProgressDialog('Comparing...', None, 0, 100, self)
        dlg.setWindowTitle(APP_NAME)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setMinimumDuration(0)
        dlg.setCancelButton(None)
        dlg.show()
        QApplication.processEvents()

        def prog(i, total, name):
            dlg.setValue(int(i * 100 / max(total, 1)))
            dlg.setLabelText(f'Comparing: {name}')
            QApplication.processEvents()

        try:
            result = compare.compare(self.book, other_path, progress=prog)
        except Exception as e:
            dlg.close()
            QMessageBox.critical(
                self, APP_NAME,
                f'Could not compare the files:\n{e}\n\n{traceback.format_exc()}')
            return
        dlg.close()

        self.settings.setValue('comparedir', os.path.dirname(other_path))
        self.settings.setValue('comparelast', os.path.abspath(other_path))
        self._compare_result = result

        if not result.diffs and not result.sheets_only_mine \
                and not result.sheets_only_theirs:
            self.on_compare_clear()
            QMessageBox.information(
                self, APP_NAME,
                'No differences found - the two files hold the same data.')
            self.lbl_status.setText('Compare: no differences found.')
            return

        self.book.diff_cells = result.cell_map()
        self.book.diff_label = os.path.basename(other_path)
        self._refresh_models()

        self._open_compare_dialog(result)

        self.a_cmp_show.setEnabled(True)
        self.a_cmp_clear.setEnabled(True)
        self.lbl_status.setText(
            f'Compare: {len(result.diffs)} differences against '
            f'{os.path.basename(other_path)}')

    def _open_compare_dialog(self, result):
        """Close any previous report window and show a fresh one."""
        if self._compare_dlg is not None:
            self._compare_dlg.close()
        d = compare.CompareDialog(self.book, result, self)
        d.jumpRequested.connect(self._on_diff_jump)
        d.applyRequested.connect(self._on_diff_apply)
        d.highlightToggled.connect(self._on_diff_highlight)
        d.finished.connect(self._on_compare_dlg_closed)
        self._compare_dlg = d
        d.show()

    def _on_compare_dlg_closed(self, _result):
        d, self._compare_dlg = self._compare_dlg, None
        if d is not None:
            d.deleteLater()

    def on_compare_show(self):
        if self._compare_dlg is not None:
            self._compare_dlg.show()
            self._compare_dlg.raise_()
            self._compare_dlg.activateWindow()
        elif self._compare_result is not None:
            self._open_compare_dialog(self._compare_result)
        else:
            self.on_compare()

    def _discard_comparison(self):
        """Drop all comparison state. Used when switching or closing files."""
        if self._compare_dlg is not None:
            dlg, self._compare_dlg = self._compare_dlg, None
            dlg.finished.disconnect(self._on_compare_dlg_closed)
            dlg.close()
            dlg.deleteLater()
        self._compare_result = None
        if self.book:
            self.book.diff_cells = {}
            self.book.diff_label = ''
        self.a_cmp_show.setEnabled(False)
        self.a_cmp_clear.setEnabled(False)

    def on_compare_clear(self):
        had = self._compare_result is not None
        self._discard_comparison()
        if self.book:
            self._refresh_models()
        self.lbl_status.setText('Comparison cleared.' if had
                                else 'No comparison to clear.')

    def _on_diff_jump(self, sheet, row, col):
        if sheet in self.book.sheets:
            self.show_sheet(sheet, row, col)
            self.raise_()
            self.activateWindow()

    def _on_diff_apply(self, items):
        by_sheet = {}
        for sheet, row, col, value in items:
            by_sheet.setdefault(sheet, []).append((row, col, value))
        self.undo.beginMacro(f'Take {len(items)} value(s) from compared file')
        try:
            for sheet, cells in by_sheet.items():
                model = self._model_for(sheet)
                payload = []
                for row, col, value in cells:
                    old = model.raw(row, col)
                    if old != value:
                        payload.append((row, col, old, value))
                if payload:
                    self.undo.push(MultiSetCommand(
                        model, payload, f'{sheet}: take {len(payload)} value(s)'))
        finally:
            self.undo.endMacro()
        self._update_title()
        self.lbl_status.setText(
            f'Copied {len(items)} value(s) from the compared file. '
            'Press Ctrl+S to write them to disk.')

    def _on_diff_highlight(self, on):
        if not self.book:
            return
        if on and self._compare_result is not None:
            self.book.diff_cells = self._compare_result.cell_map()
        else:
            self.book.diff_cells = {}
        self._refresh_models()

    def _refresh_models(self):
        for m in self._models.values():
            m.refresh_all()

    # -------------------------------------------------------------- menu
    def on_context_menu(self, pos):
        if not self.model:
            return
        idx = self.tbl.indexAt(pos)
        if not idx.isValid():
            return
        src = self.proxy.mapToSource(idx)
        r, c = src.row(), src.column()
        sheet = self.model.sheet
        tbl = self.book.enum_for(sheet, c)
        val = self.model.raw(r, c)

        m = QMenu(self)
        if not sheet.startswith('Enum_'):
            a0 = m.addAction('Details for this record\tCtrl+Shift+I')
            a0.triggered.connect(lambda: self._detail_for(sheet, r))
            m.addSeparator()
        if tbl and tbl.name != '@bool' and isinstance(val, int):
            target = self.book.data_sheet_for_enum(tbl.name)
            desc = tbl.code2desc.get(val, '?')
            if target and target in self.book.sheets:
                a = m.addAction(f'Go to {target}  \u2192  {desc}')
                a.triggered.connect(lambda: self._jump_to_record(target, val))
            a2 = m.addAction(f'Open code table Enum_{tbl.name}')
            a2.triggered.connect(lambda: self._jump_to_enum(tbl.name, val))
            m.addSeparator()
        a3 = m.addAction('Copy\tCtrl+C')
        a3.triggered.connect(self.on_copy)
        a4 = m.addAction('Paste\tCtrl+V')
        a4.triggered.connect(self.on_paste)
        a5 = m.addAction('Revert to original\tCtrl+R')
        a5.triggered.connect(self.on_revert_cell)
        m.addSeparator()
        head = self.model.sd.headers[c] if c < len(self.model.sd.headers) else ''
        a6 = m.addAction(f'Filter rows by this \u201c{head}\u201d value')
        a6.triggered.connect(
            lambda: self.ed_filter.setText(str(val) if val is not None else ''))
        m.exec(self.tbl.viewport().mapToGlobal(pos))

    def _jump_to_record(self, sheet, code):
        sd = self.book.sheets[sheet]
        for i in range(len(sd.rows)):
            if self.book.value(sheet, i, 0) == code:
                self.show_sheet(sheet, i, 1 if len(sd.headers) > 1 else 0)
                return
        QMessageBox.information(self, APP_NAME,
                                f'No record with code {code} found in {sheet}.')

    def _jump_to_enum(self, ename, code):
        sheet = 'Enum_' + ename
        if sheet not in self.book.sheets:
            return
        sd = self.book.sheets[sheet]
        for i in range(len(sd.rows)):
            if self.book.value(sheet, i, 0) == code:
                self.show_sheet(sheet, i, 1)
                return
        self.show_sheet(sheet)

    # -------------------------------------------------------------- misc
    def _update_title(self):
        if not self.book:
            self.setWindowTitle(APP_NAME)
            self.lbl_dirty.setText('')
            return
        n = len(self.book.edits)
        star = ' •' if n else ''
        self.setWindowTitle(f'{APP_NAME} - {os.path.basename(self.book.path)}{star}')
        self.lbl_dirty.setText(f'{n} cells edited' if n else 'Saved')


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    # Only auto-open when a path was passed on the command line (or a file was
    # dropped on the shortcut). Otherwise show the welcome screen so the user
    # picks a file through the menu.
    path = argv[1] if len(argv) > 1 else None
    w = MainWindow(path)
    w.show()
    return app.exec()
