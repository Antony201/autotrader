import unittest

import settings
from tgbot.handlers.zdefault import extract_symbols_keywords, extract_symbols_endpoint_btc, extract_symbols_endpoint_krw


class TestExtractSymbols(unittest.TestCase):
    def test_extract_symbols_keywords(self):
        data = [
            ('[이벤트] 디센트럴랜드(MANA) 원화마켓 오픈 이벤트  - MANA TOP 트레이딩 이벤트', {'MANA'}),
            ('[이벤트] 펀디엑스(NPXS) 원화마켓 오픈 이벤트 : TOP 트레이딩 이벤트', {'NPXS'}),
            ('[이벤트] 무비블록(MBL) 원화마켓 오픈 이벤트 : TOP 트레이딩 이벤트', {'MBL'}),
            ('[거래] 원화 마켓 신규 상장 (솔브케어 SOLVE)', {'SOLVE'}),
            ('[이벤트] 캐리프로토콜(CRE) SPC 해피포인트 협약 체결 기념 : CRE 거래하고 CRE 받자', {'CRE'}),
            ('[암호화폐] 썬더토큰(TT) 입출금 지원 및 원화마켓 오픈 예정 안내', {'TT'}),
            ('[입금] 코스모스(ATOM) 입금 오픈 (5/3 원화마켓 오픈 예정)', {'ATOM'}),
            ('[이벤트] 메디블록(MEDX) 신촌세브란스병원 업무협약 기념 - MEDX TOP 트레이딩 이벤트', {'MEDX'}),
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): ATOM/KRW', set()),
        ]
        for msg, expected in data:
            self.assertEqual(extract_symbols_keywords(msg), expected)

        settings.SYMBOLS_BLACK_LIST = {'MEDX', 'CRE'}
        data = [
            ('[이벤트] 디센트럴랜드(MANA) 원화마켓 오픈 이벤트  - MANA TOP 트레이딩 이벤트', {'MANA'}),
            ('[이벤트] 펀디엑스(NPXS) 원화마켓 오픈 이벤트 : TOP 트레이딩 이벤트', {'NPXS'}),
            ('[이벤트] 무비블록(MBL) 원화마켓 오픈 이벤트 : TOP 트레이딩 이벤트', {'MBL'}),
            ('[거래] 원화 마켓 신규 상장 (솔브케어 SOLVE)', {'SOLVE'}),
            ('[이벤트] 캐리프로토콜(CRE) SPC 해피포인트 협약 체결 기념 : CRE 거래하고 CRE 받자', set()),
            ('[암호화폐] 썬더토큰(TT) 입출금 지원 및 원화마켓 오픈 예정 안내', {'TT'}),
            ('[입금] 코스모스(ATOM) 입금 오픈 (5/3 원화마켓 오픈 예정)', {'ATOM'}),
            ('[이벤트] 메디블록(MEDX) 신촌세브란스병원 업무협약 기념 - MEDX TOP 트레이딩 이벤트', set()),
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): ATOM/KRW', set()),
        ]
        for msg, expected in data:
            self.assertEqual(extract_symbols_keywords(msg), expected)

    def test_extract_symbols_endpoint(self):
        data = [
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): ATOM/KRW', {'ATOM'}),
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): LAMB/BTC CPT/BTC', set()),
            ('by @CMfree Upbit Endpoint #3 (Jaýden.Crypto) added BTC-COSM BTC-ATOM', set()),
        ]
        for msg, expected in data:
            self.assertEqual(extract_symbols_endpoint_krw(msg), expected)

        settings.SYMBOLS_WHITE_LIST = {'LAMB', 'CPT', 'ATOM', 'COSM'}
        data = [
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): ATOM/KRW', set()),
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): LAMB/BTC CPT/BTC', {'LAMB', 'CPT'}),
            ('by @CMfree Upbit Endpoint #3 (Jaýden.Crypto) added BTC-COSM BTC-ATOM', {'COSM', 'ATOM'}),
        ]
        for msg, expected in data:
            self.assertEqual(extract_symbols_endpoint_btc(msg), expected)

        settings.SYMBOLS_WHITE_LIST = {'LAMB', 'CPT', 'ATOM', 'COSM'}
        data = [
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): ATOM/KRW', {'ATOM'}),
            ('by @CMfree Upbit Endpoint #1 (Jayden_Cryptơ): LAMB/BTC CPT/BTC', set()),
            ('by @CMfree Upbit Endpoint #3 (Jaýden.Crypto) added BTC-COSM BTC-ATOM', set()),
        ]
        for msg, expected in data:
            self.assertEqual(extract_symbols_endpoint_krw(msg), expected)


if __name__ == '__main__':
    unittest.main()
