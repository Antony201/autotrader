import logging
import unittest
from asyncio import AbstractEventLoop
from unittest.mock import patch

import aiohttp
import yaml

from caller import Caller, Account


def mock_read_file(self, filename):
    self._data = yaml.load(
        '''account_one:
  enabled: true
  numbers:
  - enabled: true
    number: +79991234567
  - enabled: true
    number: +79997654321
account_two:
  enabled: false
  numbers:
  - enabled: true
    number: +79991122334
  - enabled: false
    number: +79994433221
        '''
    )


class TestCaller(unittest.TestCase):
    @patch.object(Caller, '_read_file', mock_read_file)
    def setUp(self):
        self.c = Caller('from', 'sid', 'authkey')

    def test_init(self):
        self.assertEqual(self.c._from_number, 'from')
        self.assertEqual(self.c._account_sid, 'sid')
        self.assertEqual(self.c._auth_key, 'authkey')

    def test_read_file(self):
        self.assertIsNotNone(self.c._data)
        self.assertIsInstance(self.c._data, dict)

    def test_loop(self):
        self.assertIsNotNone(self.c._loop)
        self.assertIsInstance(self.c._loop, AbstractEventLoop)

    def test_session(self):
        self.assertIsNotNone(self.c._session)
        self.assertIsInstance(self.c._session, aiohttp.ClientSession)

    def test_logger(self):
        self.assertIsNotNone(self.c._logger)
        self.assertIsInstance(self.c._logger, logging.Logger)

    def test_parse_data(self):
        self.assertIsInstance(self.c._accounts, set)
        self.assertNotIn('account_two', self.c._accounts)
        for a in self.c._accounts:
            self.assertIsInstance(a, Account)

    def test_make_url(self):
        self.assertEqual(
            self.c._make_url('testpath'),
            'https://api.twilio.com/2010-04-01/Accounts/sid/testpath.json'
        )


if __name__ == '__main__':
    unittest.main()
