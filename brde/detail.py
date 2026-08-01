"""
brde.detail - the record details window.

Type a unit or building name, pick it from the list of matches, and see every
stat that belongs to it on one page instead of hunting across sheets. Values are
editable in place and go through the same undo stack as the main grid.

Two layers build the page:

* A generic builder that works for any sheet. It lists the record's own columns,
  resolves outgoing references to the record they point at, and finds the rows in
  other sheets that point back at this one.
* Curated profiles (PROFILES) for the sheets people actually tune - units,
  buildings and weapons - which order the interesting fields into named sections
  and pull in figures that live on a referenced record, such as the damage of the
  weapon a unit carries. Columns a profile does not mention still show up under
  "Other fields", so nothing is ever hidden.
"""
from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QCompleter, QDialog,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QPushButton,
                             QSplitter, QTableView, QVBoxLayout, QWidget,
                             QStyledItemDelegate)

SECTION_BG = QColor(233, 238, 246)
SECTION_FG = QColor(28, 43, 69)
LINK_FG = QColor(45, 108, 223)
EDITED_BG = QColor(255, 243, 205)
MUTED_FG = QColor(120, 132, 150)

MAX_RESULTS = 400


# --------------------------------------------------------------------- helpers
def _text(book, sheet, row, col):
    """Cell value as shown to the user: 'code - DESCRIPTION' for enum columns."""
    v = book.value(sheet, row, col)
    if v is None:
        return ''
    tbl = book.enum_for(sheet, col)
    if tbl and isinstance(v, int):
        d = tbl.code2desc.get(v)
        if d:
            return f'{v} - {d}'
    return str(v)


def _header(book, sheet, col):
    h = book.sheets[sheet].headers
    return h[col] if col < len(h) else f'column {col}'


def _col(book, sheet, name):
    """Column index by header name, or None."""
    try:
        return book.sheets[sheet].headers.index(name)
    except ValueError:
        return None


def _find_row(book, sheet, code):
    """Row index whose first column equals `code`, or None."""
    sd = book.sheets.get(sheet)
    if sd is None or code is None:
        return None
    for i in range(len(sd.rows)):
        if book.value(sheet, i, 0) == code:
            return i
    return None


def record_title(book, sheet, row):
    """Best human label for a record: its Name column, else its enum description."""
    sd = book.sheets.get(sheet)
    if sd is None:
        return sheet
    name = ''
    if len(sd.headers) > 1 and sd.headers[1].lower() == 'name':
        v = book.value(sheet, row, 1)
        name = str(v) if v is not None else ''
    code = book.value(sheet, row, 0)
    desc = ''
    if sd.self_enum and isinstance(code, int):
        tbl = book.enums.get(sd.self_enum)
        if tbl:
            desc = tbl.code2desc.get(code, '')
    if name and desc:
        return f'{name}  ({desc})'
    return name or desc or f'{sheet} row {row + 2}'


# ----------------------------------------------------------------- page pieces
class Field:
    """One editable line on the page. Always points at a real cell."""

    __slots__ = ('label', 'sheet', 'row', 'col', 'indent', 'link')

    def __init__(self, label, sheet, row, col, indent=0, link=None):
        self.label = label
        self.sheet = sheet
        self.row = row
        self.col = col
        self.indent = indent
        self.link = link          # (sheet, row) to open when double-clicked


class Note:
    """A non-editable line, used for 'nothing here' and reverse-reference links."""

    __slots__ = ('label', 'value', 'indent', 'link')

    def __init__(self, label, value='', indent=0, link=None):
        self.label = label
        self.value = value
        self.indent = indent
        self.link = link


class Section:
    __slots__ = ('title', 'items')

    def __init__(self, title, items):
        self.title = title
        self.items = items


# -------------------------------------------------------------------- profiles
# Sub-columns pulled in from Data_Weapons when a unit's weapon is expanded.
WEAPON_STATS = ['BaseDamage', 'StaminaDamage', 'DamageClass', 'MinRange',
                'MaxRange', 'Recovery', 'AreaOfEffect', 'SiegeMult',
                'RiderPercentage', 'PoisonDamage', 'PoisonTime',
                'HealthVampirePercentage', 'AssociatedProjectile']

# Sub-columns pulled in from Data_Abilities when an ability is expanded.
# That sheet is 175 columns wide and almost all of them are switches meaningful
# to one single ability, so the page shows a curated set: what kind of ability
# it is, what it costs, how long it lasts. Double-click the heading to open the
# full record. UsageType is the one to read first - USAGETYPE_OMNIPRESENT means
# the ability is passive, it is always on and has no button.
ABILITY_STATS = ['UsageType', 'Toggleable', 'LimitedCharges', 'TargetRange',
                 'Range', 'Delay', 'DurationOfEffect', 'ChanceOfOccuring',
                 'MinStaminaRequired', 'StaminaCost', 'HealthCost', 'YinCost',
                 'YangCost']

BATTLE_GEAR_STATS = ['RiceCost', 'WaterCost', 'Time', 'AcquisitionType']

