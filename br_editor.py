#!/usr/bin/env python3
r"""
Battle Realms Data Editor (XLSX) - launcher.

The code lives in the `brde` package next to this file; this script only makes
sure that package can be imported and then hands over to it. It stays here
because `quick_start.bat`, the shortcuts people make and the PyInstaller build
all refer to `br_editor.py` by name.

Run:  python br_editor.py  [path\to\Battle Realms.xlsx]
"""
import os
import sys

# Works when launched from any directory, and from inside a PyInstaller bundle.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fail(message):
    """Report a startup problem in a dialog if we can, on the console if not."""
    sys.stderr.write(message + '\n')
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, 'Battle Realms Data Editor', message)
    except Exception:
        pass
    return 1


def main():
    try:
        from brde.app import main as run
    except ImportError as e:
        missing = getattr(e, 'name', '') or ''
        if missing.split('.')[0] in ('PyQt6', 'openpyxl'):
            return _fail(
                f'A required package is missing: {missing}\n\n'
                'Install the dependencies with:\n'
                '    pip install -r requirements.txt\n\n'
                'Or just run quick_start.bat, which does it for you.')
        return _fail(f'Could not start the editor: {e}')
    return run()


if __name__ == '__main__':
    sys.exit(main())
