# Release Notes - Odin v1.7.1

**Release Date:** November 23, 2025  
**Version:** 1.7.1  
**Codename:** Health Monitoring Pipeline Enhancement

## ✨ Overview

Version 1.7.1 enhances the health monitoring pipeline with correlation ID tracking, nginx routing, and comprehensive structured logging for AI-powered inspection and troubleshooting.

## 🎯 Key Features

### Correlation ID Tracking

Every health check run now has a unique UUID correlation ID that flows through the entire pipeline:

- **Worker**: Generates UUID4 at start of each run
- **HTTP Transport**: Sent via `X-Correlation-ID` header to API
- **API**: Receives and logs correlation ID
- **Database**: Stored in metadata for each health check record
- **Logs**: Included in all structured logs for AI inspection

**Example**:
```json
{
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "success",
    "total_checks": 10,
    "healthy": 8,
    "unhealthy": 2
}
```

### Nginx Routing for Health API

Worker now routes health monitoring requests through nginx instead of direct API access:

- **Before**: `http://odin-api:8001/health/record`
- **After**: `http://nginx/api/health/record`

This ensures:
- Consistent routing with microservices architecture
- Load balancing and failover capabilities
- Centralized access logging in nginx
- Better network isolation and security

### Enhanced Structured Logging

All components now emit structured logs with correlation ID:

**Worker Logs**:
- Start of health check collection
- API recording success/failure
- Final completion status (INFO for success, ERROR for failures)
- Exception handling with stack traces

**API Logs**:
- Incoming health check requests
- Database insertion success/failure
- Error details with correlation ID context

**Log Format**:
```json
{
    "timestamp": "2025-11-23T10:30:00Z",
    "level": "INFO",
    "service": "worker",
    "correlation_id": "550e8400-...",
    "message": "Health checks collected and recorded",
    "metadata": {
        "total_checks": 10,
        "healthy": 8,
        "unhealthy": 2,
        "recorded": 10,
        "elapsed_seconds": 1.23
    }
}
```

### AI Inspection Capability

Query logs and health data by correlation ID for AI-powered analysis:

```python
# Get logs for specific health check run
logs = query_logs(correlation_id="550e8400-...")

# Analyze with AI
analysis = analyze_logs(logs, analysis_type="root_cause")
```

## 🔧 Technical Changes

### Worker (`src/worker/tasks/scheduled.py`)

- Added UUID4 correlation ID generation at task start
- Integrated structured logging with `get_task_logger()`
- Changed API base URL from direct access to nginx routing
- Added `X-Correlation-ID` header to all API requests
- Enhanced logging at all stages (start, record, completion, errors)
- Included correlation_id in task result dictionary

### API (`src/api/routes/health.py`)

- Added `X-Correlation-ID` header parameter to `/health/record` endpoint
- Integrated structured logging with correlation ID context
- Logs incoming requests with correlation ID
- Logs success/failure with correlation ID
- Passes correlation ID to repository layer

### Repository (`src/api/repositories/health_repository.py`)

- Added optional `correlation_id` parameter to `insert_health_checks()`
- Merges correlation ID into metadata field for each health check record
- Stores `run_timestamp` alongside correlation ID in metadata

### Database Schema

Metadata field now includes:
```json
{
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "run_timestamp": "2025-11-23T10:30:00Z"
}
```

## 🧪 Testing

### Unit Tests

**Worker Tests** (`tests/unit/worker/tasks/test_health_collection.py`):
- ✅ Test correlation ID generation
- ✅ Test nginx URL routing
- ✅ Test X-Correlation-ID header inclusion
- ✅ Test structured logging with correlation ID
- ✅ Test error logging includes correlation ID

**API Tests** (`tests/unit/api/routes/test_health_record.py`):
- ✅ Test correlation ID extraction from header
- ✅ Test correlation ID stored in metadata
- ✅ Test logging includes correlation ID
- ✅ Test endpoint without correlation ID (backward compatible)
- ✅ Test error logging with correlation ID

### Integration Tests

**Pipeline Tests** (`tests/integration/worker/test_health_monitoring_pipeline.py`):
- ✅ Complete pipeline with correlation ID (Worker → Nginx → API → DB)
- ✅ Correlation ID propagation verification
- ✅ Structured logging with correlation ID at all stages
- ✅ Nginx routing verification
- ✅ Partial failure handling with correlation ID
- ✅ API unavailable error logging with correlation ID
- ✅ Exception handling includes correlation ID
- ✅ Elapsed time tracking

### Test Coverage

- **Worker**: 100% coverage of new correlation ID and logging code
- **API**: 100% coverage of header extraction and logging
- **Repository**: 100% coverage of metadata storage
- **Integration**: 8 comprehensive end-to-end tests

## 📚 Documentation

### New Documentation

**HEALTH_MONITORING_PIPELINE.md**:
- Architecture overview with diagrams
- Correlation ID lifecycle and flow
- Structured logging format and examples
- Database schema and querying
- AI inspection guide
- Troubleshooting guide
- API reference
- Best practices

### Updated Documentation

- **README.md**: Reference to health monitoring pipeline
- **API_GUIDE.md**: Updated health endpoints documentation

## 🔄 Migration Guide

### No Breaking Changes

This release is **fully backward compatible**. Existing health monitoring continues to work without any changes.

### Optional Migration

To take advantage of correlation ID tracking:

1. **No code changes required** - correlation IDs are automatically generated
2. **Logs**: Query logs by correlation_id for enhanced troubleshooting
3. **Database**: Query `metadata->>'correlation_id'` in health check records

### Example Queries

**Find all health checks from a specific run**:
```sql
SELECT * FROM service_health_checks
WHERE metadata->>'correlation_id' = '550e8400-...';
```

**Get logs for a specific run**:
```bash
curl -X POST http://localhost/api/logs/search \
  -d '{"search": "correlation_id:550e8400-..."}'
```

## 🐛 Bug Fixes

- Fixed direct API access bypassing nginx routing
- Added proper error handling for API recording failures
- Improved logging consistency across worker and API

## ⚡ Performance

- No performance impact - correlation ID generation is negligible
- Structured logging has minimal overhead
- Database metadata field uses efficient JSONB storage

## 🔐 Security

- Nginx routing provides better network isolation
- Correlation IDs are UUIDs (no sensitive information)
- Logs follow existing security practices (no secrets logged)

## 🎓 Best Practices

1. **Always use correlation_id** when investigating health issues
2. **Query logs by correlation_id** before diving into service logs
3. **Set up alerts** based on correlation_id tracking
4. **Use AI analysis** to identify patterns across runs
5. **Archive health data** but keep correlation_id for investigations

## 📖 See Also

- [HEALTH_MONITORING_PIPELINE.md](HEALTH_MONITORING_PIPELINE.md) - Complete pipeline guide
- [HEALTH_TIMESERIES_GUIDE.md](HEALTH_TIMESERIES_GUIDE.md) - TimescaleDB guide
- [LOGGING_GUIDE.md](LOGGING_GUIDE.md) - Structured logging guide
- [MICROSERVICES_GUIDE.md](MICROSERVICES_GUIDE.md) - Microservices architecture

## 🙏 Acknowledgments

This release builds on the solid foundation of v1.7.0's microservices architecture, bringing enhanced observability and AI-powered troubleshooting to health monitoring.

---

**Upgrade Path**: Drop-in replacement - no migration required  
**Rollback**: Safe to rollback to v1.7.0 if needed (correlation IDs will be absent)

For support, see [HEALTH_MONITORING_PIPELINE.md](HEALTH_MONITORING_PIPELINE.md) troubleshooting section.

