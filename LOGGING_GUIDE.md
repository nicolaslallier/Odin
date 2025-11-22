# Centralized Logging System Guide

**Version:** 1.2.0  
**Last Updated:** 2024-11-22

## Overview

Odin v1.2.0 introduces a comprehensive centralized logging system that captures all application and infrastructure logs to PostgreSQL timeseries tables with LLM-powered analysis capabilities.

## Features

- ✅ **Centralized Storage**: All logs stored in PostgreSQL with efficient indexing
- ✅ **Structured Logging**: JSON-formatted logs with correlation IDs
- ✅ **Auto-Cleanup**: Automatic 30-day retention policy (configurable)
- ✅ **Web Viewer**: Real-time log viewer with advanced search and filtering
- ✅ **LLM Analysis**: AI-powered root cause analysis and pattern detection
- ✅ **Service Coverage**: Captures logs from API, Worker, Web, and Nginx

## Architecture

### Components

1. **DatabaseLogHandler** (`src/api/logging_config.py`)
   - Async log handler with buffering
   - Batch inserts to reduce database load
   - Graceful fallback on connection failures

2. **Log Repository** (`src/api/repositories/log_repository.py`)
   - Data access layer for log queries
   - Full-text search support
   - Correlation ID tracking

3. **Log API** (`src/api/routes/logs.py`)
   - RESTful endpoints for log access
   - Statistics and analytics
   - LLM-powered analysis

4. **Web Viewer** (`/logs`)
   - Real-time log monitoring
   - Advanced filtering and search
   - Export capabilities

### Database Schema

Logs are stored in the `application_logs` table with the following structure:

```sql
CREATE TABLE application_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
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
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Indexes are created on:
- `timestamp` (DESC)
- `level`
- `service`
- `request_id`
- `task_id`
- Full-text search on `message`
- JSONB queries on `metadata`

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Log retention (days)
LOG_RETENTION_DAYS=30

# Buffer settings
LOG_BUFFER_SIZE=100
LOG_BUFFER_TIMEOUT=5.0

# Minimum level to store in DB
LOG_LEVEL_DB_MIN=INFO
```

### Logging Levels

- **DEBUG**: Detailed diagnostic information (not stored by default)
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical issues requiring immediate attention

## Usage

### Accessing the Log Viewer

Navigate to `http://localhost/logs` in your browser.

### Filtering Logs

**By Level:**
```
Level: ERROR
```

**By Service:**
```
Service: api
```

**By Time Range:**
```
Start Time: 2024-01-01T00:00:00
End Time: 2024-01-02T00:00:00
```

**Search Messages:**
```
Search: database connection
```

### Correlation IDs

Logs are automatically tagged with correlation IDs:

- **request_id**: Tracks HTTP requests across services
- **task_id**: Tracks Celery tasks

Click on a log's correlation ID to view all related logs.

### API Endpoints

#### Get Logs
```bash
GET /api/v1/logs?level=ERROR&service=api&limit=100
```

#### Search Logs
```bash
GET /api/v1/logs/search?q=database&limit=50
```

#### Get Statistics
```bash
GET /api/v1/logs/stats
```

#### Correlate Logs
```bash
GET /api/v1/logs/correlate?request_id=abc-123
```

#### Analyze with LLM
```bash
POST /api/v1/logs/analyze
Content-Type: application/json

{
  "log_ids": [1, 2, 3],
  "analysis_type": "root_cause",
  "max_logs": 50
}
```

### LLM Analysis Types

1. **root_cause**: Identify root causes of errors
2. **pattern**: Detect recurring patterns
3. **anomaly**: Find unusual log sequences
4. **correlation**: Link related events
5. **summary**: Summarize errors

## Programmatic Logging

### Adding Correlation IDs

```python
from src.api.logging_config import get_logger
import uuid

# Create logger with correlation ID
request_id = str(uuid.uuid4())
logger = get_logger(__name__, request_id=request_id)

logger.info("Processing request", extra={"user_id": "user123"})
```

### Custom Metadata

```python
logger.info(
    "User action completed",
    extra={
        "extra_fields": {
            "action": "file_upload",
            "file_size": 1024000,
            "duration_ms": 250
        }
    }
)
```

## Maintenance

### Manual Cleanup

Clean up logs older than 30 days:

```python
from src.worker.tasks.maintenance import cleanup_old_logs_task

result = cleanup_old_logs_task.apply_async(args=[30])
print(result.get())
```

### Scheduled Cleanup

Cleanup runs automatically daily at 2:30 AM via Celery Beat:

```python
# Beat schedule in src/worker/beat_schedule.py
"cleanup-old-logs": {
    "task": "maintenance.cleanup_old_logs",
    "schedule": crontab(hour=2, minute=30),
}
```

### Database Initialization

Initialize logging schema:

```bash
./scripts/init-postgresql.sh
```

