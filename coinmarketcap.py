import asyncio
import time
from logging import getLogger

from network import AsyncHttp
from utils import singleton


@singleton
class CoinMarketCap:
    _API_URL = 'https://s2.coinmarketcap.com/generated/search/quick_search.json'
    _COIN_URL = 'https://coinmarketcap.com/currencies/%s/'
    _DELTA = 86400

    _data, _updated_at = None, None

    def __init__(self, loop=None):
        self._logger = getLogger(__name__)
        self._loop = loop or asyncio.get_event_loop()
        self.http = AsyncHttp(loop=self._loop)

    def __del__(self):
        self._loop.run_until_complete(self.http._session.close())

    @staticmethod
    def _nonce():
        return int(time.time())

    def _make_coin_url(self, slug):
        return self._COIN_URL % slug

    def _log(self, symbol, msg):
        if symbol:
            return self._logger.info(f'[cmc][{symbol}] {msg}')
        return self._logger.info(f'[cmc] {msg}')

    async def _fetch_data(self):
        try:
            self._data = await self.http.get(self._API_URL)
            self._updated_at = self._nonce()
        except Exception as e:
            self._log(None, e)
            self._data = None
            self._updated_at = None

    async def _update(self):
        if not self._data or (self._nonce() - self._updated_at) > self._DELTA:
            self._is_updating = True
            self._log(None, 'updating cmc data')
            await self._fetch_data()
            self._is_updating = False

    async def warmup(self):
        await self._fetch_data()
        self._log(None, 'warmed up')

    async def get_name_and_url(self, symbol):
        # todo schedule update
        await self._update()

        coin_info = next((i for i in self._data if symbol in i['tokens']), None)

        if not coin_info:
            self._log(symbol, 'coin info is not found')
            return

        self._log(symbol, f'coin info found {coin_info!r}')
        return coin_info['name'], self._make_coin_url(coin_info['slug'])
