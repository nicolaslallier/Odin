# Async Confluence Statistics Guide

## Overview

This guide documents the asynchronous Confluence statistics collection feature in Odin, which provides comprehensive space analytics with real-time WebSocket updates and historical time series data storage.

**Version**: 1.0.0  
**Date**: 2025-11-23

## Architecture

### Component Flow

```
┌─────────────┐      ┌──────────┐      ┌─────────────┐      ┌──────────────┐
│   Portal    │─────▶│   API    │─────▶│  RabbitMQ   │─────▶│    Worker    │
│  (Browser)  │      │ Service  │      │   Queue     │      │   (Celery)   │
└─────────────┘      └──────────┘      └─────────────┘      └──────────────┘
       ▲                   ▲                                         │
       │                   │                                         │
       │  WebSocket        │  Callback POST                         │
       │  Update           │  /internal/statistics-callback         │
       │                   │                                         │
       └───────────────────┴─────────────────────────────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │   TimescaleDB    │
                            │  (Time Series)   │
                            └──────────────────┘
```

### Data Flow Steps

1. **Job Initiation**: Portal calls `POST /confluence/statistics-async`
2. **Event Publishing**: API publishes event to RabbitMQ queue `confluence.statistics.requests`
3. **Job Response**: API returns `job_id` and status `pending` to portal
4. **Worker Processing**: Worker consumes event and collects statistics
5. **Callback**: Worker POSTs results to API `/internal/statistics-callback`
6. **Persistence**: API saves statistics to TimescaleDB
7. **Broadcast**: API broadcasts update via WebSocket to subscribed clients
8. **UI Update**: Portal receives WebSocket event and updates display

## Components

### 1. Database: TimescaleDB

#### Hypertable Schema

```sql
CREATE TABLE confluence_statistics (
    id SERIAL PRIMARY KEY,
    space_key VARCHAR(255) NOT NULL,
    space_name VARCHAR(500),
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Basic statistics
    total_pages INTEGER NOT NULL,
    total_size_bytes BIGINT NOT NULL,
    contributor_count INTEGER NOT NULL,
    last_updated TIMESTAMPTZ,
    
    -- Detailed statistics (JSONB)
    page_breakdown_by_type JSONB,
    attachment_stats JSONB,
    version_count INTEGER,
    
    -- Comprehensive statistics (JSONB)
    user_activity JSONB,
    page_views JSONB,
    comment_counts JSONB,
    link_analysis JSONB,
    
    -- Metadata
    collection_time_seconds FLOAT,
    metadata JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('confluence_statistics', 'timestamp');
```

#### Continuous Aggregates

**Hourly Statistics**:
```sql
CREATE MATERIALIZED VIEW confluence_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    space_key,
    time_bucket('1 hour', timestamp) AS hour,
    AVG(total_pages) AS avg_pages,
    MAX(total_pages) AS max_pages,
    MIN(total_pages) AS min_pages,
    COUNT(*) AS sample_count
FROM confluence_statistics
GROUP BY space_key, hour;
```

**Daily Statistics**:
```sql
CREATE MATERIALIZED VIEW confluence_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    space_key,
    time_bucket('1 day', timestamp) AS day,
    AVG(total_pages) AS avg_pages,
    COUNT(*) AS sample_count
FROM confluence_statistics
GROUP BY space_key, day;
```

### 2. API Endpoints

#### POST /confluence/statistics-async

Initiate async statistics collection.

**Request**:
```json
{
  "space_key": "AIARC"
}
```

**Response** (200 OK):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "space_key": "AIARC",
  "status": "pending",
  "estimated_time_seconds": 30,
  "created_at": "2025-11-23T10:00:00Z"
}
```

#### POST /internal/statistics-callback

Internal endpoint for worker callbacks (not exposed to portal).

**Request**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "space_key": "AIARC",
  "status": "completed",
  "statistics": {
    "space_key": "AIARC",
    "space_name": "AI Architecture",
    "timestamp": "2025-11-23T10:00:45Z",
    "basic": {
      "total_pages": 100,
      "total_size_bytes": 628775,
      "contributor_count": 5,
      "last_updated": "2025-11-02T13:26:57Z"
    },
    "detailed": {
      "page_breakdown_by_type": {"page": 95, "blogpost": 5},
      "attachment_stats": {"count": 50, "total_size_bytes": 10485760},
      "version_count": 250
    },
    "comprehensive": {
      "user_activity": {
        "John Doe": {"pages_created": 50, "total_edits": 120},
        "Jane Smith": {"pages_created": 30, "total_edits": 80}
      },
      "comment_counts": {"total": 150},
      "link_analysis": {"internal": 300, "external": 50}
    },
    "collection_time_seconds": 45.2
  },
  "error_message": null
}
```

