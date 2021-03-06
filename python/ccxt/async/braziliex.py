# -*- coding: utf-8 -*-

from ccxt.async.base.exchange import Exchange
import hashlib
import math
from ccxt.base.errors import ExchangeError
from ccxt.base.errors import AuthenticationError
from ccxt.base.errors import InvalidOrder


class braziliex (Exchange):

    def describe(self):
        return self.deep_extend(super(braziliex, self).describe(), {
            'id': 'braziliex',
            'name': 'Braziliex',
            'countries': 'BR',
            'rateLimit': 1000,
            # obsolete metainfo interface
            'hasFetchTickers': True,
            'hasFetchOpenOrders': True,
            'hasFetchMyTrades': True,
            # new metainfo interface
            'has': {
                'fetchDepositAddress': True,
                'fetchTickers': True,
                'fetchOpenOrders': True,
                'fetchMyTrades': True,
            },
            'urls': {
                'logo': 'https://user-images.githubusercontent.com/1294454/34703593-c4498674-f504-11e7-8d14-ff8e44fb78c1.jpg',
                'api': 'https://braziliex.com/api/v1',
                'www': 'https://braziliex.com/',
                'doc': 'https://braziliex.com/exchange/api.php',
                'fees': 'https://braziliex.com/exchange/fees.php',
            },
            'api': {
                'public': {
                    'get': [
                        'currencies',
                        'ticker',
                        'ticker/{market}',
                        'orderbook/{market}',
                        'tradehistory/{market}',
                    ],
                },
                'private': {
                    'post': [
                        'balance',
                        'complete_balance',
                        'open_orders',
                        'trade_history',
                        'deposit_address',
                        'sell',
                        'buy',
                        'cancel_order',
                    ],
                },
            },
            'fees': {
                'trading': {
                    'maker': 0.005,
                    'taker': 0.005,
                },
            },
            'precision': {
                'amount': 8,
                'price': 8,
            },
        })

    async def fetch_currencies(self, params={}):
        currencies = await self.publicGetCurrencies(params)
        ids = list(currencies.keys())
        result = {}
        for i in range(0, len(ids)):
            id = ids[i]
            currency = currencies[id]
            precision = currency['decimal']
            uppercase = id.upper()
            code = self.common_currency_code(uppercase)
            active = currency['active'] == 1
            status = 'ok'
            if currency['under_maintenance'] != 0:
                active = False
                status = 'maintenance'
            canWithdraw = currency['is_withdrawal_active'] == 1
            canDeposit = currency['is_deposit_active'] == 1
            if not canWithdraw or not canDeposit:
                active = False
            result[code] = {
                'id': id,
                'code': code,
                'name': currency['name'],
                'active': active,
                'status': status,
                'precision': precision,
                'wallet': {
                    'address': None,
                    'extra': None,
                    'withdraw': {
                        'active': canWithdraw,
                        'fee': currency['txWithdrawalFee'],
                    },
                    'deposit': {
                        'active': canDeposit,
                        'fee': currency['txDepositFee'],
                    },
                },
                'limits': {
                    'amount': {
                        'min': currency['minAmountTrade'],
                        'max': math.pow(10, precision),
                    },
                    'price': {
                        'min': math.pow(10, -precision),
                        'max': math.pow(10, precision),
                    },
                    'cost': {
                        'min': None,
                        'max': None,
                    },
                    'withdraw': {
                        'min': currency['MinWithdrawal'],
                        'max': math.pow(10, precision),
                    },
                    'deposit': {
                        'min': currency['minDeposit'],
                        'max': None,
                    },
                },
                'info': currency,
            }
        return result

    async def fetch_markets(self):
        markets = await self.publicGetTicker()
        ids = list(markets.keys())
        result = []
        for i in range(0, len(ids)):
            id = ids[i]
            market = markets[id]
            baseId, quoteId = id.split('_')
            base = baseId.upper()
            quote = quoteId.upper()
            base = self.common_currency_code(base)
            quote = self.common_currency_code(quote)
            symbol = base + '/' + quote
            active = market['active'] == 1
            precision = {
                'amount': 8,
                'price': 8,
            }
            lot = math.pow(10, -precision['amount'])
            result.append({
                'id': id,
                'symbol': symbol.upper(),
                'base': base,
                'quote': quote,
                'baseId': baseId,
                'quoteId': quoteId,
                'active': active,
                'lot': lot,
                'precision': precision,
                'limits': {
                    'amount': {
                        'min': lot,
                        'max': math.pow(10, precision['amount']),
                    },
                    'price': {
                        'min': math.pow(10, -precision['price']),
                        'max': math.pow(10, precision['price']),
                    },
                    'cost': {
                        'min': None,
                        'max': None,
                    },
                },
                'info': market,
            })
        return result

    def parse_ticker(self, ticker, market=None):
        symbol = market['symbol']
        timestamp = ticker['date']
        ticker = ticker['ticker']
        return {
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': float(ticker['highestBid24']),
            'low': float(ticker['lowestAsk24']),
            'bid': float(ticker['highestBid']),
            'ask': float(ticker['lowestAsk']),
            'vwap': None,
            'open': None,
            'close': None,
            'first': None,
            'last': float(ticker['last']),
            'change': float(ticker['percentChange']),
            'percentage': None,
            'average': None,
            'baseVolume': float(ticker['baseVolume24']),
            'quoteVolume': float(ticker['quoteVolume24']),
            'info': ticker,
        }

    async def fetch_ticker(self, symbol, params={}):
        await self.load_markets()
        market = self.market(symbol)
        ticker = await self.publicGetTickerMarket(self.extend({
            'market': market['id'],
        }, params))
        ticker = {
            'date': self.milliseconds(),
            'ticker': ticker,
        }
        return self.parse_ticker(ticker, market)

    async def fetch_tickers(self, symbols=None, params={}):
        await self.load_markets()
        tickers = await self.publicGetTicker(params)
        result = {}
        timestamp = self.milliseconds()
        ids = list(tickers.keys())
        for i in range(0, len(ids)):
            id = ids[i]
            market = self.markets_by_id[id]
            symbol = market['symbol']
            ticker = {
                'date': timestamp,
                'ticker': tickers[id],
            }
            result[symbol] = self.parse_ticker(ticker, market)
        return result

    async def fetch_order_book(self, symbol, params={}):
        await self.load_markets()
        orderbook = await self.publicGetOrderbookMarket(self.extend({
            'market': self.market_id(symbol),
        }, params))
        return self.parse_order_book(orderbook, None, 'bids', 'asks', 'price', 'amount')

    def parse_trade(self, trade, market=None):
        timestamp = None
        if 'date_exec' in trade:
            timestamp = self.parse8601(trade['date_exec'])
        else:
            timestamp = self.parse8601(trade['date'])
        price = float(trade['price'])
        amount = float(trade['amount'])
        symbol = market['symbol']
        cost = float(trade['total'])
        orderId = self.safe_string(trade, 'order_number')
        return {
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': symbol,
            'id': self.safe_string(trade, '_id'),
            'order': orderId,
            'type': 'limit',
            'side': trade['type'],
            'price': price,
            'amount': amount,
            'cost': cost,
            'fee': None,
            'info': trade,
        }

    async def fetch_trades(self, symbol, since=None, limit=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        trades = await self.publicGetTradehistoryMarket(self.extend({
            'market': market['id'],
        }, params))
        return self.parse_trades(trades, market, since, limit)

    async def fetch_balance(self, params={}):
        await self.load_markets()
        balances = await self.privatePostCompleteBalance(params)
        result = {'info': balances}
        currencies = list(balances.keys())
        for i in range(0, len(currencies)):
            id = currencies[i]
            balance = balances[id]
            currency = self.common_currency_code(id)
            account = {
                'free': float(balance['available']),
                'used': 0.0,
                'total': float(balance['total']),
            }
            account['used'] = account['total'] - account['free']
            result[currency] = account
        return self.parse_balance(result)

    def parse_order(self, order, market=None):
        symbol = None
        if not market:
            marketId = self.safe_string(order, 'market')
            if marketId:
                if marketId in self.markets_by_id:
                    market = self.markets_by_id[marketId]
        if market:
            symbol = market['symbol']
        timestamp = self.safe_value(order, 'timestamp')
        if not timestamp:
            timestamp = self.parse8601(order['date'])
        price = float(order['price'])
        cost = self.safe_float(order, 'total', 0.0)
        amount = self.safe_float(order, 'amount')
        filledPercentage = self.safe_float(order, 'progress')
        filled = amount * filledPercentage
        remaining = self.amount_to_precision(symbol, amount - filled)
        info = order
        if 'info' in info:
            info = order['info']
        return {
            'id': order['order_number'],
            'datetime': self.iso8601(timestamp),
            'timestamp': timestamp,
            'status': 'open',
            'symbol': symbol,
            'type': 'limit',
            'side': order['type'],
            'price': price,
            'cost': cost,
            'amount': amount,
            'filled': filled,
            'remaining': remaining,
            'trades': None,
            'fee': self.safe_value(order, 'fee'),
            'info': info,
        }

    async def create_order(self, symbol, type, side, amount, price=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        method = 'privatePost' + self.capitalize(side)
        response = await getattr(self, method)(self.extend({
            'market': market['id'],
            # 'price': self.price_to_precision(symbol, price),
            # 'amount': self.amount_to_precision(symbol, amount),
            'price': price,
            'amount': amount,
        }, params))
        success = self.safe_integer(response, 'success')
        if success != 1:
            raise InvalidOrder(self.id + ' ' + self.json(response))
        parts = response['message'].split(' / ')
        parts = parts[1:]
        feeParts = parts[5].split(' ')
        order = self.parse_order({
            'timestamp': self.milliseconds(),
            'order_number': response['order_number'],
            'type': parts[0].lower(),
            'market': parts[0].lower(),
            'amount': parts[2].split(' ')[1],
            'price': parts[3].split(' ')[1],
            'total': parts[4].split(' ')[1],
            'fee': {
                'cost': float(feeParts[1]),
                'currency': feeParts[2],
            },
            'progress': '0.0',
            'info': response,
        }, market)
        id = order['id']
        self.orders[id] = order
        return order

    async def cancel_order(self, id, symbol=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        result = await self.privatePostCancelOrder(self.extend({
            'order_number': id,
            'market': market['id'],
        }, params))
        return result

    async def fetch_open_orders(self, symbol=None, since=None, limit=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        orders = await self.privatePostOpenOrders(self.extend({
            'market': market['id'],
        }, params))
        return self.parse_orders(orders['order_open'], market, since, limit)

    async def fetch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        await self.load_markets()
        market = self.market(symbol)
        trades = await self.privatePostTradeHistory(self.extend({
            'market': market['id'],
        }, params))
        return self.parse_trades(trades['trade_history'], market, since, limit)

    async def fetch_deposit_address(self, currencyCode, params={}):
        await self.load_markets()
        currency = self.currency(currencyCode)
        response = await self.privatePostDepositAddress(self.extend({
            'currency': currency['id'],
        }, params))
        address = self.safe_string(response, 'deposit_address')
        if not address:
            raise ExchangeError(self.id + ' fetchDepositAddress failed: ' + self.last_http_response)
        tag = self.safe_string(response, 'payment_id')
        return {
            'currency': currencyCode,
            'address': address,
            'tag': tag,
            'status': 'ok',
            'info': response,
        }

    def sign(self, path, api='public', method='GET', params={}, headers=None, body=None):
        url = self.urls['api'] + '/' + api
        query = self.omit(params, self.extract_params(path))
        if api == 'public':
            url += '/' + self.implode_params(path, params)
            if query:
                url += '?' + self.urlencode(query)
        else:
            self.check_required_credentials()
            query = self.extend({
                'command': path,
                'nonce': self.nonce(),
            }, query)
            body = self.urlencode(query)
            signature = self.hmac(self.encode(body), self.encode(self.secret), hashlib.sha512)
            headers = {
                'Content-type': 'application/x-www-form-urlencoded',
                'Key': self.apiKey,
                'Sign': self.decode(signature),
            }
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    async def request(self, path, api='public', method='GET', params={}, headers=None, body=None):
        response = await self.fetch2(path, api, method, params, headers, body)
        if 'success' in response:
            success = self.safe_integer(response, 'success')
            if success == 0:
                message = self.safe_string(response, 'message')
                if message == 'Invalid APIKey':
                    raise AuthenticationError(message)
                raise ExchangeError(message)
        return response
