"""
brde.matchup - unit versus unit comparison.

Answers the question the grid cannot: put two units side by side and say which
one beats which, and why.

The "why" is one rule. A weapon carries a `DamageClass`, and a unit carries six
armour multipliers, `AMCutting` through `AMMagical`, one per damage class. The
multiplier scales the damage that class does to that unit, so it reads the
opposite way round to armour in most games: `AMPiercing = 4.0` means the unit
takes FOUR TIMES piercing damage, and `0.25` means it takes a quarter. Damage
landed is therefore

    weapon BaseDamage  x  target's AM for that weapon's damage class

which is what makes the Dragon Spearman (`AMPiercing` 4.0) melt under archer
fire while the Dragon Samurai (`AMCutting` 0.25) shrugs off swords.

Health, armour and weapon damage all move once techniques are researched, so a
comparison of the raw sheet values describes units nobody ever fields. Every
figure here can therefore be shown twice, before and after the techniques that
name the unit - see `apply_techniques`.

This module holds no Qt at all, the way `brde/schema.py` does not - it is plain
computation over a `BRWorkbook`, down to and including the page layout that
`build_rows` returns. The window that draws it lives in `brde/matchup_ui.py`.
Keeping the split means the game rules above can be tested without a display,
which is the whole point: the arithmetic is the part worth being sure about.
"""
from __future__ import annotations

import math

# Damage class -> the armour column that scales it, in the order they are shown.
# Keyed by enum description rather than by code: a mod is free to renumber
# Enum_DamageClassType, and the descriptions are what the game reads.
DAMAGE_CLASSES = [
    ('DAMAGECLASS_CUTTING', 'AMCutting', 'Cutting'),
    ('DAMAGECLASS_PIERCING', 'AMPiercing', 'Piercing'),
    ('DAMAGECLASS_BLUNT', 'AMBlunt', 'Blunt'),
    ('DAMAGECLASS_FIRE', 'AMFire', 'Fire'),
    ('DAMAGECLASS_EXPLOSIVE', 'AMExplosive', 'Explosive'),
    ('DAMAGECLASS_MAGICAL', 'AMMagical', 'Magical'),
]

ARMOUR_COLUMNS = [am for _dc, am, _lab in DAMAGE_CLASSES]

# Technique effect -> the armour column it multiplies. The effect names do not
# match the column names: the sheet calls cutting "SLASH" and magical "MAGIC".
TE_ARMOUR = {
    'TE_AC_MULT_SLASH': 'AMCutting',
    'TE_AC_MULT_PIERCE': 'AMPiercing',
    'TE_AC_MULT_BLUNT': 'AMBlunt',
    'TE_AC_MULT_FIRE': 'AMFire',
    'TE_AC_MULT_EXPLOSIVE': 'AMExplosive',
    'TE_AC_MULT_MAGIC': 'AMMagical',
}

TE_MAX_HP = 'TE_UNIT_MULT_MAX_HP'
TE_DAMAGE = 'TE_WP_MULT_DAMAGE'

# The four columns naming a weapon, and the label each one gets on the page.
WEAPON_SLOTS = [('MeleeWeapon', 'Melee'), ('MissileWeapon', 'Missile'),
                ('PrimaryWeapon', 'Primary'), ('SecondaryWeapon', 'Secondary')]

# Enum_WeaponSlotType codes, used by Data_Techniques.WeaponSlotAffected1 to say
# which weapon a damage bonus applies to. WEAPONSLOT_INVALID (-1) is treated as
# "both": TECHNIQUE_KING_OF_THE_HILL raises damage with the slot left at -1, so
# reading it strictly would silently drop the bonus.
SLOT_BOTH, SLOT_PRIMARY, SLOT_SECONDARY = 0, 1, 2

UNIT_SHEET = 'Data_Units'
WEAPON_SHEET = 'Data_Weapons'
TECHNIQUE_SHEET = 'Data_Techniques'


# --------------------------------------------------------------------- helpers
def _col(book, sheet, name):
    """Column index by header name, or None when the sheet has no such column."""
    sd = book.sheets.get(sheet)
    if sd is None:
        return None
    try:
        return sd.headers.index(name)
    except ValueError:
        return None


