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
    ('1.2.1', 'current', [
        '<b>The comparison was picking a weapon the fight never uses.</b> It '
        'scored every weapon a unit carried together and reported whichever '
        'landed the most damage, with no regard for how far away that weapon '
        'works. A Dragon Samurai against a Serpent Ronin came out as a samurai '
        'arrow against ronin swords - but the arrow needs 7 clear and the Ronin '
        'never fights further off than 0.5, so the shot is never taken. The '
        'Samurai swings its katana, and that is now what the matchup says.',
        '<b>The matchup runs once per distance.</b> "Counter matchup at range" '
        'and "Counter matchup in melee" are separate tables, each holding only '
        'the weapons usable at that distance, and each weapon in the weapon '
        'list says which of the two it belongs to. A unit with nothing to fire '
        'back is called out rather than left as an empty column.',
        '<b>A unit that wins at one distance and loses at the other is no '
        'longer given the win.</b> The Dragon Archer beats the Dragon Spearman '
        'at range and loses to it in contact, so the verdict names both and '
        'leaves the fight to whoever gets the range they want. A winner is '
        'declared only where one unit wins everywhere it can reach.',
        'The slot a weapon sits in never meant "main weapon" and is no longer '
        'read as if it did - the Samurai\'s <code>PrimaryWeapon</code> is its '
        'arrow and its katana sits in the secondary slot.',
        '<b>The window no longer opens on a comparison nobody asked for.</b> '
        'It used to load the first two units in the list and show a verdict '
        'about them straight away. Both boxes now start empty and wait to be '
        'filled in.',
        '<b>A standing note that the verdict is for reference.</b> The page '
        'compares the numbers in the file, and a real fight also turns on '
        'attack and animation speed, reach and unit size, formation and '
        'terrain, stamina, abilities, and who strikes first. The note stays on '
        'screen while the comparison is being read, and goes into the CSV '
        'export with it.',
    ]),
    ('1.2.0', '', [
        '<b>Compare two units.</b> Compare &gt; Compare units... (Ctrl+U) puts '
        'two units in two columns - cost, health, all six armour multipliers, '
        'and every weapon with its damage class and damage - and says which '
        'one beats which.',
        '<b>The counter is spelled out rather than left to be worked out.</b> '
        'An armour multiplier scales the damage a unit takes, so above 1 is a '
        'weakness and below 1 is resistance, which reads backwards from armour '
        'in most games. "Counter matchup" runs each unit\'s weapons against '
        'the other\'s armour and gives the damage landed and the hits to kill, '
        'and a sentence at the top names the winner: the Dragon Spearman\'s '
        'AMPiercing of 4.0 means a Samurai arrow lands 104 damage and kills in '
        'three hits, against 120 hits coming back.',
        '<b>Upgraded units, not paper ones.</b> Health, armour and weapon '
        'damage all move once techniques are researched, so comparing the raw '
        'sheet values describes units nobody ever fields. "Apply techniques" '
        'recomputes both sides fully upgraded and shows every value a '
        'technique moved as "base -&gt; upgraded". Ten placeholder rows in '
        'Data_Techniques that each multiply the Dragon Archer\'s damage by 1.4 '
        'are left out: nothing researches them, and stacked they would turn an '
        '18 damage arrow into 730.',
        'Green means good for the unit in that column and red means bad for '
        'it, in the armour rows and the matchup rows alike.',
        'The comparison exports to CSV, follows edits live, and right-clicking '
        'a row in Data_Units loads that unit straight into it.',
    ]),
    ('1.1.1', '', [
        '<b>Abilities on the record page.</b> A unit\'s abilities were missing, '
        'because <code>Data_Units</code> has no ability column at all - the link '
        'runs through a separate join sheet. The page now follows it, and shows '
        'innate abilities, the ability each piece of battle gear grants, spells, '
        'and the techniques that affect the unit, each with its name and key '
        'stats and editable in place. The Dragon Samurai gets its Seppuku, '
        'Dragon Skin and Yang Blade.',
        '<b>Less noise under "Referenced by".</b> Rows a curated section has '
        'already laid out properly are no longer repeated at the bottom of the '
        'page under a worse label. References into the same sheet through a '
        'different column are still listed.',
        'Techniques now name the ability they change instead of showing a bare '
        'code number.',
        '<b>Records are findable by their real name.</b> Only 32 of the 87 data '
        'sheets call the name column "Name" - abilities call it ActualAbility, '
        'weapons ActualWeapon - so searching for "Dragon Skin" or "Sight Beyond '
        'Sight" found nothing, even though the record page was already showing '
        'that name. The record you meant still ranks first: "samurai" leads '
        'with the Dragon Samurai, not with its sound effects.',
        '<b>A building\'s docked ability is spelled out</b>, the way a unit\'s '
        'abilities are. The Dragon Monument and the Lotus Warlock\'s Tower now '
        'show what docking there actually does.',
        '<b>Battle gear columns showed bare numbers.</b> A hero\'s '
        'DefaultBattleGear read "82" instead of naming the gear, and the gear '
        'combination columns had no dropdown at all. Hero Arah now shows '
        'BATTLE_GEAR_HERO_ARAH_ZEN_ARROWS and the ability behind it, Sight '
        'Beyond Sight. The unit page also lists the gear combinations that '
        'belong to the unit.',
        '<b>Weapon and upgrade classes were reading from the wrong code '
        'table.</b> A weapon\'s Class showed OBJECTCLASS_WATER when it means '
        'WEAPONCLASS_PROJECTILE, and an upgrade\'s showed the same plant / '
        'stone / water table instead of offensive / defensive / misc.',
        '<b>Ten yes/no switches had become dropdowns of the wrong thing.</b> '
        'Columns such as CreateUnit, RemoveEnemyUpgrade and AIAlwaysAddUnit end '
        'in a word that names a code table, so they were offering a list of '
        'units or upgrades where the answer is only yes or no. The real '
        'reference sits in the column beside them, and those were never '
        'touched: CreatedUnitType, SetWeapon and UpgradeUnit still resolve '
        'normally.',
        '<b>Technique effects were reading from the wrong code table.</b> '
        'TECHNIQUE_DRAGONS_STRENGTH showed "EFFECT_BALLISTAMAN_TOTEM_IMPACT" '
        'when the code means TE_WP_MULT_DAMAGE - multiply weapon damage, by the '
        'factor beside it. Effect columns in Data_Techniques now read '
        'Enum_TechniqueEffectType, and each one is shown next to the FloatParam '
        'it scales by, so the pair reads as one statement.',
        '<b>Buildings show what they research.</b> A tavern or a dojo never '
        'listed its techniques and upgrades, because those sheets point at the '
        'building rather than the other way round. There is now a "Researched '
        'here" section with the cost, time and affected units of each one, plus '
        'a "Requires" section for the buildings needed first. The old '
        '"Upgrades to" section is now called "Upgrades into another building", '
        'which is what it always meant.',
        '<b>The window now carries the program icon</b> in the title bar and on '
        'the taskbar, not just in File Explorer.',
    ]),
    ('1.1.0', '', [
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
