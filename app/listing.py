import sys
from time import time, sleep
import math
import logging
import logging.handlers
from datetime import datetime, timedelta

from app.database import Database
from app.binance_handler import BinanceHandler
from app.logger import CustomFormatter

formater_str = '%(asctime)s,%(msecs)d %(levelname)s %(message)s'
formatter = logging.Formatter(formater_str)
datefmt = "%Y-%b-%d %H:%M:%S"

LOGGER_ENUM = {'debug': 'debug.log', 'trading': 'trades.log', 'errors': 'general.log'}
# LOGGER_FILE = LOGGER_ENUM['pre']
LOGGER_FILE = "binance-trader.log"
FORMAT = '%(asctime)-15s - %(levelname)s:  %(message)s'

logger = logging.basicConfig(filename=LOGGER_FILE, filemode='a',
                             format=formater_str, datefmt=datefmt,
                             level=logging.INFO)


class Listing:

    def __init__(self, option):
        print("options: {0}".format(option))
        self.option = option  # get argument parse options
        self.wait_time = self.option.wait_time  # wait some before check new coins
        self.time_delta = self.option.time_delta  # time delta to search and show new coins
        self.logger = self.setup_logger('COIN', debug=self.option.debug)  # setup Logger
        self.markets = ['binance']  # binance, ftx
        self.perms = ['spot', 'margin']  # allowed permissions
        self.pairs = ['usdt', 'btc']  # allowed pairs
        self.binance_usdt = []  # binance btc coins
        self.binance_btc = []  # binance usdt coins
        self.binance_all = []

    def setup_logger(self, name=None, debug=True):
        # handler = logging.FileHandler(log_file)
        # handler.setFormatter(formatter)
        # logger.addHandler(handler)
        logger = logging.getLogger(name)
        stout_handler = logging.StreamHandler(sys.stdout)
        if debug:
            logger.setLevel(logging.DEBUG)
            stout_handler.setLevel(logging.DEBUG)
        # handler = logging.handlers.SysLogHandler(address='/dev/log')
        # logger.addHandler(handler)
        stout_handler.setFormatter(CustomFormatter())
        # stout_handler.setFormatter(formatter)
        logger.addHandler(stout_handler)
        return logger

    def time_format(self, stamp):  # time format
        return datetime.fromtimestamp(stamp).strftime('%Y-%m-%d %H:%M:%S')

    def float_format(self, amount: int, step_size: float):  # fix float number length
        step_str = str(step_size)
        step_len = str(len(step_str) - step_str.index('.') - 1)
        qty_format = float(step_size * math.floor(float(amount) / step_size))
        return float('{:.{width}f}'.format(qty_format, width=step_len, ))

    def float_fix(self, num: float, lng: int = 1):
        num = float(num)
        return float('{:.{width}f}'.format(num, width=lng, ))

    def millify(self, num: float, lng: int = 3):
        names = ['', 'K', 'M', 'B', 'T']
        num = float(num)
        millidx = max(0, min(len(names) - 1, int(math.floor(0 if num == 0 else math.log10(abs(num)) / 3))))
        return '{:.{width}f}{}'.format(num / 10 ** (3 * millidx), names[millidx], width=lng, )

    def get_binance_coins(self):
        coins = BinanceHandler.get_products()['symbols']  # get all coins from market
        for coin in coins:
            asset = coin['quoteAsset'].lower()  # usdt or btc
            if asset in self.pairs:
                spot = 1 if self.perms[0].upper() in coin['permissions'] else 0  # check coin spot trading
                margin = 1 if self.perms[1].upper() in coin['permissions'] else 0  # check coin margin trading
                if coin['status'] == 'TRADING' and spot == 1:
                    if asset == 'usdt': self.binance_usdt.append({'symbol': coin['symbol'],
                                                                  'status': coin['status'],
                                                                  'spot': spot,
                                                                  'margin': margin})
                    if asset == 'btc': self.binance_btc.append({'symbol': coin['symbol'],
                                                                'status': coin['status'],
                                                                'spot': spot,
                                                                'margin': margin})

    def get_binance_coins_info(self):
        print('please stand by...')
        coins = self.binance_usdt
        for coin in range(0, len(coins)):
            temp = coins[coin]
            # if temp['symbol'].lower() == 'btcusdt':
            ticker = BinanceHandler.get_ticker(temp['symbol'])
            temp['priceChange'] = ticker['priceChange']
            temp['priceChangePercent'] = self.float_fix(float(ticker['priceChangePercent']))
            temp['lastPrice'] = self.millify(float(ticker['lastPrice']))
            temp['volume'] = self.millify(float(ticker['volume']))
            temp['quoteVolume'] = self.millify(float(ticker['quoteVolume']))
            coins[coin] = temp
            # print(temp)
        self.binance_all = coins

    def show_best_coins(self):
        for coin in self.binance_all:
            if float(coin['priceChangePercent']) > 5.00 or float(coin['priceChangePercent']) < -5.00:
                # self.logger.info('symbol:%s '
                print('symbol:%s '
                      'price:%s (%s%%) '
                      'volume:%s (%s)' % (coin['symbol'],
                                          coin['lastPrice'], coin['priceChangePercent'],
                                          coin['quoteVolume'], coin['volume']))

    def run(self):  # run main
        print('\n')
        print('ACCOUNT SETTINGS')
        print('Account type: %s' % BinanceHandler.account_type())
        print('Coins trade: %s' % BinanceHandler.can_trade())
        print('Server ping: %s ms' % BinanceHandler.server_status())
        print('\n')
        self.get_binance_coins()
        self.get_binance_coins_info()
        self.show_best_coins()

        # cycle = 0
        # while cycle <= self.option.loop:
        #     start = time()
        #     self.action()
        #     sleep(self.wait_time)  # wait some
        #     stop = time()
        #     print(self.option.loop)
        #     if self.option.loop > 0:  # 0 = Unlimited loop
        #         cycle = cycle + 1
