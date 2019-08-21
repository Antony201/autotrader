from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.binance.part import AnnouncementsAPIPart, ApiPairCoinsExchangePart, ApiPairCoinsPart, \
    ApiWalletsPicsPart, ApiWalletsPart


class BinanceTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
    }

    @property
    def name(self) -> str:
        return 'binance'

    async def _init_parts(self):
        self._parts = [
            ApiWalletsPart(self),
            ApiWalletsPicsPart(self),
            ApiPairCoinsPart(self),
            ApiPairCoinsExchangePart(self),
            AnnouncementsAPIPart(self),
        ]
