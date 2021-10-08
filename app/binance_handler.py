import config
from time import time
from datetime import timedelta, datetime
from app.binance import Binance
from app.messages import Messages

client = Binance(config.api_key, config.api_secret)


class BinanceHandler:

    # TODO: append data
    @staticmethod
    def balances():
        balances = client.get_account()
        data = []
        if len(balances['balances']) == 0: return 0
        for balance in balances['balances']:
            if float(balance['locked']) > 0 or float(balance['free']) > 0:
                print('%s: %s' % (balance['asset'], balance['free']))
        return data

    @staticmethod
    def balance(asset='USDT'):
        # returned json data
        # {'makerCommission': 10, 'takerCommission': 10, 'buyerCommission': 0, 'sellerComm
        # ission': 0, 'canTrade': True, 'canWithdraw': True, 'canDeposit': True, 'updateTi
        # me': 1615388330652, 'accountType': 'SPOT', 'balances': [], 'permissions': ['SPOT
        # ']}
        balances = client.get_account()
        if len(balances['balances']) == 0: return 0
        balances['balances'] = {item['asset']: item for item in balances['balances']}
        return balances['balances'][asset]['free']

    @staticmethod
    def account_type():  # get account type
        balances = client.get_account()
        return balances['accountType'].lower()

    @staticmethod
    def can_trade():  # get trade status
        balances = client.get_account()
        if balances['canTrade']: return 'yes'
        else: return 'no'

    @staticmethod
    def orders(symbol, limit):  # get orders
        orders = client.get_open_orders(symbol, limit)
        return orders

    @staticmethod
    def server_status():  # get server status
        # timestamp when requested was launch
        systemT = int(time() * 1000)
        # timestamp when server replied
        serverT = client.get_server_time()
        lag = int(serverT['serverTime'] - systemT)
        #print('System timestamp: %d' % systemT)
        #print('Server timestamp: %d' % serverT['serverTime'])
        #print('Lag: %d' % lag)
        #if lag > 1000:
        #    return 'Not good. Excessive lag (lag > 1000ms)'
        #elif lag < 0:
        #    return 'Not good. System time ahead server time (lag < 0ms)'
        #else:
        #    return 'Good (0ms > lag > 1000ms)'
        return lag

    @staticmethod
    def openorders():
        return client.get_open_orders()

    @staticmethod
    def profits(asset = 'USDT'):
        coins = client.get_products()
        for coin in coins['data']:
            if coin['quoteAsset'] == asset:
                orders = client.get_order_books(coin['symbol'], 5)
                if len(orders['bids']) > 0 and len(orders['asks']) > 0:
                    lastBid = float(orders['bids'][0][0]) #last buy price (bid)
                    lastAsk = float(orders['asks'][0][0]) #last sell price (ask)
                    if lastBid != 0:
                        profit = (lastAsk - lastBid) /  lastBid * 100
                    else:
                        profit = 0
                    return '%6.2f%% profit : %s (bid: %.8f / ask: %.8f)' % (profit, coin['symbol'], lastBid, lastAsk)
                else:
                    return '---.--%% profit : %s (No bid/ask info retrieved)' % (coin['symbol'])

    # TODO: append data
    @staticmethod
    def market_value(symbol, kline_size, dateS, dateF = '' ):
        dateS = datetime.strptime(dateS, "%d/%m/%Y %H:%M:%S")
        data = []
        if dateF != '':
            dateF=datetime.strptime(dateF, "%d/%m/%Y %H:%M:%S")
        else:
            dateF = dateS + timedelta(seconds = 59)
        #print('Retrieving values...\n')
        klines = client.get_klines(symbol, kline_size, int(dateS.timestamp() * 1000), int(dateF.timestamp() * 1000))
        if len(klines) > 0:
            for kline in klines:
                print('[%s] Open: %s High: %s Low: %s Close: %s' % (datetime.fromtimestamp(kline[0] / 1000), kline[1], kline[2], kline[3], kline[4]))
        return data

