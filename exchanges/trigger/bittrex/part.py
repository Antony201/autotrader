from typing import Set, AsyncIterable

import peony

from common import CoinSource, Symbol
from exchanges.trigger.base.part import BasePartException, BaseTriggerExchangePart, BaseTriggerExchangeGeneratorPart


class BittrexPartException(BasePartException):
    pass


class ApiWalletsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_WALLET

    async def get(self) -> Set[Symbol]:
        url = 'https://bittrex.com/api/v1.1/public/getcurrencies'
        response = await self.http.get(url)
        if not response['success']:
            raise BittrexPartException(url, response)

        return set(
            Symbol(
                i['Currency'].upper(),
                CoinSource.API_WALLET,
                url
            )
            for i in response['result']
        )


class ApiPairsPart(BaseTriggerExchangePart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.API_PAIR

    async def get(self) -> Set[Symbol]:
        url = 'https://bittrex.com/api/v1.1/public/getmarkets'
        response = await self.http.get(url)
        if not response['success']:
            raise BittrexPartException(url, response)

        return set(
            Symbol(
                i['MarketCurrency'].upper(),
                CoinSource.API_PAIR,
                url
            )
            for i in response['result']
        )


class TwitterPart(BaseTriggerExchangeGeneratorPart):
    @property
    def source(self) -> CoinSource:
        return CoinSource.TWITTER

    async def stream(self) -> AsyncIterable[Set[Symbol]]:
        user_ids = [
            '1058405958626340869',  # bittrexus
            # '16324992',  # richiela
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

                if not self._has_text(tweet.text):
                    continue

                symbols = self._get_symbols(tweet)
                if not symbols:
                    continue

                yield set(
                    Symbol(
                        symbol,
                        CoinSource.TWITTER,
                        f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}'
                    )
                    for symbol in symbols
                )

    @staticmethod
    def _has_text(text: str) -> bool:
        return 'market is open' in text.lower()

    @staticmethod
    def _get_symbols(tweet) -> Set[str]:
        try:
            symbols = tweet.entities.symbols
        except KeyError:
            return {}
        else:
            return {symbol.text.upper() for symbol in symbols}
