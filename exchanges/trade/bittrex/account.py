from decimal import Decimal
from typing import Dict, Set

import aiobittrex

from common import Balance
from exchanges.trade.base.account import BaseAccount
from exchanges.trade.base.exchange import BaseTradeExchange


class BittrexAccount(BaseAccount):
    client: aiobittrex.BittrexAPI

    exchange: BaseTradeExchange

    async def _init_client(self):
        self.client = aiobittrex.BittrexAPI(
            self._credential.api_key,
            self._credential.api_secret
        )

    async def _init_balance(self):
        balance_response = await self.client.get_balances()
        for symbol, balance in self._parse_account_balances(balance_response).items():
            await self.update_balance(symbol, balance)

    async def _prepare_ws_account_updates(self):
        return

    async def _create_account_ws_connection(self):
        self._ws_client = aiobittrex.BittrexSocket(
            self._credential.api_key,
            self._credential.api_secret,
        )
        self._ws_account = await self._ws_client.create_ws()

    async def _ws_account_update_task(self):
        while True:
            try:
                async for msg in self._ws_client.listen_account(ws=self._ws_account):
                    await self._process_account_update(msg)
            except Exception as e:
                await self.log('Account websockets unknown error: %r', e)
            await self._create_account_ws_connection()

    async def _process_account_update(self, data):
        if 'delta' in data and 'balance' in data['delta'] and 'available' in data['delta']:
            await self._process_balance_update(data)
        elif 'order' in data:
            await self._process_order_update(data)

    async def _process_balance_update(self, data: Dict):
        delta = data['delta']
        currency = delta.get('currency', '').upper()
        if not currency:
            return await self.log('No currency at update %s', data)
        available = delta.get('available')
        if available is None:
            return await self.log('No available balance at update %s', data)
        else:
            available = Decimal(str(available))
        balance = delta.get('balance')
        if balance is None:
            return await self.log('No balance at update %s', data)
        else:
            locked = Decimal(str(balance)) - available

        await self.update_balance(
            currency,
            Balance(available, locked)
        )

    async def _process_order_update(self, data: Dict):
        await self.log('order report: %s', data['order'])
        if data['order']['closed'] and not data['order']['cancel_initiated']:
            await self.log('order report: %s', self._format_order(data['order']), send_tg=True, silent=True)

    @staticmethod
    def _parse_account_balances(balances) -> Dict[str, Balance]:
        return {
            balance['Currency']: Balance(
                Decimal(str(balance['Available'] or 0)),
                Decimal(str(balance['Balance'] or 0)) - Decimal(str(balance['Available'] or 0))
            )

            for balance in balances
        }

    def _format_order(self, order: Dict) -> str:
        return self._compose_order_report(
            order_side='BUY' if 'BUY' in order['order_type'] else 'SELL',
            qty=Decimal(order['quantity']),
            price=Decimal(order['price_per_unit']),
            pair=order['exchange'],
            total=Decimal(order['price'])
        )

    async def create_buy_order(self, symbol: str, qty: int, quote_amount_to_buy: Decimal = None):
        price = self.trade_exchange.tickers[symbol].price
        markup = self.trade_exchange.limit_order_markup_percent
        purchase_price = price / 100 * (100 + markup)
        await self.log('purchase price %s', purchase_price)
        order_result = await self.client.buy_limit(
            symbol,
            qty,
            purchase_price.quantize(Decimal('.000000')),
        )
        order_id = order_result['uuid']
        return order_id

    async def cancel_order(self, order_id: str, symbol: str = None):
        return await self.client.cancel_order(order_id)

    async def get_open_orders_id(self) -> Set[str]:
        response = await self.client.get_open_orders()
        return {
            (str(i['OrderUuid']), None)
            for i in response
        }
