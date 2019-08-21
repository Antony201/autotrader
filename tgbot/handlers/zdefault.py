import re
from logging import getLogger
from pathlib import Path
from typing import Set, Optional

from aiogram import types, Dispatcher

import settings
from common import CoinSource, Symbol
from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.manager import trigger_mgr
from exchanges.trigger.telegram.part import TelegramTriggerPart

logger = getLogger(__name__)


def register_default_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_help, commands=['help'])
    dp.register_message_handler(default_handler)
    dp.register_channel_post_handler(channel_handler)


async def cmd_help(message: types.Message):
    with open(Path().cwd() / Path('tgbot', 'texts', 'help.html')) as f:
        await message.reply(f.read())


async def default_handler(message: types.Message):
    return await message.reply(f'Unknown command, please check /help')


async def channel_handler(message: types.Message):
    if message.chat.id != settings.LISTEN_CHANNEL_ID:
        return

    msg = message.text

    symbols_btc = extract_symbols_endpoint_btc(msg)
    symbols_krw = extract_symbols_endpoint_krw(msg) | extract_symbols_keywords(msg)

    if not symbols_btc and not symbols_krw:
        logger.info('No symbols found in message: %s', msg)
        return

    trigger_name = 'telegram'
    trigger_exchange = get_trigger_exchange(trigger_name)
    if not trigger_exchange:
        logger.error('No trigger exchange with name %s found!', trigger_name)
        return

    btc_part = get_part(trigger_exchange, CoinSource.TG_CHNL_UPBIT_BTC)
    krw_part = get_part(trigger_exchange, CoinSource.TG_CHNL_UPBIT_KRW)

    await add_symbol(btc_part, symbols_btc, CoinSource.TG_CHNL_UPBIT_BTC, message)
    await add_symbol(krw_part, symbols_krw, CoinSource.TG_CHNL_UPBIT_KRW, message)


def get_trigger_exchange(name: str) -> Optional[BaseTriggerExchange]:
    trigger_exchange = None
    for e in trigger_mgr.exchanges:
        if e.name == name:
            trigger_exchange = e
            break
    return trigger_exchange


def get_part(trigger_exchange: BaseTriggerExchange, part_source: CoinSource) -> Optional[TelegramTriggerPart]:
    part = None
    for p in trigger_exchange._parts:
        if p.source == part_source:
            part = p
            break
    return part


async def add_symbol(part: TelegramTriggerPart, symbols: Set[str], src: CoinSource, message: types.Message) -> None:
    if not part:
        await message.reply(f'No symbols found for part {part}.')
        return
    for symbol in symbols:
        part.coins.add(
            Symbol(
                symbol,
                src,
                'http://from.jayden.channel'
            )
        )
        await message.reply(f'Added {symbol} for part {part.source}.')


def extract_symbols_keywords(msg: str) -> Set[str]:
    required_words = (
        '이벤트',
        '원화',
    )

    if not any(word in msg for word in required_words):
        return set()

    RE_SYMBOL_IN_BRACKETS = re.compile(r'\(.*?([A-Z0-9]{2,}).*?\)')

    return filter_blacklist(
        set(i for i in RE_SYMBOL_IN_BRACKETS.findall(msg))
    )


def extract_symbols_endpoint_btc(msg: str) -> Set[str]:
    if 'Upbit Endpoint #' not in msg:
        return set()

    RE_DASH_BTC = re.compile(r'BTC-([A-Z0-9]+)')  # BTC-ATOM → ATOM
    RE_SLASH_BTC = re.compile(r'([A-Z0-9]+)/BTC')  # ATOM/BTC → ATOM

    btc_symbols = set(RE_SLASH_BTC.findall(msg)) | set(RE_DASH_BTC.findall(msg))

    return filter_whitelist(btc_symbols)


def extract_symbols_endpoint_krw(msg: str) -> Set[str]:
    if 'Upbit Endpoint #' not in msg:
        return set()

    RE_DASH_KRW = re.compile(r'KRW-([A-Z0-9]+)')  # KRW-ATOM → ATOM
    RE_SLASH_KRW = re.compile(r'([A-Z0-9]+)/KRW')  # ATOM/KRW → ATOM

    krw_symbols = set(RE_SLASH_KRW.findall(msg)) | set(RE_DASH_KRW.findall(msg))

    return filter_blacklist(krw_symbols)


def filter_blacklist(symbols: Set[str]) -> Set[str]:
    return symbols.difference(settings.SYMBOLS_BLACK_LIST)


def filter_whitelist(symbols: Set[str]) -> Set[str]:
    return symbols.intersection(settings.SYMBOLS_WHITE_LIST)
