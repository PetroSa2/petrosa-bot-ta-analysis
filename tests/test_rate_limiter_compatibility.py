from unittest.mock import AsyncMock, MagicMock

import pytest
from petrosa_otel.rate_limiter import ConfigRateLimiter

from ta_bot.db.mongodb_client import MongoDBClient


@pytest.mark.asyncio
async def test_rate_limiter_works_with_mongodbclient_db_alias() -> None:
    mongodb_client = MongoDBClient(use_data_manager=False)

    # Simulate an initialized Motor database handle.
    mongodb_client.database = MagicMock()
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=0)
    mongodb_client.database.__getitem__.return_value = collection

    limiter = ConfigRateLimiter(mongodb_client=mongodb_client, service_name="ta-bot")

    count = await limiter._get_count({})

    assert count == 0
    mongodb_client.database.__getitem__.assert_called_with("config_rate_limits")
