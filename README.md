# Battle Realms Data Editor (XLSX)

An editor for Battle Realms game data in the newer **`Battle Realms.xlsx`** format that
replaced the old `.dat` files - which is why the original Battle Realms Data Editor no
longer works with current versions of the game.

Browse and edit every sheet with real names instead of raw code numbers, look up a
unit's full stats on one page, compare your mod against vanilla, and save without
damaging the workbook.

---

## Getting started

### Windows - the easy way

Double-click **`quick_start.bat`**. It sets everything up for you:

1. **No Python installed?** It asks first. Answer `Y` and it downloads and installs
   Python 3.12 silently, per-user, so **no administrator rights are needed**. Answer
   `N` and nothing on your computer is touched - you get manual instructions instead.
2. **Missing packages?** PyQt6 and openpyxl are installed on the first run.
3. The editor launches.

You don't need to reopen the window or reboot afterwards - the script picks up the new
Python straight away, and chooses the right installer for your CPU automatically.

### Already have Python (3.9+)

```
pip install -r requirements.txt
python br_editor.py                                  # welcome screen
python br_editor.py "C:\path\to\Battle Realms.xlsx"  # open a file directly
```

<img width="1442" height="892" alt="image" src="https://github.com/user-attachments/assets/8a26321b-3d30-46d1-814c-6d9a4b641734" />


### Opening your file

The app starts on a welcome screen with nothing loaded. Open a file in any of three
ways:

- **File ▸ Open file…** (`Ctrl+O`)
- The **"Open Battle Realms.xlsx…"** button on the welcome screen
- **Drag and drop** a `.xlsx` file onto the window

The last 8 files you opened are remembered and appear under **File ▸ Open recent** and
on the welcome screen.

> Keep a backup copy of the original `Battle Realms.xlsx` before you start modding.
> The editor also writes a `.bak` next to the file every time you save.

<img width="1442" height="892" alt="image" src="https://github.com/user-attachments/assets/e84cf1a9-20d9-442e-9683-19524d830d69" />

---

## Everything about a unit on one page

Press `Ctrl+I` (**Record ▸ Find record…**) and type a name - `samurai`, `dojo`,
`katana`. Pick the record from the list of matches and every number about it is laid
out on a single page, pulled together from sheets that are normally far apart:

- **Cost, health, fatigue, armour, line of sight, terrain speed, battle gear, spells**
- **Weapon damage, range and recovery** - the unit sheet only names the weapon; the
  page follows the reference and shows you the actual numbers
- **Abilities and techniques** - innate abilities, what each piece of battle gear
  grants, and every technique that affects the unit
- **Where it's trained** - which buildings, from which unit, and how long it takes
- **Referenced by** - everything else pointing at this record

Anything not covered by a section still appears under **Other fields**, so no column is
ever hidden from you.

Already on the right row in the grid? `Ctrl+Shift+I`, or right-click the cell.

**The page is fully editable.** Every value, dropdowns included, edits just like the
grid does: yellow highlight, `Ctrl+Z` to undo, `Ctrl+S` to save. When a field belongs to
a referenced record - a weapon's damage, say - the tooltip tells you before you type.

Field names in blue are links: double-click to open that record, **< Back** to return,
**Show in grid** to jump to the row in the main window.

Search puts the obvious answer first. Typing `samurai` matches 45 records - mostly
particle effects and sound events - but the Dragon Samurai unit is at the top.

<img width="1595" height="1016" alt="image" src="https://github.com/user-attachments/assets/d866629e-ca39-40eb-8966-b336b0e80ff3" />

---

## Which unit beats which

**Compare ▸ Compare units…** (`Ctrl+U`) puts two units side by side: cost, health, all
six armour multipliers, and every weapon with its damage class and damage. Both boxes
open empty - nothing is compared until you pick a unit on each side.

> **For reference only.** This compares the numbers in the file. A real fight also turns
> on attack and animation speed, reach and unit size, formation and terrain, stamina,
> abilities, and who strikes first, so treat the verdict as a guide rather than as the
> outcome.

The important thing it does is read the counter out loud. **An armour multiplier scales
the damage a unit takes**, so above 1 is a weakness and below 1 is resistance - backwards
from armour in most games, and the reason the Dragon Spearman's `AMPiercing` of 4.0 makes
it melt under arrow fire.

