"""
Application configuration models for runtime parameter management.

Manages application-level settings like enabled strategies, symbols,
timeframes, confidence thresholds, and risk management parameters.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """
    Application configuration model.

    Represents the complete runtime configuration for the TA Bot application,
    including enabled strategies, trading symbols, timeframes, and risk parameters.
    """

    id: Optional[str] = Field(None, description="Configuration ID")
    enabled_strategies: list[str] = Field(
        ..., description="List of enabled strategy identifiers"
    )
    symbols: list[str] = Field(..., description="List of trading symbols to monitor")
    candle_periods: list[str] = Field(
        ..., description="List of timeframes/candle periods to analyze"
    )
    min_confidence: float = Field(
        ..., description="Minimum confidence threshold for signals"
    )
    max_confidence: float = Field(
        ..., description="Maximum confidence threshold for signals"
    )
    max_positions: int = Field(
        ..., description="Maximum number of concurrent positions"
    )
    position_sizes: list[int] = Field(..., description="Available position sizes")
    version: int = Field(1, description="Configuration version number")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When config was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When config was last updated"
    )
    created_by: str = Field(..., description="Who/what created this config")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "enabled_strategies": [
                    "momentum_pulse",
                    "rsi_extreme_reversal",
                    "bollinger_breakout_signals",
                ],
                "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                "candle_periods": ["5m", "15m", "1h"],
                "min_confidence": 0.6,
                "max_confidence": 0.95,
                "max_positions": 10,
                "position_sizes": [100, 200, 500, 1000],
                "version": 3,
                "created_at": "2025-10-17T10:30:00Z",
                "updated_at": "2025-10-21T14:45:00Z",
                "created_by": "llm_agent_v1",
                "metadata": {
                    "notes": "Optimized for volatile market conditions",
                    "performance": "+15% win rate improvement",
                },
            }
        }


class AppConfigAudit(BaseModel):
    """
    Application configuration audit trail record.

    Tracks all changes to application configuration for compliance
    and performance analysis.
    """

    id: str = Field(..., description="Audit record ID")
    config_id: Optional[str] = Field(None, description="Configuration ID being audited")
    action: Literal["CREATE", "UPDATE", "DELETE"] = Field(
        ..., description="Type of configuration change"
    )
    old_config: Optional[dict[str, Any]] = Field(
        None, description="Previous configuration values"
    )
    new_config: Optional[dict[str, Any]] = Field(
        None, description="New configuration values"
    )
    changed_by: str = Field(..., description="Who/what made the change")
    changed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the change was made"
    )
    reason: Optional[str] = Field(None, description="Reason for the change")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional audit metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "config_id": "507f1f77bcf86cd799439011",
                "action": "UPDATE",
                "old_config": {
                    "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"],
                    "min_confidence": 0.7,
                },
                "new_config": {
                    "enabled_strategies": [
                        "momentum_pulse",
                        "rsi_extreme_reversal",
                        "bollinger_breakout_signals",
                    ],
                    "min_confidence": 0.6,
                },
                "changed_by": "llm_agent_v1",
                "changed_at": "2025-10-21T14:45:00Z",
                "reason": "Adding Bollinger strategy and lowering confidence for more signals",
                "metadata": {"source": "api", "ip_address": "192.168.1.100"},
            }
        }
