import yfinance as yf
from yfinance import EquityQuery
import time

from sectors import technology, healthcare, financials, industrial_energy, consumer_retail
from config import *

from utils import get_earnings_history_yf, calculate_eps_growth
from utils import earnings_beat_score
from datetime import date, timedelta

import warnings
warnings.filterwarnings("ignore")
import sys
import os
import contextlib

from utils import calculate_relative_performance_score, get_moving_average_trend_score, calculate_interest_coverage
from config import (
    HIGH_ROIC, MEDIUM_ROIC, 
    MAX_PEG_EXCELLENT, MAX_PEG_ACCEPTABLE, 
    SECTOR_EV_SALES_MEDIANS
)


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

        with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
            earnings = get_earnings_history_yf(ticker)

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        avg_volume = info.get("averageVolume3Month") or info.get("averageVolume")
        dollar_volume = price * avg_volume if price and avg_volume else None

        # --- CALCULATE THE NEW METRICS HERE (Inside the try block, before returning) ---
        sector_name = info.get("sector")
        trend_pts = get_moving_average_trend_score(ticker)
        relative_pts = calculate_relative_performance_score(ticker, sector_name)

        # --- CALCULATE THE NEW METRICS HERE ---
        sector_name = info.get("sector")
        trend_pts = get_moving_average_trend_score(ticker)
        relative_pts = calculate_relative_performance_score(ticker, sector_name)

        roic_val = info.get("returnOnInvestment") or info.get("returnOnAssets")
        interest_coverage_val = calculate_interest_coverage(ticker)

        return {
            "symbol": symbol,
            "sector": sector_name,
            "price": price,
            "avg_volume": avg_volume,
            "dollar_volume": dollar_volume,
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "debt_to_equity": info.get("debtToEquity"),
            "gross_margin": info.get("grossMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "eps_growth": calculate_eps_growth(ticker),
            "peg": info.get("pegRatio"),
            "operating_cf": info.get("operatingCashflow"),
            "free_cf": info.get("freeCashflow"),
            "quarterly_revenue": quarterly_revenue,
            "earnings_history": earnings,
            # Pass them cleanly to the main pipeline
            "trend_score": trend_pts,
            "relative_score": relative_pts,
            "roic": roic_val,
            "ev_to_sales": info.get("enterpriseToRevenue"),
            "interest_coverage": interest_coverage_val
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
        de_ratio = m.get("debt_to_equity")
        
        if de_ratio is not None:
            # If yfinance returns it as a small decimal ratio (like 3.19), 
            # multiply it by 100 to match your config file numbers (like 150)
            if de_ratio < 10:  
                de_ratio = de_ratio * 100
                
            if de_ratio > limit:
                return False
            
        ic_ratio = m.get("interest_coverage")
        if ic_ratio is not None:
            # If they fail to meet the minimum required benchmark floor
            if ic_ratio < MIN_INTEREST_COVERAGE:
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
                "eps_growth": metrics["eps_growth"],
                "earnings_history": metrics["earnings_history"],
                "relative_score": metrics["relative_score"],
                "trend_score": metrics["trend_score"],
                "roic": metrics["roic"],
                "ev_to_sales": metrics["ev_to_sales"],
                "peg": metrics["peg"],
                "interest_coverage": metrics.get("interst_coverage")
            })

        # IMPORTANT: sort per sector
        sector_results.sort(key=lambda x: x["score"], reverse=True)

        # TOP 5 per sector
        top5 = sector_results[:5]

        for s in top5:

            mc = s["market_cap"]
            mc_str = f"${mc/1e9:.2f}B" if mc else "N/A"

            dv = s["dollar_volume"]
            dv_str = f"${dv/1e6:.1f}M" if dv else "N/A"

            rev = s["revenue"]
            rev_str = f"${rev/1e6:.1f}M" if rev else "N/A"

            epsg = s["eps_growth"]
            epsg_str = f"{epsg:.2%}" if epsg is not None else "N/A"

            gm = s["gross_margin"]
            gm_str = f"{gm:.1%}" if gm is not None else "N/A"
            
            de = s["debt_to_equity"]
            de_str = f"{de:.2f}" if de is not None else "N/A"
            
            rev_g = s["revenue_growth"]
            rev_g_str = f"{rev_g:.1%}" if rev_g is not None else "N/A"

            # Parse new financial strings safely
            roic_str = f"{s['roic']:.1%}" if s['roic'] is not None else "N/A"
            evs_str = f"{s['ev_to_sales']:.2f}x" if s['ev_to_sales'] is not None else "N/A"
            peg_str = f"{s['peg']:.2f}" if s['peg'] is not None else "N/A"

            ic = s.get("interest_coverage")
            if ic is not None:
                if ic == float('inf'):
                    ic_str = "Inf (No Debt)"
                else:
                    ic_str = f"{ic:.2f}x"
            else:
                ic_str = "N/A"

            # --- VISUAL PRINTING LAYOUT ---
            print(f"--------------------------------------------------------------------------------")
            print(f"🚀 {s['symbol']:<6} | ✨ Score: {s['score']}/100 | 🏷️  {s['category']}")
            print(f"--------------------------------------------------------------------------------")
            
            # Expanded Indented Metrics Blocks for clean dashboard presentation
            print(f"   [Financials] Cap: {mc_str:<9} | Rev: {rev_str:<10} | Vol ($): {dv_str} | IntCov: {ic_str}")
            print(f"   [Margins]    Gross: {gm_str:<7} | D/E: {de_str:<10} | ROIC: {roic_str}")
            print(f"   [Growth]     Rev Growth: {rev_g_str:<6} | EPS Growth: {epsg_str:<9} | PEG: {peg_str}")
            print(f"   [Valuation]  EV/Sales: {evs_str}")
            
            # ✅ SAFE EARNINGS HISTORY FIX FOR NaTType/NaN VALUES
            print("   [Earnings]   ", end="")
            eh = s.get("earnings_history", [])
            if eh:
                valid_quarters_count = 0
                beats = 0
                for e in eh:
                    surprise_val = e.get("surprise")
                    if surprise_val is not None:
                        try:
                            f_surprise = float(surprise_val)
                            if f_surprise == f_surprise:  # Eliminates math NaN values
                                valid_quarters_count += 1
                                if f_surprise > 0:
                                    beats += 1
                        except (ValueError, TypeError):
                            continue  # Bypasses corrupted pandas types cleanly
                
                if valid_quarters_count > 0:
                    print(f"Beat Record: {beats}/{valid_quarters_count} quarters")
                else:
                    print("Beat Record: N/A")
            else:
                print("Beat Record: N/A")
            
            # --- VISUAL READOUT FOR THE TECHNICALS STRATEGIES ---
            rel_status = "Beats Sector (2/2)" if s["relative_score"] == 10 else ("Beats Period (1/2)" if s["relative_score"] == 5 else "Underperforms")
            trend_status = "Above 50-day MA" if s["trend_score"] == 5 else "Below 50-day MA"
            print(f"   [Technicals] Trend: {trend_status:<16} | Sector Rel: {rel_status}")
            
            # --- SCORE BREAKDOWN SECTION ---
            print("\n   [Score Breakdown]")
            breakdown = s.get("breakdown", {})
            for metric_name, points in breakdown.items():
                print(f"    ▪ {metric_name:<25} : +{points} pts")
                
            print()

if __name__ == "__main__":
    main()