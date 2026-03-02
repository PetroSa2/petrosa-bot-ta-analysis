#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote
import pymysql
from pymysql.cursors import DictCursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_migration():
    mysql_uri = os.getenv("MYSQL_URI")
    if not mysql_uri:
        logger.error("MYSQL_URI not set in environment")
        return False

    if mysql_uri.startswith('mysql+pymysql://'):
        mysql_uri = mysql_uri.replace('mysql+pymysql://', 'mysql://')
    
    parsed = urlparse(mysql_uri)
    db_config = {
        "host": parsed.hostname or os.getenv("MYSQL_HOST", "localhost"),
        "port": parsed.port or int(os.getenv("MYSQL_PORT", 3306)),
        "user": parsed.username or os.getenv("MYSQL_USER", "root"),
        "password": unquote(parsed.password) if parsed.password else os.getenv("MYSQL_PASSWORD", ""),
        "database": parsed.path.lstrip('/') or os.getenv("MYSQL_DATABASE", "petrosa_trading"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }

    logger.info(f"Connecting to MySQL at {db_config['host']}:{db_config['port']} as {db_config['user']}")

    try:
        connection = pymysql.connect(**db_config)
        logger.info("✅ Connected to MySQL successfully")
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            logger.info("✅ Database check successful")
        connection.close()
        return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    if run_migration():
        sys.exit(0)
    sys.exit(1)
