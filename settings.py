import os

import dotenv

dotenv.load_dotenv()

DEBUG = bool(os.environ.get('DEBUG', False))


# twitter

TWITTER_ENABLED = bool(os.environ.get('TWITTER_ENABLED', False))
if TWITTER_ENABLED:
    TWITTER_CONSUMER_KEY = os.environ['TWITTER_CONSUMER_KEY']
    TWITTER_CONSUMER_SECRET = os.environ['TWITTER_CONSUMER_SECRET']
    TWITTER_ACCESS_TOKEN = os.environ['TWITTER_ACCESS_TOKEN']
    TWITTER_ACCESS_TOKEN_SECRET = os.environ['TWITTER_ACCESS_TOKEN_SECRET']

# telegram bot
BOT_TOKEN = os.environ['BOT_TOKEN']
AUTHORIZED_USERS_TELEGRAM_IDS = tuple(int(u) for u in os.environ['AUTHORIZED_USERS_TELEGRAM_IDS'].split(','))
LOG_CHANNEL_ID = os.environ['LOG_CHANNEL_ID']
BALANCE_SHOW_LIMIT_BTC = os.environ.get('BALANCE_SHOW_LIMIT_BTC', '0.005')

# trade
PRICE_CHANGE_LIMIT_IN_PERCENT = int(os.environ.get('PRICE_CHANGE_LIMIT_IN_PERCENT', 25))

# twilio
TWILIO_FROM_NUMBER = os.environ['TWILIO_FROM_NUMBER']
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_KEY = os.environ['TWILIO_AUTH_KEY']

# trade exchange
LIMIT_ORDER_MARKUP = int(os.environ.get('LIMIT_ORDER_MARKUP', 15))

DISABLE_BUY = bool(os.environ.get('DISABLE_BUY', False))

ORDER_CANCEL_DELAY = int(os.environ.get('ORDER_CANCEL_DELAY', 15))

# MEM
# MEM_CHECK_INTERVAL = int(os.environ['MEM_CHECK_INTERVAL'])
# MEM_WATCH_LIMIT = int(os.environ['MEM_WATCH_LIMIT'])
# MEM_EXIT_LIMIT = int(os.environ['MEM_EXIT_LIMIT'])
# MEM_OBJECTS_COUNT_LIMIT = int(os.environ['MEM_OBJECTS_COUNT_LIMIT'])

# parse jayden channel

LISTEN_CHANNEL_ID = int(os.environ['LISTEN_CHANNEL_ID'])

# symbols black&white lists
SYMBOLS_BLACK_LIST = set(i.strip() for i in os.environ.get('SYMBOLS_BLACK_LIST', '').split(','))
SYMBOLS_WHITE_LIST = set(i.strip() for i in os.environ.get('SYMBOLS_WHITE_LIST', '').split(','))

UPBIT_KRW_PRICE_CHANGE_LIMIT = int(os.environ['UPBIT_KRW_PRICE_CHANGE_LIMIT'])
UPBIT_BTC_PRICE_CHANGE_LIMIT = int(os.environ['UPBIT_BTC_PRICE_CHANGE_LIMIT'])
