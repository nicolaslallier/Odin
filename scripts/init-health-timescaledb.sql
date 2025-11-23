-- TimescaleDB initialization script for health check monitoring
-- This script sets up health check timeseries storage with hypertable

-- Enable TimescaleDB extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create service_health_checks table
CREATE TABLE IF NOT EXISTS service_health_checks (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service_name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL CHECK (service_type IN ('infrastructure', 'application')),
    is_healthy BOOLEAN NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Composite primary key including timestamp for TimescaleDB hypertable
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable(
    'service_health_checks',
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_health_checks_service_name 
    ON service_health_checks (service_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_health_checks_timestamp 
    ON service_health_checks (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_health_checks_service_type 
    ON service_health_checks (service_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_health_checks_healthy_status 
    ON service_health_checks (is_healthy, timestamp DESC);

-- Create continuous aggregate for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS health_checks_hourly
WITH (timescaledb.continuous) AS
SELECT
    service_name,
    service_type,
    time_bucket('1 hour', timestamp) AS hour,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END) AS healthy_count,
    SUM(CASE WHEN NOT is_healthy THEN 1 ELSE 0 END) AS unhealthy_count,
    ROUND((SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) AS uptime_percentage,
    AVG(response_time_ms) AS avg_response_time_ms,
    MAX(response_time_ms) AS max_response_time_ms,
    MIN(response_time_ms) AS min_response_time_ms
FROM service_health_checks
GROUP BY service_name, service_type, hour
WITH NO DATA;

-- Create continuous aggregate for daily statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS health_checks_daily
WITH (timescaledb.continuous) AS
SELECT
    service_name,
    service_type,
    time_bucket('1 day', timestamp) AS day,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END) AS healthy_count,
    SUM(CASE WHEN NOT is_healthy THEN 1 ELSE 0 END) AS unhealthy_count,
    ROUND((SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) AS uptime_percentage,
    AVG(response_time_ms) AS avg_response_time_ms,
    MAX(response_time_ms) AS max_response_time_ms,
    MIN(response_time_ms) AS min_response_time_ms
FROM service_health_checks
GROUP BY service_name, service_type, day
WITH NO DATA;

-- Add refresh policy for continuous aggregates (refresh every hour)
SELECT add_continuous_aggregate_policy('health_checks_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('health_checks_daily',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Add data retention policy (keep data for 1 year)
SELECT add_retention_policy('service_health_checks',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- Add compression policy (compress data older than 7 days)
ALTER TABLE service_health_checks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'service_name, service_type',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('service_health_checks',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Grant permissions to odin user
GRANT SELECT, INSERT, UPDATE, DELETE ON service_health_checks TO odin;
GRANT USAGE, SELECT ON SEQUENCE service_health_checks_id_seq TO odin;
GRANT SELECT ON health_checks_hourly TO odin;
GRANT SELECT ON health_checks_daily TO odin;

