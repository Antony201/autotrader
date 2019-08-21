from exchanges.trigger.base.exchange import BaseTriggerExchange
from exchanges.trigger.coinbase.part import ApiAnnouncementsPart


class CoinbaseTriggerExchange(BaseTriggerExchange):
    _buy_amounts = {
        'BTC': 75,
        'ETH': 75,
        'USDT': 75,
        'BNB': 75,
    }

    @property
    def name(self) -> str:
        return 'coinbase'

    async def _init_parts(self):
        self._parts = [
            ApiAnnouncementsPart(self),
        ]
