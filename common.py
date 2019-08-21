from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import NamedTuple


class CoinSource(Enum):
    API_WALLET = 'API wallet'
    API_PAIR = 'API pair'
    API_UNOFFICIAL = 'API unofficial'
    SITE = 'Site'
    JS = 'JS'
    TWITTER = 'Twitter'
    TELEGRAM = 'Telegram'
    TG_CHNL_UPBIT_KRW = 'Jayden channel Upbit KRW'
    TG_CHNL_UPBIT_BTC = 'Jayden channel Upbit BTC'


class Symbol(NamedTuple):
    symbol: str
    source: CoinSource
    url: str = None


class NTCredential(NamedTuple):
    owner: str
    exchange_name: str
    api_key: str
    api_secret: str


@dataclass
class Balance:
    free: Decimal
    locked: Decimal

    def total(self) -> Decimal:
        return self.free + self.locked
