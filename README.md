# S&P 500 Entry & Exit Signals

[![daily-pipeline](https://github.com/jamesbens/sp500-signals/actions/workflows/pipeline.yml/badge.svg)](https://github.com/jamesbens/sp500-signals/actions/workflows/pipeline.yml)

**Live chart:** https://jamesbens.github.io/sp500-signals/ · **Portfolio:** https://jamesbens.github.io/

A small, production-style data pipeline that pulls the last 5 years of S&P 500 (`^GSPC`) history from
Yahoo Finance every trading day. It validates the data, computes technical indicators and marks
**recommended entry points (green ▲)** and **exit points (red ▼)**. It then back-tests the rule against
buy-and-hold and publishes the result as static JSON for an interactive chart.

> Educational data-engineering demo. **Not investment advice.**

## Architecture

```
Yahoo Finance ──► extract.py ──► validate() ──► transform.py ──► signals.py ──► backtest.py ──► docs/data/*.json ──► GitHub Pages chart
   (yfinance,       retry +        data           RSI(14),          2-state         vs buy &         atomic write        (ECharts)
    ~6y daily)      backoff        contracts      SMA 50/200        machine         hold
                                        ▲
                      GitHub Actions: Mon–Fri 22:30 UTC · runs tests first · commits only if data changed
```

| Stage | What it does | Why it matters |
|---|---|---|
| **Extract** | Downloads ~6 years of daily OHLCV (5 displayed + warm-up so the 200-day SMA is valid on day one). Retries with exponential back-off. | Yahoo rate-limits; the job must be robust to transient failures. |
| **Validate** | Schema, row count, duplicates, ordering, nulls, non-positive prices, `high < low`, and a >25% daily-move sanity check. | The pipeline **fails loudly** instead of publishing a wrong chart. |
| **Transform** | Wilder's RSI(14), 50-day and 200-day SMA as pure functions. | Pure functions are trivially unit-testable. |
| **Signals** | Entry when RSI crosses **above 30** (oversold rebound); exit when RSI crosses **below 70** (overbought fade). A 2-state machine guarantees entries and exits alternate. | No duplicate or contradictory markers. |
| **Backtest** | Acts on the signal at that day's close and earns returns from the next day, so there's **no look-ahead bias**. Reports total return, CAGR, volatility, Sharpe, max drawdown, exposure, win rate. | Honest evaluation against the obvious benchmark. |
| **Publish** | Writes `docs/data/sp500_signals.json` + `signals.csv` via temp-file-and-rename. | Idempotent and atomic: re-running the same day gives the same files; a crash never leaves half-written output. |

## Results (last run)

Over the 5-year window the rule made 5 round-trip trades with an 80% win rate. It had a lower max drawdown than
buy-and-hold (-20.8% vs -25.4%) while invested only ~36% of the time. In a strong bull market, buy-and-hold
still had the higher total return. The live numbers are on the chart page and change daily.

## Run locally

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                          # offline tests, synthetic data
PYTHONPATH=src python -m sp500_signals.pipeline    # writes docs/data/
python -m http.server -d docs 8000                 # open http://localhost:8000
```

Strategy parameters (RSI period and thresholds, SMA windows, display window) live in
[`src/sp500_signals/config.py`](src/sp500_signals/config.py).

## Project layout

```
src/sp500_signals/   extract.py · transform.py · signals.py · backtest.py · pipeline.py · config.py
tests/               13 offline unit tests (indicators, signal alternation, no look-ahead, data contracts)
docs/                GitHub Pages site: index.html + data/ (pipeline output)
.github/workflows/   pipeline.yml: scheduled ELT + tests + auto-commit
```

---
Built by [James Bensoussan](https://www.linkedin.com/in/james-bensoussan/), Data Engineer.
