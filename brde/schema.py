"""
brde.schema - Schema inference for Battle Realms.xlsx

Works out which columns in the Data_* sheets reference which Enum_* sheet, so
the GUI can offer a dropdown instead of making the user look up raw numbers.
"""
import re


# ---------------------------------------------------------------- helpers
def split_tokens(name: str):
    """Split a CamelCase / snake_case column name into words."""
    s = re.sub(r'[^A-Za-z0-9]', ' ', str(name))
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', s)
    s = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)
    return [t for t in s.split() if t]


def norm(s: str) -> str:
    """Lowercase and strip every non-alphanumeric character."""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


# ---------------------------------------------------------------- rules
# Columns that are definitely plain numbers - never given an enum dropdown.
NUMERIC_PATTERNS = [
    r'(Time|Cost|Rate|Damage|Count|Priority|Amount|Delay|Duration|Speed|Height|Width|'
    r'Radius|Length|Size|Scale|Angle|Chance|Percent|Bonus|Cap|Multiplier|Modifier|'
    r'Health|Fatigue|Stamina|Level|Index|Order|Value|Weight|Mass|Offset|Density|'
    r'Frequency|Volume|Alpha|Red|Green|Blue|Charges|Points|Slots|Number|Num)\d*$',
    r'^(Max|Min|Num|Initial|Total|Base|Default)(?!.*Type$)',
    r'^(X|Y|Z|U|V)$',
    r'(LOD|FPS|MS)$',
    r'^(Duration|Lifetime|Cooldown|Recharge|Threshold|Elapsed|Interval|Spread)',
]
NUMERIC_RE = [re.compile(p) for p in NUMERIC_PATTERNS]

# Hand-written rules: (column-name regex, enum name without the 'Enum_' prefix).
# Every match is still validated against the enum's actual codes before use.
EXPLICIT_RULES = [
    (r'^(Melee|Missile|Primary|Secondary|Alternate)?Weapon\d*$', 'WeaponType'),
    (r'Unit(In|Out|ToDock|ToSpawn|ToCreate|ToTrain)\d*$', 'UnitType'),
    (r'^Unit\d+$', 'UnitType'),
    (r'^DockingUnitToSpawn$', 'UnitType'),
    (r'^AffectSpecificUnitType\d*$', 'UnitType'),
    (r'^UpgradeToType$', 'BuildingType'),
    (r'^(Building|TrainBuilding)(Required|Type)\d*$', 'BuildingType'),
    (r'^BuildingAttachmentFlag$', 'BuildingAttachmentType'),
    (r'^WeaponSlot', 'WeaponSlotType'),
    (r'^DamageEffect', 'EffectType'),
    (r'^AnimState$', 'UnitAnimStateType'),
    (r'^Speech', 'SpeechFXType'),
    (r'^Class$', 'ObjectClassType'),
    (r'^ParticleEffect', 'EffectType'),
    (r'^SpeechFX', 'SpeechFXType'),
    (r'^SFX', 'SoundEventType'),
    (r'^Effect(?!iveness)', 'EffectType'),
    (r'^Sound', 'SoundType'),
    (r'^Ambient(Life)?Type$', 'AmbientLifeType'),
    (r'^(Impact|Weapon)Impact', 'WeaponImpactType'),
    (r'Material$', 'MaterialType'),
    (r'^Decal', 'DecalTypes'),
    (r'^Icon', 'TextureType'),
    (r'^TargetRange$', 'TargetableRangeType'),
    (r'^TargetCursorType$', 'CursorType'),
    (r'Cursor$', 'CursorType'),
    (r'^Play(Rider)?Animation$', 'UnitAnimStateType'),
    (r'AnimationState$', 'UnitAnimStateType'),
    (r'^CreateMagicAt', 'MagicObjectType'),
    (r'^AIBuildingClass$', 'AIBuildingType'),
    (r'^Clan\d*$', 'ClanType'),
    (r'^Model\d*$', 'ModelType'),
    (r'^Texture\d*$', 'TextureType'),
    (r'^Button\d*$', 'ButtonType'),
    (r'^AbilityAffected\d*$', 'AbilityType'),
    (r'^Ability\d*$', 'AbilityType'),
    (r'^Upgrade\d*$', 'UpgradeType'),
    (r'^Technique\d*$', 'TechniqueType'),
    (r'^Spell\d*$', 'SpellType'),
    (r'^Projectile\d*$', 'ProjectileType'),
    (r'^BattleGear\d*$', 'BattleGearType'),
    (r'^Building\d*$', 'BuildingType'),
    (r'^Object\d*$', 'ObjectType'),
    (r'^Effect\d*$', 'EffectType'),
    (r'^Beam\d*$', 'BeamType'),
    (r'^Decal\d*$', 'DecalTypes'),
    (r'^Material\d*$', 'MaterialType'),
    (r'^Music\d*$', 'MusicType'),
    (r'^Theme\d*$', 'ThemeType'),
    (r'^Province\d*$', 'ProvinceType'),
    (r'^Screen\d*$', 'ScreenType'),
    (r'^Control\d*$', 'ControlType'),
    (r'^HotKey\d*$', 'HotKeyType'),
    (r'^UVA\d*$', 'UVAType'),
]
EXPLICIT_RE = [(re.compile(p, re.I), e) for p, e in EXPLICIT_RULES]

