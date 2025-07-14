"""
Signal data model for trading signals.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum


class SignalType(Enum):
    """Signal types."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Signal:
    """Trading signal data model."""

    symbol: str
    period: str
    signal: SignalType
    confidence: float
    strategy: str
    metadata: Dict[str, Any]
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to dictionary for API transmission."""
        signal_dict = asdict(self)
        signal_dict["signal"] = self.signal.value
        return signal_dict

    def validate(self) -> bool:
        """Validate signal data."""
        if not (0.0 <= self.confidence <= 1.0):
            return False

        if not self.symbol or not self.period or not self.strategy:
            return False

        return True
