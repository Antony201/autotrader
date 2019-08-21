import asyncio
import gzip
import ujson
from decimal import Decimal
from typing import Dict, Set

import websockets

from common import NTCredential
from exchanges.trade.base.exchange import BaseTradeExchange, SymbolTicker
from exchanges.trade.huobi.account import HuobiAccount


class HuobiTradeExchange(BaseTradeExchange):
    async def init_price_filters(self):
        response = await self.http.get('https://api.huobi.pro/v1/common/symbols')
        data = response['data']
        for i in data:
            s = i['symbol'].upper()
            self.price_filters[s] = {
                'price_precision': i['price-precision'],
                'amount_precision': i['amount-precision'],
            }

    async def price_filters_update_task(self):
        while True:
            await asyncio.sleep(60 * 60)
            response = await self.http.get('https://api.huobi.pro/v1/common/symbols')
            data = response['data']
            for i in data:
                s = i['symbol'].upper()
                self.price_filters[s] = {
                    'price_precision': i['price-precision'],
                    'amount_precision': i['amount-precision'],
                }

    @property
    def name(self) -> str:
        return 'huobi'

    @property
    def buy_symbols(self) -> Set[str]:
        return {'BTC', 'ETH'}

    async def _init_account(self, exchange, credential: NTCredential):
        account = HuobiAccount(exchange, credential)

        try:
            await account.init()
        except:
            await account.client.close_session()
            raise

        return account

    async def _init_ticker(self):
        tickers = await self.ticker_24h()
        tickers_data = tickers['data']
        self.tickers = {
            i['symbol'].upper():
                SymbolTicker(
                    self.calc_price_change_percent(i['close'], i['open']),
                    Decimal(str(i['close']))
                )
            for i in tickers_data
            if i['close'] and i['open']
        }

    async def _create_ticker_ws_connection(self):
        self._ws_tickers = await websockets.connect('wss://api.huobi.pro/ws')
        await self._ws_tickers.send(
            self.encode_ws_payload(
                {
                    'sub': 'market.tickers',
                }
            )
        )

    async def _ws_ticker_update_task(self):
        while True:
            try:
                async for msg in self._ws_tickers:
                    await self._process_ticker_update(self.decode_ws_payload(msg))
            except websockets.exceptions.ConnectionClosed as e:
                await self.log('Ticker websockets connection closed: %r, restarting...', e)
            except Exception as e:
                await self.log('Ticker websockets unknown error: %r', e)
            await self._create_ticker_ws_connection()

    async def _process_ticker_update(self, data: Dict):
        if 'ping' in data:
            await self._ws_tickers.send(
                self.encode_ws_payload(
                    {'pong': data['ping']}
                )
            )
            return

        if 'subbed' in data:
            await self.log('%s subscription status: %s', data['subbed'], data['status'])
            return

        if 'ch' in data and data['ch'] == 'market.tickers':
            for ticker in data['data']:
                self._process_ticker(ticker)

    def _process_ticker(self, data: Dict):
        if not data['open'] or not data['close']:
            return
        symbol = data['symbol'].upper()
        self.tickers[symbol] = SymbolTicker(
            self.calc_price_change_percent(data['close'], data['open']),
            Decimal(str(data['close']))
        )

    async def ticker_24h(self) -> Dict:
        return await self.http.get('https://api.huobi.pro/market/tickers')

    @staticmethod
    def calc_price_change_percent(close_price: float, open_price: float):
        if not close_price or not open_price:
            return Decimal(0)
        price_change = Decimal(str(close_price)) / Decimal(str(open_price))
        price_change_percent = (price_change - 1) * 100
        return Decimal(price_change_percent.quantize(Decimal('.01')))

    @staticmethod
    def decode_ws_payload(data):
        return ujson.loads(gzip.decompress(data).decode('utf-8'))

    @staticmethod
    def encode_ws_payload(data):
        return ujson.dumps(data)

    @staticmethod
    def make_pair(base, quote):
        return f'{base}{quote}'
