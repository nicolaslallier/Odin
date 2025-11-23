# Odin v2.0.0 Micro-Frontend Architecture

## Overview

Odin v2.0.0 introduces a comprehensive micro-frontend architecture built on **Webpack Module Federation**, allowing independent development, deployment, and scaling of UI components alongside their Python backend services.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                            Nginx                                 │
│  ┌──────────────┐  ┌────────────────────────────────────────┐  │
│  │  /           │  │  /mfe/{service}/                        │  │
│  │  Portal      │  │  Micro-Frontend Bundles                 │  │
│  └──────────────┘  └────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /api/{service}/                                          │  │
│  │  Backend API Endpoints                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
   ┌──────────▼──────────┐       ┌───────────▼────────────┐
   │   Portal (Shell)    │       │  API Microservices     │
   │                     │       │                        │
   │ - React App         │       │ - health (8004)        │
   │ - Module Federation │       │ - data (8006)          │
   │   Host              │       │ - confluence (8001)    │
   │ - Authentication    │       │ - files (8002)         │
   │ - Routing           │       │ - llm (8003)           │
   │ - Layout            │       │ - logs (8005)          │
   │                     │       │ - secrets (8007)       │
   │ Loads:              │       │ - messages (8008)      │
   │ - Health MFE        │       │ - image-analysis (8009)│
   │ - Data MFE          │       │                        │
   │ - ... all MFEs      │       │ Each serves:           │
   │                     │       │ - API endpoints        │
   │                     │       │ - React bundle (MFE)   │
   │                     │       │ - Direct DB access     │
   └─────────────────────┘       └────────────────────────┘
```

## Core Concepts

### 1. Portal (Shell Application)

The **Portal** is the main entry point and orchestrator for the entire application:

- **Location**: `frontend/portal/`
- **Technology**: React 18 + TypeScript + Webpack Module Federation (Host)
- **Responsibilities**:
  - User authentication and authorization
  - Top-level navigation and layout
  - Dynamic loading of micro-frontends
  - Shared state management
  - Error boundaries for fault isolation
  - Service discovery

- **Served by**: `portal` Python service on port 8000
- **Access**: `http://localhost/` (via nginx)

### 2. Micro-Frontends

Each **Micro-Frontend** is an independent React application that can be developed, tested, and deployed separately:

- **Location**: `frontend/microservices/{service}/`
- **Technology**: React 18 + TypeScript + Webpack Module Federation (Remote)
- **Pattern**: Each MFE exposes specific components via Module Federation
- **Isolation**: CSS Modules for style isolation, error boundaries for fault tolerance

**Example: Health Micro-Frontend**
- **Location**: `frontend/microservices/health/`
- **Exposes**:
  - `./HealthApp` - Main application component
  - `./routes` - Route definitions for portal integration
- **Features**:
  - Real-time health dashboard
  - Historical health data visualization
  - Service-specific detail views
  - Charts using Recharts

### 3. Python Backend Services

Each **API Microservice** serves both its backend API and its compiled React micro-frontend:

```python
# Example: src/api/apps/health_app.py
app.mount("/health/mfe", StaticFiles(directory=str(mfe_dir)), name="health-mfe")
```

**Key characteristics**:
- **Direct database access** - Each service owns its data schema
- **Independent deployment** - Can be scaled or restarted independently
- **Fault isolation** - Failure of one service doesn't affect others
- **Technology**: Python 3.11+ / FastAPI

### 4. Module Federation

**Webpack Module Federation** enables runtime code sharing and dynamic loading:

**Host Configuration (Portal)**:
```javascript
new ModuleFederationPlugin({
  name: 'portal',
  remotes: {
    health: 'health@/mfe/health/remoteEntry.js',
    data: 'data@/mfe/data/remoteEntry.js',
    // ... other services
  },
  shared: {
    react: { singleton: true },
    'react-dom': { singleton: true },
    'react-router-dom': { singleton: true },
  },
})
```

**Remote Configuration (Health MFE)**:
```javascript
new ModuleFederationPlugin({
  name: 'health',
  filename: 'remoteEntry.js',
  exposes: {
    './HealthApp': './src/HealthApp',
    './routes': './src/routes',
  },
  shared: {
    react: { singleton: true },
    'react-dom': { singleton: true },
  },
})
```

