from unittest.mock import create_autospec

from action_watch import _get_paginated_data
from action_watch._api import APICaller


def test_get_paginated_data(mocker, tag_responses, tag_items):
    """Test that paginated data (multiple JSON arrays) is retrieved as
    a single sequence.
    """
    caller_mock = create_autospec(APICaller, instance=True)
    caller_mock.get.side_effect = tag_responses
    mocker.patch('action_watch._get_api_caller', return_value=caller_mock)

    result = _get_paginated_data('repos/owner1/repo1')

    assert list(result) == list(tag_items)
