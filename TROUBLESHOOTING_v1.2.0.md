# Troubleshooting Guide - Odin v1.2.0

## Common Issues and Solutions

### 1. "Bad Gateway" Error

**Symptom**: 502 Bad Gateway when accessing the portal

**Cause**: The `application_logs` table doesn't exist in the database

**Solution**:
```bash
./scripts/init-postgresql.sh
docker-compose restart api worker portal
```

---

### 2. "Failed to fetch" Error in Log Viewer

**Symptom**: Log viewer shows "Error loading logs: Failed to fetch"

**Causes and Solutions**:

#### Cause A: API Endpoint Variable Name Conflict
The `service` parameter in the logs endpoint was conflicting with the `service` variable name (LogService instance).

**Fixed in**: `src/api/routes/logs.py`
- Changed parameter from `service` to `service_filter` with `alias="service"`
- Renamed `service` variable to `log_service` to avoid conflicts

#### Cause B: Browser Cannot Access Internal API Port
The JavaScript was trying to access `http://localhost:8001` (internal Docker network) which is not accessible from the browser.

**Fixed in**: `src/web/routes/logs.py`
- Added API proxy endpoint: `/logs/proxy/{path:path}` (changed from `/logs/api/{path:path}`)
- Changed `api_base_url` in template context to `/logs/proxy`
- The JavaScript appends `/api/v1/logs` to the base URL, resulting in `/logs/proxy/api/v1/logs`

**Path Flow**:
1. Browser: `GET /logs/proxy/api/v1/logs`
2. Portal proxy: `GET http://odin-api:8001/api/v1/logs`
3. API service: Returns logs

**Verification**:
```bash
# Test API directly (from server)
curl http://localhost:8001/api/v1/logs?limit=5

# Test through portal proxy (from browser/server)
curl http://localhost/logs/proxy/api/v1/logs?limit=5

# Check page configuration
curl -s http://localhost/logs | grep API_BASE_URL
# Should show: window.API_BASE_URL = "/logs/proxy";
```

---

### 3. Database Event Loop Errors

**Symptom**: Logs show "RuntimeError: Event loop is closed" or "Task attached to different loop"

**Cause**: The `DatabaseLogHandler` is trying to use async operations in the wrong event loop context.

**Current Status**: 
- Logs are still being captured to the database successfully
- These errors occur during shutdown/restart sequences
- They are warnings that don't affect functionality

**Workaround**: These errors can be safely ignored for now. They appear during service restarts but don't prevent log collection.

**Potential Fix** (for future enhancement):
- Refactor `DatabaseLogHandler` to use a dedicated thread with its own event loop
- Use `asyncio.new_event_loop()` in a background thread
- Ensure proper cleanup during shutdown

---

### 4. No Logs Appearing in Viewer

**Symptom**: Log viewer loads but shows "No logs found"

**Troubleshooting Steps**:

1. **Check if logs are in database**:
```bash
docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT COUNT(*) FROM application_logs;"
```

2. **Check API endpoint**:
```bash
curl http://localhost/logs/api/v1/logs?limit=5
```

3. **Check browser console** (F12):
   - Look for network errors
   - Check the API requests being made
   - Verify the API_BASE_URL is set to `/logs/api`

4. **Check API logs**:
```bash
docker logs --tail=50 odin-api
```

---

### 5. LLM Analysis Not Working

**Symptom**: "Analyze with AI" button doesn't work or shows errors

**Troubleshooting**:

1. **Check Ollama service**:
```bash
docker ps | grep ollama
docker logs odin-ollama
```

2. **Test Ollama directly**:
```bash
curl http://localhost:11434/api/tags
```

3. **Check API logs for LLM errors**:
```bash
docker logs odin-api | grep -i llm
```

---

### 6. Portal Proxy Not Working

**Symptom**: 404 errors when accessing `/logs/api/v1/...`

**Solution**:
```bash
# Restart portal to pick up route changes
docker-compose restart portal

# Verify proxy route is loaded
docker logs portal | grep -i "logs/api"
```

---

## Verification Checklist

After fixing any issue, verify the system is working:

### ✓ Database
```bash
# Check table exists
docker exec odin-postgresql psql -U odin -d odin_db -c "\dt application_logs"

# Check logs are being inserted
docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT COUNT(*), MAX(timestamp) FROM application_logs;"
```

### ✓ API Endpoints
```bash
# Direct API access (internal)
curl http://localhost:8001/api/v1/logs?limit=1

# Proxy access (external)
curl http://localhost/logs/api/v1/logs?limit=1

# Statistics
curl http://localhost/logs/api/v1/logs/stats
```

### ✓ Web Portal
```bash
# Check page loads
curl -I http://localhost/logs

# Check JavaScript receives correct API URL
curl -s http://localhost/logs | grep API_BASE_URL
# Should show: window.API_BASE_URL = "/logs/api";
```

### ✓ Services
```bash
# All services running
docker-compose ps

# No critical errors
docker logs odin-api --tail=20
docker logs portal --tail=20
docker logs odin-worker --tail=20
```

---

## Performance Issues

### Slow Log Queries

If log queries are slow (>1 second):

1. **Check database indexes**:
```sql
-- Connect to database
docker exec -it odin-postgresql psql -U odin -d odin_db

-- Check indexes exist
\di application_logs*

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename = 'application_logs';
```

2. **Check table size**:
```sql
SELECT pg_size_pretty(pg_total_relation_size('application_logs'));
```

3. **Run VACUUM ANALYZE**:
```sql
VACUUM ANALYZE application_logs;
```

### Too Many Logs

If you're generating too many logs and filling up disk:

1. **Reduce log retention**:
```bash
# Edit .env
LOG_RETENTION_DAYS=7  # Reduce from 30 to 7 days
```

2. **Manually clean old logs**:
```sql
docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT cleanup_old_logs(7);"
```

3. **Adjust log level**:
```bash
# Edit docker-compose.yml or .env
LOG_LEVEL=WARNING  # Reduce from INFO
```

---

## Debug Mode

To enable detailed debugging:

1. **Set log level to DEBUG**:
```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
```

2. **Enable SQL query logging**:
```yaml
# docker-compose.yml for API service
environment:
  - SQLALCHEMY_ECHO=true
```

3. **Restart services**:
```bash
docker-compose restart api worker portal
```

---

## Getting Help

If issues persist:

1. **Collect logs**:
```bash
# Save all service logs
docker-compose logs > odin_logs.txt

# Save database state
docker exec odin-postgresql psql -U odin -d odin_db -c "\d application_logs" > db_schema.txt
docker exec odin-postgresql psql -U odin -d odin_db -c "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM application_logs;" >> db_schema.txt
```

2. **Check configuration**:
```bash
# Verify environment variables
docker-compose config | grep -A5 -B5 "LOG"
```

3. **Review documentation**:
- `LOGGING_GUIDE.md` - Comprehensive logging system guide
- `RELEASE_NOTES_v1.2.0.md` - Features and changes
- `README.md` - General setup and usage

---

## Quick Fixes

### Reset Everything
```bash
# Stop all services
docker-compose down

# Reinitialize database
./scripts/init-postgresql.sh

# Rebuild and restart
make rebuild
make up

# Wait for services to stabilize
sleep 10

# Verify
curl http://localhost/logs/api/v1/logs/stats
```

### Clear All Logs
```bash
# WARNING: This deletes all log data!
docker exec odin-postgresql psql -U odin -d odin_db -c "TRUNCATE application_logs;"
```

---

**Last Updated**: 2024-11-22  
**Version**: 1.2.0

