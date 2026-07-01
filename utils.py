import numpy as np

import requests
import contextlib
import os
import sys
import yfinance as yf

@contextlib.contextmanager
def suppress_stdout():
    """Suppresses both stdout and stderr to completely silence external loggers."""
    with open(os.devnull, "w") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            yield

SECTOR_BENCHMARKS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
}

def calculate_interest_coverage(ticker):
    """
    Calculates the Interest Coverage Ratio (EBIT / Interest Expense).
    Returns float, or None if data is missing or interest expense is 0/positive.
    """
    try:
        # Use annual income statement for more stable structural debt safety analysis
        income = ticker.income_stmt
        if income is None or income.empty:
            return None

        # yfinance labels can vary slightly; check standard variations
        ebit_labels = ["EBIT", "Operating Income"]
        interest_labels = ["Interest Expense", "Interest Expense Non Operating"]

        ebit = None
        interest_exp = None

        # Extract the most recent fiscal year value (first column)
        for label in ebit_labels:
            if label in income.index:
                ebit = income.loc[label].dropna().iloc[0]
                break

        for label in interest_labels:
            if label in income.index:
                interest_exp = income.loc[label].dropna().iloc[0]
                break

        if ebit is None or interest_exp is None:
            return None

        # Interest expense is often represented as a positive number in yfinance.
        # Ensure it's absolute to avoid sign confusion.
        interest_exp = abs(interest_exp)

        if interest_exp == 0:
            return float('inf')  # No interest expense means functionally infinite coverage

        return ebit / interest_exp

    except Exception as e:
        # De-comment for debugging issues with specific tickers
        # print(f"Interest Coverage Error for {ticker.ticker}: {e}")
        return None
        
def get_moving_average_trend_score(ticker):
    try:
        # FIX: Changed period from "3m" to "3mo"
        hist = ticker.history(period="3mo")
        if hist.empty or len(hist) < 50:
            return 0
        
        # Calculate 50-day moving average
        hist['50MA'] = hist['Close'].rolling(window=50).mean()
        
        current_price = hist['Close'].iloc[-1]
        ma_50 = hist['50MA'].iloc[-1]
        
        if current_price > ma_50:
            return 5
        return 0
    except Exception:
        return 0
    
def calculate_relative_performance_score(ticker, sector_name):
    # Ensure standard string format matching
    sector_clean = str(sector_name).strip()
    benchmark_symbol = SECTOR_BENCHMARKS.get(sector_clean)
    
    if not benchmark_symbol:
        # Diagnostic print: Uncomment if you suspect sector name typos
        # print(f"⚠️ Debug: Sector '{sector_clean}' not found in SECTOR_BENCHMARKS mapping.")
        return 0
    
    try:
        # Fetch data safely
        stock_hist = ticker.history(period="6mo")
        bench_ticker = yf.Ticker(benchmark_symbol)
        bench_hist = bench_ticker.history(period="6mo")
        
        # Check for empty API returns (Throttling / Blocked calls)
        if stock_hist.empty or bench_hist.empty:
            print(f"⚠️ Debug for {ticker.ticker}: API returned empty history. Stock empty: {stock_hist.empty}, Benchmark empty: {bench_hist.empty}")
            return 0
            
        def get_return(df, approx_months):
            total_rows = len(df)
            if total_rows < 10:
                return 0
            
            # Anchor 3-month lookback safely via mid-point split
            if approx_months == 3:
                start_idx = max(0, total_rows // 2)
            else:
                start_idx = 0
                
            price_then = df['Close'].iloc[start_idx]
            price_now = df['Close'].iloc[-1]
            
            if price_then == 0:
                return 0
            return (price_now - price_then) / price_then

        # Calculate performance percentages
        stock_3m = get_return(stock_hist, 3)
        stock_6m = get_return(stock_hist, 6)
        
        bench_3m = get_return(bench_hist, 3)
        bench_6m = get_return(bench_hist, 6)
        
        # Explicit evaluation rules
        beats_3m = stock_3m > bench_3m
        beats_6m = stock_6m > bench_6m
        
        if beats_3m and beats_6m:
            return 10
        elif beats_3m or beats_6m:
            return 5
        
        # If it genuinely underperformed the index over both periods, it safely returns 0
        return 0

    except Exception as e:
        print(f"❌ Error during relative performance calculation for {ticker.ticker}: {e}")
        return 0
        
def get_earnings_history_yf(ticker):
    try:
        with suppress_stdout():
            df = ticker.earnings_dates

        if df is None or df.empty:
            return []

        df = df.reset_index()
        # Ensure the dataframe is strictly ordered from newest date to oldest date
        if "Earnings Date" in df.columns:
            df = df.sort_values(by="Earnings Date", ascending=False)
        elif "index" in df.columns: # fallback if index name didn't change
            df = df.sort_values(by="index", ascending=False)

        history = []
        for _, row in df.iterrows():
            history.append({
                "est": row.get("EPS Estimate"),
                "actual": row.get("Reported EPS"),
                "surprise": row.get("Surprise(%)")
            })

        return history

    except Exception as e:
        return []
    
import pandas as pd
import numpy as np

def clean_number(x):
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    if pd.isna(x):
        return None
    return x


def earnings_beat_score(history):
    if not history:
        return 0

    valid = []

    for h in history:
        surprise = clean_number(h.get("surprise"))

        if surprise is None:
            continue

        valid.append(surprise)

    if len(valid) < 4:
        return 0

    recent = valid[:8]

    avg_surprise = sum(recent) / len(recent)
    beat_ratio = sum(1 for x in recent if x > 0) / len(recent)

    score = 0

    if beat_ratio >= 0.75:
        score += 3
    elif beat_ratio >= 0.5:
        score += 2

    if avg_surprise > 5:
        score += 2
    elif avg_surprise > 2:
        score += 1

    if not history:
        return 0
    
    return score

def calculate_eps_growth(ticker):

    try:

        income = ticker.quarterly_income_stmt

        if income is None or income.empty:
            return None


        if "Diluted EPS" not in income.index:
            return None


        eps = (
            income.loc["Diluted EPS"]
            .dropna()
            .tolist()
        )[::-1]


        # Need current quarter and same quarter last year
        if len(eps) < 5:
            return None


        current_eps = eps[-1]
        previous_eps = eps[-5]


        if previous_eps == 0:
            return None


        growth = (
            current_eps - previous_eps
        ) / abs(previous_eps)


        return growth


    except Exception as e:
        print(f"EPS Growth Error: {e}")
        return None
    
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
    
    