"""
Standard API response models for MCP-friendly communication.

All endpoints return responses wrapped in APIResponse envelope for
consistent structure that's easy for LLM agents to parse.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard response envelope for all API responses.

    MCP-Compatible Structure:
    - success: Boolean indicating if request succeeded
    - data: Response payload (only present on success)
    - error: Error details (only present on failure)
    - metadata: Additional context (pagination, timing, cache status, etc.)
    - timestamp: Response timestamp in ISO-8601 format

    This structure ensures LLM agents can easily parse responses and
    handle both success and error cases consistently.
    """

    success: bool = Field(
        ...,
        description="Whether the request was successful. Check this first to determine if data or error is present.",
    )
    data: Optional[T] = Field(
        None,
        description="Response data (only present when success=true). Contains the actual payload requested.",
    )
    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error details (only present when success=false). Contains code, message, and additional context.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the response: pagination info, timing, cache status, etc.",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp in ISO-8601 format (UTC)",
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "data": {"strategy_id": "rsi_extreme_reversal", "parameters": {}},
                    "metadata": {"cache_hit": True, "response_time_ms": 15},
                    "timestamp": "2025-10-17T14:30:00Z",
                },
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Strategy not found",
                        "details": {"strategy_id": "invalid_strategy"},
                    },
                    "metadata": {},
                    "timestamp": "2025-10-17T14:30:00Z",
                },
            ]
        }


