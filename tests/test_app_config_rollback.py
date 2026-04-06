"""
Unit tests for application configuration rollback functionality.
"""

from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc  # noqa: UP017
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.models.app_config import AppConfig, AppConfigAudit
from ta_bot.services.app_config_manager import AppConfigManager


@pytest.fixture
def mock_mongodb_client():
    client = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def config_manager(mock_mongodb_client):
    return AppConfigManager(mongodb_client=mock_mongodb_client, cache_ttl_seconds=60)


@pytest.fixture
def sample_history():
    return [
        AppConfigAudit(
            id="audit_3",
            action="UPDATE",
            old_config={"version": 2, "enabled_strategies": ["s1"]},
            new_config={"version": 3, "enabled_strategies": ["s1", "s2"]},
            changed_by="user1",
            changed_at=datetime.now(UTC),
        ),
        AppConfigAudit(
            id="audit_2",
            action="UPDATE",
            old_config={"version": 1, "enabled_strategies": []},
            new_config={"version": 2, "enabled_strategies": ["s1"]},
            changed_by="user1",
            changed_at=datetime.now(UTC),
        ),
        AppConfigAudit(
            id="audit_1",
            action="CREATE",
            new_config={"version": 1, "enabled_strategies": []},
            changed_by="user1",
            changed_at=datetime.now(UTC),
        ),
    ]


@pytest.mark.asyncio
class TestAppConfigRollback:
    async def test_get_previous_config(self, config_manager, sample_history):
        """Test getting the immediately preceding configuration."""
        with patch.object(
            config_manager, "get_audit_trail", return_value=sample_history
        ):
            prev_config = await config_manager.get_previous_config()
            assert prev_config is not None
            assert prev_config["version"] == 2
            assert prev_config["enabled_strategies"] == ["s1"]

    async def test_get_config_by_version(self, config_manager, sample_history):
        """Test getting a specific version from history."""
        with patch.object(
            config_manager, "get_audit_trail", return_value=sample_history
        ):
            config = await config_manager.get_config_by_version(1)
            assert config is not None
            assert config["version"] == 1
            assert config["enabled_strategies"] == []

            # Version not in history
            config = await config_manager.get_config_by_version(99)
            assert config is None

    async def test_get_config_by_id(self, config_manager, sample_history):
        """Test getting configuration by audit ID."""
        with patch.object(
            config_manager, "get_audit_trail", return_value=sample_history
        ):
            config = await config_manager.get_config_by_id("audit_2")
            assert config is not None
            assert config["version"] == 2

            # ID not in history
            config = await config_manager.get_config_by_id("non_existent")
            assert config is None

    async def test_rollback_to_previous_success(self, config_manager, sample_history):
        """Test successful rollback to previous version."""
        # 1. Setup mocks
        with (
            patch.object(
                config_manager, "get_audit_trail", return_value=sample_history
            ),
            patch.object(
                config_manager, "set_config", new_callable=AsyncMock
            ) as mock_set_config,
        ):
            mock_set_config.return_value = (True, MagicMock(spec=AppConfig), [])

            # 2. Execute rollback
            success, config, errors = await config_manager.rollback_config(
                changed_by="admin", reason="Testing rollback"
            )

            # 3. Verify
            assert success is True
            assert len(errors) == 0
            # CRITICAL: Verify set_config was called with 'config=' parameter
            mock_set_config.assert_called_once()
            args, kwargs = mock_set_config.call_args
            assert "config" in kwargs
            assert kwargs["config"]["version"] == 2
            assert kwargs["changed_by"] == "admin"

    async def test_rollback_to_version_success(self, config_manager, sample_history):
        """Test successful rollback to a specific version."""
        with (
            patch.object(
                config_manager, "get_audit_trail", return_value=sample_history
            ),
            patch.object(
                config_manager, "set_config", new_callable=AsyncMock
            ) as mock_set_config,
        ):
            mock_set_config.return_value = (True, MagicMock(spec=AppConfig), [])

            success, config, errors = await config_manager.rollback_config(
                changed_by="admin", target_version=1
            )

            assert success is True
            kwargs = mock_set_config.call_args[1]
            assert kwargs["config"]["version"] == 1

    async def test_rollback_to_id_success(self, config_manager, sample_history):
        """Test successful rollback to a specific audit ID."""
        with (
            patch.object(
                config_manager, "get_audit_trail", return_value=sample_history
            ),
            patch.object(
                config_manager, "set_config", new_callable=AsyncMock
            ) as mock_set_config,
        ):
            mock_set_config.return_value = (True, MagicMock(spec=AppConfig), [])

            success, config, errors = await config_manager.rollback_config(
                changed_by="admin", rollback_id="audit_1"
            )

            assert success is True
            kwargs = mock_set_config.call_args[1]
            assert kwargs["config"]["version"] == 1

    async def test_rollback_no_history_error(self, config_manager):
        """Test error when no history exists for rollback."""
        with patch.object(config_manager, "get_audit_trail", return_value=[]):
            success, config, errors = await config_manager.rollback_config(
                changed_by="admin"
            )

            assert success is False
            assert "No previous configuration found" in errors[0]

    async def test_rollback_invalid_version_error(self, config_manager):
        """Test error when version < 1 is passed."""
        success, config, errors = await config_manager.rollback_config(
            changed_by="admin", target_version=0
        )

        assert success is False
        assert "Invalid version number" in errors[0]

    async def test_rollback_version_not_found_error(
        self, config_manager, sample_history
    ):
        """Test error when target version is not found."""
        with patch.object(
            config_manager, "get_audit_trail", return_value=sample_history
        ):
            success, config, errors = await config_manager.rollback_config(
                changed_by="admin", target_version=99
            )

            assert success is False
            assert "version 99 not found" in errors[0]
