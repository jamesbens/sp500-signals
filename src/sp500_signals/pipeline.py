"""Orchestrates one end-to-end run. Idempotent: re-running on the same day rewrites the same files.

    python -m sp500_signals.pipeline            # full run, writes docs/data/*.json|csv
    python -m sp500_signals.pipeline --dry-run  # compute and print a summary, write nothing
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .config import CONFIG, Config
from .extract import fetch_history, validate
from .signals import generate_signals, position_series
from .transform import add_indicators

log = logging.getLogger("sp500_signals")


def build(df: pd.DataFrame, cfg: Config) -> dict:
    """Pure transformation: raw bars in, publishable payload out (no I/O, easy to test)."""
    df = add_indicators(df, cfg.rsi_period, cfg.sma_fast, cfg.sma_slow)
    window_start = df.index[-1] - pd.DateOffset(years=cfg.display_years)
    view = df.loc[df.index >= window_start]

    signals = generate_signals(view, cfg.rsi_oversold, cfg.rsi_overbought)
    position = position_series(view.index, signals)
    stats = run_backtest(view["close"], position, signals, cfg.risk_free_rate)

    def r(x, n=2):
        return None if pd.isna(x) else round(float(x), n)

    return {
        "meta": {
            "ticker": cfg.ticker,
            "name": "S&P 500",
            "source": "Yahoo Finance via yfinance",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "start": view.index[0].date().isoformat(),
            "end": view.index[-1].date().isoformat(),
            "rows": len(view),
            "strategy": {
                "name": "RSI mean reversion",
                "rsi_period": cfg.rsi_period,
                "entry_rule": f"RSI({cfg.rsi_period}) crosses above {cfg.rsi_oversold:g}",
                "exit_rule": f"RSI({cfg.rsi_period}) crosses below {cfg.rsi_overbought:g}",
            },
            "disclaimer": "Educational data-engineering demo. Not investment advice.",
        },
        "series": {
            "date": [d.date().isoformat() for d in view.index],
            "close": [r(v) for v in view["close"]],
            "sma_fast": [r(v) for v in view["sma_fast"]],
            "sma_slow": [r(v) for v in view["sma_slow"]],
            "rsi": [r(v, 1) for v in view["rsi"]],
        },
        "signals": [
            {
                "date": row.date.date().isoformat(),
                "type": row.type,
                "close": r(row.close),
                "rsi": r(row.rsi, 1),
                "reason": row.reason,
            }
            for row in signals.itertuples()
        ],
        "backtest": stats,
    }


def write_outputs(payload: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write to a temp file then rename, so a crashed run never leaves a half-written JSON live.
    target = out_dir / "sp500_signals.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    tmp.replace(target)
    pd.DataFrame(payload["signals"]).to_csv(out_dir / "signals.csv", index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="compute but do not write files")
    parser.add_argument("--out", type=Path, default=CONFIG.output_dir)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    start = date.today() - pd.DateOffset(years=CONFIG.display_years, days=CONFIG.warmup_days)
    raw = fetch_history(CONFIG.ticker, start=start.date())
    df = validate(raw)
    log.info("extracted %d validated rows (%s -> %s)", len(df), df.index[0].date(), df.index[-1].date())

    payload = build(df, CONFIG)
    bt = payload["backtest"]
    log.info(
        "%d signals | strategy %.1f%% vs buy&hold %.1f%% | max DD %.1f%% vs %.1f%%",
        len(payload["signals"]),
        bt["strategy"]["total_return"] * 100,
        bt["buy_and_hold"]["total_return"] * 100,
        bt["strategy"]["max_drawdown"] * 100,
        bt["buy_and_hold"]["max_drawdown"] * 100,
    )
    if not args.dry_run:
        write_outputs(payload, args.out)
        log.info("wrote %s", args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
