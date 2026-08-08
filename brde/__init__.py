"""
Battle Realms Data Editor (XLSX).

Editor for the `Battle Realms.xlsx` game data file that replaced the old .dat
files. Run it with `python br_editor.py` or `python -m brde`.

Module layout, in dependency order - nothing here imports anything above it:

    schema     which columns reference which Enum_* table (pure logic, no Qt)
    matchup    unit versus unit: armour, damage classes, counters (no Qt either)
    core       reads the workbook, saves by patching the XML inside the .xlsx zip
    model      grid table model, dropdown delegate, undo commands
    detail     record search and the per-record stat page
    compare    diff engine and the difference report window
    matchup_ui the unit comparison window, drawing what matchup works out
    app        the main window, wiring all of the above together
"""

__version__ = '1.2.1'
__all__ = ['__version__']
