# Battle Realms Data Editor (XLSX)

An editor for Battle Realms game data in the newer **`Battle Realms.xlsx`** format
that replaced the old `.dat` files, which is why the original Battle Realms Data
Editor no longer works. Written in Python + PyQt6.

## Install & run

**Easiest way (Windows):** double-click `quick_start.bat`. It handles setup for you:

1. **No Python installed?** The script says so and asks for confirmation before
   doing anything. Answer `Y` and it downloads Python 3.12.10 from python.org and
   installs it silently - per-user, so **no administrator rights are needed** - with
   *Add to PATH* and pip enabled. Answer `N` and nothing on your computer is
   touched; you get manual instructions instead.
2. **Missing packages?** PyQt6 and openpyxl are installed on first run.
3. Then the editor launches.

The script picks the matching installer for your CPU (x64 / ARM64 / x86) and reads
the updated PATH straight from the registry, so it finds the fresh Python without
you having to reopen the window or reboot.

The app starts on a **welcome screen** with no file loaded. Pick a file in any of
three ways:

- **File ▸ Open file…** on the menu bar (or `Ctrl+O`) → file browser dialog
- The **"Open Battle Realms.xlsx…"** button in the middle of the welcome screen
- **Drag and drop** a `.xlsx` file onto the window

Previously opened files appear under **File ▸ Open recent** and as quick-open
buttons on the welcome screen.

**Manual (Python 3.9+ already installed):**

```bash
pip install -r requirements.txt
python br_editor.py                                  # welcome screen
python br_editor.py "C:\path\to\Battle Realms.xlsx"  # open a file directly
python -m brde                                       # same thing, as a module
```

## Menu bar

| Menu | Contents |
|---|---|
| **File** | Open file… · Open recent ▸ · Save · Save As… · Close file · Exit |
| **Edit** | Undo · Redo · Copy · Paste · Clear cells · Revert to original · Add row |
| **View** | Show enum descriptions · Filter rows · Go to sheet… · List edited cells |
| **Record** | Find record… (Ctrl+I) · Details for the selected row (Ctrl+Shift+I) |
| **Compare** | Compare with another file… (Ctrl+D) · Compare with last file again · Show last report · Clear comparison |
| **Help** | How to use (F1) · About |

## Viewing a unit or building in full

**Record ▸ Find record…** (`Ctrl+I`) answers the question the grid makes hard: *what
are the Samurai's actual numbers?* Type a name - `samurai`, `dojo`, `katana` - pick
the record from the list of matches, and everything about it is on one page.

Already looking at the right row in the grid? **Record ▸ Details for the selected
row** (`Ctrl+Shift+I`), or right-click the cell, opens it straight away.

The Samurai's stats are spread across several sheets, and the page pulls them
together:

- **From `Data_Units`** - cost, health, fatigue, the six armour multipliers, line of
  sight, terrain speed multipliers, battle gear, spells.
- **From `Data_Weapons`** - the damage, range, recovery and damage class of every
  weapon it carries. The unit sheet only names the weapon; the numbers live one
  table away, and the page follows the reference for you.
- **From `Data_Buildings`** - which buildings train it, from which unit, and how
  long it takes. The Samurai turns out to have three recipes.
- **Referenced by** - every other row that points at this record: techniques,
  upgrades, battle gear, war party effectiveness.

Anything a section does not mention still appears under **Other fields**, so no
column is ever hidden from you.

The page is not read-only. **Every value is editable in place**, dropdowns included,
and edits behave exactly like edits in the grid: yellow highlight, `Ctrl+Z` to undo,
`Ctrl+S` to write out. A field that belongs to a referenced record - a weapon's
damage, say - edits *that* record, which the tooltip tells you before you type.

Field names shown in blue are links: **double-click the name** to open the record it
points at, and **< Back** to return. **Show in grid** jumps to the row in the main
window. Right-clicking any cell in the grid also offers *View details for this
record*.

