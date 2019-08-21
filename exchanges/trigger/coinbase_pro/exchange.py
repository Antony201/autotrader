from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.coinbase_pro.part import ApiWalletsPart, ApiAnnouncementsPart, TwitterPart


class CoinbaseProTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
        'BNB': 75,
    }

    @property
    def name(self) -> str:
        return 'coinbase_pro'

    async def _init_parts(self):
        self._parts = [
            ApiWalletsPart(self),
            ApiAnnouncementsPart(self),
            TwitterPart(self)
        ]
