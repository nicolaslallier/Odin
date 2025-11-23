# Health Check Timeseries Monitoring - Version 1.7.0

## Overview

The Health Check Timeseries system provides comprehensive monitoring and historical tracking of all Odin services. It collects health status data every minute and stores it in TimescaleDB for analysis, trending, and alerting.

## Architecture

### Components

```
┌──────────────┐     1 min      ┌──────────────┐     HTTP POST    ┌──────────────┐
│              │   scheduled     │              │   /health/record │              │
│ odin-worker  │ ─────────────> │  odin-API    │ ──────────────> │ PostgreSQL   │
│   (Celery)   │   collect       │   (FastAPI)  │     persist      │ (TimescaleDB)│
│              │                 │              │                  │              │
└──────────────┘                 └──────────────┘                  └──────────────┘
                                        ▲                                 ▲
                                        │                                 │
                                        │ HTTP GET /health/history        │
                                        │                                 │
                                  ┌─────┴──────┐                         │
                                  │            │                          │
                                  │odin-portal │                          │
                                  │   (Web)    │ ─────query────────────> │
                                  │            │                          │
                                  └────────────┘                          │
                                                                          │
                                        User views dashboard with          │
                                        real-time and historical data      │
```

### Data Flow

1. **Collection (Every 1 minute)**:
   - Worker task `collect_and_record_health_checks` runs
   - Fetches infrastructure health from `/health/services` (database, storage, queue, vault, ollama)
   - Checks application services directly (api, worker, beat, flower)
   - Packages all health data into a batch request

2. **Storage**:
   - Worker POSTs batch to `/health/record` endpoint
   - API validates request using Pydantic models
   - Repository inserts records into `service_health_checks` hypertable
   - TimescaleDB automatically partitions by time

3. **Retrieval**:
   - Portal fetches current status from `/health/latest`
   - Portal queries historical data from `/health/history`
   - Data filtered by time range, service name, or service type
   - Displayed as uptime charts and statistics

## Database Schema

### service_health_checks Table

```sql
CREATE TABLE service_health_checks (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL, -- 'infrastructure' or 'application'
    is_healthy BOOLEAN NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
);
```

### Hypertable Configuration

- **Partition Key**: `timestamp`
- **Chunk Interval**: 1 day
- **Retention Policy**: 365 days (1 year)
- **Compression**: Enabled for data older than 7 days
- **Compression Segment By**: `service_name`, `service_type`

### Continuous Aggregates

**Hourly Statistics** (`health_checks_hourly`):
- Time bucket: 1 hour
- Metrics: total checks, healthy count, unhealthy count, uptime percentage, response times
- Refresh policy: Every hour

**Daily Statistics** (`health_checks_daily`):
- Time bucket: 1 day
- Metrics: same as hourly
- Refresh policy: Every day

## API Endpoints

### POST /health/record

Record batch health check data to TimescaleDB.

**Request Body**:
```json
{
  "checks": [
    {
      "service_name": "database",
      "service_type": "infrastructure",
      "is_healthy": true,
      "response_time_ms": 12.5,
      "error_message": null,
      "metadata": {"version": "14.5"}
    }
  ],
  "timestamp": "2024-01-15T10:00:00Z"
}
```

**Response**:
```json
{
  "recorded": 10,
  "timestamp": "2024-01-15T10:00:00Z",
  "message": "Health checks recorded successfully"
}
```

### GET /health/history

Query historical health check data with filters.

**Query Parameters**:
- `start_time` (required): Start of time range (ISO 8601)
- `end_time` (required): End of time range (ISO 8601)
- `service_names` (optional): Array of service names to filter
- `service_type` (optional): Filter by 'infrastructure' or 'application'
- `limit` (optional): Maximum records to return (default: 1000, max: 10000)

**Response**:
```json
{
  "records": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:00:00+00:00",
      "service_name": "database",
      "service_type": "infrastructure",
      "is_healthy": true,
      "response_time_ms": 10.5,
      "error_message": null,
      "metadata": {}
    }
  ],
  "total": 1,
  "start_time": "2024-01-15T00:00:00Z",
  "end_time": "2024-01-15T23:59:59Z"
}
```

### GET /health/latest

Get the most recent health status for all services.

**Response**:
```json
{
  "services": {
    "database": true,
    "api": true,
    "worker": false
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Web Portal Endpoints

### GET /health/api/history

Fetch historical health data for dashboard visualization.

**Query Parameters**:
- `time_range`: `1h`, `24h`, `7d`, or `30d`
- `service_names`: Comma-separated service names

**Response**:
```json
{
  "success": true,
  "records": [...],
  "total": 1440,
  "time_range": "24h",
  "start_time": "2024-01-14T10:00:00Z",
  "end_time": "2024-01-15T10:00:00Z"
}
```

## Query Examples

### Get last 24 hours of database health

```sql
SELECT timestamp, is_healthy, response_time_ms
FROM service_health_checks
WHERE service_name = 'database'
  AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### Calculate uptime for last 7 days

