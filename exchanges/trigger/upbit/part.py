import time
from typing import Set

from common import Symbol, CoinSource
from exchanges.trigger.base.part import BaseTriggerExchangePart, BasePartException


class UpbitPartException(BasePartException):
    pass


class ApiPairsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_PAIR

    async def get(self) -> Set[Symbol]:
        url = f'https://s3.ap-northeast-2.amazonaws.com/crix-production/crix_master?nonce={self.nonce()}'
        response = await self.http.get(url)
        if not isinstance(response, list):
            raise UpbitPartException(url, response)

        return set(
            Symbol(
                i['baseCurrencyCode'].upper(),
                CoinSource.API_PAIR,
                url
            )
            for i in response
            if i['quoteCurrencyCode'].upper() == 'KRW'
        )

    @staticmethod
    def nonce():
        return int(time.time())

    @property
    def price_change_limit(self):
        return 25


# class AnnouncementsPart(BaseTriggerExchangePart):
#     COIN_NAME_FROM_TITLE_REGEX = re.compile(r'([A-Z0-9]+)')
#
#     @property
#     def source(self) -> CoinSource:
#         return CoinSource.SITE
#
#     async def get(self) -> Set[Symbol]:
#         url = 'https://api-manager.upbit.com/api/v1/notices'
#         search_words = (
#             '원화 마켓 신규 상장',  # krw market new listing
#             '이벤트',  # event
#         )
#
#         response = await self.http.get(url)
#         if not response or not response['data'] or not response['success']:
#             raise UpbitPartException(url, response)
#
#         titles = [
#             n['title']
#             for n in response['data']['list']
#             if any(
#                 w in n['title']
#                 for w in search_words
#             )
#         ]
#
#         coin_names = [
#             self.COIN_NAME_FROM_TITLE_REGEX.findall(t)
#             for t in titles
#         ]
#
#         return set(
#             Symbol(
#                 symbol,
#                 CoinSource.SITE,
#                 url
#             )
#             for symbol in set(itertools.chain(*coin_names))
#             if symbol != 'TOP' and not symbol.isdigit()
#         )
#
#     @property
#     def price_change_limit(self):
#         return 25


class ApiPairsBTCOnlyPart(BaseTriggerExchangePart):
    DELAY = 10

    @property
    def source(self) -> CoinSource:
        return CoinSource.API_PAIR

    @property
    def trigger_actions(self):
        return {'call'}

    async def get(self) -> Set[Symbol]:
        url = f'https://s3.ap-northeast-2.amazonaws.com/crix-production/crix_master?nonce={self.nonce()}'
        response = await self.http.get(url)
        if not isinstance(response, list):
            raise UpbitPartException(url, response)

        return set(
            Symbol(
                i['baseCurrencyCode'].upper(),
                CoinSource.API_PAIR,
                url
            )
            for i in response
            if i['quoteCurrencyCode'].upper() == 'BTC'
        )

    @staticmethod
    def nonce():
        return int(time.time())
