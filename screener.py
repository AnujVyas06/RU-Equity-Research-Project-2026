import yfinance as yf
from yfinance import EquityQuery
import time

from config import *


def fetch_candidates(sector):
    query = EquityQuery(
        "and",
        [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("eq", ["sector", sector]),
            EquityQuery(
                "btwn",
                [
                    "intradaymarketcap",
                    MIN_MARKET_CAP,
                    MAX_MARKET_CAP,
                ],
            ),
            EquityQuery(
                "gt",
                [
                    "avgdailyvol3m",
                    MIN_AVG_VOLUME,
                ],
            ),
        ],
    )

    tickers = []
    offset = 0

    while True:
        result = yf.screen(
            query=query,
            offset=offset,
            size=FETCH_BATCH_SIZE,
        )

        quotes = result["quotes"]

        if not quotes:
            break

        tickers.extend(q["symbol"] for q in quotes)

        offset += FETCH_BATCH_SIZE

    return sorted(set(tickers))


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


def passes_hard_filters(metrics):
    if metrics is None:
        return False

    revenue = metrics["revenue"]

    if revenue is None:
        return False

    if revenue < MIN_REVENUE:
        return False

    sector = metrics["sector"]

    if sector != "Financial Services":
        de = metrics["debt_to_equity"]

        if de is None:
            return False

        if de > MAX_DEBT_TO_EQUITY:
            return False

    return True


def score_stock(metrics):
    score = 0

    if metrics["roe"] is not None and metrics["roe"] > MIN_ROE:
        score += 1

    if metrics["roa"] is not None and metrics["roa"] > MIN_ROA:
        score += 1

    if (
        metrics["gross_margin"] is not None
        and metrics["gross_margin"] > MIN_GROSS_MARGIN
    ):
        score += 1

    if (
        metrics["revenue_growth"] is not None
        and metrics["revenue_growth"] > 0
    ):
        score += 1

    if (
        metrics["free_cf"] is not None
        and metrics["free_cf"] > 0
    ):
        score += 1

    if (
        metrics["peg"] is not None
        and metrics["peg"] < MAX_PEG
    ):
        score += 1

    return score


def main():
    results = []

    for sector in SECTORS:
        print(f"Scanning {sector}...")

        tickers = fetch_candidates(sector)

        print(f"Found {len(tickers)} candidates")

        for ticker in tickers:
            time.sleep(0.5)
            metrics = get_metrics(ticker)

            if not passes_hard_filters(metrics):
                continue

            score = score_stock(metrics)

            results.append(
                {
                    "symbol": ticker,
                    "sector": sector,
                    "score": score,
                    "roe": metrics["roe"],
                    "revenue": metrics["revenue"],
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)

    print("\nTOP 25 STOCKS\n")

    for stock in results[:25]:
        print(
            f"{stock['symbol']:6} | "
            f"{stock['sector'][:20]:20} | "
            f"Score: {stock['score']}"
        )


if __name__ == "__main__":
    main()