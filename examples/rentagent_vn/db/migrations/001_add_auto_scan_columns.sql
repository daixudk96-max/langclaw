-- Migration: Add auto-scan schedule columns to campaigns table
-- Run this on existing databases to add the new columns

ALTER TABLE campaigns ADD COLUMN auto_scan_hour INTEGER NOT NULL DEFAULT 6;
ALTER TABLE campaigns ADD COLUMN auto_scan_timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh';
ALTER TABLE campaigns ADD COLUMN last_auto_scan_date TEXT;
