from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.bithumb.part import ApiWalletsPart, \
    ApiWalletsJSONPart, ApiPairCoinsPart, AnnouncementsAPIPart


class BithumbTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
    }

    @property
    def name(self) -> str:
        return 'bithumb'

    async def _init_parts(self):
        self._parts = [
            ApiWalletsPart(self),
            ApiWalletsJSONPart(self),
            ApiPairCoinsPart(self),
            AnnouncementsAPIPart(self),
        ]