Search results are ordered so the obvious answer comes first. Typing `samurai`
matches 45 records - mostly particle effects and sound events whose names start with
the word - but the Dragon Samurai unit is at the top, because units, buildings and
weapons outrank the rest.

## Comparing two files

**Compare ▸ Compare with another file…** (`Ctrl+D`) asks you to browse to a second
`.xlsx`, then reports every difference between it and the file you have open -
useful for diffing your mod against vanilla, or two versions of your own work.

The report window lists **Sheet · Row · Key · Column · This file · Other file ·
Status**, and you can:

- **Filter** by sheet, by status, or by free text - matching enum descriptions too,
  so typing `geisha` finds the row even though the cell holds a number
- **Double-click** any row to jump straight to that cell in the main grid
- **Take other value** - copy their value into your file as a normal, undoable edit
  (`Ctrl+Z` works, `Ctrl+S` writes it out)
- **Export to CSV** - save the whole report to read elsewhere or share

Differing cells are also tinted purple in the grid, and their tooltip shows both
values side by side. Untick *Highlight in grid* in the report, or use
**Clear comparison**, to remove the tint.

Three details worth knowing:

- **Rows are matched by their `Type` key, not by position.** Insert one record near
  the top of a sheet and only that record is reported - not every row below it.
  Position matching is used only for sheets with no usable unique key.
- **Columns are matched by header name**, so a column inserted in the middle does
  not shift everything after it.
- Records present in only one of the two files are reported as *only in this file* /
  *only in other file* rather than as changed cells, and sheets or columns that
  exist in just one file are listed at the top of the report.

The comparison reads your **unsaved edits**, so pending changes appear as
differences; the tool warns you about this before it starts.

## Features

| Feature | Description |
|---|---|
| **Record details** | `Ctrl+I`. Search a unit or building by name and read every stat on one page, weapon damage included. Editable in place. |
| **Dropdowns instead of raw numbers** | 546 reference columns are detected automatically. Click a cell and pick `17 - WEAPON_BOWBASH` from the list instead of looking the number up by hand. |
| **Type to search the dropdown** | Long lists (2,900 sound codes, for example) filter as you type - match on any part of the name. |
| **Show enum descriptions** | The grid shows `0 - UNIT_D_ARCHER` instead of `0`. Untick to see raw codes. |
| **Row filter** | The "Filter rows" box matches both codes and enum descriptions. |
| **Undo / Redo** | `Ctrl+Z` / `Ctrl+Y`, unlimited depth. |
| **Edited cells highlighted** | Edited cells turn yellow; hover to see the original value. `Ctrl+E` lists every edit and jumps to it. |
| **Jump to referenced record** | Right-click an enum cell → "Go to Data_Weapons" or "Open code table Enum_WeaponType". |
| **Invalid code warning** | Codes that do not exist in the enum table are shown in red. |
| **Copy / Paste** | `Ctrl+C` / `Ctrl+V` over a range, tab-separated so it round-trips with Excel. |
| **Add row** | `Ctrl+Shift+N` appends a new row to the current sheet. |
| **Quick sheet switching** | `Ctrl+P` to type a sheet name, or use the searchable list on the left. |
| **Open recent** | The last 8 files are remembered between sessions. |
| **Automatic backup** | Every save first creates `Battle Realms.xlsx.YYYYMMDD_HHMMSS.bak`. |

## Version history

Also shown in **Help ▸ About**, which is the authoritative copy - it is generated
from `CHANGELOG` in `brde/about.py`.

**1.1.1** (current)

- **Abilities on the record page.** A unit's abilities were missing, because
  `Data_Units` has no ability column at all - the link runs through a separate join
  sheet. The page now follows it, and shows innate abilities, the ability each piece
  of battle gear grants, spells, and the techniques that affect the unit, each with
  its name and key stats and editable in place. The Dragon Samurai gets its Seppuku,
  Dragon Skin and Yang Blade.
- **Less noise under "Referenced by".** Rows a curated section has already laid out
  properly are no longer repeated at the bottom of the page under a worse label.
  References into the same sheet through a different column are still listed.
