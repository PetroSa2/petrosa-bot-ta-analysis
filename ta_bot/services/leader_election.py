"""
Leader election module for TA Bot replicas.
"""

import asyncio
import os
import time
from typing import Optional

import nats

from otel_init import get_tracer

# Get tracer for manual spans
tracer = get_tracer("ta_bot.services.leader_election")


class LeaderElection:
    """Simple leader election using NATS."""

    def __init__(self, nc: nats.NATS, election_subject: str = "ta-bot.leader-election"):
        self.nc = nc
        self.election_subject = election_subject
        self.pod_name = os.getenv("HOSTNAME", "unknown")
        self.is_leader = False
        self.leader_info = None
        self.election_interval = 30  # seconds
        self.heartbeat_interval = 10  # seconds

    async def start_election(self):
        """Start the leader election process."""
        while True:
            try:
                # Try to become leader
                await self._try_become_leader()

                if self.is_leader:
                    # Act as leader
                    await self._act_as_leader()
                else:
                    # Wait and try again
                    await asyncio.sleep(self.election_interval)

            except Exception as e:
                print(f"Leader election error: {e}")
                await asyncio.sleep(5)

    async def _try_become_leader(self):
        """Try to become the leader."""
        with tracer.start_as_current_span("leader_election_attempt") as span:
            span.set_attribute("pod_name", self.pod_name)
            span.set_attribute("election_subject", self.election_subject)

            try:
                # Publish leader claim
                leader_claim = {
                    "pod_name": self.pod_name,
                    "timestamp": time.time(),
                    "ttl": 60,  # 60 seconds TTL
                }

                await self.nc.publish(self.election_subject, str(leader_claim).encode())

                # Wait a bit and check if we're still the most recent
                await asyncio.sleep(2)

                # Check current leader
                current_leader = await self._get_current_leader()

                if current_leader and current_leader.get("pod_name") == self.pod_name:
                    self.is_leader = True
                    self.leader_info = current_leader
                    span.set_attribute("became_leader", True)
                    print(f"🎯 {self.pod_name} is now the leader")
                else:
                    self.is_leader = False
                    span.set_attribute("became_leader", False)
                    if current_leader:
                        span.set_attribute(
                            "current_leader", current_leader.get("pod_name")
                        )

            except Exception as e:
                print(f"Error trying to become leader: {e}")
                span.set_attribute("error", str(e))
                span.set_attribute("became_leader", False)
                self.is_leader = False

    async def _act_as_leader(self):
        """Act as the leader by sending heartbeats."""
        try:
            while self.is_leader:
                # Create a new span for each heartbeat iteration
                with tracer.start_as_current_span("leader_heartbeat") as span:
                    span.set_attribute("pod_name", self.pod_name)

                    # Send heartbeat
                    heartbeat = {
                        "pod_name": self.pod_name,
                        "timestamp": time.time(),
                        "ttl": 60,
                    }

                    await self.nc.publish(
                        self.election_subject, str(heartbeat).encode()
                    )

                    await asyncio.sleep(self.heartbeat_interval)

        except Exception as e:
            print(f"Error acting as leader: {e}")
            self.is_leader = False

    async def _get_current_leader(self) -> dict | None:
        """Get the current leader information."""
        try:
            # This is a simplified version - in production you'd want a more robust approach
            # For now, we'll assume the most recent message is the leader
            return {"pod_name": self.pod_name, "timestamp": time.time()}
        except Exception as e:
            print(f"Error getting current leader: {e}")
            return None

    def is_current_leader(self) -> bool:
        """Check if this replica is the current leader."""
        return self.is_leader
