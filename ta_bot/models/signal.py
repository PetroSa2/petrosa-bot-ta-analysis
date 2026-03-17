"""
Standardized Signal data model for trading signals.
Aligned with petrosa-cio contracts.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SignalType(StrEnum):
    """Signal types for trading actions"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(StrEnum):
    """Signal strength levels"""

    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    EXTREME = "extreme"


class StrategyMode(StrEnum):
    """Strategy processing modes"""

    DETERMINISTIC = "deterministic"
    ML_LIGHT = "ml_light"
    LLM_REASONING = "llm_reasoning"


class OrderType(StrEnum):
    """Supported order types"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class TimeInForce(StrEnum):
    """Order time in force options"""

    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    GTX = "GTX"


class Signal(BaseModel):
    """Enhanced trading signal aligned with Trade Engine format."""

    # Core signal information
    strategy_id: str = Field(..., description="Unique identifier for the strategy")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    action: Literal["buy", "sell", "hold", "close"] = Field(
        ..., description="Trading action"
    )
    confidence: float = Field(..., ge=0, le=1, description="Signal confidence (0-1)")
    current_price: float = Field(..., description="Current market price")
    price: float = Field(..., description="Signal price/execution price")

    # Optional fields with defaults
    strategy_mode: StrategyMode = Field(
        StrategyMode.DETERMINISTIC, description="Processing mode"
    )
    strength: SignalStrength = Field(
        SignalStrength.MEDIUM, description="Signal strength level"
    )
    quantity: float = Field(0.0, description="Signal quantity")
    source: str = Field("ta_bot", description="Signal source")
    strategy: str = Field("", description="Strategy name")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    timeframe: str = Field("15m", description="Timeframe")
    order_type: OrderType = Field(OrderType.MARKET, description="Order type")
    time_in_force: TimeInForce = Field(TimeInForce.GTC, description="Time in force")
    position_size_pct: float | None = Field(None, ge=0, le=1)
    stop_loss: float | None = Field(None, description="Stop loss price")
    stop_loss_pct: float | None = Field(None, ge=0, le=1)
    take_profit: float | None = Field(None, description="Take profit price")
    take_profit_pct: float | None = Field(None, ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Add legacy/compatibility fields
    signal_id: str | None = Field(None, description="Compatibility with contracts")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> datetime:
        """Ensure timestamp is valid datetime."""
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return datetime.utcnow()
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v or datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert signal to dictionary for backward compatibility."""
        # Use model_dump for Pydantic V2
        data = self.model_dump()

        # Convert datetime to ISO string
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()

        # Ensure strategy is set if empty
        if not data.get("strategy"):
            data["strategy"] = self.strategy_id

        return data

    def validate_signal(self, strict_risk: bool = False) -> bool:
        """
        Validate signal data.
        Note: Renamed from validate() to avoid conflict with Pydantic's internal validate.
        """
        if self.current_price <= 0 or self.price <= 0:
            return False

        if strict_risk and self.action in ["buy", "sell"]:
            if self.stop_loss is None or self.take_profit is None:
                return False
            if not (self.stop_loss > 0 and self.take_profit > 0):
                return False

        return True

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "protected_namespaces": (),
    }
