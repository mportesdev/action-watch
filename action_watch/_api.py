import os
from pathlib import Path

import requests
import requests_cache
from helper_auth import HelperAuth
from loguru import logger

CACHE_DIR = Path.home() / '.cache' / 'action-watch'
HTTP_CACHE = CACHE_DIR / '.cache.sqlite3'


class APICaller:
    api_base_url = 'https://api.github.com'
    errors = (requests.HTTPError,)

    def __init__(self, cached, auth_helper, auth_header):
        if cached:
            logger.debug('Setting up requests_cache.CachedSession')
            self._session = requests_cache.CachedSession(os.fspath(HTTP_CACHE))
        else:
            logger.debug('Setting up requests.Session')
            self._session = requests.Session()

        self._headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        if auth_helper:
            logger.debug('Using authentication handler')
            self._auth = HelperAuth(auth_helper, cache_token=True)
        else:
            self._auth = None
            if auth_header:
                logger.debug('Using Authorization header')
                self._headers['Authorization'] = auth_header
            else:
                logger.debug('No authentication')

    def get(self, api_endpoint, **kwargs):
        url = f'{self.api_base_url}/{api_endpoint}'
        with self._session as session:
            response = session.get(
                url, headers=self._headers, auth=self._auth, **kwargs
            )
        cached = getattr(response, "from_cache", False)
        logger.debug(f'cached response: {cached}')
        if not cached:
            logger.debug(
                f'rate limit remaining: {response.headers["X-RateLimit-Remaining"]}'
            )
        try:
            response.raise_for_status()
        except self.errors:
            logger.debug(f'Response status {response.status_code} from url {url}')
            raise
        return response
