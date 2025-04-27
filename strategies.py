import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

from PortfolioManager import Portfolio


def mean_reversion_strat(ticker, portfolio: Portfolio):
    data = yf.download(ticker, start="1900-01-01")

    # 200-day moving average
    data['MA_200'] = data['Close'].rolling(window=200).mean()

    # Bollinger Bands (20-day moving average ±2 std dev)
    window = 100
    std = data['Close'].rolling(window=window).std()
    ma = data['Close'].rolling(window=window).mean()

    z_score = 3

    data['MA_20'] = ma
    data['BB_upper'] = ma + z_score * std
    data['BB_lower'] = ma - z_score * std

    data['pnl'] = 0

    # General strategy, if price goes below lower band, go long and close all short positions
    # If price goes above upper band, short and close all long positions

    # Assuming amount invested each time is the same

    long_positions = []

    row_index = 0

    for index, row in data.iterrows():
        close_price = row['Close'][ticker]
        bb_lower = row['BB_upper'][""]
        bb_upper = row['BB_lower'][""]
        # print(close_price, bb_upper)  # Access columns in each row
        if row_index > window:
            row_profit = 0
            if close_price < bb_lower:
                # Open a long
                portfolio.buy(ticker, 10)
            if close_price > bb_upper:
                for pos in long_positions:
                    profit = (close_price - pos) / pos
                    row_profit += profit
                    # TODO update param to use 'todays' date
                    portfolio.sell(portfolio.pvalue(ticker, "today"))

        row_index += 1

    return portfolio
