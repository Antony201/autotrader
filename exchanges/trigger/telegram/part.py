from typing import Set

import settings
from common import CoinSource, Symbol
from exchanges.trigger.base.part import BasePartException, BaseTriggerExchangePart


class TelegramPartException(BasePartException):
    pass


class TelegramTriggerPart(BaseTriggerExchangePart):
    coins = set()

    @property
    def source(self) -> CoinSource:
        return CoinSource.TELEGRAM

    async def get(self) -> Set[Symbol]:
        result = self.coins
        self.coins = set()
        return result


class TelegramChannelUpbitKRWTriggerPart(BaseTriggerExchangePart):
    coins = set()

    @property
    def price_change_limit(self):
        return settings.UPBIT_KRW_PRICE_CHANGE_LIMIT

    @property
    def source(self) -> CoinSource:
        return CoinSource.TG_CHNL_UPBIT_KRW

    async def get(self) -> Set[Symbol]:
        result = self.coins
        self.coins = set()
        return result


class TelegramChannelUpbitBTCTriggerPart(BaseTriggerExchangePart):
    coins = set()

    @property
    def price_change_limit(self):
        return settings.UPBIT_BTC_PRICE_CHANGE_LIMIT

    @property
    def source(self) -> CoinSource:
        return CoinSource.TG_CHNL_UPBIT_BTC

    async def get(self) -> Set[Symbol]:
        result = self.coins
        self.coins = set()
        return result
