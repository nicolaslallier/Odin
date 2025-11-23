# Health Monitoring Pipeline Guide

**Version:** 1.7.1  
**Last Updated:** November 23, 2025

## Overview

The Odin Health Monitoring Pipeline is an automated system that continuously monitors the health of all infrastructure and application services, records health data to TimescaleDB for historical analysis, and provides comprehensive logging with correlation IDs for AI-powered inspection and troubleshooting.

## Architecture

```
┌──────────────┐
│ Celery Beat  │  Triggers every 1 minute
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Worker: collect_and_record_health_checks()               │
│                                                            │
│ 1. Generate UUID correlation_id                           │
│ 2. Initialize structured logger with correlation_id       │
│ 3. Collect health from all services:                      │
│    - Infrastructure (DB, Storage, Queue, Vault, Ollama)   │
│    - Applications (API, Worker, Beat, Flower)             │
│ 4. Send to API with X-Correlation-ID header               │
│ 5. Log results (INFO/ERROR) with correlation_id           │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
            ┌─────────────┐
            │   Nginx     │  Routes /api/health/* → api-health:8004
            └──────┬──────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│ Health API: POST /health/record                          │
│                                                            │
│ 1. Extract X-Correlation-ID from header                   │
│ 2. Initialize logger with correlation_id                  │
│ 3. Log incoming request with correlation_id               │
│ 4. Pass correlation_id to repository                      │
│ 5. Log success/failure with correlation_id                │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│ HealthRepository: insert_health_checks()                 │
│                                                            │
│ 1. Merge correlation_id into each check's metadata        │
│ 2. Batch insert to service_health_checks table            │
│ 3. Return count of inserted records                       │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
            ┌─────────────┐
            │ TimescaleDB │  Hypertable: service_health_checks
            │             │  - Stores health data with timestamps
            │             │  - Metadata includes correlation_id
            └─────────────┘
```

## Correlation ID Flow

### Purpose

The correlation ID is a UUID4 string that uniquely identifies each health check run. It enables:

1. **Tracking**: Follow a single health check run through all components
2. **AI Inspection**: Query logs by correlation_id to understand what happened
3. **Debugging**: Identify issues in specific runs without confusion
4. **Analysis**: Correlate health data with log events

### Lifecycle

1. **Generation**: Worker generates UUID4 at the start of `collect_and_record_health_checks()`
2. **Worker Context**: Included in all worker logs via structured logging
3. **HTTP Transport**: Sent to API via `X-Correlation-ID` header
4. **API Context**: Extracted from header and included in all API logs
5. **Database Storage**: Stored in `metadata.correlation_id` field for each health check record
6. **Result Propagation**: Returned in worker task result for Celery task tracking

### Format

```
550e8400-e29b-41d4-a716-446655440000
```

Pure UUID4 string (36 characters with hyphens).

## Structured Logging

### Log Structure

All logs follow a structured format with correlation_id for AI inspection:

```json
{
    "timestamp": "2025-11-23T10:30:00.123456Z",
    "level": "INFO",
    "service": "worker",
    "logger": "src.worker.tasks.scheduled",
    "task_id": "celery-task-uuid",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Health check collection completed successfully",
    "metadata": {
        "total_checks": 10,
        "healthy": 8,
        "unhealthy": 2,
        "recorded": 10,
        "elapsed_seconds": 1.23
    }
}
```

### Worker Logs

The worker emits logs at key stages:

1. **Start**: INFO level when collection begins
2. **Recording Success**: INFO level when API records checks successfully
3. **Recording Failure**: ERROR level when API recording fails
4. **Completion Success**: INFO level when collection completes without errors
5. **Completion Partial**: ERROR level when collection completes with some errors
6. **Exception**: ERROR level with stack trace when unexpected exception occurs

### API Logs

The API emits logs at key stages:

1. **Incoming Request**: INFO level when receiving health check batch
2. **Recording Success**: INFO level when TimescaleDB insert succeeds
3. **Recording Failure**: ERROR level when TimescaleDB insert fails

## Database Schema

### Table: service_health_checks

