import asyncio
import itertools
import logging
from decimal import Decimal
from typing import List, Dict, Optional

from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import markdown as md

import settings
from common import Balance
from exchanges.trade.base.account import BaseAccount
from exchanges.trade.base.exchange import BaseTradeExchange, SymbolTicker
from exchanges.trade.manager import trade_mgr
from utils import norm

logger = logging.getLogger(__name__)


def register_trade_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_balances, commands=['balances'])
    dp.register_message_handler(cmd_cancel, commands=['cancel'])


async def cmd_balances(message: types.Message):
    msg = []
    all_accounts = get_all_accounts()
    longest_asset: str = max(
        itertools.chain.from_iterable(
            a.balance.keys()
            for a in all_accounts
        ),
        key=len
    )

    msg.append(f'Assets that cost less than ₿{settings.BALANCE_SHOW_LIMIT_BTC} are ignored.\n')

    for owner, accounts in itertools.groupby(all_accounts, lambda x: x.owner):
        msg.append(md.hbold(owner))
        for account in accounts:
            exchange: BaseTradeExchange = account.trade_exchange
            msg.append(f'\t{exchange.name}')

            account_balances_msg = []
            balances: Dict[str, Balance] = account.balance
            logger.info('Owner %s, exchange %s, balances: %s', owner, exchange.name, balances)
            for asset in sorted(balances.keys()):
                balance = balances[asset]
                if check_cost(asset, balance.total(), account):
                    asset_balance = '\t\t{asset:<{width}} = {free}'.format(
                        asset=asset,
                        width=len(longest_asset),
                        free=norm(balance.free),
                    )

                    if balance.free != balance.total():
                        asset_balance = f'{asset_balance}/{norm(balance.total())}'

                    account_balances_msg.append(md.hcode(asset_balance))

            if account_balances_msg:
                msg.extend(account_balances_msg)
            else:
                msg.append(md.hitalic('\t\tno significant balances'))
        msg.append('')

    await message.reply(
        '\n'.join(msg)
    )


async def cmd_cancel(message: types.Message):
    all_accounts = get_all_accounts()
    tasks = []

    for owner, accounts in itertools.groupby(all_accounts, lambda x: x.owner):
        for account in accounts:
            tasks.append(cancel_orders_on_account(message, account))

    await asyncio.gather(*tasks)

    await message.reply('cancel finished')


async def cancel_orders_on_account(message: types.Message, account: BaseAccount):
    exchange: BaseTradeExchange = account.trade_exchange
    owner = account.owner

    logger.info('Fetching %s open orders on %s', owner, exchange.name)
    open_orders = await account.get_open_orders_id()
    logger.info('Got %d open orders for owner %s at %s', len(open_orders), owner, exchange.name)

    if len(open_orders) > 0:
        cancel_orders = await asyncio.gather(
            *[
                account.cancel_order(order_id, symbol)
                for order_id, symbol in open_orders
            ]
        )

        logger.info('Got cancel results for %s at %s: %s', owner, exchange.name, cancel_orders)
    else:
        logger.info('Nothing to cancel for %s at %s', owner, exchange.name)
        cancel_orders = []

    await message.reply(
        f'{owner}@{exchange.name}: canceled {len(cancel_orders)}/{len(open_orders)} orders'
    )


def get_all_accounts() -> List[BaseAccount]:
    return sorted(
        itertools.chain.from_iterable(e.accounts for e in trade_mgr.exchanges),
        key=lambda x: x.owner
    )


def check_cost(asset: str, total: Decimal, account: BaseAccount, convert_to='BTC') -> bool:
    cost_limit = Decimal(settings.BALANCE_SHOW_LIMIT_BTC)
    exchange = account.trade_exchange

    if norm(total) == '0':
        return False

    if asset == convert_to:
        return total >= cost_limit

    price = get_price(asset, convert_to, exchange)
    if price is None:
        return True

    cost = price * total

    if cost < cost_limit:
        logger.info(
            '%s %s balance is %s, too small. Price %s, cost %s. Skipping...',
            account.owner,
            asset,
            total,
            price,
            cost
        )
        return False

    return True


def get_price(asset: str, convert_to: str, exchange: BaseTradeExchange) -> Optional[Decimal]:
    if 'USD' in asset:
        btc_pair: str = exchange.make_pair(convert_to, asset)
    else:
        btc_pair: str = exchange.make_pair(asset, convert_to)

    ticker: SymbolTicker = exchange.tickers.get(btc_pair)
    if not ticker:
        logger.warning('%s ticker not found for exchange %s', btc_pair, exchange.name)
        return

    if 'USD' in asset:
        return Decimal(1) / ticker.price
    return ticker.price
