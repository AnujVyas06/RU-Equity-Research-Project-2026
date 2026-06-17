# sectors/technology.py
from utils import revenue_acceleration_score

def score(metrics):

    score = 0
    breakdown = {}

    # -------------------------
    # Revenue Growth (15)
    # -------------------------

    growth = metrics.get("revenue_growth")

    if growth is not None:

        if growth > 0.40:
            pts = 15
        elif growth > 0.25:
            pts = 12
        elif growth > 0.15:
            pts = 8
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["Revenue Growth"] = pts


    # -------------------------
    # Revenue Acceleration (15)
    # -------------------------

    quarterly_revenue = metrics.get("quarterly_revenue")

    pts = revenue_acceleration_score(quarterly_revenue)

    score += pts
    breakdown["Revenue Acceleration"] = pts

    # -------------------------
    # Gross Margin (10)
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
    # EPS Growth (10)
    # -------------------------

    eps = metrics.get("eps_growth")

    if eps is not None:

        if eps > 0.30:
            pts = 10
        elif eps > 0.15:
            pts = 7
        elif eps > 0:
            pts = 3
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["EPS Growth"] = pts


    # -------------------------
    # Operating Cash Flow (5)
    # -------------------------
    if (metrics.get("operating_cf") or 0) > 0:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Operating Cash Flow"] = pts


    # -------------------------
    # Free Cash Flow (5)
    # -------------------------

    if (metrics.get("free_cf") or 0) > 0:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Free Cash Flow"] = pts


    # -------------------------
    # ROIC (5)
    # -------------------------

    roic = metrics.get("roic")

    if roic is not None:

        if roic > 0.15:
            pts = 5
        elif roic > 0.10:
            pts = 3
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["ROIC"] = pts


    # -------------------------
    # PEG (2)
    # -------------------------

    peg = metrics.get("peg")

    if peg is not None:

        if peg < 1:
            pts = 2
        elif peg < 1.5:
            pts = 1
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["PEG"] = pts


    return score, breakdown