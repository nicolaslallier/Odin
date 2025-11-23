# Frontend Development Guide - Odin v2.0.0

## Quick Start

### Prerequisites

- **Node.js**: 20.x or higher
- **npm**: 10.x or higher  
- **Docker**: For running backend services
- **Git**: For version control

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd odin

# Install all dependencies (portal + micro-frontends + shared)
npm install

# Build the shared package first (required dependency)
npm run build:shared
```

## Development Workflow

### Option 1: Full Stack Development (Recommended)

Run backend services in Docker and frontend in development mode for hot reload:

```bash
# Terminal 1: Start backend services
docker-compose --profile health up

# Terminal 2: Start portal in dev mode (hot reload)
npm run dev:portal

# Terminal 3: Start health MFE in dev mode (hot reload)
npm run dev:mfe:health
```

**Access**:
- Portal: `http://localhost:3000` (webpack dev server)
- Health MFE: `http://localhost:3001` (standalone dev mode)
- API: `http://localhost/api/health/` (via nginx)

### Option 2: Full Docker Build

Build and run everything in Docker:

```bash
# Build all (includes frontend build in Docker)
docker-compose build

# Run all services
docker-compose --profile all up

# Access portal
open http://localhost
```

## Project Structure

```
frontend/
├── portal/                      # Main application shell
│   ├── src/
│   │   ├── App.tsx             # Root component with routing
│   │   ├── index.tsx           # Entry point
│   │   ├── context/
│   │   │   ├── AuthContext.tsx            # Authentication
│   │   │   └── MicroFrontendContext.tsx   # Service discovery
│   │   ├── components/
│   │   │   ├── Layout.tsx                 # Main layout
│   │   │   ├── Navigation.tsx             # Sidebar nav
│   │   │   ├── Header.tsx                 # Top bar
│   │   │   ├── ProtectedRoute.tsx         # Auth guard
│   │   │   └── MicroFrontendRoutes.tsx    # Dynamic MFE loading
│   │   ├── pages/
│   │   │   ├── HomePage.tsx               # Dashboard
│   │   │   ├── LoginPage.tsx              # Login form
│   │   │   └── NotFoundPage.tsx           # 404
│   │   └── styles/
│   │       └── global.css                 # Global styles
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── webpack.config.js       # Module Federation HOST config
│
├── packages/
│   └── shared/                  # Shared utilities library
│       ├── src/
│       │   ├── types/          # TypeScript definitions
│       │   │   ├── api.ts              # API types
│       │   │   ├── common.ts           # Common types
│       │   │   ├── health.ts           # Health types
│       │   │   └── auth.ts             # Auth types
│       │   ├── components/     # Reusable components
│       │   │   ├── Button.tsx
│       │   │   ├── Card.tsx
│       │   │   ├── Loading.tsx
│       │   │   ├── ErrorBoundary.tsx
│       │   │   └── StatusBadge.tsx
│       │   ├── utils/          # Utility functions
│       │   │   ├── api-client.ts       # HTTP client
│       │   │   ├── format.ts           # Formatters
│       │   │   ├── date.ts             # Date utilities
│       │   │   └── storage.ts          # LocalStorage helpers
│       │   ├── hooks/          # Custom React hooks
│       │   │   ├── useApi.ts           # API call hook
│       │   │   ├── useAuth.ts          # Auth hook
│       │   │   └── useLocalStorage.ts  # Storage hook
│       │   └── constants/      # Shared constants
│       │       └── index.ts
│       └── package.json
│
└── microservices/
    └── health/                  # Health monitoring MFE
        ├── src/
        │   ├── HealthApp.tsx           # Main component (exposed)
        │   ├── index.tsx               # Standalone entry
        │   ├── routes.ts               # Route definitions (exposed)
        │   └── components/
        │       ├── HealthDashboard.tsx # Current status view
        │       ├── HealthHistory.tsx   # Historical data
        │       ├── HealthDetails.tsx   # Service details
        │       └── HealthChart.tsx     # Data visualization
        ├── public/
        │   └── index.html
        ├── package.json
        ├── tsconfig.json
        └── webpack.config.js   # Module Federation REMOTE config
```

