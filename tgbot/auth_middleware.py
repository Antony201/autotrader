import logging

from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

import settings


class AuthMiddleware(BaseMiddleware):
    def __init__(self, logger=__name__):
        if not isinstance(logger, logging.Logger):
            logger = logging.getLogger(logger)

        self.logger = logger

        self.authorized_users = settings.AUTHORIZED_USERS_TELEGRAM_IDS

        super().__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict):
        self.logger.info('New message: %s', message)
        try:
            user_id = message.from_user.id
        except AttributeError as e:
            self.logger.error('Unable to get user id: %s', e)
            raise CancelHandler()
        else:
            if user_id not in self.authorized_users:
                self.logger.warning('User is not authorized!')
                raise CancelHandler()
            self.logger.info('User is authorized.')
