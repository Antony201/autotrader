from decimal import Decimal
from typing import Dict, Set

import aiobittrex

from common import NTCredential
from exchanges.trade.base.exchange import BaseTradeExchange, SymbolTicker
from exchanges.trade.bittrex.account import BittrexAccount


class BittrexTradeExchange(BaseTradeExchange):
    async def init_price_filters(self):
        return

    async def price_filters_update_task(self):
        return

    @property
    def name(self) -> str:
        return 'bittrex'

    @property
    def buy_symbols(self) -> Set[str]:
        return {'BTC', 'ETH'}

    async def _init_account(self, exchange, credential: NTCredential):
        account = BittrexAccount(exchange, credential)

        await account.init()

        return account

    async def _init_ticker(self):
        tick_data = await self.ticker_24h()
        self.tickers = {
            data['MarketName']: SymbolTicker(
                self.calc_price_change_percent(data['Ask'], data['PrevDay']) if data['PrevDay'] else Decimal(0),
                Decimal(str(data['Ask']))
            )
            for data in tick_data['result']
        }

    async def _create_ticker_ws_connection(self):
        self._ws_client = aiobittrex.BittrexSocket()
        self._ws_tickers = await self._ws_client.create_ws()

    async def _ws_ticker_update_task(self):
        while True:
            try:
                async for msg in self._ws_client.listen_summary(ws=self._ws_tickers):
                    await self._process_ticker_update(msg)
            except Exception as e:
                await self.log('Ticker websockets unknown error: %r', e)
            await self._create_ticker_ws_connection()

    async def _process_ticker_update(self, data: Dict):
        tickers = data['deltas']
        for t in tickers:
            await self._process_ticker(t)

    async def _process_ticker(self, data: Dict):
        if data['ask'] and data['prev_day']:
            symbol = data['market_name']
            self.tickers[symbol] = SymbolTicker(
                self.calc_price_change_percent(data['ask'], data['prev_day']),
                Decimal(str(data['ask']))
            )
        else:
            await self.log('incorrect ticker: %s', data)

    @staticmethod
    def calc_price_change_percent(ask: float, prev_day: float):
        price_change = Decimal(str(ask)) / Decimal(str(prev_day))
        price_change_percent = (price_change - 1) * 100
        return Decimal(price_change_percent.quantize(Decimal('.01')))

    async def ticker_24h(self) -> Dict:
        return await self.http.get('https://bittrex.com/api/v1.1/public/getmarketsummaries')

    async def get_markets(self) -> Dict:
        return await self.http.get('https://bittrex.com/api/v1.1/public/getmarkets')

    @staticmethod
    def make_pair(base, quote):
        return f'{quote}-{base}'
