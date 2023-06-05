from unittest.mock import create_autospec

import pytest
import requests

from action_watch import _get_paginated_data, APICaller


@pytest.fixture
def responses():
    page_1 = (
        {
            'link': '<endpoint?page=2>; rel="next",'
                    ' <endpoint?page=3>; rel="last"',
        },
        [
            {'name': 'v2.0.0'},
            {'name': 'v2'},
        ],
    )
    page_2 = (
        {
            'link': '<endpoint?page=1>; rel="prev",'
                    ' <endpoint?page=1>; rel="first",'
                    ' <endpoint?page=3>; rel="next",'
                    ' <endpoint?page=3>; rel="last"',
        },
        [
            {'name': 'v1'},
            {'name': 'v1.1.0'},
        ],
    )
    page_3 = (
        {
            'link': '<endpoint?page=2>; rel="prev",'
                    ' <endpoint?page=1>; rel="first"',
        },
        [
            {'name': 'v1.0.0'},
        ],
    )

    def _response_mock(headers, data):
        _mock = create_autospec(requests.Response, instance=True)
        _mock.headers = headers
        _mock.json.return_value = data
        return _mock

    return [
        _response_mock(headers, data)
        for headers, data in (page_1, page_2, page_3)
    ]


def test_get_paginated_data(mocker, responses):
    """Test that paginated data (multiple JSON arrays) is retrieved as
    a single sequence.
    """
    caller_mock = create_autospec(APICaller, instance=True)
    caller_mock.get.side_effect = responses
    mocker.patch.dict('action_watch.__dict__', api_caller=caller_mock)

    result = _get_paginated_data('repos/owner1/repo1')

    assert list(result) == [
        {'name': 'v2.0.0'},
        {'name': 'v2'},
        {'name': 'v1'},
        {'name': 'v1.1.0'},
        {'name': 'v1.0.0'},
    ]
