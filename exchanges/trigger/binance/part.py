import re
from typing import Set
from urllib.parse import urlencode

from common import Symbol, CoinSource
from exchanges.trigger.base.part import BaseTriggerExchangePart, BasePartException


class BinancePartException(BasePartException):
    pass


class ApiWalletsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_UNOFFICIAL

    async def get(self) -> Set[Symbol]:
        url = 'https://www.binance.com/assetWithdraw/getAllAsset.html'
        response = await self.http.get(url)
        if not response or not isinstance(response, list) or not len(response):
            raise BinancePartException(url, response)

        return set(
            Symbol(
                i['assetCode'],
                CoinSource.API_UNOFFICIAL,
                url
            )
            for i in response
        )


class ApiWalletsPicsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_UNOFFICIAL

    async def get(self) -> Set[Symbol]:
        url = 'https://www.binance.com/dictionary/getAssetPic.html'
        response = await self.http.post(url)
        if 'data' not in response:
            raise BinancePartException(url, response)

        return set(
            Symbol(
                i['asset'],
                CoinSource.API_UNOFFICIAL,
                url
            )
            for i in response['data']
        )


class ApiPairCoinsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_UNOFFICIAL

    async def get(self) -> Set[Symbol]:
        url = 'https://www.binance.com/exchange/public/product'
        response = await self.http.get(url)
        if not response or 'data' not in response:
            raise BinancePartException(url, response)
        return set(
            Symbol(
                i['baseAsset'],
                CoinSource.API_PAIR,
                url
            )
            for i in response['data']
        )


class ApiPairCoinsExchangePart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_PAIR

    async def get(self) -> Set[Symbol]:
        url = 'https://api.binance.com/api/v1/exchangeInfo'
        response = await self.http.get(url)
        if not response or 'symbols' not in response:
            raise BinancePartException(url, response)
        return set(
            Symbol(
                i['baseAsset'],
                CoinSource.API_PAIR,
                url
            )
            for i in response['symbols']
        )


class AnnouncementsAPIPart(BaseTriggerExchangePart):
    # DELAY = 3.0
    REGEX = re.compile(r'\(([A-Za-z0-9]+)\)')

    @property
    def source(self) -> CoinSource:
        return CoinSource.SITE

    async def get(self) -> Set[Symbol]:
        search_words = ('lists', 'list')
        params = dict(
            page=1,
            rows=3,
            lang='en'
        )
        url = f'https://www.binance.com/public/getNotice.html?{urlencode(params)}'

        response = await self.http.post(url)
        if 'data' not in response:
            raise BinancePartException(url, response)

        symbols = set()
        for ann in response['data']:
            ann_title = ann['name'].strip().lower()
            if any(w in ann_title for w in search_words):
                for symbol in self.REGEX.findall(ann_title):
                    symbols.add(symbol.upper())

        return set(
            Symbol(
                symbol,
                CoinSource.SITE,
                url
            )
            for symbol in symbols
        )
