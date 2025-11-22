# Odin Quick Start Guide

## Get Everything Running (5 minutes)

### Step 1: Rebuild Everything

```bash
# Stop any running containers
make down

# Rebuild with new configuration
make rebuild

# This will install new dependencies and configure everything
```

### Step 2: Start All Services

```bash
# Start all services including nginx and portal
make up

# Wait 30 seconds for services to initialize
```

### Step 3: Verify Everything Works

```bash
# Check service accessibility
make check-services

# You should see: ✅ All services accessible!
```

### Step 4: Access Your Portal

Open your browser and go to:
- **http://localhost/** - Your Odin Web Portal (Hello World page)

Other services:
- http://localhost/health - Portal health check
- http://localhost/ollama/ - Ollama AI
- http://localhost/n8n/ - n8n workflow automation
- http://localhost/rabbitmq/ - RabbitMQ (user: odin, pass: odin_dev_password)
- http://localhost/vault/ - Vault
- http://localhost/minio/ - MinIO (user: minioadmin, pass: minioadmin)

## Common Commands

```bash
# View portal logs
docker logs portal -f

# View all logs
make logs

# Restart portal
docker-compose restart portal

# Access portal shell (while web server keeps running)
make shell

# Stop everything
make down
```

## If Something Goes Wrong

```bash
# 1. Check what's failing
make check-services

# 2. Check container status
docker ps -a

# 3. Check logs
docker logs portal
docker logs odin-nginx

# 4. Nuclear option - clean restart
make down
docker system prune -f
make rebuild
make up
```

## Development Modes

### Production Mode (Default - Web Server Runs Automatically)
```bash
make up
# Portal starts automatically, access at http://localhost/
```

### Development Mode (Interactive Shell)
```bash
make shell-dev
# Opens bash shell, run commands manually
# To start web server: python -m src.web
```

### Run Tests
```bash
# All tests
make test

# Only web tests
make web-test

# Service accessibility tests
make test-services

# Check services
make check-services
```

## Architecture

```
Browser (http://localhost/)
    ↓
Nginx (Port 80)
    ↓
Portal Container (Port 8000, internal)
    ↓
FastAPI Application
```

## Troubleshooting

### "Connection Refused" Error
**Cause**: Portal web server not running
**Fix**:
```bash
docker logs portal  # Check if web server started
make down
make rebuild
make up
```

### "502 Bad Gateway" Error
**Cause**: Portal started but crashed
**Fix**:
```bash
docker logs portal  # Check for errors
# Fix the error, then:
docker-compose restart portal
```

### Portal Not Starting
**Cause**: Missing dependencies or build error
**Fix**:
```bash
make rebuild  # Rebuilds everything from scratch
```

### Need Interactive Shell
```bash
# Access running container shell
make shell

# Or start in dev mode with shell
make shell-dev
```

## Next Steps

1. ✅ Verify services work: `make check-services`
2. ✅ Run tests: `make test-services`
3. ✅ Access portal: http://localhost/
4. 📖 Read: `SERVICE_TESTING_GUIDE.md` for detailed diagnostics
5. 📖 Read: `WEB_INTERFACE_GUIDE.md` for development guide

---

**Need Help?** Run `make check-services` and check the output!

