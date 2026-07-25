# Battle Realms Data Editor (XLSX)

An editor for Battle Realms game data in the newer **`Battle Realms.xlsx`** format
that replaced the old `.dat` files, which is why the original Battle Realms Data
Editor no longer works. Written in Python + PyQt6.

## Install & run

**Easiest way (Windows):** double-click `quick_start.bat`. It handles setup for you:

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
| **Compare** | Compare with another file… (Ctrl+D) · Compare with last file again · Show last report · Clear comparison |
| **Help** | How to use (F1) · About |

## Comparing two files

**Compare ▸ Compare with another file…** (`Ctrl+D`) asks you to browse to a second
`.xlsx`, then reports every difference between it and the file you have open —
useful for diffing your mod against vanilla, or two versions of your own work.

The report window lists **Sheet · Row · Key · Column · This file · Other file ·
Status**, and you can:

- **Filter** by sheet, by status, or by free text — matching enum descriptions too,
  so typing `geisha` finds the row even though the cell holds a number
- **Double-click** any row to jump straight to that cell in the main grid
- **Take other value** — copy their value into your file as a normal, undoable edit
  (`Ctrl+Z` works, `Ctrl+S` writes it out)
- **Export to CSV** — save the whole report to read elsewhere or share

Differing cells are also tinted purple in the grid, and their tooltip shows both
values side by side. Untick *Highlight in grid* in the report, or use
**Clear comparison**, to remove the tint.

Three details worth knowing:

- **Rows are matched by their `Type` key, not by position.** Insert one record near
  the top of a sheet and only that record is reported — not every row below it.
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

## Building a standalone .exe

To hand the editor to someone who does not have Python, package it with
PyInstaller. Double-click **`build_exe.bat`** — it installs PyInstaller if needed
and asks which layout you want:

| Mode | Output | Trade-off |
|---|---|---|
| **One folder** (recommended) | `dist\BattleRealmsDataEditor\` | Starts instantly. ~90 MB. Share the whole folder or zip it. |
| **Single file** | `dist\BattleRealmsDataEditor.exe` | One portable file, ~45 MB. Each launch takes a few seconds while it unpacks to a temp folder. |

Neither output needs Python, PyQt6 or the `.bat` files on the target machine.

Drop an `icon.ico` next to the script and the build picks it up automatically.

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

Build leftovers — the `build` folder and `BattleRealmsDataEditor.spec` — can be
deleted afterwards.

## Source layout

```
br_schema.py     Infers which columns reference which Enum_* table
br_core.py       Reads the workbook (openpyxl) and saves by patching XML
br_model.py      Table model, dropdown delegate, undo commands
br_compare.py    File comparison engine and difference report window
br_editor.py     Main window — run this file
quick_start.bat  Launcher: installs Python/packages if needed, then runs
build_exe.bat    Packages everything into a standalone .exe
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