SPELL_STATS = ['Range', 'StaminaCost', 'MinStamina', 'TargetEffect', 'AnimState']

TECHNIQUE_STATS = ['YangNeeded', 'Cost', 'Time', 'AssociatedBuilding',
                   'AbilityAffected1', 'AbilityAffected2', 'Effect1']

# Same list seen from the building that researches the technique. AssociatedBuilding
# is dropped - it is the record you are already looking at - and the units the
# technique benefits are shown instead.
TECHNIQUE_AT_BUILDING_STATS = ['YangNeeded', 'Cost', 'Time', 'Unit1', 'Unit2',
                               'Unit3', 'Unit4', 'AbilityAffected1',
                               'AbilityAffected2', 'Effect1']

UPGRADE_STATS = ['YangNeeded', 'Cost', 'Time', 'Value', 'Class', 'Secret',
                 'AlternateWeapon', 'Unit1', 'Unit2', 'Unit3', 'Unit4']


def _expand(col, target_sheet, subcols):
    """Profile item: show `col`, then the listed columns of the record it names."""
    return ('expand', col, target_sheet, subcols)


def _units_trained_at(book, sheet, row):
    """Which buildings train this unit, from Data_Buildings.UnitOut1..6."""
    code = book.value(sheet, row, 0)
    out = []
    bs = book.sheets.get('Data_Buildings')
    if bs is None or not isinstance(code, int):
        return out
    for slot in range(1, 7):
        c_out = _col(book, 'Data_Buildings', f'UnitOut{slot}')
        if c_out is None:
            continue
        c_in = _col(book, 'Data_Buildings', f'UnitIn{slot}')
        c_time = _col(book, 'Data_Buildings', f'UnitTrainingTime{slot}')
        for i in range(len(bs.rows)):
            if book.value('Data_Buildings', i, c_out) != code:
                continue
            title = record_title(book, 'Data_Buildings', i)
            out.append(Note(title, f'slot {slot}', link=('Data_Buildings', i)))
            if c_in is not None:
                out.append(Field('From unit', 'Data_Buildings', i, c_in, indent=1))
            if c_time is not None:
                out.append(Field('Training time', 'Data_Buildings', i, c_time,
                                 indent=1))
    if not out:
        out.append(Note('Not trained by any building', ''))
    return out


_units_trained_at.consumes = [('Data_Buildings', f'UnitOut{i}') for i in range(1, 7)]


def _building_training(book, sheet, row):
    """The six UnitIn/UnitOut training slots, skipping the empty ones."""
    out = []
    for slot in range(1, 7):
        c_out = _col(book, sheet, f'UnitOut{slot}')
        if c_out is None:
            continue
        if book.value(sheet, row, c_out) in (None, -1):
            continue
        out.append(Note(f'Slot {slot}', ''))
        for label, name in (('Trains', f'UnitOut{slot}'),
                            ('From unit', f'UnitIn{slot}'),
                            ('Training time', f'UnitTrainingTime{slot}'),
                            ('Training rate', f'UnitTrainingRate{slot}')):
            c = _col(book, sheet, name)
            if c is not None:
                out.append(Field(label, sheet, row, c, indent=1))
    if not out:
        out.append(Note('Trains no units', ''))
    return out


def _ability_block(book, code, indent=0):
    """The curated stats of one ability. Returns (items, row in Data_Abilities).

    The row comes back so the caller can point its own heading line at the full
    record, which is what makes double-clicking the heading open Data_Abilities.
    """
    if code in (None, -1):
        return [], None
    arow = _find_row(book, 'Data_Abilities', code)
    if arow is None:
        return [Note('Not defined in Data_Abilities', '', indent=indent)], None
    out = []
    c = _col(book, 'Data_Abilities', 'ActualAbility')
    if c is not None:
        out.append(Field('Name', 'Data_Abilities', arow, c, indent=indent))
    for sub in ABILITY_STATS:
        sc = _col(book, 'Data_Abilities', sub)
        if sc is not None:
            out.append(Field(sub, 'Data_Abilities', arow, sc, indent=indent))
    return out, arow


def _unit_abilities(book, sheet, row):
    """Innate abilities, read from the Data_UnitAndInnateAbilities join sheet.

    Data_Units has no ability column at all - the link lives in a separate
    two-column sheet - which is why an ability such as the Dragon Samurai's
    Seppuku is invisible on the unit's own row.
    """
    join = 'Data_UnitAndInnateAbilities'
    sd = book.sheets.get(join)
    code = book.value(sheet, row, 0)
    out = []
    if sd is None or not isinstance(code, int):
        return out
    c_unit = _col(book, join, 'UnitType')
    c_ab = _col(book, join, 'AbilityType')
    if c_unit is None or c_ab is None:
        return out
    n = 0
    for i in range(len(sd.rows)):
        if book.value(join, i, c_unit) != code:
            continue
        n += 1
        f = Field(f'Innate ability {n}', join, i, c_ab)
        stats, arow = _ability_block(book, book.value(join, i, c_ab), indent=1)
        if arow is not None:
            f.link = ('Data_Abilities', arow)
        out.append(f)
        out.extend(stats)
    if not out:
        out.append(Note('No innate abilities', ''))
    return out


