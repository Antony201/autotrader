import asyncio
import logging
from typing import Set, Dict, List

import aiohttp
import yaml
from aiohttp import ClientSession


class Account:
    enabled: bool
    name: str
    phone_numbers: Set[str]

    def __init__(self, name: str, data: Dict):
        self._init_logger()

        self.name = name
        if not isinstance(self.name, str):
            raise ValueError('Account parameter `name` must be str, got %s', type(self.name))

        self.enabled = data.get('enabled')
        if not isinstance(self.enabled, bool):
            raise ValueError('Account parameter `enabled` must be bool, got %s', type(self.enabled))

        if not self.enabled:
            return

        phone_numbers = data.get('numbers')
        if not isinstance(phone_numbers, list):
            raise ValueError('Account parameter `phone_numbers` must be list, got %s', type(phone_numbers))

        self.phone_numbers = set()
        self._parse_phone_numbers(phone_numbers)

    def _init_logger(self):
        self._logger = logging.getLogger(__name__)

    def _parse_phone_numbers(self, phone_numbers: List[Dict]):
        for phone_number in phone_numbers:
            enabled = phone_number.get('enabled')
            if not isinstance(enabled, bool):
                raise ValueError('Phone number parameter `enabled` must be bool, got %s', type(enabled))

            number = phone_number['number']
            parsed_number = self._parse_phone_number(number)

            if not enabled:
                self._logger.info('Phone number %r of account %r is disabled, ignoring...', parsed_number, self.name)

            self.phone_numbers.add(parsed_number)

    @staticmethod
    def _parse_phone_number(phone_number: int) -> str:
        str_num = str(phone_number)
        if len(str_num) != 11:
            raise ValueError('Phone number must be in 79991234567 format')

        if not str_num.isdigit():
            raise ValueError('Phone number must contain only digits')

        return f'+{str_num}'

    def __repr__(self):
        return f'Account {self.name} ({",".join(self.phone_numbers)})'


class Caller:
    _logger: logging.Logger = None

    _accounts: Set[Account]

    def __init__(self, from_number: str, account_sid: str, auth_key: str, loop=None, filename='./phone_numbers.yaml'):
        self._init_logger()

        self._from_number = from_number
        self._account_sid = account_sid
        self._auth_key = auth_key

        self._loop = loop or asyncio.get_event_loop()
        self._session = self._init_session()

        self._read_file(filename)

        self._accounts = set()
        self._parse_data()

    def __del__(self):
        self._loop.run_until_complete(self._session.close())

    def _init_session(self) -> ClientSession:
        return ClientSession(
            loop=self._loop,
            auth=aiohttp.BasicAuth(self._account_sid, self._auth_key),
        )

    def _init_logger(self):
        self._logger = logging.getLogger(__name__)

    def _read_file(self, filename):
        with open(filename) as f:
            self._data = yaml.load(f.read(), Loader=yaml.FullLoader)

    def _parse_data(self):
        for account_name, data in self._data.items():
            parsed_account = Account(account_name, data)
            if parsed_account.enabled:
                self._accounts.add(parsed_account)
                self._logger.info('Added account %r', parsed_account)
            else:
                self._logger.info('Account %r is disabled, ignoring...', account_name)

    async def _request(self, url: str, method: str, params: Dict):
        params = params or {}
        params.update(
            {
                'From': self._from_number,
                'Url': 'http://demo.twilio.com/docs/voice.xml'
            }
        )

        http_method = getattr(self._session, method)
        async with http_method(url=url, data=params) as response:
            return await response.json()

    def _make_url(self, path: str):
        return f'https://api.twilio.com/2010-04-01/Accounts/{self._account_sid}/{path}.json'

    async def call_all(self):
        tasks = [
            self.call_account(account)
            for account in self._accounts
        ]
        return await asyncio.gather(*tasks)

    async def call_account(self, account: Account):
        tasks = [
            self.make_call(phone_number)
            for phone_number in account.phone_numbers
        ]
        return await asyncio.gather(*tasks)

    async def make_call(self, to_number: str):
        self._logger.info('Call %s...', to_number)
        result = await self._request(
            self._make_url('Calls'),
            'post',
            {'To': to_number}
        )
        self._logger.info('Call %s result: %s', to_number, result)
        return result