Or manually:

```bash
docker exec -i odin-postgresql psql -U odin -d odin_db < scripts/init-logging.sql
```

## Monitoring

### Health Check

The log system health is included in service health checks:

```bash
GET /health
```

### Statistics

View log statistics:

```bash
curl http://localhost:8001/api/v1/logs/stats
```

Response:
```json
{
  "time_range": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-02T00:00:00Z"
  },
  "total_logs": 15000,
  "by_level": {
    "DEBUG": 0,
    "INFO": 12000,
    "WARNING": 2500,
    "ERROR": 450,
    "CRITICAL": 50
  },
  "by_service": {
    "api": {...},
    "worker": {...},
    "web": {...}
  }
}
```

## Troubleshooting

### Logs Not Appearing

1. **Check database connection**:
   ```bash
   docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT COUNT(*) FROM application_logs;"
   ```

2. **Verify logging configuration**:
   - Ensure `POSTGRES_DSN` is set correctly
   - Check `LOG_LEVEL_DB_MIN` (logs below this level won't be stored)

3. **Check buffer settings**:
   - Logs are buffered (default: 100 records or 5 seconds)
   - Wait a few seconds or trigger more logs

### Log Viewer Not Loading

1. **Check API connectivity**:
   ```bash
   curl http://localhost:8001/api/v1/logs?limit=10
   ```

2. **Check browser console** for JavaScript errors

3. **Verify web service** is running:
   ```bash
   docker ps | grep portal
   ```

### LLM Analysis Failing

1. **Check Ollama service**:
   ```bash
   curl http://localhost/ollama/api/tags
   ```

2. **Verify model availability**:
   ```bash
   docker exec odin-ollama ollama list
   ```

3. **Pull required model**:
   ```bash
   docker exec odin-ollama ollama pull llama2
   ```

### Database Performance

For large log volumes, consider:

1. **Partition tables** by month
2. **Adjust retention** to fewer days
3. **Increase buffer size** to reduce insert frequency
4. **Add indexes** for specific query patterns

## Best Practices

### 1. Use Structured Logging

```python
# Good
logger.info("User login", extra={"user_id": "123", "ip": "192.168.1.1"})

# Avoid
logger.info(f"User 123 logged in from 192.168.1.1")
```

### 2. Add Correlation IDs

Always include request_id or task_id for traceability:

```python
logger = get_logger(__name__, request_id=request.state.request_id)
```

### 3. Use Appropriate Levels

- DEBUG: Verbose diagnostic info (development only)
- INFO: Normal operations
- WARNING: Recoverable issues
- ERROR: Failures requiring attention
- CRITICAL: System-wide failures

### 4. Don't Log Secrets

Never log passwords, tokens, or sensitive data:

```python
# Bad
logger.info(f"Connecting with password: {password}")

# Good
logger.info("Connecting to database", extra={"host": host})
```

### 5. Optimize Log Volume

- Set appropriate `LOG_LEVEL_DB_MIN`
- Use DEBUG level sparingly
- Aggregate repetitive messages

## Performance

### Buffer Tuning

Adjust based on log volume:

- **High volume** (>1000 logs/sec): Increase `LOG_BUFFER_SIZE` to 500-1000
- **Low latency** needed: Decrease `LOG_BUFFER_TIMEOUT` to 1-2 seconds
- **Database load** concerns: Increase both buffer size and timeout

### Query Optimization

The system includes optimized indexes. For custom queries:

```sql
-- Use indexes
EXPLAIN ANALYZE
SELECT * FROM application_logs
WHERE service = 'api'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC
LIMIT 100;
```

## Security

### Access Control

- Log API requires authentication (configure in production)
- Sensitive data should not be logged
- Database credentials stored securely in environment variables

### Data Privacy

- Logs may contain PII - ensure compliance with regulations
- Configure retention period based on requirements
- Consider anonymizing user_id fields

## Migration & Upgrades

### From v1.1.0 to v1.2.0

1. **Run database migration**:
   ```bash
   ./scripts/init-postgresql.sh
   ```

2. **Update environment** variables in `.env`

3. **Restart services**:
   ```bash
   docker-compose restart
   ```

4. **Verify logging**:
   ```bash
   curl http://localhost:8001/api/v1/logs/stats
   ```

## Support

For issues or questions:

1. Check logs: `docker-compose logs api worker web`
2. Verify health: `curl http://localhost/health`
3. Review this guide
4. Check GitHub issues

## Version History

- **v1.2.0** (2024-11-22): Initial centralized logging system
  - PostgreSQL timeseries storage
  - Web log viewer
  - LLM-powered analysis
  - Automatic cleanup

---

**Next Steps:**
- Visit the [Log Viewer](http://localhost/logs)
- Try [LLM Analysis](#llm-analysis-types)
- Review [Best Practices](#best-practices)