_unit_abilities.consumes = [('Data_UnitAndInnateAbilities', 'UnitType')]


def _unit_battle_gear(book, sheet, row):
    """The battle gear slots, each expanded into the ability it grants.

    A unit names a gear code; the ability behind it is two sheets away, through
    Data_BattleGear.AbilityType into Data_Abilities.
    """
    out = []
    for name in ('BattleGear1', 'BattleGear2', 'BattleGear3', 'DefaultBattleGear'):
        c = _col(book, sheet, name)
        if c is None:
            continue
        f = Field(name, sheet, row, c)
        code = book.value(sheet, row, c)
        grow = _find_row(book, 'Data_BattleGear', code) \
            if code not in (None, -1) else None
        if grow is not None:
            f.link = ('Data_BattleGear', grow)
        out.append(f)
        if grow is None:
            continue
        for sub in BATTLE_GEAR_STATS:
            sc = _col(book, 'Data_BattleGear', sub)
            if sc is not None:
                out.append(Field(sub, 'Data_BattleGear', grow, sc, indent=1))
        c_ab = _col(book, 'Data_BattleGear', 'AbilityType')
        if c_ab is None:
            continue
        af = Field('Grants ability', 'Data_BattleGear', grow, c_ab, indent=1)
        stats, arow = _ability_block(book, book.value('Data_BattleGear', grow, c_ab),
                                     indent=2)
        if arow is not None:
            af.link = ('Data_Abilities', arow)
        out.append(af)
        out.extend(stats)
    if not out:
        out.append(Note('No battle gear', ''))
    return out


def _unit_spells(book, sheet, row):
    """Spell1..5, each expanded into its Data_Spells record."""
    out = []
    for slot in range(1, 6):
        c = _col(book, sheet, f'Spell{slot}')
        if c is None:
            continue
        f = Field(f'Spell{slot}', sheet, row, c)
        code = book.value(sheet, row, c)
        srow = _find_row(book, 'Data_Spells', code) \
            if code not in (None, -1) else None
        if srow is not None:
            f.link = ('Data_Spells', srow)
        out.append(f)
        if srow is None:
            continue
        for sub in SPELL_STATS:
            sc = _col(book, 'Data_Spells', sub)
            if sc is not None:
                out.append(Field(sub, 'Data_Spells', srow, sc, indent=1))
    if not out:
        out.append(Note('No spells', ''))
    return out


def _unit_techniques(book, sheet, row):
    """Techniques that name this unit in Unit1..4."""
    code = book.value(sheet, row, 0)
    ts = book.sheets.get('Data_Techniques')
    out = []
    if ts is None or not isinstance(code, int):
        return out
    cols = [(n, _col(book, 'Data_Techniques', n))
            for n in ('Unit1', 'Unit2', 'Unit3', 'Unit4')]
    for i in range(len(ts.rows)):
        slots = [n for n, c in cols
                 if c is not None and book.value('Data_Techniques', i, c) == code]
        if not slots:
            continue
        out.append(Note(record_title(book, 'Data_Techniques', i), ', '.join(slots),
                        link=('Data_Techniques', i)))
        for sub in TECHNIQUE_STATS:
            sc = _col(book, 'Data_Techniques', sub)
            if sc is not None:
                out.append(Field(sub, 'Data_Techniques', i, sc, indent=1))
    if not out:
        out.append(Note('No techniques affect this unit', ''))
    return out


_unit_techniques.consumes = [('Data_Techniques', f'Unit{i}') for i in range(1, 5)]


def _researched_here(book, sheet, row, other, stats, empty):
    """Rows of `other` whose AssociatedBuilding is this building."""
    code = book.value(sheet, row, 0)
    sd = book.sheets.get(other)
    out = []
    if sd is None or not isinstance(code, int):
        return out
    c_at = _col(book, other, 'AssociatedBuilding')
    if c_at is None:
        return out
    for i in range(len(sd.rows)):
        if book.value(other, i, c_at) != code:
            continue
        out.append(Note(record_title(book, other, i), '', link=(other, i)))
        for sub in stats:
            sc = _col(book, other, sub)
            if sc is not None:
                out.append(Field(sub, other, i, sc, indent=1))
    if not out:
        out.append(Note(empty, ''))
    return out


def _building_research(book, sheet, row):
    """Techniques and upgrades researched at this building.

    Both sheets point at the building rather than the other way round, so
    nothing on the building's own row hints that a Tavern researches Darts,
    Drunken Revelry and Fortified Ale. Not to be confused with the
    "Upgrades into" section, which is this building turning into another one.
    """
    out = _researched_here(book, sheet, row, 'Data_Techniques',
                           TECHNIQUE_AT_BUILDING_STATS,
                           'No techniques researched here')
    out += _researched_here(book, sheet, row, 'Data_Upgrades', UPGRADE_STATS,
                            'No upgrades researched here')
    return out


_building_research.consumes = [('Data_Techniques', 'AssociatedBuilding'),
                               ('Data_Upgrades', 'AssociatedBuilding')]


