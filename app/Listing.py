import os
import sys
import time
import config
#import threading
import math
import logging
import logging.handlers
from datetime import datetime, timedelta

from Database import Database
from Account import Account
from Orders import Orders
from Logger import CustomFormatter

formater_str = '%(asctime)s,%(msecs)d %(levelname)s %(message)s'
formatter = logging.Formatter(formater_str)
datefmt="%Y-%b-%d %H:%M:%S"

LOGGER_ENUM = {'debug': 'debug.log', 'trading': 'trades.log', 'errors': 'general.log'}
#LOGGER_FILE = LOGGER_ENUM['pre']
LOGGER_FILE = "binance-trader.log"
FORMAT = '%(asctime)-15s - %(levelname)s:  %(message)s'

logger = logging.basicConfig(filename = LOGGER_FILE, filemode = 'a',
                             format = formater_str, datefmt = datefmt,
                             level = logging.INFO)

class Listing():

    def __init__(self, option):
        print("options: {0}".format(option))

        # get argument parse options
        self.option = option

        # wait some before check new coins
        self.wait_time = self.option.wait_time

        # time delta to search and show new coins
        self.time_delta = self.option.time_delta

        # setup Logger
        self.logger = self.setup_logger('COIN', debug=self.option.debug)

    # Function setup as many loggers as you want
    def setup_logger(self, name=None, debug=True):

        #handler = logging.FileHandler(log_file)
        #handler.setFormatter(formatter)
        #logger.addHandler(handler)
        logger = logging.getLogger(name)
        stout_handler = logging.StreamHandler(sys.stdout)

        if debug:
            logger.setLevel(logging.DEBUG)
            stout_handler.setLevel(logging.DEBUG)

        #handler = logging.handlers.SysLogHandler(address='/dev/log')
        #logger.addHandler(handler)
        stout_handler.setFormatter(CustomFormatter())
        #stout_handler.setFormatter(formatter)
        logger.addHandler(stout_handler)
        return logger

    def action(self):

        # database
        #CREATE TABLE 'all'
        #('symbol' VARCHAR(25),
        #'status' VARCHAR(25),
        #'add' INTEGER)
        #CREATE TABLE 'new'
        #('symbol' VARCHAR(25),
        #'status' VARCHAR(25),
        #'add' INTEGER)

        # dict_keys(['timezone', 'serverTime', 'rateLimits', 'exchangeFilters', 'symbols'])
        # symbol keys:
        #{'symbol': 'SUPERUSDT', 'status': 'TRADING', 'baseAsset': 'SUPER', 'baseAssetPrecision': 8,
        # 'quoteAsset': 'USDT', 'quotePrecision': 8, 'quoteAssetPrecision': 8, 'baseCommissionPrecision': 8,
        # 'quoteCommissionPrecision': 8,
        # 'orderTypes': ['LIMIT', 'LIMIT_MAKER', 'MARKET', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'],
        # 'icebergAllowed': True, 'ocoAllowed': True, 'quoteOrderQtyMarketAllowed': True, 'isSpotTradingAllowed': True,
        # 'isMarginTradingAllowed': False, 'filters': [
        #    {'filterType': 'PRICE_FILTER', 'minPrice': '0.00100000', 'maxPrice': '10000.00000000',
        #     'tickSize': '0.00100000'},
        #    {'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2', 'avgPriceMins': 5},
        #    {'filterType': 'LOT_SIZE', 'minQty': '0.00100000', 'maxQty': '90000.00000000', 'stepSize': '0.00100000'},
        #    {'filterType': 'MIN_NOTIONAL', 'minNotional': '10.00000000', 'applyToMarket': True, 'avgPriceMins': 5},
        #    {'filterType': 'ICEBERG_PARTS', 'limit': 10},
        #    {'filterType': 'MARKET_LOT_SIZE', 'minQty': '0.00000000', 'maxQty': '190515.25378179',
        #     'stepSize': '0.00000000'}, {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': 200},
        #    {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': 5}], 'permissions': ['SPOT']}

        # get all coins
        coins = Orders.get_products()['symbols']

        # current date and time
        stamp = int(datetime.timestamp(datetime.now()))

        # debug
        # timestamp: now - 180 days
        #stamp = int(datetime.timestamp(datetime.now() - timedelta(days=180)))
        #print(self.time_format(stamp))
        # clear database
        #Database.clear_table('all')

        # debug date and time
        #print(stamp)
        #print(self.time_format(stamp))

        # check if coin exists in database
        print('ADD COINS:')
        add = 0
        for coin in coins:
            # if not exist, add coin in database
            if Database.read_symbol('all', coin['symbol']) == None:
                add = add + 1
                Database.write_symbol('all', [coin['symbol'], coin['status'], stamp])
                self.logger.info('symbol:%s status:%s' % (coin['symbol'], coin['status']))

        if add == 0:
            print('None')

        # get coins from database
        dbase = Database.read_table('all')

        # show coins newer than time delta
        print('NEW COINS:')
        new = 0
        delta = int(datetime.timestamp(datetime.fromtimestamp(stamp) - timedelta(days=self.time_delta)))
        for i in dbase:
            if delta < i[2] and delta > 0:
                new = new + 1
                self.logger.info('symbol:%s status:%s date:%s' % (i[0], i[1], self.time_format(i[2])))

        if new == 0:
            print('None')
        print('\n')

    # time format
    def time_format(self, stamp):
        return datetime.fromtimestamp(stamp).strftime('%Y-%m-%d %H:%M:%S')

    # fix float number length
    def float_format(self, amount, step_size):

        step_str = str(step_size)
        step_len = str(len(step_str) - step_str.index('.') - 1)
        qty_format = float(step_size * math.floor(float(amount) / step_size))
        return float('{:.{width}f}'.format(qty_format, width=step_len,))

    # get coin settings info
    def get_coin_sets(self, symbol):

        info = Orders.get_info(symbol)

        if not info:
            self.logger.error('Invalid symbol, please try again...')
            exit(1)
        info['filters'] = {item['filterType']: item for item in info['filters']}
        return info

    # run main
    def run(self):

        # print account settings
        print('\n')
        print('ACCOUNT SETTINGS')
        print('Account type: %s' % Account.account_type())
        print('We can trade: %s' % Account.can_trade())
        print('Connection status: %s ms' % Account.server_status())
        print('\n')

        """
        # DEBUG LINES

        startTime = time.time()
        actionTrader = threading.Thread(target = self.action, args = (coin_symbol))
        actions.append(actionTrader)
        actionTrader.start()
        endTime = time.time()

        if endTime - startTime < self.wait_time:
            time.sleep(self.wait_time - (endTime - startTime))

            # 0 = Unlimited loop
            if self.option.loop > 0:
                cycle = cycle + 1
        """

        cycle = 0
#        actions = []

        while (cycle <= self.option.loop):

           startTime = time.time()

           # wait some before check new coins
           time.sleep(self.wait_time)

#           lister = threading.Thread(target=self.action, args=())
#           actions.append(lister)
#           lister.start()

           self.action()
           endTime = time.time()

           if endTime - startTime < self.wait_time:

               time.sleep(self.wait_time - (endTime - startTime))

               # 0 = Unlimited loop
               if self.option.loop > 0:
                   cycle = cycle + 1
