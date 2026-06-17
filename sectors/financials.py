# sectors/financials.py
from utils import revenue_acceleration_score

def score(metrics):

    score = 0
    breakdown = {}

    # ROE (core for banks)

    roe = metrics.get("roe")

    if roe is not None:

        if roe > 0.15:
            pts = 15
        elif roe > 0.12:
            pts = 10
        else:
            pts = 5

    else:
        pts = 0

    score += pts
    breakdown["ROE"] = pts


    # Revenue Growth

    growth = metrics.get("revenue_growth")

    if growth is not None:

        if growth > 0.20:
            pts = 10
        else:
            pts = 5

    else:
        pts = 0

    score += pts
    breakdown["Revenue Growth"] = pts


    # Revenue Acceleration

    quarterly_revenue = metrics.get("quarterly_revenue")

    pts = revenue_acceleration_score(quarterly_revenue)

    score += pts
    breakdown["Revenue Acceleration"] = pts


    # Net Interest Margin

    nim = metrics.get("net_interest_margin")

    if nim is not None and nim > 0.02:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Net Interest Margin"] = pts


    return score, breakdown