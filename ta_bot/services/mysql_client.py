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
import json

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL client for database operations."""
    
    def __init__(self, host: str | None = None, port: int = 3306, user: str | None = None,
                 password: str | None = None, database: str | None = None, uri: str | None = None):
        """Initialize MySQL client."""
        # Try to get URI from environment first
        mysql_uri = os.getenv("MYSQL_URI")

        if mysql_uri:
            # Parse the URI - handle mysql+pymysql:// protocol
            if mysql_uri.startswith('mysql+pymysql://'):
                # Remove the mysql+pymysql:// prefix for parsing
                uri_for_parsing = mysql_uri.replace('mysql+pymysql://', 'mysql://')
            else:
                uri_for_parsing = mysql_uri

            parsed_uri = urlparse(uri_for_parsing)

            self.host: str = parsed_uri.hostname or "localhost"
            self.port: int = parsed_uri.port or 3306
            self.user: str = parsed_uri.username or "root"
            # URL decode the password to handle special characters
            self.password: str | None = parsed_uri.password
            if self.password and '%' in self.password:
                from urllib.parse import unquote
                self.password = unquote(self.password)
            # Handle URL encoding in database name
            self.database: str = parsed_uri.path.lstrip('/')
            if '%' in self.database:
                from urllib.parse import unquote
                self.database = unquote(self.database)
            logger.info(f"MySQL URI parsed successfully")
        else:
            # Use individual parameters
            self.host = (host or os.getenv("MYSQL_HOST", "mysql-server")) or "mysql-server"
            self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
            self.user = (user or os.getenv("MYSQL_USER", "petrosa")) or "petrosa"
            self.password = password or os.getenv("MYSQL_PASSWORD", "petrosa")
            self.database = (database or os.getenv("MYSQL_DATABASE", "petrosa")) or "petrosa"
        
        self.connection: Any = None

    async def connect(self):
        """Connect to MySQL database."""
        try:
            logger.info(f"Attempting to connect to MySQL...")
            
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
                charset='utf8mb4'
            )
            logger.info(f"Connected to MySQL successfully")
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
                "1d": "klines_d1"
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
                    logger.warning(f"No data found for {symbol} {period} in table {table_name}")
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(rows)
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Convert Decimal columns to float for pandas calculations
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_columns:
                    df[col] = df[col].astype(float)
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                return df
                
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol} {period}: {e}")
            # Try to reconnect on error
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            return pd.DataFrame()

    async def persist_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Persist a single signal to MySQL."""
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
                INSERT INTO signals (symbol, timeframe, action, confidence, strategy, metadata, timestamp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            metadata_json = json.dumps(signal_data.get('metadata', {}))
            
            with self.connection.cursor() as cursor:
                cursor.execute(sql, (
                    signal_data['symbol'],
                    signal_data['timeframe'],
                    signal_data['action'],
                    signal_data['confidence'],
                    signal_data['strategy'],
                    metadata_json,
                    signal_data['timestamp']
                ))
                
            logger.info(f"Persisted signal for {signal_data['symbol']} {signal_data['timeframe']}")
            return True
            
        except Exception as e:
            logger.error(f"Error persisting signal: {e}")
            # Try to reconnect on error
            try:
                await self.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            return False

    async def persist_signals_batch(self, signals: List[Dict[str, Any]]) -> bool:
        """Persist multiple signals to MySQL in a batch."""
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
                INSERT INTO signals (symbol, timeframe, action, confidence, strategy, metadata, timestamp, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            values = []
            for signal_data in signals:
                metadata_json = json.dumps(signal_data.get('metadata', {}))
                values.append((
                    signal_data['symbol'],
                    signal_data['timeframe'],
                    signal_data['action'],
                    signal_data['confidence'],
                    signal_data['strategy'],
                    metadata_json,
                    signal_data['timestamp']
                ))
            
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