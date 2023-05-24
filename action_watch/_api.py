import os
from pathlib import Path

import requests
import requests_cache
from helper_auth import HelperAuth
from loguru import logger

CACHE_DIR = Path.home() / '.cache' / 'action-watch'
HTTP_CACHE = CACHE_DIR / '.cache.sqlite3'


class APICaller:
    errors = (requests.HTTPError,)

    def __init__(self, cached, auth_helper, auth_header):
        if cached:
            logger.info('Setting up requests_cache.CachedSession')
            self._session = requests_cache.CachedSession(os.fspath(HTTP_CACHE))
        else:
            logger.info('Setting up requests.Session')
            self._session = requests.Session()

        self._headers = {'Accept': 'application/vnd.github+json'}
        if auth_helper:
            logger.info('Using authentication handler')
            self._auth = HelperAuth(auth_helper, cache_token=True)
        else:
            self._auth = None
            if auth_header:
                logger.info('Using Authorization header')
                self._headers['Authorization'] = auth_header
            else:
                logger.info('No authentication')

    def get(self, url, **kwargs):
        with self._session as session:
            response = session.get(
                url, headers=self._headers, auth=self._auth, **kwargs
            )
        try:
            response.raise_for_status()
        except self.errors:
            logger.info(f'Response status {response.status_code} from url {url}')
            raise
        return response
