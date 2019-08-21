import unittest
from decimal import Decimal

from utils import norm


class TestUtils(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(norm(Decimal('5.00')), '5')
        self.assertEqual(norm(Decimal('3')), '3')
        self.assertEqual(norm(Decimal('2.4e-7')), '0.00000024')
        self.assertEqual(norm(Decimal('2.4e-10')), '0')
        self.assertEqual(norm(Decimal('1.2345678987654')), '1.2345679')
        self.assertEqual(norm(Decimal('1.23450000000')), '1.2345')
        self.assertEqual(norm(Decimal('0.000000001')), '0')
        self.assertEqual(norm(Decimal('1.2345678987654') * Decimal('1.2345678987654')), '1.5241579')


if __name__ == '__main__':
    unittest.main()
