import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts to path so we can import run_migration
scripts_dir = Path(__file__).parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))


class TestRunMysqlMigration(unittest.TestCase):
    @patch("run_mysql_migration.os.getenv")
    @patch("run_mysql_migration.pymysql.connect")
    def test_run_migration_unquotes_password(self, mock_connect, mock_getenv):
        from run_mysql_migration import run_migration

        # Mock MYSQL_URI with encoded password "pass%40word"
        mock_getenv.return_value = "mysql://user:pass%40word@localhost:3306/db"

        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = True  # Column already exists

        # Run migration
        result = run_migration()

        # Verify success
        self.assertTrue(result)

        # Verify connect was called with unquoted password "pass@word"
        mock_connect.assert_called_once()
        args, kwargs = mock_connect.call_args
        self.assertEqual(kwargs["password"], "pass@word")
        self.assertEqual(kwargs["user"], "user")
        self.assertEqual(kwargs["host"], "localhost")
        self.assertEqual(kwargs["port"], 3306)
        self.assertEqual(kwargs["database"], "db")

    @patch("run_mysql_migration.os.getenv")
    @patch("run_mysql_migration.pymysql.connect")
    def test_run_migration_adds_column_if_missing(self, mock_connect, mock_getenv):
        from run_mysql_migration import run_migration

        mock_getenv.return_value = "mysql://user:pass@localhost:3306/db"

        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # First call to fetchone (SHOW COLUMNS) returns None (missing column)
        mock_cursor.fetchone.return_value = None

        result = run_migration()

        self.assertTrue(result)
        # Verify ALTER TABLE was called
        mock_cursor.execute.assert_any_call(
            "ALTER TABLE signals ADD COLUMN timeframe VARCHAR(10) DEFAULT '1h' AFTER symbol"
        )


if __name__ == "__main__":
    unittest.main()
