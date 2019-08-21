import asyncio
import base64
import gzip
import hashlib
import hmac
from collections import OrderedDict, defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Set
from urllib.parse import urlparse, urlencode

import ujson
import websockets

import exchange_libs.aiohuobi.client
from common import Balance
from exchanges.trade.base.account import BaseAccount


class HuobiAccount(BaseAccount):
    client: exchange_libs.aiohuobi.client.Client
    _WS_ACCOUNT_URL = 'wss://api.huobi.pro/ws/v1'

    async def _init_client(self):
        self.client = exchange_libs.aiohuobi.client.Client(
            self._credential.api_key,
            self._credential.api_secret
        )

    async def _init_balance(self):
        accounts = await self.client.accounts()
        self.account_id = accounts['data'][0]['id']
        balances = await self.client.balance(self.account_id)
        for symbol, balance in self._parse_account_balances(balances).items():
            await self.update_balance(symbol, balance)

    async def _prepare_ws_account_updates(self):
        return

    async def _create_account_ws_connection(self):
        self._ws_account = await websockets.connect(self._WS_ACCOUNT_URL)

    async def _ws_account_update_task(self):
        while True:
            await self.auth_ws()
            await self.ws_subscribe('accounts')
            await self.ws_subscribe('orders.*')
            try:
                async for msg in self._ws_account:
                    await self._process_account_update(self.decode_ws_payload(msg))
            except websockets.exceptions.ConnectionClosed as e:
                await self.log('Account websockets connection closed: %r, restarting...', e)
            except Exception as e:
                await self.log('Account websockets unknown error: %r', e)
            await self._create_account_ws_connection()

    async def _process_account_update(self, data: Dict):
        if 'op' in data and data['op'] == 'ping':
            msg = self.encode_ws_payload(
                {
                    'op': 'pong',
                    'ts': data['ts']
                }
            )
            await self._ws_account.send(msg)
            return

        if 'op' in data and data['op'] == 'sub':
            await self.log('subbed to %s', data.get('topic'))
            return

        topic = data.get('topic')

        if topic == 'accounts':
            await self._process_balance_update(data)
        elif isinstance(topic, str) and topic.startswith('orders'):
            await self._process_order_update(data)

    async def _process_balance_update(self, data: Dict[str, Any]):
        for symbol, balance in self._parse_account_balances_ws(data).items():
            await self.update_balance(symbol, balance)

    async def _process_order_update(self, data: Dict):
        await self.log('order report: %s', data)
        if data['data']['order-state'] == 'filled':
            await self.log('order report: %s', self._format_order(data), send_tg=True, silent=True)

    @staticmethod
    def _parse_account_balances(balances) -> Dict[str, Decimal]:
        result = defaultdict(dict)
        for i in balances['data']['list']:
            cur = i['currency'].upper()
            typ = i['type'].lower()
            result[cur][typ] = Decimal(i['balance'])

        return {
            currency: Balance(
                balances['trade'],
                balances['frozen']
            )
            for currency, balances in result.items()
            if balances['trade'] or balances['frozen']
        }

    def _parse_account_balances_ws(self, balances):
        result = defaultdict(dict)
        for i in balances['data']['list']:
            if i['account-id'] != self.account_id:
                continue
            cur = i['currency'].upper()
            typ = i['type'].lower()
            i[cur][typ] = Decimal(i['balance'])

        return {
            currency: Balance(
                balances['trade'],
                balances['frozen']
            )
            for currency, balances in result.items()
        }

    def _format_order(self, order: Dict) -> str:
        data = order['data']
        return self._compose_order_report(
            order_side='BUY' if 'buy' in data['order-type'] else 'SELL',
            qty=Decimal(data['order-amount']),
            price=Decimal(data['price']),
            pair=data['symbol'].upper(),
            total=Decimal(data['order-amount']) * Decimal(data['price'])
        )

    async def create_buy_order(self, symbol: str, qty: int, quote_amount_to_buy: Decimal = None):
        price = self.trade_exchange.tickers[symbol].price
        markup = self.trade_exchange.limit_order_markup_percent
        purchase_price = price / 100 * (100 + markup)

        price_filters = self.trade_exchange.price_filters[symbol]

        price_precision = price_filters['price_precision']
        amount_precision = price_filters['amount_precision']

        await self.log('purchase price %s', purchase_price)
        if price_precision == 0:
            purchase_price = purchase_price.to_integral()
        else:
            purchase_price = purchase_price.quantize(Decimal('.' + '0' * price_precision))
        await self.log('normalized purchase price %s', purchase_price)

        await self.log('amount %s', quote_amount_to_buy)
        if amount_precision == 0:
            quote_amount_to_buy = quote_amount_to_buy.to_integral()
        else:
            quote_amount_to_buy = quote_amount_to_buy.quantize(Decimal('.' + '0' * amount_precision))
        await self.log('normalized amount %s', quote_amount_to_buy)

        order_result = await self.client.buy_limit_order(
            self.account_id,
            quote_amount_to_buy,
            symbol.lower(),
            purchase_price
        )

        order_id = order_result['data']
        return order_id

    async def cancel_order(self, order_id: str, symbol: str = None):
        return await self.client.cancel_order(order_id)

    @staticmethod
    def decode_ws_payload(data):
        return ujson.loads(gzip.decompress(data).decode('utf-8'))

    @staticmethod
    def encode_ws_payload(data):
        return ujson.dumps(data)

    @staticmethod
    def get_ts():
        return datetime.utcnow().isoformat(timespec='seconds')

    async def auth_ws(self):
        params = OrderedDict(
            AccessKeyId=self._credential.api_key,
            SignatureMethod='HmacSHA256',
            SignatureVersion='2',
            Timestamp=self.get_ts(),
        )
        await self._ws_account.send(
            self.encode_ws_payload(
                {
                    **params,
                    **{
                        'Signature': self.generate_signature(params),
                        'op': 'auth'
                    }
                }
            )
        )
        await asyncio.sleep(1)

    def generate_signature(self, params):
        parsed_url = urlparse(self._WS_ACCOUNT_URL)

        method, host, path = 'GET', parsed_url.netloc, parsed_url.path

        payload = '\n'.join(
            [
                method,
                host,
                path,
                urlencode(params)
            ]
        )

        digest = hmac.new(
            self._credential.api_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).digest()

        return base64.b64encode(digest).decode()

    async def ws_subscribe(self, topic):
        await self._ws_account.send(
            self.encode_ws_payload(
                {
                    'op': 'sub',
                    'topic': topic,
                }
            )
        )

    async def get_open_orders_id(self) -> Set[str]:
        response = await self.client.get_open_orders(self.account_id)
        return {
            (str(i['id']), None)
            for i in response['data']
        }
