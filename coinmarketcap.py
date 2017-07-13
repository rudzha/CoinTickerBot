import requests
import time


class CoinMarketCapAPI:
    def __init__(self):
        self.base_uri = 'https://api.coinmarketcap.com/v1/ticker/'
        self.last_updated = 0
        self.ticker = {}
        self.limit = 50

    def update(self):
        if self.last_updated < (time.time() - 600):
            payload = {'convert': 'eur', 'limit': 50}
            response = requests.get(self.base_uri, params=payload)
            self.ticker = {coin['symbol']: coin for coin in response.json()}
            self.last_updated = time.time()

    def list(self):
        self.update()
        result = [(value['symbol'], value['name'], value['market_cap_usd']) for key, value in self.ticker.items()]
        return sorted(result, key=lambda x: float(x[2]), reverse=True)

    def get_coin(self, symbol):
        self.update()
        symbol = symbol.upper()
        if symbol not in self.ticker:
            return None

        return self.ticker[symbol]
