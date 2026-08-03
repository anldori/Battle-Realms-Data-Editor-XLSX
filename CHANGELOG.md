# Changelog

Also shown in **Help ▸ About**, which is the authoritative copy — it is generated from
`CHANGELOG` in `brde/about.py`.

## 1.1.1 (current)

- **Abilities on the record page.** A unit's abilities were missing, because
  `Data_Units` has no ability column at all — the link runs through a separate join
  sheet. The page now follows it, and shows innate abilities, the ability each piece of
  battle gear grants, spells, and the techniques that affect the unit, each with its
  name and key stats and editable in place. The Dragon Samurai gets its Seppuku, Dragon
  Skin and Yang Blade.
- **Less noise under "Referenced by".** Rows a curated section has already laid out
  properly are no longer repeated at the bottom of the page under a worse label.
  References into the same sheet through a different column are still listed.
- Techniques now name the ability they change instead of showing a bare code number.
- **Records are findable by their real name.** Only 32 of the 87 data sheets call the
  name column `Name` — abilities call it `ActualAbility`, weapons `ActualWeapon` — so
  searching for "Dragon Skin" or "Sight Beyond Sight" found nothing, even though the
  record page was already showing that name. The record you meant still ranks first:
  "samurai" leads with the Dragon Samurai, not with its sound effects.
- **A building's docked ability is spelled out**, the way a unit's abilities are. The
  Dragon Monument and the Lotus Warlock's Tower now show what docking there actually
  does.
- **Battle gear columns showed bare numbers.** A hero's `DefaultBattleGear` read `82`
  instead of naming the gear, and the gear combination columns had no dropdown at all.
  Hero Arah now shows `BATTLE_GEAR_HERO_ARAH_ZEN_ARROWS` and the ability behind it,
  Sight Beyond Sight. The unit page also lists the gear combinations that belong to the
  unit.
- **Weapon and upgrade classes were reading from the wrong code table.** A weapon's
  `Class` showed `OBJECTCLASS_WATER` when it means `WEAPONCLASS_PROJECTILE`, and an
  upgrade's showed the same plant / stone / water table instead of offensive /
  defensive / misc.
- **Ten yes/no switches had become dropdowns of the wrong thing.** Columns such as
  `CreateUnit`, `RemoveEnemyUpgrade` and `AIAlwaysAddUnit` end in a word that names a
  code table, so they were offering a list of units or upgrades where the answer is only
  yes or no. The real reference sits in the column beside them, and those were never
  touched: `CreatedUnitType`, `SetWeapon` and `UpgradeUnit` still resolve normally.
- **Technique effects were reading from the wrong code table.**
  `TECHNIQUE_DRAGONS_STRENGTH` showed `EFFECT_BALLISTAMAN_TOTEM_IMPACT` when the code
  means `TE_WP_MULT_DAMAGE` — multiply weapon damage, by the factor beside it. Effect
  columns in `Data_Techniques` now read `Enum_TechniqueEffectType`, and each one is
  shown next to the `FloatParam` it scales by, so the pair reads as one statement.
- **Buildings show what they research.** A tavern or a dojo never listed its techniques
  and upgrades, because those sheets point at the building rather than the other way
  round. There is now a "Researched here" section with the cost, time and affected units
  of each one, plus a "Requires" section for the buildings needed first. The old
  "Upgrades to" section is now called "Upgrades into another building", which is what it
  always meant.
- **The window now carries the program icon** in the title bar and on the taskbar, not
  just in File Explorer.

## 1.1.0

- **Compare two files.** Diff your mod against vanilla, or two versions of your own
  work. Rows are matched by their `Type` key rather than by position, differences can be
  filtered and exported to CSV, and any of them can be taken back into your file as an
  ordinary undoable edit.
- **Record details.** Search a unit or building by name and read every stat on one page,
  including the damage and range of each weapon it carries, which live in a different
  sheet. Everything on the page is editable in place.

## 1.0.0

- First release. Browse and edit every sheet, with dropdowns instead of raw code
  numbers, undo/redo, copy and paste, and saving that patches the XML inside the `.xlsx`
  so untouched parts of the file stay byte-for-byte identical.
