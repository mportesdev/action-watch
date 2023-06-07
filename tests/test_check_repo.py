from action_watch import _check_repo


def test_check_repo(mocker, tag_items, branch_items):
    mocker.patch(
        'action_watch._get_paginated_data', side_effect=[tag_items, branch_items]
    )
    mocker.patch('action_watch._get_latest_release_tag', return_value='v2.0.0')

    updatable, recommended = _check_repo(
        'owner1/repo1',
        usages={
            'v1': ['1.yml'],
            'v2': ['2.yml'],
            'release/v1': ['3.yml'],
            'release/v2': ['4.yml'],
        }
    )

    assert updatable == {
        'v1': ['1.yml'],
        'release/v1': ['3.yml'],
    }
    assert recommended == 'v2'