def _building_prereqs(book, sheet, row):
    """What has to exist before this building can be placed.

    Lives in Data_BuildingTechTree, keyed by the building itself, so the generic
    reverse-reference scan could only ever label it with this building's own name.
    """
    code = book.value(sheet, row, 0)
    tree = 'Data_BuildingTechTree'
    sd = book.sheets.get(tree)
    out = []
    if sd is None or not isinstance(code, int):
        return out
    trow = _find_row(book, tree, code)
    if trow is None:
        out.append(Note('Not listed in the building tech tree', ''))
        return out
    for slot in range(1, 5):
        c = _col(book, tree, f'Prerequisite{slot}')
        if c is None:
            continue
        f = Field(f'Prerequisite{slot}', tree, trow, c)
        v = book.value(tree, trow, c)
        brow = _find_row(book, 'Data_Buildings', v) if v not in (None, -1) else None
        if brow is not None:
            f.link = ('Data_Buildings', brow)
        out.append(f)
    if not out:
        out.append(Note('No prerequisites', ''))
    return out


_building_prereqs.consumes = [('Data_BuildingTechTree', 'Type')]


def _weapon_wielders(book, sheet, row):
    """Units that carry this weapon."""
    code = book.value(sheet, row, 0)
    us = book.sheets.get('Data_Units')
    out = []
    if us is None or not isinstance(code, int):
        return out
    cols = [(n, _col(book, 'Data_Units', n)) for n in
            ('MeleeWeapon', 'MissileWeapon', 'PrimaryWeapon', 'SecondaryWeapon')]
    for i in range(len(us.rows)):
        slots = [n for n, c in cols
                 if c is not None and book.value('Data_Units', i, c) == code]
        if slots:
            out.append(Note(record_title(book, 'Data_Units', i),
                            ', '.join(slots), link=('Data_Units', i)))
    if not out:
        out.append(Note('Not carried by any unit', ''))
    return out


_weapon_wielders.consumes = [('Data_Units', n) for n in
                             ('MeleeWeapon', 'MissileWeapon', 'PrimaryWeapon',
                              'SecondaryWeapon')]


PROFILES = {
    'Data_Units': [
        ('Overview', ['Name', 'Type', 'Clan', 'UnitClass', 'ModelType',
                      'PathingCategory', 'UnitPortrait']),
        ('Training cost', ['RiceTrainCost', 'WaterTrainCost', 'YinYangTrainCost',
                           'BuildingRequired1', 'BuildingRequired2',
                           'BuildingRequired3']),
        ('Trained at', _units_trained_at),
        ('Health and stamina', ['MaxHealth', 'InitialHealth', 'MaxHealthRecovery',
                                'HealthRecoveryRate', 'MaxFatigue',
                                'InitialFatigue', 'FatigueRecovery',
                                'StaminaWhenRunning', 'CannotBeHealed',
                                'ImmuneToPoison']),
        ('Armour multipliers', ['AMCutting', 'AMPiercing', 'AMBlunt', 'AMFire',
                                'AMExplosive', 'AMMagical']),
        # Melee and missile come first so the stats hang off the descriptive
        # name; Primary/Secondary usually just repeat one of them, and then read
        # as "Same as MeleeWeapon".
        ('Weapons', [_expand('MeleeWeapon', 'Data_Weapons', WEAPON_STATS),
                     _expand('MissileWeapon', 'Data_Weapons', WEAPON_STATS),
                     _expand('PrimaryWeapon', 'Data_Weapons', WEAPON_STATS),
                     _expand('SecondaryWeapon', 'Data_Weapons', WEAPON_STATS),
                     'MissileWeaponLaunchHeight']),
        ('Combat', ['PrefersMelee', 'AttackCapable', 'Superiority',
                    'MaxUnitsAttacking', 'ImmuneToCharge', 'Bracing',
                    'LOS', 'LOSForestMult', 'AIAttackRange',
                    'EncroachmentRange', 'FightOrFlightRange',
                    'YangScore', 'YinScore', 'DeathYinYangAwarded',
                    'YinYangDamageIncrementor']),
        ('Abilities', _unit_abilities),
        ('Battle gear', _unit_battle_gear),
        ('Spells', _unit_spells),
        ('Techniques', _unit_techniques),
        ('Movement', ['Mount', 'UsePackHorse', 'AscendHillMultiplier',
                      'DescendHillMultiplier', 'DirtSpeedMultiplier',
                      'ForestSpeedMultiplier', 'GrassSpeedMultiplier',
                      'MudSpeedMultiplier', 'RiceSpeedMultiplier',
                      'RockSpeedMultiplier', 'SnowSpeedMultiplier',
                      'WaterSpeedMultiplier']),
        ('Damage effects', ['DamageEffectCutting', 'DamageEffectPiercing',
                            'DamageEffectBlunt', 'DamageEffectFire',
                            'DamageEffectExplosive', 'DamageEffectMagical',
                            'UnitExplodeEffect']),
    ],
    'Data_Buildings': [
        ('Overview', ['Name', 'Type', 'Clan', 'ModelType', 'TechLevel',
                      'WotWTechLevel', 'AIBuildingClass', 'BuildingPortrait']),
        ('Build cost', ['RiceCost', 'WaterCost', 'BuildTime', 'RiceRefund',
                        'WaterRefund', 'CanOnlyHaveOne']),
        ('Defence', ['MaxHealth', 'Flammability', 'MaxFireDamagePerSec',
                     'FireExtinguishPoint', 'FireConsumePoint', 'LOS',
                     'AMCutting', 'AMPiercing', 'AMBlunt', 'AMFire',
                     'AMExplosive', 'AMMagical', 'Destroyable']),
        ('Requires', _building_prereqs),
        ('Trains', _building_training),
        ('Training cost', ['RiceTrainCost', 'WaterTrainCost']),
        ('Researched here', _building_research),
        # Named "into" on purpose: this is the building turning into another
        # building, not the techniques and upgrades you research at it. Those
        # are in "Researched here" above.
        ('Upgrades into another building',
         ['UpgradeToType', 'UpgradeToRate', 'UpgradeRiceCost',
                         'UpgradeWaterCost', 'UpgradeRiceRefund',
                         'UpgradeWaterRefund', 'UnlocksBuildingType',
                         'NumOfBuildingsUnlocked']),
        ('Docking', ['UnitToDock', 'DockingUnitCount', 'DockedAbility',
                     'DockingTrainingTime', 'DockingUnitToSpawn']),
        ('AI', ['AIOffensiveScore', 'AIDefensiveScore', 'AIMaxDefault',
                'AIMustHaveFirstPass', 'AIBuildingPriority',
                'YinScore', 'YangScore']),
    ],
    'Data_Weapons': [
        ('Overview', ['Type', 'ActualWeapon', 'Class', 'DamageClass',
                      'WeaponImpactType', 'IsFireWeapon']),
        ('Damage', ['BaseDamage', 'FirePointDamage', 'StaminaDamage',
                    'PoisonDamage', 'PoisonTime', 'AreaOfEffect', 'SiegeMult',
                    'RiderPercentage', 'NoFalloff', 'AffectsFriendlies']),
        ('Vampirism', ['HealthVampirePercentage', 'StaminaVampirePercentage',
                       'HealsWielder', 'YinPerHit', 'YangPerHit']),
        ('Range', ['MinRange', 'MaxRange', 'MaxMountedRange', 'Recovery',
                   'OpportunityFire', 'AssociatedProjectile']),
        ('Height', ['HeightDifferential', 'UpMultiplier', 'DownMultiplier']),
        ('Watchtower', ['WatchtowerCapable', 'WatchtowerMinRange',
                        'WatchtowerMaxRange']),
        ('Carried by', _weapon_wielders),
    ],
}


