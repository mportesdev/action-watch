import os
import re
import shutil
import sys
from pathlib import Path

import requests
import requests_cache
import yaml
from dotenv import load_dotenv
from handpick import values_for_key
from helper_auth import HelperAuth
from loguru import logger

DOTENV_DEFAULT = Path(__file__).parent / '.env-default'
CONFIG_DIR = Path.home() / '.config' / 'action-watch'
DOTENV = CONFIG_DIR / '.env'
CACHE_DIR = Path.home() / '.cache' / 'action-watch'
PATH_CACHE = CACHE_DIR / '.yml_files.yaml'
HTTP_CACHE = CACHE_DIR / '.cache.sqlite3'
API_URL = 'https://api.github.com'
HEADERS = {'Accept': 'application/vnd.github+json'}


def _get_usages(discovery_root, use_cache=False):

    def _cached_workflow_paths():
        if use_cache:
            try:
                with PATH_CACHE.open(encoding='utf8') as f:
                    logger.debug(f'Reading filenames from {PATH_CACHE}')
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.debug(f'{PATH_CACHE} not found')

    def _discovered_workflow_paths():
        print(f'Discovering workflow files under {discovery_root}')
        paths = []
        for path in discovery_root.rglob('.github/workflows/*.yml'):
            path_str = os.fspath(path)
            paths.append(path_str)
            logger.debug(path_str)
        if not paths:
            logger.debug('No workflow files found')
        elif use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with PATH_CACHE.open('w', encoding='utf8') as f:
                logger.debug(f'Writing filenames to {PATH_CACHE}')
                yaml.safe_dump(paths, f)
        return paths

    def _read_workflow_files(paths):
        for file_path in paths:
            with open(file_path, encoding='utf8') as f:
                workflow_data = yaml.safe_load(f)
            for action_spec in values_for_key(workflow_data, 'uses'):
                yield file_path, action_spec

    paths = _cached_workflow_paths() or _discovered_workflow_paths()
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
            response = session.get(url, headers=HEADERS, params=query_params, auth=auth)
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
            raise

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
            f'{API_URL}/repos/{repo}/releases/latest', headers=HEADERS, auth=auth
        )
    cached = getattr(response, "from_cache", False)
    logger.debug(f'cached response: {cached}')
    if not cached:
        logger.debug(
            f'rate limit remaining: {response.headers["X-RateLimit-Remaining"]}'
        )
    response.raise_for_status()
    return response.json()['tag_name']


def _sha_info_for_endpoint(repo, endpoint):
    """Return a mapping from revision (tag or branch) name to commit SHA.

    `endpoint` should be 'tags' or 'branches'.
    """
    return {
        item['name']: item['commit']['sha'][:7]
        for page_data in _get_paginated_data(f'{API_URL}/repos/{repo}/{endpoint}')
        for item in page_data
    }


def _check_repo(repo, used_revs):
    print(f'[{repo}]')
    try:
        sha_for_tag = _sha_info_for_endpoint(repo, 'tags')
        sha_for_branch = _sha_info_for_endpoint(repo, 'branches')
    except requests.HTTPError:
        print('Skipped')
        return
    revs = sha_for_tag | sha_for_branch

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


def _get_env_string(key):
    return os.getenv(f'ACTION_WATCH_{key}', '')


def _setup_env():
    """Create a default `.env` file if necessary.
    Load `.env` into environment.
    """
    if not DOTENV.is_file():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DOTENV_DEFAULT, DOTENV)
    load_dotenv(DOTENV)


def main():
    _setup_env()
    logger.remove()
    logger.add(
        sys.stderr,
        level='DEBUG' if _get_env_flag('DEBUG') else 'WARNING',
        format='<level>{level}: {message}</level>',
    )

    discovery_root = _get_env_string('DISCOVERY_ROOT')
    if not discovery_root:
        logger.debug('Discovery root not specified, falling back to cwd')
    action_usages = _get_usages(
        Path(discovery_root).expanduser(),
        use_cache=_get_env_flag('CACHE_PATHS'),
    )
    if not action_usages:
        print('No action usages found')
        return

    global session
    if _get_env_flag('CACHE_REQUESTS'):
        session = requests_cache.CachedSession(os.fspath(HTTP_CACHE))
    else:
        session = requests.Session()

    global auth
    auth_helper = _get_env_string('AUTH_HELPER')
    if auth_helper:
        logger.debug('Using authentication handler')
        auth = HelperAuth(auth_helper, cache_token=True)
    else:
        auth = None
        auth_header = _get_env_string('AUTH_HEADER')
        if auth_header:
            logger.debug('Using Authorization header')
            HEADERS['Authorization'] = auth_header
        else:
            logger.debug('No authentication')

    for repo, usages in action_usages.items():
        _check_repo(repo, usages)


if __name__ == '__main__':
    main()