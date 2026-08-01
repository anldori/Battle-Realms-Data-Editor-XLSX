"""
brde.about - the About dialog and the changelog it shows.

CHANGELOG is the single source of truth for the version history. When you add a
release, add it here first; `README.md` carries a shortened copy for people
reading the project on the web.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from . import __version__

AUTHOR = '@anldori  [VN]DaoAnhDuy'

TAGLINE = ('Editor for Battle Realms game data in the newer Battle Realms.xlsx '
           'format that replaced the old .dat files.')

# (version, when, [changes]) - newest first.
CHANGELOG = [
    ('1.1.0', 'current', [
        '<b>Compare two files.</b> Diff your mod against vanilla, or two '
        'versions of your own work. Rows are matched by their Type key rather '
        'than by position, so inserting a record no longer reports every row '
        'below it as changed. Differences can be filtered, exported to CSV, '
        'and taken back into your file as ordinary undoable edits.',
        '<b>Record details.</b> Search a unit or building by name and read '
        'every stat on one page, including the damage and range of each weapon '
        'it carries, which live in a different sheet. Everything on the page is '
        'editable in place.',
    ]),
    ('1.0.0', 'first release', [
        'First release. Browse and edit every sheet, with dropdowns instead of '
        'raw code numbers, undo/redo, copy and paste, and saving that patches '
        'the XML inside the .xlsx so untouched parts of the file stay '
        'byte-for-byte identical.',
    ]),
]


def changelog_html():
    parts = []
    for version, when, changes in CHANGELOG:
        label = f'Version {version}'
        if when:
            label += f'  <span style="color:#5a6b85;">({when})</span>'
        parts.append(f'<p style="margin:14px 0 4px 0;"><b>{label}</b></p>')
        parts.append('<ul style="margin:0 0 0 -22px;">')
        for c in changes:
            parts.append(f'<li style="margin-bottom:6px;">{c}</li>')
        parts.append('</ul>')
    return ''.join(parts)


class AboutDialog(QDialog):
    """Who made it, what it does, and what changed in each version."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('About Battle Realms Data Editor')
        self.resize(620, 560)
        self.setSizeGripEnabled(True)

        v = QVBoxLayout(self)
        v.setSpacing(4)

        title = QLabel('Battle Realms Data Editor')
        f = QFont()
        f.setBold(True)
        f.setPointSize(15)
        title.setFont(f)
        v.addWidget(title)

        version = QLabel(f'Version {__version__}')
        version.setStyleSheet('color:#5a6b85;')
        v.addWidget(version)
        v.addSpacing(10)

        author = QLabel(f'Created by <b>{AUTHOR}</b>')
        author.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        v.addWidget(author)
        v.addSpacing(10)

        tagline = QLabel(TAGLINE)
        tagline.setWordWrap(True)
        v.addWidget(tagline)
        v.addSpacing(14)

        heading = QLabel('Changelog')
        fh = QFont()
        fh.setBold(True)
        heading.setFont(fh)
        v.addWidget(heading)

        body = QLabel(changelog_html())
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setContentsMargins(4, 0, 4, 0)

        holder = QWidget()
        hv = QVBoxLayout(holder)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.addWidget(body)
        hv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.StyledPanel)
        v.addWidget(scroll, 1)

        note = QLabel(
            'On save, the XML inside the .xlsx archive is patched in place, so '
            'every part of the file that was not edited stays byte-for-byte '
            'identical and the original formatting is preserved.'
            '<br><br>Built with Python, PyQt6 and openpyxl.')
        note.setWordWrap(True)
        note.setStyleSheet('color:#5a6b85;')
        v.addWidget(note)

        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton('Close')
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        v.addLayout(row)