# -------------------------------------------------------------------- builder
def _reverse_refs(book):
    """{enum name -> [(sheet, col)]} for every column that references it."""
    cache = getattr(book, '_detail_revrefs', None)
    if cache is not None:
        return cache
    out = {}
    for name in book.sheet_order:
        if name.startswith('Enum_'):
            continue
        sd = book.sheets[name]
        for c, e in sd.col_enum.items():
            if e and e != '@bool':
                out.setdefault(e, []).append((name, c))
    book._detail_revrefs = out
    return out


def _referenced_by(book, sheet, row, skip_sheets=(), skip_pairs=()):
    """Rows elsewhere that point at this record.

    `skip_pairs` holds the (sheet, column) joins a curated section already laid
    out properly. Without it the same rows appear twice, and the second copy is
    the useless one: a join sheet such as Data_UnitAndInnateAbilities is titled
    by its first column, so the Samurai's ability row would read "UNIT_D_SAMURAI"
    rather than naming the ability. The skip is per column, not per sheet, so
    other references into the same sheet - Data_Buildings.UnitIn, UnitToDock -
    are still listed.
    """
    sd = book.sheets[sheet]
    code = book.value(sheet, row, 0)
    items = []
    if not sd.self_enum or not isinstance(code, int):
        return items
    for other, col in _reverse_refs(book).get(sd.self_enum, []):
        if other == sheet and col == 0:
            continue          # the record's own key column
        if other in skip_sheets or (other, col) in skip_pairs:
            continue
        osd = book.sheets[other]
        hits = [i for i in range(len(osd.rows))
                if book.value(other, i, col) == code]
        for i in hits[:40]:
            items.append(Note(f'{other}.{osd.headers[col]}',
                              record_title(book, other, i),
                              link=(other, i)))
        if len(hits) > 40:
            items.append(Note(f'{other}.{osd.headers[col]}',
                              f'... and {len(hits) - 40} more rows'))
    if not items:
        items.append(Note('Nothing references this record', ''))
    return items


