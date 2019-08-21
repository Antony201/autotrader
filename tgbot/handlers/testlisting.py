from aiogram import types
from aiogram.dispatcher import Dispatcher

# from exchanges.trade.manager import trade_mgr
from common import CoinSource, Symbol
from exchanges.trigger.manager import trigger_mgr


def register_testlisting_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_delete_coin, commands=['delete_coin', 'dc'])
    dp.register_message_handler(cmd_fake_coin, commands=['fake_coin', 'fk'])
    # dp.register_message_handler(cmd_websockets_status, commands=['websocket_status', 'ws'])


async def cmd_delete_coin(message: types.Message):
    # msg = '\n'.join(
    #     f'{a._credential.owner} balance on {e.name}: {a.balance}'
    #     for e in trade_mgr.exchanges
    #     for a in e.accounts
    # )
    # return await message.reply(msg)
    args = message.text.split()[1:]
    if len(args) != 2:
        return await message.reply('Invalid arguments!')
    exchange_name, coin = args
    result = await trigger_mgr.drop_coin(exchange_name, coin)
    if not result:
        return await message.reply(f'Unable to drop coin {coin!r} from exchange {exchange_name!r}')
    await message.reply(f'Coin {coin!r} successfully dropped from exchange {exchange_name!r}.')


async def cmd_fake_coin(message: types.Message):
    _, *args = message.text.split()
    coin_name = str(args.pop(0))
    coin_name = coin_name.upper()

    trigger_exchange = None
    for e in trigger_mgr.exchanges:
        if e.name == 'telegram':
            trigger_exchange = e
            break
    if not trigger_exchange:
        return

    fake_part = None
    for p in trigger_exchange._parts:
        if p.source == CoinSource.TELEGRAM:
            fake_part = p

    if not fake_part:
        return

    fake_part.coins.add(
        Symbol(
            coin_name,
            CoinSource.TELEGRAM,
            'http://fake.telegram.url'
        )
    )

    await message.reply(f'Added {coin_name} to the fake trigger.')

# async def cmd_websockets_status(message: types.Message):
#     msg = ''
#     for e in trade_mgr.exchanges:
#         msg += e.name + '\n'
#         for a in e.accounts:
#             msg += a._credential.owner + str(a._ws_account.state.name) + '\n'
#         msg += '\n'
#     await message.reply(msg)
