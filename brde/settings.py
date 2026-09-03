"""Theme styles, and the Saving and Display preference dialogs.

Neither dialog owns a QSettings: the window that opens one passes its own in,
so preferences are read back from where they were written. The test suite
points MainWindow at an ini file in a temp directory, and a dialog that built
its own QSettings would quietly write to the user's real one instead.
"""
from PyQt6.QtGui import QColor, QPalette, QFont, QFontDatabase
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QCheckBox, QSpinBox, QGroupBox,
                             QFontComboBox)

LIGHT_THEME = 'light'
DARK_THEME = 'dark'
SYSTEM_THEME = 'system'

# Matches the QTableView default set in app.py, so "Reset to default" and a
# fresh install agree on what an untouched grid looks like.
DEFAULT_ROW_HEIGHT = 22

# Both themes pin `font-size: 12px` on QWidget, and a stylesheet beats
# QApplication.setFont() every time - setting the app font alone changes
# nothing on screen. So the chosen font is compiled into a stylesheet of its
# own and appended after the theme, where a later rule of equal weight wins.
# The `#Welcome*` and `#*Button` rules are ID selectors and outrank this, so
# the welcome screen keeps its own sizes and only picks up the family.
_FONT_STYLE = """
QWidget, QMainWindow, QDialog, QMenuBar, QMenu, QToolBar, QLabel, QPushButton,
QCheckBox, QRadioButton, QComboBox, QSpinBox, QLineEdit, QPlainTextEdit,
QListWidget, QTableView, QHeaderView::section, QGroupBox, QTabBar::tab {
    font-family: "%s";
    font-size: %dpt;
}
"""


def default_font(base_font=None):
    """The font Qt hands out before any preference is applied.

    Callers that have a window pass the font it started with; the fallback is
    for anything with no window to ask, the test suite mainly.
    """
    if base_font is not None:
        return base_font
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)


def font_style(settings, base_font=None):
    """Stylesheet fragment for the saved font, or '' if none was ever saved."""
    if not settings.contains('display/font'):
        return ''
    base = default_font(base_font)
    family = settings.value('display/font', base.family())
    size = settings.value('display/font_size', base.pointSize(), type=int)
    return _FONT_STYLE % (family, size)

DARK_STYLE = """
QMainWindow {
    font-size: 12px;
    background: #1e1e1e;
    color: #f0f0f0;
    border: 1px solid #1e1e1e;
}
QWidget { font-size: 12px; background: #1e1e1e; color: #f0f0f0; }
QListWidget { border: none; background: #2d2d2d; color: #f0f0f0; }
QListWidget::item { padding: 5px 8px; }
QListWidget::item:selected { background: #2d6cdf; color: white; }
QTableView {
    gridline-color: #404040;
    background: #0d0d0d;
    color: #ffffff;
    selection-background-color: #2d6cdf;
    selection-color: #ffffff;
    alternate-background-color: #1a1a1a;
}
QTableView::item {
    padding: 2px;
    color: #ffffff;
    background-color: #0d0d0d;
}
QTableView::item:alternate {
    background-color: #1a1a1a;
}
QHeaderView::section {
    background: #2d2d2d; padding: 4px 6px; border: 0;
    color: #ffffff;
    border-right: 1px solid #3d3d3d; border-bottom: 1px solid #3d3d3d;
}
QLineEdit {
    padding: 4px 6px; border: 1px solid #4d4d4d; border-radius: 4px;
    background: #2d2d2d; color: #f0f0f0;
}
QToolBar { border-bottom: 1px solid #3d3d3d; spacing: 4px; padding: 3px; background: #2d2d2d; }
QMenuBar { background: #2d2d2d; border-bottom: 1px solid #3d3d3d; color: #f0f0f0; }
QMenuBar::item { padding: 5px 11px; }
QMenuBar::item:selected { background: #2d6cdf; color: white; }
QMenu { background: #2d2d2d; color: #f0f0f0; border: 1px solid #3d3d3d; }
QMenu::item:selected { background: #2d6cdf; }
QScrollBar:vertical { background: #2d2d2d; width: 12px; }
QScrollBar::handle:vertical { background: #4d4d4d; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #5d5d5d; }
#Welcome { background: #1e1e1e; }
#WelcomeTitle { font-size: 24px; font-weight: bold; color: #f0f0f0; }
#WelcomeSub { font-size: 13px; color: #b0b0b0; }
#BigButton {
    font-size: 15px; font-weight: bold; color: white; background: #2d6cdf;
    border: none; border-radius: 6px; padding: 12px 30px;
}
#BigButton:hover { background: #3575e8; }
#SecondButton {
    font-size: 13px; color: #2d6cdf; background: #2d2d2d;
    border: 1px solid #4d6cbb; border-radius: 6px; padding: 9px 22px;
}
#SecondButton:hover { background: #3d3d3d; border-color: #2d6cdf; }
#RecentLink {
    text-align: left; border: 1px solid #3d3d3d; border-radius: 5px;
    padding: 8px 12px; background: #252525; color: #f0f0f0;
}
#RecentLink:hover { background: #3d3d3d; border-color: #2d6cdf; }
"""

