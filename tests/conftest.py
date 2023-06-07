from unittest.mock import create_autospec

import pytest
import requests

tags_test_data = (
    {
        'headers': {
            'link': '<endpoint?page=2>; rel="next",'
                    ' <endpoint?page=3>; rel="last"',
        },
        'body': [
            {
                'name': 'v2.0.0',
                'commit': {
                    'sha': 'a8f2909aad81d2e2e2843a796aedda99e1c8ed0c',  # latest
                },
            },
            {
                'name': 'v1.1.0',
                'commit': {
                    'sha': 'ec028e6d0a1a3ad0d43909ec4fbec3a6cf403c0b',
                },
            },
        ],
    },
    {
        'headers': {
            'link': '<endpoint?page=1>; rel="prev",'
                    ' <endpoint?page=1>; rel="first",'
                    ' <endpoint?page=3>; rel="next",'
                    ' <endpoint?page=3>; rel="last"',
        },
        'body': [
            {
                'name': 'v1.0.0',
                'commit': {
                    'sha': '82b82359ad539833ae0762d92b5ad4f816714359',
                },
            },
            {
                'name': 'v2',
                'commit': {
                    'sha': 'a8f2909aad81d2e2e2843a796aedda99e1c8ed0c',  # latest
                },
            },
        ],
    },
    {
        'headers': {
            'link': '<endpoint?page=2>; rel="prev",'
                    ' <endpoint?page=1>; rel="first"',
        },
        'body': [
            {
                'name': 'v1',
                'commit': {
                    'sha': 'ec028e6d0a1a3ad0d43909ec4fbec3a6cf403c0b',
                },
            },
        ],
    },
)

branches_test_data = (
    {
        'headers': {
            'link': '<endpoint?page=2>; rel="next",'
                    ' <endpoint?page=2>; rel="last"',
        },
        'body': [
            {
                'name': 'main',
                'commit': {
                    'sha': '3ed5b0b31915e00966e11ef0fab1554d0b4b149f',
                },
            },
            {
                'name': 'release/v2',
                'commit': {
                    'sha': 'a8f2909aad81d2e2e2843a796aedda99e1c8ed0c',  # latest
                },
            },
        ],
    },
    {
        'headers': {
            'link': '<endpoint?page=1>; rel="prev",'
                    ' <endpoint?page=1>; rel="first"',
        },
        'body': [
            {
                'name': 'unstable/v2',
                'commit': {
                    'sha': 'c2d7d283597b000b014d7a600717c22c6b3deb84',
                },
            },
            {
                'name': 'release/v1',
                'commit': {
                    'sha': 'ec028e6d0a1a3ad0d43909ec4fbec3a6cf403c0b',
                },
            },
        ],
    },
)


@pytest.fixture
def tag_responses():
    def _response_mock(headers, body):
        _mock = create_autospec(requests.Response, instance=True)
        _mock.headers = headers
        _mock.json.return_value = body
        return _mock

    return [_response_mock(page['headers'], page['body']) for page in tags_test_data]


@pytest.fixture
def tag_items():
    return (revision for page in tags_test_data for revision in page['body'])


@pytest.fixture
def branch_items():
    return (revision for page in branches_test_data for revision in page['body'])