## Project Structure

```
/Users/nicolaslallier/Dev Nick/Odin/
├── frontend/
│   ├── portal/                    # Portal shell application
│   │   ├── src/
│   │   │   ├── App.tsx           # Main app with routing
│   │   │   ├── index.tsx         # Entry point
│   │   │   ├── context/          # Auth & MFE contexts
│   │   │   ├── components/       # Layout, navigation
│   │   │   ├── pages/            # Home, login, 404
│   │   │   └── styles/           # Global CSS
│   │   ├── public/
│   │   ├── package.json
│   │   └── webpack.config.js     # Module Federation host config
│   │
│   ├── packages/
│   │   └── shared/               # Shared utilities
│   │       ├── src/
│   │       │   ├── types/        # TypeScript types
│   │       │   ├── components/   # Shared React components
│   │       │   ├── utils/        # API client, formatters
│   │       │   ├── hooks/        # Custom React hooks
│   │       │   └── constants/    # Shared constants
│   │       └── package.json
│   │
│   └── microservices/
│       ├── health/               # Health monitoring MFE
│       │   ├── src/
│       │   │   ├── HealthApp.tsx # Main component
│       │   │   ├── routes.ts     # Route definitions
│       │   │   └── components/   # Health-specific components
│       │   ├── public/
│       │   ├── package.json
│       │   └── webpack.config.js # Module Federation remote config
│       │
│       ├── data/                 # Data management MFE
│       ├── confluence/           # Confluence integration MFE
│       ├── files/                # File management MFE
│       ├── llm/                  # LLM services MFE
│       ├── logs/                 # Logs viewing MFE
│       ├── secrets/              # Secrets management MFE
│       ├── messages/             # Messages MFE
│       └── image-analysis/       # Image analysis MFE
│
├── src/
│   ├── api/                      # API microservices (Python/FastAPI)
│   │   ├── apps/                 # Service applications
│   │   │   ├── health_app.py    # Health microservice
│   │   │   ├── data_app.py      # Data microservice
│   │   │   └── ...               # Other microservices
│   │   ├── routes/               # API routes
│   │   ├── repositories/         # Database repositories
│   │   └── services/             # Business logic
│   │
│   ├── web/                      # Portal backend (Python/FastAPI)
│   │   └── app.py               # Serves React portal
│   │
│   └── worker/                   # Celery worker
│       └── tasks/                # Background tasks
│
├── package.json                  # Root workspace config
├── tsconfig.json                 # TypeScript config
├── Dockerfile                    # Multi-stage build
├── docker-compose.yml            # Service orchestration
└── nginx/
    └── nginx.conf               # Routing configuration
```

## Data Flow

### 1. User Authentication

```
User → Portal (/login) → Auth Context → localStorage → All MFEs
```

The portal manages authentication and shares the auth state with all micro-frontends through context and local storage.

### 2. Micro-Frontend Loading

```
Portal loads → Discovers services (/api/portal/services) →
Dynamically imports MFE (health@/mfe/health/remoteEntry.js) →
Renders MFE component → MFE calls API (/api/health/*) →
API service returns data → MFE updates UI
```

### 3. Health Data Pipeline (Example)

```
Worker (Celery Beat) → Collects health data every minute →
POST /api/health/record → Health API Service →
Writes directly to TimescaleDB (service_health_checks table) →
Health MFE → GET /api/health/history → Visualizes data
```

## Key Design Decisions

### 1. Module Federation over iframe

**Why Module Federation?**
- True code sharing (shared React instances, shared dependencies)
- Type-safe integration with TypeScript
- Better performance (no iframe overhead)
- Seamless UX (no iframe sandboxing issues)

### 2. Python Serves React Bundles

**Why colocate?**
- Single deployment unit per service
- Simplified infrastructure
- Consistent versioning (API + UI deployed together)
- Reduced latency (same origin)

### 3. Direct Database Access

**Why direct access?**
- Each microservice owns its data
- No cross-service database queries
- Clear boundaries and responsibilities
- Simplified data consistency

### 4. Nginx Routing Layer

**Why nginx?**
- Single entry point for all services
- CORS handling for Module Federation
- Service discovery abstraction
- SSL/TLS termination
- Load balancing capability

## Development Workflow

### Setting Up Development Environment

