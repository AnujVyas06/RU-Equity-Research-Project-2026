# sectors/healthcare.py
from utils import revenue_acceleration_score

def score(metrics):

    score = 0
    breakdown = {}

    # -------------------------
    # Revenue Growth (15 pts)
    # -------------------------

    growth = metrics.get("revenue_growth")

    if growth is not None:

        if growth > 0.30:
            pts = 15
        elif growth > 0.20:
            pts = 10
        elif growth > 0.10:
            pts = 5
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["Revenue Growth"] = pts


    # -------------------------
    # Revenue Acceleration (15 pts)
    # -------------------------

    quarterly_revenue = metrics.get("quarterly_revenue")

    pts = revenue_acceleration_score(quarterly_revenue)

    score += pts
    breakdown["Revenue Acceleration"] = pts


    # -------------------------
    # Gross Margin (Healthcare threshold ~40%)
    # -------------------------

    margin = metrics.get("gross_margin")

    if margin is not None:

        if margin > 0.40:
            pts = 10
        elif margin > 0.25:
            pts = 7
        elif margin > 0.15:
            pts = 4
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["Gross Margin"] = pts


    # -------------------------
    # EPS Growth (10 pts)
    # -------------------------

    eps = metrics.get("eps_growth")

    if eps is not None:

        if eps > 0.25:
            pts = 10
        elif eps > 0.10:
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
    # Cash Strength / Runway (important for healthcare)
    # -------------------------

    operating_cf = metrics.get("operating_cf", 0)

    free_cf = metrics.get("free_cf", 0)

    if operating_cf > 0 and free_cf > 0:
        pts = 5
    elif operating_cf > 0:
        pts = 3
    else:
        pts = 0

    score += pts
    breakdown["Cash Flow Health"] = pts


    return score, breakdown