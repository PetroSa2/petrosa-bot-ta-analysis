"""
Signal data model for trading signals.
"""

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional


class SignalType(str, Enum):
    """Signal types for trading actions"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(str, Enum):
    """Signal strength levels"""

    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    EXTREME = "extreme"


class StrategyMode(str, Enum):
    """Strategy processing modes"""

    DETERMINISTIC = "deterministic"
    ML_LIGHT = "ml_light"
    LLM_REASONING = "llm_reasoning"


class OrderType(str, Enum):
    """Supported order types"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class TimeInForce(str, Enum):
    """Order time in force options"""

    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTX = "GTX"


def sanitize_json_value(value: Any) -> Any:
    """
    Sanitize a value for JSON serialization.
    Converts NaN, Infinity, and -Infinity to None.
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    elif isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [sanitize_json_value(v) for v in value]
    return value


@dataclass
class Signal:
    """Trading signal data model - aligned with Trade Engine format."""

    # Core signal information (required)
    strategy_id: str
    symbol: str
    action: Literal["buy", "sell", "hold", "close"]
    confidence: float
    current_price: float
    price: float

    # Optional fields with defaults
    strategy_mode: StrategyMode = StrategyMode.DETERMINISTIC
    strength: SignalStrength = SignalStrength.MEDIUM
    quantity: float = 0.0
    source: str = "ta_bot"
    strategy: str = ""
    metadata: dict[str, Any] = None
    timeframe: str = "15m"
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.GTC
    position_size_pct: Optional[float] = None
    stop_loss: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_pct: Optional[float] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Set default values after initialization."""
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.strategy:
            self.strategy = self.strategy_id

    def to_dict(self) -> dict[str, Any]:
        """Convert signal to dictionary for API transmission."""
        signal_dict = asdict(self)
        # Convert enums to their values
        signal_dict["strategy_mode"] = self.strategy_mode.value
        signal_dict["strength"] = self.strength.value
        signal_dict["order_type"] = self.order_type.value
        signal_dict["time_in_force"] = self.time_in_force.value

        # CRITICAL FIX: Convert ALL top-level numpy types to native Python types
        # This ensures stop_loss, take_profit, and other numeric fields serialize correctly
        for key, value in list(signal_dict.items()):
            if value is not None and hasattr(value, "item"):  # numpy scalar
                signal_dict[key] = value.item()
            elif value is not None and hasattr(value, "dtype"):  # numpy array/bool
                signal_dict[key] = float(value) if value.dtype != bool else bool(value)

        # Convert numpy types in metadata to native Python types
        if signal_dict.get("metadata"):
            metadata = {}
            for key, value in signal_dict["metadata"].items():
                if hasattr(value, "item"):  # numpy scalar
                    converted_value = value.item()
                elif hasattr(value, "dtype"):  # numpy array/bool
                    converted_value = (
                        bool(value) if value.dtype == bool else float(value)
                    )
                else:
                    converted_value = value

                # Sanitize the value to remove NaN/Inf
                metadata[key] = sanitize_json_value(converted_value)

            signal_dict["metadata"] = metadata

        # Sanitize all fields to ensure no NaN/Inf values
        signal_dict = sanitize_json_value(signal_dict)

        return signal_dict

    def validate(self) -> bool:
        """Validate signal data."""
        if not (0.0 <= self.confidence <= 1.0):
            return False

        if not self.symbol or not self.strategy_id:
            return False

        if self.current_price <= 0 or self.price <= 0:
            return False

        return True
