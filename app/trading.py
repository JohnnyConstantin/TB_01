# Define Python imports
import os
import sys
import time
import config
import threading
import math
import logging
import logging.handlers

# Define Custom imports
from app.database import Database
from app.account import Account
from app.binance_handler import Orders
from app.logger import CustomFormatter

formater_str = '%(asctime)s,%(msecs)d %(levelname)s %(name)s: %(message)s'
formatter = logging.Formatter(formater_str)
datefmt="%Y-%b-%d %H:%M:%S"

LOGGER_ENUM = {'debug': 'debug.log', 'trading': 'trades.log', 'errors': 'general.log'}
#LOGGER_FILE = LOGGER_ENUM['pre']
LOGGER_FILE = "binance-trader.log"
FORMAT = '%(asctime)-15s - %(levelname)s:  %(message)s'

logger = logging.basicConfig(filename = LOGGER_FILE, filemode = 'a',
                             format = formater_str, datefmt = datefmt,
                             level = logging.INFO)

# Aproximated value to get back the commission for sell and buy
TOKEN_COMMISSION = 0.001
BNB_COMMISSION   = 0.0005
#((eth*0.05)/100)


class Trading:

    # Define trade vars
    buy_order_id = 0
    sell_order_id = 0
    coin_amount = 0
    order_id = 0
    order_data = None

    buy_filled = True
    sell_filled = True

    buy_filled_qty = 0
    sell_filled_qty = 0

    # percent (When you drop 10%, sell panic.)
    stop_loss = 0
    price_step = 0

    # order price (for print at bot start)
    notional = 0

    # the quantity of coins to buy or sell in the order
    quantity = 0

    # BTC amount
    amount = 0

    # float(step_size * math.floor(float(free)/step_size))
    lot_step = 0

    # test mode
    balance_usdt = 35

    # Define static vars
    WAIT_TIME_BUY_SELL = 1 # seconds
    WAIT_TIME_CHECK_BUY_SELL = 0.2 # seconds
    WAIT_TIME_CHECK_SELL = 5 # seconds
    WAIT_TIME_STOP_LOSS = 20 # seconds

    MAX_TRADE_SIZE = 7 # int

    # Type of commission, Default BNB_COMMISSION
    commission = BNB_COMMISSION

    def __init__(self, option):
        print("options: {0}".format(option))

        # Get argument parse options
        self.option = option

        # Define parser vars
        self.order_id = self.option.orderid
        self.coin_amount = self.option.coin_amount
        self.wait_time = self.option.wait_time
        self.stop_loss = self.option.stop_loss

        self.price_increase = self.option.price_increase
        self.price_decrease = self.option.price_decrease

        # BTC amount
        self.amount = self.option.amount

        # type of commission
        if self.option.commission == 'TOKEN':
            self.commission = TOKEN_COMMISSION

        # setup Logger
        self.logger = self.setup_logger(self.option.symbol, debug=self.option.debug)

        # if test mode enabled, delete buy and sell orders
        if self.option.test_mode == True:
            Database.delete(1)
            Database.delete(2)

    # Function setup as many loggers as you want
    def setup_logger(self, symbol, debug=True):

        #handler = logging.FileHandler(log_file)
        #handler.setFormatter(formatter)
        #logger.addHandler(handler)
        logger = logging.getLogger(symbol)
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

    # create buy order
    def buy(self, coin_symbol, coin_amount, buy_price, pro_price):

        # check if open order exists, exit
        self.check_order(self.buy_order_id)

        try:
            # create buy order
            if self.option.test_mode == True:
                self.buy_order_id = 1
            else:
                self.buy_order_id = Orders.buy_limit(coin_symbol, coin_amount, buy_price)

            # write buy order to database
            Database.write([self.buy_order_id, coin_symbol, 0, buy_price, 'buy', coin_amount, self.option.profit])

            self.logger.info('Buy order created id: %d, q: %s, p: %s, Take profit aprox :%s' % (self.buy_order_id, coin_amount, float(buy_price), pro_price))

        except Exception as e:
            #print('bl: %s' % (e))
            self.logger.debug('Buy error: %s' % (e))
            time.sleep(self.WAIT_TIME_BUY_SELL)

    # cancel order
    def order_cancel(self, coin_symbol, order_id, order_action):

        # check test mode
        if self.option.test_mode == True:

            if order_action == 'BUY':
                self.buy_order_id = 0
                return

            if order_action == 'SELL':
                self.sell_order_id = 0
                return

        # get order
        order = Orders.get_order(coin_symbol, order_id)

        # if order does not exist, all ok
        if not order:

            # release buy order id
            if order_action == 'BUY':
                self.buy_order_id = 0

            # release sell order id
            if order_action == 'SELL':
                self.sell_order_id = 0
            return

        # if order exists with status 'NEW' or 'CANCELLED', cancel order
        if order['status'] == 'NEW' or order['status'] != 'CANCELLED':
            Orders.cancel_order(coin_symbol, order_id)

            # release buy order id
            if order_action == 'BUY':
                self.buy_order_id = 0

            # release sell order id
            if order_action == 'SELL':
                self.sell_order_id = 0

    # check buy or sell order status
    def order_check(self, coin_symbol, coin_amount, order, sell_price, last_price, order_action):

        # wait some before check order
        time.sleep(self.WAIT_TIME_CHECK_SELL)

        # check test mode
        if self.option.test_mode == True:

            # get current price
            last_price = Orders.get_ticker(coin_symbol)
            last_price = self.float_format(last_price, self.price_step)

            # check if order exists and last price >= price in order, all ok
            if last_price >= order[3]:

                # close buy order
                if order_action == 'BUY':

                    # write sell order to log
                    self.logger.info(order_action + ' order created id: %d, amount: %s, price: %s, last price :%s, profit: %s' % (
                        self.buy_order_id, coin_amount, sell_price, last_price, self.option.profit))
                    self.buy_order_id = 0
                    self.coin_amount = self.coin_amount + order[5]
                    print('SUCCESSFULLY BOUGHT COINS!')
                    print('COIN AMOUNT: ' + str(self.coin_amount))
                    print('COIN BUY PRICE: ' + str(order[3]) + ' $')
                    print('BALANCE: TODO')
                    return True

                # close sell order
                if order_action == 'SELL':

                    # write sell order to log
                    self.logger.info(order_action + ' order created id: %d, amount: %s, price: %s, last price :%s, profit: %s' % (
                        self.sell_order_id, coin_amount, sell_price, last_price, self.option.profit))
                    self.sell_order_id = 0
                    self.coin_amount = self.coin_amount - order[5]
                    print('SUCCESSFULLY SOLD COINS!')
                    print('COIN AMOUNT: ' + str(self.coin_amount))
                    print('COIN SELL PRICE: ' + str(order[3]) + ' $')
                    print('BALANCE: TODO')
                    return True

            self.order_cancel(coin_symbol, order['orderId'], order_action)
            return False

        # if order status is 'FILLED', all ok
        if order['status'] == 'FILLED' and order['side'] == order_action:

            # write sell order to log
            self.logger.info(order_action + ' order created id: %d, amount: %s, price: %s, last price :%s, profit: %s' % (
            order['orderId'], coin_amount, sell_price, last_price, self.option.profit))

            # write sell order to database
            Database.write([order['orderId'], coin_symbol, 0, sell_price, order_action, coin_amount, last_price])
            return True

        else:
            # wait some before check order status
            time.sleep(self.WAIT_TIME_CHECK_BUY_SELL)

            # if order status is 'FILLED', all ok
            if order['status'] == 'FILLED' and order['side'] == order_action:

                # write sell order to log
                self.logger.info(order_action + ' order created id: %d, amount: %s, price: %s, last price :%s, profit: %s' % (
                    order['orderId'], coin_amount, sell_price, last_price, self.option.profit))

                # write sell order to database
                Database.write([order['orderId'], coin_symbol, 0, sell_price, order_action, coin_amount, last_price])
                return True

            # if order status is 'PARTIALLY_FILLED', cancel order
            elif order['status'] == 'PARTIALLY_FILLED' and order['side'] == order_action:
                self.logger.info(order_action + ' order partially filled ... try cancel ...')
                self.order_cancel(coin_symbol, order['orderId'], order_action)

            # cancel order
            else:
                self.logger.warning(order_action + ' order fail, not filled ... try cancel ...')
                self.order_cancel(coin_symbol, order['orderId'], order_action)
        return False

    def order_sell(self, coin_symbol, coin_amount, sell_price, last_price):

        # check test mode
        if self.option.test_mode == True:

            # create sell order
            self.sell_order_id = 2
            sell_order = [self.sell_order_id, coin_symbol, 0, sell_price, 'SELL', coin_amount, last_price]

        else:

            # create sell order
            sell_order = Orders.sell_limit(coin_symbol, coin_amount, sell_price)
            self.sell_order_id = sell_order['orderId']

        # check order status, if true, all ok
        if self.order_check(self, coin_symbol, coin_amount, sell_order, sell_price, last_price, 'SELL') == False:
            return

