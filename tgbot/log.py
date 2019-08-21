import asyncio
import logging

from aiogram import Bot
from aiogram.types import ParseMode
from aiogram.utils.markdown import quote_html

import settings


class TelegramLog:
    _logger: logging.Logger = None

    _prefix: str = None
    _queue: asyncio.Queue

    def __init__(self):
        self._queue = asyncio.Queue()
        self._logger = logging.getLogger('tg_log')
        self._bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
        self._channel_id = settings.LOG_CHANNEL_ID

    async def init(self, loop=None):
        loop = loop or asyncio.get_event_loop()
        loop.create_task(self._consume_tg_log())

    async def log(self, message, silent=False, quote=True):
        await self._queue.put(
            (message, silent, quote)
        )

    async def _consume_tg_log(self):
        while True:
            item = await self._queue.get()
            if item is None:
                break

            msg, silent, quote = item

            self._logger.debug('sending message to %s: %s', self._channel_id, item)
            await self._bot.send_message(
                self._channel_id,
                quote_html(msg) if quote else msg,
                disable_notification=silent
            )
            await asyncio.sleep(0.0)


tg_log = TelegramLog()
