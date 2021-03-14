# -*- coding: UTF-8 -*-
# @yasinkuyu

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
from Database import Database
from Account import Account
from Orders import Orders
from Logger import CustomFormatter

formater_str = '%(asctime)s,%(msecs)d %(levelname)s %(name)s: %(message)s'
formatter = logging.Formatter(formater_str)
datefmt="%Y-%b-%d %H:%M:%S"

LOGGER_ENUM = {'debug':'debug.log', 'trading':'trades.log','errors':'general.log'}
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


class Trading():

    # Define trade vars
    buy_order_id = 0
    sell_order_id = 0
    coin_quantity = 0
    order_id = 0
    order_data = None

    buy_filled = True
    sell_filled = True

    buy_filled_qty = 0
    sell_filled_qty = 0

    # percent (When you drop 10%, sell panic.)
    stop_loss = 0

    # order price (for print at bot start)
    notional = 0

    # the quantity of coins to buy or sell in the order
    quantity = 0

    # BTC amount
    amount = 0

    # float(step_size * math.floor(float(free)/step_size))
    step_size = 0

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
        self.quantity = self.option.quantity
        self.wait_time = self.option.wait_time
        self.stop_loss = self.option.stop_loss

        self.increasing = self.option.increasing
        self.decreasing = self.option.decreasing

        # BTC amount
        self.amount = self.option.amount

        # type of commission
        if self.option.commission == 'TOKEN':
            self.commission = TOKEN_COMMISSION

        # setup Logger
        self.logger =  self.setup_logger(self.option.symbol, debug = self.option.debug)

        # if test mode enabled, delete buy and sell orders
        if self.option.test_mode == True:
            Database.delete(1)
            Database.delete(2)

    def setup_logger(self, symbol, debug = True):
        """Function setup as many loggers as you want"""
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

    def buy(self, symbol, quantity, buy_price, profitableSellingPrice):

        # check if open orders exists - return
        self.check_order()

# TODO: REWORK
        buy_price = float('{:.8f}'.format(buy_price))
        profitableSellingPrice = float('{:.8f}'.format(profitableSellingPrice))

        try:
            # create buy order
            if self.option.test_mode == True:
                orderId = 1
            else:
                orderId = Orders.buy_limit(symbol, quantity, buy_price)

            # write buy order to database
            Database.write([orderId, symbol, 0, buy_price, 'BUY', quantity, self.option.profit])

            #print('Buy order created id:%d, q:%.8f, p:%.8f' % (orderId, quantity, float(buy_price)))
            self.logger.info('Buy order created id: %d, q: %s, p: %s, Take profit aprox :%s' % (orderId, quantity, float(buy_price), profitableSellingPrice))

            self.buy_order_id = 1
            self.order_id = orderId
            return orderId

        except Exception as e:
            #print('bl: %s' % (e))
            self.logger.debug('Buy error: %s' % (e))
            time.sleep(self.WAIT_TIME_BUY_SELL)
            return None

# TODO: TRY, EXCEPT
    # check buy order status
    def buy_order_check(self, buy_order):

        # if buy order status is 'FILLED' - all ok
        if buy_order['status'] == 'FILLED' and buy_order['side'] == 'BUY':
            #print('Buy order filled... Try sell...')
            self.logger.info('Buy order filled... Try sell...')
            return True

        else:
            # wait before check buy order status
            time.sleep(self.WAIT_TIME_CHECK_BUY_SELL)

            # if buy order status is 'FILLED' - all ok
            if buy_order['status'] == 'FILLED' and buy_order['side'] == 'BUY':
                #print('Buy order filled after 0.1 second... Try sell...')
                self.logger.info('Buy order filled after 0.1 second... Try sell...')

            # if buy order status is 'PARTIALLY_FILLED' - cancel order
            elif buy_order['status'] == 'PARTIALLY_FILLED' and buy_order['side'] == 'BUY':
                #print('Buy order partially filled... Try sell... Cancel remaining buy...')
                self.logger.info('Buy order partially filled... Try sell... Cancel remaining buy...')
                self.cancel(symbol, orderId)

            # else - cancel order
            else:
                self.cancel(symbol, orderId)
                #print('Buy order fail (Not filled) Cancel order...')
                self.logger.warning('Buy order fail (Not filled) Cancel order...')
                self.order_id = 0
        return False

    def sell(self, symbol, quantity, orderId, sell_price, last_price):

        '''
        The specified limit will try to sell until it reaches.
        If not successful, the order will be canceled.
        '''

