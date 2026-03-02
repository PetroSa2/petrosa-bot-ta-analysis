#!/usr/bin/env python3
import logging
import os
import sys
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
        connection.close()
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    if run_migration():
        sys.exit(0)
    sys.exit(1)