The **Counter matchup** section runs each unit's weapons against the other's armour and
gives the damage that actually lands and the hits to kill, with a sentence at the top
naming the winner.

**It does this once per distance**, because a weapon is only in the fight at the range it
is used at. A Dragon Samurai carries a katana it swings in contact and an arrow it fires
from 7 to 12 away; a Serpent Ronin never fights further off than 0.5, so the arrow is
never fired at it and the katana is what the melee table holds. There are two tables,
**at range** and **in melee**, and each weapon in the weapon list says which one it
belongs to.

That also means a unit only wins outright when it wins everywhere it can reach. Where the
two units each own a distance, the verdict says so and leaves the fight to whoever gets
the range they want:

> It depends on the range - Dragon Archer wins at range, Dragon Spearman wins in melee. At
> range, Dragon Archer attacks with WEAPON_ARROW, which is piercing, and Dragon Spearman
> takes it at ×4 - 93.6 a hit, 3 hits to kill, and Dragon Spearman cannot reply. In melee,
> Dragon Archer attacks with WEAPON_BOWBASH […]

Green is good for the unit in that column, red is bad for it - in the armour rows and the
matchup rows alike, because each matchup column holds what that unit does *to* the other.

**Techniques are applied by default**, because health, armour and weapon damage all move
once they are researched and the raw sheet values describe units nobody ever fields. Every
value a technique moved is shown as `450 -> 630`; untick **Apply techniques** to see the
file as written.

Right-click a row in `Data_Units` to load that unit straight in, edit any cell in the main
window and the verdict recomputes, and **Export to CSV…** saves the whole comparison.

<img width="1388" height="960" alt="image" src="https://github.com/user-attachments/assets/0fc40b0c-0d4b-46f8-ad0a-a709f30d8bd8" />

---

## Comparing two files

**Compare ▸ Compare with another file…** (`Ctrl+D`) reports every difference between
your open file and a second `.xlsx`. Useful for diffing your mod against vanilla, or two
versions of your own work.

From the report you can:

- **Filter** by sheet, status, or free text - text search matches names as well as
  codes, so typing `geisha` finds a row even though the cell holds a number
- **Double-click** any row to jump to that cell in the grid
- **Take other value** - copy their value into your file as a normal, undoable edit
- **Export to CSV**

Differing cells are also tinted purple in the grid, with both values in the tooltip.
Use **Clear comparison** to remove the tint.

Two things that make the report readable: rows are matched by their `Type` key rather
than by position, so inserting a record near the top of a sheet reports only that
record - not every row below it. Columns are matched by header name, so a column
inserted in the middle doesn't shift everything after it.

The comparison includes your unsaved edits, and warns you before it starts.

---

## Features

| Feature | What it does |
| --- | --- |
| **Record details** | `Ctrl+I`. Search a unit or building by name and read every stat on one page, weapon damage included. Editable in place. |
| **Unit vs unit** | `Ctrl+U`. Two units side by side, with the counter worked out from damage class against armour multiplier, and techniques applied. |
| **Dropdowns instead of raw numbers** | 546 reference columns are detected automatically. Pick `17 - WEAPON_BOWBASH` from a list instead of looking the number up by hand. |
| **Type to search the dropdown** | Long lists - 2,900 sound codes, for example - filter as you type, matching any part of the name. |
| **Show enum descriptions** | The grid shows `0 - UNIT_D_ARCHER` instead of `0`. Untick to see raw codes. |
| **Row filter** | The "Filter rows" box matches both codes and names. |
| **Undo / Redo** | `Ctrl+Z` / `Ctrl+Y`, unlimited depth. |
| **Edited cells highlighted** | Edits turn yellow; hover to see the original value. `Ctrl+E` lists every edit and jumps to it. |
| **Jump to referenced record** | Right-click an enum cell → "Go to Data_Weapons" or "Open code table Enum_WeaponType". |
| **Invalid code warning** | Codes that don't exist in the enum table are shown in red. |
| **Copy / Paste** | `Ctrl+C` / `Ctrl+V` over a range, tab-separated so it round-trips with Excel. |
| **Add row** | `Ctrl+Shift+N` appends a row to the current sheet. |
| **Quick sheet switching** | `Ctrl+P` to type a sheet name, or use the searchable list on the left. |
| **Open recent** | The last 8 files are remembered between sessions. |
| **Automatic backup** | Every save first creates `Battle Realms.xlsx.YYYYMMDD_HHMMSS.bak`. |

