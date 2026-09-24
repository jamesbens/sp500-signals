"""Pipeline configuration. All strategy parameters live here so a run is fully reproducible."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    ticker: str = "^GSPC"
    display_years: int = 5
    # Extra history pulled before the display window so the 200-day SMA is warm on day one.
    warmup_days: int = 400
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    sma_fast: int = 50
    sma_slow: int = 200
    risk_free_rate: float = 0.0
    output_dir: Path = Path("docs/data")


CONFIG = Config()
