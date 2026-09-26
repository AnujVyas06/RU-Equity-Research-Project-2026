import yfinance as yf
from yfinance import EquityQuery
import time
import pandas as pd
import warnings
import sys
import os
import contextlib
from datetime import date, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import custom modules & configs
import healthcare
from config import *
from utils import (
    get_earnings_history_yf, 
    calculate_eps_growth, 
    earnings_beat_score,
    calculate_relative_performance_score, 
    get_moving_average_trend_score, 
    calculate_interest_coverage
)

warnings.filterwarnings("ignore")

SECTOR_SCORERS = {
    "Healthcare": healthcare.score,
}


# =====================================================
# SAFE EXTRACTION HELPERS FOR HEALTHCARE
# =====================================================

def extract_financial_row(df, row_keys):
    """Safely extracts the most recent row matching any alias in row_keys from a dataframe."""
    if df is None or df.empty:
        return None
    for key in row_keys:
        if key in df.index:
            series = df.loc[key].dropna()
            if not series.empty:
                return series
    return None


def get_healthcare_metrics(ticker, info, quarterly_revenue):
    """
    Extracts Healthcare-specific metrics safely handling yfinance version variations.
    """
    metrics = {
        "rd_intensity": None,
        "cash_runway_quarters": None,
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),
        "dso": None,
        "sga_trend": None
    }
    
    try:
        q_fin = ticker.quarterly_financials
        q_cashflow = ticker.quarterly_cashflow
        balance_sheet = ticker.balance_sheet
        
        # --- 1. R&D Intensity ---
        rd_row = extract_financial_row(q_fin, [
            "Research Development", 
            "Research And Development", 
            "Research and Development"
        ])
        if rd_row is not None and quarterly_revenue and quarterly_revenue[-1] > 0:
            latest_rd = rd_row.iloc[0]
            if pd.notna(latest_rd):
                metrics["rd_intensity"] = latest_rd / quarterly_revenue[-1]

        # --- 2. Cash Runway (Quarters) ---
        cash = info.get("totalCash")
        if cash is None and balance_sheet is not None and not balance_sheet.empty:
            cash_row = extract_financial_row(balance_sheet, [
                "Cash And Cash Equivalents", 
                "Cash Financial", 
                "Cash Cash Equivalents And Short Term Investments"
            ])
            if cash_row is not None and len(cash_row) > 0:
                cash = cash_row.iloc[0]

        ocf_row = extract_financial_row(q_cashflow, [
            "Operating Cash Flow", 
            "Cash Flow From Continuing Operating Activities"
        ])
        if ocf_row is not None and len(ocf_row) > 0:
            quarterly_ocf = ocf_row.iloc[0]
            if pd.notna(quarterly_ocf) and cash is not None:
                if quarterly_ocf >= 0:
                    metrics["cash_runway_quarters"] = float("inf")
                else:
                    burn_rate = abs(quarterly_ocf)
                    metrics["cash_runway_quarters"] = cash / burn_rate

        # --- 3. Days Sales Outstanding (DSO) ---
        rec_row = extract_financial_row(balance_sheet, [
            "Net Receivables", 
            "Accounts Receivable", 
            "Receivables"
        ])
        if rec_row is not None and quarterly_revenue and quarterly_revenue[-1] > 0:
            receivables = rec_row.iloc[0]
            if pd.notna(receivables):
                metrics["dso"] = (receivables / quarterly_revenue[-1]) * 91.25

        # --- 4. SG&A Trend (Scaling Efficiency Inflection) ---
        sga_row = extract_financial_row(q_fin, [
            "Selling General Administrative", 
            "Selling General And Administration", 
            "Selling General and Administrative Header"
        ])
        rev_row = extract_financial_row(q_fin, ["Total Revenue"])
        
        if sga_row is not None and rev_row is not None:
            combined = pd.DataFrame({"sga": sga_row, "rev": rev_row}).dropna()
            if len(combined) >= 2:
                combined = combined.iloc[::-1]  # Oldest to newest
                sga_ratios = combined["sga"] / combined["rev"]
                metrics["sga_trend"] = sga_ratios.iloc[-1] - sga_ratios.iloc[0]

    except Exception:
        pass  # Fail gracefully with default Nones

    return metrics


# =====================================================
# SCREENING
# =====================================================