#######################################################################################################

    @staticmethod  # create limit buy order
    def buy_limit(symbol, quantity, buy_price):
        order = client.buy_limit(symbol, quantity, buy_price)
        if 'msg' in order:
            Messages.get(order['msg'])
        return order['orderId']

    @staticmethod  # create limit sell order
    def sell_limit(symbol, quantity, sell_price):
        order = client.sell_limit(symbol, quantity, sell_price)
        if 'msg' in order:
            Messages.get(order['msg'])
        return order

    @staticmethod
    def buy_market(symbol, quantity):
        order = client.buy_market(symbol, quantity)
        if 'msg' in order:
            Messages.get(order['msg'])
        return order

    @staticmethod
    def sell_market(symbol, quantity):
        order = client.sell_market(symbol, quantity)
        if 'msg' in order:
            Messages.get(order['msg'])
        return order

    @staticmethod
    def cancel_order(symbol, orderId):
        try:
            order = client.cancel(symbol, orderId)
            if 'msg' in order:
                Messages.get(order['msg'])
            print('Profit loss, called order, %s' % (orderId))
            return True
        except Exception as e:
            print('cancel_order Exception: %s' % e)
            return False

    @staticmethod
    def get_order_book(symbol):
        try:
            # example data returned
            # {'lastUpdateId': 34959506, 'bids': [['3.74950000', '40.00000000'], ['3.74940000'
            # , '7.94000000'], ['3.74850000', '4.64000000'], ['3.74820000', '7.14000000'], ['3
            # .74660000', '89.92000000']], 'asks': [['3.77170000', '26.86000000'], ['3.7718000
            # 0', '41.10000000'], ['3.77210000', '6.91000000'], ['3.77220000', '1307.11000000'
            # ], ['3.77240000', '215.90000000']]}
            orders = client.get_order_books(symbol, 5)
            lastBid = float(orders['bids'][0][0]) #last buy price (bid)
            lastAsk = float(orders['asks'][0][0]) #last sell price (ask)
            return lastBid, lastAsk
        except Exception as e:
            print('get_order_book Exception: %s' % e)
            return 0, 0

    @staticmethod
    def get_order(symbol, orderId):
        try:
            order = client.query_order(symbol, orderId)
            if 'msg' in order:
                #import ipdb; ipdb.set_trace()
                Messages.get(order['msg']) # TODO
                return False
            return order
        except Exception as e:
            print('get_order Exception: %s' % e)
            return False

    @staticmethod
    def get_order_status(symbol, orderId):
        try:
            order = client.query_order(symbol, orderId)
            if 'msg' in order:
                Messages.get(order['msg'])
            return order['status']
        except Exception as e:
            print('get_order_status Exception: %s' % e)
            return None

    @staticmethod
    def get_ticker(symbol):  # get ticker info
        # {'symbol': 'AVAUSDT', 'priceChange': '-0.21460000', 'priceChangePercent': '-5.60
        # 8', 'weightedAvgPrice': '3.90048603', 'prevClosePrice': '3.82630000', 'lastPrice
        # ': '3.61210000', 'lastQty': '6.75000000', 'bidPrice': '3.60700000', 'bidQty': '8
        # 9.50000000', 'askPrice': '3.60880000', 'askQty': '9.43000000', 'openPrice': '3.8
        # 2670000', 'highPrice': '4.25990000', 'lowPrice': '3.59290000', 'volume': '167702
        # 3.60000000', 'quoteVolume': '6541207.13088600', 'openTime': 1615504164230, 'clos
        # eTime': 1615590564230, 'firstId': 1056067, 'lastId': 1088663, 'count': 32597}
        try: return client.get_ticker(symbol.upper())
        except Exception as e: print('Get Ticker Exception: %s' % e)

    @staticmethod
    def get_products():  # get list of coins
        # dict_keys(['timezone', 'serverTime', 'rateLimits', 'exchangeFilters', 'symbols'])
        # symbol keys:
        # {'symbol': 'SUPERUSDT', 'status': 'TRADING', 'baseAsset': 'SUPER', 'baseAssetPrecision': 8,
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
        try: return client.get_exchange_info()
        except Exception as e: print('Get Coins Exception: %s' % e)
