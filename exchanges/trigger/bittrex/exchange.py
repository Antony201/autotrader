from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.bittrex.part import ApiWalletsPart, TwitterPart, ApiPairsPart


class BittrexTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
    }

    @property
    def name(self) -> str:
        return 'bittrex'

    async def _init_parts(self):
        self._parts = [
            ApiWalletsPart(self),
            ApiPairsPart(self),
            TwitterPart(self)
        ]
