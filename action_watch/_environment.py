import os

from dotenv import load_dotenv

from ._paths import CONFIG_DIR

DOTENV = CONFIG_DIR / '.env'

DOTENV_TEMPLATE = '''
# Path to search recursively for `.github/workflows/*.yml` files.
# If empty or not set, falls back to current working directory.
# Example: ~/projects/python/
ACTION_WATCH_DISCOVERY_ROOT={}

# Git credential helper command to be used by an authentication handler to authenticate to GitHub.
# See https://pypi.org/project/helper-auth/ for more info.
# Example: git credential-github
ACTION_WATCH_AUTH_HELPER={}

# String to be used as the Authorization header of HTTP requests to authenticate to GitHub.
# Ignored if ACTION_WATCH_AUTH_HELPER is set.
# Example: Bearer YourGitHubToken
ACTION_WATCH_AUTH_HEADER={}

# The following are boolean flags. Use 0 or 1.

# Cache the paths of the discovered workflow files.
ACTION_WATCH_CACHE_PATHS={}

# Cache the GitHub API requests and responses.
ACTION_WATCH_CACHE_REQUESTS={}

# Output debug messages to stderr.
ACTION_WATCH_DEBUG={}
'''.lstrip()


def _setup_env():
    _process_dotenv(DOTENV)


def _process_dotenv(dotenv_path):
    """If the `dotenv_path` file exists, load it into environment.
    Otherwise, create the `dotenv_path` file based on existing
    environment variables, if any.
    """
    if dotenv_path.is_file():
        load_dotenv(dotenv_path)
    else:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        dotenv_path.write_text(
            DOTENV_TEMPLATE.format(
                _get_env_string('DISCOVERY_ROOT'),
                _get_env_string('AUTH_HELPER'),
                _get_env_string('AUTH_HEADER'),
                _get_env_string('CACHE_PATHS'),
                _get_env_string('CACHE_REQUESTS'),
                _get_env_string('DEBUG'),
            ),
            encoding='utf8',
        )


def _get_env_flag(key):
    """Return False if the environment variable is not set, empty or '0'.
    Return True otherwise.
    """
    value = os.getenv(f'ACTION_WATCH_{key}')
    return bool(value) and value != '0'


def _get_env_string(key):
    return os.getenv(f'ACTION_WATCH_{key}', '')
