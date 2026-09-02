# Changelog

Also shown in **Help ▸ About**, which is the authoritative copy - it is generated from
`CHANGELOG` in `brde/about.py`.

## 1.5.0 (current)

- **Open the game's old `.dat` file.** *File ▸ Open old .dat file…* reads
  `Battle Realms.dat`, the format the spreadsheet replaced, so an old mod can still be
  read without the original editor.
- **It opens read-only.** Browse every sheet, search for a record, compare two units,
  and diff it against a workbook - but nothing in it can be edited or saved. The title
  bar says so while one is open.
- Everything else works on it unchanged: dropdowns instead of code numbers, colour
  previews, and the record page.

## 1.4.0

- **A colour picker built for this file**, in place of the system panel's grid of 48
  fixed colours. A large picking surface, a proper hex field, and a screen picker that
  lifts a colour straight off a screenshot of the game.
- **The colours already in the sheet are shown beside the one being picked**, with the
  row you are editing ringed among them. Choosing a team colour is about telling it
  apart from the other ten, which can only be judged next to them. Click one to take it.
- **A warning when two colours are about to be confused**, naming the row it clashes
  with. Set just under the closest pair the game itself ships, so the unmodified file
  stays silent.
- The old colour sits beside the new one while you pick. Click it to put it back.
- Transparency has a slider of its own over a checkerboard. The system picker had no
  alpha channel at all.

## 1.3.0

- **Colours look like colours.** A colour in this file is three or four separate number
  columns, so a band of the colour now runs along the bottom of the cells that make it.
- **Pick a colour instead of typing three numbers.** Right-click it in the grid, or
  double-click it on a record page. One undo step, and only the channels that actually
  changed are written.
- **A record that stores more than one colour sets them together.** A team colour and
  its minimap colour come from one dialog, and the menu entry names every colour it
  will overwrite.
- A record page with colours opens with them, shown as a bar with the hex code across
  it. The channels stay below as editable fields.
- Transparency is drawn over a checkerboard, so a faint colour is not mistaken for a
  blank one.

## 1.2.1

- **Fixed: the unit comparison used weapons the fight never reaches.** A Dragon Samurai
  against a Serpent Ronin was scored with the samurai's arrow, which needs 7 clear and
  is never fired at something that close. It swings its katana now.
- **The comparison runs once per distance** - one table at range, one in melee - and
  every weapon says which of the two it is in.
- **A unit that wins at one distance and loses at the other is no longer given the
  win.** The verdict names both and says where each one wins.
- The window opens empty instead of comparing the first two units in the list before
  being asked.
- A standing note that the verdict is for reference: the file holds no attack speed,
  reach, formation or terrain.

## 1.2.0

- **Compare two units.** *Compare ▸ Compare units…* (`Ctrl+U`) puts cost, health, all
  six armour multipliers and every weapon side by side, with a sentence naming the
  winner.
- **The counter is worked out for you.** An armour multiplier scales the damage a unit
  *takes*, so above 1 is a weakness - backwards from most games. The page gives the
  damage that lands and the hits to kill, rather than leaving it to be read the wrong
  way round.
- **Techniques are applied**, so you compare units as they are actually fielded. Every
  value a technique moved is shown as `450 -> 630`. Untick to see the file as written.
- Green is good for the unit in that column and red is bad for it. The comparison
  follows your edits live and exports to CSV.

## 1.1.1

- **Abilities on the record page.** A unit's innate abilities, the ability each piece
  of battle gear grants, its spells, and every technique that affects it - each with
  its own stats, editable in place.
- **Buildings show what they research.** A tavern or a dojo now lists its techniques
  and upgrades with cost, time and affected units, plus the buildings needed first.
- **Records are findable by their real name.** Most sheets do not call the name column
  `Name`, so "Dragon Skin" and "Sight Beyond Sight" used to find nothing. The record
  you meant still ranks first.
- **Several columns were reading from the wrong list.** Weapon and upgrade classes,
  technique effects, battle gear, and ten yes/no switches that had turned into
  dropdowns of units. All of them now show what they mean.
- Less repetition under "Referenced by", and the window carries the program icon in the
  title bar and on the taskbar.

## 1.1.0

- **Compare two files.** Diff your mod against vanilla, or two versions of your own
  work. Rows are matched by their key rather than by position, so inserting a record no
  longer reports every row below it as changed. Differences can be filtered, exported,
  and taken back into your file as ordinary undoable edits.
- **Record details.** Search a unit or building by name and read every stat on one
  page, including the weapon damage that lives in another sheet. Everything on the page
  is editable in place.

## 1.0.0

- First release. Browse and edit every sheet, with dropdowns instead of raw code
  numbers, undo and redo, copy and paste, and a save that leaves every part of the file
  you did not touch exactly as it was.
