"""
MySQL client for fetching candle data and persisting signals.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL client for database operations."""

    def __init__(self, host: str = None, port: int = 3306, user: str = None, 
                 password: str = None, database: str = None, uri: str = None):
        """Initialize MySQL client."""
        if uri:
            self.uri = uri
            self.host = None
            self.port = None
            self.user = None
            self.password = None
            self.database = None
        else:
            self.uri = None
            self.host = host or os.getenv("MYSQL_HOST", "mysql-server")
            self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
            self.user = user or os.getenv("MYSQL_USER", "petrosa")
            self.password = password or os.getenv("MYSQL_PASSWORD", "petrosa")
            self.database = database or os.getenv("MYSQL_DATABASE", "petrosa")
        self.connection = None

    async def connect(self):
        """Connect to MySQL database."""
        try:
            if self.uri:
                # Use URI connection
                self.connection = pymysql.connect(
                    uri=self.uri,
                    cursorclass=DictCursor,
                    autocommit=True
                )
                logger.info(f"Connected to MySQL using URI")
            else:
                # Use individual parameters
                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    cursorclass=DictCursor,
                    autocommit=True
                )
                logger.info(f"Connected to MySQL at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MySQL database."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from MySQL")

    async def fetch_candles(self, symbol: str, period: str, limit: int = 100) -> pd.DataFrame:
        """Fetch candle data from MySQL."""
        try:
            if not self.connection:
                await self.connect()

            # Map period to table name
            period_mapping = {
                "1m": "klines_m1",
                "5m": "klines_m5", 
                "15m": "klines_m15",
                "30m": "klines_m30",
                "1h": "klines_h1",
                "4h": "klines_h4",
                "1d": "klines_d1"
            }
            
            table_name = period_mapping.get(period)
            if not table_name:
                logger.error(f"Unsupported period: {period}")
                return pd.DataFrame()

            # Query to fetch recent candles
            query = f"""
                SELECT 
                    timestamp,
                    open,
                    high, 
                    low,
                    close,
                    volume
                FROM {table_name}
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """

            with self.connection.cursor() as cursor:
                cursor.execute(query, (symbol, limit))
                results = cursor.fetchall()

            if not results:
                logger.warning(f"No candle data found for {symbol} {period}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by timestamp (oldest first)
            df = df.sort_values('timestamp')
            
            # Convert numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            logger.info(f"Fetched {len(df)} candles for {symbol} {period}")
            return df

        except Exception as e:
            logger.error(f"Error fetching candles for {symbol} {period}: {e}")
            return pd.DataFrame()

    async def persist_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Persist signal to MySQL with trade engine API schema."""
        try:
            if not self.connection:
                await self.connect()

            # Insert signal into signals table
            query = """
                INSERT INTO signals (
                    symbol,
                    period,
                    signal_type,
                    confidence,
                    strategy,
                    metadata,
                    timestamp,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            with self.connection.cursor() as cursor:
                cursor.execute(query, (
                    signal_data['symbol'],
                    signal_data['period'],
                    signal_data['signal'],
                    signal_data['confidence'],
                    signal_data['strategy'],
                    str(signal_data['metadata']),  # Store as JSON string
                    signal_data['timestamp']
                ))

            logger.info(f"Signal persisted for {signal_data['symbol']} {signal_data['strategy']}")
            return True

        except Exception as e:
            logger.error(f"Error persisting signal: {e}")
            return False

    async def persist_signals_batch(self, signals: List[Dict[str, Any]]) -> bool:
        """Persist multiple signals in a batch."""
        try:
            if not self.connection:
                await self.connect()

            if not signals:
                return True

            # Insert multiple signals
            query = """
                INSERT INTO signals (
                    symbol,
                    period,
                    signal_type,
                    confidence,
                    strategy,
                    metadata,
                    timestamp,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """

            values = []
            for signal in signals:
                values.append((
                    signal['symbol'],
                    signal['period'],
                    signal['signal'],
                    signal['confidence'],
                    signal['strategy'],
                    str(signal['metadata']),
                    signal['timestamp']
                ))

            with self.connection.cursor() as cursor:
                cursor.executemany(query, values)

            logger.info(f"Persisted {len(signals)} signals in batch")
            return True

        except Exception as e:
            logger.error(f"Error persisting signals batch: {e}")
            return False 