- Techniques now name the ability they change instead of showing a bare code number.
- **Buildings show what they research.** A tavern or a dojo never listed its
  techniques and upgrades, because those sheets point at the building rather than the
  other way round. There is now a "Researched here" section with the cost, time and
  affected units of each one, plus a "Requires" section for the buildings needed
  first. The old "Upgrades to" section is now called "Upgrades into another
  building", which is what it always meant.
- **The window now carries the program icon** in the title bar and on the taskbar,
  not just in File Explorer.

**1.1.0**

- **Compare two files.** Diff your mod against vanilla, or two versions of your own
  work. Rows are matched by their `Type` key rather than by position, differences can
  be filtered and exported to CSV, and any of them can be taken back into your file
  as an ordinary undoable edit.
- **Record details.** Search a unit or building by name and read every stat on one
  page, including the damage and range of each weapon it carries, which live in a
  different sheet. Everything on the page is editable in place.

**1.0.0**

- First release. Browse and edit every sheet, with dropdowns instead of raw code
  numbers, undo/redo, copy and paste, and saving that patches the XML inside the
  `.xlsx` so untouched parts of the file stay byte-for-byte identical.

## Preserving the original file format

This is the most important part. The editor does **not** rewrite the workbook with
openpyxl - that approach regenerates the entire file and can drop formatting
details.

Instead it **patches the XML inside the `.xlsx` archive directly**: the file is
opened as a ZIP archive, only the `<c>` elements of the cells you actually changed
are rewritten, and the archive is repacked with the original entry order and
compression settings.

Verified in testing: editing 107 cells across 9 different sheets changed only 10
parts of the archive (the 9 sheet XML files plus `sharedStrings.xml`). The other
**191 parts were byte-for-byte identical to the original file**. Sheet count,
styles, layout, column widths and frozen panes all survive untouched.

## Building a standalone .exe

To hand the editor to someone who does not have Python, package it with
PyInstaller. Double-click **`build\build_exe.bat`** - it installs PyInstaller if
needed and asks which layout you want:

| Mode | Output | Trade-off |
|---|---|---|
| **One folder** (recommended) | `dist\BattleRealmsDataEditor\` | Starts instantly. ~90 MB. Share the whole folder or zip it. |
| **Single file** | `dist\BattleRealmsDataEditor.exe` | One portable file, ~45 MB. Each launch takes a few seconds while it unpacks to a temp folder. |

Neither output needs Python, PyQt6 or the `.bat` files on the target machine.

Drop an **`icon.ico` into the `build` folder** and it is embedded in the executable
automatically - no editing of the script. A copy in the project root also works.

For a scripted build, pass the layout as an argument (`build_exe.bat 1` for one
folder, `2` for a single file); then nothing is asked and nothing pauses.

Equivalent command if you prefer to run it yourself:

```bash
pip install pyinstaller
pyinstaller br_editor.py --name BattleRealmsDataEditor --onedir --windowed ^
    --collect-submodules openpyxl --exclude-module tkinter
```

The `--windowed` flag matters: without it Windows opens a console window behind
the GUI. `--collect-submodules openpyxl` is insurance against openpyxl's lazy
imports being missed by PyInstaller's static analysis. The full script also
excludes the unused Qt modules (QML, WebEngine, Multimedia, Charts and so on),
which is where most of the size saving comes from.

The finished program lands in `dist\`; PyInstaller's intermediate files and the
generated `.spec` go to `build\_work\`. Both are throwaway and both are ignored by
git, so delete them whenever you like. See `build\README.md` for more.

## Source layout

```
br_editor.py         Launcher - run this file
brde/
    __init__.py      Package docstring and version
    __main__.py      Lets you run `python -m brde`
    schema.py        Infers which columns reference which Enum_* table
    core.py          Reads the workbook (openpyxl) and saves by patching XML
    model.py         Table model, dropdown delegate, undo commands
    detail.py        Record details window: search, stat page, cross-sheet lookups
    compare.py       File comparison engine and difference report window
    app.py           Main window, wiring all of the above together
