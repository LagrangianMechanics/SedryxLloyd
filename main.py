from PortfolioManager import Portfolio
from strategies import mean_reversion_strat

# Download data
tickers = ["GOLD", "QQQ", "AAPL", "DJI", "CHP", ]
currencies = [
    "GBPUSD=X", "GBPEUR=X", "EURUSD=X", "GBPJPY=X", "JPY=X", "GBP=X", "GBPAUD=X",
    "GBPBRL=X", "GBPCAD=X", "GBPCHF=X", "GBPCNY=X", "GBPINR=X", "GBPNOK=X", "GBPQAR=X",
    "GBPZAR=X", "EURCHF=X", "EURCAD=X", "EURJPY=X", "EURSEK=X", "EURHUF=X", "CAD=X",
    "USDHKD=X", "USDSGD=X", "INR=X", "USDMXN=X", "CNY=X", "CHF=X"
]

portfolio = Portfolio(currencies)

portfolio.deposit(1000)

portfolio = mean_reversion_strat("GBPQAR=X", portfolio)

print(portfolio.areturns())