# TODO: STOP LOSS

    def stop(self, coin_symbol, coin_amount, orderId, last_price):
        # If the target is not reached, stop-loss.
        stop_order = Orders.get_order(coin_symbol, orderId)

        stopprice =  self.calc(float(stop_order['price']))

        lossprice = stopprice - (stopprice * self.stop_loss / 100)

        status = stop_order['status']

        # Order status
        if status == 'NEW' or status == 'PARTIALLY_FILLED':

            if self.cancel(coin_symbol, orderId):

                # Stop loss
                if last_price >= lossprice:

                    sello = Orders.sell_market(coin_symbol, coin_amount)

                    #print('Stop-loss, sell market, %s' % (last_price))
                    self.logger.info('Stop-loss, sell market, %s' % (last_price))

                    sell_id = sello['orderId']

                    if sello == True:
                        return True
                    else:
                        # Wait a while after the sale to the loss.
                        time.sleep(self.WAIT_TIME_STOP_LOSS)
                        statusloss = sello['status']
                        if statusloss != 'NEW':
                            print('Stop-loss, sold')
                            self.logger.info('Stop-loss, sold')
                            return True
                        else:
                            self.cancel(coin_symbol, sell_id)
                            return False
                else:
                    sello = Orders.sell_limit(coin_symbol, coin_amount, lossprice)
                    print('Stop-loss, sell limit, %s' % (lossprice))
                    time.sleep(self.WAIT_TIME_STOP_LOSS)
                    statusloss = sello['status']
                    if statusloss != 'NEW':
                        print('Stop-loss, sold')
                        return True
                    else:
                        self.cancel(coin_symbol, sell_id)
                        return False
            else:
                print('Cancel did not work... Might have been sold before stop loss...')
                return True

        elif status == 'FILLED':
            self.order_id = 0
            self.order_data = None
            print('Order filled')
            return True
        else:
            return False

    def stop1(self, coin_symbol, coin_amount, orderId, last_price, sell_price):

        # if all sales trials fail, the grievance is stop-loss
        if self.stop_loss > 0:

            # If sell order failed after 5 seconds, 5 seconds more wait time before selling at loss
            time.sleep(self.WAIT_TIME_CHECK_SELL)

            if self.stop(coin_symbol, coin_amount, orderId, last_price):

                if Orders.get_order(coin_symbol, orderId)['status'] != 'FILLED':
                    #print('We apologize... Sold at loss...')
                    self.logger.info('We apologize... Sold at loss...')

            else:
                #print('We apologize... Cant sell even at loss... Please sell manually... Stopping program...')
                self.logger.info('We apologize... Cant sell even at loss... Please sell manually... Stopping program...')
                self.cancel(coin_symbol, orderId)
                exit(1)

            while (sell_status != 'FILLED'):
                time.sleep(self.WAIT_TIME_CHECK_SELL)
                sell_status = Orders.get_order(coin_symbol, orderId)['status']
                lastPrice = Orders.get_ticker(coin_symbol)
                #print('Status: %s Current price: %.8f Sell price: %.8f' % (sell_status, lastPrice, sell_price))
                #print('Sold! Continue trading...')

                self.logger.info('Status: %s Current price: %.8f Sell price: %.8f' % (sell_status, lastPrice, sell_price))
                self.logger.info('Sold! Continue trading...')

            self.order_data = None

    def check(self, coin_symbol, orderId, coin_amount):
        # If profit is available and there is no purchase from the specified price, take it with the market.

        # check if open order exists - return
        self.check_order()

        trading_size = 0
        time.sleep(self.WAIT_TIME_BUY_SELL)

        while trading_size < self.MAX_TRADE_SIZE:

            # Order info
            order = Orders.get_order(coin_symbol, orderId)

            side  = order['side']
            price = float(order['price'])

            # TODO: Sell partial qty
            orig_qty = float(order['origQty'])
            self.buy_filled_qty = float(order['executedQty'])

            status = order['status']

            self.logger.info('Wait buy order: %s id:%d, price: %.8f, orig_qty: %.8f' % (coin_symbol, order['orderId'], price, orig_qty))

            if status == 'NEW':

                if self.cancel(coin_symbol, orderId):

                    buyo = Orders.buy_market(coin_symbol, coin_amount)

                    #print('Buy market order')
                    self.logger.info('Buy market order')

                    self.order_id = buyo['orderId']
                    self.order_data = buyo

                    if buyo == True:
                        break
                    else:
                        trading_size += 1
                        continue
                else:
                    break

            elif status == 'FILLED':
                self.order_id = order['orderId']
                self.order_data = order
                #print('Filled')
                self.logger.info('Filled')
                break
            elif status == 'PARTIALLY_FILLED':
                #print('Partial filled')
                self.logger.info('Partial filled')
                break
            else:
                trading_size += 1
                continue

    def calc(self, last_bid):
        try:
            sell_price = last_bid + (last_bid * self.option.profit / 100)
            commission = (last_bid * self.commission)
            # estimated sell price considering commission
            return sell_price + commission
        except Exception as e:
            print('Calc Error: %s' % (e))
            return

    # check if there is an open order, exit
    def check_order(self, order_id):
        if order_id > 0:
            exit(1)

    def action(self, coin_symbol):
        #import ipdb; ipdb.set_trace()

        # get current price
        last_price = Orders.get_ticker(coin_symbol)
        last_price = self.float_format(last_price, self.price_step)

        # get last buy and last sell prices from order book
        last_bid, last_ask = Orders.get_order_book(coin_symbol)
        last_bid = self.float_format(last_bid, self.price_step)
        last_ask = self.float_format(last_ask, self.price_step)

        # prepare target buy price with little increase
        buy_price = last_bid + self.price_increase
        buy_price = self.float_format(buy_price, self.price_step)

        # prepare target sell price with little decrease
        sell_price = last_ask - self.price_decrease
        sell_price = self.float_format(sell_price, self.price_step)

        # profitable selling price
        pro_price = self.calc(last_bid)
        pro_price = self.float_format(pro_price, self.price_step)

        # check working mode
        if self.option.mode == 'range':
            buy_price = float(self.option.buy_price)
            sell_price = float(self.option.sell_price)
            pro_price = sell_price

        # screen log
        if self.option.prints and self.order_id == 0:
            spreadPerc = (last_ask / last_bid - 1) * 100.0
            self.logger.debug('price:%.8f buyprice:%.8f sellprice:%.8f bid:%.8f ask:%.8f spread:%.2f Originalsellprice:%.8f' % (last_price, buy_price, pro_price, last_bid, last_ask, spreadPerc, pro_price-(last_bid * self.commission)))

        # analyze = threading.Thread(target=analyze, args=(symbol,))
        # analyze.start()

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
        coins_all = Orders.get_products()['symbols']
        #print(str(coins_all))
        # status: TRADING, BREAK
        for coin in coins_all:
            print(str(coin['symbol']) + ' - ' + str(coin['status']))

        # check test mode
        if self.option.test_mode == True:
            # get buy order from database
            buy_order = Database.read(1)

            # check if buy order exists - try to sell it later
            if buy_order != None:
                self.buy_order_id = 1

            # get sell order from database
            sell_order = Database.read(2)

            # check if sell order exists
            if sell_order != None:
                self.sell_order_id = 2

        else:
            # check if buy order not exist - successfully bought
            buy_order = Orders.get_order(coin_symbol, self.buy_order_id)

            if self.buy_order_check(buy_order) == False:
                self.buy_order_id = 0

            # check if sell order not exist - successfully sold
            sell_order = Orders.get_order(coin_symbol, self.sell_order_id)

            if self.sell_order_check(sell_order) == False:
                self.sell_order_id = 0

