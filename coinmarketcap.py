import requests
import time


class CoinMarketCapAPI:
    def __init__(self):
        self.base_uri = 'https://api.coinmarketcap.com/v1/ticker/?convert=eur&limit=30'
        self.last_updated = 0
        self.ticker = {}

    def update(self):
        if self.last_updated < (time.time() - 600):
            response = requests.get(self.base_uri)
            self.ticker = {coin['symbol']: coin for coin in response.json()}
            self.last_updated = time.time()

    def list(self):
        self.update()
        return self.ticker.keys()

    def get_coin(self, symbol):
        self.update()
        symbol = symbol.upper()
        if symbol not in self.ticker:
            return None

        return self.ticker[symbol]
