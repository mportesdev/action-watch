import pytest

from action_watch._paths import _abs_path


@pytest.mark.parametrize(
    'path',
    (
        pytest.param('', id='empty'),
        pytest.param('~/python/', id='tilde'),
        pytest.param('/home/eddie/projects/', id='absolute'),
    ),
)
def test_abs_path(path):
    result = _abs_path(path)
    assert result.is_absolute()
    assert '~' not in str(result)
