import pytest

from action_watch import _check_repo

@pytest.fixture
def tag_data():
    page_data = [
        {
            'name': 'v2.0.0',
            'commit': {
                'sha': 'a8f2909aad81d2e2e2843a796aedda99e1c8ed0c',
            },
        },
        {
            'name': 'v2',
            'commit': {
                'sha': 'a8f2909aad81d2e2e2843a796aedda99e1c8ed0c',
            },
        },
        {
            'name': 'v1',
            'commit': {
                'sha': 'ec028e6d0a1a3ad0d43909ec4fbec3a6cf403c0b',
            },
        },
    ]
    return iter([page_data])


def test_check_repo(capsys, mocker, tag_data):
    mocker.patch('action_watch._get_paginated_data', return_value=tag_data)
    mocker.patch('action_watch._get_latest_release_tag', return_value='v2.0.0')
    _check_repo('owner1/repo1', {'v1': ['1.yml']})
    stdout = capsys.readouterr().out
    assert "Recommended update 'v1' -> 'v2'" in stdout
    assert "1.yml" in stdout