# Columns whose name reads as a yes/no question. Checked before name matching,
# because a trailing noun otherwise drags them into the wrong enum: 'IsFireWeapon'
# ends in 'Weapon' and its 0/1 values happen to be valid WeaponType codes, so it
# would be shown as 'WEAPON_ARAH_ARROW'. Only applied when the column really does
# hold nothing but 0 and 1.
BOOL_PREFIX_RE = re.compile(
    r'^(Is|Can|Has|Should|Allow|Allows|Use|Uses|Enable|Enables|Prefers|Affects|'
    r'Only|Always|Never|No)[A-Z]')

# Armour multipliers. Floats in Data_Units, but Data_Buildings stores whole
# numbers, which would otherwise be mistaken for a yes/no column.
ARMOR_RE = re.compile(r'^AM(Cutting|Piercing|Blunt|Fire|Explosive|Magical)$')

# Marker used in place of an enum name for boolean (0/1) columns.
BOOL_ENUM = '@bool'
BOOL_ITEMS = [(0, 'No / False (0)'), (1, 'Yes / True (1)')]

# Data_* sheet -> the enum that defines its own primary key (the 'Type' column).
# Only needed where the sheet name does not map to an enum name directly.
SHEET_SELF_OVERRIDE = {
    'Data_BattleGear': 'BattleGearType',
    'Data_UnitAndBattleGear': 'UnitAndBattleGearType',
    'Data_UnitToUnitAndBattleGear': 'UnitAndBattleGearType',
    'Data_MAXJointProperties': 'MAXJointProperties',
    'Data_MAXTriangleProperties': 'MAXTriangleProperties',
    'Data_TeamColors': 'TeamColors',
    'Data_Decals': 'DecalTypes',
    'Data_GameLOD': 'GameLOD',
    'Data_ModelEventMarkers': 'ModelEventMarkers',
    'Data_AmbientLifeEffects': 'AmbientLifeEffects',
    'Data_AmbientLifeSounds': 'AmbientLifeSounds',
    'Data_PathingCategory': 'PathingCategory',
    'Data_WorldVariables': 'WorldDataType',
    'Data_ScriptCommands': 'ScriptCommands',
    'Data_Techniques': 'TechniqueType',
    'Data_Objects': 'ObjectType',
    'Data_ModelClasses': 'ModelClass',
    'Data_ClanSFX': 'ClanType',
    'Data_BuildingTechTree': 'BuildingType',
    'Data_WeaponEffects': 'WeaponType',
    'Data_WeaponSFX': 'WeaponType',
    'Data_AIWarPartyMakeUps': 'AIWarPartyType',
    'Data_UnitToWarPartyEffectivenes': 'UnitType',
    'Data_UnitAndInnateAbilities': 'UnitType',
    'Data_UnitStaticAttachmentStates': 'UnitStaticAttachmentStateType',
    'Data_InterfaceModelAnimStates': 'InterfaceModelAnimStateTyp',
    'Data_DialogueResources': 'DialogueActorType',
    'Data_GameTriggers': 'TriggerType',
    'Data_ScriptCommandUserTypes': 'ScriptCommands',
    'MapEditor_ForestTypes': 'StaticObjectType',
    'MapEditorObjects': 'StaticObjectType',
}


def _derive_from_sheet_name(sheet: str, enums: dict):
    base = sheet.split('_', 1)[1] if '_' in sheet else sheet
    tries = [base + 'Type', base, base + 'Types']
    if base.endswith('ies'):
        tries.insert(0, base[:-3] + 'yType')
    if base.endswith('sses'):
        tries.insert(0, base[:-2] + 'Type')
    elif base.endswith('s'):
        tries.insert(0, base[:-1] + 'Type')
    lut = {norm(k): k for k in enums}
    for t in tries:
        if norm(t) in lut:
            return lut[norm(t)]
    return None