# TODO: REWORK
        sell_price = float('{:.8f}'.format(sell_price))
        last_price = float('{:.8f}'.format(last_price))

        # get buy order
        if self.option.test_mode == True:
            orderId = 1
            buy_order = Database.read(orderId)

            #if buy_order == None:
            #    return

        else:
            buy_order = Orders.get_order(symbol, orderId)

            # check buy order
            if self.buy_order_check(buy_order) == False:
                return

        # create sell order
        if self.option.test_mode == True:
            orderId = 2
            order = [orderId, symbol, 0, sell_price, 'SELL', quantity, last_price]

        else:
            sell_order = Orders.sell_limit(symbol, quantity, sell_price)
            orderId = sell_order['orderId']
            # wait before check sell order
            time.sleep(self.WAIT_TIME_CHECK_SELL)

            if sell_order_check() == True:
                return

# TODO: ADD USDT AFTER SELL ORDER

        #self.logger.info('Sell order create id: %d' % orderId)
        self.logger.info('Sell order created id: %d, q: %s, p: %s, Last price :%s' % (orderId, quantity, float(sell_price), last_price))

        # write sell order to database
        Database.write([orderId, symbol, 0, sell_price, 'SELL', quantity, last_price])
        self.sell_order_id = 2

        # if all sales trials fail, the grievance is stop-loss
        if self.stop_loss > 0:

            # If sell order failed after 5 seconds, 5 seconds more wait time before selling at loss
            time.sleep(self.WAIT_TIME_CHECK_SELL)

            if self.stop(symbol, quantity, orderId, last_price):

                if Orders.get_order(symbol, orderId)['status'] != 'FILLED':
                    #print('We apologize... Sold at loss...')
                    self.logger.info('We apologize... Sold at loss...')

            else:
                #print('We apologize... Cant sell even at loss... Please sell manually... Stopping program...')
                self.logger.info('We apologize... Cant sell even at loss... Please sell manually... Stopping program...')
                self.cancel(symbol, orderId)
                exit(1)

            while (sell_status != 'FILLED'):
                time.sleep(self.WAIT_TIME_CHECK_SELL)
                sell_status = Orders.get_order(symbol, orderId)['status']
                lastPrice = Orders.get_ticker(symbol)
                #print('Status: %s Current price: %.8f Sell price: %.8f' % (sell_status, lastPrice, sell_price))
                #print('Sold! Continue trading...')

                self.logger.info('Status: %s Current price: %.8f Sell price: %.8f' % (sell_status, lastPrice, sell_price))
                self.logger.info('Sold! Continue trading...')


            self.order_id = 0
            self.order_data = None

    # check sell order
    def sell_order_check(self, sell_order):
        # if sell order is 'FILLED' - all ok
        if sell_order['status'] == 'FILLED':

            #print('Sell order (Filled) Id: %d' % orderId)
            #print('LastPrice : %.8f' % last_price)
            #print('Profit: %%%s. Buy price: %.8f Sell price: %.8f' % (self.option.profit, float(sell_order['price']), sell_price))

            self.logger.info('Sell order (Filled) Id: %d' % sell_order['orderId'])
            self.logger.info('LastPrice : %.8f' % sell_order['last_price'])
            self.logger.info('Profit: %%%s. Buy price: %.8f Sell price: %.8f' % (self.option.profit, float(sell_order['price']), sell_order['last_price']))

            self.order_id = 0
            self.order_data = None
            return True
        return False

    def stop(self, symbol, quantity, orderId, last_price):
        # If the target is not reached, stop-loss.
        stop_order = Orders.get_order(symbol, orderId)

        stopprice =  self.calc(float(stop_order['price']))

        lossprice = stopprice - (stopprice * self.stop_loss / 100)

        status = stop_order['status']

        # Order status
        if status == 'NEW' or status == 'PARTIALLY_FILLED':

            if self.cancel(symbol, orderId):

                # Stop loss
                if last_price >= lossprice:

                    sello = Orders.sell_market(symbol, quantity)

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
                            self.cancel(symbol, sell_id)
                            return False
                else:
                    sello = Orders.sell_limit(symbol, quantity, lossprice)
                    print('Stop-loss, sell limit, %s' % (lossprice))
                    time.sleep(self.WAIT_TIME_STOP_LOSS)
                    statusloss = sello['status']
                    if statusloss != 'NEW':
                        print('Stop-loss, sold')
                        return True
                    else:
                        self.cancel(symbol, sell_id)
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

    def check(self, symbol, orderId, quantity):
        # If profit is available and there is no purchase from the specified price, take it with the market.

        # check if open order exists - return
        self.check_order()

        trading_size = 0
        time.sleep(self.WAIT_TIME_BUY_SELL)

        while trading_size < self.MAX_TRADE_SIZE:

            # Order info
            order = Orders.get_order(symbol, orderId)

            side  = order['side']
            price = float(order['price'])

            # TODO: Sell partial qty
            orig_qty = float(order['origQty'])
            self.buy_filled_qty = float(order['executedQty'])

            status = order['status']

            #print('Wait buy order: %s id:%d, price: %.8f, orig_qty: %.8f' % (symbol, order['orderId'], price, orig_qty))
            self.logger.info('Wait buy order: %s id:%d, price: %.8f, orig_qty: %.8f' % (symbol, order['orderId'], price, orig_qty))

            if status == 'NEW':

                if self.cancel(symbol, orderId):

                    buyo = Orders.buy_market(symbol, quantity)

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

    # if order is not filled, cancel it
    def cancel(self, symbol, orderId):

        # get order
        order = Orders.get_order(symbol, orderId)

        # if order does not exist - all ok
        if not order:
            self.order_id = 0
            self.order_data = None
            return True

        # if order exists with status 'NEW' or 'CANCELLED' - cancel order
        if order['status'] == 'NEW' or order['status'] != 'CANCELLED':
            Orders.cancel_order(symbol, orderId)
            self.order_id = 0
            self.order_data = None
            return True

    def calc(self, lastBid):
        try:
            sell_price = lastBid + (lastBid * self.option.profit / 100)
            commission = (lastBid * self.commission)
            # estimated sell price considering commission
            return sell_price + commission
        except Exception as e:
            print('Calc Error: %s' % (e))
            return

    # check if there is an open order, exit
    def check_order(self):
        if self.order_id > 0:
            exit(1)

    def action(self, symbol):
        #import ipdb; ipdb.set_trace()

        # the quantity of coins to buy or sell in the order
        quantity = self.quantity

        # get current ticker price
        lastPrice = Orders.get_ticker(symbol)

        # get buy and sell prices from order book
        lastBid, lastAsk = Orders.get_order_book(symbol)

        # target buy price with little increase
        buyPrice = lastBid + self.increasing
        #buyPrice = lastPrice + self.increasing

        # target sell price with little decrease
        sellPrice = lastAsk - self.decreasing

        # profitable selling price
        profitableSellingPrice = self.calc(lastBid)

        # Check working mode
        if self.option.mode == 'range':
            buyPrice = float(self.option.buyprice)
            sellPrice = float(self.option.sellprice)
            profitableSellingPrice = sellPrice

        # screen log
        if self.option.prints and self.order_id == 0:
            spreadPerc = (lastAsk/lastBid - 1) * 100.0
            #print('price:%.8f buyp:%.8f sellp:%.8f bid:%.8f ask:%.8f spread:%.2f' % (lastPrice, buyPrice, profitableSellingPrice, lastBid, lastAsk, spreadPerc))
            #print('price:%.8f buyp:%.8f sellp:%.8f bid:%.8f ask:%.8f spread:%.2f' % (lastPrice, buyPrice, profitableSellingPrice, lastBid, lastAsk, spreadPerc))
            #print('\n')
            self.logger.debug('price:%.8f buyprice:%.8f sellprice:%.8f bid:%.8f ask:%.8f spread:%.2f Originalsellprice:%.8f' % (lastPrice, buyPrice, profitableSellingPrice, lastBid, lastAsk, spreadPerc, profitableSellingPrice-(lastBid *self.commission)   ))

        # analyze = threading.Thread(target=analyze, args=(symbol,))
        # analyze.start()

        if self.option.test_mode == True:
            buy_order = Database.read(1)
            if buy_order != None and lastPrice >= buy_order[3]:
                Database.delete(1)
                self.buy_order_id = 0
                self.coin_quantity = self.coin_quantity + buy_order[5]
                print('SUCCESSFULLY BOUGHT COINS!')
                print('COIN AMOUNT: ' + str(self.coin_quantity))
                print('COIN BUY PRICE: ' + str(buy_order[3]) + ' $')

            sell_order = Database.read(2)
            if sell_order != None and lastPrice >= sell_order[3]:
                Database.delete(2)
                self.sell_order_id = 0
                self.coin_quantity = self.coin_quantity - sell_order[5]
                print('SUCCESSFULLY SOLD COINS!')
                print('COIN AMOUNT: ' + str(self.coin_quantity))
                print('COIN SELL PRICE: ' + str(sell_order[3]) + ' $')
                print('BALANCE: TODO')
                self.order_id = 0

        if self.option.test_mode == True:
            order_data = Database.read(2)
            if order_data != None:
                self.order_data = order_data
                self.order_id = 1

        if self.coin_quantity > 0 or self.buy_order_id > 0:
            # profit mode
            if self.order_data is not None:
                order = self.order_data

