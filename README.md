# Battle Realms Data Editor (XLSX)

An editor for Battle Realms game data in the newer **`Battle Realms.xlsx`** format
that replaced the old `.dat` files, which is why the original Battle Realms Data
Editor no longer works. Written in Python + PyQt6.

## Install & run

**Easiest way (Windows):** double-click `run_editor.bat`. It handles setup for you:

1. **No Python installed?** The script says so and asks for confirmation before
   doing anything. Answer `Y` and it downloads Python 3.12.10 from python.org and
   installs it silently — per-user, so **no administrator rights are needed** — with
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
```

## Menu bar

| Menu | Contents |
|---|---|
| **File** | Open file… · Open recent ▸ · Save · Save As… · Close file · Exit |
| **Edit** | Undo · Redo · Copy · Paste · Clear cells · Revert to original · Add row |
| **View** | Show enum descriptions · Filter rows · Go to sheet… · List edited cells |
| **Help** | How to use (F1) · About |

## Features

| Feature | Description |
|---|---|
| **Dropdowns instead of raw numbers** | 561 reference columns are detected automatically. Click a cell and pick `17 — WEAPON_BOWBASH` from the list instead of looking the number up by hand. |
| **Type to search the dropdown** | Long lists (2,900 sound codes, for example) filter as you type — match on any part of the name. |
| **Show enum descriptions** | The grid shows `0 — UNIT_D_ARCHER` instead of `0`. Untick to see raw codes. |
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

## Preserving the original file format

This is the most important part. The editor does **not** rewrite the workbook with
openpyxl — that approach regenerates the entire file and can drop formatting
details.

Instead it **patches the XML inside the `.xlsx` archive directly**: the file is
opened as a ZIP archive, only the `<c>` elements of the cells you actually changed
are rewritten, and the archive is repacked with the original entry order and
compression settings.

Verified in testing: editing 107 cells across 9 different sheets changed only 10
parts of the archive (the 9 sheet XML files plus `sharedStrings.xml`). The other
**191 parts were byte-for-byte identical to the original file**. Sheet count,
styles, layout, column widths and frozen panes all survive untouched.

## Source layout

```
br_schema.py   Infers which columns reference which Enum_* table
br_core.py     Reads the workbook (openpyxl) and saves by patching XML
br_model.py    Table model, dropdown delegate, undo commands
br_editor.py   Main window — run this file
```

### How enum columns are detected

The workbook contains no data validation rules, so `br_schema.py` infers the
mapping in four steps. Every candidate must pass a **coverage check** — all values
present in the column have to exist in the enum table — before it is accepted:

1. **Primary key columns** — the `Type` column of `Data_Buildings` → `Enum_BuildingType`.
2. **Explicit rules** — `MeleeWeapon`/`MissileWeapon` → `Enum_WeaponType`,
   `EffectCollisionWater` → `Enum_EffectType`, `SFXBuildingPlaced` → `Enum_SoundEventType`, and so on.
3. **Numeric blacklist** — names ending in `Cost`, `Rate`, `Damage`, `Time`,
   `Radius`… are always plain numbers and never get a dropdown.
4. **Name matching** — split the CamelCase name, then try it with the sheet name as
   a prefix: `Data_BattleGear.AcquisitionType` → `Enum_BattleGearAcquisitionType`.

Columns that only ever hold 0 or 1 get a **Yes/No** dropdown, but you can still
type any other value.

Result on the sample file: **561 of 563** reference-style columns detected
correctly. The two exceptions (`WatchtowerMinUnitRange`, `MilliwaterPerFireUnit`)
really are plain numbers.

### Adjusting the mapping

Edit `EXPLICIT_RULES` or `SHEET_SELF_OVERRIDE` in `br_schema.py`. For example, to
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
  `Data_UnitToWarPartyEffectivenes.Type`) — that is the game's own data, not a bug
  in the tool.
