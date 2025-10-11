#!/usr/bin/env python3
"""
MySQL Migration Script - Add Timeframe Column
Date: 2025-10-11
Purpose: Add missing timeframe column to signals table
"""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the timeframe column migration."""
    # Get database credentials from environment
    db_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "petrosa_trading"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }

    logger.info(f"Connecting to MySQL at {db_config['host']}:{db_config['port']}")

    try:
        # Connect to database
        connection = pymysql.connect(**db_config)
        logger.info("✅ Connected to MySQL successfully")

        with connection.cursor() as cursor:
            # Check if column already exists
            logger.info("Checking if timeframe column exists...")
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'signals'
                AND COLUMN_NAME = 'timeframe'
            """,
                (db_config["database"],),
            )

            result = cursor.fetchone()
            column_exists = result["count"] > 0

            if column_exists:
                logger.info("⚠️  Timeframe column already exists - skipping migration")
                return True

            logger.info("Adding timeframe column to signals table...")

            # Add timeframe column
            cursor.execute(
                """
                ALTER TABLE signals
                ADD COLUMN timeframe VARCHAR(10) DEFAULT '15m'
                AFTER symbol
            """
            )
            logger.info("✅ Added timeframe column")

            # Update existing records
            logger.info("Updating existing records with default timeframe...")
            cursor.execute(
                """
                UPDATE signals
                SET timeframe = '15m'
                WHERE timeframe IS NULL OR timeframe = ''
            """
            )
            rows_updated = cursor.rowcount
            logger.info(f"✅ Updated {rows_updated} existing records")

            # Add index
            logger.info("Adding index on timeframe column...")
            try:
                cursor.execute(
                    """
                    CREATE INDEX idx_signals_timeframe ON signals(timeframe)
                """
                )
                logger.info("✅ Added index on timeframe column")
            except pymysql.err.OperationalError as e:
                if "Duplicate key name" in str(e):
                    logger.info("⚠️  Index already exists - skipping")
                else:
                    raise

            # Commit changes
            connection.commit()
            logger.info("✅ Migration completed successfully")

            # Verify the change
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = 'signals'
                AND COLUMN_NAME = 'timeframe'
            """,
                (db_config["database"],),
            )

            column_info = cursor.fetchone()
            logger.info(f"✅ Verification - Column info: {column_info}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

    finally:
        if "connection" in locals():
            connection.close()
            logger.info("Closed database connection")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("MySQL Migration: Add Timeframe Column to Signals Table")
    logger.info("=" * 80)

    success = run_migration()

    if success:
        logger.info("=" * 80)
        logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        sys.exit(0)
    else:
        logger.error("=" * 80)
        logger.error("❌ MIGRATION FAILED")
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
