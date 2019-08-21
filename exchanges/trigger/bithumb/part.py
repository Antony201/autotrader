import re
from typing import Set

from common import Symbol, CoinSource
from exchanges.trigger.base.part import BaseTriggerExchangePart, BasePartException


class BithumbPartException(BasePartException):
    pass


class ApiWalletsPart(BaseTriggerExchangePart):
    @property
    def trigger_actions(self):
        return {'call'}

    @property
    def source(self) -> CoinSource:
        return CoinSource.API_WALLET

    async def get(self) -> Set[Symbol]:
        url = 'https://www.bithumb.com/trade/getAsset/DASH'  # idk why DASH
        response = await self.http.get(url, headers={'X-Requested-With': 'XMLHttpRequest'})
        if not response or response['error'] != '0000':
            raise BithumbPartException(url, response)

        return set(
            Symbol(
                i,
                CoinSource.API_WALLET,
                url
            )
            for i in response['data']
        )


class ApiWalletsJSONPart(BaseTriggerExchangePart):
    @property
    def trigger_actions(self):
        return {'call'}

    @property
    def source(self) -> CoinSource:
        return CoinSource.API_UNOFFICIAL

    async def get(self) -> Set[Symbol]:
        url = 'https://www.bithumb.com/resources/csv/market_sise.json'
        response = await self.http.get(url)
        if not response or not isinstance(response, list):
            raise BithumbPartException(url, response)

        return set(
            Symbol(
                i['symbol'],
                CoinSource.API_UNOFFICIAL,
                url
            )
            for i in response
        )


class ApiPairCoinsPart(BaseTriggerExchangePart):
    @property
    def trigger_actions(self):
        return {'call'}

    @property
    def source(self) -> CoinSource:
        return CoinSource.API_PAIR

    async def get(self) -> Set[Symbol]:
        url = 'https://api.bithumb.com/public/ticker/ALL'
        response = await self.http.get(url)
        if not response or response['status'] != '0000':
            raise BithumbPartException(url, response)
        return set(
            Symbol(
                symbol,
                CoinSource.API_PAIR,
                url
            )
            for symbol, data in response['data'].items()
            if isinstance(data, dict)
        )


class AnnouncementsAPIPart(BaseTriggerExchangePart):
    DELAY = 3.0
    REGEX = re.compile(r'\(([A-Za-z0-9]+)\)')

    @property
    def trigger_actions(self):
        return {'call'}

    @property
    def source(self) -> CoinSource:
        return CoinSource.SITE

    async def get(self) -> Set[Symbol]:
        search_words = ('상장 및',)
        ARTICLE_TITLE = 2
        url = 'https://cafe.bithumb.com/boards/43/contents'

        post_form_data = {
            'draw': 1,
            'columns[0][data]': 0,
            'columns[0][name]': None,
            'columns[0][searchable]': True,
            'columns[0][orderable]': False,
            'columns[0][search][value]': None,
            'columns[0][search][regex]': False,
            'columns[1][data]': 1,
            'columns[1][name]': None,
            'columns[1][searchable]': True,
            'columns[1][orderable]': False,
            'columns[1][search][value]': None,
            'columns[1][search][regex]': False,
            'columns[2][data]': 2,
            'columns[2][name]': None,
            'columns[2][searchable]': True,
            'columns[2][orderable]': False,
            'columns[2][search][value]': None,
            'columns[2][search][regex]': False,
            'columns[3][data]': 3,
            'columns[3][name]': None,
            'columns[3][searchable]': True,
            'columns[3][orderable]': False,
            'columns[3][search][value]': None,
            'columns[3][search][regex]': False,
            'columns[4][data]': 4,
            'columns[4][name]': None,
            'columns[4][searchable]': True,
            'columns[4][orderable]': False,
            'columns[4][search][value]': None,
            'columns[4][search][regex]': False,
            'start': 0,
            'length': 15,
            'search[value]': None,
            'search[regex]': False
        }

        response = await self.http.post(url, data=post_form_data)
        if 'data' not in response:
            raise BithumbPartException(url, response)
        data = response['data']

        filtered = (
            i[ARTICLE_TITLE] for i in data
            if any(w in i[ARTICLE_TITLE] for w in search_words)
        )

        symbols = set()
        for i in filtered:
            symbols.update(self.REGEX.findall(i))

        return set(
            Symbol(
                symbol,
                CoinSource.SITE,
                url
            )
            for symbol in symbols
        )
