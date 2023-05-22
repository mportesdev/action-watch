import pytest

from action_watch import _next_page_number


@pytest.mark.parametrize(
    'headers, expected',
    (
        pytest.param(
            {'link': '<endpoint?page=2>; rel="next", <endpoint?page=2>; rel="last"'},
            '2',
            id='next page 2',
        ),
        pytest.param(
            {'link': '<endpoint?page=1>; rel="prev", <endpoint?page=1>; rel="first"'},
            None,
            id='no next page',
        ),
        pytest.param({}, None, id='no link header'),
    ),
)
def test_next_page_number(headers, expected):
    assert _next_page_number(headers) == expected
