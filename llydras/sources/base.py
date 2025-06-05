# base.py

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

DAILY = timedelta(days = 1)

@dataclass
class Source:
	def prices(self, tickers: list[str], start: date, end: date, freq: timedelta = DAILY):
		return None

@dataclass
class StockSource(Source):
	def dividend(self, tickers: list[str], start: date, end: date, freq: timedelta = DAILY):
		return None