#### GET /confluence/statistics-history/{space_key}

Query historical statistics with time range filtering.

**Query Parameters**:
- `start_date`: ISO 8601 date (optional, default: 7 days ago)
- `end_date`: ISO 8601 date (optional, default: now)
- `granularity`: `raw`, `hourly`, or `daily` (default: `raw`)
- `limit`: Maximum entries (1-1000, default: 100)

**Response** (200 OK):
```json
{
  "space_key": "AIARC",
  "entries": [
    {
      "id": 123,
      "space_key": "AIARC",
      "space_name": "AI Architecture",
      "timestamp": "2025-11-23T10:00:45Z",
      "total_pages": 100,
      "total_size_bytes": 628775,
      "contributor_count": 5,
      "collection_time_seconds": 45.2,
      "metadata": {...}
    }
  ],
  "total": 1,
  "time_range": {
    "start": "2025-11-16T10:00:00Z",
    "end": "2025-11-23T10:00:00Z"
  },
  "granularity": "raw"
}
```

### 3. WebSocket Protocol

#### Connection

Connect to: `ws://localhost/api/ws`

#### Messages

**Subscribe to Space**:
```json
{
  "type": "subscribe",
  "space_key": "AIARC"
}
```

**Statistics Update** (Server → Client):
```json
{
  "type": "statistics_update",
  "space_key": "AIARC",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "statistics": {...}
}
```

**Heartbeat**:
```json
{
  "type": "ping"
}
```

**Response**:
```json
{
  "type": "pong"
}
```

### 4. Worker Task

#### Task Name

`src.worker.tasks.confluence.collect_confluence_statistics`

#### Event Payload

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "space_key": "AIARC",
  "timestamp": "2025-11-23T10:00:00Z",
  "callback_url": "http://odin-api:8001/internal/statistics-callback"
}
```

#### Retry Configuration

- **Max Retries**: 3
- **Retry Delay**: 60 seconds
- **Timeout**: 3600 seconds (1 hour)

## Configuration

### Environment Variables

#### API Service

```bash
# PostgreSQL with TimescaleDB
POSTGRES_DSN=postgresql+asyncpg://odin:password@postgresql:5432/odin_db

# RabbitMQ
RABBITMQ_URL=amqp://odin:password@rabbitmq:5672/

# WebSocket (auto-configured)
```

#### Worker Service

```bash
# Celery Broker
CELERY_BROKER_URL=amqp://odin:password@rabbitmq:5672//

# Celery Result Backend
CELERY_RESULT_BACKEND=db+postgresql://odin:password@postgresql:5432/odin_db

# API Callback
API_CALLBACK_URL=http://odin-api:8001

# Confluence Credentials (from Vault)
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-root-token
```

#### Docker Compose

```yaml
services:
  postgresql:
    image: timescale/timescaledb:latest-pg16
    volumes:
      - ./scripts/init-timescaledb.sql:/docker-entrypoint-initdb.d/02-init-timescaledb.sql:ro
```

## Usage Examples

### Portal JavaScript

```javascript
// Initialize WebSocket connection
const ws = window.confluenceWS;

// Subscribe to space updates
ws.subscribe('AIARC');

// Request async statistics
const response = await fetch('/confluence/statistics-async', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({space_key: 'AIARC'})
});
const job = await response.json();
console.log('Job ID:', job.job_id);

// Listen for updates
window.addEventListener('confluenceStatisticsUpdate', (event) => {
    const {spaceKey, jobId, status, statistics} = event.detail;
    if (status === 'completed') {
        displayStatistics(statistics);
    }
});
```

### Python Worker

```python
from src.worker.tasks.confluence import collect_confluence_statistics

