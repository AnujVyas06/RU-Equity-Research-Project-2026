import numpy as np


def revenue_acceleration_score(quarterly_revenue):

    """
    Returns:
    15 = Accelerating
    8  = Stable
    0  = Declining
    """

    if quarterly_revenue is None or len(quarterly_revenue) < 4:
        return 0


    # -----------------------------
    # Step 1: compute QoQ growth
    # -----------------------------

    growth = []

    for i in range(1, len(quarterly_revenue)):

        prev = quarterly_revenue[i - 1]
        curr = quarterly_revenue[i]

        if prev is None or curr is None or prev == 0:
            continue

        growth.append((curr - prev) / abs(prev))


    if len(growth) < 3:
        return 0


    growth = np.array(growth)



    # -----------------------------
    # Step 2: split trend windows
    # -----------------------------

    mid = len(growth) // 2

    early = growth[:mid]
    late = growth[mid:]



    if len(early) == 0 or len(late) == 0:
        return 0



    early_avg = np.mean(early)
    late_avg = np.mean(late)



    # -----------------------------
    # Step 3: classification logic
    # -----------------------------

    diff = late_avg - early_avg



    # Normalize noise (prevents tiny differences breaking everything)
    threshold = 0.03   # 3% change buffer



    if diff > threshold:
        return 15   # Accelerating

    elif diff > -threshold:
        return 8    # Stable

    else:
        return 0    # Declining