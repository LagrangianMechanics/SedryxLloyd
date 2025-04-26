import yfinance as yf

def yfinanceSource(start, end, tickers, freq):
	return yf.download(' '.join(tickers), start = start, end = end, interval = freq)