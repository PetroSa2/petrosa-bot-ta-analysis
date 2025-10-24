"""
MySQL client for fetching candle data and persisting signals.

This client now supports both direct MySQL connections and Data Manager API
for data access. Data Manager is the recommended approach for new deployments.
"""

import json
import logging
import math
import os
from typing import Any, Dict, List
from urllib.parse import urlparse

import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

# Import Data Manager client
try:
    from .data_manager_client import DataManagerClient

    DATA_MANAGER_AVAILABLE = True
except ImportError:
    DATA_MANAGER_AVAILABLE = False
    DataManagerClient = None

logger = logging.getLogger(__name__)


class MySQLClient:
    """
    MySQL client for database operations.

    Supports both direct MySQL connections and Data Manager API.
    Data Manager is the recommended approach for new deployments.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int = 3306,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        uri: str | None = None,
        use_data_manager: bool = True,
    ):
        """
        Initialize MySQL client.

        Args:
            use_data_manager: If True, use Data Manager API instead of direct MySQL
        """
        self.use_data_manager = use_data_manager and DATA_MANAGER_AVAILABLE

        if self.use_data_manager:
            # Initialize Data Manager client
            self.data_manager_client = DataManagerClient()
            self.connection = None  # No direct MySQL connection needed
            logger.info("Using Data Manager for data access")
            return

        # Fallback to direct MySQL connection
        logger.info("Using direct MySQL connection")

        # Try to get URI from environment first
        mysql_uri = os.getenv("MYSQL_URI")

        if mysql_uri:
            # Parse the URI - handle mysql+pymysql:// protocol
            if mysql_uri.startswith("mysql+pymysql://"):
                # Remove the mysql+pymysql:// prefix for parsing
                uri_for_parsing = mysql_uri.replace("mysql+pymysql://", "mysql://")
            else:
                uri_for_parsing = mysql_uri

            parsed_uri = urlparse(uri_for_parsing)

            self.host: str = parsed_uri.hostname or "localhost"
            self.port: int = parsed_uri.port or 3306
            self.user: str = parsed_uri.username or "root"
            # URL decode the password to handle special characters
            self.password: str | None = parsed_uri.password
            if self.password and "%" in self.password:
                from urllib.parse import unquote

                self.password = unquote(self.password)
            # Handle URL encoding in database name
            self.database: str = parsed_uri.path.lstrip("/")
            if "%" in self.database:
                from urllib.parse import unquote

                self.database = unquote(self.database)
            logger.info("MySQL URI parsed successfully")
        else:
            # Use individual parameters
            self.host = (
                host or os.getenv("MYSQL_HOST", "mysql-server")
            ) or "mysql-server"
            self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
            self.user = (user or os.getenv("MYSQL_USER", "petrosa")) or "petrosa"
            self.password = password or os.getenv("MYSQL_PASSWORD", "petrosa")
            self.database = (
                database or os.getenv("MYSQL_DATABASE", "petrosa")
            ) or "petrosa"

        self.connection: Any = None

    async def connect(self):
        """Connect to MySQL database or Data Manager."""
        if self.use_data_manager:
            await self.data_manager_client.connect()
        else:
            try:
                logger.info("Attempting to connect to MySQL...")

                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    cursorclass=DictCursor,
                    autocommit=True,
                    connect_timeout=30,
                    read_timeout=30,
                    write_timeout=30,
                    charset="utf8mb4",
                )
                logger.info("Connected to MySQL successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MySQL: {e}")
                raise

    async def disconnect(self):
        """Disconnect from MySQL database or Data Manager."""
        if self.use_data_manager:
            await self.data_manager_client.disconnect()
        else:
            if self.connection:
                self.connection.close()
                logger.info("Disconnected from MySQL")

    async def fetch_candles(
        self, symbol: str, period: str, limit: int = 100
    ) -> pd.DataFrame:
        """Fetch candle data from MySQL or Data Manager."""
        if self.use_data_manager:
            return await self.data_manager_client.fetch_candles(symbol, period, limit)

        if not self.connection:
            logger.error("Not connected to MySQL")
            return pd.DataFrame()

        try:
            # Check if connection is still alive
            try:
                self.connection.ping(reconnect=True)
            except Exception as e:
                logger.warning(f"Connection lost, reconnecting: {e}")
                await self.connect()

            # Map period to table name
            period_mapping = {
                "1m": "klines_m1",
                "5m": "klines_m5",
                "15m": "klines_m15",
                "30m": "klines_m30",
                "1h": "klines_h1",
                "4h": "klines_h4",
                "1d": "klines_d1",
            }

            table_name = period_mapping.get(period)
            if not table_name:
                logger.error(f"Unsupported period: {period}")
                return pd.DataFrame()

            # Build SQL query
            sql = f"""
                SELECT timestamp, open_price as open, high_price as high, low_price as low, close_price as close, volume
                FROM {table_name}
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """

            with self.connection.cursor() as cursor:
                cursor.execute(sql, (symbol, limit))
                rows = cursor.fetchall()

                if not rows:
                    logger.warning(
                        f"No data found for {symbol} {period} in table {table_name}"
                    )
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(rows)
                df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                # Convert Decimal columns to float for pandas calculations
                numeric_columns = ["open", "high", "low", "close", "volume"]
                for col in numeric_columns:
                    df[col] = df[col].astype(float)
                df = df.sort_values("timestamp").reset_index(drop=True)

                return df

        except Exception as e:
            logger.error(f"Error fetching candles for {symbol} {period}: {e}")
            # Try to reconnect on error
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            return pd.DataFrame()

    def _deep_sanitize_for_json(self, obj: Any) -> Any:
        """
        Recursively sanitize an object for JSON serialization.
        Converts NaN, Infinity, and -Infinity to None.
        """
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, dict):
            return {k: self._deep_sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._deep_sanitize_for_json(v) for v in obj]
        else:
            return obj

    async def persist_signal(self, signal_data: dict[str, Any]) -> bool:
        """Persist a single signal to MySQL or Data Manager."""
        if self.use_data_manager:
            return await self.data_manager_client.persist_signal(signal_data)

        if not self.connection:
            logger.error("Not connected to MySQL")
            return False

        try:
            # Check if connection is still alive
            try:
                self.connection.ping(reconnect=True)
            except Exception as e:
                logger.warning(f"Connection lost, reconnecting: {e}")
                await self.connect()

            sql = """
                INSERT INTO signals (symbol, timeframe, period, signal_type, confidence, strategy, metadata, timestamp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            # Get metadata and ALWAYS sanitize for JSON
            metadata = signal_data.get("metadata", {})

            # Pre-sanitize to remove NaN/Inf values BEFORE json.dumps
            sanitized_metadata = self._deep_sanitize_for_json(metadata)

            try:
                metadata_json = json.dumps(sanitized_metadata, allow_nan=False)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize even after sanitization: {e}")
                # Fallback: convert everything to strings
                metadata_json = json.dumps(
                    {k: str(v) for k, v in sanitized_metadata.items()}
                )

            # Map new field names to old database columns
            signal_type = signal_data.get(
                "action", signal_data.get("signal_type", "hold")
            )
            strategy = signal_data.get(
                "strategy", signal_data.get("strategy_id", "unknown")
            )
            timeframe = signal_data.get("timeframe", "15m")

            with self.connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        signal_data["symbol"],
                        timeframe,
                        timeframe,  # period column (legacy)
                        signal_type,
                        signal_data["confidence"],
                        strategy,
                        metadata_json,
                        signal_data["timestamp"],
                    ),
                )

            logger.info(
                f"Persisted signal for {signal_data['symbol']} {signal_data['timeframe']}"
            )
            return True

        except Exception as e:
            logger.error(f"Error persisting signal: {e}")
            # Try to reconnect on error
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            return False

    async def persist_signals_batch(self, signals: list[dict[str, Any]]) -> bool:
        """Persist multiple signals to MySQL or Data Manager in a batch."""
        if self.use_data_manager:
            return await self.data_manager_client.persist_signals_batch(signals)

        if not self.connection:
            logger.error("Not connected to MySQL")
            return False

        if not signals:
            logger.warning("No signals to persist")
            return True

        try:
            # Check if connection is still alive
            try:
                self.connection.ping(reconnect=True)
            except Exception as e:
                logger.warning(f"Connection lost, reconnecting: {e}")
                await self.connect()

            sql = """
                INSERT INTO signals (symbol, timeframe, period, signal_type, confidence, strategy, metadata, timestamp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            values = []
            for idx, signal_data in enumerate(signals):
                # Get metadata and ALWAYS sanitize it before JSON serialization
                metadata = signal_data.get("metadata", {})

                # Pre-sanitize to remove NaN/Inf values BEFORE json.dumps
                sanitized_metadata = self._deep_sanitize_for_json(metadata)

                # Now dump with allow_nan=False for extra safety
                try:
                    metadata_json = json.dumps(sanitized_metadata, allow_nan=False)
                except (TypeError, ValueError) as e:
                    logger.error(
                        f"Signal {idx}: Failed to serialize even after sanitization: {e}"
                    )
                    logger.error(f"Signal {idx}: Metadata: {sanitized_metadata}")
                    # Fallback: convert everything to strings
                    metadata_json = json.dumps(
                        {k: str(v) for k, v in sanitized_metadata.items()}
                    )

                # Map new field names to old database columns
                signal_type = signal_data.get(
                    "action", signal_data.get("signal_type", "hold")
                )
                strategy = signal_data.get(
                    "strategy", signal_data.get("strategy_id", "unknown")
                )
                timeframe = signal_data.get("timeframe", "15m")

                # Log this signal's metadata for debugging
                logger.info(
                    f"Signal {idx}: {signal_data.get('symbol')} {signal_data.get('strategy_id')}: "
                    f"metadata_json len={len(metadata_json)}, content={metadata_json}"
                )

                values.append(
                    (
                        signal_data["symbol"],
                        timeframe,
                        timeframe,  # period column (legacy)
                        signal_type,
                        signal_data["confidence"],
                        strategy,
                        metadata_json,
                        signal_data["timestamp"],
                    )
                )

            # Execute the batch insert
            logger.info(f"Executing batch insert for {len(signals)} signals")
            with self.connection.cursor() as cursor:
                cursor.executemany(sql, values)

            logger.info(f"Persisted {len(signals)} signals to MySQL")
            return True

        except Exception as e:
            logger.error(f"Error persisting signals batch: {e}")
            # Try to reconnect on error
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            return False
