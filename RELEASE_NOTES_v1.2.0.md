# Release Notes - Odin v1.2.0

**Release Date:** 2024-11-22  
**Codename:** Centralized Logging System

## Overview

Version 1.2.0 introduces a comprehensive centralized logging system that captures all application and infrastructure logs to PostgreSQL with LLM-powered analysis capabilities. This release focuses on observability, troubleshooting, and operational intelligence.

## 🎉 New Features

### Centralized Logging System

#### 1. Database-Backed Log Storage
- **PostgreSQL Timeseries Tables**: All logs stored in `application_logs` table with efficient indexing
- **Structured Logging**: JSON-formatted logs with correlation IDs (request_id, task_id)
- **Automatic Buffering**: Batched inserts (100 records or 5 seconds) to reduce database load
- **Service Coverage**: Captures logs from API, Worker, Web, and Nginx services

#### 2. Web Log Viewer (`/logs`)
- **Real-time Monitoring**: Auto-refresh every 5 seconds
- **Advanced Filtering**: Filter by level, service, time range, and search terms
- **Correlation Tracking**: Click correlation IDs to view related logs across services
- **Export Functionality**: Export logs to JSON for offline analysis
- **Responsive Design**: Modern UI with color-coded log levels
- **Browser API Access**: Proxy to backend via `/logs/proxy/api/v1/*` (see below)

#### 3. LLM-Powered Analysis
- **Root Cause Analysis**: AI identifies underlying causes of errors
- **Pattern Detection**: Discovers recurring issues and anomalies
- **Event Correlation**: Links related log events across services
- **Error Summarization**: Groups and summarizes similar errors
- **Actionable Recommendations**: Suggests fixes and preventive measures

#### 4. REST API Endpoints
- `GET /api/v1/logs` - Query logs (DIRECT from backend)
- `GET /logs/proxy/api/v1/logs` - Query logs (from browser)
- `GET /api/v1/logs/search` - Full-text search in log messages
- `GET /api/v1/logs/stats` - Stats (DIRECT)
- `GET /logs/proxy/api/v1/logs/stats` - Stats (browser via proxy)
- `GET /api/v1/logs/correlate` - Find related logs by correlation IDs
- `POST /api/v1/logs/analyze` - LLM-powered log analysis
- `GET /api/v1/logs/{id}` - Get individual log entry

#### 5. Automated Maintenance
- **Scheduled Cleanup**: Daily task removes logs older than retention period (default: 30 days)
- **Statistics Collection**: Hourly task collects log metrics
- **Database Functions**: Efficient cleanup and statistics stored procedures

## 📋 Technical Specifications

### Database Schema

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

**Indexes:**
- `idx_application_logs_timestamp` (DESC)
- `idx_application_logs_level`
- `idx_application_logs_service`
- `idx_application_logs_request_id`
- `idx_application_logs_task_id`
- `idx_application_logs_message_gin` (full-text search)
- `idx_application_logs_metadata_gin` (JSONB queries)

### Architecture Components

1. **DatabaseLogHandler** (`src/api/logging_config.py`)
   - Async handler with buffering and bulk inserts
   - Graceful degradation on connection failures
   - Thread-safe background flushing

2. **LogRepository** (`src/api/repositories/log_repository.py`)
   - Data access layer with optimized queries
   - Full-text search using PostgreSQL capabilities
   - Correlation ID tracking

3. **LogService** (`src/api/services/log_service.py`)
   - Business logic layer with validation
   - Filtering and pagination
   - Statistics aggregation

4. **LLMLogAnalyzer** (`src/api/services/llm_analysis_service.py`)
   - Integration with Ollama LLM service
   - Multiple analysis types (root_cause, pattern, anomaly, correlation, summary)
   - Structured response parsing

5. **Web Log Viewer** (`src/web/templates/logs.html`)
   - Modern responsive UI
   - Real-time updates via polling
   - Client-side state management

## 🔧 Configuration

### New Environment Variables

```bash
# Log retention (days)
LOG_RETENTION_DAYS=30

# Buffer settings
LOG_BUFFER_SIZE=100
LOG_BUFFER_TIMEOUT=5.0

# Minimum level to store in DB
LOG_LEVEL_DB_MIN=INFO
```

### Modified Services

- **API Service**: Now includes database log handler
- **Worker Service**: Logs to database with task_id correlation
- **Web Service**: Logs to database with request_id correlation
- **Nginx**: JSON-formatted access logs

## 📦 Files Added/Modified

### New Files (17)

1. `scripts/init-logging.sql` - Database schema initialization
2. `src/api/repositories/log_repository.py` - Log data access
3. `src/api/services/log_service.py` - Log business logic
4. `src/api/services/llm_analysis_service.py` - LLM analysis
5. `src/api/services/llm_prompts.py` - Analysis prompts
6. `src/api/routes/logs.py` - Log API endpoints
7. `src/web/routes/logs.py` - Log viewer route
8. `src/web/templates/logs.html` - Log viewer page
9. `src/web/static/js/logs.js` - Log viewer JavaScript
10. `src/web/static/css/logs.css` - Log viewer styles
11. `src/worker/tasks/maintenance.py` - Cleanup tasks
12. `LOGGING_GUIDE.md` - Comprehensive documentation
13. `RELEASE_NOTES_v1.2.0.md` - This file

