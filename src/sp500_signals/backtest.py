"""Backtest the signal strategy against buy-and-hold over the same window."""

from __future__ import annotations

import math

import pandas as pd

TRADING_DAYS = 252


def _stats(daily_returns: pd.Series, exposure: pd.Series | None, rf: float) -> dict:
    equity = (1 + daily_returns).cumprod()
    years = len(daily_returns) / TRADING_DAYS
    total = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / years) - 1 if years > 0 else float("nan")
    vol = daily_returns.std() * math.sqrt(TRADING_DAYS)
    sharpe = (daily_returns.mean() * TRADING_DAYS - rf) / vol if vol > 0 else float("nan")
    drawdown = (equity / equity.cummax() - 1).min()
    return {
        "total_return": round(float(total), 4),
        "cagr": round(float(cagr), 4),
        "volatility": round(float(vol), 4),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown": round(float(drawdown), 4),
        "exposure": round(float(exposure.mean()), 4) if exposure is not None else 1.0,
    }


def run_backtest(close: pd.Series, position: pd.Series, signals: pd.DataFrame, rf: float = 0.0) -> dict:
    market = close.pct_change().fillna(0.0)
    strategy = market * position

    trades = []
    entries = signals[signals["type"] == "entry"].reset_index(drop=True)
    exits = signals[signals["type"] == "exit"].reset_index(drop=True)
    for i, entry in entries.iterrows():
        closed = i < len(exits)
        exit_price = exits.loc[i, "close"] if closed else close.iloc[-1]
        trades.append(exit_price / entry["close"] - 1)
    wins = [t for t in trades if t > 0]

    return {
        "strategy": _stats(strategy, position, rf),
        "buy_and_hold": _stats(market, None, rf),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades), 4) if trades else None,
        "avg_trade_return": round(sum(trades) / len(trades), 4) if trades else None,
        "open_position": bool(len(entries) > len(exits)),
    }
