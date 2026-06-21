import yfinance as yf

ticker = yf.Ticker("AAPL")
print(ticker.earnings_dates)