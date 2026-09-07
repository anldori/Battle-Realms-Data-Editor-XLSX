"""Check for updates from GitHub releases."""
import json
import urllib.error
import urllib.request
from typing import NamedTuple

from . import __version__


class Release(NamedTuple):
    version: str
    name: str
    url: str
    is_newer: bool


REPO = 'anldori/Battle-Realms-Data-Editor-XLSX'
API_URL = f'https://api.github.com/repos/{REPO}/releases/latest'
RELEASES_URL = f'https://github.com/{REPO}/releases'


def _parse_version(v: str) -> tuple[int, ...]:
    """Convert '1.6.0' to (1, 6, 0) for comparison."""
    try:
        return tuple(int(x) for x in v.lstrip('v').split('.'))
    except (ValueError, AttributeError):
        return ()


def check_for_updates() -> Release | None:
    """Query GitHub API for latest release. Returns None on error."""
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as response:
            data = json.loads(response.read().decode())

        tag_name = data.get('tag_name', '').lstrip('v')
        current = _parse_version(__version__)
        latest = _parse_version(tag_name)

        if not tag_name or not latest:
            return None

        return Release(
            version=tag_name,
            name=data.get('name', tag_name),
            url=RELEASES_URL,
            is_newer=latest > current
        )
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TypeError):
        return None
