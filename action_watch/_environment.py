import os

from dotenv import load_dotenv

from ._paths import CONFIG_DIR

DOTENV = CONFIG_DIR / '.env'

DEFAULT_DOTENV = '''
# Path to search recursively for `.github/workflows/*.yml` files.
# If empty or not set, falls back to current working directory.
# Example: ~/projects/python/
ACTION_WATCH_DISCOVERY_ROOT=

# Git credential helper command to be used by an authentication handler to authenticate to GitHub.
# See https://pypi.org/project/helper-auth/ for more info.
# Example: git credential-github
ACTION_WATCH_AUTH_HELPER=

# String to be used as the Authorization header of HTTP requests to authenticate to GitHub.
# Ignored if ACTION_WATCH_AUTH_HELPER is set.
# Example: Bearer YourGitHubToken
ACTION_WATCH_AUTH_HEADER=

# The following are boolean flags. Use 0 or 1.

# Cache the paths of the discovered workflow files.
ACTION_WATCH_CACHE_PATHS=1

# Cache the GitHub API requests and responses.
ACTION_WATCH_CACHE_REQUESTS=1

# Output debug messages to stderr.
ACTION_WATCH_DEBUG=0
'''.lstrip()


def _setup_env():
    """Create a default `.env` file if necessary. Load `.env` into
    environment.
    """
    if not DOTENV.is_file():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DOTENV.write_text(DEFAULT_DOTENV, encoding='utf8')
    load_dotenv(DOTENV)


def _get_env_flag(key):
    value = os.getenv(f'ACTION_WATCH_{key}')
    return bool(value) and value != '0'


def _get_env_string(key):
    return os.getenv(f'ACTION_WATCH_{key}', '')
