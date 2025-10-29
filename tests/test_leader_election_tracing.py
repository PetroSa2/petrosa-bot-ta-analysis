"""
Tests for OpenTelemetry tracing in leader election module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.services.leader_election import LeaderElection


class TestLeaderElectionTracing:
    """Test cases for OpenTelemetry tracing in LeaderElection."""

    @pytest.fixture
    def mock_nats(self):
        """Create a mock NATS connection."""
        mock_nc = AsyncMock()
        mock_nc.publish = AsyncMock()
        return mock_nc

    @pytest.mark.asyncio
    @patch("ta_bot.services.leader_election.tracer")
    async def test_try_become_leader_creates_span(self, mock_tracer, mock_nats):
        """Test that _try_become_leader creates span with attributes."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        election = LeaderElection(mock_nats)

        # Mock _get_current_leader to return this pod as leader
        election._get_current_leader = AsyncMock(
            return_value={"pod_name": election.pod_name}
        )

        await election._try_become_leader()

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once_with(
            "leader_election_attempt"
        )

        # Verify span attributes
        mock_span.set_attribute.assert_any_call("pod_name", election.pod_name)
        mock_span.set_attribute.assert_any_call(
            "election_subject", "ta-bot.leader-election"
        )
        mock_span.set_attribute.assert_any_call("became_leader", True)

    @pytest.mark.asyncio
    @patch("ta_bot.services.leader_election.tracer")
    async def test_try_become_leader_not_elected(self, mock_tracer, mock_nats):
        """Test span attributes when not elected as leader."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        election = LeaderElection(mock_nats)

        # Mock _get_current_leader to return different pod as leader
        election._get_current_leader = AsyncMock(return_value={"pod_name": "other-pod"})

        await election._try_become_leader()

        # Verify not-elected attributes
        mock_span.set_attribute.assert_any_call("became_leader", False)
        mock_span.set_attribute.assert_any_call("current_leader", "other-pod")

    @pytest.mark.asyncio
    @patch("ta_bot.services.leader_election.tracer")
    @patch("ta_bot.services.leader_election.asyncio.sleep", new_callable=AsyncMock)
    async def test_act_as_leader_creates_span_per_heartbeat(
        self, mock_sleep, mock_tracer, mock_nats
    ):
        """Test that _act_as_leader creates a span for each heartbeat."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        election = LeaderElection(mock_nats)
        election.is_leader = True

        # Use a counter to stop after 2 heartbeats
        heartbeat_count = [0]

        async def stop_after_two(*args, **kwargs):
            heartbeat_count[0] += 1
            if heartbeat_count[0] >= 2:
                election.is_leader = False

        mock_sleep.side_effect = stop_after_two

        await election._act_as_leader()

        # Verify span was created for each heartbeat (2 times)
        assert mock_tracer.start_as_current_span.call_count == 2
        mock_tracer.start_as_current_span.assert_called_with("leader_heartbeat")

        # Verify pod_name attribute was set
        assert mock_span.set_attribute.call_count >= 2

    @pytest.mark.asyncio
    @patch("ta_bot.services.leader_election.tracer")
    async def test_try_become_leader_error_sets_span_attribute(
        self, mock_tracer, mock_nats
    ):
        """Test that errors during election are recorded in span."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        election = LeaderElection(mock_nats)

        # Make publish raise an error
        mock_nats.publish.side_effect = Exception("Connection lost")

        await election._try_become_leader()

        # Verify error was recorded in span
        mock_span.set_attribute.assert_any_call("error", "Connection lost")
        mock_span.set_attribute.assert_any_call("became_leader", False)

        # Verify is_leader is False
        assert election.is_leader is False


if __name__ == "__main__":
    pytest.main([__file__])
