from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.upbit.part import ApiPairsPart, ApiPairsBTCOnlyPart


class UpbitTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
        'BNB': 75,
    }

    @property
    def name(self) -> str:
        return 'upbit'

    async def _init_parts(self):
        self._parts = (
            ApiPairsPart(self),
            # AnnouncementsPart(self),
            ApiPairsBTCOnlyPart(self)
        )
