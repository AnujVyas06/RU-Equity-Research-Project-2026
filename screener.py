import yfinance as yf
from yfinance import EquityQuery
import time

from config import *

#First Screener
def fetch_candidates(sector):
    query = EquityQuery(
        "and",
        [
            #Screens Based On Sector From Config
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("eq", ["sector", sector]),
            EquityQuery(
                #Filters Stocks Between Our Hard Min & Max MC Filters (in config)
                "btwn",
                [
                    "intradaymarketcap",
                    MIN_MARKET_CAP,
                    MAX_MARKET_CAP,
                ],
            ),
            EquityQuery(
                "gt",
                #Filters Stocks Greater Than Preset Volume (in config)
                [
                    "avgdailyvol3m",
                    MIN_AVG_VOLUME,
                ],
            ),
        ],
    )

    #Puts First Filtered Stocks Into Tickers
    #Offset Tells Yahoo Finance to Start At Beginning Of The List
    tickers = []
    offset = 0

    #Loop Runs Till We Tell It To Break
    while True:
        result = yf.screen(
            query=query,
            offset=offset,
            size=FETCH_BATCH_SIZE,
        )

        #Quotes Gets the Symbol
        quotes = result["quotes"]

        #Break When No More Stocks
        if not quotes:
            break

        tickers.extend(q["symbol"] for q in quotes)
        #Gets 250 Stocks Then the Next 250 (prevents from errors)
        offset += FETCH_BATCH_SIZE

    return sorted(set(tickers))

#Gets Our Specific Requirements
def get_metrics(symbol):
    try:
        info = yf.Ticker(symbol).info

        return {
            "symbol": symbol,
            "sector": info.get("sector"),
            "revenue": info.get("totalRevenue"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "gross_margin": info.get("grossMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "peg": info.get("pegRatio"),
            "operating_cf": info.get("operatingCashflow"),
            "free_cf": info.get("freeCashflow"),
        }

    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None

#Checks For Hard Filters
def passes_hard_filters(metrics):
    if metrics is None:
        return False

    #Revenue
    revenue = metrics.get("revenue")
    if revenue is None or revenue < MIN_REVENUE:
        return False

    sector = metrics.get("sector")

    # only enforce debt filter outside financials
    if sector != "Financial Services":
        de = metrics.get("debt_to_equity")
        if de is None or de > MAX_DEBT_TO_EQUITY:
            return False

    return True


def score_stock(metrics):
    breakdown = {}

    breakdown["roe"] = (
        metrics["roe"] is not None and metrics["roe"] > MIN_ROE
    )

    breakdown["roa"] = (
        metrics["roa"] is not None and metrics["roa"] > MIN_ROA
    )

    breakdown["margin"] = (
        metrics["gross_margin"] is not None
        and metrics["gross_margin"] > MIN_GROSS_MARGIN
    )

    breakdown["growth"] = (
        metrics["revenue_growth"] is not None
        and metrics["revenue_growth"] > 0
    )

    breakdown["fcf"] = (
        metrics["free_cf"] is not None
        and metrics["free_cf"] > 0
    )

    breakdown["peg"] = (
        metrics["peg"] is not None
        and metrics["peg"] < MAX_PEG
    )

    score = sum(breakdown.values())

    return score, breakdown

#Prints Stocks
def main():
    results = []

    for sector in SECTORS:
        print(f"\nScanning {sector}...")

        tickers = fetch_candidates(sector)

        print(f"Found {len(tickers)} candidates")

        for ticker in tickers:
            time.sleep(0.5)

            metrics = get_metrics(ticker)
            if not passes_hard_filters(metrics):
                continue

            score, breakdown = score_stock(metrics)

            results.append({
                "symbol": ticker,
                "sector": sector,
                "score": score,
                "breakdown": breakdown,
                "roe": metrics["roe"],
                "revenue": metrics["revenue"],
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    from collections import defaultdict

    sector_stocks = defaultdict(list)

    # Group stocks by sector
    for stock in results:
        sector_stocks[stock["sector"]].append(stock)

    print("\nTOP 5 STOCKS BY SECTOR\n")

    for sector in SECTORS:
        print(f"\n=== {sector} ===")

        for stock in sector_stocks[sector][:5]:
            b = stock["breakdown"]

            print(
                f"{stock['symbol']:6} | "
                f"Score: {stock['score']} | "
                f"ROE:{int(b['roe'])} "
                f"ROA:{int(b['roa'])} "
                f"M:{int(b['margin'])} "
                f"G:{int(b['growth'])} "
                f"FCF:{int(b['fcf'])} "
                f"PEG:{int(b['peg'])}"
            )

if __name__ == "__main__":
    main()