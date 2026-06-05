import yfinance as yf
from yfinance import EquityQuery

SECTOR = "Technology"


def test_pagination():
    query = EquityQuery(
        "and",
        [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("eq", ["sector", SECTOR]),
            EquityQuery("gt", ["avgdailyvol3m", 100000]),
        ],
    )

    page0 = yf.screen(query=query, offset=0, size=50)
    page1 = yf.screen(query=query, offset=50, size=50)

    tickers0 = [q["symbol"] for q in page0["quotes"]]
    tickers1 = [q["symbol"] for q in page1["quotes"]]

    overlap = set(tickers0) & set(tickers1)

    print("\nTEST 1 - Pagination")
    print("Overlap:", overlap)

    if overlap:
        print("FAIL")
    else:
        print("PASS")


def test_revenue():
    info = yf.Ticker("AAPL").info

    print("\nTEST 2 - Revenue")
    print(info.get("totalRevenue"))


def test_de():
    info = yf.Ticker("AAPL").info

    print("\nTEST 3 - Debt To Equity")
    print(info.get("debtToEquity"))


def test_roe():
    info = yf.Ticker("AAPL").info

    print("\nTEST 4 - ROE")
    print(info.get("returnOnEquity"))


def test_smallcap():
    info = yf.Ticker("AVAV").info

    fields = [
        "totalRevenue",
        "debtToEquity",
        "returnOnEquity",
        "returnOnAssets",
        "pegRatio",
        "grossMargins",
        "revenueGrowth",
        "operatingCashflow",
        "freeCashflow",
    ]

    print("\nTEST 5 - Small Cap")

    for field in fields:
        print(field, "=", info.get(field))


def test_financials():
    info = yf.Ticker("JPM").info

    print("\nTEST 6 - Financials")

    print("Debt To Equity:", info.get("debtToEquity"))
    print("ROE:", info.get("returnOnEquity"))
    print("ROA:", info.get("returnOnAssets"))
    print("Revenue:", info.get("totalRevenue"))


if __name__ == "__main__":
    test_pagination()
    test_revenue()
    test_de()
    test_roe()
    test_smallcap()
    test_financials()