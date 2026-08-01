# Build folder

Everything needed to package the editor into a standalone `.exe`.

## Making a build

Double-click **`build_exe.bat`** and pick a layout:

| | Output | Trade-off |
|---|---|---|
| **1. One folder** | `dist\BattleRealmsDataEditor\` | Starts instantly, about 90 MB. Share the whole folder, or zip it. |
| **2. Single file** | `dist\BattleRealmsDataEditor.exe` | One portable file, about 45 MB. Each launch takes a few seconds to unpack. |

It installs PyInstaller for you on the first run. Neither output needs Python,
PyQt6 or any `.bat` file on the machine it runs on.

For a scripted build, pass the layout as an argument and nothing is asked and
nothing pauses:

```bat
build_exe.bat 1     REM one folder
build_exe.bat 2     REM single file
```

## Using your own icon

Put **`icon.ico`** in this folder. The build picks it up automatically and
embeds it in the executable - no editing of the script needed. A copy in the
project root works too, but the one here wins.

Windows caches icons aggressively; if an old icon lingers on a shortcut, the
file in `dist\` still has the right one.

## What ends up where

- `dist\` - the finished program, in the project root
- `build\_work\` - PyInstaller's intermediate files and the generated `.spec`

Both are throwaway and are ignored by git. Delete them whenever you like.
