import os
import re
import sys
from pathlib import Path

import requests
import requests_cache
import yaml
from dotenv import load_dotenv
from handpick import values_for_key
from loguru import logger

PATH_CACHE = Path(__file__).parent / '.yml_files.yaml'
API_URL = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json'}
HTTP_CACHE = Path(__file__).parent / '.cache.sqlite3'


def _get_usages(discovery_root, use_cache=False):

    def _read_workflow_files():
        workflow_files = None
        if use_cache:
            try:
                with PATH_CACHE.open(encoding='utf8') as f:
                    logger.debug(f'Reading filenames from {PATH_CACHE}')
                    workflow_files = yaml.safe_load(f)
            except FileNotFoundError:
                logger.debug(f'{PATH_CACHE} not found')
        if workflow_files is None:
            print(f'Discovering workflow files under {discovery_root}')
            workflow_files = [
                os.fspath(path)
                for path in discovery_root.rglob('.github/workflows/*.yml')
            ]
            if use_cache:
                with PATH_CACHE.open('w', encoding='utf8') as f:
                    logger.debug(f'Writing filenames to {PATH_CACHE}')
                    yaml.safe_dump(workflow_files, f)
        logger.debug('\n' + '\n'.join(workflow_files))
        for filename in workflow_files:
            with open(filename, encoding='utf8') as f:
                workflow_data = yaml.safe_load(f)
            for action_spec in values_for_key(workflow_data, 'uses'):
                yield filename, action_spec

    result = {}
    for filename, action_spec in _read_workflow_files():
        repo, revision = action_spec.split('@')
        item = result.setdefault(repo, {})
        filenames = item.setdefault(revision, [])
        if filename not in filenames:
            filenames.append(filename)

    logger.debug(f'\n{yaml.safe_dump(result, indent=4)}')
    return result


def _get_paginated_data(url):

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
        logger.debug(page_dispatch)
        result = page_dispatch.get('next')
        logger.debug(f'next page number: {result}')
        return result

    query_params = {}
    while True:
        with session:
            response = session.get(url, headers=HEADERS, params=query_params)
            logger.debug(f'cached response: {getattr(response, "from_cache", False)}')
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.warning(f'response status {response.status_code} from url {url}')
            return

        page_data = response.json()
        logger.debug(f'page {query_params.get("page", 1)}: {len(page_data)} items')
        yield page_data

        next_page = _next_page_number(response.headers)
        if next_page is None:
            return
        query_params['page'] = next_page


def _get_latest_release_tag(repo):
    with session:
        response = session.get(
            f'{API_URL}/repos/{repo}/releases/latest',
            headers=HEADERS,
        )
        logger.debug(f'cached response: {getattr(response, "from_cache", False)}')
    response.raise_for_status()
    return response.json()['tag_name']


def _check_repo(repo, used_revs):
    print(f'[{repo}]')
    sha_for_tag = {}
    for page_data in _get_paginated_data(f'{API_URL}/repos/{repo}/tags'):
        for item in page_data:
            sha_for_tag[item['name']] = item['commit']['sha'][:7]

    sha_for_branch = {}
    for page_data in _get_paginated_data(f'{API_URL}/repos/{repo}/branches'):
        for item in page_data:
            sha_for_branch[item['name']] = item['commit']['sha'][:7]

    revs = sha_for_tag | sha_for_branch
    if not revs:
        print('Skipped')
        return

    latest_tag = _get_latest_release_tag(repo)
    latest_sha = sha_for_tag[latest_tag]
    logger.debug(f'latest release tag: {latest_tag} (commit {latest_sha})')

    current_revs = [rev for rev, sha in revs.items() if sha == latest_sha]
    logger.debug(f'revisions pointing to commit {latest_sha}: {current_revs}')

    outdated_used = {
        rev: files for rev, files in used_revs.items()
        if rev in revs and rev not in current_revs
    }
    logger.debug(f'outdated revisions: {list(outdated_used)}')

    unknown_used = {rev: files for rev, files in used_revs.items() if rev not in revs}
    logger.debug(f'unknown revisions: {list(unknown_used)}')

    updatable = outdated_used | unknown_used
    if not updatable:
        print('OK')
        return

    print('Found outdated')
    current_tags = [tag for tag, sha in sha_for_tag.items() if sha == latest_sha]
    recommended = sorted(current_tags)[0]
    for rev, files in updatable.items():
        print(f'Recommended update {rev!r} -> {recommended!r} in files:')
        for file in files:
            print(f'  {file}')


def _get_env_flag(key):
    value = os.getenv(f'ACTION_WATCH_{key}')
    return bool(value) and value != '0'


if __name__ == '__main__':
    load_dotenv()
    logger.remove()
    logger.add(
        sys.stderr,
        level='DEBUG' if _get_env_flag('DEBUG') else 'WARNING',
        format='<level>{level}: {message}</level>',
    )

    if _get_env_flag('CACHE_REQUESTS'):
        session = requests_cache.CachedSession(os.fspath(HTTP_CACHE))
    else:
        session = requests.Session()

    discovery_root = Path(os.getenv('ACTION_WATCH_DISCOVERY_ROOT')).expanduser()
    for repo, usages in _get_usages(
            discovery_root,
            use_cache=_get_env_flag('CACHE_PATHS'),
    ).items():
        _check_repo(repo, usages)
