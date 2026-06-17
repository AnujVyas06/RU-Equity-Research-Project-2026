# sectors/industrial_energy.py
from utils import revenue_acceleration_score

from utils import revenue_acceleration_score


def score(metrics):

    score = 0
    breakdown = {}

    # Revenue Growth

    growth = metrics.get("revenue_growth")

    if growth is not None:

        if growth > 0.25:
            pts = 15
        elif growth > 0.15:
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


    # Free Cash Flow

    if (metrics.get("free_cf") or 0) > 0:
        pts = 5
    else:
        pts = 0

    score += pts
    breakdown["Free Cash Flow"] = pts


    return score, breakdown