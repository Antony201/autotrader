import unittest

from common import NTCredential
from credentials import NonUniqueCredentials, check_unique


class TestCredentials(unittest.TestCase):
    def test_non_unique_credentials(self):
        non_uniq = [
            NTCredential(
                'owner1',
                'exchange1',
                'key1',
                'secret1',
            ),
            NTCredential(
                'owner2',
                'exchange1',
                'key1',
                'secret1',
            ),
        ]
        with self.assertRaises(NonUniqueCredentials):
            check_unique(non_uniq)

    def test_unique_credentials(self):
        uniq = [
            NTCredential(
                'owner1',
                'exchange1',
                'key1',
                'secret1',
            ),
            NTCredential(
                'owner2',
                'exchange2',
                'key2',
                'secret2',
            ),
        ]
        self.assertEqual(uniq, check_unique(uniq))


if __name__ == '__main__':
    unittest.main()