def build_sections(book, sheet, row):
    """The whole page for one record, as a list of Section."""
    sd = book.sheets[sheet]
    ncols = len(sd.headers)
    used = set()
    sections = []
    expanded_sheets = set()
    # (target sheet, row) -> the column that already expanded it. Units routinely
    # name the same weapon twice - PrimaryWeapon and MissileWeapon both point at
    # the bow - and printing its stats a second time is just noise.
    expanded = {}
    # (sheet, col) joins a curated section has already listed, so "Referenced by"
    # does not print them a second time under a worse label.
    consumed = set()

    def field(name, indent=0):
        c = _col(book, sheet, name)
        if c is None or c >= ncols:
            return None
        used.add(c)
        return Field(name, sheet, row, c, indent=indent)

    for title, spec in PROFILES.get(sheet, []):
        items = []
        if callable(spec):
            items = spec(book, sheet, row)
            # whatever the callable laid out itself must not be repeated under
            # "Other fields"
            for it in items:
                if isinstance(it, Field) and it.sheet == sheet and it.row == row:
                    used.add(it.col)
            for other, header in getattr(spec, 'consumes', ()):
                oc = _col(book, other, header)
                if oc is not None:
                    consumed.add((other, oc))
        else:
            for entry in spec:
                if isinstance(entry, str):
                    f = field(entry)
                    if f is not None:
                        items.append(f)
                    continue
                # ('expand', col, target_sheet, subcols)
                _kind, colname, target, subcols = entry
                f = field(colname)
                if f is None:
                    continue
                code = book.value(sheet, row, f.col)
                trow = _find_row(book, target, code) if code not in (None, -1) else None
                if trow is not None:
                    f.link = (target, trow)
                    expanded_sheets.add(target)
                items.append(f)
                if trow is None:
                    continue
                already = expanded.get((target, trow))
                if already is not None:
                    items.append(Note(f'Same as {already}', '', indent=1,
                                      link=(target, trow)))
                    continue
                expanded[(target, trow)] = colname
                for sub in subcols:
                    sc = _col(book, target, sub)
                    if sc is not None:
                        items.append(Field(sub, target, trow, sc, indent=1))
        if items:
            sections.append(Section(title, items))

    # every column the profile did not mention, in sheet order
    rest = []
    for c in range(ncols):
        if c in used or not sd.headers[c]:
            continue
        f = Field(sd.headers[c], sheet, row, c)
        tbl = book.enum_for(sheet, c)
        if tbl and tbl.name != '@bool':
            target = book.data_sheet_for_enum(tbl.name)
            v = book.value(sheet, row, c)
            trow = _find_row(book, target, v) if target and v not in (None, -1) else None
            if trow is not None:
                f.link = (target, trow)
        rest.append(f)
    if rest:
        sections.append(Section('Other fields' if sheet in PROFILES
                                else 'Fields', rest))

    sections.append(Section('Referenced by',
                            _referenced_by(book, sheet, row, expanded_sheets,
                                           consumed)))
    return sections


# ---------------------------------------------------------------- search index
class RecordIndex:
    """Searchable list of every record in every data sheet.

    Ranking matters more than it looks. Typing "samurai" matches 45 records, most
    of them particle effects and sound events whose name happens to start with the
    word, so a plain "starts with wins" order buries the Dragon Samurai unit that
    the user was obviously after. Matches are therefore ordered by how the text
    matched first, and by how likely the sheet is to be what someone means second.
    """

    # Lower sorts first when two records matched equally well.
    SHEET_RANK = {'Data_Units': 0, 'Data_Buildings': 1, 'Data_Weapons': 2,
                  'Data_Abilities': 3, 'Data_BattleGear': 3, 'Data_Techniques': 3,
                  'Data_Upgrades': 3, 'Data_Spells': 3, 'Data_Projectiles': 4,
                  'Data_Objects': 4, 'Data_Clans': 4}
    OTHER_RANK = 5

    def __init__(self, book):
        self.book = book
        self.entries = []          # (sheet, row, title, haystack, sheet_rank)
        for name in book.sheet_order:
            if name.startswith('Enum_'):
                continue
            sd = book.sheets[name]
            if not sd.headers:
                continue
            has_name = len(sd.headers) > 1 and sd.headers[1].lower() == 'name'
            tbl = book.enums.get(sd.self_enum) if sd.self_enum else None
            rank = self.SHEET_RANK.get(name, self.OTHER_RANK)
            for i in range(len(sd.rows)):
                code = book.value(name, i, 0)
                nm = str(book.value(name, i, 1) or '') if has_name else ''
                desc = tbl.code2desc.get(code, '') if tbl and isinstance(code, int) else ''
                if not nm and not desc:
                    continue
                title = f'{nm} - {desc}' if nm and desc else (nm or desc)
                self.entries.append(
                    (name, i, title, f'{nm}\n{desc}\n{name}'.lower(), rank))

    @staticmethod
    def _bucket(needle, haystack):
        """0 exact, 1 starts a word, 2 anywhere, or None when it does not match."""
        best = None
        for part in haystack.split('\n'):
            if needle not in part:
                continue
            if part == needle:
                return 0
            # a word inside the name starting with the needle, so "samurai"
            # ranks "Dragon Samurai" as highly as "Samurai Death"
            words = part.replace('_', ' ').replace('-', ' ').split()
            b = 1 if any(w.startswith(needle) for w in words) else 2
            if best is None or b < best:
                best = b
        return best

    def search(self, text, limit=MAX_RESULTS):
        """Matches, best first: how the text matched, then how likely the sheet."""
        n = text.strip().lower()
        if not n:
            return []
        scored = []
        for e in self.entries:
            b = self._bucket(n, e[3])
            if b is not None:
                scored.append((b, e[4], len(e[2]), e))
        scored.sort(key=lambda x: x[:3])
        return [x[3] for x in scored[:limit]]


