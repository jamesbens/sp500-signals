"""Technical indicators. Pure functions over pandas Series so they are trivially unit-testable."""

import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI (exponential smoothing with alpha = 1/period)."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss
    out = 100 - 100 / (1 + rs)
    # No losses in the window -> RSI is 100 by definition.
    return out.where(loss != 0, 100.0).where(gain.notna())


def add_indicators(df: pd.DataFrame, rsi_period: int, sma_fast: int, sma_slow: int) -> pd.DataFrame:
    out = df.copy()
    out["rsi"] = rsi(out["close"], rsi_period)
    out["sma_fast"] = sma(out["close"], sma_fast)
    out["sma_slow"] = sma(out["close"], sma_slow)
    return out
