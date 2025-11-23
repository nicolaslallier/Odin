# Release Notes - Odin v1.7.0

**Release Date:** November 23, 2025  
**Version:** 1.7.0  
**Codename:** Microservices Revolution

## ✨ Major Architecture Change

- The Odin API is now nine independent microservices (confluence, files, llm, health, logs, data, secrets, messages, image-analysis)
- Each service is individually startable/stoppable and automatically shuts down after inactivity (default: 5 minutes)
- Nginx and Docker Compose fully reworked for microservice routing and management
- Unified scripts for easy service start/stop/list and automatic idle shutdown
- No breaking changes for any clients: all API URLs remain compatible and auto-routed by nginx

## 📚 Documentation

- Full new guide: MICROSERVICES_GUIDE.md
- Updated README.md, API_GUIDE.md, env.example
- All management, usage, migration, and troubleshooting help included

## 🧪 Testing

- 100% new test suite for all microservice factories, middleware, orchestration scripts, and end-to-end integration
- Integration tests confirm nginx/docker-compose integrity, service entry points, and script operability

## 🏆 Summary of Benefits

- Resource-efficient; only active services run
- Fault isolation, independent scaling
- Zero migration effort for API clients (all routes compatible)
- Full dev/prod flexibility, easy operational management

---

For details, see [MICROSERVICES_GUIDE.md], [API_GUIDE.md], or release source on GitHub.