# ---------------------------------------------------------------------- model
class DetailModel(QAbstractTableModel):
    """Flat list of section headers and fields. The value column is editable."""

    HEADERS = ['Field', 'Value']

    def __init__(self, book, push_edit, parent=None):
        super().__init__(parent)
        self.book = book
        self.push_edit = push_edit          # (sheet, row, col, value) -> None
        self.rows = []                      # Section | Field | Note
        self.sheet = None
        self.row = None

    def set_record(self, sheet, row):
        self.beginResetModel()
        self.sheet, self.row = sheet, row
        self.rows = []
        for sec in build_sections(self.book, sheet, row):
            self.rows.append(sec)
            self.rows.extend(sec.items)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.sheet = self.row = None
        self.rows = []
        self.endResetModel()

    def refresh(self):
        """Re-read every value after an edit made elsewhere."""
        if self.sheet is None:
            return
        top = self.index(0, 0)
        bottom = self.index(max(len(self.rows) - 1, 0), 1)
        self.dataChanged.emit(top, bottom)

    def item(self, row):
        return self.rows[row] if 0 <= row < len(self.rows) else None

    # ------------------------------------------------------------ Qt overrides
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 2

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if o == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[s]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        it = self.rows[index.row()]
        c = index.column()

        if isinstance(it, Section):
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

        if isinstance(it, Note):
            if role == Qt.ItemDataRole.DisplayRole:
                return ('    ' * it.indent + it.label) if c == 0 else str(it.value)
            if role == Qt.ItemDataRole.ForegroundRole:
                if it.link:
                    return QBrush(LINK_FG)
                return QBrush(MUTED_FG)
            if role == Qt.ItemDataRole.ToolTipRole and it.link:
                return 'Double-click to open this record'
            return None

        # Field
        if role == Qt.ItemDataRole.DisplayRole:
            if c == 0:
                return '    ' * it.indent + it.label
            return _text(self.book, it.sheet, it.row, it.col)
        if role == Qt.ItemDataRole.EditRole and c == 1:
            v = self.book.value(it.sheet, it.row, it.col)
            return '' if v is None else v
        if role == Qt.ItemDataRole.BackgroundRole:
            if (it.sheet, it.row, it.col) in self.book.edits:
                return QBrush(EDITED_BG)
        if role == Qt.ItemDataRole.ForegroundRole and c == 0 and it.link:
            return QBrush(LINK_FG)
        if role == Qt.ItemDataRole.ToolTipRole:
            lines = [f'{it.sheet}.{_header(self.book, it.sheet, it.col)}'
                     f'  (row {it.row + 2})']
            if it.sheet != self.sheet:
                lines.append('Lives on a referenced record - editing it here '
                             'changes that record.')
            tbl = self.book.enum_for(it.sheet, it.col)
            if tbl:
                lines.append(f'Enum_{tbl.name}')
            key = (it.sheet, it.row, it.col)
            if key in self.book.edits:
                lines.append(f'Original: {self.book.original.get(key)}')
            if it.link:
                lines.append('Double-click the field name to open the record '
                             'it points at.')
            return '\n'.join(lines)
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        it = self.rows[index.row()]
        if isinstance(it, Section):
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if isinstance(it, Field) and index.column() == 1:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        it = self.rows[index.row()]
        if not isinstance(it, Field) or index.column() != 1:
            return False
        self.push_edit(it.sheet, it.row, it.col, value)
        return True


class DetailDelegate(QStyledItemDelegate):
    """Same editing experience as the grid: a searchable dropdown for enums."""

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book

    def _field(self, index):
        it = index.model().item(index.row())
        return it if isinstance(it, Field) else None

    def createEditor(self, parent, option, index):
        it = self._field(index)
        tbl = self.book.enum_for(it.sheet, it.col) if it else None
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