tests/               Test suite, standard library unittest only
build/
    build_exe.bat    Packages everything into a standalone .exe
    icon.ico         Optional - put yours here and the build uses it
quick_start.bat      Launcher: installs Python/packages if needed, then runs
requirements.txt     PyQt6 and openpyxl
```

The modules are listed in dependency order: nothing imports anything above it in
that list. `schema.py` in particular has no Qt and no file I/O, so its rules can be
exercised on their own.

`br_editor.py` stays at the top level because `quick_start.bat`, desktop shortcuts
and the PyInstaller build all refer to it by name. It only fixes up `sys.path` and
calls into the package, and it turns a missing dependency into a readable message
instead of a stack trace.

### Running the tests

```bash
python -m unittest discover -s tests -v
```

No test framework to install - it is all standard library. The tests that need real
game data look for `Battle Realms.xlsx` in the project root and skip themselves if it
is not there, so the suite still passes without it.

### How enum columns are detected

The workbook contains no data validation rules, so `brde/schema.py` infers the
mapping in several steps. Every candidate must pass a **coverage check** - all values
present in the column have to exist in the enum table - before it is accepted:

1. **Primary key columns** - the `Type` column of `Data_Buildings` → `Enum_BuildingType`.
2. **Armour multipliers** - `AMCutting` and friends are always plain numbers.
3. **Yes/no phrasing** - a column named `IsSomething`, `CanSomething`, `HasSomething`…
   holding nothing but 0 and 1 is a flag, not a reference.
4. **Explicit rules** - `MeleeWeapon`/`MissileWeapon` → `Enum_WeaponType`,
   `EffectCollisionWater` → `Enum_EffectType`, `SFXBuildingPlaced` → `Enum_SoundEventType`, and so on.
5. **Numeric blacklist** - names ending in `Cost`, `Rate`, `Damage`, `Time`,
   `Radius`… are always plain numbers and never get a dropdown.
6. **Name matching** - split the CamelCase name, then try it with the sheet name as
   a prefix: `Data_BattleGear.AcquisitionType` → `Enum_BattleGearAcquisitionType`.

Columns that only ever hold 0 or 1 get a **Yes/No** dropdown, but you can still
type any other value.

Steps 2 and 3 exist because the coverage check is weak for small code ranges: a
column holding only 0 and 1 passes against nearly every enum table, so name matching
alone would claim it. `Data_Weapons.IsFireWeapon` ends in `Weapon` and its 0/1 values
are valid `WeaponType` codes, so it used to be displayed as `WEAPON_ARAH_ARROW`;
`Data_Buildings.AMCutting` was shown as a Yes/No dropdown. Those two rules fix 23
columns in the sample file.

Result on the sample file: **546 reference-style columns** detected. The known
exceptions (`WatchtowerMinUnitRange`, `MilliwaterPerFireUnit`) really are plain
numbers.

### Adjusting the detail page

Sections come from `PROFILES` in `brde/detail.py`, one entry per sheet. A section is a
title plus a list of column names; `_expand(...)` pulls fields in from a referenced
record, and a function can be used where the layout has to be computed, as with the
six training slots of a building. Sheets with no profile still get a page, built
generically from the schema. Adding a section is a matter of listing column names -
anything you leave out simply stays under *Other fields*.

### Adjusting the mapping

Edit `EXPLICIT_RULES` or `SHEET_SELF_OVERRIDE` in `brde/schema.py`. For example, to
force a column named `MyColumn` to use `Enum_UnitType`:

```python
EXPLICIT_RULES = [
    (r'^MyColumn$', 'UnitType'),
    ...
]
```

## Notes

- Keep a copy of the original `Battle Realms.xlsx` before modding, though the
  editor also creates a `.bak` on every save.
- A code of `-1` means "none / invalid" in most enum columns.
- A red cell means the code is not in the enum table. The original file already
  contains two such columns (`Data_UnitSpeechFXEvents.Type` and
  `Data_UnitToWarPartyEffectivenes.Type`) - that is the game's own data, not a bug
  in the tool.
