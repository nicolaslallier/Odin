-- Centralized Logging System Database Schema
-- Version: 1.2.0
-- Description: Creates timeseries log tables with proper indexes and retention policies

-- Enable UUID extension for request_id and task_id
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application_logs table
CREATE TABLE IF NOT EXISTS application_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,
    service VARCHAR(50) NOT NULL,
    logger VARCHAR(255),
    message TEXT NOT NULL,
    module VARCHAR(255),
    function VARCHAR(255),
    line INTEGER,
    exception TEXT,
    request_id UUID,
    task_id UUID,
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_application_logs_timestamp ON application_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_application_logs_level ON application_logs(level);
CREATE INDEX IF NOT EXISTS idx_application_logs_service ON application_logs(service);
CREATE INDEX IF NOT EXISTS idx_application_logs_request_id ON application_logs(request_id) WHERE request_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_application_logs_task_id ON application_logs(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_application_logs_created_at ON application_logs(created_at DESC);

-- Create composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_application_logs_service_level_timestamp ON application_logs(service, level, timestamp DESC);

-- Create GIN index for full-text search on message
CREATE INDEX IF NOT EXISTS idx_application_logs_message_gin ON application_logs USING gin(to_tsvector('english', message));

-- Create GIN index for metadata JSONB queries
CREATE INDEX IF NOT EXISTS idx_application_logs_metadata_gin ON application_logs USING gin(metadata);

-- Create partitioning function (monthly partitions)
-- Note: This is a simplified approach. For production with TimescaleDB, use hypertables instead.
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partition for current month
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'application_logs_' || to_char(start_date, 'YYYY_MM');
    
    -- Check if partition exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF application_logs 
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
    END IF;
    
    -- Create partition for next month
    start_date := end_date;
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'application_logs_' || to_char(start_date, 'YYYY_MM');
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF application_logs 
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            start_date,
            end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create function to cleanup old logs
CREATE OR REPLACE FUNCTION cleanup_old_logs(retention_days INTEGER DEFAULT 30)
RETURNS TABLE(deleted_count BIGINT) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    rows_deleted BIGINT;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    DELETE FROM application_logs
    WHERE created_at < cutoff_date;
    
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    
    RETURN QUERY SELECT rows_deleted;
END;
$$ LANGUAGE plpgsql;

-- Create function to get log statistics
CREATE OR REPLACE FUNCTION get_log_statistics(
    start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '24 hours',
    end_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE(
    service VARCHAR(50),
    level VARCHAR(10),
    count BIGINT,
    latest_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.service,
        l.level,
        COUNT(*)::BIGINT as count,
        MAX(l.timestamp) as latest_timestamp
    FROM application_logs l
    WHERE l.timestamp BETWEEN start_time AND end_time
    GROUP BY l.service, l.level
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Create view for recent errors (last 24 hours)
CREATE OR REPLACE VIEW recent_errors AS
SELECT 
    id,
    timestamp,
    service,
    logger,
    message,
    exception,
    request_id,
    task_id,
    user_id,
    metadata
FROM application_logs
WHERE 
    level IN ('ERROR', 'CRITICAL')
    AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 1000;

-- Create view for log summary by service
CREATE OR REPLACE VIEW log_summary_by_service AS
SELECT 
    service,
    COUNT(*) as total_logs,
    COUNT(CASE WHEN level = 'DEBUG' THEN 1 END) as debug_count,
    COUNT(CASE WHEN level = 'INFO' THEN 1 END) as info_count,
    COUNT(CASE WHEN level = 'WARNING' THEN 1 END) as warning_count,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) as error_count,
    COUNT(CASE WHEN level = 'CRITICAL' THEN 1 END) as critical_count,
    MAX(timestamp) as last_log_time
FROM application_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY service
ORDER BY total_logs DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, DELETE ON application_logs TO odin;
-- GRANT EXECUTE ON FUNCTION cleanup_old_logs TO odin;
-- GRANT EXECUTE ON FUNCTION get_log_statistics TO odin;
-- GRANT SELECT ON recent_errors TO odin;
-- GRANT SELECT ON log_summary_by_service TO odin;

-- Add comments for documentation
COMMENT ON TABLE application_logs IS 'Centralized application and infrastructure logs with timeseries data';
COMMENT ON COLUMN application_logs.timestamp IS 'When the log event occurred (from application)';
COMMENT ON COLUMN application_logs.created_at IS 'When the log was inserted into the database';
COMMENT ON COLUMN application_logs.metadata IS 'Additional context stored as JSON (flexible schema)';
COMMENT ON FUNCTION cleanup_old_logs IS 'Removes logs older than specified retention period (default: 30 days)';
COMMENT ON FUNCTION get_log_statistics IS 'Returns aggregated log statistics for a time range';

-- Create a trigger to automatically set created_at
CREATE OR REPLACE FUNCTION set_created_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_created_at
BEFORE INSERT ON application_logs
FOR EACH ROW
EXECUTE FUNCTION set_created_at();

-- Initial setup complete
DO $$
BEGIN
    RAISE NOTICE 'Logging system schema initialized successfully';
    RAISE NOTICE 'Run cleanup_old_logs() periodically to maintain retention policy';
END $$;

