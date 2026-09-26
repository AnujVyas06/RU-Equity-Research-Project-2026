# Sector-Aware Stock Screener

A Python tool that screens U.S. equities via Yahoo Finance, applies liquidity/fundamental hard filters, and scores surviving candidates against sector-specific criteria to surface the top 5 stocks per sector on a 100-point scale.

## What it does

1. **Screens** a universe of U.S. stocks by market cap and trading volume using `yfinance`'s `EquityQuery` screener.
2. **Fetches** fundamental and technical metrics for each candidate (revenue, margins, growth rates, cash flow, debt ratios, earnings history, moving averages, relative sector performance).
3. **Filters** out candidates that fail hard minimums (revenue, revenue growth, debt-to-equity, interest coverage, dollar volume).
4. **Scores** each surviving candidate using a sector-specific model (Technology and Healthcare currently implemented) that weights the metrics that matter most for that sector.
5. **Reports** the top 5 stocks per sector with a formatted breakdown of financials, margins, growth, valuation, earnings history, technicals, and the full point breakdown.

## Project structure

```
.
├── stock_screener.py      # Main pipeline: screening, metric fetching, filtering, reporting
├── config.py               # All thresholds, limits, and scoring constants
├── utils.py                 # Shared calculation helpers (interest coverage, trend score,
│                             #   relative performance, earnings beats, EPS/revenue growth)
└── sectors/
    ├── technology.py        # Technology sector scoring model
    ├── healthcare.py         # Healthcare sector scoring model
    ├── financials.py         # Financial Services scoring model
    ├── industrial_energy.py  # Industrials / Energy scoring model
    └── consumer_retail.py    # Consumer Cyclical / Consumer Defensive scoring model
```

## How scoring works

Each sector module implements a `score(metrics) -> (score, breakdown)` function. All models score out of 100 points but weight categories differently based on what matters for that sector:

- **Technology**: revenue growth & acceleration, gross margin, EPS growth, cash flow, capital efficiency (ROIC), valuation (EV/Sales, PEG), technicals.
- **Healthcare**: R&D intensity, cash runway (critical for pre-profit biotech), liquidity, days sales outstanding, SG&A scaling efficiency, revenue dynamics, technicals.

Final scores map to a category label:

| Score  | Category                  |
|--------|----------------------------|
| ≥ 90   | Exceptional Growth Company |
| ≥ 75   | Strong Growth Candidate    |
| ≥ 60   | Needs Review               |
| < 60   | Not Growth Candidate       |

## Configuration

All tunable parameters live in `config.py`:

- **Universe filters**: market cap range, minimum average volume, minimum dollar volume, screener batch size.
- **Hard filters**: minimum revenue, minimum revenue growth, minimum interest coverage.
- **Debt/equity limits**: per-sector maximum leverage (Financial Services excluded, since leverage norms differ).
- **Scoring constants**: ROIC thresholds, EPS growth thresholds, PEG ratio targets, sector EV/Sales medians.
- **`SECTORS`**: which sectors to run the screener against (comment/uncomment as needed).

## Setup

```bash
pip install yfinance pandas numpy requests
```

## Usage

```bash
python stock_screener.py
```

This prints a formatted dashboard to the console for each sector enabled in `config.py`, showing the top 5 candidates with financials, margins, growth, valuation, earnings beat history, technicals, and a full score breakdown.

## Notes & known limitations

- Relies on Yahoo Finance's unofficial screener API (`yfinance`), which can rate-limit or return incomplete data; the code fails gracefully (returns `None`/`0`) when fields are missing.
- `debt_to_equity` values from Yahoo are inconsistently scaled (sometimes a ratio like `1.5`, sometimes a percentage like `150`); the filter logic normalizes this heuristically.
- A 0.5s delay is added between ticker fetches to reduce the chance of throttling — expect the full run to take a while for large sectors.
- Sector benchmarks for relative performance scoring (e.g., `XLK` for Technology, `XLV` for Healthcare) are hardcoded in `utils.py`.

## Roadmap ideas

- Add remaining sector scoring models with the same rigor as Technology/Healthcare.
- Cache fetched metrics to avoid re-hitting the API on repeated runs.
- Export results to CSV/JSON in addition to console output.
- Add unit tests around the scoring functions and edge-case handling (NaN surprises, missing quarterly data, etc.).
