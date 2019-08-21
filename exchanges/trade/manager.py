import asyncio
from itertools import groupby
from typing import List, Type

import credentials
import settings
from caller import Caller
from common import Symbol, NTCredential
from exchanges.trade.base.exchange import BaseTradeExchange
from exchanges.trade.binance.exchange import BinanceTradeExchange
from exchanges.trade.bittrex.exchange import BittrexTradeExchange
from exchanges.trade.huobi.exchange import HuobiTradeExchange
from log import BaseLog


class TradeExchangeManager(BaseLog):
    _credentials: List[NTCredential] = None
    exchanges: List[BaseTradeExchange] = []

    def __init__(self):
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[trade_mgr]'
        )
        self._trade_exchange_classes = [
            BinanceTradeExchange,
            BittrexTradeExchange,
            HuobiTradeExchange,
        ]

    async def init(self):
        await self._init_caller()
        await self._init_credentials()
        await self._init_exchanges()

    async def on_shutdown(self):
        for e in self.exchanges:
            await self.log('closing session')
            await e.http.close()

    async def _init_credentials(self):
        self._credentials = sorted(
            credentials.get_credentials(),
            key=lambda x: x.exchange_name
        )

    async def _init_exchanges(self):
        for exchange_name, creds in groupby(self._credentials, lambda x: x.exchange_name):
            trade_exchange_cls = self.get_trade_exchange_cls_by_name(exchange_name)

            if not trade_exchange_cls:
                await self.log('Unable to find trade exchange with name %r!', exchange_name)
                continue

            trade_exchange = trade_exchange_cls()

            await trade_exchange.init(creds)

            self.exchanges.append(trade_exchange)

    async def _init_caller(self):
        self.caller = Caller(
            settings.TWILIO_FROM_NUMBER,
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_KEY
        )

    def get_trade_exchange_cls_by_name(self, exchange_name: str) -> Type[BaseTradeExchange]:
        for exchange in self._trade_exchange_classes:
            if exchange().name == exchange_name:
                return exchange

    async def process_coin(self, trigger_exchange, coin: Symbol, price_change_limit: int):
        other_exchanges = [
            e for e in self.exchanges
            if e.name != trigger_exchange.name
        ]

        if not other_exchanges:
            await self.log(
                'coin %s exists only %s, nothing to buy :(',
                coin, trigger_exchange.name,
                send_tg=True
            )
            return

        if settings.DEBUG:
            await self.log('debug mode, not buying!', send_tg=True)
            return

        tasks = [
            e.buy(
                trigger_exchange,
                coin.symbol,
                price_change_limit
            )
            for e in other_exchanges
        ]

        await asyncio.gather(*tasks)


trade_mgr = TradeExchangeManager()
