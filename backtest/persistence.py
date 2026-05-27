"""Persistence of CharacterizationArtifact to petrosa-data-manager (AC5 / FR24).

The persister posts the artifact to the data-manager's generic ``/insert``
endpoint under the ``characterization_artifacts`` MongoDB collection so it is
queryable by other services (FR20, FR30, FR62).

Usage::

    from backtest.persistence import ArtifactPersister

    persister = ArtifactPersister()
    ok = persister.persist(artifact)

The persister is intentionally **synchronous** (uses ``asyncio.run`` internally)
so the CLI can call it without converting to async.  Callers that already run
inside an async context should use ``await persister.apersist(artifact)`` instead.

Failures are logged and surfaced as ``False`` return value; they never raise so
a CLI ``--persist`` flag degrades gracefully when data-manager is unreachable.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from backtest.artifact import CharacterizationArtifact

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://petrosa-data-manager:80"
_COLLECTION = "characterization_artifacts"
_DATABASE = "mongodb"


class ArtifactPersister:
    """Post a ``CharacterizationArtifact`` to the data-manager audit trail."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or os.getenv("DATA_MANAGER_URL", _DEFAULT_URL)

    def _build_record(self, artifact: CharacterizationArtifact) -> dict[str, Any]:
        record = artifact.to_dict()
        # Primary key for idempotent re-runs: same strategy+symbol+period+window
        record["_artifact_key"] = (
            f"{artifact.strategy_id}:{artifact.symbol}:{artifact.period}"
            f":{artifact.range_from}:{artifact.range_to}"
        )
        return record

    async def apersist(self, artifact: CharacterizationArtifact) -> bool:
        """Async variant — use this from within an async context."""
        from ta_bot.services.data_manager_client import DataManagerClient

        record = self._build_record(artifact)
        client = DataManagerClient(base_url=self._base_url)
        try:
            await client.connect()
            result = await client._client.insert(
                database=_DATABASE,
                collection=_COLLECTION,
                data=record,
                validate=False,
            )
            inserted = result.get("inserted_count", 0)
            if inserted > 0:
                logger.info(
                    "Persisted artifact for %s/%s to data-manager (%s)",
                    artifact.strategy_id,
                    artifact.symbol,
                    _COLLECTION,
                )
                return True
            logger.warning(
                "data-manager inserted_count=0 for artifact %s/%s",
                artifact.strategy_id,
                artifact.symbol,
            )
            return False
        except Exception:
            logger.exception(
                "Failed to persist artifact for %s/%s to data-manager",
                artifact.strategy_id,
                artifact.symbol,
            )
            return False
        finally:
            await client.disconnect()

    def persist(self, artifact: CharacterizationArtifact) -> bool:
        """Synchronous wrapper — safe to call from the CLI."""
        try:
            return asyncio.run(self.apersist(artifact))
        except RuntimeError:
            # Already inside an event loop; fall back to creating a task
            logger.error(
                "Cannot call ArtifactPersister.persist() from within an async context; "
                "use await apersist() instead."
            )
            return False
