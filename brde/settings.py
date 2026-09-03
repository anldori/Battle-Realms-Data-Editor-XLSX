"""Settings dialog for theme selection."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QRadioButton, QButtonGroup, QPushButton)

LIGHT_THEME = 'light'
DARK_THEME = 'dark'
SYSTEM_THEME = 'system'

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


class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_theme=SYSTEM_THEME):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        theme_label = QLabel('Theme:')
        layout.addWidget(theme_label)

        self.theme_group = QButtonGroup(self)

        light_radio = QRadioButton('Light')
        dark_radio = QRadioButton('Dark')
        system_radio = QRadioButton('System default')

        self.theme_group.addButton(light_radio, 0)
        self.theme_group.addButton(dark_radio, 1)
        self.theme_group.addButton(system_radio, 2)

        layout.addWidget(light_radio)
        layout.addWidget(dark_radio)
        layout.addWidget(system_radio)

        if current_theme == LIGHT_THEME:
            light_radio.setChecked(True)
        elif current_theme == DARK_THEME:
            dark_radio.setChecked(True)
        else:
            system_radio.setChecked(True)

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

    def get_theme(self):
        checked_id = self.theme_group.checkedId()
        if checked_id == 0:
            return LIGHT_THEME
        elif checked_id == 1:
            return DARK_THEME
        else:
            return SYSTEM_THEME
