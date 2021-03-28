import config
from BinanceAPI import BinanceAPI
from Messages import Messages

client = BinanceAPI(config.api_key, config.api_secret)

class Orders():

    # create limit buy order
    @staticmethod
    def buy_limit(symbol, quantity, buy_price):
        order = client.buy_limit(symbol, quantity, buy_price)
        if 'msg' in order:
            Messages.get(order['msg'])
        return order['orderId']

    # create limit sell order
    @staticmethod
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
    def get_ticker(symbol):
        try:
            # example json returned
            # {'symbol': 'AVAUSDT', 'priceChange': '-0.21460000', 'priceChangePercent': '-5.60
            # 8', 'weightedAvgPrice': '3.90048603', 'prevClosePrice': '3.82630000', 'lastPrice
            # ': '3.61210000', 'lastQty': '6.75000000', 'bidPrice': '3.60700000', 'bidQty': '8
            # 9.50000000', 'askPrice': '3.60880000', 'askQty': '9.43000000', 'openPrice': '3.8
            # 2670000', 'highPrice': '4.25990000', 'lowPrice': '3.59290000', 'volume': '167702
            # 3.60000000', 'quoteVolume': '6541207.13088600', 'openTime': 1615504164230, 'clos
            # eTime': 1615590564230, 'firstId': 1056067, 'lastId': 1088663, 'count': 32597}
            ticker = client.get_ticker(symbol)
            return float(ticker['lastPrice'])
        except Exception as e:
            print('Get Ticker Exception: %s' % e)

    @staticmethod
    def get_info(symbol):
        try:
            info = client.get_exchange_info()
            if symbol != "":
                return [market for market in info['symbols'] if market['symbol'] == symbol][0]
            return info
        except Exception as e:
            print('get_info Exception: %s' % e)

    # return list of products currently listed on binance
    @staticmethod
    def get_products():
        #return client.get_products()
        return client.get_exchange_info()
