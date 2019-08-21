import asyncio
import hashlib
import hmac
from decimal import Decimal
from enum import Enum
from time import time
from typing import Optional
from urllib.parse import urlencode

from aiohttp import ClientSession, ClientTimeout, ClientResponse, ContentTypeError

from exchange_libs.aiobinance.exceptions import BinanceAPIException, BinanceRequestException


class HttpMethod(Enum):
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    DELETE = 'delete'


class Client:
    _API_URL = 'https://api.binance.com/api'

    _PUBLIC_API_VERSION = 'v1'
    _PRIVATE_API_VERSION = 'v3'

    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'

    ORDER_TYPE_MARKET = 'MARKET'
    ORDER_TYPE_LIMIT = 'LIMIT'

    TIME_IN_FORCE_GTC = 'GTC'  # Good till cancelled
    TIME_IN_FORCE_IOC = 'IOC'  # Immediate or cancel
    TIME_IN_FORCE_FOK = 'FOK'  # Fill or kill

    def __init__(self, api_key: str, api_secret: str, timeout=10, loop=None):
        self._API_KEY = api_key
        self._API_SECRET = api_secret

        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop()
        self._session = self._init_session()

    def _generate_signature(self, params):
        return hmac.new(
            self._API_SECRET.encode('u8'),
            urlencode(params).encode('u8'),
            hashlib.sha256
        ).hexdigest()

    def _init_session(self) -> ClientSession:
        return ClientSession(
            headers={
                'Accept': 'application/json',
                'User-Agent': 'binance/python',
                'X-MBX-APIKEY': self._API_KEY
            },
            timeout=ClientTimeout(total=self._timeout),
            loop=self._loop
        )

    def _create_api_uri(self, path: str, private: bool = False) -> str:
        return f'{self._API_URL}/{self._PRIVATE_API_VERSION if private else self._PUBLIC_API_VERSION}/{path}'

    async def _request_api(self, method: HttpMethod, path: str, private: bool = False, params: Optional[dict] = None):
        return await self._request(
            method,
            self._create_api_uri(path, private),
            private,
            params
        )

    async def _request(self, method: HttpMethod, url: str, sign: bool = False, params: Optional[dict] = None):
        params = params or {}

        if sign:
            params.update({'timestamp': self._get_nonce()})
            params.update({'signature': self._generate_signature(params)})

        http_method = getattr(self._session, method.value)
        async with http_method(url, params=params) as response:
            return await self._handle_response(response)

    @staticmethod
    async def _handle_response(response: ClientResponse):
        try:
            response_json = await response.json()
        except ContentTypeError:
            raise BinanceRequestException(f'Invalid response: {await response.text()!r}')
        else:
            if 200 <= response.status < 300:
                return response_json

            raise BinanceAPIException(response, response_json)

    async def _get(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.GET, path, sign, params)

    async def _post(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.POST, path, sign, params)

    async def _put(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.PUT, path, sign, params)

    async def _delete(self, path: str, sign: bool = False, params: Optional[dict] = None):
        return await self._request_api(HttpMethod.DELETE, path, sign, params)

    @staticmethod
    def _get_nonce() -> int:
        return int(time() * 1000)

    async def get_account(self):
        return await self._get('account', sign=True)

    async def create_order(self, **params):
        """Send in a new order

        Any order with an icebergQty MUST have timeInForce set to GTC.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#new-order--trade

        :param symbol: required
        :type symbol: str
        :param side: required
        :type side: str
        :param type: required
        :type type: str
        :param timeInForce: required if limit order
        :type timeInForce: str
        :param quantity: required
        :type quantity: decimal
        :param price: required
        :type price: str
        :param newClientOrderId: A unique id for the order. Automatically generated if not sent.
        :type newClientOrderId: str
        :param icebergQty: Used with LIMIT, STOP_LOSS_LIMIT, and TAKE_PROFIT_LIMIT to create an iceberg order.
        :type icebergQty: decimal
        :param newOrderRespType: Set the response JSON. ACK, RESULT, or FULL; default: RESULT.
        :type newOrderRespType: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        Response ACK:

        .. code-block:: python

            {
                "symbol":"LTCBTC",
                "orderId": 1,
                "clientOrderId": "myOrder1" # Will be newClientOrderId
                "transactTime": 1499827319559
            }

        Response RESULT:

        .. code-block:: python

            {
                "symbol": "BTCUSDT",
                "orderId": 28,
                "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
                "transactTime": 1507725176595,
                "price": "0.00000000",
                "origQty": "10.00000000",
                "executedQty": "10.00000000",
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": "SELL"
            }

        Response FULL:

        .. code-block:: python

            {
                "symbol": "BTCUSDT",
                "orderId": 28,
                "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
                "transactTime": 1507725176595,
                "price": "0.00000000",
                "origQty": "10.00000000",
                "executedQty": "10.00000000",
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": "SELL",
                "fills": [
                    {
                        "price": "4000.00000000",
                        "qty": "1.00000000",
                        "commission": "4.00000000",
                        "commissionAsset": "USDT"
                    },
                    {
                        "price": "3999.00000000",
                        "qty": "5.00000000",
                        "commission": "19.99500000",
                        "commissionAsset": "USDT"
                    },
                    {
                        "price": "3998.00000000",
                        "qty": "2.00000000",
                        "commission": "7.99600000",
                        "commissionAsset": "USDT"
                    },
                    {
                        "price": "3997.00000000",
                        "qty": "1.00000000",
                        "commission": "3.99700000",
                        "commissionAsset": "USDT"
                    },
                    {
                        "price": "3995.00000000",
                        "qty": "1.00000000",
                        "commission": "3.99500000",
                        "commissionAsset": "USDT"
                    }
                ]
            }

        :raises: BinanceRequestException, BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException

        """
        return await self._post('order', True, params)

    async def order_market(self, **params):
        """Send in a new market order

        :param symbol: required
        :type symbol: str
        :param side: required
        :type side: str
        :param quantity: required
        :type quantity: decimal
        :param newClientOrderId: A unique id for the order. Automatically generated if not sent.
        :type newClientOrderId: str
        :param newOrderRespType: Set the response JSON. ACK, RESULT, or FULL; default: RESULT.
        :type newOrderRespType: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        See order endpoint for full response options

        :raises: BinanceRequestException, BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException

        """
        params.update({
            'type': self.ORDER_TYPE_MARKET
        })
        return await self.create_order(**params)

    async def order_market_buy(self, symbol: str, quantity: str, newOrderRespType: str = 'ACK'):
        """Send in a new market buy order

        :param symbol: required
        :type symbol: str
        :param quantity: required
        :type quantity: decimal
        :param newClientOrderId: A unique id for the order. Automatically generated if not sent.
        :type newClientOrderId: str
        :param newOrderRespType: Set the response JSON. ACK, RESULT, or FULL; default: RESULT.
        :type newOrderRespType: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        See order endpoint for full response options

        :raises: BinanceRequestException, BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException

        """
        return await self.order_market(
            **{
                'side': self.SIDE_BUY,
                'symbol': symbol,
                'quantity': quantity,
                # 'newOrderRespType': newOrderRespType
            }
        )

    async def order_limit(self, time_in_force=TIME_IN_FORCE_GTC, **params):
        """Send in a new limit order
        Any order with an icebergQty MUST have timeInForce set to GTC.
        :param symbol: required
        :type symbol: str
        :param side: required
        :type side: str
        :param quantity: required
        :type quantity: decimal
        :param price: required
        :type price: str
        :param timeInForce: default Good till cancelled
        :type timeInForce: str
        :param newClientOrderId: A unique id for the order. Automatically generated if not sent.
        :type newClientOrderId: str
        :param icebergQty: Used with LIMIT, STOP_LOSS_LIMIT, and TAKE_PROFIT_LIMIT to create an iceberg order.
        :type icebergQty: decimal
        :param newOrderRespType: Set the response JSON. ACK, RESULT, or FULL; default: RESULT.
        :type newOrderRespType: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int
        :returns: API response
        See order endpoint for full response options
        :raises: BinanceRequestException, BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException
        """
        params.update({
            'type': self.ORDER_TYPE_LIMIT,
            'timeInForce': time_in_force
        })
        return await self.create_order(**params)

    async def order_limit_buy(self, symbol: str, quantity: str, price: Decimal, time_in_force=TIME_IN_FORCE_GTC):
        return await self.order_limit(
            time_in_force,
            **{
                'type': self.ORDER_TYPE_LIMIT,
                'side': self.SIDE_BUY,
                'symbol': symbol,
                'quantity': quantity,
                'price': str(price),
            }
        )

    async def create_test_order(self, symbol: str, side: str, type: str, quantity: Decimal):
        """Test new order creation and signature/recvWindow long. Creates and validates a new order but does not send it into the matching engine.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#test-new-order-trade

        :param symbol: required
        :type symbol: str
        :param side: required
        :type side: str
        :param type: required
        :type type: str
        :param timeInForce: required if limit order
        :type timeInForce: str
        :param quantity: required
        :type quantity: decimal
        :param price: required
        :type price: str
        :param newClientOrderId: A unique id for the order. Automatically generated if not sent.
        :type newClientOrderId: str
        :param icebergQty: Used with iceberg orders
        :type icebergQty: decimal
        :param newOrderRespType: Set the response JSON. ACK, RESULT, or FULL; default: RESULT.
        :type newOrderRespType: str
        :param recvWindow: The number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        .. code-block:: python

            {}

        :raises: BinanceRequestException, BinanceAPIException, BinanceOrderException, BinanceOrderMinAmountException, BinanceOrderMinPriceException, BinanceOrderMinTotalException, BinanceOrderUnknownSymbolException, BinanceOrderInactiveSymbolException


        """
        return await self._post(
            'order/test',
            True,
            params={
                'type': type,
                'side': side,
                'symbol': symbol,
                'quantity': str(quantity)
            }
        )

    async def get_order(self, symbol: str, orderId: str):
        """Check an order's status. Either orderId or origClientOrderId must be sent.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#query-order-user_data

        :param symbol: required
        :type symbol: str
        :param orderId: The unique order id
        :type orderId: int
        :param origClientOrderId: optional
        :type origClientOrderId: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        .. code-block:: python

            {
                "symbol": "LTCBTC",
                "orderId": 1,
                "clientOrderId": "myOrder1",
                "price": "0.1",
                "origQty": "1.0",
                "executedQty": "0.0",
                "status": "NEW",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": "BUY",
                "stopPrice": "0.0",
                "icebergQty": "0.0",
                "time": 1499827319559
            }

        :raises: BinanceRequestException, BinanceAPIException

        """
        return await self._get(
            'order',
            True,
            {'symbol': symbol, 'orderId': orderId}
        )

    async def get_all_orders(self, symbol: str):
        """Get all account orders; active, canceled, or filled.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#all-orders-user_data

        :param symbol: required
        :type symbol: str
        :param orderId: The unique order id
        :type orderId: int
        :param limit: Default 500; max 500.
        :type limit: int
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        .. code-block:: python

            [
                {
                    "symbol": "LTCBTC",
                    "orderId": 1,
                    "clientOrderId": "myOrder1",
                    "price": "0.1",
                    "origQty": "1.0",
                    "executedQty": "0.0",
                    "status": "NEW",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "side": "BUY",
                    "stopPrice": "0.0",
                    "icebergQty": "0.0",
                    "time": 1499827319559
                }
            ]

        :raises: BinanceRequestException, BinanceAPIException

        """
        return await self._get('allOrders', True, {'symbol': symbol})

    async def cancel_order(self, symbol: str, orderId: str):
        """Cancel an active order. Either orderId or origClientOrderId must be sent.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#cancel-order-trade

        :param symbol: required
        :type symbol: str
        :param orderId: The unique order id
        :type orderId: int
        :param origClientOrderId: optional
        :type origClientOrderId: str
        :param newClientOrderId: Used to uniquely identify this cancel. Automatically generated by default.
        :type newClientOrderId: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        .. code-block:: python

            {
                "symbol": "LTCBTC",
                "origClientOrderId": "myOrder1",
                "orderId": 1,
                "clientOrderId": "cancelMyOrder1"
            }

        :raises: BinanceRequestException, BinanceAPIException

        """
        return await self._delete('order', True, {'symbol': symbol, 'orderId': orderId})

    async def get_open_orders(self, symbol: str = None):
        """Get all open orders on a symbol.

        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#current-open-orders-user_data

        :param symbol: optional
        :type symbol: str
        :param recvWindow: the number of milliseconds the request is valid for
        :type recvWindow: int

        :returns: API response

        .. code-block:: python

            [
                {
                    "symbol": "LTCBTC",
                    "orderId": 1,
                    "clientOrderId": "myOrder1",
                    "price": "0.1",
                    "origQty": "1.0",
                    "executedQty": "0.0",
                    "status": "NEW",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "side": "BUY",
                    "stopPrice": "0.0",
                    "icebergQty": "0.0",
                    "time": 1499827319559
                }
            ]

        :raises: BinanceRequestException, BinanceAPIException

        """
        if symbol:
            return await self._get('openOrders', True, {'symbol': symbol})
        return await self._get('openOrders', True)

    async def create_listen_key(self):
        result = await self._post('userDataStream', False)
        return result['listenKey']

    async def keepalive_listen_key(self, listen_key: str):
        return await self._put('userDataStream', False, params={'listenKey': listen_key})

    async def close_listen_key(self, listen_key: str):
        return await self._delete('userDataStream', False, params={'listenKey': listen_key})

    async def ping(self):
        return await self._get('ping')
