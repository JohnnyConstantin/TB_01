import sys
sys.path.insert(0, './app')
import time
import config
from datetime import timedelta, datetime
from BinanceAPI import BinanceAPI

client = BinanceAPI(config.api_key, config.api_secret)

class Account:

    #def __init__(self):
    #    self.client = BinanceAPI(config.api_key, config.api_secret)

    # TODO: append data
    @staticmethod
    def balances():
        balances = client.get_account()
        data = []
        if len(balances['balances']) == 0:
            return 0
        for balance in balances['balances']:
            if float(balance['locked']) > 0 or float(balance['free']) > 0:
                print('%s: %s' % (balance['asset'], balance['free']))
        return data

    @staticmethod
    def balance(asset = 'USDT'):
        # returned json data
        # {'makerCommission': 10, 'takerCommission': 10, 'buyerCommission': 0, 'sellerComm
        # ission': 0, 'canTrade': True, 'canWithdraw': True, 'canDeposit': True, 'updateTi
        # me': 1615388330652, 'accountType': 'SPOT', 'balances': [], 'permissions': ['SPOT
        # ']}
        balances = client.get_account()
        if len(balances['balances']) == 0:
            return 0
        balances['balances'] = {item['asset']: item for item in balances['balances']}
        return balances['balances'][asset]['free']

    @staticmethod
    def account_type():
        balances = client.get_account()
        return balances['accountType'].lower()

    @staticmethod
    def can_trade():
        balances = client.get_account()
        if balances['canTrade'] == True:
            return 'yes'
        else:
            return 'no'

    @staticmethod
    def orders(symbol, limit):
        orders = client.get_open_orders(symbol, limit)
        return orders

    @staticmethod
    def tickers():
        return client.get_all_tickers()

    @staticmethod
    def server_status():

        # timestamp when requested was launch
        systemT = int(time.time() * 1000)

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