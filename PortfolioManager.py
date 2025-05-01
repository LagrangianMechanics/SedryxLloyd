from yfinanceSource import yfinanceSource
from haspyT import *
import pandas as pd
import numpy as np

#–––––Types–––––
#Dates
RawDate = Type(pd.Timestamp)
Date = RawDate | Str
DateRange = Tuple[RawDate, RawDate]

#Table
Table = Type(pd.DataFrame)


#–––––Errors–––––
class PortfolioError(Exception):
    pass

class InsufficientFundsError(PortfolioError):
    pass

class ShortSellingError(PortfolioError):
    pass

#–––––Stream–––––
class Stream:
    def __init__(self, data: Table, live = False):
        self.data = data
        self.live = live
        self.index = 0 if not self.live else -1
        
        self.start_index = self.data.index[0]
        now_index = self.start_index
        present_index = now_index if not self.live else (self.data.index[self.index - 1] if self.index > 0 else self.data.index[0])

        self.now = self.data.loc[now_index]
        self.history = self.data.loc[self.start_index : present_index]
    def next(self):
        self.index += 1
        self.index %= len(self.data.index)
        
        now_index = self.data.index[self.index]
        self.now = self.data.loc[now_index]
        present_index = now_index if not self.live else (self.data.index[self.index - 1] if self.index > 0 else self.data.index[0])
        
        self.history = self.data.loc[self.start_index : present_index]

def date_input(date, default: Maybe[DateRange] = None):
    start, end = default or (None, None)
    
    match date:
        case () | (None, ) | (None, None):
            return (start, end)
        case (pd.Timestamp(), ):
            return date
        case (str() as s, ):
            return (pd.to_datetime(s), )
        case (str() | pd.Timestamp() as x, int() as days):
            x = pd.to_datetime(x)
            x, y = sorted((x, x + pd.Timedelta(days = days)))
            return (x, y)
        case (str() | pd.Timestamp() as x, None):
            x = pd.to_datetime(x)
            return (x, end)
        case (None, str() | pd.Timestamp() as y):
            y = pd.to_datetime(y)
            return (start, y)
        case (str() | pd.Timestamp() as x, str() | pd.Timestamp() as y):
            x, y = pd.to_datetime(x), pd.to_datetime(y)
            if x > y:
                raise ValueError("Invalid date range — the start date must come before the end date.") 
            return (x, y)

class Trade:
    def __init__(self, portfolio):
        self.portfolio = portfolio
    def __call__(self, *date, freq = 'D'):
        date = date_input(date, default = self.portfolio._adate_range)
        
        if None in date:
            raise ValueError('Invalid date range selected.')

        start, end = date
        
        if self.portfolio._adate_range == None:
            self.portfolio.load_prices(start, end)
        
        astart, aend = self.portfolio._adate_range

        if start < astart or end > aend:
            start = min(start, astart)
            end = max(end, aend)
            self.portfolio.load_prices(start, end)

        prices = self.portfolio.asset_prices.loc[start : end]
        stream = Stream(prices)
        tStart, tEnd = prices.index[0], prices.index[-1]
        pre = tStart
        self.portfolio.holdings.loc[tStart] = [0] * len(self.portfolio.assets)
        self.portfolio.portfolio_performance.loc[tStart] = [0] * len(self.portfolio.assets)
        u = Stream(self.portfolio.portfolio_performance, True)
        for date in prices.index:
            self.portfolio.holdings.loc[date] = self.portfolio.holdings.loc[pre]
            
            self.portfolio.portfolio_performance.loc[date] = self.portfolio.holdings.loc[date] * self.portfolio.asset_prices.loc[date]
            u.next()
            
            self.portfolio._date = date
            
            yield date, stream, u
            stream.next()
            pre = date

        self.portfolio._date = None