```sql
CREATE TABLE service_health_checks (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    is_healthy BOOLEAN NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
);

-- Converted to TimescaleDB hypertable
SELECT create_hypertable('service_health_checks', 'timestamp');
```

### Metadata Fields

Each health check record includes metadata with correlation tracking:

```json
{
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "run_timestamp": "2025-11-23T10:30:00.123456Z"
}
```

## Querying Health Data

### Query by Correlation ID

Find all health checks from a specific run:

```sql
SELECT 
    timestamp,
    service_name,
    service_type,
    is_healthy,
    response_time_ms,
    error_message,
    metadata->>'correlation_id' as correlation_id
FROM service_health_checks
WHERE metadata->>'correlation_id' = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY timestamp DESC;
```

### Query Recent Unhealthy Services

```sql
SELECT 
    service_name,
    service_type,
    timestamp,
    error_message,
    metadata->>'correlation_id' as correlation_id
FROM service_health_checks
WHERE is_healthy = false
    AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Query Health History for Service

```sql
SELECT 
    timestamp,
    is_healthy,
    response_time_ms,
    metadata->>'correlation_id' as correlation_id
FROM service_health_checks
WHERE service_name = 'database'
    AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

## AI Inspection

### Querying Logs by Correlation ID

Use the Logs API to query logs for a specific health check run:

```bash
# Get all logs for a specific health check run
curl -X POST http://localhost/api/logs/search \
  -H "Content-Type: application/json" \
  -d '{
    "search": "correlation_id:550e8400-e29b-41d4-a716-446655440000",
    "limit": 100
  }'
```

### Example AI Inspection Query

```python
import httpx

# 1. Get recent health check runs with failures
response = httpx.get(
    "http://localhost/api/health/history",
    params={
        "start_time": "2025-11-23T00:00:00Z",
        "end_time": "2025-11-23T23:59:59Z",
        "limit": 100
    }
)
health_data = response.json()

# 2. Find correlation IDs with unhealthy services
unhealthy_runs = [
    record["metadata"]["correlation_id"]
    for record in health_data["records"]
    if not record["is_healthy"]
]

# 3. Get logs for each unhealthy run
for correlation_id in unhealthy_runs:
    logs_response = httpx.post(
        "http://localhost/api/logs/search",
        json={
            "search": f"correlation_id:{correlation_id}",
            "limit": 100
        }
    )
    logs = logs_response.json()
    
    # 4. Analyze logs with AI/LLM
    analysis_response = httpx.post(
        "http://localhost/api/logs/analyze",
        json={
            "log_ids": [log["id"] for log in logs["logs"]],
            "analysis_type": "root_cause"
        }
    )
    print(analysis_response.json())
```

## Troubleshooting

### Health Checks Not Recording

**Symptom**: Worker runs but no data appears in TimescaleDB.

**Diagnosis**:

1. Check worker logs for correlation_id and errors:
   ```bash
   docker logs odin-worker | grep correlation_id
   ```

2. Verify nginx routing is working:
   ```bash
   curl -X GET http://localhost/api/health/
   ```

3. Check if Health API microservice is running:
   ```bash
   docker ps | grep api-health
   ```

**Solution**:

1. Start Health API microservice:
   ```bash
   ./scripts/start-api-service.sh health
   ```

2. Verify nginx configuration for `/api/health/` route

### Correlation ID Not in Logs

**Symptom**: Logs don't include correlation_id field.

**Diagnosis**:

1. Check worker logging configuration:
   ```bash
   docker exec odin-worker env | grep LOG
   ```

2. Verify structured logging is enabled (JSON format)

**Solution**:

1. Ensure `use_json=True` in worker logging config
2. Restart worker to apply configuration changes

### Partial Health Check Failures

**Symptom**: Worker reports `status: "partial"` with errors.

**Diagnosis**:

1. Query logs by correlation_id to see which services failed:
   ```python
   # Use correlation_id from worker result
   logs = get_logs_by_correlation_id(correlation_id)
   ```

2. Check health of reported services directly

**Solution**:

1. Restart unhealthy services
2. Verify network connectivity between services
3. Check service logs for specific errors

### API Recording Failures

**Symptom**: Worker collects checks but API returns 500 error.

**Diagnosis**:

