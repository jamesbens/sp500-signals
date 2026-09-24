"""Offline tests: synthetic prices only, so CI never depends on Yahoo being up."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sp500_signals.backtest import run_backtest  # noqa: E402
from sp500_signals.config import Config  # noqa: E402
from sp500_signals.extract import DataQualityError, normalize, validate  # noqa: E402
from sp500_signals.pipeline import build  # noqa: E402
from sp500_signals.signals import ENTRY, EXIT, generate_signals, position_series  # noqa: E402
from sp500_signals.transform import rsi, sma  # noqa: E402


def make_bars(close: np.ndarray, start="2019-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(close), name="date")
    close = pd.Series(close, index=idx)
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1_000_000}
    )


@pytest.fixture
def wave_bars():
    """Sine wave around an uptrend: guaranteed oversold and overbought episodes."""
    n = 1800
    t = np.arange(n)
    return make_bars(3000 + t * 1.5 + 250 * np.sin(t / 25))


def test_sma_matches_manual_mean():
    s = pd.Series([1.0, 2, 3, 4, 5])
    assert sma(s, 3).tolist()[2:] == [2.0, 3.0, 4.0]
    assert sma(s, 3).isna().sum() == 2


def test_rsi_bounds_and_extremes():
    up = pd.Series(np.arange(1, 60, dtype=float))
    down = up[::-1].reset_index(drop=True)
    assert rsi(up).dropna().eq(100).all()
    assert rsi(down).dropna().lt(1).all()
    noisy = pd.Series(np.random.default_rng(0).normal(0, 1, 500).cumsum() + 100)
    values = rsi(noisy).dropna()
    assert values.between(0, 100).all()


def test_signals_alternate_and_start_with_entry(wave_bars):
    df = wave_bars.assign(rsi=rsi(wave_bars["close"]))
    sig = generate_signals(df, 30, 70)
    assert len(sig) >= 4
    assert sig["type"].iloc[0] == ENTRY
    types = sig["type"].tolist()
    assert all(a != b for a, b in zip(types, types[1:])), "entries and exits must alternate"


def test_position_has_no_lookahead(wave_bars):
    df = wave_bars.assign(rsi=rsi(wave_bars["close"]))
    sig = generate_signals(df, 30, 70)
    pos = position_series(df.index, sig)
    first_entry = sig.loc[sig["type"] == ENTRY, "date"].iloc[0]
    assert pos.loc[first_entry] == 0.0  # signal day itself is not yet invested
    assert pos.shift(-1).loc[first_entry] == 1.0


def test_backtest_buy_and_hold_matches_price_change(wave_bars):
    close = wave_bars["close"]
    stats = run_backtest(close, pd.Series(1.0, index=close.index), pd.DataFrame(columns=["type", "close"]))
    expected = close.iloc[-1] / close.iloc[0] - 1
    assert stats["buy_and_hold"]["total_return"] == pytest.approx(expected, abs=1e-4)


def test_build_payload_shape(wave_bars):
    payload = build(wave_bars, Config(display_years=5))
    n = len(payload["series"]["date"])
    assert all(len(v) == n for v in payload["series"].values())
    assert {s["type"] for s in payload["signals"]} <= {ENTRY, EXIT}
    assert payload["meta"]["disclaimer"]


def test_normalize_flattens_multiindex():
    cols = pd.MultiIndex.from_product([["Close", "High", "Low", "Open", "Volume"], ["^GSPC"]])
    raw = pd.DataFrame([[1, 2, 0.5, 1, 10]], columns=cols, index=pd.to_datetime(["2024-01-02"]))
    out = normalize(raw)
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d.drop(columns="volume"), "missing columns"),
        (lambda d: d.iloc[:10], "rows"),
        (lambda d: d.assign(close=d["close"].where(d.index != d.index[5])), "null"),
        (lambda d: d.assign(low=d["high"] * 2), "high < low"),
        (lambda d: d.assign(close=d["close"].where(d.index != d.index[50], 1.0)), "implausible"),
    ],
)
def test_validate_rejects_bad_data(wave_bars, mutate, message):
    with pytest.raises(DataQualityError, match=message):
        validate(mutate(wave_bars))


def test_validate_accepts_good_data(wave_bars):
    assert validate(wave_bars) is not None
