import asyncio
from decimal import Decimal
from typing import Dict, Any, Set

import ujson
import websockets

import exchange_libs.aiobinance.client
from common import Balance
from exchanges.trade.base.account import BaseAccount


class BinanceAccount(BaseAccount):
    client: exchange_libs.aiobinance.client.Client
    keepalive_task: asyncio.Task = None

    async def _init_client(self):
        self.client = exchange_libs.aiobinance.client.Client(
            self._credential.api_key,
            self._credential.api_secret
        )

    async def _init_balance(self):
        account = await self.client.get_account()
        for symbol, balance in self._parse_account_balances(account, False).items():
            await self.update_balance(symbol, balance)

    async def _prepare_ws_account_updates(self):
        await self._init_listen_key()

    async def _init_listen_key(self):
        self._listen_key = await self.client.create_listen_key()
        task = asyncio.create_task(self._listenkey_keepalive())
        if self.keepalive_task is not None:
            await self.log('Found keepalive task: %s', self.keepalive_task)
            if not self.keepalive_task.cancelled():
                await self.log('Cancelling keepalive task: %s', self.keepalive_task)
                self.keepalive_task.cancel()
        self.keepalive_task = task
        await self.log('Keepalive task created: %s', self.keepalive_task)

    async def _listenkey_keepalive(self):
        interval = 60 * 5
        while True:
            await asyncio.sleep(interval)
            result = await self.client.keepalive_listen_key(self._listen_key)
            await self.log('Listen key keepalive result: %s', result)

    async def _create_account_ws_connection(self):
        while True:
            try:
                connection = await websockets.connect(f'wss://stream.binance.com:9443/ws/{self._listen_key}')
            except Exception as e:
                await self.log('Unable to create ws connection (%s): %s', type(e).__name__, e)
            else:
                self._ws_account = connection
                return

    async def _ws_account_update_task(self):
        while True:
            try:
                async for msg in self._ws_account:
                    await self._process_account_update(ujson.loads(msg))
            except websockets.exceptions.ConnectionClosed as e:
                await self.log('Account websockets connection closed: %r, restarting...', e)
            except Exception as e:
                await self.log('Account websockets unknown error: %r', e)
            await self._prepare_ws_account_updates()
            await self._create_account_ws_connection()

    async def _process_account_update(self, data: Dict):
        event = data.get('e')

        if event == 'outboundAccountInfo':
            await self._process_balance_update(data)
        elif event == 'executionReport':
            await self._process_order_update(data)

    async def _process_balance_update(self, data: Dict[str, Any]):
        for symbol, balance in self._parse_account_balances(data, True).items():
            await self.update_balance(symbol, balance)

    async def _process_order_update(self, data: Dict):
        await self.log('order report: %s', data)
        if data['X'] == 'FILLED':
            await self.log('order report: %s', self._format_order(data), send_tg=True, silent=True)

    @staticmethod
    def _parse_account_balances(account, ws=False) -> Dict[str, Balance]:
        if ws:
            ASSET, BALANCES, FREE, LOCKED = 'a', 'B', 'f', 'l'
        else:
            ASSET, BALANCES, FREE, LOCKED = 'asset', 'balances', 'free', 'locked'

        return {
            balance[ASSET]: Balance(
                Decimal(balance[FREE]),
                Decimal(balance[LOCKED])
            )

            for balance in account[BALANCES]
        }

    def _format_order(self, order: Dict) -> str:
        return self._compose_order_report(
            order_side=order['S'],
            qty=Decimal(order['q']),
            price=Decimal(order['Z']) / Decimal(order['z']),
            pair=order['s'],
            total=Decimal(order['Z'])
        )

    async def create_buy_order(self, symbol: str, qty: int, quote_amount_to_buy: Decimal = None):
        price = self.trade_exchange.tickers[symbol].price
        markup = self.trade_exchange.limit_order_markup_percent
        purchase_price = price / 100 * (100 + markup)
        await self.log('purchase price %s', purchase_price)

        order_result = await self.client.order_limit_buy(
            symbol,
            str(qty),
            purchase_price.quantize(Decimal('.000000')),
        )

        order_id = order_result['orderId']
        return order_id

    async def cancel_order(self, order_id: str, symbol: str = None):
        return await self.client.cancel_order(symbol, order_id)

    async def get_open_orders_id(self) -> Set[str]:
        orders = await self.client.get_open_orders()
        return {
            (str(i['orderId']), i['symbol'])
            for i in orders
        }
