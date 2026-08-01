# Battle Realms Data Editor (XLSX) - project context

## Language convention (IMPORTANT)

- **Everything shipped is English.** Source code, identifiers, comments, docstrings,
  commit messages, `README.md`, and - above all - every string the user sees in the
  GUI (window titles, menus, buttons, tooltips, status bar, dialogs, error messages).
  No Vietnamese in the product, ever.
- **The user writes prompts in Vietnamese or English.** Reply in the language they
  used. This never changes what goes into the code: the answer may be Vietnamese,
  the code and UI stay English.
- No i18n/translation layer is planned. Do not add `.ts`/`.qm` files, `tr()` wrappers,
  or a locale system unless explicitly asked.

## Punctuation: no em dashes

Use a plain hyphen `-`, never an em dash `—`. Em dashes read as AI-written text, and
the user does not want them anywhere: GUI strings, code comments, docstrings,
`README.md`, `CLAUDE.md`, or chat replies. The same goes for en dashes `–`.

The enum label separator is therefore `' - '` - see `EnumTable.label()` in
`brde/core.py`, `SheetModel.data()` and `EnumDelegate.createEditor()` in `brde/model.py`,
and `DiffModel._label()` in `brde/compare.py`. All four must agree.

`coerce()` in `brde/model.py` parses that label back into a code, and two rules keep it
safe. It splits on `' - '` **with the surrounding spaces**, never a bare `-`, so a
negative code such as `-1 - NONE` keeps its sign; and it only strips the label when
the text before the separator really parses as a number, so a plain string value like
`Foo - Bar` is left alone. It still accepts the legacy `' — '` form so values copied
from an older build, or from a `.csv` exported by one, still paste correctly - that is
the one intentional em dash left in the codebase. Do not "clean it up".

## What this is

A PyQt6 desktop editor for `Battle Realms.xlsx`, the spreadsheet format that replaced
the game's old `.dat` files (which is why the original Battle Realms Data Editor no
longer works). Python 3.9+, PyQt6, openpyxl. Not a git repository.

Run the tests with `python -m unittest discover -s tests` before calling any change
done. They cover schema inference, the XML writer, value coercion, the detail page
and the main window driven headlessly - 94 tests, about a minute.

## Modules

| File | Role |
|---|---|
| `brde/schema.py` | Pure logic, no Qt/IO. Infers which columns reference which `Enum_*` sheet. |
| `brde/core.py` | Reads the workbook (openpyxl) and saves by patching XML inside the .xlsx zip. |
| `brde/model.py` | `SheetModel`, `EnumDelegate`, `RowFilter`, undo commands. |
| `brde/detail.py` | "View details" window: record search, per-record stat page, cross-sheet lookups. |
| `brde/compare.py` | Diff engine + non-modal difference report dialog. |
| `brde/about.py` | About dialog. Holds `CHANGELOG`, the single source of truth for the version history. |
| `brde/app.py` | `MainWindow`, wiring everything together. |
| `br_editor.py` | Launcher at the top level. Fixes `sys.path`, calls `brde.app.main()`, turns a missing dependency into a readable message. Keep the name: `quick_start.bat`, shortcuts and the PyInstaller build all refer to it. |
| `tests/` | `unittest` suite, no third-party test runner. Workbook-dependent tests skip themselves when `Battle Realms.xlsx` is absent. |
| `quick_start.bat` | Launcher: installs Python/packages if missing, then runs the editor. |
| `build/build_exe.bat` | Installs PyInstaller if needed and builds a standalone .exe. Lives in `build/` but builds the project one level up, so it `cd`s to `%~dp0..` first. Optional `build/icon.ico` is picked up automatically. |

Import direction is one-way: `brde.app` → `brde.compare`, `brde.detail`, `brde.core`,
`brde.model` → `brde.core` → `brde.schema`. Keep it that way; `brde/schema.py` must stay free
of Qt, and `brde/detail.py` must not import `brde.app`.

## The detail window (`brde/detail.py`)

`build_sections(book, sheet, row)` returns the page for one record as `Section`s of
`Field` (an editable line pointing at a real cell) and `Note` (a read-only line).
A `Field` always carries a real `(sheet, row, col)`, which is what makes fields
pulled in from a *referenced* record editable too - a weapon's damage shown on a
unit's page edits `Data_Weapons`.

Layout comes from `PROFILES`, keyed by sheet: a list of `(title, spec)` where `spec`
is a list of column names, or a callable `(book, sheet, row) -> [items]` when the
layout has to be computed (the six building training slots, "trained at"). Any column
a profile does not mention lands in "Other fields", so nothing is ever hidden. Sheets
with no profile get a fully generic page.

`build_sections` guarantees each cell appears once. A profile column is marked used
when it is emitted, a callable's own-sheet fields are marked used from what it
returns, and an `_expand` target that was already expanded prints "Same as
&lt;column&gt;" instead of repeating the stats - units routinely name the same weapon
under both `MeleeWeapon` and `SecondaryWeapon`. Anything still unused lands in "Other
fields", which is what keeps the "nothing is hidden" promise; unused building
training slots show up there by design.

Two invariants:

