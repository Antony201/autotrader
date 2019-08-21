import asyncio
import logging

from aiogram.utils.markdown import hbold, text, hcode

import settings
from coinmarketcap import CoinMarketCap
from exchanges.trade.manager import trade_mgr, TradeExchangeManager
from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.manager import trigger_mgr, TriggerExchangeManager
from mem import mem_watcher_tracemalloc, mem_watcher_pympler
from tgbot.bot import start_bot, bot
from tgbot.log import tg_log

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="[%(asctime)s] %(levelname)-8s [%(name)-s.%(funcName)-s:%(lineno)d] %(message)s",
)
logger = logging.getLogger(__name__)


async def on_shutdown():
    await trade_mgr.on_shutdown()
    await trigger_mgr.on_shutdown()
    await bot.close()


async def send_start_msg(trade_mgr: TradeExchangeManager, trigger_mgr: TriggerExchangeManager):
    msg = ''

    msg += 'Bot started.\n\n'

    enabled_phone_accounts = [c.name for c in trade_mgr.caller._accounts]
    msg += text(hbold('Enabled phone accounts: '), ', '.join(enabled_phone_accounts), '\n')

    msg += '\n'
    msg += hbold('Enabled trade accounts:')
    msg += '\n'
    for e in trade_mgr.exchanges:
        msg += hcode(f' {e.name.title()}: ')
        msg += ', '.join(a._credential.owner for a in e.accounts)
        msg += '\n'

    msg += '\n'
    msg += hbold('Enabled trigger parts:')
    msg += '\n'
    for e in trigger_mgr.exchanges:
        amounts = ', '.join(f'{k}: {v}%' for k, v in e._buy_amounts.items())
        msg += hcode(f' {e.name.title()}({amounts}): ')
        msg += ', '.join(type(p).__name__ for p in e._parts)
        msg += '\n'

    msg += '\n'
    msg += hbold('Ignored coins: ')
    msg += ', '.join(BaseTriggerExchange.EXCLUDED_COINS) + f', \'{BaseTriggerExchange.EXCLUDED_COINS_REGEX.pattern}\''
    msg += '\n'

    msg += '\n'
    msg += text(hbold('Limit order markup:'), f'{settings.LIMIT_ORDER_MARKUP}%')
    msg += '\n'

    msg += '\n'
    msg += text(hbold('Order cancel delay:'), f'{settings.ORDER_CANCEL_DELAY} seconds')
    msg += '\n'

    await tg_log.log(msg, True, False)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.create_task(mem_watcher_pympler())
    loop.create_task(mem_watcher_tracemalloc())

    logger.info('starting')

    cmc = CoinMarketCap(loop=loop)
    loop.run_until_complete(cmc.warmup())

    loop.run_until_complete(tg_log.init(loop))

    loop.run_until_complete(trade_mgr.init())

    loop.run_until_complete(trigger_mgr.init())

    loop.run_until_complete(send_start_msg(trade_mgr, trigger_mgr))

    # loop.run_until_complete(tg_log.log('bot started'))

    logger.info('started')

    start_bot(loop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(on_shutdown())
        logger.info('stopped')
