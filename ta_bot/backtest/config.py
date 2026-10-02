"""Validated defaults for the trade simulator."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BacktestConfig:
    fee_bp_per_side: Decimal = Decimal("4")
    slippage_bp: Decimal = Decimal("0")
    funding_bp: Decimal = Decimal("0")
    notional: Decimal = Decimal("1000")
    time_stop_bars: int = 0

    def __post_init__(self) -> None:
        for name in ("fee_bp_per_side", "slippage_bp", "funding_bp", "notional"):
            value = Decimal(getattr(self, name))
            if value < 0 or (name == "notional" and value == 0):
                raise ValueError(f"{name} must be positive or zero")
        if self.time_stop_bars < 0:
            raise ValueError("time_stop_bars must be >= 0")

    def as_dict(self) -> dict[str, str | int]:
        return {
            "fee_bp_per_side": str(self.fee_bp_per_side),
            "slippage_bp": str(self.slippage_bp),
            "funding_bp": str(self.funding_bp),
            "notional": str(self.notional),
            "sizing_convention": "fixed notional",
            "time_stop_bars": self.time_stop_bars,
            "entry_rule": "next bar open",
            "funding_rule": "flat charge at 00:00, 08:00, 16:00 UTC",
        }
