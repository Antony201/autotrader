import re
from typing import Set

import ujson

from common import CoinSource, Symbol
from exchanges.trigger.base.part import BasePartException, BaseTriggerExchangePart
from network import OutputFormat


class CoinbasePartException(BasePartException):
    pass


class ApiAnnouncementsPart(BaseTriggerExchangePart):
    DELAY = 0
    REGEX = re.compile(r'\(([A-Za-z0-9]+)\)')

    @property
    def source(self) -> CoinSource:
        return CoinSource.API_UNOFFICIAL

    async def get(self) -> Set[Symbol]:
        url = 'https://medium.com/_/api/collections/c114225aeaf7/stream'
        response_raw = await self.http.get(url, output=OutputFormat.RAW)
        response_correct = response_raw[response_raw.find('{'):]
        response = ujson.loads(response_correct)
        if not response or not response['success']:
            raise CoinbasePartException(url, response)
        posts = response['payload']['references']['Post']

        titles = (
            p['title']
            for _, p in posts.items()
            if 'is now available on coinbase' in p['title'].lower()
        )

        symbols = set()
        for i in titles:
            symbols.update(self.REGEX.findall(i))

        return set(
            Symbol(
                symbol,
                CoinSource.SITE,
                'https://blog.coinbase.com/'
            )
            for symbol in symbols
        )
