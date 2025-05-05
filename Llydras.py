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
    def __init__(self, portfolio, methods = None):
        self.portfolio = portfolio

        self.methods = methods or [Stats.avalue]
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
        self.portfolio.holdings.loc[tStart] = [self.portfolio.cash] + [0] * len(self.portfolio.assets)
        self.portfolio.portfolio_performance.loc[tStart] = [0] * len(self.portfolio.assets)
        u = Stream(self.portfolio.portfolio_performance, True)
        print(self.portfolio.holdings)
        for date in prices.index:
            self.portfolio.holdings.loc[date] = self.portfolio.holdings.loc[pre]
            print('Try', self.portfolio.holdings.loc[date, self.portfolio.assets[0] :] )
            
            self.portfolio.portfolio_performance.loc[date] = self.portfolio.holdings.loc[date, self.portfolio.assets[0] :] * self.portfolio.asset_prices.loc[date]
            u.next()
            
            self.portfolio._date = date
            
            yield date, stream, u
            stream.next()
            pre = date

        self.portfolio._date = None

class Portfolio:
    '''
    A financial portfolio tracking time-evolving holdings, cash, trades, and performance.

    The Portfolio class manages asset holdings, cash balance, portfolio valuation, 
    and trade execution. It also provides an intuitive `trade()` method that 
    allows strategy logic to be written inside a `for` loop.
    '''
    def __init__(self, assets: List[Str, ...], source: Tuple[RawDate, RawDate, Tuple[Str, ...], Str] >> Table = None):
        self.cash: Float = 0
        self.assets: Tuple[Str, ...] = tuple(assets)

        # Asset data sources
        self.source = source or yfinanceSource

        # Date ranges
        self._adate_range: Maybe[DateRange] = None
        self._tdate_range: Maybe[DateRange] = None
        self._pdate_range: Maybe[DateRange] = None
        self._date: Maybe[RawDate] = None  # When not None, indicates an active trading session.
                                   # Represents the current date of the session in progress.
                                   # This is the primary flag for session state.

        # Tables
        self.holdings: Table = pd.DataFrame(columns=('Cash', *self.assets))  
        # Number of units(shares) held at each time step, including cash.

        self.asset_prices: Maybe[Table] = None  
        # Asset prices indexed by time. Must align with holdings for performance computation.

        self.portfolio_performance: Maybe[Table] = pd.DataFrame(columns=self.assets)  
        # Monetary value of assets (excluding cash) in the portfolio at each time step.

        #Namespaces
        self.stats = Stats(self)
        #Statistical methods and indicators related to portfolio performance.

        #Other
        self.trade = Trade(self)

    # Priviate Methods
    def _update_cash(self, delta: Float):
        '''
        Update the cash balance by `delta`. If a trading session is active the
        holdings table is also updated.
        '''
        self.cash += delta

        if self._date != None:
            #If in the middle of a trading session update the holdings table
            self.holdings.loc[self._date, 'Cash'] += delta
    def _update_holdings(self, asset: Str, delta_shares: Float):
        '''
        Update the holdings and performance tables for a given asset at the current date.

        Notes
        -----
        Assumes an active trading session (self._date is not None).
        No input validation is performed. Use with caution.
        '''
        self.holdings.loc[self._date, asset] += delta_shares
        self.portfolio_performance.loc[self._date, asset] = self.holdings.loc[self._date, asset] * self.asset_prices.loc[self._date, asset]
    
    # Public Methods
    def load_prices(self, start: Date, end: Date, freq: Str = 'D'):
        '''
        Preload asset price data into the portfolio.

        Parameters
        ----------
        start : Date
            The start date for the data request.
        end : Date
            The end date for the data request.
        freq : str, default 'D'
            Data frequency (e.g. 'D' for daily, 'H' for hourly).

        Raises
        ------
        PortfolioError
            If called during an active trading session.
        ValueError
            If `start` is after `end`.
        '''

        if self._date != None:
            raise PortfolioError('Cannot load new price data during an active trading session.')

        start_date = pd.to_datetime(start)
        end_date = pd.to_datetime(end)

        if start_date > end_date:
            raise ValueError("Invalid date range — the start date must come before the end date.")

        # Fetch price data from the configured source
        self.asset_prices = self.source(start_date, end_date, self.assets, freq)

        # Cache the actual date range returned.
        dates = self.asset_prices.index
        self._adate_range = (dates[0], datas[-1])
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

class Stats:
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio
    def add(func):
        ak = lambda f: lambda self, *args, **kwargs: self._asset_func(self, f, *args, **kwargs)
        pk = lambda f: lambda self, *args, **kwargs: self._portfolio_func(self, f, *args, **kwargs)
        
        setattr(Stats, f'a{func.__name__}', ak(func))
        setattr(Stats, f'p{func.__name__}', pk(func))
        
        return func
    def append(func):
        g = lambda f: lambda self, *args, **kwargs: f(self.portfolio, *args, **kwargs)
        setattr(Stats, func.__name__, g(func))
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

@Stats.append
def weights(p):
    v = p.stats.pvalue()
    return v