def _val(book, sheet, row, name, default=None):
    c = _col(book, sheet, name)
    if c is None:
        return default
    v = book.value(sheet, row, c)
    return default if v is None else v


def _num(book, sheet, row, name, default=0.0):
    v = _val(book, sheet, row, name, None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return float(v)


def _find_row(book, sheet, code):
    """Row index whose key column equals `code`, or None."""
    sd = book.sheets.get(sheet)
    if sd is None or not isinstance(code, int):
        return None
    for i in range(len(sd.rows)):
        if book.value(sheet, i, 0) == code:
            return i
    return None


def _label(book, enum_name, code, default=''):
    tbl = book.enums.get(enum_name)
    if tbl is None or not isinstance(code, int):
        return default
    return tbl.code2desc.get(code, default)


def fmt(v, places=2):
    """A number as a person would write it: 1.2999999523 -> '1.3', 450.0 -> '450'."""
    if v is None:
        return ''
    if isinstance(v, str):
        return v
    r = round(float(v), places)
    if r == int(r):
        return str(int(r))
    return f'{r:g}'


def _mult(v):
    """A multiplier, always signed so it reads as one: 'x1.4'."""
    return 'x' + fmt(v)


def _hits(n):
    """'1 hit' / '3 hits'."""
    return f'{n} hit' if n == 1 else f'{n} hits'


# ------------------------------------------------------------------- the units
def unit_list(book):
    """[(row, name, clan label)] for every named unit, grouped by clan.

    Only rows with a Name are offered: Data_Units carries 999 rows of which 155
    are real units, and the rest would be blank lines in the picker.
    """
    sd = book.sheets.get(UNIT_SHEET)
    if sd is None:
        return []
    c_name = _col(book, UNIT_SHEET, 'Name')
    c_clan = _col(book, UNIT_SHEET, 'Clan')
    if c_name is None:
        return []
    out = []
    for i in range(len(sd.rows)):
        name = book.value(UNIT_SHEET, i, c_name)
        if name is None or not str(name).strip():
            continue
        clan = book.value(UNIT_SHEET, i, c_clan) if c_clan is not None else None
        out.append((i, str(name).strip(), _label(book, 'ClanType', clan, '')))
    out.sort(key=lambda e: (e[2], e[1]))
    return out


class Attack:
    """One weapon a unit carries, with the damage it actually deals."""

    __slots__ = ('slots', 'name', 'code', 'row', 'damage_class', 'raw_class',
                 'class_label', 'base_damage', 'damage', 'min_range',
                 'max_range', 'area', 'siege', 'rider', 'stamina', 'poison',
                 'weapon_class')

    def __init__(self, code, row, name):
        self.slots = []
        self.name = name
        self.code = code
        self.row = row
        self.damage_class = None
        self.raw_class = ''
        self.class_label = ''
        self.base_damage = 0.0
        self.damage = 0.0
        self.min_range = 0.0
        self.max_range = 0.0
        self.area = 0.0
        self.siege = 0.0
        self.rider = 0.0
        self.stamina = 0.0
        self.poison = 0.0
        self.weapon_class = ''

    @property
    def armour_column(self):
        """The AM column a target uses against this weapon, or None."""
        for dc, am, _lab in DAMAGE_CLASSES:
            if dc == self.raw_class:
                return am
        return None

    @property
    def title(self):
        slots = '/'.join(self.slots)
        return f'{self.name} ({slots})' if slots else self.name


class UnitStats:
    """Everything the comparison needs about one unit."""

    __slots__ = ('book', 'row', 'code', 'name', 'clan', 'unit_class', 'can_mount',
                 'rice', 'water', 'yinyang', 'base_health', 'health',
                 'base_armour', 'armour', 'attacks', 'techniques', 'upgraded')

    @property
    def title(self):
        return self.name or f'{UNIT_SHEET} row {self.row + 2}'

    def armour_against(self, attack):
        """This unit's multiplier against `attack`, or None if it has no class."""
        col = attack.armour_column
        return None if col is None else self.armour.get(col)


class Technique:
    """A researched technique and what it does to the unit, in words."""

    __slots__ = ('name', 'row', 'effects')

    def __init__(self, name, row, effects):
        self.name = name
        self.row = row
        self.effects = effects          # ['Max health x1.4', ...]

    @property
    def summary(self):
        return ', '.join(self.effects)


def _weapon(book, code, wanted_dc):
    """Load one Data_Weapons record. `wanted_dc` is {code -> description}."""
    wrow = _find_row(book, WEAPON_SHEET, code)
    if wrow is None:
        return None
    name = _val(book, WEAPON_SHEET, wrow, 'ActualWeapon', '') \
        or _label(book, 'WeaponType', code, f'weapon {code}')
    a = Attack(code, wrow, str(name))
    dc = _val(book, WEAPON_SHEET, wrow, 'DamageClass', None)
    a.damage_class = dc if isinstance(dc, int) else None
    a.raw_class = wanted_dc.get(a.damage_class, '')
    a.class_label = next((lab for raw, _am, lab in DAMAGE_CLASSES
                          if raw == a.raw_class), a.raw_class or 'none')
    a.base_damage = _num(book, WEAPON_SHEET, wrow, 'BaseDamage')
    a.damage = a.base_damage
    a.min_range = _num(book, WEAPON_SHEET, wrow, 'MinRange')
    a.max_range = _num(book, WEAPON_SHEET, wrow, 'MaxRange')
    a.area = _num(book, WEAPON_SHEET, wrow, 'AreaOfEffect')
    a.siege = _num(book, WEAPON_SHEET, wrow, 'SiegeMult')
    a.rider = _num(book, WEAPON_SHEET, wrow, 'RiderPercentage')
    a.stamina = _num(book, WEAPON_SHEET, wrow, 'StaminaDamage')
    a.poison = _num(book, WEAPON_SHEET, wrow, 'PoisonDamage')
    a.weapon_class = _label(book, 'WeaponClassType',
                            _val(book, WEAPON_SHEET, wrow, 'Class', None), '')
    return a


def unit_stats(book, row, with_techniques=True):
    """Read one unit, optionally with every technique that affects it applied."""
    u = UnitStats()
    u.book = book
    u.row = row
    u.code = book.value(UNIT_SHEET, row, 0)
    u.name = str(_val(book, UNIT_SHEET, row, 'Name', '') or '').strip()
    u.clan = _label(book, 'ClanType', _val(book, UNIT_SHEET, row, 'Clan', None), '')
    u.unit_class = _label(book, 'UnitClassType',
                          _val(book, UNIT_SHEET, row, 'UnitClass', None), '')
    # Mount names the horse the unit may ride, not a horse it is already on:
    # 55 of the 155 units carry UNIT_U_TRAINEDHORSE here. It is worth showing
    # because a weapon's RiderPercentage only applies once a target is mounted.
    u.can_mount = _val(book, UNIT_SHEET, row, 'Mount', -1) not in (None, -1)
    u.rice = _num(book, UNIT_SHEET, row, 'RiceTrainCost')
    u.water = _num(book, UNIT_SHEET, row, 'WaterTrainCost')
    u.yinyang = _num(book, UNIT_SHEET, row, 'YinYangTrainCost')
    u.base_health = _num(book, UNIT_SHEET, row, 'MaxHealth')
    u.health = u.base_health
    u.base_armour = {am: _num(book, UNIT_SHEET, row, am, 1.0)
                     for am in ARMOUR_COLUMNS}
    u.armour = dict(u.base_armour)
    u.techniques = []
    u.upgraded = False

    # One Attack per distinct weapon, remembering every slot it fills. Units
    # routinely name the same weapon twice - a Samurai's katana is both its
    # melee and its secondary weapon - and listing it twice says nothing.
    dc_tbl = book.enums.get('DamageClassType')
    dc_names = dict(dc_tbl.code2desc) if dc_tbl is not None else {}
    by_code = {}
    u.attacks = []
    for column, label in WEAPON_SLOTS:
        code = _val(book, UNIT_SHEET, row, column, None)
        if not isinstance(code, int) or code < 0:
            continue
        if code in by_code:
            by_code[code].slots.append(label)
            continue
        a = _weapon(book, code, dc_names)
        if a is None:
            continue
        a.slots.append(label)
        by_code[code] = a
        u.attacks.append(a)

    if with_techniques:
        apply_techniques(book, u)
    return u


def _slot_codes(book, row):
    """(primary weapon code, secondary weapon code) for one unit."""
    return (_val(book, UNIT_SHEET, row, 'PrimaryWeapon', None),
            _val(book, UNIT_SHEET, row, 'SecondaryWeapon', None))


def techniques_for(book, row):
    """Rows of Data_Techniques that affect the unit at `row`.

    A technique reaches a unit two ways: by naming it in Unit1..4, or by
    AffectEntireClan matching the unit's clan. Only two vanilla techniques use
    the clan-wide form - Meditation and Herbalists, the healing rate ones - and
    they name no unit at all, so missing that case would drop them entirely.

    Techniques with no AssociatedBuilding are skipped, because nothing in the
    game can research them. In the vanilla file that rule picks out exactly the
    ten TECHNIQUE_RESERVED_00..09 placeholder rows and nothing else, which
    matters: every one of them multiplies the Dragon Archer's damage by 1.4, so
    stacking them turns an 18 damage arrow into 730 and every archer matchup
    into nonsense. Reading the name would work as well, but a building is a fact
    about the data rather than a guess about a naming convention, and a mod that
    fills one of these rows in gets it counted the moment it becomes buildable.
    """
    sd = book.sheets.get(TECHNIQUE_SHEET)
    code = book.value(UNIT_SHEET, row, 0)
    if sd is None or not isinstance(code, int):
        return []
    clan = _val(book, UNIT_SHEET, row, 'Clan', None)
    unit_cols = [_col(book, TECHNIQUE_SHEET, f'Unit{i}') for i in range(1, 5)]
    c_clan = _col(book, TECHNIQUE_SHEET, 'AffectEntireClan')
    c_bldg = _col(book, TECHNIQUE_SHEET, 'AssociatedBuilding')
    out = []
    for i in range(len(sd.rows)):
        if c_bldg is not None and \
                book.value(TECHNIQUE_SHEET, i, c_bldg) in (None, -1):
            continue
        named = any(c is not None and book.value(TECHNIQUE_SHEET, i, c) == code
                    for c in unit_cols)
        clanwide = (c_clan is not None and isinstance(clan, int) and clan >= 0
                    and book.value(TECHNIQUE_SHEET, i, c_clan) == clan)
        if named or clanwide:
            out.append(i)
    return out


def apply_techniques(book, u: UnitStats):
    """Multiply health, armour and weapon damage by every technique that applies.

    Effects are looked up by name in Enum_TechniqueEffectType rather than by
    code, so renumbering that table in a mod does not quietly turn a health
    bonus into an armour one.
    """
    effect_name = {}
    tbl = book.enums.get('TechniqueEffectType')
    if tbl is not None:
        effect_name = dict(tbl.code2desc)
    primary, secondary = _slot_codes(book, u.row)

    for trow in techniques_for(book, u.row):
        name = _label(book, 'TechniqueType',
                      book.value(TECHNIQUE_SHEET, trow, 0), f'row {trow + 2}')
        slot = _val(book, TECHNIQUE_SHEET, trow, 'WeaponSlotAffected1', SLOT_BOTH)
        notes = []
        for i in range(1, 5):
            code = _val(book, TECHNIQUE_SHEET, trow, f'Effect{i}', None)
            if not isinstance(code, int) or code < 0:
                continue
            eff = effect_name.get(code, '')
            param = _num(book, TECHNIQUE_SHEET, trow, f'FloatParam{i}', 0.0)
            if eff == TE_MAX_HP and param > 0:
                u.health *= param
                notes.append(f'Max health {_mult(param)}')
            elif eff in TE_ARMOUR and param > 0:
                col = TE_ARMOUR[eff]
                u.armour[col] *= param
                notes.append(f'{col[2:]} armour {_mult(param)}')
            elif eff == TE_DAMAGE and param > 0:
                hit = _apply_damage(u, param, slot, primary, secondary)
                if hit:
                    notes.append(f'{", ".join(hit)} damage {_mult(param)}')
        if notes:
            u.techniques.append(Technique(name, trow, notes))
            u.upgraded = True
    return u


def _apply_damage(u: UnitStats, param, slot, primary, secondary):
    """Scale the damage of whichever weapons the technique's slot names."""
    hit = []
    for a in u.attacks:
        if slot == SLOT_PRIMARY and a.code != primary:
            continue
        if slot == SLOT_SECONDARY and a.code != secondary:
            continue
        a.damage *= param
        hit.append(a.name)
    return hit


# ----------------------------------------------------------------- the matchup
# How to read a target's armour multiplier, worst to best for the attacker.
def rate(mult):
    """(rank, wording) for an armour multiplier, from the attacker's side.

    Rank is signed so the view can colour by it: positive means the attack is
    landing well, negative means the target shrugs it off.
    """
    if mult is None:
        return 0, ''
    if mult <= 0:
        return -3, 'immune'
    if mult >= 2:
        return 3, 'hard counter'
    if mult > 1:
        return 2, 'effective'
    if mult == 1:
        return 0, 'neutral'
    if mult <= 0.5:
        return -2, 'heavily resisted'
    return -1, 'resisted'


class Threat:
    """One unit's weapon measured against the other unit's armour."""

    __slots__ = ('attack', 'mult', 'damage', 'hits', 'rank', 'wording')

    def __init__(self, attack, mult, damage, hits, rank, wording):
        self.attack = attack
        self.mult = mult
        self.damage = damage
        self.hits = hits
        self.rank = rank
        self.wording = wording


def threats(attacker: UnitStats, defender: UnitStats):
    """Every weapon `attacker` carries, scored against `defender`'s armour."""
    out = []
    for a in attacker.attacks:
        mult = defender.armour_against(a)
        if mult is None:
            continue
        damage = a.damage * mult
        hits = math.ceil(defender.health / damage) if damage > 0 else None
        rank, wording = rate(mult)
        out.append(Threat(a, mult, damage, hits, rank, wording))
    return out


def best_threat(attacker: UnitStats, defender: UnitStats):
    """The weapon that kills `defender` fastest, or None when it cannot attack."""
    scored = [t for t in threats(attacker, defender) if t.damage > 0]
    if not scored:
        return None
    return max(scored, key=lambda t: t.damage)


class Verdict:
    """Who wins the straight one-on-one, and the sentence explaining it."""

    __slots__ = ('a', 'b', 'best_a', 'best_b', 'winner', 'text')

    def __init__(self, a, b, best_a, best_b, winner, text):
        self.a = a
        self.b = b
        self.best_a = best_a
        self.best_b = best_b
        self.winner = winner          # 'a', 'b' or None
        self.text = text


def verdict(a: UnitStats, b: UnitStats) -> Verdict:
    """Compare hits to kill both ways and put the result into one sentence."""
    ta, tb = best_threat(a, b), best_threat(b, a)

    if ta is None and tb is None:
        return Verdict(a, b, None, None, None,
                       f'Neither {a.title} nor {b.title} can damage the other.')
    if ta is None:
        return Verdict(a, b, None, tb, 'b',
                       f'{a.title} cannot damage {b.title} at all, while '
                       f'{b.title} kills it in {_hits(tb.hits)} with its '
                       f'{tb.attack.name}.')
    if tb is None:
        return Verdict(a, b, ta, None, 'a',
                       f'{b.title} cannot damage {a.title} at all, while '
                       f'{a.title} kills it in {_hits(ta.hits)} with its '
                       f'{ta.attack.name}.')

    winner = None
    if ta.hits < tb.hits:
        winner = 'a'
    elif tb.hits < ta.hits:
        winner = 'b'

    def side(t, atk, dfn):
        return (f'{atk.title} attacks with {t.attack.name}, which is '
                f'{t.attack.class_label.lower()}, and {dfn.title} takes '
                f'{t.attack.class_label.lower()} damage at {_mult(t.mult)} - '
                f'{fmt(t.damage, 1)} a hit, {_hits(t.hits)} to kill')

    if winner is None:
        text = (f'Evenly matched at {_hits(ta.hits)} each way. '
                + side(ta, a, b) + '. ' + side(tb, b, a) + '.')
    else:
        win, lose = (a, b) if winner == 'a' else (b, a)
        tw, tl = (ta, tb) if winner == 'a' else (tb, ta)
        edge = 'counters' if tw.rank > 0 and tw.hits * 2 <= tl.hits else 'beats'
        text = (f'{win.title} {edge} {lose.title}. ' + side(tw, win, lose)
                + '. Back the other way, ' + side(tl, lose, win) + '.')
    return Verdict(a, b, ta, tb, winner, text)


# ------------------------------------------------------------------ page model
class Section:
    __slots__ = ('title',)

    def __init__(self, title):
        self.title = title


class Row:
    """One line of the comparison: a label and the two units' values.

    `rank_a` / `rank_b` are the signed scores from `rate()`, or None. The view
    turns them into a colour; keeping them numbers here is what lets the layout
    be tested without a display.
    """

    __slots__ = ('label', 'a', 'b', 'rank_a', 'rank_b', 'indent', 'better')

    def __init__(self, label, a='', b='', rank_a=None, rank_b=None, indent=0,
                 better=None):
        self.label = label
        self.a = a
        self.b = b
        self.rank_a = rank_a
        self.rank_b = rank_b
        self.indent = indent
        self.better = better          # 'a', 'b' or None - which side to embolden


def _higher(x, y):
    """Which of two numbers is the better one to have. Ties give None."""
    if x is None or y is None or x == y:
        return None
    return 'a' if x > y else 'b'


def _stat(label, va, vb, higher_is_better=True, places=2):
    better = _higher(va, vb)
    if better and not higher_is_better:
        better = 'b' if better == 'a' else 'a'
    return Row(label, fmt(va, places), fmt(vb, places), better=better)


def _upgraded(base, now, places=2):
    """'450' when nothing changed, '450 -> 630' when a technique moved it."""
    if round(base, 4) == round(now, 4):
        return fmt(now, places)
    return f'{fmt(base, places)} -> {fmt(now, places)}'


def build_rows(a: UnitStats, b: UnitStats, v: Verdict):
    """The whole comparison as a flat list of Section and Row."""
    out = [Section('Overview')]
    out.append(Row('Clan', a.clan, b.clan))
    out.append(Row('Unit class', a.unit_class, b.unit_class))
    out.append(Row('Can ride a horse', 'yes' if a.can_mount else 'no',
                   'yes' if b.can_mount else 'no'))
    out.append(_stat('Rice cost', a.rice, b.rice, higher_is_better=False))
    out.append(_stat('Water cost', a.water, b.water, higher_is_better=False))
    if a.yinyang or b.yinyang:
        out.append(_stat('Yin/Yang cost', a.yinyang, b.yinyang,
                         higher_is_better=False))

    out.append(Section('Health'))
    out.append(Row('Max health', _upgraded(a.base_health, a.health),
                   _upgraded(b.base_health, b.health),
                   better=_higher(a.health, b.health)))

    # Armour is the counter table itself, so each side is rated on its own terms
    # rather than only against the other unit: a multiplier above 1 is a
    # weakness whoever is standing opposite.
    out.append(Section('Armour multipliers (higher means more damage taken)'))
    for _dc, am, lab in DAMAGE_CLASSES:
        ra, _wa = rate(a.armour[am])
        rb, _wb = rate(b.armour[am])
        out.append(Row(lab,
                       _upgraded(a.base_armour[am], a.armour[am]),
                       _upgraded(b.base_armour[am], b.armour[am]),
                       # a high multiplier is bad for its owner, so the sign is
                       # flipped from the attacker's reading in rate()
                       rank_a=-ra, rank_b=-rb,
                       better=_higher(b.armour[am], a.armour[am])))

    out.append(Section('Weapons'))
    for i in range(max(len(a.attacks), len(b.attacks))):
        wa = a.attacks[i] if i < len(a.attacks) else None
        wb = b.attacks[i] if i < len(b.attacks) else None
        out.append(Row(f'Weapon {i + 1}',
                       wa.title if wa else '', wb.title if wb else ''))
        out.append(Row('Damage class', wa.class_label if wa else '',
                       wb.class_label if wb else '', indent=1))
        out.append(Row('Damage',
                       _upgraded(wa.base_damage, wa.damage) if wa else '',
                       _upgraded(wb.base_damage, wb.damage) if wb else '',
                       indent=1,
                       better=_higher(wa.damage if wa else None,
                                      wb.damage if wb else None)))
        out.append(Row('Range', f'{fmt(wa.min_range)} - {fmt(wa.max_range)}'
                       if wa else '',
                       f'{fmt(wb.min_range)} - {fmt(wb.max_range)}' if wb else '',
                       indent=1,
                       better=_higher(wa.max_range if wa else None,
                                      wb.max_range if wb else None)))
        if (wa and wa.area) or (wb and wb.area):
            out.append(Row('Area of effect', fmt(wa.area) if wa else '',
                           fmt(wb.area) if wb else '', indent=1))
        if (wa and wa.poison) or (wb and wb.poison):
            out.append(Row('Poison damage', fmt(wa.poison) if wa else '',
                           fmt(wb.poison) if wb else '', indent=1))
        out.append(Row('Vs mounted', _mult(wa.rider) if wa else '',
                       _mult(wb.rider) if wb else '', indent=1))
    if not a.attacks and not b.attacks:
        out.append(Row('No weapons', '', ''))

    # The point of the whole window: each column holds what that unit does TO
    # the other one, so reading down a column tells you how that unit fares.
    out.append(Section('Counter matchup - each column is what that unit does to '
                       'the other'))
    ta, tb = threats(a, b), threats(b, a)
    for i in range(max(len(ta), len(tb))):
        x = ta[i] if i < len(ta) else None
        y = tb[i] if i < len(tb) else None
        out.append(Row(f'Attack {i + 1}',
                       f'{x.attack.name} ({x.attack.class_label})' if x else '',
                       f'{y.attack.name} ({y.attack.class_label})' if y else ''))
        out.append(Row("Target's armour", _mult(x.mult) if x else '',
                       _mult(y.mult) if y else '', indent=1,
                       rank_a=x.rank if x else None,
                       rank_b=y.rank if y else None))
        out.append(Row('Damage landed', fmt(x.damage, 1) if x else '',
                       fmt(y.damage, 1) if y else '', indent=1,
                       better=_higher(x.damage if x else None,
                                      y.damage if y else None)))
        out.append(Row('Hits to kill', str(x.hits) if x and x.hits else '',
                       str(y.hits) if y and y.hits else '', indent=1,
                       rank_a=x.rank if x else None,
                       rank_b=y.rank if y else None,
                       better=_higher(-(x.hits or 0) if x else None,
                                      -(y.hits or 0) if y else None)))
        out.append(Row('Reading', x.wording if x else '',
                       y.wording if y else '', indent=1))
    if not ta and not tb:
        out.append(Row('Neither unit can attack the other', '', ''))

    out.append(Row('Winner',
                   'wins' if v.winner == 'a' else '',
                   'wins' if v.winner == 'b' else '',
                   rank_a=3 if v.winner == 'a' else None,
                   rank_b=3 if v.winner == 'b' else None,
                   better=v.winner))

    if a.techniques or b.techniques:
        out.append(Section('Techniques applied'))
        # The two units research different techniques, so the name has to sit
        # inside the column it belongs to. Putting it in the label column and
        # pairing the lists by position would caption the Spearman's Dragon's
        # Heart with the Samurai's Dragon's Fire.
        for i in range(max(len(a.techniques), len(b.techniques))):
            ta_ = a.techniques[i] if i < len(a.techniques) else None
            tb_ = b.techniques[i] if i < len(b.techniques) else None
            out.append(Row(f'Technique {i + 1}',
                           f'{ta_.name} - {ta_.summary}' if ta_ else '',
                           f'{tb_.name} - {tb_.summary}' if tb_ else ''))
    return out


def compare_units(book, row_a, row_b, with_techniques=True):
    """Everything the dialog needs: both units, the verdict and the page."""
    a = unit_stats(book, row_a, with_techniques)
    b = unit_stats(book, row_b, with_techniques)
    v = verdict(a, b)
    return a, b, v, build_rows(a, b, v)
