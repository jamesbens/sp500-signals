"""Extract daily OHLCV history from Yahoo Finance and validate it before anything downstream sees it."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataQualityError(Exception):
    """Raised when extracted data fails a validation rule."""


def fetch_history(ticker: str, start: date, end: date | None = None, retries: int = 3) -> pd.DataFrame:
    """Download daily bars with retry + exponential backoff (Yahoo occasionally rate-limits)."""
    end = end or date.today() + timedelta(days=1)
    for attempt in range(1, retries + 1):
        try:
            raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if raw.empty:
                raise DataQualityError(f"Yahoo returned no rows for {ticker}")
            return normalize(raw)
        except Exception as exc:  # network errors surface as many exception types
            if attempt == retries:
                raise
            wait = 2**attempt
            log.warning("fetch attempt %d failed (%s); retrying in %ds", attempt, exc, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance's (field, ticker) MultiIndex columns into a tidy, lower-case frame."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    return df[REQUIRED_COLUMNS].sort_index()


def validate(df: pd.DataFrame, min_rows: int = 250) -> pd.DataFrame:
    """Enforce data contracts. Fails loudly rather than publishing a wrong chart."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise DataQualityError(f"missing columns: {sorted(missing)}")
    if len(df) < min_rows:
        raise DataQualityError(f"only {len(df)} rows, expected >= {min_rows}")
    if df.index.has_duplicates:
        raise DataQualityError("duplicate trading dates")
    if not df.index.is_monotonic_increasing:
        raise DataQualityError("dates are not sorted")
    prices = df[["open", "high", "low", "close"]]
    if prices.isna().any().any():
        raise DataQualityError("null prices present")
    if (prices <= 0).any().any():
        raise DataQualityError("non-positive prices present")
    if (df["high"] < df["low"]).any():
        raise DataQualityError("high < low on at least one bar")
    # A >25% one-day move on the index would almost certainly be a data error.
    worst = df["close"].pct_change().abs().max()
    if worst > 0.25:
        raise DataQualityError(f"implausible daily move of {worst:.1%}")
    return df