class Portfolio:
    def __init__(self, assets: List[Str, ...], source = None):
        self.cash: Float = 0
        self.assets: Tuple[Str, ...] = tuple(assets)

        self.source: Tuple[RawDate, RawDate, Tuple[Str, ...], Str] >> Table = source or yfinanceSource

        self._adate_range: Maybe[DateRange] = None
        self._tdate_range: Maybe[DateRange] = None
        self._pdate_range: Maybe[DateRange] = None
        self._date: Maybe[RawDate] = None

        self.holdings: Table = pd.DataFrame(columns = self.assets)
        self.asset_prices: Maybe[Table] = None
        self.portfolio_performance: Maybe[Table] = pd.DataFrame(columns = self.assets)

        self.stats = Stats(self)
        self.trade = Trade(self)
    def deposit(self, amount: Float):
        if amount < 0:
            raise ValueError('Deposits must be positive.')
        self._update_cash(amount)
    def withdraw(self, amount: Float):
        if amount < 0:
            raise ValueError('Withdrawals must be positive.')
        if amount > self.cash:
            raise InsufficientFundsError('Insufficient funds for withdrawal.')
        self._update_cash(-amount)
    def _update_cash(self, delta: Float):
        self.cash += delta
    def _update_holdings(self, asset: Str, delta_shares: Float):
        self.holdings.loc[self._date, asset] += delta_shares
        self.portfolio_performance.loc[self._date, asset] = self.holdings.loc[self._date, asset] * self.asset_prices.loc[self._date, asset]
    def buy(self, asset: Str, amount: Float):
        if asset not in self.assets:
            raise ValueError(f'Asset \'{asset}\' not in portfolio. Please add it first using the \'add_asset()\' method.')
        if amount < 0:
            raise ValueError('Amount to buy must be positive.')
        if amount > self.cash:
            raise InsufficientFundsError('Insufficient funds for purchase.')
        
        price = self.asset_prices.loc[self._date, asset]
        shares = amount / price

        self._update_cash(-amount)
        self._update_holdings(asset, shares)
    def sell(self, asset: Str, amount: Float):
        if asset not in self.assets:
            raise ValueError(f'Asset \'{asset}\' not in portfolio. Please add it first using the \'add_asset()\' method.')
        if amount < 0:
            raise ValueError('Amount to sell must be positive.')

        price = self.asset_prices.loc[self._date, asset]
        shares = amount / price
        holding = self.holdings.loc[self._date, asset]

        if holding < shares:
            raise ShortSellingError(f'Cannot sell {amount} of {asset}. The portfolio currently holds {holding}. Short selling is not permitted. To change this, use the \'short_selling()\' method.')

        self._update_cash(amount)
        self._update_holdings(asset, -shares)
    def load_prices(self, start: Date, end: Date, freq: str = 'D'):
        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)

        if start_date > end_date:
            raise ValueError("Invalid date range — the start date must come before the end date.")

        self.asset_prices = self.source(start_date, end_date, self.assets, freq)

        self._adate_range = (start_date, end_date)

class Stats:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def add(func):
        ak = lambda f: lambda self, *args, **kwargs: self._asset_func(self, f, *args, **kwargs)
        pk = lambda f: lambda self, *args, **kwargs: self._portfolio_func(self, f, *args, **kwargs)
        
        setattr(Stats, f'a{func.__name__}', ak(func))
        setattr(Stats, f'p{func.__name__}', pk(func))
        
        return func
    
    @staticmethod
    def _asset_func(self, func, *args, **kwargs):
        if self.portfolio._date == None:
            print('Not Trading!')
            data = func(self.portfolio.asset_prices, *args, **kwargs)
            return data
        else:
            print('Trading!')
            data = func(self.portfolio.asset_prices, *args, **kwargs)
            return Stream(data)
    
    @staticmethod
    def _portfolio_func(self, func, *args, **kwargs):
        if self.portfolio._date == None:
            print('Not Trading!')
            data = func(self.portfolio.portfolio_performance, *args, **kwargs)
            return data
        else:
            print('Trading!')
            data = func(self.portfolio.portfolio_performance, *args, **kwargs)
            return Stream(data, live = True)

@Stats.add
def value(table):
    return table

@Stats.add
def returns(table):
    return table / table.shift(1) - 1

@Stats.add
def mean(table):
    return table.mean()

@Stats.add
def logreturns(table):
    return np.log(table) - np.log(table.shift(1))