def fetch_candidates(sector="Healthcare"):

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

        sector_name = info.get("sector") or "Healthcare"
        trend_pts = get_moving_average_trend_score(ticker)
        relative_pts = calculate_relative_performance_score(ticker, sector_name)

        roic_val = info.get("returnOnInvestment") or info.get("returnOnAssets")
        interest_coverage_val = calculate_interest_coverage(ticker)

        # Pull new Healthcare-specific metrics
        hc_metrics = get_healthcare_metrics(ticker, info, quarterly_revenue)

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
            "trend_score": trend_pts,
            "relative_score": relative_pts,
            "roic": roic_val,
            "ev_to_sales": info.get("enterpriseToRevenue"),
            "interest_coverage": interest_coverage_val,
            # Healthcare specifics
            "rd_intensity": hc_metrics["rd_intensity"],
            "cash_runway_quarters": hc_metrics["cash_runway_quarters"],
            "current_ratio": hc_metrics["current_ratio"],
            "quick_ratio": hc_metrics["quick_ratio"],
            "dso": hc_metrics["dso"],
            "sga_trend": hc_metrics["sga_trend"],
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
            if de_ratio < 10:  
                de_ratio = de_ratio * 100
                
            if de_ratio > limit:
                return False
            
        ic_ratio = m.get("interest_coverage")
        if ic_ratio is not None:
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

    print("\nTOP HEALTHCARE STOCKS\n")

    sector = "Healthcare"
    print(f"\n===== {sector} =====")

    scorer = SECTOR_SCORERS.get(sector)
    if scorer is None:
        print("Scorer for Healthcare not found!")
        return

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
            "interest_coverage": metrics.get("interest_coverage"),
            "rd_intensity": metrics.get("rd_intensity"),
            "cash_runway_quarters": metrics.get("cash_runway_quarters"),
            "current_ratio": metrics.get("current_ratio"),
            "quick_ratio": metrics.get("quick_ratio"),
            "dso": metrics.get("dso"),
            "sga_trend": metrics.get("sga_trend")
        })

    # Sort candidates by score descending
    sector_results.sort(key=lambda x: x["score"], reverse=True)

    # TOP 5 output
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

        roic_str = f"{s['roic']:.1%}" if s['roic'] is not None else "N/A"
        evs_str = f"{s['ev_to_sales']:.2f}x" if s['ev_to_sales'] is not None else "N/A"
        peg_str = f"{s['peg']:.2f}" if s['peg'] is not None else "N/A"

        ic = s.get("interest_coverage")
        if ic is not None:
            ic_str = "Inf (No Debt)" if ic == float('inf') else f"{ic:.2f}x"
        else:
            ic_str = "N/A"

        # Format Healthcare Specific Display Strings
        rdi = s.get("rd_intensity")
        rdi_str = f"{rdi:.1%}" if rdi is not None else "N/A"
        
        runway = s.get("cash_runway_quarters")
        if runway is not None:
            runway_str = "Inf (Profitable)" if runway == float("inf") else f"{runway:.1f} Qtrs"
        else:
            runway_str = "N/A"

        cr = s.get("current_ratio")
        cr_str = f"{cr:.2f}x" if cr is not None else "N/A"

        qr = s.get("quick_ratio")
        qr_str = f"{qr:.2f}x" if qr is not None else "N/A"

        dso = s.get("dso")
        dso_str = f"{dso:.0f} days" if dso is not None else "N/A"

        sga = s.get("sga_trend")
        sga_str = f"{sga:+.1%}" if sga is not None else "N/A"

        # --- VISUAL PRINTING LAYOUT ---
        print(f"--------------------------------------------------------------------------------")
        print(f"🚀 {s['symbol']:<6} | ✨ Score: {s['score']}/100 | 🏷️  {s['category']}")
        print(f"--------------------------------------------------------------------------------")
        
        print(f"   [Financials] Cap: {mc_str:<9} | Rev: {rev_str:<10} | Vol ($): {dv_str} | IntCov: {ic_str}")
        print(f"   [Margins]    Gross: {gm_str:<7} | D/E: {de_str:<10} | ROIC: {roic_str}")
        print(f"   [Growth]     Rev Growth: {rev_g_str:<6} | EPS Growth: {epsg_str:<9} | PEG: {peg_str}")
        print(f"   [Valuation]  EV/Sales: {evs_str}")
        print(f"   [Healthcare] R&D Int: {rdi_str:<7} | Runway: {runway_str:<16} | Curr/Quick: {cr_str} / {qr_str}")
        print(f"   [Efficiency] DSO: {dso_str:<11} | SG&A Trend: {sga_str}")
        
        # Earnings History
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
                        if f_surprise == f_surprise:
                            valid_quarters_count += 1
                            if f_surprise > 0:
                                beats += 1
                    except (ValueError, TypeError):
                        continue
            
            if valid_quarters_count > 0:
                print(f"Beat Record: {beats}/{valid_quarters_count} quarters")
            else:
                print("Beat Record: N/A")
        else:
            print("Beat Record: N/A")
        
        # Technicals
        rel_status = "Beats Sector (2/2)" if s["relative_score"] == 10 else ("Beats Period (1/2)" if s["relative_score"] == 5 else "Underperforms")
        trend_status = "Above 50-day MA" if s["trend_score"] == 5 else "Below 50-day MA"
        print(f"   [Technicals] Trend: {trend_status:<16} | Sector Rel: {rel_status}")
        
        # Score Breakdown
        print("\n   [Score Breakdown]")
        breakdown = s.get("breakdown", {})
        for metric_name, points in breakdown.items():
            print(f"    ▪ {metric_name:<25} : +{points} pts")
            
        print()

if __name__ == "__main__":
    main()