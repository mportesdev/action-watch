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

CONFIG_DIR = Path.home() / '.config' / 'action-watch'
DOTENV = CONFIG_DIR / '.env'
CACHE_DIR = Path.home() / '.cache' / 'action-watch'
PATH_CACHE = CACHE_DIR / '.yml_files.yaml'
HTTP_CACHE = CACHE_DIR / '.cache.sqlite3'
API_URL = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json'}


def _get_usages(discovery_root, use_cache=False):

    def _discover_workflow_files():
        paths = None
        if use_cache:
            try:
                with PATH_CACHE.open(encoding='utf8') as f:
                    logger.debug(f'Reading filenames from {PATH_CACHE}')
                    paths = yaml.safe_load(f)
            except FileNotFoundError:
                logger.debug(f'{PATH_CACHE} not found')
        if paths is None:
            print(f'Discovering workflow files under {discovery_root}')
            paths = [
                os.fspath(path)
                for path in discovery_root.rglob('.github/workflows/*.yml')
            ]
            if use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                with PATH_CACHE.open('w', encoding='utf8') as f:
                    logger.debug(f'Writing filenames to {PATH_CACHE}')
                    yaml.safe_dump(paths, f)
        logger.debug('\n' + '\n'.join(paths))
        return paths

    def _read_workflow_files(paths):
        for file_path in paths:
            with open(file_path, encoding='utf8') as f:
                workflow_data = yaml.safe_load(f)
            for action_spec in values_for_key(workflow_data, 'uses'):
                yield file_path, action_spec

    paths = _discover_workflow_files()
    result = {}
    for file_path, action_spec in _read_workflow_files(paths):
        repo, revision = action_spec.split('@')
        item = result.setdefault(repo, {})
        file_paths = item.setdefault(revision, [])
        if file_path not in file_paths:
            file_paths.append(file_path)

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
        result = page_dispatch.get('next')
        logger.debug(f'pagination: {page_dispatch}, next page: {result}')
        return result

    query_params = {}
    while True:
        with session:
            response = session.get(url, headers=HEADERS, params=query_params)
        cached = getattr(response, "from_cache", False)
        logger.debug(f'cached response: {cached}')
        if not cached:
            logger.debug(
                f'rate limit remaining: {response.headers["X-RateLimit-Remaining"]}'
            )
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
    cached = getattr(response, "from_cache", False)
    logger.debug(f'cached response: {cached}')
    if not cached:
        logger.debug(
            f'rate limit remaining: {response.headers["X-RateLimit-Remaining"]}'
        )
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
    logger.info(f'latest release tag: {latest_tag} (commit {latest_sha})')

    current_revs = [rev for rev, sha in revs.items() if sha == latest_sha]
    logger.info(f'revisions pointing to commit {latest_sha}: {current_revs}')

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


def main():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not DOTENV.is_file():
        DOTENV.touch()
    load_dotenv(DOTENV)
    logger.remove()
    logger.add(
        sys.stderr,
        level='DEBUG' if _get_env_flag('DEBUG') else 'WARNING',
        format='<level>{level}: {message}</level>',
    )

    global session
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


if __name__ == '__main__':
    main()