---

## Menu bar

| Menu | Contents |
| --- | --- |
| **File** | Open file… · Open recent ▸ · Save · Save As… · Close file · Exit |
| **Edit** | Undo · Redo · Copy · Paste · Clear cells · Revert to original · Add row |
| **View** | Show enum descriptions · Filter rows · Go to sheet… · List edited cells |
| **Record** | Find record… (`Ctrl+I`) · Details for the selected row (`Ctrl+Shift+I`) |
| **Compare** | Compare with another file… (`Ctrl+D`) · Compare with last file again · Show last report · Clear comparison · Compare units… (`Ctrl+U`) · Compare this unit with… (`Ctrl+Shift+U`) |
| **Help** | How to use (`F1`) · About |

---

## Your file stays intact

Saving does **not** rewrite the workbook from scratch. The editor patches the XML inside
the `.xlsx` archive directly, touching only the cells you actually changed and repacking
with the original entry order and compression.

In testing, editing 107 cells across 9 sheets changed only 10 parts of the archive - the
other **191 parts were byte-for-byte identical to the original**. Sheet count, styles,
layout, column widths and frozen panes all survive untouched.

---

## Sharing it with someone who doesn't have Python

Double-click **`build\build_exe.bat`**. It installs PyInstaller if needed and asks which
layout you want:

| Mode | Output | Trade-off |
| --- | --- | --- |
| **One folder** (recommended) | `dist\BattleRealmsDataEditor\` | Starts instantly. ~90 MB. Share the folder or zip it. |
| **Single file** | `dist\BattleRealmsDataEditor.exe` | One portable file, ~45 MB. Takes a few seconds to launch. |

Neither output needs Python, PyQt6 or the `.bat` files on the target machine. Drop an
`icon.ico` into the `build` folder and it's embedded automatically. For a scripted
build, pass the layout as an argument: `build_exe.bat 1` or `build_exe.bat 2`.

### If your antivirus flags the .exe

Windows Defender, and occasionally one or two smaller scanners, report the prebuilt
`.exe` from the Releases page as `Trojan:Win32/Wacatac.B!ml` or something similarly
generic. **It is a false positive.** At the time of writing 3 of 70 engines on
VirusTotal flag it, all three by machine learning rather than by an actual signature
(note the `!ml` suffix Microsoft puts on a guess), while 67 engines including
Kaspersky, ESET, BitDefender, Avast, Symantec, Sophos, Trend Micro and CrowdStrike
report it clean, and VirusTotal's own sandbox rates the observed behaviour clean at
97% confidence.

The cause is the shape of the file rather than anything it does. A PyInstaller
single-file build is a small executable with a ~38 MB compressed archive glued to the
end of it, which it unpacks into a temporary folder on every launch and deletes on
exit. Unsigned, near-maximum entropy, self-extracting, deletes its own files
afterwards, and brand new so no scanner has ever seen a copy before: that is exactly
the profile heuristics are trained to distrust, and every legitimate PyInstaller app
runs into it.

For what it is worth, the editor opens no network connections at all - there is no
networking code in the source - and writes nothing outside the workbook you open and
the `.bak` beside it. If you would rather not take that on trust:

- **Run it from source instead.** `quick_start.bat`, or `python br_editor.py`.
- **Build the `.exe` yourself** with `build\build_exe.bat`. **One folder** mode is
  flagged far less often than single file, because nothing is packed or unpacked.
- **Check the current verdicts yourself.** The released binary is SHA256
  `60d900c61f1de793ed23553467c344d8b19e8bb98ef092431eb6c48565f8089c` -
  [see it on VirusTotal](https://www.virustotal.com/gui/file/60d900c61f1de793ed23553467c344d8b19e8bb98ef092431eb6c48565f8089c).

---

## Good to know

- A code of `-1` means "none / invalid" in most columns.
- A red cell means the code isn't in the enum table. The original game file already
  contains two such columns (`Data_UnitSpeechFXEvents.Type` and
  `Data_UnitToWarPartyEffectivenes.Type`) - that's the game's own data, not a bug in
  the tool.
- Written in Python + PyQt6. See the source under `brde/` if you want to dig deeper.
- Version history is in [CHANGELOG.md](CHANGELOG.md), and in **Help ▸ About**.
