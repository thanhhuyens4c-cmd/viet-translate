-- Migration: Add image_url column to message and direct_message tables
-- Date: 2026-09-30
-- Description: Supports image sharing in chat between translator and hirer

ALTER TABLE message ADD COLUMN image_url VARCHAR(500);
ALTER TABLE direct_message ADD COLUMN image_url VARCHAR(500);
