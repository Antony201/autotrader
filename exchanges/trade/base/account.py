import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Set

import settings
from common import NTCredential, Balance
from log import BaseLog
from utils import norm


class BaseAccountAbstract(ABC):
    @abstractmethod
    async def _init_client(self):
        '''Initializes and returns exchange API client.'''

    @abstractmethod
    async def _init_balance(self):
        '''Fetch balance from HTTP API at startup.'''

    @abstractmethod
    async def _prepare_ws_account_updates(self):
        '''Execute some misc tasks before scheduling account update process.'''

    @abstractmethod
    async def _create_account_ws_connection(self):
        '''Creates WS connection to account stream (balance & order updates).'''

    @abstractmethod
    async def _ws_account_update_task(self):
        ''''''

    @abstractmethod
    async def _process_account_update(self, data: Dict):
        ''''''

    @abstractmethod
    async def _process_balance_update(self, data: Dict):
        ''''''

    @abstractmethod
    async def _process_order_update(self, data: Dict):
        ''''''

    @staticmethod
    @abstractmethod
    def _format_order(order: Dict) -> str:
        ''''''

    @abstractmethod
    async def create_buy_order(self, symbol: str, qty: int, quote_amount_to_buy: Decimal = None):
        '''Creates buy order.'''

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str = None):
        '''Cancels order by id.'''

    @abstractmethod
    async def get_open_orders_id(self) -> Set[str]:
        '''Returns set of all open orders ids for this account.'''


class BaseAccount(BaseLog, BaseAccountAbstract, ABC):
    trade_exchange = None
    client: Any = None
    balance: Dict[str, Balance] = None

    _credential: NTCredential = None
    _ws_account = None

    def __init__(self, trade_exchange, credential: NTCredential):
        self.trade_exchange = trade_exchange
        self._credential = credential

        self.init_logger(
            f'{self.__module__}.{self.__class__.__name__}',
            f'[{self.trade_exchange.name}][{self._credential.owner}]'
        )

        self.balance = dict()

    async def init(self):
        await self.log('client init started')
        await self._init_client()
        await self.log('client init finished')

        await self.log('balance init started')
        await self._init_balance()
        await self.log('balance init finished')

        await self.log('prepare ws account started')
        await self._prepare_ws_account_updates()
        await self.log('prepare ws account finished')

        await self.log('creating account ws started')
        await self._create_account_ws_connection()
        await self.log('creating account ws finished')

        await self.log('creating account update task starting')
        asyncio.create_task(self._ws_account_update_task())
        await self.log('creating account update task finished')

    async def buy(self, trigger_exchange, pair: str, quote_symbol):
        amount_to_buy_percent = trigger_exchange.buy_amount_percent(quote_symbol)

        balance: Balance = self.balance[quote_symbol]

        quote_amount_to_buy = balance.free * amount_to_buy_percent / 100
        ticker = self.trade_exchange.tickers[pair]

        dirty_qty = quote_amount_to_buy / ticker.price

        qty = int(dirty_qty)

        await self.log(
            '[%s] %s quote amount %s, dirty qty %s, qty %s',
            pair, quote_symbol, quote_amount_to_buy, dirty_qty, qty
        )

        try:
            order_id = await self.create_buy_order(
                pair,
                qty,
                quote_amount_to_buy
            )
        except Exception as e:
            await self.log(
                '[%s] order create error (%s): %s',
                pair, type(e).__name__, e,
            )
            await self.log(
                '[%s] Unable to create order (%s): %s',
                pair, type(e).__name__, e,
                send_tg=True
            )
        else:
            asyncio.create_task(
                self.cancel_and_check_with_delay(
                    settings.ORDER_CANCEL_DELAY,  # seconds
                    order_id,
                    pair
                )
            )
            await self.log('[%s] placed order with id %s', pair, order_id)
            await self.log(
                '[%s] New buy order with id %s placed: %d %s for %s %s',
                pair, order_id, qty, pair, quote_amount_to_buy, quote_symbol,
                send_tg=True
            )

    async def cancel_and_check_with_delay(self, delay, order_id: str, symbol: str = None):
        await asyncio.sleep(delay)
        try:
            cancel_result = await self.cancel_order(order_id, symbol)
        except Exception as e:
            await self.log(
                '%s order cancel error (%s): %s',
                order_id, type(e).__name__, e,
                level=logging.ERROR,
            )
            await self.log(
                '%s order cancel error (%s): %s',
                order_id, type(e).__name__, e,
                level=logging.ERROR,
                send_tg=True
            )
        else:
            await self.log(
                '%s order cancel result: %s',
                order_id, cancel_result,
            )
            await self.log(
                '%s order cancel result: %s',
                order_id, cancel_result,
                send_tg=True
            )

    async def update_balance(self, symbol: str, balance: Balance) -> None:
        previous_balance = self.balance.get(symbol)
        if previous_balance != balance:
            await self.log('%s balance update: %s -> %s', symbol, previous_balance, balance)
            self.balance[symbol] = balance

    @staticmethod
    def _compose_order_report(order_side: str, qty: Decimal, price: Decimal, pair: str, total: Decimal):
        return f'{order_side} {pair} {norm(qty)}@{norm(price)} for {norm(total)}'

    @property
    def owner(self) -> str:
        return self._credential.owner
