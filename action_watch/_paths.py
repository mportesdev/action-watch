from pathlib import Path

HOME_DIR = Path.home()
CACHE_DIR = HOME_DIR / '.cache' / 'action-watch'
CONFIG_DIR = HOME_DIR / '.config' / 'action-watch'


def _abs_path(path):
    return Path(path).expanduser().resolve()
