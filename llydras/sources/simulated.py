from datetime import date, timedelta
import pandas as pd
import numpy as np

from .base import StockSource

class BrownianSource(StockSource):
    def __init__(self, mu = 100, sigma = 20):
        self.mu = 100
        self.std = np.sqrt(20)
    def prices(self, tickers: list[str], start: date, end: date, freq: timedelta):
        secs_to_days = 24 * (60 ** 2)

        # Time units in days
        time_lapse = end - start
        total = time_lapse.total_seconds() / secs_to_days

        # dt
        dt = freq.total_seconds() / secs_to_days
        sqrt_dt = np.sqrt(dt)

        # N and L
        N = int(total / dt)
        L = len(tickers)

        Return = np.random.normal(0.5, np.sqrt(0.2), L)
        Volitality = np.random.normal(20, np.sqrt(5), L)
        
        r = Return / N
        sigma = Volitality / N

        # === Geometric Brownian Motion ===
        # X_t = X0 * exp((r - sigma ^ 2 / 2) * t + sigma * W_t)
        Q = r - sigma ** 2 / 2
        W = np.zeros(L)
        X0 = np.random.normal(self.mu, self.std, L) # random initial values vector

        Date = start # current date
        n = 0

        pricesTable = pd.DataFrame(columns = tickers)
        pricesTable.index.name = 'Date'

        while n <= N:
            Date = start + n * freq
            X = X0 * np.exp(Q * n * dt + sigma * W)
            pricesTable.loc[Date] = X
            W += np.random.normal(0, sqrt_dt, L)
            n += 1

        return pricesTable