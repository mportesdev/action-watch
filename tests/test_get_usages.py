import pytest

from action_watch import _get_usages


@pytest.fixture
def root_dir(tmp_path):
    path = tmp_path / 'root'
    path.mkdir()
    return path


@pytest.fixture
def discovered_file(root_dir):
    subdir = root_dir / '.github' / 'workflows'
    subdir.mkdir(parents=True)
    file = subdir / '1.yml'
    file.write_text(
        'foo:\n'
        '  bar:\n'
        '  - uses: owner1/repo1@v1\n',
        encoding='utf8',
    )
    return file


@pytest.fixture
def cached_file(tmp_path):
    file = tmp_path / '2.yml'
    file.write_text(
        'foo:\n'
        '  bar:\n'
        '  - uses: owner2/repo2@v2\n',
        encoding='utf8',
    )
    return file


@pytest.fixture
def existing_path_cache(tmp_path, cached_file):
    path = tmp_path / 'files.yaml'
    path.write_text(f'- {cached_file}\n', encoding='utf8')
    return path


@pytest.fixture
def missing_path_cache(tmp_path):
    return tmp_path / 'files.yaml'


def test_get_usages(root_dir, existing_path_cache, discovered_file):
    """If `filename_cache` is None, files will be discovered under
    the discovery root.
    """
    result = _get_usages(root_dir, filename_cache=None)
    assert result == {'owner1/repo1': {'v1': [f'{discovered_file}']}}


def test_get_usages_read_cache(root_dir, existing_path_cache, cached_file):
    """If `filename_cache` is specified, filenames will be read from
    the cache and discovery will be skipped.
    """
    result = _get_usages(root_dir, filename_cache=existing_path_cache)
    assert result == {'owner2/repo2': {'v2': [f'{cached_file}']}}


def test_get_usages_write_cache(root_dir, missing_path_cache, discovered_file):
    """If `filename_cache` is specified but doesn't exist, files will be
    discovered under the discovery root and filenames written to cache.
    """
    result = _get_usages(root_dir, filename_cache=missing_path_cache)
    assert result == {'owner1/repo1': {'v1': [f'{discovered_file}']}}
    assert missing_path_cache.read_text(encoding='utf8') == f'- {discovered_file}\n'
