# Service Accessibility Testing Guide

This guide explains how to test and diagnose service accessibility issues in the Odin environment.

## Quick Diagnostic

If services are giving you errors, start here:

### 1. Check Service Status

```bash
# Quick diagnostic - shows which services are accessible
make check-services
```

This will test all services and show you exactly which ones are working and which are failing.

### 2. Run Regression Tests

```bash
# Comprehensive test suite for service accessibility
make test-services
```

This runs detailed regression tests that verify:
- Nginx routing is working
- Portal is accessible at root path (/)
- All service endpoints are responding
- Health checks are working
- Error handling is correct

## Common Issues and Fixes

### Issue: "Connection Refused" Errors

**Symptoms:**
- Services return connection errors
- `make check-services` shows CONNECTION ERROR

**Fixes:**
1. Make sure services are running:
   ```bash
   make services-up
   docker ps  # Check all containers are running
   ```

2. Check if portal container is running:
   ```bash
   docker ps | grep portal
   ```

3. If portal is not running, start it:
   ```bash
   docker-compose up -d app
   ```

### Issue: "404 Not Found" Errors

**Symptoms:**
- URLs return 404
- Nginx is running but routes aren't working

**Fixes:**
1. Check nginx configuration:
   ```bash
   docker logs odin-nginx | tail -20
   ```

2. Verify nginx has loaded the correct config:
   ```bash
   docker exec odin-nginx nginx -t  # Test config
   docker exec odin-nginx nginx -s reload  # Reload if needed
   ```

3. Restart nginx:
   ```bash
   docker-compose restart nginx
   ```

### Issue: "Timeout" Errors

**Symptoms:**
- Requests hang and timeout
- Services show as unhealthy

**Fixes:**
1. Check if container is actually running:
   ```bash
   docker ps -a
   ```

2. Check container logs:
   ```bash
   docker logs <container-name>
   ```

3. Restart the specific service:
   ```bash
   docker-compose restart <service-name>
   ```

### Issue: Portal Not Accessible at Root (/)

**Symptoms:**
- http://localhost/ returns error or wrong content
- Portal works at /app/ but not /

**Fixes:**
1. Verify nginx configuration routes / to portal:
   ```bash
   grep -A 5 "location / {" nginx/nginx.conf
   ```

2. Rebuild and restart:
   ```bash
   make down
   make build
   make services-up
   ```

## Detailed Testing

### Test Individual Services

You can test specific aspects:

```bash
# Test only nginx routing
docker-compose run --rm app pytest tests/regression/test_service_accessibility.py::TestNginxRouting -v

# Test only service endpoints
docker-compose run --rm app pytest tests/regression/test_service_accessibility.py::TestServiceEndpoints -v

# Test portal integration
docker-compose run --rm app pytest tests/regression/test_service_accessibility.py::TestServiceIntegration -v

# Test error handling
docker-compose run --rm app pytest tests/regression/test_service_accessibility.py::TestErrorHandling -v
```

### Manual Testing

Test each service manually:

```bash
# Portal
curl http://localhost/
curl http://localhost/health

# Nginx
curl http://localhost/nginx-health

# Ollama
curl http://localhost/ollama/

# n8n
curl http://localhost/n8n/

# RabbitMQ
curl http://localhost/rabbitmq/

# Vault
curl http://localhost/vault/

# MinIO
curl http://localhost/minio/
```

## Service Health Checks

Check container health status:

```bash
# All services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific service health
docker inspect --format='{{.State.Health.Status}}' portal
docker inspect --format='{{.State.Health.Status}}' odin-minio
docker inspect --format='{{.State.Health.Status}}' odin-vault
```

## Troubleshooting Workflow

Follow this workflow when debugging service issues:

1. **Run Diagnostic**
   ```bash
   make check-services
   ```

2. **Check Container Status**
   ```bash
   docker ps -a
   ```

3. **Check Logs** (for failing services)
   ```bash
   docker logs odin-nginx
   docker logs portal
   docker logs <failing-service>
   ```

4. **Run Regression Tests**
   ```bash
   make test-services
   ```

5. **Fix Issues** based on error messages

6. **Verify Fix**
   ```bash
   make check-services
   ```

## Expected Service Behaviors

### Portal (http://localhost/)
- **Status Code**: 200
- **Content-Type**: text/html
- **Content**: Should contain "Hello World" or "Odin"

### Portal Health (http://localhost/health)
- **Status Code**: 200
- **Content-Type**: application/json
- **Content**: `{"status": "healthy", "service": "odin-web"}`

### Nginx Health (http://localhost/nginx-health)
- **Status Code**: 200
- **Content-Type**: text/plain
- **Content**: "nginx healthy"

### Other Services
- **Ollama**: 200, 404, or 405 (depending on setup)
- **n8n**: 200 or 401 (might require authentication)
- **RabbitMQ**: 200 or 401 (requires authentication)
- **Vault**: 200, 307, or 400 (various responses possible)
- **MinIO**: 200 or 403 (requires authentication)

## Continuous Testing

Add these tests to your workflow:

```bash
# Before committing changes
make check-services
make test-services

# After deployment
make check-services

# In CI/CD pipeline
make test-services
```

## Service URLs Reference

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Portal Root | http://localhost/ | 200 (HTML) |
| Portal Health | http://localhost/health | 200 (JSON) |
| Portal Static | http://localhost/static/css/style.css | 200 (CSS) |
| Nginx Health | http://localhost/nginx-health | 200 (Text) |
| Ollama | http://localhost/ollama/ | Variable |
| n8n | http://localhost/n8n/ | 200/401 |
| RabbitMQ | http://localhost/rabbitmq/ | 200/401 |
| Vault | http://localhost/vault/ | 200/307/400 |
| MinIO | http://localhost/minio/ | 200/403 |

## Getting Help

If you're still having issues:

1. Run the diagnostic: `make check-services`
2. Check the output for specific errors
3. Look at container logs: `docker logs <container-name>`
4. Verify services are running: `docker ps`
5. Check network connectivity between containers
6. Restart all services: `make down && make services-up`

---

**Remember**: Always run `make check-services` first to identify which services are having issues!

