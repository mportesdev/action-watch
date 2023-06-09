from action_watch import _repo_and_revision


def test_repo_and_revision():
    repo, revision = _repo_and_revision('owner/repo@v1')
    assert repo == 'owner/repo'
    assert revision == 'v1'


def test_repo_and_revision_additional_part():
    repo, revision = _repo_and_revision('owner/repo/name@v1')
    assert repo == 'owner/repo'
    assert revision == 'v1'