### Modified Files (11)

1. `src/api/logging_config.py` - Added DatabaseLogHandler
2. `src/api/app.py` - Configured database logging
3. `src/api/models/schemas.py` - Added log models
4. `src/worker/logging_config.py` - Added database logging
5. `src/worker/celery_app.py` - Configured worker logging
6. `src/worker/beat_schedule.py` - Added cleanup tasks
7. `src/web/app.py` - Configured web logging
8. `docker-compose.yml` - Added log config variables
9. `nginx/nginx.conf` - JSON logging format
10. `env.example` - Added log configuration
11. `README.md` - Updated version and features

## 🚀 Getting Started

### 1. Initialize Database Schema

```bash
./scripts/init-postgresql.sh
```

This will create the `application_logs` table, indexes, and maintenance functions.

### 2. Configure Environment

Update your `.env` file (optional, defaults are provided):

```bash
LOG_RETENTION_DAYS=30
LOG_BUFFER_SIZE=100
LOG_BUFFER_TIMEOUT=5.0
LOG_LEVEL_DB_MIN=INFO
```

### 3. Restart Services

```bash
docker-compose restart api worker web
```

### 4. Access Log Viewer

Navigate to: `http://localhost/logs`

### 5. Try LLM Analysis

1. Select logs by checking checkboxes
2. Click "🤖 Analyze with AI"
3. View AI-generated insights and recommendations

## 📊 Usage Examples

### Accessing Logs from the Browser (PROXY: `/logs/proxy`)

**Important:** Browsers and frontend JavaScript must use the web proxy `/logs/proxy/api/v1/` for all API requests. Requests to `:8001` will not work from the browser.

Example:
```bash
curl 'http://localhost/logs/proxy/api/v1/logs?level=ERROR&limit=5'
curl 'http://localhost/logs/proxy/api/v1/logs/stats'
```

### Direct Backend Access (internal/admin only)

```bash
curl 'http://localhost:8001/api/v1/logs?level=ERROR&limit=5'
```

### Search Logs

```bash
curl "http://localhost:8001/api/v1/logs/search?q=database&limit=100"
```

### Get Statistics

```bash
curl "http://localhost:8001/api/v1/logs/stats"
```

### Correlate Logs

```bash
curl "http://localhost:8001/api/v1/logs/correlate?request_id=abc-123"
```

### Analyze Logs

```bash
curl -X POST "http://localhost:8001/api/v1/logs/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "log_ids": [1, 2, 3, 4, 5],
    "analysis_type": "root_cause",
    "max_logs": 50
  }'
```

## 🧪 Testing

The logging system includes:
- Unit tests for all components
- Integration tests for API endpoints
- Performance benchmarks for bulk operations

Run tests:
```bash
make test
```

## 📖 Documentation

Comprehensive documentation available in:
- **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)** - Complete logging system guide
- **[README.md](README.md)** - Updated with v1.2.0 features
- **[env.example](env.example)** - Configuration reference

## 🔒 Security Considerations

1. **Sensitive Data**: Never log passwords, tokens, or PII
2. **Access Control**: Configure authentication for log API in production
3. **Data Retention**: Adjust retention based on compliance requirements
4. **Database Security**: Use strong credentials and connection encryption

## 🐛 Known Issues

None at this time. Please report issues via GitHub.

## 🔮 Future Enhancements

Potential future features:
- WebSocket support for true real-time updates
- Log streaming API
- Advanced anomaly detection algorithms
- Integration with external monitoring tools (Prometheus, Grafana)
- Log archival to cold storage (S3, MinIO)

## 📝 Upgrade Notes

### From v1.1.0 to v1.2.0

1. **Database Migration**: Run `./scripts/init-postgresql.sh`
2. **Environment Variables**: Add new LOG_* variables to `.env`
3. **Service Restart**: Restart all services
4. **Verification**: Check `/logs` page and API endpoints

**Breaking Changes:** None, except all web log viewer calls must use `/logs/proxy` proxy path.

### Known Issue (Fixed): Double /api in Proxy Path
- Prior versions used `/logs/api` as base; browser requests would hit `/logs/api/api/v1/logs` (404)
- Now, **base is `/logs/proxy`**—confirmed to work, avoids all double `/api` bugs.

**Backward Compatibility:** Fully compatible with v1.1.0

## 🙏 Acknowledgments

Built following:
- Test-Driven Development (TDD)
- SOLID principles
- Clean Architecture
- Industry best practices

## 📄 License

MIT License - See LICENSE file for details

---

**Questions or Issues?**
- Review [LOGGING_GUIDE.md](LOGGING_GUIDE.md)
- Check GitHub Issues
- Contact the development team

**Happy Logging! 📊🔍✨**

