import asyncio
from abc import ABC, abstractmethod
from logging import ERROR
from typing import Set, AsyncGenerator

import settings
from common import CoinSource, Symbol
from log import BaseLog
from network import TooManyRequests, AsyncHttp
from twitter import TwitterPeonySingle


class BasePartException(Exception):
    def __init__(self, url, response):
        self.url = url
        self.response = response

    def __str__(self):
        return f'URL: {self.url!r}, response: {self.response!r}'


class BaseTriggerExchangePartAbstract(ABC):
    @property
    @abstractmethod
    def source(self) -> CoinSource:
        '''Returns part source.'''

    @abstractmethod
    async def get(self) -> Set[Symbol]:
        '''Returns coins.'''


class BaseTriggerExchangePart(BaseLog, BaseTriggerExchangePartAbstract, ABC):
    DELAY = 0

    def __init__(self, trigger_exchange):
        self._trigger_exchange = trigger_exchange
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[{self._trigger_exchange.name}][{self.source.value}]'
        )
        self.http = AsyncHttp()

    @property
    def price_change_limit(self):
        return settings.PRICE_CHANGE_LIMIT_IN_PERCENT

    @property
    def trigger_actions(self):
        return {'buy', 'call'}

    async def on_shutdown(self):
        await self.log('closing session')
        await self.http.close()

    async def check_part(self):
        while True:
            try:
                await asyncio.sleep(self.DELAY)
                coins = await self.get()
            except TooManyRequests as e:
                if not e.retry_after:
                    sleep_time = 60 * 10
                else:
                    sleep_time = e.retry_after + 60
                await self.log(
                    f'%s: too many requests, retry after %d (%d) seconds',
                    self.__class__.__name__, e.retry_after, sleep_time,
                    level=ERROR
                )
                await self.log(
                    f'%s: too many requests, retry after %d (%d) seconds',
                    self.__class__.__name__, e.retry_after, sleep_time,
                    level=ERROR, send_tg=True
                )
                await asyncio.sleep(sleep_time)
            except BasePartException as e:
                await self.log(str(e))
            except Exception as e:
                await self.log(f'Unknown error ({type(e).__name__}): {e}')
            else:
                await self._trigger_exchange.process_coins(self, coins)


class BaseTriggerExchangeGeneratorPartAbstract(ABC):
    @property
    @abstractmethod
    def source(self) -> CoinSource:
        '''Returns part source.'''

    @abstractmethod
    async def stream(self) -> AsyncGenerator[Set[Symbol], None]:
        '''Returns coins.'''


class BaseTriggerExchangeGeneratorPart(BaseLog, BaseTriggerExchangeGeneratorPartAbstract, ABC):
    def __init__(self, trigger_exchange):
        self._trigger_exchange = trigger_exchange
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[{self._trigger_exchange.name}][{self.source.value}]'
        )

        if not settings.TWITTER_ENABLED:
            self._logger.warning('twitter disabled')
            return

        self.client = TwitterPeonySingle(
            consumer_key=settings.TWITTER_CONSUMER_KEY,
            consumer_secret=settings.TWITTER_CONSUMER_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET
        )

    @property
    def price_change_limit(self):
        return settings.PRICE_CHANGE_LIMIT_IN_PERCENT

    @property
    def trigger_actions(self):
        return {'buy', 'call'}

    async def check_part(self):
        if not settings.TWITTER_ENABLED:
            self._logger.warning('twitter disabled')
            return
        async for coins in self.stream():
            await self._trigger_exchange.process_coins(self, coins)
