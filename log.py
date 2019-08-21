import asyncio
import logging

from tgbot.log import tg_log


class BaseLog:
    _logger: logging.Logger = None
    _prefix: str = None
    _queue = asyncio.Queue()

    async def log(self, message: str, *args, level: int = logging.INFO, send_tg: bool = False, silent: bool = False,
                  quote: bool = True):
        msg = self._prefix + ' ' + str(message) if self._prefix else str(message)

        if send_tg:
            return await tg_log.log(msg % args, silent, quote)

        self._logger.log(
            level,
            msg,
            *args
        )

    def init_logger(self, logger_name: str = None, prefix: str = ''):
        self._prefix = prefix
        self._logger = logging.getLogger(logger_name or __name__)
