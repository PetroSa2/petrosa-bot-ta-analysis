"""
Comprehensive tests for application configuration models.
"""

from datetime import datetime

import pytest

from ta_bot.models.app_config import AppConfig, AppConfigAudit


class TestAppConfig:
    """Test suite for AppConfig model."""

    def test_app_config_creation_with_all_fields(self):
        """Test creating AppConfig with all fields."""
        config = AppConfig(
            id="507f1f77bcf86cd799439011",
            enabled_strategies=["momentum_pulse", "rsi_extreme_reversal"],
            symbols=["BTCUSDT", "ETHUSDT"],
            candle_periods=["5m", "15m"],
            min_confidence=0.6,
            max_confidence=0.95,
            max_positions=10,
            position_sizes=[100, 200, 500],
            version=1,
            created_by="test_user",
        )

        assert config.id == "507f1f77bcf86cd799439011"
        assert len(config.enabled_strategies) == 2
        assert len(config.symbols) == 2
        assert len(config.candle_periods) == 2
        assert config.min_confidence == 0.6
        assert config.max_confidence == 0.95
        assert config.max_positions == 10
        assert len(config.position_sizes) == 3
        assert config.version == 1
        assert config.created_by == "test_user"

    def test_app_config_creation_minimal(self):
        """Test creating AppConfig with minimal required fields."""
        config = AppConfig(
            enabled_strategies=["momentum_pulse"],
            symbols=["BTCUSDT"],
            candle_periods=["15m"],
            min_confidence=0.7,
            max_confidence=0.9,
            max_positions=5,
            position_sizes=[100],
            created_by="system",
        )

        assert config.id is None  # Optional field
        assert len(config.enabled_strategies) == 1
        assert config.version == 1  # Default value
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)
        assert isinstance(config.metadata, dict)

    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        config = AppConfig(
            enabled_strategies=["momentum_pulse"],
            symbols=["BTCUSDT"],
            candle_periods=["15m"],
            min_confidence=0.6,
            max_confidence=0.9,
            max_positions=10,
            position_sizes=[100],
            created_by="test",
        )

        assert config.version == 1
        assert config.metadata == {}
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)

    def test_app_config_json_schema_extra(self):
        """Test that AppConfig has proper JSON schema example."""
        schema = AppConfig.model_config.get("json_schema_extra")
        assert schema is not None
        assert "example" in schema
        assert "enabled_strategies" in schema["example"]

    def test_app_config_with_metadata(self):
        """Test AppConfig with custom metadata."""
        metadata = {
            "notes": "Test config",
            "performance": "+10% improvement",
        }

        config = AppConfig(
            enabled_strategies=["momentum_pulse"],
            symbols=["BTCUSDT"],
            candle_periods=["15m"],
            min_confidence=0.6,
            max_confidence=0.9,
            max_positions=10,
            position_sizes=[100],
            created_by="test",
            metadata=metadata,
        )

        assert config.metadata == metadata
        assert config.metadata["notes"] == "Test config"


class TestAppConfigAudit:
    """Test suite for AppConfigAudit model."""

    def test_app_config_audit_create_action(self):
        """Test creating audit record for CREATE action."""
        audit = AppConfigAudit(
            id="audit123",
            config_id="config123",
            action="CREATE",
            new_config={"enabled_strategies": ["momentum_pulse"]},
            changed_by="test_user",
            reason="Initial setup",
        )

        assert audit.id == "audit123"
        assert audit.config_id == "config123"
        assert audit.action == "CREATE"
        assert audit.old_config is None
        assert audit.new_config is not None
        assert audit.changed_by == "test_user"
        assert audit.reason == "Initial setup"

    def test_app_config_audit_update_action(self):
        """Test creating audit record for UPDATE action."""
        old_config = {"enabled_strategies": ["momentum_pulse"]}
        new_config = {"enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"]}

        audit = AppConfigAudit(
            id="audit123",
            config_id="config123",
            action="UPDATE",
            old_config=old_config,
            new_config=new_config,
            changed_by="test_user",
            reason="Added RSI strategy",
        )

        assert audit.action == "UPDATE"
        assert audit.old_config == old_config
        assert audit.new_config == new_config
        assert audit.reason == "Added RSI strategy"

    def test_app_config_audit_delete_action(self):
        """Test creating audit record for DELETE action."""
        audit = AppConfigAudit(
            id="audit123",
            config_id="config123",
            action="DELETE",
            old_config={"enabled_strategies": ["momentum_pulse"]},
            changed_by="test_user",
            reason="Removing old config",
        )

        assert audit.action == "DELETE"
        assert audit.old_config is not None
        assert audit.new_config is None

    def test_app_config_audit_defaults(self):
        """Test AppConfigAudit default values."""
        audit = AppConfigAudit(
            id="audit123",
            action="CREATE",
            changed_by="test_user",
        )

        assert audit.config_id is None
        assert audit.old_config is None
        assert audit.new_config is None
        assert audit.reason is None
        assert isinstance(audit.changed_at, datetime)
        assert isinstance(audit.metadata, dict)

    def test_app_config_audit_with_metadata(self):
        """Test AppConfigAudit with metadata."""
        metadata = {"source": "api", "ip_address": "192.168.1.100"}

        audit = AppConfigAudit(
            id="audit123",
            action="CREATE",
            changed_by="test_user",
            metadata=metadata,
        )

        assert audit.metadata == metadata
        assert audit.metadata["source"] == "api"

    def test_app_config_audit_json_schema_extra(self):
        """Test that AppConfigAudit has proper JSON schema example."""
        schema = AppConfigAudit.model_config.get("json_schema_extra")
        assert schema is not None
        assert "example" in schema
        assert "action" in schema["example"]