# TODO: GET PRICE BY NAME, NOT BY INDEX
                # last control
                #newProfitableSellingPrice = self.calc(float(order['price']))
                newProfitableSellingPrice = self.calc(float(order[3]))

                if (lastAsk >= newProfitableSellingPrice):
                    profitableSellingPrice = newProfitableSellingPrice

            # range mode
            if self.option.mode == 'range':
                profitableSellingPrice = self.option.sellprice

            '''            
            If the order is complete, 
            try to sell it.
            '''

            # perform sell action

            if self.sell_order_id == 0:
                sellAction = threading.Thread(target = self.sell, args = (symbol, quantity, self.order_id, profitableSellingPrice, lastPrice,))
                sellAction.start()
                return

        '''
        Did profit get caught
        if ask price is greater than profit price,
        buy with my buy price,
        '''

# 3.9195
# 3.9037153499999997
# 2021-03-14 13:29:28,561,561 INFO AVAUSDT: Mode: profit, Lastsk: 3.9195, Profit Sell Price 3.9037153499999997,0
#
# Message : Account has insufficient balance for requested action.
# price:3.90750000 buyp:3.89040000 sellp:3.90391605 bid:3.89030000 ask:3.91950000
# spread:0.75
        #print(str(lastAsk) + ' ' + str(profitableSellingPrice))
        if (lastAsk >= profitableSellingPrice and self.option.mode == 'profit') or \
           (lastPrice <= float(self.option.buyprice) and self.option.mode == 'range'):
            if self.order_id == 0:
                self.logger.info ("Mode: {0}, LastAsk: {1}, Profit Sell Price {2}, ".format(self.option.mode, lastAsk, profitableSellingPrice))
                self.buy(symbol, quantity, buyPrice, profitableSellingPrice)

                # Perform check/sell action
                # checkAction = threading.Thread(target=self.check, args=(symbol, self.order_id, quantity,))
                # checkAction.start()

    def logic(self):
        return 0

    def filters(self):

        symbol = self.option.symbol

        # Get symbol exchange info
        symbol_info = Orders.get_info(symbol)

        if not symbol_info:
            #print('Invalid symbol, please try again...')
            self.logger.error('Invalid symbol, please try again...')
            exit(1)

        symbol_info['filters'] = {item['filterType']: item for item in symbol_info['filters']}

        return symbol_info

    def float_format(self, quantity, step_size):
        step_str = str(step_size)
        step_len = str(len(step_str) - step_str.index('.') - 1)
        qty_format = float(step_size * math.floor(float(quantity) / step_size))
        return float('{:.{width}f}'.format(qty_format, width = step_len))

    def validate(self):

        valid = True

        print('\n')
        print('COIN SETTINGS')

        # current symbol
        symbol = self.option.symbol
        print('Trading symbol: %s' % symbol)

        # get symbol settings
        filters = self.filters()['filters']

        # get order book prices
        lastBid, lastAsk = Orders.get_order_book(symbol)

        # get current price
        lastPrice = Orders.get_ticker(symbol)
        #lastPrice = '{:.8f}%'.format(lastPrice)
        #print('Current price: %s' % lastPrice)

        # minimal quantity
        minQty = float(filters['LOT_SIZE']['minQty'])
        #print('Minimal quantity: %s' % minQty)

        # minimal price
        minPrice = float(filters['PRICE_FILTER']['minPrice'])
        #print('Minimal price: %s' % minPrice)

        # minimal price for buy or sell
        minNotional = float(filters['MIN_NOTIONAL']['minNotional'])
        print('Minimal notional: %s $' % minNotional)

        # quantity from options
        quantity = float(self.option.quantity)
        #print('quantity: %s' % quantity)

        # stepSize defines the intervals that a quantity/icebergQty can be increased/decreased by
        stepSize = float(filters['LOT_SIZE']['stepSize'])
        print('Lot step: %s' % stepSize)

        # tickSize defines the intervals that a price/stopPrice can be increased/decreased by
        tickSize = float(filters['PRICE_FILTER']['tickSize'])
        print('Price step: %s $' % tickSize)

        # check if option increasing size greater than tickSize
        if (float(self.option.increasing) < tickSize):
            self.increasing = tickSize

        # check if option decreasing size greater than tickSize
        if (float(self.option.decreasing) < tickSize):
            self.decreasing = tickSize

        # just for validation
        lastBid = lastBid + self.increasing

        # check if quantity or amount is zero, minNotional increase 10%
        quantity = (minNotional / lastBid)
        quantity = quantity + (quantity * 10 / 100)
        notional = minNotional

        # calculate amount to quantity
        if self.amount > 0:
            quantity = (self.amount / lastBid)

        # check quantity
        if self.quantity > 0:
            quantity = self.quantity

        quantity = self.float_format(quantity, stepSize)
        notional = lastBid * float(quantity)

        # set globals
        self.notional = notional
        self.quantity = quantity
        self.step_size = stepSize

        # minQty = minimum order quantity
        if quantity < minQty:
            #print('Invalid quantity, minQty: %.8f (u: %.8f)' % (minQty, quantity))
            self.logger.error('Invalid quantity, minQty: %.8f (u: %.8f)' % (minQty, quantity))
            valid = False

        if lastPrice < minPrice:
            print('Invalid price, minPrice: %.8f (u: %.8f)' % (minPrice, lastPrice))
            self.logger.error('Invalid price, minPrice: %.8f (u: %.8f)' % (minPrice, lastPrice))
            valid = False

        # minNotional = minimum order value (price * quantity)
        if notional < minNotional:
            #print('Invalid notional, minNotional: %.8f (u: %.8f)' % (minNotional, notional))
            self.logger.error('Invalid notional, minNotional: %.8f (u: %.8f)' % (minNotional, notional))
            valid = False

        if not valid:
            exit(1)

    def run(self):

        cycle = 0
        actions = []
        symbol = self.option.symbol

        # validate symbol
        self.validate()

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
        print('Order price: %.8f $' % self.notional)
        print('Order amount: %s' % self.quantity)
        print('Stoploss amount: %s' % self.stop_loss)
        print('BNB commission: %s $' % self.commission)
        #print('Estimated profit: %s' % (self.quantity * self.option.profit))

        if self.option.mode == 'range':
           if self.option.buyprice == 0 or self.option.sellprice == 0:
               print('Please enter --buyprice / --sellprice\n')
               exit(1)
           print('Range Mode Options:')
           print('\tBuy Price: %.8f', self.option.buyprice)
           print('\tSell Price: %.8f', self.option.sellprice)
        else:
            print('Take profit: %0.2f %%' % self.option.profit)
            print('Buy price: bid + %s' % self.increasing)
            print('Sell price: ask - %s + commission' % self.decreasing)

        startTime = time.time()

        """
        # DEBUG LINES
        actionTrader = threading.Thread(target=self.action, args=(symbol,))
        actions.append(actionTrader)
        actionTrader.start()

        endTime = time.time()

        if endTime - startTime < self.wait_time:

            time.sleep(self.wait_time - (endTime - startTime))

            # 0 = Unlimited loop
            if self.option.loop > 0:
                cycle = cycle + 1

        """

        if self.option.test_mode == True:
            test_msg = ' IN TEST MODE'
        print('\n')
        print('BOT STARTED' + test_msg)
        print('\n')

        while (cycle <= self.option.loop):

           startTime = time.time()

           actionTrader = threading.Thread(target=self.action, args=(symbol,))
           actions.append(actionTrader)
           actionTrader.start()

           endTime = time.time()

           if endTime - startTime < self.wait_time:

               time.sleep(self.wait_time - (endTime - startTime))

               # 0 = Unlimited loop
               if self.option.loop > 0:
                   cycle = cycle + 1
