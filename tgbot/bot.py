import logging

from aiogram import Bot
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils.executor import start_polling

import settings
from tgbot.auth_middleware import AuthMiddleware
from tgbot.handlers.testlisting import register_testlisting_handlers
from tgbot.handlers.trade import register_trade_handlers
from tgbot.handlers.zdefault import register_default_handlers

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)


def register_middlewares(dp: Dispatcher):
    dp.middleware.setup(AuthMiddleware())
    dp.middleware.setup(LoggingMiddleware())


def register_handlers(dp: Dispatcher):
    register_testlisting_handlers(dp)
    register_trade_handlers(dp)

    register_default_handlers(dp)


async def on_startup(dp: Dispatcher):
    register_handlers(dp)
    register_middlewares(dp)


def start_bot(loop=None):
    start_polling(dp, skip_updates=True, on_startup=on_startup, loop=loop)
