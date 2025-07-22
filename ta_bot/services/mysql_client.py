"""
MySQL client for fetching candle data and persisting signals.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL client for database operations."""

    def __init__(self, host: str = None, port: int = 3306, user: str = None, 
                 password: str = None, database: str = None, uri: str = None):
        """Initialize MySQL client."""
        # Try to get URI from environment first
        mysql_uri = os.getenv("MYSQL_URI")
        logger.info(f"Raw MYSQL_URI from environment: {mysql_uri}")
        
        if mysql_uri:
            # Parse the URI - handle mysql+pymysql:// protocol
            if mysql_uri.startswith('mysql+pymysql://'):
                # Remove the mysql+pymysql:// prefix for parsing
                uri_for_parsing = mysql_uri.replace('mysql+pymysql://', 'mysql://')
                logger.info(f"Converted URI for parsing: {uri_for_parsing}")
            else:
                uri_for_parsing = mysql_uri
                
            parsed_uri = urlparse(uri_for_parsing)
            logger.info(f"Parsed URI components:")
            logger.info(f"  hostname: {parsed_uri.hostname}")
            logger.info(f"  port: {parsed_uri.port}")
            logger.info(f"  username: {parsed_uri.username}")
            logger.info(f"  password: {'***' if parsed_uri.password else 'None'}")
            logger.info(f"  path: {parsed_uri.path}")
            
            self.host = parsed_uri.hostname
            self.port = parsed_uri.port or 3306
            self.user = parsed_uri.username
            self.password = parsed_uri.password
            # Handle URL encoding in database name
            self.database = parsed_uri.path.lstrip('/')
            if '%' in self.database:
                from urllib.parse import unquote
                original_db = self.database
                self.database = unquote(self.database)
                logger.info(f"URL decoded database name: '{original_db}' -> '{self.database}'")
            logger.info(f"Final parsed MySQL URI: {self.host}:{self.port}/{self.database}")
        elif uri:
            # Use provided URI
            if uri.startswith('mysql+pymysql://'):
                uri_for_parsing = uri.replace('mysql+pymysql://', 'mysql://')
            else:
                uri_for_parsing = uri
                
            parsed_uri = urlparse(uri_for_parsing)
            self.host = parsed_uri.hostname
            self.port = parsed_uri.port or 3306
            self.user = parsed_uri.username
            self.password = parsed_uri.password
            self.database = parsed_uri.path.lstrip('/')
            if '%' in self.database:
                from urllib.parse import unquote
                self.database = unquote(self.database)
        else:
            # Use individual parameters
            self.host = host or os.getenv("MYSQL_HOST", "mysql-server")
            self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
            self.user = user or os.getenv("MYSQL_USER", "petrosa")
            self.password = password or os.getenv("MYSQL_PASSWORD", "petrosa")
            self.database = database or os.getenv("MYSQL_DATABASE", "petrosa")
        
        self.connection = None

    async def connect(self):
        """Connect to MySQL database."""
        try:
            logger.info(f"Attempting to connect to MySQL with parameters:")
            logger.info(f"  Host: {self.host}")
            logger.info(f"  Port: {self.port}")
            logger.info(f"  User: {self.user}")
            logger.info(f"  Database: {self.database}")
            logger.info(f"  Password: {'***' if self.password else 'None'}")
            logger.info(f"  Database repr: {repr(self.database)}")
            logger.info(f"  Password repr: {repr(self.password)}")
            
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
        if not self.connection:
            logger.error("Not connected to MySQL")
            return pd.DataFrame()

        try:
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

            # Build SQL query
            sql = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM {table_name}
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            
            logger.info(f"Executing SQL query: {sql}")
            logger.info(f"Parameters: symbol={symbol}, limit={limit}")
            
            with self.connection.cursor() as cursor:
                cursor.execute(sql, (symbol, limit))
                rows = cursor.fetchall()
                
                logger.info(f"Query returned {len(rows)} rows")
                if rows:
                    logger.info(f"First row: {rows[0]}")
                    logger.info(f"Last row: {rows[-1]}")
                
                if not rows:
                    logger.warning(f"No data found for {symbol} {period} in table {table_name}")
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(rows)
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                logger.info(f"Created DataFrame with {len(df)} rows")
                logger.info(f"DataFrame columns: {df.columns.tolist()}")
                logger.info(f"DataFrame head:\n{df.head()}")
                
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