# Task is automatically dispatched from queue
# Manual dispatch example:
event = {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "space_key": "AIARC",
    "timestamp": "2025-11-23T10:00:00Z",
    "callback_url": "http://odin-api:8001/internal/statistics-callback"
}
collect_confluence_statistics.delay(event)
```

## Performance Considerations

### Scalability

- **Small Spaces** (< 100 pages): ~5 seconds
- **Medium Spaces** (100-1000 pages): ~30 seconds
- **Large Spaces** (1000-10000 pages): ~5 minutes
- **Very Large Spaces** (> 10000 pages): ~30 minutes

### Optimization

1. **Worker Concurrency**: Increase worker processes for parallel job processing
2. **Pagination**: Worker fetches pages in batches of 100
3. **Connection Pooling**: Reuse HTTP connections to Confluence
4. **TimescaleDB Compression**: Data older than 7 days is compressed
5. **Data Retention**: Data older than 365 days is automatically deleted

### Limitations

- Maximum 10 concurrent statistics jobs per worker
- Queue size limit: 1000 pending jobs
- WebSocket connections: Maximum 100 simultaneous clients
- TimescaleDB query timeout: 60 seconds

## Troubleshooting

### Job Stuck in Pending

**Symptoms**: Job status remains `pending` after 5 minutes

**Possible Causes**:
1. Worker not running or not consuming queue
2. RabbitMQ connection issues
3. Queue name mismatch

**Resolution**:
```bash
# Check worker status
docker logs odin-worker

# Check RabbitMQ queues
docker exec odin-rabbitmq rabbitmqctl list_queues

# Restart worker
docker restart odin-worker
```

### WebSocket Not Connecting

**Symptoms**: No real-time updates received

**Possible Causes**:
1. Nginx not proxying WebSocket correctly
2. API WebSocket endpoint not initialized
3. Client not subscribed to space

**Resolution**:
```bash
# Check nginx config
docker exec odin-nginx cat /etc/nginx/nginx.conf | grep upgrade

# Check API logs
docker logs odin-api | grep WebSocket

# Test WebSocket connection
wscat -c ws://localhost/api/ws
```

### Statistics Not Saved

**Symptoms**: Callback succeeds but no data in TimescaleDB

**Possible Causes**:
1. TimescaleDB extension not installed
2. Table not converted to hypertable
3. Permission issues

**Resolution**:
```bash
# Check TimescaleDB
docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT * FROM timescaledb_information.hypertables;"

# Check permissions
docker exec odin-postgresql psql -U odin -d odin_db -c "\\dp confluence_statistics"

# Reinitialize database
docker-compose down -v
docker-compose up -d
```

### Confluence API Errors

**Symptoms**: Worker task fails with 401 or 403

**Possible Causes**:
1. Invalid Confluence credentials
2. API token expired
3. Insufficient permissions

**Resolution**:
```bash
# Check Vault credentials
docker exec odin-vault vault kv get secret/confluence/credentials

# Update credentials
docker exec -i odin-vault sh -c 'vault kv put secret/confluence/credentials \
  base_url="https://domain.atlassian.net/wiki" \
  email="user@example.com" \
  api_token="new_token"'
```

## Security

### Authentication

- **API Internal Endpoint**: Should be restricted to worker network
- **WebSocket**: Consider adding token-based authentication
- **Vault Credentials**: Never log or expose in error messages

### Best Practices

1. Use HTTPS/WSS in production
2. Implement rate limiting on async statistics endpoint
3. Validate job_id to prevent unauthorized access
4. Encrypt sensitive data in TimescaleDB
5. Rotate Confluence API tokens regularly

## Monitoring

### Metrics to Track

- Statistics job completion rate
- Average collection time per space size
- WebSocket connection count
- RabbitMQ queue depth
- TimescaleDB query performance
- Worker task failure rate

### Logging

**API**:
```python
logger.info(f"Statistics job created: {job_id}")
logger.info(f"Broadcast statistics for {space_key} to {sent_count} clients")
```

**Worker**:
```python
logger.info(f"Starting statistics collection: job_id={job_id}, space_key={space_key}")
logger.info(f"Statistics collection completed: pages={total_pages}, time={collection_time:.2f}s")
```

## Future Enhancements

1. **Progress Updates**: Stream progress percentage during collection
2. **Scheduled Collection**: Periodic statistics collection via Celery Beat
3. **Comparison View**: Compare statistics across time periods
4. **Alerts**: Notify on significant changes (e.g., page count drop)
5. **Export**: Export historical data to CSV/JSON
6. **Caching**: Cache recent statistics for instant display
7. **Analytics Dashboard**: Visual analytics with charts and trends

## References

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [Confluence Cloud API](https://developer.atlassian.com/cloud/confluence/rest/v1/intro/)

