from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.telegram.part import TelegramTriggerPart, TelegramChannelUpbitKRWTriggerPart, \
    TelegramChannelUpbitBTCTriggerPart


class TelegramTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 70,
        'BNB': 70,
        'ETH': 70,
        'USDT': 70,
    }

    @property
    def name(self) -> str:
        return 'telegram'

    async def _init_parts(self):
        self._parts = [
            TelegramTriggerPart(self),
            TelegramChannelUpbitKRWTriggerPart(self),
            TelegramChannelUpbitBTCTriggerPart(self),
        ]