# TODO: COMPARE STOP VS STOP1 OR WHAT TO DO IF CANT SELL

#        if self.sell_order_id != 0:
#            # if all sales trials fail, the grievance is stop-loss
#            self.stop1(symbol, coin_amount, self.sell_order_id, last_price, sell_order[3])

        # check if coins amount > 0 or buy order exists - try to sell it
        if self.coin_amount > 0 or self.buy_order_id > 0:

            # profit mode
            if self.order_data is not None:
                order = self.order_data

# TODO: GET PRICE BY NAME, NOT BY INDEX

                # last control
                best_price = self.calc(float(order[3]))

                if (last_ask >= best_price):
                    pro_price = best_price

            # range mode
            if self.option.mode == 'range':
                pro_price = self.option.sell_price

# TODO: SPAM SELL ORDERS OR NOT, SO WHY THREAD ?

            # start sell action
            if self.sell_order_id == 0 and self.buy_order_id == 1 and self.coin_amount > 0:
                sellAction = threading.Thread(target=self.order_sell, args=(coin_symbol, self.coin_amount, pro_price, last_price,))
                sellAction.start()
                return

        # check if ask price is greater than profit price, buy with my buy price
        if (last_ask >= pro_price and self.option.mode == 'profit' and \
           self.buy_order_id == 0 and self.sell_order_id == 0 and self.coin_amount == 0) or \
           (last_price <= float(self.option.buy_price) and self.option.mode == 'range'):
              self.logger.info("Mode: {0}, LastAsk: {1}, Profit Sell Price {2}, ".format(self.option.mode, last_ask, pro_price))
              self.buy(coin_symbol, self.coin_amount, buy_price, pro_price)
        else:
            print('LAST: ' + str(last_price) + ' BUY: ' + str(buy_price) + ' SELL: ' + str(pro_price))

              # Perform check/sell action
              # checkAction = threading.Thread(target=self.check, args=(coin_symbol, self.buy_order_id, coin_amount,))
              # checkAction.start()

        print('HAVE BUY ORDER: ' + str(self.buy_order_id))
        print('HAVE SELL ORDER: ' + str(self.sell_order_id))

    def logic(self):
        return 0

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

    def run(self):

        # for check errors
        valid = True

        # get coin symbol
        coin_symbol = self.option.symbol

        # get coin settings
        coin_sets = self.get_coin_sets(coin_symbol)['filters']

        # minimal order price
        order_min_price = float(coin_sets['MIN_NOTIONAL']['minNotional'])

        # minimal coin price
        coin_min_price = float(coin_sets['PRICE_FILTER']['minPrice'])

        # minimal lot amount
        lot_min_amount = float(coin_sets['LOT_SIZE']['minQty'])

        # minimal lot step size
        lot_min_step = float(coin_sets['LOT_SIZE']['stepSize'])

        # minimal price step size
        price_min_step = float(coin_sets['PRICE_FILTER']['tickSize'])

        # get market order book prices
        last_bid, last_ask = Orders.get_order_book(coin_symbol)

        # fix float length
        last_bid = self.float_format(last_bid, price_min_step)
        last_ask = self.float_format(last_ask, price_min_step)

        # get market current coin price
        last_price = Orders.get_ticker(coin_symbol)

        # fix float length
        last_price = self.float_format(last_price, price_min_step)

        # check if price_increase greater than price_min_step
        if (float(self.option.price_increase) < price_min_step):
            self.price_increase = price_min_step
        else:
            # fix float length
            self.price_increase = self.float_format(self.price_increase, price_min_step)

        # check if price_decrease greater than price_min_step
        if (float(self.option.price_decrease) < price_min_step):
            self.price_decrease = price_min_step
        else:
            # fix float length
            self.price_decrease = self.float_format(self.price_decrease, price_min_step)

        # to be sure to exceed the limit (for example, min order price)
        last_bid = last_bid + self.price_increase

        # calculate amount to quantity
        #if self.amount > 0:
        #    quantity = (self.amount / last_bid)

        # check if amount is zero, order price increase 10%
        if self.coin_amount > 0:
            coin_amount = self.coin_amount
        else:
            coin_amount = (order_min_price / last_bid)
            coin_amount = coin_amount + (coin_amount * 10 / 100)

        # fix float length
        coin_amount = self.float_format(coin_amount, lot_min_step)

        notional = last_bid * float(coin_amount)

        # fix float length
        notional = self.float_format(notional, price_min_step)

        # lot_min_amount = minimum order quantity
        if coin_amount < lot_min_amount:
            self.logger.error('Invalid coin amount, lot min amount: %.8f (u: %.8f)' % (lot_min_amount, coin_amount))
            valid = False

        if last_price < coin_min_price:
            print('Invalid price, coin min price: %.8f (u: %.8f)' % (coin_min_price, last_price))
            self.logger.error('Invalid price, coin min price: %.8f (u: %.8f)' % (coin_min_price, last_price))
            valid = False

        # order_min_price = minimum order value (price * coin_amount)
        if notional < order_min_price:
            print('Invalid notional, order min price: %.8f (u: %.8f)' % (order_min_price, notional))
            self.logger.error('Invalid notional, order min price: %.8f (u: %.8f)' % (order_min_price, notional))
            valid = False

        # check if have errors, exit
        if not valid:
            exit(1)

        # set global variables
        self.notional = notional
        self.coin_amount = coin_amount
        self.lot_step = lot_min_step
        self.price_step = price_min_step

        # print coin settings
        print('\n')
        print('COIN SETTINGS')
        print('Trading symbol: %s' % coin_symbol)
        print('Minimal order: %s $' % order_min_price)
        print('Lot step: %s' % lot_min_step)
        print('Price step: %s $' % price_min_step)

        # print account settings
        print('\n')
        print('ACCOUNT SETTINGS')
        print('Account type: %s' % Account.account_type())
        print('We can trade: %s' % Account.can_trade())
        if self.option.test_mode == True:
            balance_usdt = self.balance_usdt
        else:
            balance_usdt = Account.balance()
        print('Balance usdt: %s $' % balance_usdt)
        print('Connection status: %s ms' % Account.server_status())

        print('\n')
        print('BOT SETTINGS')
        print('Order price: %s $' % self.notional)
        print('Order amount: %s' % self.coin_amount)
        print('Stoploss amount: %s' % self.stop_loss)
        print('BNB commission: %s $' % self.commission)
        #print('Estimated profit: %s' % (self.coin_amount * self.option.profit))

        if self.option.mode == 'range':
           if self.option.buyprice == 0 or self.option.sell_price == 0:
               print('Please enter --buy_price / --sell_price\n')
               exit(1)
           print('Range Mode Options:')
           print('\tBuy Price: %.8f', self.option.buy_price)
           print('\tSell Price: %.8f', self.option.sell_price)
        else:
            print('Take profit: %0.2f %%' % self.option.profit)
            print('Buy price: bid + %s' % self.price_increase)
            print('Sell price: ask - %s + commission' % self.price_decrease)

        startTime = time.time()

        """
        # DEBUG LINES
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
        actions = []

        if self.option.test_mode == True:
            test_msg = ' IN TEST MODE'
        print('\n')
        print('BOT STARTED' + test_msg)
        print('\n')

        while (cycle <= self.option.loop):

           startTime = time.time()

           actionTrader = threading.Thread(target=self.action, args=(coin_symbol,))
           actions.append(actionTrader)
           actionTrader.start()

           endTime = time.time()

           if endTime - startTime < self.wait_time:

               time.sleep(self.wait_time - (endTime - startTime))

               # 0 = Unlimited loop
               if self.option.loop > 0:
                   cycle = cycle + 1