def get_dark_palette():
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#1e1e1e'))
    palette.setColor(QPalette.ColorRole.WindowText, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.Base, QColor('#0d0d0d'))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#1a1a1a'))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#2d2d2d'))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.Text, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.Button, QColor('#2d2d2d'))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.BrightText, QColor('#ffffff'))
    palette.setColor(QPalette.ColorRole.Link, QColor('#2d6cdf'))
    palette.setColor(QPalette.ColorRole.Highlight, QColor('#2d6cdf'))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
    return palette


def get_light_palette():
    palette = QPalette()
    return palette  # Use default light palette


LIGHT_STYLE = """
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
#SecondButton {
    font-size: 13px; color: #2d6cdf; background: #ffffff;
    border: 1px solid #b9c8e4; border-radius: 6px; padding: 9px 22px;
}
#SecondButton:hover { background: #eef3fc; border-color: #2d6cdf; }
#RecentLink {
    text-align: left; border: 1px solid #dfe3e8; border-radius: 5px;
    padding: 8px 12px; background: #fbfbfd; color: #1c2b45;
}
#RecentLink:hover { background: #eef3fc; border-color: #2d6cdf; }
"""


class SavingSettingsDialog(QDialog):
    # The window that opens this owns the QSettings: the test suite redirects
    # MainWindow's to an ini file in a temp directory, and a dialog that made
    # its own would write somewhere the window never reads.
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle('Saving Settings')
        self.resize(350, 180)
        self.settings = settings if settings is not None else parent.settings

        layout = QVBoxLayout(self)

        # --- Backup section
        backup_group = QGroupBox('Backup')
        backup_group_layout = QVBoxLayout(backup_group)

        self.backup_checkbox = QCheckBox('Enable backup on save')
        self.backup_checkbox.setChecked(
            self.settings.value('backup/enabled', True, type=bool))
        backup_group_layout.addWidget(self.backup_checkbox)

        keep_backup_layout = QHBoxLayout()
        keep_backup_layout.addWidget(QLabel('Keep last'))
        self.backup_count_spinbox = QSpinBox()
        self.backup_count_spinbox.setMinimum(1)
        self.backup_count_spinbox.setMaximum(20)
        self.backup_count_spinbox.setValue(
            self.settings.value('backup/keep_count', 5, type=int))
        keep_backup_layout.addWidget(self.backup_count_spinbox)
        keep_backup_layout.addWidget(QLabel('backups'))
        keep_backup_layout.addStretch()
        backup_group_layout.addLayout(keep_backup_layout)

        layout.addWidget(backup_group)

        # --- Auto-save section
        autosave_group = QGroupBox('Auto-save')
        autosave_group_layout = QVBoxLayout(autosave_group)

        self.autosave_checkbox = QCheckBox('Enable auto-save on change')
        self.autosave_checkbox.setChecked(
            self.settings.value('autosave/enabled', False, type=bool))
        autosave_group_layout.addWidget(self.autosave_checkbox)

        layout.addWidget(autosave_group)
        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton('OK')
        cancel_btn = QPushButton('Cancel')
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_backup_enabled(self):
        return self.backup_checkbox.isChecked()

    def get_backup_keep_count(self):
        return self.backup_count_spinbox.value()

    def get_autosave_enabled(self):
        return self.autosave_checkbox.isChecked()

    def save_settings(self):
        self.settings.setValue('backup/enabled', self.get_backup_enabled())
        self.settings.setValue('backup/keep_count', self.get_backup_keep_count())
        self.settings.setValue('autosave/enabled', self.get_autosave_enabled())


class DisplaySettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None, base_font=None):
        super().__init__(parent)
        self.setWindowTitle('Display Settings')
        self.resize(400, 200)
        self.settings = settings if settings is not None else parent.settings
        # What "Reset to default" goes back to: the font the window started
        # with, before any of this touched it.
        self._default_font = default_font(base_font)

        layout = QVBoxLayout(self)

        # --- Font section
        font_group = QGroupBox('Font')
        font_group_layout = QVBoxLayout(font_group)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel('Font:'))
        self.font_combo = QFontComboBox()

        current_font = self.settings.value('display/font',
                                           self._default_font.family())
        self.font_combo.setCurrentFont(QFont(current_font))
        font_layout.addWidget(self.font_combo)
        font_group_layout.addLayout(font_layout)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel('Font size:'))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setMinimum(8)
        self.font_size_spinbox.setMaximum(24)
        self.font_size_spinbox.setValue(
            self.settings.value('display/font_size',
                                self._default_font.pointSize(), type=int))
        size_layout.addWidget(self.font_size_spinbox)
        size_layout.addWidget(QLabel('pt'))
        size_layout.addStretch()
        font_group_layout.addLayout(size_layout)

        layout.addWidget(font_group)

        # --- Grid section
        grid_group = QGroupBox('Grid')
        grid_group_layout = QVBoxLayout(grid_group)

        row_height_layout = QHBoxLayout()
        row_height_layout.addWidget(QLabel('Row height:'))
        self.row_height_spinbox = QSpinBox()
        self.row_height_spinbox.setMinimum(16)
        self.row_height_spinbox.setMaximum(48)
        self.row_height_spinbox.setValue(
            self.settings.value('display/row_height', DEFAULT_ROW_HEIGHT,
                                type=int))
        row_height_layout.addWidget(self.row_height_spinbox)
        row_height_layout.addWidget(QLabel('px'))
        row_height_layout.addStretch()
        grid_group_layout.addLayout(row_height_layout)

        layout.addWidget(grid_group)
        layout.addStretch()

        button_layout = QHBoxLayout()
        reset_btn = QPushButton('Reset to default')
        reset_btn.clicked.connect(self._reset_to_default)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        ok_btn = QPushButton('OK')
        cancel_btn = QPushButton('Cancel')
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _reset_to_default(self):
        self.font_combo.setCurrentFont(self._default_font)
        self.font_size_spinbox.setValue(self._default_font.pointSize())
        self.row_height_spinbox.setValue(DEFAULT_ROW_HEIGHT)

    def get_font(self):
        return self.font_combo.currentFont().family()

    def get_font_size(self):
        return self.font_size_spinbox.value()

    def get_row_height(self):
        return self.row_height_spinbox.value()

    def save_settings(self):
        self.settings.setValue('display/font', self.get_font())
        self.settings.setValue('display/font_size', self.get_font_size())
        self.settings.setValue('display/row_height', self.get_row_height())
