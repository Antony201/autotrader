import asyncio
import logging
import os
import random
from enum import Enum
from typing import Union, Optional, Dict, List

import aiohttp
from aiohttp import ClientSession, ClientTimeout


class AsyncHttpException(Exception):
    pass


class InvalidOutputTypeException(AsyncHttpException):
    pass


class InvalidHttpMethodException(AsyncHttpException):
    pass


class InvalidResponseException(AsyncHttpException):
    pass


class TooManyRequests(AsyncHttpException):
    def __init__(self, exception, retry_after):
        super().__init__(exception)
        self.retry_after = int(retry_after)


logger = logging.getLogger('http')

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/65.0.3325.181 Chrome/65.0.3325.181 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:59.0) Gecko/20100101 Firefox/59.0",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0"
]


class OutputFormat(Enum):
    RAW = 'raw'
    JSON = 'json'


class HttpMethod(Enum):
    GET = 'get'
    POST = 'post'


class AsyncHttp:
    def __init__(self, loop=None):
        self._timeout = int(os.environ.get('REQUEST_TIMEOUT', 60))
        self._loop = loop or asyncio.get_event_loop()
        self._session = self._init_session()

    async def close(self):
        await self._session.close()

    def _init_session(self) -> ClientSession:
        return ClientSession(
            raise_for_status=True,
            headers={
                'User-Agent': random.choice(DEFAULT_USER_AGENTS),
            },
            timeout=ClientTimeout(total=self._timeout),
            loop=self._loop
        )

    async def get(
            self,
            url: str,
            output: OutputFormat = OutputFormat.JSON,
            headers: Optional[dict] = None,
    ) -> Union[Dict, List, str]:
        return await self._request(url, headers, output, HttpMethod.GET)

    async def post(
            self,
            url: str,
            output: OutputFormat = OutputFormat.JSON,
            headers: Optional[None] = None,
            data: Optional[dict] = None
    ) -> Union[dict, str]:
        return await self._request(url, headers, output, HttpMethod.POST, data)

    async def _request(
            self,
            url: str,
            headers: Optional[dict],
            output: OutputFormat,
            method: HttpMethod,
            data: Optional[dict] = None
    ) -> Union[dict, str]:
        if not isinstance(output, OutputFormat):
            raise InvalidOutputTypeException(
                f'Invalid output format type {type(output)}, must be OutputFormat instance'
            )

        if not isinstance(method, HttpMethod):
            raise InvalidHttpMethodException(
                f'Invalid http method type {type(method)}, must be HttpMethod instance'
            )

        try:
            http_method = getattr(self._session, method.value)
            async with http_method(url=url, data=data, headers=headers) as response:
                if output == OutputFormat.RAW:
                    result = await response.text()
                else:
                    result = await response.json()

                return result
        except aiohttp.ClientResponseError as e:
            if hasattr(e, 'status') and e.status == 429:
                raise TooManyRequests(e, e.headers.get('Retry-After', 0))
            raise
        except Exception as e:
            raise InvalidResponseException('%s: %s' % (type(e).__name__, e))
