# Slim build spec, driven by build_exe.bat through BRDE_* environment variables.
# Measured with PyInstaller on Python 3.14 / PyQt6 6.11: onefile 38.8 MB -> 23.8 MB.
# The big cuts are opengl32sw.dll (19.7 MB software GL, unused by QtWidgets), Qt6Pdf,
# Qt6Network, Qt6Svg, translations and unused image plugins. QtNetwork is NOT needed:
# update.py uses urllib, which needs the ssl/libcrypto that stay in.
import os
from PyInstaller.utils.hooks import collect_submodules
ROOT = os.environ['BRDE_ROOT']; NAME = os.environ.get('BRDE_NAME', 'BattleRealmsDataEditor')
ONEFILE = os.environ.get('BRDE_ONEFILE') == '1'
ICON = os.environ.get('BRDE_ICON') or None
EXCL = ['PIL','lxml','tkinter','pytest','numpy','pandas','unittest',
        'PyQt6.QtNetwork','PyQt6.QtPdf','PyQt6.QtPdfWidgets','PyQt6.QtSvg','PyQt6.QtSvgWidgets',
        'PyQt6.QtOpenGL','PyQt6.QtOpenGLWidgets','PyQt6.QtDBus','PyQt6.QtPrintSupport',
        'PyQt6.QtQml','PyQt6.QtQuick','PyQt6.QtQuick3D','PyQt6.QtWebEngineCore','PyQt6.QtWebEngineWidgets',
        'PyQt6.QtMultimedia','PyQt6.QtMultimediaWidgets','PyQt6.QtCharts','PyQt6.QtDataVisualization',
        'PyQt6.QtBluetooth','PyQt6.QtNetworkAuth','PyQt6.QtPositioning','PyQt6.QtSensors',
        'PyQt6.QtSerialPort','PyQt6.QtTest','PyQt6.QtSql']
# Files dropped after analysis. Matched on the destination path, case-insensitive.
DROP = ('opengl32sw.dll','d3dcompiler','qt6network','qt6pdf','qt6svg','qt6opengl','qt6dbus','qt6printsupport',
        os.sep+'translations'+os.sep, '/translations/',
        'imageformats/qtiff','imageformats/qwebp','imageformats/qgif','imageformats/qicns','imageformats/qtga',
        'imageformats/qwbmp','imageformats/qsvg','imageformats/qpdf','imageformats\\qtiff','imageformats\\qwebp',
        'imageformats\\qgif','imageformats\\qicns','imageformats\\qtga','imageformats\\qwbmp','imageformats\\qsvg',
        'imageformats\\qpdf','/tls/','\\tls\\','networkinformation','generic','iconengines')
def keep(entry):
    d = entry[0].lower()
    return not any(x in d for x in DROP)

a = Analysis([os.path.join(ROOT,'br_editor.py')], pathex=[ROOT],
             hiddenimports=collect_submodules('openpyxl'), excludes=EXCL)
a.binaries = [e for e in a.binaries if keep(e)]
a.datas = [e for e in a.datas if keep(e)]
if ICON:
    a.datas.append((os.path.basename(ICON), ICON, 'DATA'))
pyz = PYZ(a.pure)
kw = dict(name=NAME, console=False, icon=ICON, upx=False, strip=False)
if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **kw)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **kw)
    COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)

