import pytest

from action_watch._environment import _setup_env


@pytest.fixture
def existing_dotenv(tmp_path):
    path = tmp_path / '.env'
    path.write_text('ACTION_WATCH_DEBUG=foo\n', encoding='utf8')
    return path


@pytest.fixture
def missing_dotenv(tmp_path):
    return tmp_path / '.env'


def test_setup_env_existing_dotenv_existing_env_var(
        monkeypatch, mocker, existing_dotenv
):
    """Value in the '.env' file is not overwritten by an existing
    environment variable.
    """
    monkeypatch.setenv('ACTION_WATCH_DEBUG', 'bar')
    mocker.patch('action_watch._environment.DOTENV', existing_dotenv)
    _setup_env()

    assert 'ACTION_WATCH_DEBUG=foo\n' in existing_dotenv.read_text()


def test_setup_env_missing_dotenv_existing_env_var(monkeypatch, mocker, missing_dotenv):
    """Value of an existing environment variable is written to the newly
    created '.env' file.
    """
    monkeypatch.setenv('ACTION_WATCH_DEBUG', 'baz')
    mocker.patch('action_watch._environment.DOTENV', missing_dotenv)
    _setup_env()

    assert 'ACTION_WATCH_DEBUG=baz\n' in missing_dotenv.read_text()


def test_setup_env_missing_dotenv_no_env_var(mocker, missing_dotenv):
    """Empty value is written to the newly created '.env' file."""
    mocker.patch('action_watch._environment.DOTENV', missing_dotenv)
    _setup_env()

    assert 'ACTION_WATCH_DEBUG=\n' in missing_dotenv.read_text()
