import asyncio
import re
from typing import Set, AsyncIterable

import peony
import ujson

from common import CoinSource, Symbol
from exchanges.trigger.base.part import BasePartException, BaseTriggerExchangePart, BaseTriggerExchangeGeneratorPart
from network import OutputFormat


class CoinbaseProPartException(BasePartException):
    pass


class ApiWalletsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_WALLET

    async def get(self) -> Set[Symbol]:
        await asyncio.sleep(1.0)
        url = 'https://api.pro.coinbase.com/currencies/'
        response = await self.http.get(url)
        if not response or not isinstance(response, list):
            raise CoinbaseProPartException(url, response)

        return set(
            Symbol(
                i['id'].upper(),
                CoinSource.API_WALLET,
                url
            )
            for i in response
        )


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
            raise CoinbaseProPartException(url, response)
        posts = response['payload']['references']['Post']

        titles = (
            p['title']
            for _, p in posts.items()
            if 'is launching on coinbase pro' in p['title'].lower()
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


class TwitterPart(BaseTriggerExchangeGeneratorPart):
    REGEX = re.compile(r'([A-Z]+\b)')

    @property
    def source(self) -> CoinSource:
        return CoinSource.TWITTER

    async def stream(self) -> AsyncIterable[Set[Symbol]]:
        user_ids = [
            '720487892670410753',  # CoinbasePro
            # '902585667947036672',  # ape36484
        ]

        req = self.client.stream.statuses.filter.post(follow=','.join(user_ids))
        async with req as stream:
            async for tweet in stream:
                try:
                    await self.log(tweet)
                except Exception as e:
                    await self.log('unable to log tweet: %s', e)

                if not peony.events.tweet(tweet):
                    continue

                if str(tweet.user.id) not in user_ids:
                    continue

                if self._has_usdc_in_text(tweet):
                    continue

                symbols = self._get_symbols(tweet)
                if not symbols:
                    continue

                await self.log('new coins: %s', symbols)

                yield set(
                    Symbol(
                        symbol,
                        CoinSource.TWITTER,
                        f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}'
                    )
                    for symbol in symbols
                )

    @staticmethod
    def _has_usdc_in_text(tweet):
        try:
            text = tweet.text
        except KeyError:
            return False
        else:
            return 'USDC' in text

    def _get_symbols(self, tweet):
        try:
            text = tweet.text
        except KeyError:
            return []
        else:
            return {s for s in self.REGEX.findall(text)}
