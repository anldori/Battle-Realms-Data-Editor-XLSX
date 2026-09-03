"""
brde.about - the About dialog and the changelog it shows.

CHANGELOG is the single source of truth for the version history. When you add a
release, add it here first, then copy it into `CHANGELOG.md`, which is the same
list for people reading the project on the web. `tests/test_version.py` checks
that the two agree and that both lead with `__version__`.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from . import __version__

AUTHOR = '@anldori  [VN]DaoAnhDuy'

TAGLINE = ('Editor for Battle Realms game data in the newer Battle Realms.xlsx '
           'format that replaced the old .dat files. It also opens those .dat '
           'files, read-only, so an old mod can still be read.')

# (version, when, [changes]) - newest first.
#
# Keep these short, and keep them about what the user can now do. The list is
# read in a dialog, not in a design document: the reasoning behind a change
# belongs in CLAUDE.md and the detail of how it works belongs in README.md.
# One or two lines a bullet, a handful of bullets a release.
CHANGELOG = [
    ('1.6.0', 'current', [
        '<b>A dark theme.</b> <i>Settings &gt; Themes</i> switches between '
        'light, dark, and whatever the system is set to, and remembers which '
        'you picked.',
        '<b>The font is yours to choose.</b> <i>Settings &gt; Display</i> sets '
        'the typeface, its size, and how tall a grid row is, with a '
        '<i>Reset to default</i> that puts back what the editor started with.',
        '<b>Backups can be turned off, or kept short.</b> <i>Settings &gt; '
        'Saving</i> stops the timestamped <code>.bak</code> appearing beside '
        'your workbook on every save, or caps it at the last few so the folder '
        'stays tidy.',
        '<b>Auto-save, if you want it.</b> Off by default. Turn it on and '
        'every edit is written to the file as you make it, and '
        '<code>Ctrl+Z</code> still undoes as normal.',
    ]),
    ('1.5.0', '', [
        "<b>Open the game's old <code>.dat</code> file.</b> "
        '<i>File &gt; Open old .dat file...</i> reads Battle Realms.dat, the '
        'format the spreadsheet replaced, so an old mod can still be read '
        'without the original editor.',
        '<b>It opens read-only.</b> Browse every sheet, search for a record, '
        'compare two units, and diff it against a workbook - but nothing in '
        'it can be edited or saved. The title bar says so while one is open.',
        'Everything else works on it unchanged: dropdowns instead of code '
        'numbers, colour previews, and the record page.',
    ]),
    ('1.4.0', '', [
        '<b>A colour picker built for this file</b>, in place of the system '
        "panel's grid of 48 fixed colours. A large picking surface, a proper "
        'hex field, and a screen picker that lifts a colour straight off a '
        'screenshot of the game.',
        '<b>The colours already in the sheet are shown beside the one being '
        'picked</b>, with the row you are editing ringed among them. Choosing '
        'a team colour is about telling it apart from the other ten, which '
        'can only be judged next to them. Click one to take it.',
        '<b>A warning when two colours are about to be confused</b>, naming '
        'the row it clashes with. Set just under the closest pair the game '
        'itself ships, so the unmodified file stays silent.',
        'The old colour sits beside the new one while you pick. Click it to '
        'put it back.',
        'Transparency has a slider of its own over a checkerboard. The system '
        'picker had no alpha channel at all.',
    ]),
    ('1.3.0', '', [
        '<b>Colours look like colours.</b> A colour in this file is three or '
        'four separate number columns, so a band of the colour now runs along '
        'the bottom of the cells that make it.',
        '<b>Pick a colour instead of typing three numbers.</b> Right-click it '
        'in the grid, or double-click it on a record page. One undo step, and '
        'only the channels that actually changed are written.',
        '<b>A record that stores more than one colour sets them together.</b> '
        'A team colour and its minimap colour come from one dialog, and the '
        'menu entry names every colour it will overwrite.',
        'A record page with colours opens with them, shown as a bar with the '
        'hex code across it. The channels stay below as editable fields.',
        'Transparency is drawn over a checkerboard, so a faint colour is not '
        'mistaken for a blank one.',
    ]),
    ('1.2.1', '', [
        '<b>Fixed: the unit comparison used weapons the fight never '
        'reaches.</b> A Dragon Samurai against a Serpent Ronin was scored '
        "with the samurai's arrow, which needs 7 clear and is never fired at "
        'something that close. It swings its katana now.',
        '<b>The comparison runs once per distance</b> - one table at range, '
        'one in melee - and every weapon says which of the two it is in.',
        '<b>A unit that wins at one distance and loses at the other is no '
        'longer given the win.</b> The verdict names both and says where each '
        'one wins.',
        'The window opens empty instead of comparing the first two units in '
        'the list before being asked.',
        'A standing note that the verdict is for reference: the file holds no '
        'attack speed, reach, formation or terrain.',
    ]),
    ('1.2.0', '', [
        '<b>Compare two units.</b> <i>Compare &gt; Compare units...</i> '
        '(Ctrl+U) puts cost, health, all six armour multipliers and every '
        'weapon side by side, with a sentence naming the winner.',
        '<b>The counter is worked out for you.</b> An armour multiplier '
        'scales the damage a unit <i>takes</i>, so above 1 is a weakness - '
        'backwards from most games. The page gives the damage that lands and '
        'the hits to kill, rather than leaving it to be read the wrong way '
        'round.',
        '<b>Techniques are applied</b>, so you compare units as they are '
        'actually fielded. Every value a technique moved is shown as '
        '<code>450 -&gt; 630</code>. Untick to see the file as written.',
        'Green is good for the unit in that column and red is bad for it. The '
        'comparison follows your edits live and exports to CSV.',
    ]),
    ('1.1.1', '', [
        "<b>Abilities on the record page.</b> A unit's innate abilities, the "
        'ability each piece of battle gear grants, its spells, and every '
        'technique that affects it - each with its own stats, editable in '
        'place.',
        '<b>Buildings show what they research.</b> A tavern or a dojo now '
        'lists its techniques and upgrades with cost, time and affected '
        'units, plus the buildings needed first.',
        '<b>Records are findable by their real name.</b> Most sheets do not '
        'call the name column "Name", so "Dragon Skin" and "Sight Beyond '
        'Sight" used to find nothing. The record you meant still ranks first.',
        '<b>Several columns were reading from the wrong list.</b> Weapon and '
        'upgrade classes, technique effects, battle gear, and ten yes/no '
        'switches that had turned into dropdowns of units. All of them now '
        'show what they mean.',
        'Less repetition under "Referenced by", and the window carries the '
        'program icon in the title bar and on the taskbar.',
    ]),
    ('1.1.0', '', [
        '<b>Compare two files.</b> Diff your mod against vanilla, or two '
        'versions of your own work. Rows are matched by their key rather than '
        'by position, so inserting a record no longer reports every row below '
        'it as changed. Differences can be filtered, exported, and taken back '
        'into your file as ordinary undoable edits.',
        '<b>Record details.</b> Search a unit or building by name and read '
        'every stat on one page, including the weapon damage that lives in '
        'another sheet. Everything on the page is editable in place.',
    ]),
    ('1.0.0', 'first release', [
        'First release. Browse and edit every sheet, with dropdowns instead '
        'of raw code numbers, undo and redo, copy and paste, and a save that '
        'leaves every part of the file you did not touch exactly as it was.',
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
            'Saving changes only the cells you edited. Every other part of '
            'your file, and all of its formatting, is left exactly as it was.'
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