1. Check API logs with correlation_id:
   ```bash
   docker logs api-health | grep <correlation_id>
   ```

2. Verify TimescaleDB connection:
   ```bash
   docker exec -it timescaledb psql -U odin -d odin_health -c "SELECT 1;"
   ```

**Solution**:

1. Verify TimescaleDB is running and healthy
2. Check database credentials in API configuration
3. Verify `service_health_checks` table exists and is a hypertable

## Configuration

### Environment Variables

**Worker**:
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_LEVEL_DB_MIN`: Minimum level for database logging (default: INFO)
- `LOG_BUFFER_SIZE`: Log buffer size (default: 100)
- `LOG_BUFFER_TIMEOUT`: Log buffer timeout in seconds (default: 5.0)

**API**:
- `DATABASE_URL`: PostgreSQL connection string for TimescaleDB
- `LOG_LEVEL`: API logging level (default: INFO)

### Beat Schedule

Configured in `src/worker/beat_schedule.py`:

```python
"collect-health-checks": {
    "task": "src.worker.tasks.scheduled.collect_and_record_health_checks",
    "schedule": timedelta(minutes=1),
    "options": {"expires": 60},
}
```

To change frequency, modify the `timedelta(minutes=1)` value.

## Monitoring

### Flower Dashboard

Monitor health check tasks in real-time:

```
http://localhost/flower/
```

Look for tasks named `src.worker.tasks.scheduled.collect_and_record_health_checks`.

### Health Status Dashboard

View current health status:

```bash
# Latest health for all services
curl http://localhost/api/health/latest

# Health history
curl "http://localhost/api/health/history?start_time=2025-11-23T00:00:00Z&end_time=2025-11-23T23:59:59Z"
```

### Circuit Breaker States

Check circuit breaker states for services:

```bash
curl http://localhost/api/health/circuit-breakers
```

## Best Practices

1. **Always use correlation_id** when investigating health issues
2. **Query logs by correlation_id** before diving into individual service logs
3. **Monitor unhealthy trends** over time, not just individual failures
4. **Set up alerts** based on health check failures with correlation tracking
5. **Use AI analysis** to identify patterns across multiple health check runs
6. **Archive old health data** but keep correlation_id mapping for investigation

## API Reference

### POST /health/record

Record batch of health checks to TimescaleDB.

**Headers**:
- `X-Correlation-ID` (optional): UUID for tracking this health check run

**Request**:
```json
{
    "checks": [
        {
            "service_name": "database",
            "service_type": "infrastructure",
            "is_healthy": true,
            "response_time_ms": 12.5,
            "error_message": null,
            "metadata": {}
        }
    ],
    "timestamp": "2025-11-23T10:30:00Z"
}
```

**Response** (201):
```json
{
    "recorded": 1,
    "timestamp": "2025-11-23T10:30:00Z",
    "message": "Health checks recorded successfully"
}
```

### GET /health/history

Query historical health check data.

**Parameters**:
- `start_time` (required): Start time (ISO format)
- `end_time` (required): End time (ISO format)
- `service_names` (optional): Filter by service names
- `service_type` (optional): Filter by service type
- `limit` (optional): Maximum records (default: 1000)

**Response**:
```json
{
    "records": [...],
    "total": 100,
    "start_time": "2025-11-23T00:00:00Z",
    "end_time": "2025-11-23T23:59:59Z"
}
```

### GET /health/latest

Get latest health status for all services.

**Response**:
```json
{
    "services": {
        "database": true,
        "storage": true,
        "queue": true,
        "vault": true,
        "ollama": true,
        "api": true,
        "worker": true,
        "beat": true,
        "flower": true
    },
    "timestamp": "2025-11-23T10:30:00Z"
}
```

## See Also

- [HEALTH_DASHBOARD_v1.1.0.md](HEALTH_DASHBOARD_v1.1.0.md) - Web interface for health monitoring
- [HEALTH_TIMESERIES_GUIDE.md](HEALTH_TIMESERIES_GUIDE.md) - TimescaleDB setup and queries
- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - Structured logging configuration
- [MICROSERVICES_GUIDE.md](MICROSERVICES_GUIDE.md) - Microservices architecture

