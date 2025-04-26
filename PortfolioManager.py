from yfinanceSource import yfinanceSource
import pandas as pd

class PortfolioError(Exception):
	pass

class InsufficientFundsError(PortfolioError):
	pass

class ShortSellingError(PortfolioError):
	pass

class Portfolio:
	def __init__(self, assets: tuple[str], source = None):
		self.balance = 0
		self.holdings = {a : 0 for a in assets}
		self.assets = set(assets)

		self.source = source or yfinanceSource

		self._adate_range = None
		self._udate_range = None
		self._pdate_range = None
		self._date = None
		
		self.asset_prices = None
	def deposit(self, amount: float):
		if amount < 0:
			raise ValueError('Deposits must be positive.')
		self.balance += amount
	def withdraw(self, amount: float):
		if amount < 0:
			raise ValueError('Withdrawals must be positive.')
		if amount > self.balance:
			raise InsufficientFundsError('Insufficient funds for withdrawal.')
		self.balance -= amount
	def buy(self, asset: str, amount: float):
		if asset not in self.assets:
			raise ValueError(f'Asset \'{asset}\' not in portfolio. Please add it first using the \'add_asset()\' method.')
		if amount < 0:
			raise ValueError('Amount to buy must be positive.')
		if amount > self.balance:
			raise InsufficientFundsError('Insufficient funds for purchase.')
		self.balance -= amount
		
		price = self.get(asset, self.date)
		shares = amount / price
		self.holdings[asset] += shares
	def sell(self, asset: str, amount: float):
		if asset not in self.assets:
			raise ValueError(f'Asset \'{asset}\' not in portfolio. Please add it first using the \'add_asset()\' method.')
		if amount < 0:
			raise ValueError('Amount to sell must be positive.')

		price = self.get(asset, self.date)
		shares = amount / price
		holding = self.holdings[asset]

		if holding < shares:
			raise ShortSellingError(f'Cannot sell {amount} of {asset}. The portfolio currently holds {holding}. Short selling is not permitted. To change this, use the \'short_selling()\' method.')
		
		self.balance += amount
		self.holdings[asset] -= shares
	def load_prices(self, start: str, end: str, freq: str = 'D'):
		start_date = pd.to_datetime(start)
		end_date = pd.to_datetime(end)

		if start_date > end_date:
			raise ValueError("Invalid date range — the start date must come before the end date.")

		index = pd.date_range(start, end, freq)
		self.asset_prices = self.source(start_date, end_date, freq)
		self.asset_prices.index = index

		self.start_date = start_date
		self.end_date = end_date
	def trade(self, start = None, end = None, freq = 'D'):
		if start < self.start_date or self.end_date < end:
			self.load_prices(start, end, freq = freq)

		for date, prices in self.asset_prices.loc[start : end]:
			self.date = date
			yield date, prices

		self.date = None

	def _retrive_from_range(self, data, date, freq = None):
		match date:
			case None:
				pass
			case time:
				data = data.loc[time]
			case (None, end):
				data = data.loc[self.start_date : end]
			case (start, None):
				data = data.loc[start : self.end_date]
			case (start, end):
				data = data.loc[start : end]
			case _:
				raise ValueError
	def 
	def avalue(self, asset = None, date = None, freq = None):
		match asset:
			pass
	def areturns(self, asset = None, date = None, freq = None):
		pass
	def alogreturns(self, asset = None, date = None, freq = None):
		pass
	def pvalue(self, date, freq = None):
		pass
	def preturns(self, date, freq = None):
		pass
	def plogreturns(self, date, freq = None):
		pass