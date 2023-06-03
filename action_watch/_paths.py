from pathlib import Path

import platformdirs

CACHE_DIR = platformdirs.user_cache_path('action-watch')
CONFIG_DIR = platformdirs.user_config_path('action-watch')


def _abs_path(path):
    return Path(path).expanduser().resolve()
