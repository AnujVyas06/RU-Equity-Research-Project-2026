# sectors/consumer_retail.py
from utils import revenue_acceleration_score

def score(metrics):

    score = 0
    breakdown = {}

    # Revenue Growth

    growth = metrics.get("revenue_growth")

    if growth is not None:

        if growth > 0.20:
            pts = 15
        elif growth > 0.10:
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


    # Gross Margin

    margin = metrics.get("gross_margin")

    if margin is not None:

        if margin > 0.25:
            pts = 10
        elif margin > 0.15:
            pts = 5
        else:
            pts = 0

    else:
        pts = 0

    score += pts
    breakdown["Gross Margin"] = pts


    return score, breakdown