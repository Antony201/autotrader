import asyncio
import collections
import logging
import re
from abc import ABC, abstractmethod
from typing import Set, List, Iterable, Dict

from aiogram.utils.markdown import hbold

import settings
from coinmarketcap import CoinMarketCap
from common import Symbol
from exchanges.trade.manager import trade_mgr
from exchanges.trigger.base.part import BaseTriggerExchangePart, BaseTriggerExchangeGeneratorPart
from log import BaseLog


class BaseTriggerExchangeAbstract(ABC):
    _buy_amounts: Dict[str, int]

    @property
    @abstractmethod
    def name(self) -> str:
        '''Returns exchange name.'''

    @abstractmethod
    async def _init_parts(self):
        '''init exchange parts'''


class BaseTriggerExchange(BaseLog, BaseTriggerExchangeAbstract, ABC):
    known_coins: Set = None
    call_coins: Set = None
    _parts: List[BaseTriggerExchangePart] = []
    EXCLUDED_COINS = {
        'BTC',
        'ETH',
        'KRW',
        'PAX',
        'DAI',
        'BCHABC',
        'BCHSV',
        'PST',
        'BTT',
        'CELR'
    }
    EXCLUDED_COINS_REGEX = re.compile(r'\w?USD\w?')

    def __init__(self):
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[{self.name}]'
        )
        self.cmc = CoinMarketCap()

    def buy_amount_percent(self, symbol: str) -> int:
        return self._buy_amounts.get(symbol)

    async def on_shutdown(self):
        for part in self._parts:
            if isinstance(part, BaseTriggerExchangePart):
                await part.on_shutdown()

    def get_symbols(self, coins: Iterable[Symbol]):
        result = set()

        for c in coins:
            if isinstance(c, Symbol):
                result.add(c.symbol)
            elif isinstance(c, collections.Iterable):
                result.update(self.get_symbols(c))

        return result

    async def init(self):
        await self._init_parts()
        await self._init_coins()

    async def _init_coins(self):
        self.known_coins = set()
        self.call_coins = set()

        exclude_parts = set()

        for part in self._parts:
            try:
                if isinstance(part, BaseTriggerExchangeGeneratorPart):
                    await self.log('%s: is a generator, skipping...', part.__class__.__name__)
                    continue

                coins = await part.get()
            except Exception as e:
                await self.log(
                    '%s: unable to init coins; %s, %s',
                    part.__class__.__name__, type(e).__name__, e,
                    send_tg=True
                )
                exclude_parts.add(part)
            else:
                part_coins = self.get_symbols(coins)
                if part.trigger_actions == {'call'}:
                    self.call_coins.update(part_coins)
                else:
                    self.known_coins.update(part_coins)
                await self.log(
                    '%s: initial launch, added %d coins',
                    part.__class__.__name__, len(part_coins),
                )

        if exclude_parts:
            await self.log('excluded parts %s', exclude_parts, level=logging.WARNING)

        self._parts = [p for p in self._parts if p not in exclude_parts]

    async def schedule_parts_check(self):
        for part in self._parts:
            asyncio.create_task(part.check_part())

    async def process_coins(self, part: BaseTriggerExchangePart, coins: Set[Symbol]):
        if part.trigger_actions == {'call'}:
            new_coins = set(
                c for c in coins
                if c.symbol not in self.call_coins and
                c.symbol not in self.EXCLUDED_COINS and
                not self.EXCLUDED_COINS_REGEX.match(c.symbol)
            )
            self.call_coins.update(self.get_symbols(new_coins))
        else:
            new_coins = set(
                c for c in coins
                if c.symbol not in self.known_coins and
                c.symbol not in self.EXCLUDED_COINS and
                not self.EXCLUDED_COINS_REGEX.match(c.symbol)
            )
            self.known_coins.update(self.get_symbols(new_coins))

        if not new_coins:
            return

        await self.log('got %d new coins: %s', len(new_coins), '\n'.join(str(c) for c in new_coins))

        for coin in new_coins:
            cmc_result = await self.cmc.get_name_and_url(coin.symbol)
            if not cmc_result:
                coin_title = hbold(coin.symbol)
            else:
                name, url = cmc_result
                url = url + '#markets'
                coin_title = f'{name} ({coin.symbol}):\n{url}'

            coin_info = f'{coin.source.value}, {coin.url}'

            await self.log(
                f'listed {coin_title} ({coin_info})',
                send_tg=True,
                quote=False
            )

        if not settings.DEBUG and 'call' in part.trigger_actions:
            asyncio.create_task(trade_mgr.caller.call_all())

        if settings.DISABLE_BUY:
            return  # temporary

        if 'buy' in part.trigger_actions:
            for coin in new_coins:
                await self._process_coin(coin, part.price_change_limit)

    async def _process_coin(self, coin: Symbol, price_change_limit: int):
        await trade_mgr.process_coin(self, coin, price_change_limit)