# --------------------------------------------------------------------- window
class DetailWindow(QDialog):
    """Search on the left, the selected record's stats on the right."""

    jumpRequested = pyqtSignal(str, int, int)              # sheet, row, col
    editRequested = pyqtSignal(str, int, int, object)      # sheet, row, col, value

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book
        self.index = RecordIndex(book)
        self._history = []
        self._current = None

        self.setWindowTitle('View details')
        self.resize(1080, 720)
        self.setSizeGripEnabled(True)

        # ---- left: search
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)
        self.ed = QLineEdit()
        self.ed.setPlaceholderText('Type a unit or building name...')
        self.ed.setClearButtonEnabled(True)
        self.ed.textChanged.connect(self._search)
        lv.addWidget(self.ed)
        self.lst = QListWidget()
        self.lst.currentItemChanged.connect(self._on_pick)
        lv.addWidget(self.lst, 1)
        self.lbl_hits = QLabel('')
        self.lbl_hits.setStyleSheet('color:#5a6b85;')
        lv.addWidget(self.lbl_hits)

        # ---- right: detail
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)

        bar = QHBoxLayout()
        self.b_back = QPushButton('< Back')
        self.b_back.setEnabled(False)
        self.b_back.clicked.connect(self._go_back)
        bar.addWidget(self.b_back)
        self.lbl_title = QLabel('Pick a record on the left')
        f = QFont()
        f.setBold(True)
        f.setPointSize(11)
        self.lbl_title.setFont(f)
        bar.addWidget(self.lbl_title, 1)
        self.b_grid = QPushButton('Show in grid')
        self.b_grid.setEnabled(False)
        self.b_grid.clicked.connect(self._show_in_grid)
        bar.addWidget(self.b_grid)
        rv.addLayout(bar)

        self.model = DetailModel(book, self._push_edit, self)
        self.tbl = QTableView()
        self.tbl.setModel(self.model)
        self.tbl.setItemDelegate(DetailDelegate(book, self.tbl))
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                 | QAbstractItemView.EditTrigger.SelectedClicked
                                 | QAbstractItemView.EditTrigger.EditKeyPressed
                                 | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(22)
        self.tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)
        self.tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnWidth(0, 320)
        self.tbl.doubleClicked.connect(self._on_double_click)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._on_context_menu)
        rv.addWidget(self.tbl, 1)

        self.lbl_hint = QLabel(
            'Edit a value here and it changes the file exactly as an edit in the '
            'grid does - Ctrl+Z and Ctrl+S in the main window still apply.')
        self.lbl_hint.setStyleSheet('color:#5a6b85;')
        self.lbl_hint.setWordWrap(True)
        rv.addWidget(self.lbl_hint)

        sp = QSplitter()
        sp.addWidget(left)
        sp.addWidget(right)
        sp.setStretchFactor(0, 0)
        sp.setStretchFactor(1, 1)
        sp.setSizes([330, 750])

        v = QVBoxLayout(self)
        v.addWidget(sp)

        self.ed.setFocus()

    # ------------------------------------------------------------ searching
    def _search(self, text):
        self.lst.blockSignals(True)
        self.lst.clear()
        hits = self.index.search(text)
        for sheet, row, title, _hay, _rank in hits:
            it = QListWidgetItem(f'{title}\n{sheet}')
            it.setData(Qt.ItemDataRole.UserRole, (sheet, row))
            self.lst.addItem(it)
        self.lst.blockSignals(False)
        if not text.strip():
            self.lbl_hits.setText('')
        elif not hits:
            self.lbl_hits.setText('No record matches that name.')
        else:
            more = ' (showing the first %d)' % MAX_RESULTS \
                if len(hits) >= MAX_RESULTS else ''
            self.lbl_hits.setText(f'{len(hits)} matches{more}')
        if len(hits) == 1:
            self.lst.setCurrentRow(0)

    def _on_pick(self, cur, _prev):
        if cur is None:
            return
        sheet, row = cur.data(Qt.ItemDataRole.UserRole)
        self.show_record(sheet, row)

    # ------------------------------------------------------------ navigation
    def show_record(self, sheet, row, remember=True):
        if sheet not in self.book.sheets:
            return
        if remember and self._current and self._current != (sheet, row):
            self._history.append(self._current)
            self.b_back.setEnabled(True)
        self._current = (sheet, row)
        self.model.set_record(sheet, row)
        self.lbl_title.setText(
            f'{record_title(self.book, sheet, row)}   -   {sheet}, row {row + 2}')
        self.b_grid.setEnabled(True)
        self.tbl.scrollToTop()

    def _go_back(self):
        if not self._history:
            return
        sheet, row = self._history.pop()
        self.b_back.setEnabled(bool(self._history))
        self.show_record(sheet, row, remember=False)

    def _on_double_click(self, index):
        if index.column() != 0:
            return
        it = self.model.item(index.row())
        if it is not None and getattr(it, 'link', None):
            self.show_record(*it.link)

    def _show_in_grid(self):
        if self._current:
            self.jumpRequested.emit(self._current[0], self._current[1], 0)

    def _on_context_menu(self, pos):
        idx = self.tbl.indexAt(pos)
        it = self.model.item(idx.row()) if idx.isValid() else None
        if it is None or isinstance(it, Section):
            return
        m = QMenu(self)
        if getattr(it, 'link', None):
            a = m.addAction('Open this record')
            a.triggered.connect(lambda: self.show_record(*it.link))
        if isinstance(it, Field):
            a2 = m.addAction(f'Show in grid ({it.sheet})')
            a2.triggered.connect(
                lambda: self.jumpRequested.emit(it.sheet, it.row, it.col))
        if not m.isEmpty():
            m.exec(self.tbl.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ editing
    def _push_edit(self, sheet, row, col, value):
        self.editRequested.emit(sheet, row, col, value)

    def refresh(self):
        """Called by the main window whenever a cell changes anywhere."""
        self.model.refresh()
