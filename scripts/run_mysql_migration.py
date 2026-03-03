#!/usr/bin/env python3
import logging
import os
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_migration():
    mysql_uri = os.getenv("MYSQL_URI")
    if not mysql_uri:
        logger.error("MYSQL_URI not set in environment")
        return False

    if mysql_uri.startswith("mysql+pymysql://"):
        mysql_uri = mysql_uri.replace("mysql+pymysql://", "mysql://")

    parsed = urlparse(mysql_uri)
    db_config = {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": unquote(parsed.password) if parsed.password else "",
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }

    logger.info(
        f"Connecting to MySQL at {db_config['host']}:{db_config['port']} as {db_config['user']}"
    )

    try:
        connection = pymysql.connect(**db_config)
        logger.info("✅ Connected to MySQL successfully")
        with connection.cursor() as cursor:
            # Perform migration: Add timeframe column if not exists
            cursor.execute("SHOW COLUMNS FROM signals LIKE 'timeframe'")
            if not cursor.fetchone():
                logger.info("Adding 'timeframe' column to signals table...")
                cursor.execute(
                    "ALTER TABLE signals ADD COLUMN timeframe VARCHAR(10) DEFAULT '1h' AFTER symbol"
                )
                logger.info("✅ Column added successfully")
            else:
                logger.info("✓ Column 'timeframe' already exists")

            # Backfill existing NULL or empty timeframe values to the default
            logger.info("Updating existing NULL/empty 'timeframe' values to default '1h'...")
            cursor.execute(
                "UPDATE signals SET timeframe = '1h' "
                "WHERE timeframe IS NULL OR timeframe = ''"
            )
            logger.info("✓ Existing 'timeframe' values updated where necessary")

            # Ensure an index exists on signals(timeframe) to support efficient queries
            logger.info("Checking for existing index 'idx_signals_timeframe' on signals(timeframe)...")
            cursor.execute(
                """
                SELECT COUNT(1) AS idx_exists
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'signals'
                  AND INDEX_NAME = 'idx_signals_timeframe'
                """,
                (db_config["database"],),
            )
            row = cursor.fetchone()
            idx_exists = bool(row and row.get("idx_exists"))
            if not idx_exists:
                logger.info("Creating index 'idx_signals_timeframe' on signals(timeframe)...")
                cursor.execute("CREATE INDEX idx_signals_timeframe ON signals(timeframe)")
                logger.info("✅ Index 'idx_signals_timeframe' created successfully")
            else:
                logger.info("✓ Index 'idx_signals_timeframe' already exists")

        connection.commit()
        connection.close()
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
