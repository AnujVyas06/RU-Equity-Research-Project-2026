import yfinance as yf
from yfinance import EquityQuery
import time

from sectors import technology, healthcare, financials, industrial_energy, consumer_retail
from config import *

SECTOR_SCORERS = {
    "Technology": technology.score,
    "Healthcare": healthcare.score,
    "Financial Services": financials.score,
    "Industrials": industrial_energy.score,
    "Energy": industrial_energy.score,
    "Consumer Cyclical": consumer_retail.score,
    "Consumer Defensive": consumer_retail.score,
}


# =====================================================
# SCREENING
# =====================================================

def fetch_candidates(sector):

    query = EquityQuery(
        "and",
        [
            EquityQuery("eq", ["region", "us"]),
            EquityQuery("eq", ["sector", sector]),
            EquityQuery(
                "btwn",
                [
                    "lastclosemarketcap.lasttwelvemonths",
                    MIN_MARKET_CAP,
                    MAX_MARKET_CAP
                ]
            ),
            EquityQuery(
                "gt",
                [
                    "avgdailyvol3m",
                    MIN_AVG_VOLUME
                ]
            )
        ]
    )

    tickers = []
    offset = 0

    while True:
        result = yf.screen(
            query=query,
            offset=offset,
            size=FETCH_BATCH_SIZE
        )

        quotes = result.get("quotes", [])
        if not quotes:
            break

        tickers.extend(q["symbol"] for q in quotes)
        offset += FETCH_BATCH_SIZE

    return list(set(tickers))


# =====================================================
# METRICS
# =====================================================

def get_metrics(symbol):

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        quarterly_revenue = None

        try:
            q_fin = ticker.quarterly_financials

            if q_fin is not None and not q_fin.empty:
                if "Total Revenue" in q_fin.index:
                    quarterly_revenue = (
                        q_fin.loc["Total Revenue"]
                        .dropna()
                        .tolist()
                    )[::-1]

        except Exception:
            pass

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        avg_volume = info.get("averageVolume3Month") or info.get("averageVolume")

        dollar_volume = price * avg_volume if price and avg_volume else None

        return {
            "symbol": symbol,
            "sector": info.get("sector"),
            "price": price,
            "avg_volume": avg_volume,
            "dollar_volume": dollar_volume,
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "debt_to_equity": info.get("debtToEquity"),
            "gross_margin": info.get("grossMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "peg": info.get("pegRatio"),
            "operating_cf": info.get("operatingCashflow"),
            "free_cf": info.get("freeCashflow"),
            "quarterly_revenue": quarterly_revenue
        }

    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None


# =====================================================
# FILTERS
# =====================================================

def passes_hard_filters(m):

    if m is None:
        return False

    if m["market_cap"] is not None:
        if m["market_cap"] < MIN_MARKET_CAP or m["market_cap"] > MAX_MARKET_CAP:
            return False

    if m["dollar_volume"] is not None:
        if m["dollar_volume"] < MIN_DOLLAR_VOLUME:
            return False

    if m["revenue"] is not None:
        if m["revenue"] < MIN_REVENUE:
            return False

    if m["revenue_growth"] is not None:
        if m["revenue_growth"] < MIN_REVENUE_GROWTH:
            return False

    sector = m.get("sector")

    if sector != "Financial Services":
        limit = DEBT_TO_EQUITY_LIMITS.get(sector, 300)
        if m.get("debt_to_equity") is not None:
            if m["debt_to_equity"] > limit:
                return False

    return True


# =====================================================
# LABELS
# =====================================================

def category(score):
    if score >= 90:
        return "Exceptional Growth Company"
    elif score >= 75:
        return "Strong Growth Candidate"
    elif score >= 60:
        return "Needs Review"
    return "Not Growth Candidate"


# =====================================================
# MAIN
# =====================================================

def main():

    print("\nTOP STOCKS BY SECTOR\n")

    for sector in SECTORS:

        print(f"\n===== {sector} =====")

        scorer = SECTOR_SCORERS.get(sector)
        if scorer is None:
            continue

        tickers = fetch_candidates(sector)
        print(f"Found {len(tickers)} candidates")

        sector_results = []

        for ticker in tickers:

            time.sleep(0.5)

            metrics = get_metrics(ticker)
            if not passes_hard_filters(metrics):
                continue

            score, breakdown = scorer(metrics)

            sector_results.append({
                "symbol": ticker,
                "sector": sector,
                "score": score,
                "category": category(score),
                "breakdown": breakdown,
                "market_cap": metrics["market_cap"],
                "price": metrics["price"],
                "dollar_volume": metrics["dollar_volume"],
                "revenue": metrics["revenue"],
                "debt_to_equity": metrics["debt_to_equity"],
                "gross_margin": metrics["gross_margin"],
                "revenue_growth": metrics["revenue_growth"],
            })

        # IMPORTANT: sort per sector
        sector_results.sort(key=lambda x: x["score"], reverse=True)

        # TOP 5 per sector
        top5 = sector_results[:5]

        for s in top5:

            print(
                f"{s['symbol']:6}"
                f"| Score {s['score']}/100"
                f"| {s['category']}"
            )

            print(
                f"MC: ${s['market_cap']/1e9:.2f}B | "
                f"Dollar Vol: ${s['dollar_volume']/1e6:.1f}M | "
                f"Revenue: ${s['revenue']/1e6:.1f}M | "
                f"D/E: {s['debt_to_equity']} | "
                f"Gross Margin: {s['gross_margin']} | "
                f"Revenue Growth: {s['revenue_growth']}"
            )

            print(s["breakdown"])
            print()


if __name__ == "__main__":
    main()