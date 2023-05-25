import os
import shutil
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DOTENV = files('action_watch') / '.env-default'
CONFIG_DIR = Path.home() / '.config' / 'action-watch'
DOTENV = CONFIG_DIR / '.env'


def _setup_env():
    """Create a default `.env` file if necessary. Load `.env` into
    environment.
    """
    if not DOTENV.is_file():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEFAULT_DOTENV, DOTENV)
    load_dotenv(DOTENV)


def _get_env_flag(key):
    value = os.getenv(f'ACTION_WATCH_{key}')
    return bool(value) and value != '0'


def _get_env_string(key):
    return os.getenv(f'ACTION_WATCH_{key}', '')
