# config.py


# =====================================================
# UNIVERSE FILTERS
# =====================================================

# Market Cap
MIN_MARKET_CAP = 500_000_000
MAX_MARKET_CAP = 10_000_000_000


# Yahoo first liquidity screen
# Shares traded per day

MIN_AVG_VOLUME = 100_000


# Real liquidity requirement
# Avg Daily Volume x Share Price

MIN_DOLLAR_VOLUME = 2_000_000



# Yahoo API batch size

FETCH_BATCH_SIZE = 250





# =====================================================
# HARD FILTERS
# =====================================================


# Trailing Twelve Month Revenue

MIN_REVENUE = 50_000_000


# Minimum YoY Revenue Growth

MIN_REVENUE_GROWTH = 0.15



# Interest Coverage

MIN_INTEREST_COVERAGE = 3





# =====================================================
# DEBT / EQUITY LIMITS
# =====================================================


# Yahoo returns:
# 150 = 1.5
# 200 = 2.0


DEBT_TO_EQUITY_LIMITS = {


    "Technology":150,

    "Healthcare":200,

    "Consumer Cyclical":300,

    "Consumer Defensive":300,

    "Industrials":300,

    "Energy":300,

    "Basic Materials":300,


    # Financial companies excluded

    "Financial Services":None

}





# =====================================================
# SCORING CONSTANTS
# =====================================================


HIGH_ROIC = 0.15

MEDIUM_ROIC = 0.10


HIGH_EPS_GROWTH = 0.30

MEDIUM_EPS_GROWTH = 0.15


MAX_PEG_EXCELLENT = 1.0

MAX_PEG_ACCEPTABLE = 1.5





# =====================================================
# SECTORS
# =====================================================


SECTORS = [

    "Technology",

    #"Healthcare",

    #"Financial Services",

    #"Industrials",

    #"Energy",

    #"Consumer Cyclical",

    #"Consumer Defensive",

    #"Basic Materials",

]