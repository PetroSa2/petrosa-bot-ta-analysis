from unittest.mock import MagicMock

from petrosa_otel.rate_limiter import ConfigRateLimiter

from ta_bot.db.mongodb_client import MongoDBClient


def test_rate_limiter_supports_mongodbclient_database_attr() -> None:
    mongodb_client = MongoDBClient(use_data_manager=False)

    # Simulate an initialized Motor database handle.
    mongodb_client.database = MagicMock()
    expected_collection = MagicMock()
    mongodb_client.database.__getitem__.return_value = expected_collection

    limiter = ConfigRateLimiter(mongodb_client=mongodb_client, service_name="ta-bot")

    assert limiter._get_collection() is expected_collection