class ErrorDetail(BaseModel):
    """
    Structured error information for machine parsing.

    Provides consistent error format that LLM agents can use to
    understand what went wrong and how to fix it.
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED)",
    )
    message: str = Field(
        ..., description="Human-readable error message explaining what went wrong"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context with specific information about the failure",
    )
    field: Optional[str] = Field(
        None, description="Field name if this is a field-specific validation error"
    )
    suggestion: Optional[str] = Field(
        None, description="Optional suggestion on how to fix the error"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Parameter value out of range",
                "details": {"parameter": "rsi_period", "value": 100, "max": 50},
                "field": "parameters.rsi_period",
                "suggestion": "Use a value between 2 and 50",
            }
        }


class ConfigUpdateRequest(BaseModel):
    """
    Request model for updating strategy configuration parameters.

    Use this to modify how a trading strategy behaves at runtime. Changes take effect
    within 60 seconds due to caching. All changes are audited for tracking.
    """

    parameters: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary of strategy parameters to update. Must match the schema "
            "for the specific strategy. Get valid parameters from GET /api/v1/strategies/{strategy_id}/schema. "
            "Example: {'rsi_period': 14, 'oversold_threshold': 30}"
        ),
    )
    changed_by: str = Field(
        ...,
        description=(
            "Identifier of who/what is making this change (e.g., 'llm_agent_v1', 'manual_user', 'backtester'). "
            "Used for audit trail and tracking performance of configuration changes."
        ),
        min_length=1,
        max_length=100,
    )
    reason: Optional[str] = Field(
        None,
        description=(
            "Optional explanation for why this configuration is being changed. "
            "Helps track the rationale behind parameter adjustments for future analysis."
        ),
    )
    validate_only: bool = Field(
        False,
        description=(
            "If true, validates the parameters against the schema without saving. "
            "Use this for dry-run validation before committing changes."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "parameters": {
                    "rsi_period": 14,
                    "oversold_threshold": 30,
                    "extreme_threshold": 5,
                },
                "changed_by": "llm_agent_v1",
                "reason": "Market volatility adjustment - reducing sensitivity",
                "validate_only": False,
            }
        }


class ConfigResponse(BaseModel):
    """
    Response model containing strategy configuration details.

    Shows the active configuration for a strategy, including where it came from
    (database or defaults) and whether it's symbol-specific or global.
    """

    strategy_id: str = Field(
        ...,
        description="Unique identifier of the strategy (e.g., 'rsi_extreme_reversal')",
    )
    symbol: Optional[str] = Field(
        None,
        description=(
            "Trading symbol if this is a symbol-specific configuration override. "
            "Null means this is a global configuration applied to all symbols."
        ),
    )
    parameters: Dict[str, Any] = Field(
        ..., description="Current parameter values for this strategy configuration"
    )
    version: int = Field(
        ..., description="Configuration version number. Increments with each update."
    )
    source: str = Field(
        ...,
        description=(
            "Source of this configuration: 'mongodb' (primary DB), 'mysql' (fallback DB), "
            "or 'default' (hardcoded defaults, auto-persisted on first use)"
        ),
    )
    is_override: bool = Field(
        ...,
        description=(
            "True if this is a symbol-specific override. False if global configuration. "
            "Symbol-specific configs take precedence over global ones."
        ),
    )
    created_at: str = Field(
        ..., description="ISO-8601 timestamp when this configuration was first created"
    )
    updated_at: str = Field(
        ...,
        description="ISO-8601 timestamp of the most recent update to this configuration",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_id": "rsi_extreme_reversal",
                "symbol": "BTCUSDT",
                "parameters": {
                    "rsi_period": 2,
                    "oversold_threshold": 25,
                    "extreme_threshold": 2,
                    "base_confidence": 0.65,
                },
                "version": 3,
                "source": "mongodb",
                "is_override": True,
                "created_at": "2025-10-17T10:30:00Z",
                "updated_at": "2025-10-17T14:45:00Z",
            }
        }


class StrategyListItem(BaseModel):
    """Summary information for a strategy in the list view."""

    strategy_id: str = Field(..., description="Strategy unique identifier")
    name: str = Field(..., description="Human-readable strategy name")
    description: str = Field(
        ..., description="Brief description of what the strategy does"
    )
    has_global_config: bool = Field(
        ..., description="Whether a global configuration exists for this strategy"
    )
    symbol_overrides: List[str] = Field(
        default_factory=list,
        description="List of symbols that have specific configuration overrides",
    )
    parameter_count: int = Field(
        ..., description="Number of configurable parameters this strategy has"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_id": "rsi_extreme_reversal",
                "name": "RSI Extreme Reversal",
                "description": "Detects extreme RSI conditions for mean reversion",
                "has_global_config": True,
                "symbol_overrides": ["BTCUSDT", "ETHUSDT"],
                "parameter_count": 10,
            }
        }


class ParameterSchemaItem(BaseModel):
    """Schema definition for a single strategy parameter."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Data type: 'int', 'float', 'bool', 'str'")
    description: str = Field(..., description="What this parameter controls")
    default: Any = Field(..., description="Default value if not configured")
    min: Optional[float] = Field(
        None, description="Minimum allowed value (for numeric types)"
    )
    max: Optional[float] = Field(
        None, description="Maximum allowed value (for numeric types)"
    )
    allowed_values: Optional[List[Any]] = Field(
        None, description="List of allowed values (for enum-like parameters)"
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


class AuditTrailItem(BaseModel):
    """Single audit trail entry showing a configuration change."""

    id: str = Field(..., description="Audit record ID")
    strategy_id: str = Field(..., description="Strategy that was modified")
    symbol: Optional[str] = Field(None, description="Symbol (null for global configs)")
    action: str = Field(..., description="Action taken: CREATE, UPDATE, or DELETE")
    old_parameters: Optional[Dict[str, Any]] = Field(
        None, description="Previous parameter values (null for CREATE)"
    )
    new_parameters: Optional[Dict[str, Any]] = Field(
        None, description="New parameter values (null for DELETE)"
    )
    changed_by: str = Field(..., description="Who/what made the change")
    changed_at: str = Field(..., description="ISO-8601 timestamp of change")
    reason: Optional[str] = Field(None, description="Reason for the change")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439012",
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


# -------------------------------------------------------------------------
# Application Configuration Models
# -------------------------------------------------------------------------


class AppConfigUpdateRequest(BaseModel):
    """
    Request model for updating application configuration.

    Use this to modify application-level settings like enabled strategies,
    symbols, timeframes, confidence thresholds, and risk management parameters.
    Changes take effect within 60 seconds due to caching. All changes are audited.
    """

    enabled_strategies: Optional[List[str]] = Field(
        None,
        description=(
            "List of strategy identifiers to enable. Must be non-empty. "
            "Each strategy must exist in the system. "
            "Example: ['momentum_pulse', 'rsi_extreme_reversal']"
        ),
    )
    symbols: Optional[List[str]] = Field(
        None,
        description=(
            "List of trading symbols to monitor. Must be uppercase and valid format. "
            "Example: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']"
        ),
    )
    candle_periods: Optional[List[str]] = Field(
        None,
        description=(
            "List of timeframes to analyze. Must be valid Binance timeframes. "
            "Example: ['5m', '15m', '1h']"
        ),
    )
    min_confidence: Optional[float] = Field(
        None,
        description=(
            "Minimum confidence threshold for signals (0.0 to 1.0). "
            "Must be less than max_confidence. Example: 0.6"
        ),
    )
    max_confidence: Optional[float] = Field(
        None,
        description=(
            "Maximum confidence threshold for signals (0.0 to 1.0). "
            "Must be greater than min_confidence. Example: 0.95"
        ),
    )
    max_positions: Optional[int] = Field(
        None,
        description=(
            "Maximum number of concurrent positions allowed. "
            "Must be at least 1. Example: 10"
        ),
    )
    position_sizes: Optional[List[int]] = Field(
        None,
        description=(
            "Available position sizes (positive integers). "
            "Example: [100, 200, 500, 1000]"
        ),
    )
    changed_by: str = Field(
        ...,
        description=(
            "Identifier of who/what is making this change (e.g., 'llm_agent_v1', 'admin'). "
            "Used for audit trail."
        ),
        min_length=1,
        max_length=100,
    )
    reason: Optional[str] = Field(
        None,
        description=(
            "Optional explanation for why this configuration is being changed. "
            "Helps track the rationale for future analysis."
        ),
    )
    validate_only: bool = Field(
        False,
        description=(
            "If true, validates the configuration without saving. "
            "Use this for dry-run validation."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled_strategies": [
                    "momentum_pulse",
                    "rsi_extreme_reversal",
                    "bollinger_breakout_signals",
                ],
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "candle_periods": ["5m", "15m"],
                "min_confidence": 0.6,
                "max_confidence": 0.9,
                "max_positions": 5,
                "position_sizes": [100, 200, 500],
                "changed_by": "llm_agent_v1",
                "reason": "Optimizing for volatile market conditions",
                "validate_only": False,
            }
        }


