import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Iterator, NamedTuple, Set

import settings
from common import NTCredential
from exchanges.trade.base.account import BaseAccount
from log import BaseLog
from network import AsyncHttp


class SymbolTicker(NamedTuple):
    price_change_percent: Decimal
    price: Decimal


class BaseTradeExchangeAbstract(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        '''Returns exchange name.'''

    @property
    @abstractmethod
    def buy_symbols(self) -> Set[str]:
        '''Returns supported exchange symbols for buy with available balance.'''

    @abstractmethod
    async def _init_account(self, exchange, credential: NTCredential):
        '''Returns BaseAccount instance.'''

    @abstractmethod
    async def _init_ticker(self):
        '''Initializes tickers via http api.'''

    @abstractmethod
    async def _create_ticker_ws_connection(self):
        '''Returns websocket connection to tickers websockets API.'''

    @abstractmethod
    async def _ws_ticker_update_task(self):
        ''''''

    @abstractmethod
    async def _process_ticker_update(self, data: Dict):
        ''''''

    @abstractmethod
    async def _process_ticker(self, data: Dict):
        '''Process ticker updates from websockets API.'''

    @staticmethod
    @abstractmethod
    def make_pair(base, quote):
        ''''''

    @abstractmethod
    async def init_price_filters(self):
        ''''''

    @abstractmethod
    async def price_filters_update_task(self):
        ''''''


class BaseTradeExchange(BaseLog, BaseTradeExchangeAbstract, ABC):
    accounts: List[BaseAccount] = None
    tickers: Dict[str, SymbolTicker] = None
    _ws_tickers = None
    http: AsyncHttp = None

    def __init__(self):
        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[{self.name}]'
        )
        self.accounts = []
        self.tickers = {}
        self.price_filters = {}

    @property
    def limit_order_markup_percent(self) -> int:
        return settings.LIMIT_ORDER_MARKUP

    async def init(self, credentials: Iterator[NTCredential]):
        await self.log('init session started')
        await self.init_session()
        await self.log('init session finished')

        await self.log('init accounts started')
        await self.init_accounts(credentials)
        await self.log('init accounts finished')

        await self.log('init ticker started')
        await self._init_ticker()
        await self.log('init ticker finished')

        await self.log('init price filters started')
        await self.init_price_filters_and_task()
        await self.log('init price filters finished')

        await self.log('init ticker ws started')
        await self.init_ticker_ws()
        await self.log('init ticker ws finished')

    async def init_ticker_ws(self):
        await self.log('create ticker ws started')
        await self._create_ticker_ws_connection()
        await self.log('create ticker ws finished')

        await self.log('creating ticker update task started')
        asyncio.create_task(self._ws_ticker_update_task())
        await self.log('creating ticker update task finished')

    async def init_price_filters_and_task(self):
        await self.log('init price filters started')
        await self.init_price_filters()
        await self.log('init price filters finished')

        await self.log('create price filters update task started')
        asyncio.create_task(self.price_filters_update_task())
        await self.log('create price filters update task finished')

    async def init_accounts(self, credentials: Iterator[NTCredential]):
        for credential in credentials:
            try:
                account = await self._init_account(self, credential)
            except Exception as e:
                logging.getLogger(__name__).exception(e)
                await self.log(
                    'Unable to init %s client (%s): %s',
                    credential.owner, type(e).__name__, e,
                    level=logging.WARNING
                )
                await self.log(
                    'Unable to init %s client (%s): %s',
                    credential.owner, type(e).__name__, e,
                    level=logging.WARNING,
                    send_tg=True
                )
            else:
                self.accounts.append(account)

    async def init_session(self):
        self.http = AsyncHttp()

    async def buy(self, trigger_exchange, symbol: str, price_change_limit: int):
        tasks = [
            self.buy_pair(
                trigger_exchange,
                self.make_pair(symbol, quote_symbol),
                quote_symbol,
                price_change_limit
            )
            for quote_symbol in self.buy_symbols
        ]
        await asyncio.gather(*tasks)

    async def buy_pair(self, trigger_exchange, pair: str, quote_symbol: str, price_change_limit: int):
        ticker = self.tickers.get(pair)

        if not ticker:
            return await self.log('Pair %s not found, skipping...', pair, send_tg=True)

        await self.log(
            '%s buy amount percent is %s%%',
            trigger_exchange.name, trigger_exchange.buy_amount_percent(quote_symbol)
        )

        await self.log('Pair %s ticker: %s, limit is %s', pair, ticker, price_change_limit)
        await self.log('Pair %s ticker: %s, limit is %s', pair, ticker, price_change_limit, send_tg=True)
        if ticker.price_change_percent > price_change_limit:
            return await self.log(
                'Pair %s 24hr price change %s%% > %d%%, skipping...',
                pair, ticker.price_change_percent, price_change_limit,
                send_tg=True
            )

        for a in self.accounts:
            asyncio.create_task(
                a.buy(
                    trigger_exchange,
                    pair,
                    quote_symbol
                )
            )
