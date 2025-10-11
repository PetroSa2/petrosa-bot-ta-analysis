-- Migration script to add timeframe column to signals table
-- Date: 2025-10-11
-- Purpose: Fix MySQL schema issue where timeframe column is missing

-- Add timeframe column to signals table
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS timeframe VARCHAR(10) DEFAULT '15m'
AFTER symbol;

-- Update existing records to have default timeframe value
UPDATE signals
SET timeframe = '15m'
WHERE timeframe IS NULL OR timeframe = '';

-- Add index on timeframe for better query performance
CREATE INDEX IF NOT EXISTS idx_signals_timeframe ON signals(timeframe);

-- Verify the column was added
SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'signals' AND COLUMN_NAME = 'timeframe';
