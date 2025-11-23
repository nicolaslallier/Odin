-- TimescaleDB initialization script for Odin
-- This script sets up the TimescaleDB extension and creates the confluence_statistics hypertable

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create confluence_statistics table
CREATE TABLE IF NOT EXISTS confluence_statistics (
    id SERIAL,
    space_key VARCHAR(255) NOT NULL,
    space_name VARCHAR(500),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Basic statistics
    total_pages INTEGER NOT NULL DEFAULT 0,
    total_size_bytes BIGINT NOT NULL DEFAULT 0,
    contributor_count INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ,
    
    -- Detailed statistics
    page_breakdown_by_type JSONB DEFAULT '{}',
    attachment_stats JSONB DEFAULT '{}',
    version_count INTEGER DEFAULT 0,
    
    -- Comprehensive statistics
    user_activity JSONB DEFAULT '{}',
    page_views JSONB DEFAULT '{}',
    comment_counts JSONB DEFAULT '{}',
    link_analysis JSONB DEFAULT '{}',
    
    -- Metadata
    collection_time_seconds FLOAT,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Composite primary key including timestamp for TimescaleDB hypertable
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable(
    'confluence_statistics',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_confluence_stats_space_key 
    ON confluence_statistics (space_key, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_confluence_stats_timestamp 
    ON confluence_statistics (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_confluence_stats_space_timestamp 
    ON confluence_statistics (space_key, timestamp DESC);

-- Create continuous aggregate for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS confluence_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    space_key,
    time_bucket('1 hour', timestamp) AS hour,
    AVG(total_pages) AS avg_pages,
    MAX(total_pages) AS max_pages,
    MIN(total_pages) AS min_pages,
    AVG(total_size_bytes) AS avg_size_bytes,
    MAX(total_size_bytes) AS max_size_bytes,
    AVG(contributor_count) AS avg_contributors,
    COUNT(*) AS sample_count
FROM confluence_statistics
GROUP BY space_key, hour
WITH NO DATA;

-- Create continuous aggregate for daily statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS confluence_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    space_key,
    time_bucket('1 day', timestamp) AS day,
    AVG(total_pages) AS avg_pages,
    MAX(total_pages) AS max_pages,
    MIN(total_pages) AS min_pages,
    AVG(total_size_bytes) AS avg_size_bytes,
    MAX(total_size_bytes) AS max_size_bytes,
    AVG(contributor_count) AS avg_contributors,
    COUNT(*) AS sample_count
FROM confluence_statistics
GROUP BY space_key, day
WITH NO DATA;

-- Add refresh policy for continuous aggregates (refresh every hour)
SELECT add_continuous_aggregate_policy('confluence_stats_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('confluence_stats_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Add data retention policy (keep data for 1 year)
SELECT add_retention_policy('confluence_statistics',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- Add compression policy (compress data older than 7 days)
ALTER TABLE confluence_statistics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'space_key',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('confluence_statistics',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Grant permissions to odin user
GRANT SELECT, INSERT, UPDATE, DELETE ON confluence_statistics TO odin;
GRANT USAGE, SELECT ON SEQUENCE confluence_statistics_id_seq TO odin;
GRANT SELECT ON confluence_stats_hourly TO odin;
GRANT SELECT ON confluence_stats_daily TO odin;