```sql
SELECT 
    service_name,
    COUNT(*) as total_checks,
    SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END) as healthy_checks,
    ROUND((SUM(CASE WHEN is_healthy THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC * 100), 2) as uptime_percent
FROM service_health_checks
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY service_name
ORDER BY uptime_percent DESC;
```

### Find all downtime incidents

```sql
SELECT service_name, timestamp, error_message
FROM service_health_checks
WHERE is_healthy = false
  AND timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;
```

### Average response times by service

```sql
SELECT 
    service_name,
    AVG(response_time_ms) as avg_response_ms,
    MAX(response_time_ms) as max_response_ms,
    MIN(response_time_ms) as min_response_ms
FROM service_health_checks
WHERE response_time_ms IS NOT NULL
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY service_name
ORDER BY avg_response_ms DESC;
```

## Worker Task

### collect_and_record_health_checks

Scheduled task that runs every 1 minute via Celery Beat.

**Responsibilities**:
1. Fetch infrastructure health from API `/health/services`
2. Check API health with response time measurement
3. Check Worker/Beat status via Flower API
4. Check Flower dashboard availability
5. Package all checks into batch request
6. POST to `/health/record` for persistence

**Error Handling**:
- Continues on individual service failures
- Marks unavailable services as unhealthy
- Logs errors but doesn't fail the entire task
- Returns summary with status and error list

## Configuration

### Environment Variables

No additional environment variables required. Uses existing database connection from `POSTGRES_DSN`.

### Beat Schedule

```python
"collect-health-checks": {
    "task": "src.worker.tasks.scheduled.collect_and_record_health_checks",
    "schedule": timedelta(minutes=1),
    "options": {"expires": 60},
}
```

## Monitoring Services

### Infrastructure Services
- `database`: PostgreSQL/TimescaleDB
- `storage`: MinIO object storage
- `queue`: RabbitMQ message broker
- `vault`: HashiCorp Vault secrets manager
- `ollama`: Ollama AI/ML server

### Application Services
- `api`: Odin FastAPI service
- `worker`: Celery worker process
- `beat`: Celery beat scheduler
- `flower`: Celery monitoring dashboard
- `portal`: Web interface

## Troubleshooting

### No Historical Data Showing

**Possible Causes**:
1. Worker not running: Check `docker ps` for odin-worker
2. Task not scheduled: Verify beat schedule with Flower
3. Database issue: Check PostgreSQL logs
4. API endpoint error: Check odin-api logs

**Solution**:
```bash
# Check worker status
docker logs odin-worker

# Check beat schedule
docker exec odin-worker celery -A src.worker.celery_app inspect scheduled

# Manually trigger collection
docker exec odin-worker celery -A src.worker.celery_app call src.worker.tasks.scheduled.collect_and_record_health_checks
```

### High Data Volume

If storage grows too large:

**Check current size**:
```sql
SELECT pg_size_pretty(pg_total_relation_size('service_health_checks'));
```

**Adjust retention policy**:
```sql
SELECT remove_retention_policy('service_health_checks');
SELECT add_retention_policy('service_health_checks', INTERVAL '90 days');
```

**Manually compress old data**:
```sql
SELECT compress_chunk(c) FROM show_chunks('service_health_checks') c;
```

### Missing Services in Dashboard

If a service isn't appearing:
1. Check if it's being collected in worker logs
2. Verify service name matches expected values
3. Check database for records: `SELECT DISTINCT service_name FROM service_health_checks;`

## Performance Considerations

### Write Performance
- Batch inserts (10-15 records per minute)
- Hypertable partitioning distributes writes
- Compression reduces storage for old data

### Query Performance
- Indexes on `(service_name, timestamp)` for filtered queries
- Continuous aggregates for fast hourly/daily summaries
- Time-based partitioning enables chunk exclusion

### Storage Optimization
- Compression after 7 days reduces size by ~90%
- Retention policy automatically drops old chunks
- JSONB metadata field is efficient for flexible data

## Upgrades and Migrations

### From Previous Versions

No migration needed - this is a new feature in v1.7.0.

### Future Considerations

- Additional metrics (CPU, memory, disk usage)
- Alerting based on uptime thresholds
- Integration with external monitoring systems
- Custom retention policies per service type

## Best Practices

1. **Monitor Worker Logs**: Ensure collection task runs without errors
2. **Check Uptime Regularly**: Use portal dashboard to spot trends
3. **Set Up Alerts**: Configure notifications for critical services
4. **Review Query Performance**: Monitor continuous aggregate refresh times
5. **Validate Data**: Periodically check data consistency

## Support

For issues or questions:
- Check application logs: `docker logs odin-worker`, `docker logs odin-api`
- Review PostgreSQL logs: `docker logs odin-postgresql`
- Consult TROUBLESHOOTING.md for common issues
- File GitHub issues for bugs or feature requests

