import asyncio
import base64
import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from urllib.parse import urlparse, urlencode

import aiohttp

from exchange_libs.aiohuobi.exceptions import HuobiResponseException, HuobiAPIException, HuobiAuthenticationRequired


class HttpMethod(Enum):
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    DELETE = 'delete'


class Client:
    _API_URL = 'https://api.huobi.pro'

    def __init__(self, access_key: str = None, secret_key: str = None, loop: asyncio.AbstractEventLoop = None):
        self._access_key = access_key
        self._secret_key = secret_key

        self._loop = loop or asyncio.get_event_loop()
        self._session = self._init_session()

    def _init_session(self):
        return aiohttp.ClientSession(
            headers={
                'Accept': 'application/json',
                'User-Agent': 'aiohuobi',
            },
            loop=self._loop
        )

    async def close_session(self):
        await self._session.close()

    @staticmethod
    def _get_ts():
        return datetime.utcnow().isoformat(timespec='seconds')

    def _create_api_uri(self, path: str) -> str:
        return f'{self._API_URL}{path}'

    async def _request(self, method: HttpMethod, path: str, sign: bool = False, params: Optional[dict] = None):
        params = params or {}

        if sign:
            if not self._access_key or not self._secret_key:
                raise HuobiAuthenticationRequired(f'Authentication required for {path!r}')
            signed_params = self._sign(path, method)

        url = f'{self._create_api_uri(path)}?{urlencode(signed_params)}'

        http_method = getattr(self._session, method.value)
        async with http_method(url, json=params) as response:
            return await self._handle_response(response)

    @staticmethod
    async def _handle_response(response: aiohttp.ClientResponse):
        try:
            response_json = await response.json()
        except aiohttp.ContentTypeError:
            raise HuobiResponseException(f'Invalid response: {await response.text()!r}')
        else:
            if response_json['status'] == 'ok':
                return response_json

            raise HuobiAPIException(response, response_json)

    async def _request_api(self, method: HttpMethod, path: str, private: bool = False, params: Optional[dict] = None):
        return await self._request(
            method,
            path,
            private,
            params
        )

    async def _get(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.GET, path, sign, params)

    async def _post(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.POST, path, sign, params)

    def _sign(self, path: str, method: HttpMethod):
        sign_params = dict(
            AccessKeyId=self._access_key,
            SignatureMethod='HmacSHA256',
            SignatureVersion='2',
            Timestamp=self._get_ts(),
        )

        parsed_url = urlparse(self._API_URL)

        payload = '\n'.join(
            [
                method.value.upper(),
                parsed_url.netloc,
                path,
                urlencode(sign_params)
            ]
        )

        digest = hmac.new(
            self._secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).digest()

        sign_params['Signature'] = base64.b64encode(digest).decode()
        return sign_params

    async def accounts(self):
        return await self._get(
            '/v1/account/accounts',
            True
        )

    async def balance(self, account_id):
        return await self._get(
            f'/v1/account/accounts/{account_id}/balance',
            True
        )

    async def buy_market_order(self, account_id: int, amount: Decimal, symbol: str):
        return await self._post(
            '/v1/order/orders/place',
            True,
            {
                'account-id': account_id,
                'amount': str(amount),
                'source': 'api',
                'symbol': symbol.lower(),
                'type': 'buy-market',
            }
        )

    async def buy_limit_order(self, account_id: int, amount: Decimal, symbol: str, price: Decimal):
        return await self._post(
            '/v1/order/orders/place',
            True,
            {
                'account-id': account_id,
                'amount': str(amount),
                'source': 'api',
                'symbol': symbol.lower(),
                'price': str(price),
                'type': 'buy-limit',
            }
        )

    async def cancel_order(self, order_id: str):
        return await self._post(
            f'/v1/order/orders/{order_id}/submitcancel',
            True,
        )

    async def get_open_orders(self, account_id):
        return await self._get(
            f'/v1/order/openOrders',
            True,
            params={'account-id': account_id}
        )
