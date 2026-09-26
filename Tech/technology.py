# sectors/technology.py
from utils import revenue_acceleration_score
from utils import earnings_beat_score
from config import (
    HIGH_EPS_GROWTH, MEDIUM_EPS_GROWTH, 
    HIGH_ROIC, MEDIUM_ROIC, 
    MAX_PEG_EXCELLENT, MAX_PEG_ACCEPTABLE, 
    SECTOR_EV_SALES_MEDIANS
)

def score(metrics):

    score = 0
    breakdown = {}

    # -------------------------
    # Revenue Growth (Max 20) - Scaled up for 100-pt system
    # -------------------------
    growth = metrics.get("revenue_growth")
    if growth is not None:
        if growth > 0.40:
            pts = 20
        elif growth > 0.25:
            pts = 15
        elif growth > 0.15:
            pts = 10
        else:
            pts = 0
    else:
        pts = 0

    score += pts
    breakdown["Revenue Growth"] = pts


    # -------------------------
    # Revenue Acceleration (Max 15)
    # -------------------------
    quarterly_revenue = metrics.get("quarterly_revenue")
    pts = revenue_acceleration_score(quarterly_revenue)
    score += pts
    breakdown["Revenue Acceleration"] = pts


    # -------------------------
    # Gross Margin (Max 10)
    # -------------------------
    margin = metrics.get("gross_margin")
    if margin is not None:
        if margin > 0.50:
            pts = 10
        elif margin > 0.35:
            pts = 7
        elif margin > 0.20:
            pts = 4
        else:
            pts = 0
    else:
        pts = 0

    score += pts
    breakdown["Gross Margin"] = pts


    # -------------------------
    # EPS Growth (Max 15) - Scaled up for 100-pt system
    # -------------------------
    eps_growth = metrics.get("eps_growth")
    if eps_growth is not None:
        if eps_growth > HIGH_EPS_GROWTH:        # 0.30 from config
            pts = 15
        elif eps_growth > MEDIUM_EPS_GROWTH:    # 0.15 from config
            pts = 10
        elif eps_growth > 0:
            pts = 5
        else:
            pts = 0
    else:
        pts = 0

    score += pts
    breakdown["EPS Growth"] = pts


    # -------------------------
    # Earnings Beat History (Max 5)
    # -------------------------
    beat_pts = earnings_beat_score(metrics.get("earnings_history"))
    score += beat_pts
    breakdown["Earnings Beat History"] = beat_pts


    # -------------------------
    # Operating Cash Flow (Max 5)
    # -------------------------
    if (metrics.get("operating_cf") or 0) > 0:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Operating Cash Flow"] = pts


    # -------------------------
    # Free Cash Flow (Max 5)
    # -------------------------
    if (metrics.get("free_cf") or 0) > 0:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Free Cash Flow"] = pts


    # -------------------------
    # Relative Performance (Max 10)
    # -------------------------
    relative_pts = metrics.get("relative_score", 0) 
    score += relative_pts
    breakdown["Relative Performance"] = relative_pts


    # -------------------------
    # Technical Trend (Max 5)
    # -------------------------
    trend_pts = metrics.get("trend_score", 0)
    score += trend_pts
    breakdown["Technical Trend"] = trend_pts


    # ---------------------------------------------------------
    # Capital Efficiency (ROIC Score) (Max 5)
    # ---------------------------------------------------------
    roic = metrics.get("roic") 
    roic_pts = 0
    if roic is not None:
        if roic > HIGH_ROIC:
            roic_pts = 5
        elif roic >= MEDIUM_ROIC:
            roic_pts = 3

    score += roic_pts
    breakdown["Capital Efficiency"] = roic_pts


    # ---------------------------------------------------------
    # EV/Sales vs Sector Median (Max 3)
    # ---------------------------------------------------------
    ev_sales = metrics.get("ev_to_sales") 
    sector_name = metrics.get("sector", "Technology")
    sector_median = SECTOR_EV_SALES_MEDIANS.get(sector_name, 4.0)
    ev_sales_pts = 0

    if ev_sales is not None:
        if ev_sales < sector_median:
            ev_sales_pts = 3
        elif abs(ev_sales - sector_median) / sector_median <= 0.15:
            ev_sales_pts = 2

    score += ev_sales_pts
    breakdown["EV/Sales Valuation"] = ev_sales_pts


    # ---------------------------------------------------------
    # PEG Ratio Score (Max 2)
    # ---------------------------------------------------------
    peg = metrics.get("peg") 
    peg_pts = 0
    if peg is not None:
        if peg < MAX_PEG_EXCELLENT:
            peg_pts = 2
        elif peg <= MAX_PEG_ACCEPTABLE:
            peg_pts = 1

    score += peg_pts
    breakdown["PEG Ratio"] = peg_pts

    return score, breakdown