- The window never edits the book itself. `DetailModel.setData` calls back into
  `MainWindow._on_detail_edit`, which coerces the value and pushes a
  `SetValueCommand`, so the undo stack, the dirty count and the yellow highlight all
  behave as if the edit had been typed into the grid.
- Two-way sync runs on `SheetModel.valueChanged`, which `MainWindow._model_for` wires
  to `_on_value_changed`. That fires for grid edits, pastes and undos alike, and
  refreshes the open detail page. Do not connect `dataChanged` for this - it does not
  carry the cell coordinates.

`RecordIndex` ranks matches by how the text matched (exact, word-prefix, substring)
and then by `SHEET_RANK`. Without the sheet ranking, typing "samurai" puts particle
effects above the Dragon Samurai unit, because their names start with the word.

## Building the .exe

`build/build_exe.bat` deliberately keeps PyInstaller out of `build/` itself:
`--workpath` and `--specpath` point at `build/_work`, and `--distpath` at
`dist/` in the project root. Without that, PyInstaller's default work directory
*is* `build/`, which would bury `build_exe.bat` and `icon.ico` in generated files
and make the whole folder unsafe to ignore in git. `.gitignore` therefore ignores
`build/_work/`, never `build/`.

Pass `1` or `2` as an argument for a non-interactive build (one folder / single
file); the script then skips both the question and every `pause`, which is what
makes it testable.

## Releasing a version

Three things must agree, and a test enforces the first two:

1. `__version__` in `brde/__init__.py`
2. `CHANGELOG` in `brde/about.py` - newest entry first, and the current version
   must appear in it
3. The "Version history" section of `README.md`, a shortened copy for people
   reading the project on the web

The author credit shown in the About dialog is `AUTHOR` in `brde/about.py`:
`@anldori  [VN]DaoAnhDuy`. Do not change it.

## Key design decisions - do not break these

**1. Saving never rewrites the workbook with openpyxl.**
`BRWorkbook.save()` opens the `.xlsx` as a ZIP, regex-patches only the `<c>` cell
elements that actually changed, appends new `sharedStrings` entries (fixing up
`count`/`uniqueCount`), and repacks preserving each entry's original
`compress_type`, `date_time` and attribute bits. Untouched parts stay byte-for-byte
identical so the game reads the file exactly as before. Rewriting with openpyxl would
regenerate the whole file and drop formatting - never do it.

**2. Edits live in an overlay, not in the row data.**
`BRWorkbook.edits: {(sheet, row0, col0) -> value}` with a parallel `original` map.
`SheetData.rows` keeps the on-disk values until a successful save. Always read cells
through `book.value(sheet, row, col)` so pending edits are visible; never read
`sd.rows[r][c]` directly outside `brde.core`. `set_value` deletes the entry when the
value is edited back to its original, so `book.dirty` stays exact.

**3. Enum mapping is inferred, and every candidate is coverage-checked.**
The workbook carries no data-validation rules. `infer_column_enum()` runs five stages:
primary-key column → `EXPLICIT_RULES` regexes → numeric blacklist → CamelCase token
matching with sheet-name prefixing → 0/1 fallback to `@bool`. A candidate is accepted
only if every value present in the column exists in the enum table (`-1` always
allowed as "none"). Keep that check on any new rule - a name that merely looks right
must still lose to the data.

**4. Coordinates are 0-based data-area indices; Excel rows are `row0 + 2`.**
Row 1 is the header. The vertical header, tooltips, the compare report and
`_patch_sheet` all apply the `+ 2`. Enum sheets are loaded twice: once as lookup
tables in `book.enums` (keyed without the `Enum_` prefix), once as ordinary
browsable/editable sheets in `book.sheets` (keyed with it).

**5. All mutations go through the undo stack.**
Push `SetValueCommand` or `MultiSetCommand`; never call `book.set_value()` straight
from the UI, or Ctrl+Z desyncs.

## Data conventions in the workbook

- Sheets are prefixed `Data_*` (records), `Enum_*` (code tables), plus a few
  `MapEditor*` others. Column 0 of a `Data_*` sheet is normally its primary key.
- `-1` means "none / invalid" in most enum columns.
- Red cells = code not present in the enum table. `Data_UnitSpeechFXEvents.Type` and
  `Data_UnitToWarPartyEffectivenes.Type` are like that in the vanilla file already -
  that is the game's own data, not a bug.

## Gotchas

- A real `Battle Realms.xlsx` sits in this directory (201 sheets, 90 `Data_*`), so
  changes can be verified against actual data. Do not edit or overwrite it - the
  tests copy it to a temporary directory before saving anything.
- The GUI can be driven headlessly for testing with `QT_QPA_PLATFORM=offscreen`;
  `MainWindow.open_file()` and `DetailWindow` both work that way.
- The coverage check in `brde/schema.py` is weak for 0/1 columns, since they pass
  against almost any enum. That is why the armour-multiplier and yes/no rules run
  before name matching.

## Running

```bash
python br_editor.py                                  # welcome screen
python br_editor.py "C:\path\to\Battle Realms.xlsx"  # open a file directly
python -m brde                                       # same thing, as a module
python -m unittest discover -s tests                 # the test suite
```
