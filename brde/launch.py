r"""
brde.launch - works out how to start the game from the file being edited.

There is no configured game path anywhere in this program, and that is on
purpose: the file being edited already says where the game is. `Battle
Realms.xlsx` is read by the game out of its own install folder, so the folder
the open file sits in is the one piece of evidence that cannot be stale.

The rule, in order:

1. If the open file is anywhere inside the Steam copy of the game, start it
   through Steam - `steam://rungameid/1025600`. Steam owns the DRM check, the
   overlay, achievements and cloud saves, and going around it either fails or
   quietly loses those.
2. Otherwise look for a game executable beside the file, then in the folders
   just above it, and run that one directly. This is the case for the older
   1.5x builds, which never came from Steam at all.
3. Otherwise nothing is found, and the caller says so rather than guessing.

Step 2 walks up `PARENT_LEVELS` folders because a workbook is very often kept
in a `mod\...` subfolder of the game rather than loose in it. It stops at the
drive root and only accepts an exact executable name, so it cannot wander into
an unrelated game.

No Qt and nothing from the rest of the package: this module only answers "what
should be started, and how", and `brde.app` is what actually starts it. That
keeps the registry reading and the .vdf parsing testable with no display.
"""
from __future__ import annotations

import os
import re
from collections import namedtuple

try:
    import winreg
except ImportError:          # not Windows - there is no Steam registry to read
    winreg = None

# Battle Realms: Zen Edition. The older retail builds have no app id at all,
# which is exactly why step 2 above exists.
APP_ID = '1025600'

# Zen Edition ships the first name; the 1.5x builds use one of the others.
# Matched case-insensitively but as whole names, never as a prefix.
GAME_EXES = ('Battle_Realms_F.exe', 'Battle Realms F.exe',
             'BattleRealms.exe', 'Battle Realms.exe')

MAP_EDITOR_EXES = ('WorldMaster.exe',)

# How far above the file's own folder to look for the executable.
PARENT_LEVELS = 3

# kind is 'steam', 'exe' or 'none'.
#   steam: start `url`, `folder` is the install directory
#   exe:   start `exe` with `folder` as the working directory
#   none:  nothing was found; `folder` is where we looked first
Target = namedtuple('Target', 'kind folder exe appid')

_KV = re.compile(r'"([^"]+)"\s+"([^"]*)"')


def _kv_pairs(text):
    """Every "key" "value" pair in a Valve .vdf/.acf file, nesting ignored.

    Both files this module reads have the key it wants at exactly one place,
    so the tree they describe never has to be built.
    """
    for m in _KV.finditer(text):
        # Paths in a .vdf are written with doubled backslashes.
        yield m.group(1), m.group(2).replace('\\\\', '\\')


def _read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except OSError:
        return None


def steam_root():
    """Steam's own install folder, or None if Steam is not installed here."""
    if winreg is None:
        return None
    for hive, key, name in (
            (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam',
             'InstallPath'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam',
             'InstallPath')):
        try:
            with winreg.OpenKey(hive, key) as k:
                value, _ = winreg.QueryValueEx(k, name)
        except OSError:
            continue
        if value and os.path.isdir(value):
            return os.path.normpath(value)
    return None


def library_folders(root=None):
    """Every Steam library on this machine, the install folder included.

    Games are commonly moved off the system drive, so the library that holds
    Battle Realms is often not the one Steam itself lives in.
    """
    root = root or steam_root()
    if not root:
        return []
    out = [os.path.normpath(root)]
    seen = {os.path.normcase(out[0])}
    text = _read(os.path.join(root, 'steamapps', 'libraryfolders.vdf'))
    if not text:
        return out
    for key, value in _kv_pairs(text):
        if key.lower() != 'path' or not value:
            continue
        path = os.path.normpath(value)
        if os.path.normcase(path) in seen or not os.path.isdir(path):
            continue
        seen.add(os.path.normcase(path))
        out.append(path)
    return out


def app_dirs(appid=APP_ID, root=None):
    """Where Steam has installed `appid`, across every library."""
    dirs = []
    for lib in library_folders(root):
        text = _read(os.path.join(lib, 'steamapps',
                                  'appmanifest_%s.acf' % appid))
        if not text:
            continue
        for key, value in _kv_pairs(text):
            if key.lower() != 'installdir' or not value:
                continue
            path = os.path.join(lib, 'steamapps', 'common', value)
            if os.path.isdir(path):
                dirs.append(os.path.normpath(path))
            break
    return dirs


def is_inside(child, parent):
    """True if `child` is `parent` or sits under it.

    The separator matters: without it "Battle Realms 2" reads as being inside
    "Battle Realms", and the wrong game gets launched.
    """
    if not child or not parent:
        return False
    try:
        c = os.path.normcase(os.path.abspath(child))
        p = os.path.normcase(os.path.abspath(parent)).rstrip(os.sep)
    except (OSError, ValueError):
        return False
    return c == p or c.startswith(p + os.sep)


def find_exe(folder, names=GAME_EXES):
    """The first of `names` present in `folder`, matched without case."""
    if not folder or not os.path.isdir(folder):
        return None
    try:
        listing = {n.lower(): n for n in os.listdir(folder)}
    except OSError:
        return None
    for want in names:
        real = listing.get(want.lower())
        if real:
            return os.path.join(folder, real)
    return None


def folders_up(folder, levels=PARENT_LEVELS):
    """`folder`, then up to `levels` folders above it, stopping at the root."""
    out = []
    cur = os.path.abspath(folder)
    for _ in range(levels + 1):
        out.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return out


def steam_url(appid=APP_ID):
    return 'steam://rungameid/%s' % appid


def resolve(path, appid=APP_ID, root=None):
    """How to start the game that owns `path`. Never raises; see `Target`."""
    if not path:
        return Target('none', None, None, None)
    folder = os.path.dirname(os.path.abspath(path))

    for installed in app_dirs(appid, root):
        if is_inside(folder, installed):
            return Target('steam', installed, find_exe(installed), appid)

    for cand in folders_up(folder):
        exe = find_exe(cand)
        if exe:
            return Target('exe', cand, exe, None)

    return Target('none', folder, None, None)
