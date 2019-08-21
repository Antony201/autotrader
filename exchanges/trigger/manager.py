import asyncio
from typing import List

from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.coinbase.exchange import CoinbaseTriggerExchange
from exchanges.trigger.coinbase_pro.exchange import CoinbaseProTriggerExchange
from exchanges.trigger.telegram.exchange import TelegramTriggerExchange
from exchanges.trigger.upbit.exchange import UpbitTriggerExchange
from log import BaseLog


class TriggerExchangeManager(BaseLog):
    exchanges: List[BaseTriggerExchange] = None

    def __init__(self):
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            '[trigger_mgr]'
        )
        self.trigger_exchanges = [
            # BinanceTriggerExchange,
            # BittrexTriggerExchange,
            # BithumbTriggerExchange,
            CoinbaseTriggerExchange,
            CoinbaseProTriggerExchange,
            UpbitTriggerExchange,
            TelegramTriggerExchange
        ]

    async def init(self):
        await self._init_exchanges()
        await self._init_coins()
        await self._schedule_exchange_parts_check()

    async def on_shutdown(self):
        for e in self.exchanges:
            await self.log('closing %s sessions', e.name)
            await e.on_shutdown()

    async def _init_exchanges(self):
        self.exchanges = [
            e()
            for e in self.trigger_exchanges
        ]

    async def _init_coins(self):
        await asyncio.gather(
            *[
                e.init()
                for e in self.exchanges
            ]
        )

    async def _schedule_exchange_parts_check(self):
        for e in self.exchanges:
            await e.schedule_parts_check()

    async def drop_coin(self, exchange_name: str, coin: str):
        c = coin.upper()
        for e in self.exchanges:
            if e.name == exchange_name:
                if c in e.known_coins:
                    e.known_coins.discard(c)
                    return True


trigger_mgr = TriggerExchangeManager()
