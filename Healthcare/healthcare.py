# sectors/healthcare.py

from utils import revenue_acceleration_score, earnings_beat_score

def score(metrics):
    score = 0
    breakdown = {}

    # 1. R&D Intensity (Max 15 pts) - Band-based scoring
    rd_int = metrics.get("rd_intensity")
    if rd_int is not None:
        if 0.10 <= rd_int <= 0.35:
            pts = 15  # Optimal investment range for commercial healthcare
        elif 0.35 < rd_int <= 0.60:
            pts = 10  # Heavy R&D focus / Growth Biotech
        elif rd_int > 0.60:
            pts = 4   # Commercial stage red flag / high cash burn
        elif 0.05 <= rd_int < 0.10:
            pts = 5   # Low investment
        else:
            pts = 0   # Under-investing (<5%)
    else:
        pts = 0
    score += pts
    breakdown["R&D Intensity"] = pts

    # 2. Cash Runway (Max 20 pts) - Crucial for pre-profit/growth healthcare
    runway = metrics.get("cash_runway_quarters")
    if runway is not None:
        if runway == float("inf"):
            pts = 20  # Cash flow positive
        elif runway >= 8: # >= 2 years runway
            pts = 18
        elif runway >= 6: # 1.5 - 2 years
            pts = 12
        elif runway >= 4: # 1 year runway
            pts = 6
        else:
            pts = 0   # Dilution risk (<1 year runway)
    else:
        pts = 0
    score += pts
    breakdown["Cash Runway"] = pts

    # 3. Liquidity - Current Ratio (Max 10 pts)
    cr = metrics.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            pts = 10
        elif cr >= 1.5:
            pts = 7
        elif cr >= 1.0:
            pts = 3
        else:
            pts = 0
    else:
        pts = 0
    score += pts
    breakdown["Liquidity (Current Ratio)"] = pts

    # 4. Receivables Risk / Days Sales Outstanding (Max 10 pts)
    dso = metrics.get("dso")
    if dso is not None:
        if dso <= 45:
            pts = 10  # Fast collections
        elif dso <= 65:
            pts = 7   # Standard medical reimbursement lag
        elif dso <= 90:
            pts = 3   # Elevated reimbursement risk
        else:
            pts = 0   # High collection risk (>90 days)
    else:
        pts = 5       # Neutral fallback if non-applicable (e.g. pre-revenue biotech)
    score += pts
    breakdown["DSO / Collections"] = pts

    # 5. SG&A Trend (Max 10 pts)
    sga_trend = metrics.get("sga_trend")
    if sga_trend is not None:
        if sga_trend < -0.05:
            pts = 10  # SG&A % dropped > 5% (Scaling efficiency inflection)
        elif sga_trend < 0:
            pts = 6   # Slight efficiency improvement
        else:
            pts = 0   # Bloat or loss of operating leverage
    else:
        pts = 0
    score += pts
    breakdown["SG&A Scaling Efficiency"] = pts

    # 6. Revenue Growth & Acceleration (Max 20 pts)
    rev_growth = metrics.get("revenue_growth") or 0
    q_rev = metrics.get("quarterly_revenue")
    rev_score = 0
    
    if rev_growth > 0.25:
        rev_score += 10
    elif rev_growth > 0.10:
        rev_score += 5

    accel_pts = revenue_acceleration_score(q_rev)
    rev_score += 10 if accel_pts == 15 else (5 if accel_pts == 8 else 0)
    
    score += rev_score
    breakdown["Revenue Dynamics"] = rev_score

    # 7. Technical & Relative Strength (Max 15 pts)
    rel_pts = metrics.get("relative_score", 0) # Max 10
    trend_pts = metrics.get("trend_score", 0)   # Max 5
    tech_score = rel_pts + trend_pts
    score += tech_score
    breakdown["Technicals & Momentum"] = tech_score

    return score, breakdown