import ujson
from decimal import Decimal
from typing import Dict, Set

import websockets

from common import NTCredential
from exchanges.trade.base.exchange import BaseTradeExchange, SymbolTicker
from exchanges.trade.binance.account import BinanceAccount


class BinanceTradeExchange(BaseTradeExchange):
    async def init_price_filters(self):
        return

    async def price_filters_update_task(self):
        return

    @property
    def name(self) -> str:
        return 'binance'

    @property
    def buy_symbols(self) -> Set[str]:
        return {'BTC', 'ETH', 'USDT', 'BNB'}

    async def _init_account(self, exchange, credential: NTCredential):
        account = BinanceAccount(exchange, credential)

        await account.init()

        return account

    async def _init_ticker(self):
        self.tickers = {
            data['symbol']:
                SymbolTicker(
                    Decimal(data['priceChangePercent']),
                    Decimal(data['askPrice'])
                )
            for data in await self.ticker_24h()
        }

    async def _create_ticker_ws_connection(self):
        self._ws_tickers = await websockets.connect('wss://stream.binance.com:9443/ws/!ticker@arr')

    async def _ws_ticker_update_task(self):
        while True:
            try:
                async for msg in self._ws_tickers:
                    self._process_ticker_update(ujson.loads(msg))
            except websockets.exceptions.ConnectionClosed as e:
                await self.log('Ticker websockets connection closed: %r, restarting...', e)
            except Exception as e:
                await self.log('Ticker websockets unknown error: %r', e)
            await self._create_ticker_ws_connection()

    def _process_ticker_update(self, data: Dict):
        for ticker in data:
            self._process_ticker(ticker)

    def _process_ticker(self, data: Dict):
        symbol = data['s']
        self.tickers[symbol] = SymbolTicker(
            Decimal(data['P']),
            Decimal(data['a'])
        )

    async def ticker_24h(self) -> Dict:
        return await self.http.get('https://api.binance.com/api/v1/ticker/24hr')

    async def exchange_info(self) -> Dict:
        return await self.http.get('https://api.binance.com/api/v1/exchangeInfo')

    @staticmethod
    def make_pair(base, quote):
        return f'{base}{quote}'
