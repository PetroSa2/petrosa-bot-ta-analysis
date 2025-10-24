"""
Strategy configuration models for runtime parameter management.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    """
    Strategy configuration model.

    Represents a complete configuration for a strategy,
    either global (applied to all symbols) or symbol-specific.
    """

    id: Optional[str] = Field(None, description="Configuration ID")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: Optional[str] = Field(
        None, description="Trading symbol (None for global configs)"
    )
    parameters: dict[str, Any] = Field(
        ..., description="Strategy parameters as key-value pairs"
    )
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
                "strategy_id": "rsi_extreme_reversal",
                "symbol": "BTCUSDT",
                "parameters": {
                    "rsi_period": 2,
                    "oversold_threshold": 25,
                    "extreme_threshold": 2,
                },
                "version": 3,
                "created_at": "2025-10-17T10:30:00Z",
                "updated_at": "2025-10-17T14:45:00Z",
                "created_by": "llm_agent_v1",
                "metadata": {
                    "notes": "Adjusted for volatile market",
                    "performance": "+12% win rate",
                },
            }
        }


class StrategyConfigAudit(BaseModel):
    """
    Audit trail record for configuration changes.

    Tracks who changed what, when, and why for full accountability.
    """

    id: Optional[str] = Field(None, description="Audit record ID")
    config_id: Optional[str] = Field(
        None, description="Configuration ID that was changed"
    )
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: Optional[str] = Field(None, description="Symbol (None for global)")
    action: Literal["CREATE", "UPDATE", "DELETE"] = Field(
        ..., description="Type of change made"
    )
    old_parameters: Optional[dict[str, Any]] = Field(
        None, description="Previous parameter values"
    )
    new_parameters: Optional[dict[str, Any]] = Field(
        None, description="New parameter values"
    )
    changed_by: str = Field(..., description="Who/what made the change")
    changed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the change occurred"
    )
    reason: Optional[str] = Field(None, description="Reason for the change")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "config_id": "507f1f77bcf86cd799439011",
                "strategy_id": "rsi_extreme_reversal",
                "symbol": "BTCUSDT",
                "action": "UPDATE",
                "old_parameters": {"oversold_threshold": 30},
                "new_parameters": {"oversold_threshold": 25},
                "changed_by": "llm_agent_v1",
                "changed_at": "2025-10-17T14:45:00Z",
                "reason": "Market volatility adjustment",
            }
        }


class ParameterSchema(BaseModel):
    """
    Schema definition for a strategy parameter.

    Describes type, constraints, and purpose of a configuration parameter.
    """

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Data type (int, float, bool, str)")
    description: str = Field(..., description="What this parameter controls")
    default: Any = Field(..., description="Default value")
    min: Optional[float] = Field(None, description="Minimum value (for numeric)")
    max: Optional[float] = Field(None, description="Maximum value (for numeric)")
    allowed_values: Optional[list[Any]] = Field(
        None, description="Allowed values (for enums)"
    )
    example: Any = Field(..., description="Example valid value")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "rsi_period",
                "type": "int",
                "description": "RSI calculation period",
                "default": 2,
                "min": 2,
                "max": 50,
                "example": 14,
            }
        }


class StrategyInfo(BaseModel):
    """
    Strategy information model for listing strategies.
    """

    strategy_id: str = Field(..., description="Strategy identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Strategy description")
    has_global_config: bool = Field(False, description="Whether global config exists")
    symbol_overrides: list[str] = Field(
        default_factory=list, description="Symbols with overrides"
    )
    parameter_count: int = Field(0, description="Number of parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_id": "rsi_extreme_reversal",
                "name": "RSI Extreme Reversal",
                "description": "Detects extreme RSI conditions for reversals",
                "has_global_config": True,
                "symbol_overrides": ["BTCUSDT", "ETHUSDT"],
                "parameter_count": 7,
            }
        }


class ConfigSource(BaseModel):
    """
    Configuration source metadata.

    Indicates where the configuration was loaded from.
    """

    source: Literal["mongodb", "mysql", "default"] = Field(
        ..., description="Source of configuration"
    )
    is_override: bool = Field(
        False, description="Whether this is a symbol-specific override"
    )
    cache_hit: bool = Field(False, description="Whether this was served from cache")
    load_time_ms: Optional[float] = Field(None, description="Time taken to load config")