class AppConfigResponse(BaseModel):
    """
    Response model containing application configuration details.

    Shows the active application-level configuration including all runtime settings.
    """

    enabled_strategies: List[str] = Field(
        ..., description="List of currently enabled strategies"
    )
    symbols: List[str] = Field(
        ..., description="List of trading symbols being monitored"
    )
    candle_periods: List[str] = Field(
        ..., description="List of timeframes being analyzed"
    )
    min_confidence: float = Field(..., description="Minimum confidence threshold")
    max_confidence: float = Field(..., description="Maximum confidence threshold")
    max_positions: int = Field(..., description="Maximum concurrent positions allowed")
    position_sizes: List[int] = Field(..., description="Available position sizes")
    version: int = Field(
        ..., description="Configuration version number. Increments with each update."
    )
    source: str = Field(
        ...,
        description=(
            "Source of this configuration: 'mongodb' (primary DB), 'mysql' (fallback DB), "
            "or 'default' (startup defaults)"
        ),
    )
    created_at: str = Field(
        ..., description="ISO-8601 timestamp when configuration was first created"
    )
    updated_at: str = Field(
        ..., description="ISO-8601 timestamp of the most recent update"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
                "source": "mongodb",
                "created_at": "2025-10-17T10:30:00Z",
                "updated_at": "2025-10-21T14:45:00Z",
            }
        }


class AppAuditTrailItem(BaseModel):
    """Single audit trail entry showing an application configuration change."""

    id: str = Field(..., description="Audit record ID")
    action: str = Field(..., description="Action taken: CREATE, UPDATE, or DELETE")
    old_config: Optional[Dict[str, Any]] = Field(
        None, description="Previous configuration values (null for CREATE)"
    )
    new_config: Optional[Dict[str, Any]] = Field(
        None, description="New configuration values (null for DELETE)"
    )
    changed_by: str = Field(..., description="Who/what made the change")
    changed_at: str = Field(..., description="ISO-8601 timestamp of change")
    reason: Optional[str] = Field(None, description="Reason for the change")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "action": "UPDATE",
                "old_config": {
                    "enabled_strategies": ["momentum_pulse"],
                    "min_confidence": 0.7,
                },
                "new_config": {
                    "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"],
                    "min_confidence": 0.6,
                },
                "changed_by": "llm_agent_v1",
                "changed_at": "2025-10-21T14:45:00Z",
                "reason": "Adding RSI strategy and lowering confidence for more signals",
            }
        }
