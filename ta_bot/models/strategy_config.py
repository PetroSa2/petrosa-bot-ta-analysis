"""
Strategy configuration models for runtime parameter management.
"""

from datetime import datetime
from enum import Enum

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrategyConfig(BaseModel):
    """
    Strategy configuration model.

    Represents a complete configuration for a strategy,
    either global (applied to all symbols) or symbol-specific.
    """

    id: str | None = Field(None, description="Configuration ID")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str | None = Field(
        None, description="Trading symbol (None for global configs)"
    )
    parameters: dict[str, Any] = Field(
        ..., description="Strategy parameters as key-value pairs"
    )
    version: int = Field(1, description="Configuration version number")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When config was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When config was last updated",
    )
    created_by: str = Field(..., description="Who/what created this config")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class StrategyConfigAudit(BaseModel):
    """
    Audit trail record for configuration changes.

    Tracks who changed what, when, and why for full accountability.
    """

    id: str | None = Field(None, description="Audit record ID")
    config_id: str | None = Field(None, description="Configuration ID that was changed")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str | None = Field(None, description="Symbol (None for global)")
    action: Literal["CREATE", "UPDATE", "DELETE"] = Field(
        ..., description="Type of change made"
    )
    old_parameters: dict[str, Any] | None = Field(
        None, description="Previous parameter values"
    )
    new_parameters: dict[str, Any] | None = Field(
        None, description="New parameter values"
    )
    changed_by: str = Field(..., description="Who/what made the change")
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the change occurred",
    )
    reason: str | None = Field(None, description="Reason for the change")

    model_config = ConfigDict(
        json_schema_extra={
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
    )


class ParameterSchema(BaseModel):
    """
    Schema definition for a strategy parameter.

    Describes type, constraints, and purpose of a configuration parameter.
    """

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Data type (int, float, bool, str)")
    description: str = Field(..., description="What this parameter controls")
    default: Any = Field(..., description="Default value")
    min: float | None = Field(None, description="Minimum value (for numeric)")
    max: float | None = Field(None, description="Maximum value (for numeric)")
    allowed_values: list[Any] | None = Field(
        None, description="Allowed values (for enums)"
    )
    example: Any = Field(..., description="Example valid value")

    model_config = ConfigDict(
        json_schema_extra={
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
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "strategy_id": "rsi_extreme_reversal",
                "name": "RSI Extreme Reversal",
                "description": "Detects extreme RSI conditions for reversals",
                "has_global_config": True,
                "symbol_overrides": ["BTCUSDT", "ETHUSDT"],
                "parameter_count": 7,
            }
        }
    )


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
    load_time_ms: float | None = Field(None, description="Time taken to load config")


class StrategyLifecycleState(str, Enum):
    """Strategy lifecycle state machine states (AC1 of FR9)."""

    REGISTERED = "registered"
    BACKTESTED = "backtested"
    ADMITTED = "admitted"
    LIVE_TRIAL = "live_trial"
    GRADUATED = "graduated"
    DEMOTED = "demoted"
    RETIRED = "retired"


# Valid state transitions for the lifecycle state machine
VALID_LIFECYCLE_TRANSITIONS: dict[
    StrategyLifecycleState, list[StrategyLifecycleState]
] = {
    StrategyLifecycleState.REGISTERED: [
        StrategyLifecycleState.BACKTESTED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.BACKTESTED: [
        StrategyLifecycleState.ADMITTED,
        StrategyLifecycleState.REGISTERED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.ADMITTED: [
        StrategyLifecycleState.LIVE_TRIAL,
        StrategyLifecycleState.DEMOTED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.LIVE_TRIAL: [
        StrategyLifecycleState.GRADUATED,
        StrategyLifecycleState.DEMOTED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.GRADUATED: [
        StrategyLifecycleState.DEMOTED,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.DEMOTED: [
        StrategyLifecycleState.ADMITTED,
        StrategyLifecycleState.LIVE_TRIAL,
        StrategyLifecycleState.RETIRED,
    ],
    StrategyLifecycleState.RETIRED: [
        StrategyLifecycleState.REGISTERED,
    ],
}


class StrategyLifecycleEvent(BaseModel):
    """
    A single state transition event in a strategy's lifecycle (AC2 of FR9).

    Persisted alongside StrategyConfigAudit; each transition records the
    CIO-side decision_id as a join key for cross-service timeline merging.
    """

    id: str | None = Field(None, description="Event record ID (set by DB on insert)")
    strategy_id: str = Field(..., description="Strategy identifier")
    from_state: StrategyLifecycleState | None = Field(
        None, description="Previous state (None for initial registration)"
    )
    to_state: StrategyLifecycleState = Field(
        ..., description="New state after transition"
    )
    transitioned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the transition occurred",
    )
    transitioned_by: str = Field(
        ...,
        description="Actor that triggered the transition (e.g., 'cio_agent', 'operator')",
    )
    decision_id: str | None = Field(
        None,
        description="CIO-side decision_id join key; enables cross-service timeline merging via data-manager LifecycleRepository",
    )
    reasoning_context: str | None = Field(
        None, description="Why this transition occurred"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439020",
                "strategy_id": "rsi_extreme_reversal",
                "from_state": "admitted",
                "to_state": "live_trial",
                "transitioned_at": "2026-05-27T10:00:00Z",
                "transitioned_by": "cio_agent",
                "decision_id": "dec_abc123",
                "reasoning_context": "Passed 30-day paper-trading gate with Sharpe > 1.2",
            }
        }
    )