def natural_self_enum(sheet: str, enums: dict):
    """Primary-key enum derived from the SHEET NAME ONLY (ignores the override map).

    Used by the "jump to record" feature: Enum_UnitType must resolve back to
    Data_Units, not to a secondary table such as Data_UnitAndInnateAbilities.
    """
    return _derive_from_sheet_name(sheet, enums)


def sheet_self_enum(sheet: str, enums: dict):
    """Enum that defines the primary key of a Data_* sheet."""
    if sheet in SHEET_SELF_OVERRIDE:
        cand = SHEET_SELF_OVERRIDE[sheet]
        return cand if cand in enums else None
    return _derive_from_sheet_name(sheet, enums)


def singularize(w: str) -> str:
    if w.endswith('ies'):
        return w[:-3] + 'y'
    if w.endswith('sses') or w.endswith('shes') or w.endswith('ches'):
        return w[:-2]
    if w.endswith('s') and not w.endswith('ss'):
        return w[:-1]
    return w


def _name_candidates(col: str, sheet_base: str, enums: dict):
    """Candidate enum names for a column, best match first.

    Tries progressively shorter suffixes of the column's word list, each
    optionally prefixed with the sheet name, e.g.
    Data_BattleGear.AcquisitionType -> Enum_BattleGearAcquisitionType.
    """
    lut = {norm(k): k for k in enums}
    toks = split_tokens(col)
    while toks and toks[-1].isdigit():
        toks.pop()
    prefixes = []
    for p in (sheet_base, singularize(sheet_base), ''):
        if p not in prefixes:
            prefixes.append(p)
    out = []
    suffixes = ['', 'Type', 'Types', 'Class', 'ClassType', 's']
    for start in range(len(toks)):
        base = ''.join(toks[start:])
        if not base:
            continue
        for pi, pre in enumerate(prefixes):
            rank = len(prefixes) - pi          # sheet-prefixed matches win
            for suf in suffixes:
                k = norm(pre + base + suf)
                if k in lut:
                    out.append((len(toks) - start, rank, lut[k]))
            if base.lower().endswith('type'):
                k = norm(pre + base[:-4])
                if k in lut:
                    out.append((len(toks) - start, rank, lut[k]))
    out.sort(key=lambda x: (-x[0], -x[1]))
    seen, res = set(), []
    for _, _, e in out:
        if e not in seen:
            seen.add(e)
            res.append(e)
    return res


def infer_column_enum(sheet: str, col: str, values, enums: dict, self_enum=None):
    """Return an enum name ('WeaponType'), '@bool', or None for a plain number.

    values: the integer values actually present in the column (must be non-empty).
    enums:  {enum_name: set_of_valid_codes}

    Every candidate must pass a coverage check - all values in the column have
    to exist in the enum (with -1 always allowed as "none / invalid") - so a
    name that merely looks right is rejected when the data disagrees. The
    coverage check alone is not enough for small code ranges, though: a 0/1
    column passes against almost any enum, which is why the yes/no phrasing test
    runs before name matching.
    """
    if not values:
        return None
    sv = set(values)
    colname = str(col)

    # 1. primary-key column
    if colname.lower() in ('type', 'code') and self_enum:
        return self_enum

    # 2. armour multipliers are always plain numbers
    if ARMOR_RE.match(colname):
        return None

    # 3. yes/no phrasing wins over any name match, but only if the data agrees
    if BOOL_PREFIX_RE.match(colname) and sv <= {0, 1}:
        return BOOL_ENUM

    # 4. hand-written rules
    for rx, ename in EXPLICIT_RE:
        if rx.search(colname) and ename in enums:
            if sv <= enums[ename] | {-1}:
                return ename

    # 5. numeric blacklist
    if any(rx.search(colname) for rx in NUMERIC_RE):
        return None

    # 6. name matching + coverage check
    sheet_base = sheet.split('_', 1)[1] if '_' in sheet else sheet
    for cand in _name_candidates(colname, sheet_base, enums):
        if sv <= enums[cand] | {-1}:
            return cand

    # 7. boolean: only 0/1 present -> Yes/No dropdown (other values still typable)
    if sv <= {0, 1}:
        return BOOL_ENUM
    return None


def enum_to_data_sheet(ename: str, data_sheets, enums: dict):
    """Enum name -> the Data_* sheet keyed by it. Used for "jump to record"."""
    for s in data_sheets:
        if sheet_self_enum(s, enums) == ename:
            return s
    return None