```bash
# Install all dependencies
npm install

# Build shared package
npm run build:shared

# Development mode - Portal
npm run dev:portal

# Development mode - Health MFE
npm run dev:mfe:health

# Build all for production
npm run build:all
```

### Docker Development

```bash
# Build with frontend
docker-compose build

# Start all services
docker-compose --profile all up

# View portal
open http://localhost
```

### Adding a New Micro-Frontend

1. **Create React Application**:
```bash
mkdir -p frontend/microservices/my-service
cd frontend/microservices/my-service
npm init -y
```

2. **Configure Module Federation** in `webpack.config.js`:
```javascript
new ModuleFederationPlugin({
  name: 'myService',
  filename: 'remoteEntry.js',
  exposes: {
    './MyServiceApp': './src/MyServiceApp',
    './routes': './src/routes',
  },
  shared: { /* ... */ },
})
```

3. **Update Portal** to load the new MFE in `frontend/portal/webpack.config.js`:
```javascript
remotes: {
  myService: 'myService@/mfe/my-service/remoteEntry.js',
}
```

4. **Update Python Backend** in `src/api/apps/my_service_app.py`:
```python
mfe_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "microservices" / "my-service" / "dist"
if mfe_dir.exists():
    app.mount("/my-service/mfe", StaticFiles(directory=str(mfe_dir)), name="my-service-mfe")
```

5. **Update Nginx** in `nginx/nginx.conf`:
```nginx
location /mfe/my-service/ {
    set $api_my_service_backend http://api-my-service:8010;
    proxy_pass $api_my_service_backend/my-service/mfe/;
    add_header 'Access-Control-Allow-Origin' '*' always;
}
```

## Testing Strategy

### Unit Tests (Jest + React Testing Library)
```bash
npm run test --workspace=@odin/mfe-health
```

### Integration Tests
- Test portal loading micro-frontends
- Test authentication flow
- Test API communication

### E2E Tests (Playwright/Cypress)
- Full user workflows
- Cross-MFE navigation
- Error handling

## Deployment

### Production Build

```bash
# Build all frontend applications
npm run build:all

# Build Docker images
docker-compose build

# Deploy
docker-compose --profile all up -d
```

### CI/CD Considerations

1. **Build Order**: shared → portal → microservices
2. **Cache**: Cache `node_modules` and `frontend/*/dist`
3. **Parallel Builds**: Build MFEs in parallel
4. **Health Checks**: Wait for services to be healthy before deployment

## Troubleshooting

### MFE Fails to Load

**Symptom**: `Error loading remote entry`

**Solutions**:
1. Check nginx routing configuration
2. Verify CORS headers are set
3. Check service is running: `docker-compose ps`
4. Verify build output exists: `ls frontend/microservices/health/dist/`

### Shared Dependencies Conflict

**Symptom**: React hooks error, duplicate React instances

**Solution**: Ensure `singleton: true` for shared dependencies in Module Federation config.

### Authentication Not Persisting

**Symptom**: Login required on every page refresh

**Solution**: Check `localStorage` is accessible and `AuthContext` is wrapping the app.

## Performance Considerations

1. **Code Splitting**: Each MFE is loaded on-demand
2. **Shared Dependencies**: React, React-DOM, React-Router shared across all MFEs
3. **Lazy Loading**: MFEs loaded only when their routes are accessed
4. **Caching**: Nginx caches static assets with appropriate headers
5. **Bundle Size**: Monitor bundle sizes with webpack-bundle-analyzer

## Security

1. **CORS**: Properly configured for Module Federation
2. **Authentication**: Centralized in portal, shared via context
3. **API Security**: Each service validates auth tokens
4. **XSS Protection**: React's built-in escaping
5. **CSP**: Content Security Policy headers in nginx

## Future Enhancements

1. **Dynamic Service Discovery**: Auto-detect running microservices
2. **Feature Flags**: Toggle features without redeployment
3. **A/B Testing**: Test different MFE versions
4. **Analytics**: Track MFE loading performance
5. **Micro-Frontend Versioning**: Support multiple versions simultaneously

## References

- [Webpack Module Federation Documentation](https://webpack.js.org/concepts/module-federation/)
- [React Documentation](https://react.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Odin API Guide](./API_GUIDE.md)
- [Odin Development Guide](./README.md)

