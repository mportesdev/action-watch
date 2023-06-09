import functools
import os
import re
import sys

import yaml
from handpick import values_for_key
from loguru import logger

from ._api import APICaller
from ._environment import _setup_env, _get_env_flag, _get_env_string
from ._paths import CACHE_DIR, _abs_path

PATH_CACHE = CACHE_DIR / '.yml_files.yaml'


def _repo_and_revision(action_revision):
    action, revision = action_revision.split('@')
    repo = '/'.join(action.split('/')[:2])
    return repo, revision


def _get_usages(discovery_root, filename_cache=None):

    def _cached_workflow_paths():
        if filename_cache:
            try:
                with filename_cache.open(encoding='utf8') as f:
                    logger.debug(f'Reading filenames from {filename_cache}')
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.debug(f'{filename_cache} not found')

    def _discovered_workflow_paths():
        logger.info(f'Discovering workflow files under {discovery_root}')
        paths = []
        for path in discovery_root.rglob('.github/workflows/*.yml'):
            path_str = os.fspath(path)
            paths.append(path_str)
            print('.', end='', flush=True)
            logger.debug(path_str)
        num_paths = len(paths)
        print(f' {num_paths} {"file" if num_paths == 1 else "files"}')
        if not paths:
            logger.debug('No workflow files found')
        elif filename_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with filename_cache.open('w', encoding='utf8') as f:
                logger.debug(f'Writing filenames to {filename_cache}')
                yaml.safe_dump(paths, f)
        return paths

    def _read_workflow_files(paths):
        for file_path in paths:
            with open(file_path, encoding='utf8') as f:
                workflow_data = yaml.safe_load(f)
            for action_revision in values_for_key(workflow_data, 'uses'):
                yield file_path, action_revision

    paths = _cached_workflow_paths() or _discovered_workflow_paths()
    result = {}
    for file_path, action_revision in _read_workflow_files(paths):
        repo, revision = _repo_and_revision(action_revision)
        item = result.setdefault(repo, {})
        file_paths = item.setdefault(revision, [])
        if file_path not in file_paths:
            file_paths.append(file_path)

    logger.debug(f'Usages found:\n{yaml.safe_dump(result, indent=4)}')
    return result


@functools.cache
def _get_api_caller():
    return APICaller(
        cached=_get_env_flag('CACHE_REQUESTS'),
        auth_helper=_get_env_string('AUTH_HELPER'),
        auth_header=_get_env_string('AUTH_HEADER'),
    )


def _next_page_number(headers):
    if 'link' not in headers:
        return
    page_dispatch = {
        re_match['label']: re_match['number']
        for re_match in re.finditer(
            r'page=(?P<number>\d+).+?rel="(?P<label>\w+)"',
            headers['link']
        )
    }
    result = page_dispatch.get('next')
    logger.debug(f'pagination: {page_dispatch}, next page: {result}')
    return result


def _get_paginated_data(api_endpoint, page=None):
    response = _get_api_caller().get(
        api_endpoint, params={'page': page} if page else None
    )
    page_data = response.json()
    logger.debug(f'page {page or 1}: {len(page_data)} items')
    yield from page_data

    page = _next_page_number(response.headers)
    if page:
        yield from _get_paginated_data(api_endpoint, page=page)


def _get_latest_release_tag(repo):
    response = _get_api_caller().get(f'repos/{repo}/releases/latest')
    return response.json()['tag_name']


def _sha_info_for_endpoint(repo, endpoint):
    """Return a mapping from revision (tag or branch) name to commit SHA.

    `endpoint` should be 'tags' or 'branches'.
    """
    return {
        item['name']: item['commit']['sha'][:7]
        for item in _get_paginated_data(f'repos/{repo}/{endpoint}')
    }


def _check_repo(repo, usages):
    sha_for_tag = _sha_info_for_endpoint(repo, 'tags')
    sha_for_branch = _sha_info_for_endpoint(repo, 'branches')
    revs = sha_for_tag | sha_for_branch

    latest_tag = _get_latest_release_tag(repo)
    latest_sha = sha_for_tag[latest_tag]
    logger.debug(f'latest release tag: {latest_tag} (commit {latest_sha})')

    current_revs = [rev for rev, sha in revs.items() if sha == latest_sha]
    logger.debug(f'revisions pointing to commit {latest_sha}: {current_revs}')

    outdated_usages = {
        rev: files for rev, files in usages.items()
        if rev in revs and rev not in current_revs
    }
    logger.debug(f'outdated revisions: {list(outdated_usages)}')

    unknown_usages = {rev: files for rev, files in usages.items() if rev not in revs}
    logger.debug(f'unknown revisions: {list(unknown_usages)}')

    updatable = outdated_usages | unknown_usages
    current_tags = [tag for tag, sha in sha_for_tag.items() if sha == latest_sha]
    recommended = sorted(current_tags)[0]
    return updatable, recommended


def _report_repo(repo, usages):
    print(repo, end=' ', flush=True)
    try:
        updatable, recommended = _check_repo(repo, usages)
    except _get_api_caller().errors as err:
        logger.error(f'{type(err).__name__} {err.response.status_code}')
        return

    if not updatable:
        logger.success('OK')
        return

    logger.warning('Found outdated')
    for rev, files in updatable.items():
        logger.warning(f'  Recommended update {rev!r} -> {recommended!r} in files:')
        for file in files:
            logger.warning(f'    {file}')


def main():
    _setup_env()
    if not _get_env_flag('DEBUG'):
        logger.remove()
        logger.add(sys.stdout, level='INFO', format='<level>{message}</level>')

    discovery_root = _get_env_string('DISCOVERY_ROOT')
    if not discovery_root:
        logger.debug('Discovery root not specified, falling back to cwd')
    action_usages = _get_usages(
        _abs_path(discovery_root),
        filename_cache=PATH_CACHE if _get_env_flag('CACHE_PATHS') else None,
    )
    if not action_usages:
        logger.info('No action usages found')
        return
    usage_count = sum(
        len(file_paths)
        for usages_by_revision in action_usages.values()
        for file_paths in usages_by_revision.values()
    )
    logger.info(f'Found {usage_count} usages of {len(action_usages)} actions')

    for repo, usages in action_usages.items():
        _report_repo(repo, usages)


if __name__ == '__main__':
    main()