## Creating a New Micro-Frontend

### Step 1: Create Directory Structure

```bash
mkdir -p frontend/microservices/my-service/src/components
mkdir -p frontend/microservices/my-service/public
cd frontend/microservices/my-service
```

### Step 2: Create `package.json`

```json
{
  "name": "@odin/mfe-my-service",
  "version": "2.0.0",
  "private": true,
  "scripts": {
    "dev": "webpack serve --mode development",
    "build": "webpack --mode production",
    "lint": "eslint src --ext .ts,.tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@odin/shared": "*",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "typescript": "^5.3.3",
    "webpack": "^5.89.0",
    "webpack-cli": "^5.1.4",
    "webpack-dev-server": "^4.15.1",
    "ts-loader": "^9.5.1",
    "html-webpack-plugin": "^5.6.0"
  }
}
```

### Step 3: Create `webpack.config.js`

```javascript
const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    entry: './src/index.tsx',
    mode: isProduction ? 'production' : 'development',
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].[contenthash].js',
      publicPath: 'auto',
      clean: true,
    },

    resolve: {
      extensions: ['.tsx', '.ts', '.js', '.jsx'],
      alias: {
        '@odin/shared': path.resolve(__dirname, '../../packages/shared/src'),
      },
    },

    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
      ],
    },

    plugins: [
      new ModuleFederationPlugin({
        name: 'myService',
        filename: 'remoteEntry.js',
        exposes: {
          './MyServiceApp': './src/MyServiceApp',
          './routes': './src/routes',
        },
        shared: {
          react: { singleton: true, requiredVersion: '^18.2.0' },
          'react-dom': { singleton: true, requiredVersion: '^18.2.0' },
          'react-router-dom': { singleton: true, requiredVersion: '^6.20.1' },
        },
      }),
      new HtmlWebpackPlugin({
        template: './public/index.html',
      }),
    ],

    devServer: {
      port: 3002, // Use unique port
      hot: true,
      historyApiFallback: true,
      headers: { 'Access-Control-Allow-Origin': '*' },
      proxy: { '/api': { target: 'http://localhost', changeOrigin: true } },
    },
  };
};
```

### Step 4: Create React Components

**src/MyServiceApp.tsx**:
```typescript
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from '@odin/shared';

export const MyServiceApp: React.FC = () => {
  return (
    <ErrorBoundary>
      <div className="my-service-app">
        <Routes>
          <Route path="/" element={<div>My Service Home</div>} />
        </Routes>
      </div>
    </ErrorBoundary>
  );
};
```

**src/routes.ts**:
```typescript
import { RouteConfig } from '@odin/shared';

export const routes: RouteConfig[] = [
  {
    path: '/my-service',
    title: 'My Service',
    icon: 'service',
    exact: true,
  },
];
```

**src/index.tsx** (for standalone dev):
```typescript
import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MyServiceApp } from './MyServiceApp';

const container = document.getElementById('root');
if (!container) throw new Error('Root element not found');

const root = createRoot(container);
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <MyServiceApp />
    </BrowserRouter>
  </React.StrictMode>
);
```

### Step 5: Integrate with Portal

Update `frontend/portal/webpack.config.js`:

```javascript
remotes: {
  // ... existing remotes
  myService: 'myService@/mfe/my-service/remoteEntry.js',
},
```

### Step 6: Update Python Backend

**src/api/apps/my_service_app.py**:
```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def create_app(config = None) -> FastAPI:
    app = create_base_app("my-service", config=config)
    
    # Mount micro-frontend
    mfe_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "microservices" / "my-service" / "dist"
    if mfe_dir.exists():
        app.mount("/my-service/mfe", StaticFiles(directory=str(mfe_dir)), name="my-service-mfe")
    
    return app
```

### Step 7: Update Nginx

Add to `nginx/nginx.conf`:

```nginx
location /mfe/my-service/ {
    set $api_my_service_backend http://api-my-service:8010;
    proxy_pass $api_my_service_backend/my-service/mfe/;
    add_header 'Access-Control-Allow-Origin' '*' always;
    proxy_intercept_errors on;
    error_page 502 503 504 = @api_unavailable;
}
```

### Step 8: Update Root `package.json`

Add build script:

```json
{
  "scripts": {
    "build:mfe:my-service": "npm run build --workspace=@odin/mfe-my-service",
    "build:all:mfes": "npm run build:mfe:health && npm run build:mfe:my-service && ...",
  }
}
```

## Common Development Tasks

### Adding a New Shared Component

1. Create component in `frontend/packages/shared/src/components/`
2. Export from `frontend/packages/shared/src/components/index.ts`
3. Rebuild shared package: `npm run build:shared`
4. Import in micro-frontends: `import { MyComponent } from '@odin/shared'`

### Adding a New API Type

1. Define type in `frontend/packages/shared/src/types/`
2. Export from appropriate index file
3. Use in components with full type safety

### Debugging

**Portal**:
```bash
# Open browser dev tools
# Check console for Module Federation errors
# Use React DevTools extension
```

**Micro-Frontend**:
```bash
# Run standalone
npm run dev:mfe:health

# Access at http://localhost:3001
# Debug in isolation
```

**API Calls**:
```typescript
// Enable request logging
import { apiClient } from '@odin/shared';

// apiClient automatically logs errors
// Check browser Network tab for requests
```

## Testing

### Unit Tests

```bash
# Run tests for specific MFE
npm test --workspace=@odin/mfe-health

# Run with coverage
npm test --workspace=@odin/mfe-health -- --coverage

# Watch mode
npm test --workspace=@odin/mfe-health -- --watch
```

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

test('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

## Build and Deployment

### Development Build

```bash
# Build specific MFE
npm run build:mfe:health

# Build portal
npm run build:portal

# Build all
npm run build:all
```

### Production Build

```bash
# Build optimized bundles
NODE_ENV=production npm run build:all

# Output: frontend/*/dist/
```

### Docker Build

```bash
# Build with frontend
docker-compose build

# The Dockerfile handles:
# 1. Node.js build stage (npm run build:all)
# 2. Python runtime stage (copy dist/ folders)
```

## Code Quality

### Linting

```bash
# Lint all frontend code
npm run lint:frontend

# Lint specific workspace
npm run lint --workspace=@odin/portal

# Auto-fix issues
npm run lint --workspace=@odin/portal -- --fix
```

### Formatting

```bash
# Format all code
npm run format:frontend

# Format specific workspace
npm run format --workspace=@odin/mfe-health
```

### Type Checking

```bash
# Check types across all workspaces
npm run type-check:frontend

# Check specific workspace
npm run type-check --workspace=@odin/portal
```

## Troubleshooting

### Module Federation Errors

**Error**: `Shared module is not available for eager consumption`

**Solution**: Ensure `singleton: true` for React in Module Federation config

### Build Errors

**Error**: `Cannot find module '@odin/shared'`

**Solution**: Build shared package first: `npm run build:shared`

### Hot Reload Not Working

**Solution**: 
1. Check webpack dev server is running
2. Verify proxy configuration
3. Check CORS headers

### TypeScript Errors

**Error**: `Could not find a declaration file for module '@odin/shared'`

**Solution**: Run `npm run build:shared` to generate type declarations

## Best Practices

1. **Always build shared package first** before developing MFEs
2. **Use TypeScript strictly** - enable all strict flags
3. **Component isolation** - keep components pure and testable
4. **Error boundaries** - wrap risky code in ErrorBoundary
5. **Loading states** - always show loading indicators for async operations
6. **Code splitting** - use React.lazy() for large components
7. **Accessibility** - follow WCAG guidelines
8. **Performance** - monitor bundle sizes, use React.memo() judiciously

## Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Module Federation Docs](https://webpack.js.org/concepts/module-federation/)
- [Odin Architecture Guide](./MICROFRONTEND_ARCHITECTURE.md)
- [Release Notes](./RELEASE_NOTES_v2.0.0.md)

